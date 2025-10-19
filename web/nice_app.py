from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from nicegui import app, events, ui

from config_runner import run_from_config

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class FlowList(list):
    """Representa una lista que debe serializarse en estilo inline."""


def _flow_list_representer(dumper: yaml.Dumper, data: FlowList) -> yaml.SequenceNode:
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


yaml.add_representer(FlowList, _flow_list_representer)
yaml.SafeDumper.add_representer(FlowList, _flow_list_representer)


@dataclass
class DefaultsState:
    tipo_imagen: str = "MCMI"
    satelite: str = "GOES16"
    data_dir: str = "data/"
    recorte: str = "[-18.6, -56.45, -79.79, -50.0]"
    export_out_dir: str = "salidas/"
    export_show: bool = False
    export_shp: str = ""


@dataclass
class JobState:
    nombre: str = ""
    tipo_imagen: str = ""
    satelite: str = "GOES19"
    datetime: str = ""
    productos: str = "true_color"
    canales: str = ""
    salidas: str = "PNG"
    data_dir: str = ""
    recorte: str = ""
    geotiff_enabled: bool = False
    geotiff_producto: str = ""
    geotiff_out_dir: str = ""
    geotiff_filename_pattern: str = "{producto}_{ts}.tif"


@dataclass
class AppState:
    defaults: DefaultsState = field(default_factory=DefaultsState)
    jobs: List[JobState] = field(default_factory=lambda: [JobState()])
    selected_config: Optional[str] = None


state = AppState()

yaml_area: Optional[ui.textarea] = None
status_label: Optional[ui.label] = None
config_select: Optional[ui.select] = None
config_name_input: Optional[ui.input] = None
save_button: Optional[ui.button] = None
run_button: Optional[ui.button] = None
add_job_button: Optional[ui.button] = None
log_view: Optional[ui.log] = None
spinner: Optional[ui.spinner] = None
jobs_container: Optional[ui.column] = None


def _split_list(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_recorte(text: str) -> Optional[List[float]]:
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]
    parts = [
        item.strip() for item in stripped.replace(";", ",").split(",") if item.strip()
    ]
    if len(parts) != 4:
        raise ValueError("El recorte debe tener 4 valores numéricos.")
    try:
        values = [float(item) for item in parts]
    except ValueError as exc:  # noqa: TRY003
        raise ValueError("Los valores de recorte deben ser numéricos.") from exc
    return values


def _format_recorte_input(value: Any) -> str:
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return f"[{', '.join(str(v) for v in value)}]"
    return str(value) if value not in (None, "") else ""


def _clean_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in data.items()
        if value not in (None, "", [], {}, False)
    }


def _build_defaults_dict() -> Dict[str, Any]:
    defaults = {
        "tipo_imagen": state.defaults.tipo_imagen or None,
        "satelite": state.defaults.satelite or None,
        "data_dir": state.defaults.data_dir or None,
    }

    if state.defaults.recorte:
        recorte_values = _parse_recorte(state.defaults.recorte)
        if recorte_values:
            defaults["recorte"] = FlowList(recorte_values)

    export_cfg: Dict[str, Any] = {}
    if state.defaults.export_out_dir:
        export_cfg["out_dir"] = state.defaults.export_out_dir
    if state.defaults.export_show:
        export_cfg["show"] = state.defaults.export_show
    if state.defaults.export_shp:
        export_cfg["shapefile_provincias"] = state.defaults.export_shp

    if export_cfg:
        defaults["export"] = export_cfg

    return _clean_dict(defaults)


def _build_job_dict(job: JobState) -> Dict[str, Any]:
    job_cfg: Dict[str, Any] = {
        "nombre": job.nombre or None,
        "tipo_imagen": job.tipo_imagen or None,
        "satelite": job.satelite or None,
        "data_dir": job.data_dir or None,
    }

    if job.datetime:
        dt = job.datetime.strip()
        if dt and len(dt) == 16 and dt.count(":") == 1:
            dt = f"{dt}:00"
        job_cfg["datetime"] = dt

    productos = _split_list(job.productos)
    if productos:
        job_cfg["productos"] = FlowList(productos)

    canales = _split_list(job.canales)
    if canales:
        job_cfg["canales"] = FlowList(canales)

    salidas = _split_list(job.salidas)
    if salidas:
        job_cfg["salidas"] = FlowList(salidas)

    if job.recorte:
        recorte_values = _parse_recorte(job.recorte)
        if recorte_values:
            job_cfg["recorte"] = FlowList(recorte_values)

    if job.geotiff_enabled:
        geo_cfg: Dict[str, Any] = {}
        if job.geotiff_producto:
            geo_cfg["producto"] = job.geotiff_producto
        if job.geotiff_out_dir:
            geo_cfg["out_dir"] = job.geotiff_out_dir
        if job.geotiff_filename_pattern:
            geo_cfg["filename_pattern"] = job.geotiff_filename_pattern
        if geo_cfg:
            job_cfg["geotiff_conf"] = geo_cfg

    return _clean_dict(job_cfg)


def _build_yaml_document() -> Dict[str, Any]:
    defaults = _build_defaults_dict()
    jobs = [_build_job_dict(job) for job in state.jobs]

    jobs = [job for job in jobs if job]
    if not jobs:
        raise ValueError("Necesitás al menos un job válido.")

    doc = _clean_dict({"defaults": defaults, "jobs": jobs})
    if "defaults" not in doc:
        raise ValueError("Revisá los defaults ingresados.")
    return doc


def build_yaml_text() -> str:
    doc = _build_yaml_document()
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120)


async def _refresh_yaml_output() -> None:
    if yaml_area is None or status_label is None:
        return
    try:
        yaml_text = build_yaml_text()
    except Exception as exc:  # noqa: BLE001
        yaml_area.value = f"# Error: {exc}"
        status_label.text = str(exc)
        status_label.style("color: #ff8a80")
    else:
        yaml_area.value = yaml_text
        status_label.text = "YAML listo para guardar o ejecutar."
        status_label.style("color: #9be7ff")


async def _refresh_config_list(select: ui.select, keep: Optional[str] = None) -> None:
    if select is None:
        return
    configs = sorted(
        {p.name for p in CONFIG_DIR.glob("*.yml")}
        | {p.name for p in CONFIG_DIR.glob("*.yaml")}
    )
    select.options = configs
    if keep and keep in configs:
        select.value = keep
        state.selected_config = keep
    elif configs:
        select.value = configs[0]
        state.selected_config = select.value
    else:
        select.value = None
        state.selected_config = None


async def _load_config(path_name: str) -> None:
    path = (CONFIG_DIR / path_name).resolve()
    if not path.exists():
        ui.notify(f"No se encontró {path_name}", color="negative")
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # noqa: BLE001
        ui.notify(f"YAML inválido: {exc}", color="negative")
        return

    defaults = data.get("defaults", {})
    state.defaults.tipo_imagen = defaults.get("tipo_imagen", "") or ""
    state.defaults.satelite = defaults.get("satelite", "") or ""
    state.defaults.data_dir = defaults.get("data_dir", "") or ""
    state.defaults.recorte = _format_recorte_input(defaults.get("recorte", ""))
    export = defaults.get("export", {}) if isinstance(defaults, dict) else {}
    state.defaults.export_out_dir = export.get("out_dir", "") or ""
    state.defaults.export_show = bool(export.get("show", False))
    state.defaults.export_shp = export.get("shapefile_provincias", "") or ""

    jobs_data = data.get("jobs", []) if isinstance(data, dict) else []
    if jobs_data:
        new_jobs = []
        for job in jobs_data:
            if not isinstance(job, dict):
                continue
            j = JobState()
            j.nombre = job.get("nombre", "") or ""
            j.tipo_imagen = job.get("tipo_imagen", "") or ""
            j.satelite = job.get("satelite", "") or ""
            dt = job.get("datetime", "") or ""
            if isinstance(dt, str) and len(dt) == 19 and dt.count(":") == 2:
                dt = dt[:-3]
            j.datetime = dt
            productos = job.get("productos", [])
            if isinstance(productos, list):
                j.productos = ", ".join(str(p) for p in productos if p)
            else:
                j.productos = str(productos)
            canales = job.get("canales", [])
            if isinstance(canales, list):
                j.canales = ", ".join(str(c) for c in canales if c)
            else:
                j.canales = str(canales)
            salidas = job.get("salidas", [])
            if isinstance(salidas, list):
                j.salidas = ", ".join(str(s) for s in salidas if s)
            else:
                j.salidas = str(salidas)
            j.data_dir = job.get("data_dir", "") or ""
            j.recorte = _format_recorte_input(job.get("recorte", ""))
            geo = job.get("geotiff_conf") or job.get("geotiff") or {}
            if isinstance(geo, dict):
                j.geotiff_enabled = bool(geo)
                j.geotiff_producto = geo.get("producto", "") or ""
                j.geotiff_out_dir = geo.get("out_dir", "") or ""
                j.geotiff_filename_pattern = (
                    geo.get("filename_pattern", j.geotiff_filename_pattern)
                    or j.geotiff_filename_pattern
                )
            new_jobs.append(j)
        state.jobs = new_jobs or [JobState()]
    else:
        state.jobs = [JobState()]

    render_jobs()
    await _refresh_yaml_output()
    ui.notify(f"Configuración {path_name} cargada", color="positive")


def _validate_filename(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Indicá un nombre de archivo.")
    if not cleaned.endswith((".yml", ".yaml")):
        cleaned = f"{cleaned}.yml"
    resolved = (CONFIG_DIR / cleaned).resolve()
    if not str(resolved).startswith(str(CONFIG_DIR.resolve())):
        raise ValueError("Nombre de archivo inválido.")
    return resolved.name


async def _handle_save(_: events.ClickEventArguments) -> None:
    if config_name_input is None:
        ui.notify("La interfaz todavía no está lista.", color="negative")
        return
    try:
        filename = _validate_filename(
            config_name_input.value or state.selected_config or ""
        )
        yaml_text = build_yaml_text()
    except Exception as exc:  # noqa: BLE001
        ui.notify(str(exc), color="negative")
        return

    path = (CONFIG_DIR / filename).resolve()
    path.write_text(yaml_text, encoding="utf-8")
    await _refresh_config_list(config_select, keep=filename)
    config_name_input.value = filename
    ui.notify(f"Guardado como {filename}", color="positive")


async def _handle_add_job(_: events.ClickEventArguments) -> None:
    state.jobs.append(JobState())
    render_jobs()
    await _refresh_yaml_output()


async def _handle_remove_job(index: int) -> None:
    if len(state.jobs) == 1:
        ui.notify("Debe existir al menos un job.", color="warning")
        return
    state.jobs.pop(index)
    render_jobs()
    await _refresh_yaml_output()


async def _handle_refresh_configs(_: events.ClickEventArguments) -> None:
    await _refresh_config_list(config_select, keep=state.selected_config)
    ui.notify("Lista de configuraciones actualizada.", color="info")


async def _handle_load(_: events.ClickEventArguments) -> None:
    if not state.selected_config:
        ui.notify("Elegí un archivo a cargar.", color="warning")
        return
    await _load_config(state.selected_config)
    config_name_input.value = state.selected_config


async def _handle_select_change(event: events.ValueChangeEventArguments) -> None:
    state.selected_config = event.value or None


async def _handle_defaults_change(_: events.ValueChangeEventArguments) -> None:
    await _refresh_yaml_output()


async def _handle_job_change(_: events.ValueChangeEventArguments) -> None:
    await _refresh_yaml_output()


async def _stream_run_config(path: Path):
    queue: "asyncio.Queue[Optional[str]]" = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _blocking() -> None:
        stdout_fd = sys.stdout.fileno()
        stderr_fd = sys.stderr.fileno()
        stdout_backup = os.dup(stdout_fd)
        stderr_backup = os.dup(stderr_fd)
        pipe_r, pipe_w = os.pipe()

        def _reader() -> None:
            with os.fdopen(pipe_r, "rb", closefd=True) as reader:
                while True:
                    chunk = reader.read(4096)
                    if not chunk:
                        break
                    loop.call_soon_threadsafe(
                        queue.put_nowait, chunk.decode("utf-8", errors="replace")
                    )
            loop.call_soon_threadsafe(queue.put_nowait, None)

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        try:
            os.dup2(pipe_w, stdout_fd)
            os.dup2(pipe_w, stderr_fd)
            os.close(pipe_w)
            logging.captureWarnings(True)
            run_from_config(str(path))
        except Exception as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(queue.put_nowait, f"[ERROR] {exc}\n")
        finally:
            logging.captureWarnings(False)
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            finally:
                os.dup2(stdout_backup, stdout_fd)
                os.dup2(stderr_backup, stderr_fd)
                os.close(stdout_backup)
                os.close(stderr_backup)
                try:
                    os.close(pipe_w)
                except OSError:
                    pass
            reader_thread.join(timeout=1.0)

    async def runner() -> None:
        await asyncio.to_thread(_blocking)

    task = asyncio.create_task(runner())

    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk
    finally:
        await task


async def _handle_run(_: events.ClickEventArguments) -> None:
    if log_view is None or spinner is None or config_name_input is None:
        ui.notify("La interfaz todavía no está lista.", color="negative")
        return
    try:
        filename = _validate_filename(
            config_name_input.value or state.selected_config or "temp_frontend.yml"
        )
        yaml_text = build_yaml_text()
    except Exception as exc:  # noqa: BLE001
        ui.notify(str(exc), color="negative")
        return

    log_view.clear()
    spinner.visible = True
    buttons_disable(True)

    save_path = (CONFIG_DIR / filename).resolve()
    save_path.write_text(yaml_text, encoding="utf-8")
    result_path = save_path

    log_view.push(f"== Ejecutando {result_path.name} ==")

    try:
        async for chunk in _stream_run_config(result_path):
            for line in chunk.splitlines():
                if line.strip():
                    log_view.push(line)
    except Exception as exc:  # noqa: BLE001
        log_view.push(f"[ERROR] {exc}")
        ui.notify(f"Error durante la ejecución: {exc}", color="negative")
    else:
        log_view.push("== Proceso finalizado ==")
        ui.notify("Proceso completado", color="positive")
    finally:
        spinner.visible = False
        buttons_disable(False)
    await _refresh_config_list(config_select, keep=filename)
    config_name_input.value = filename


def buttons_disable(flag: bool) -> None:
    for button in (save_button, run_button, add_job_button):
        if button is None:
            continue
        if flag:
            button.disable()
        else:
            button.enable()


def render_jobs() -> None:
    if jobs_container is None:
        return
    jobs_container.clear()
    for index, job in enumerate(state.jobs):
        with jobs_container:
            with ui.card().classes("w-full gap-3"):
                ui.label(f"Job {index + 1}").classes("text-lg font-semibold")
                with ui.row().classes("gap-4 flex-wrap"):
                    ui.input("Nombre", value=job.nombre).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "nombre", e.value),
                    )
                    ui.input(
                        "Tipo imagen", value=job.tipo_imagen, placeholder="(opcional)"
                    ).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "tipo_imagen", e.value),
                    )
                    ui.input("Satélite", value=job.satelite).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "satelite", e.value),
                    )
                with ui.row().classes("gap-4 flex-wrap"):
                    ui.input(
                        "Datetime (UTC)",
                        value=job.datetime,
                        placeholder="YYYY-MM-DDTHH:MM",
                    ).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "datetime", e.value),
                    )
                    ui.input("Productos (coma)", value=job.productos).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "productos", e.value),
                    )
                    ui.input("Salidas (coma)", value=job.salidas).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "salidas", e.value),
                    )
                with ui.row().classes("gap-4 flex-wrap"):
                    ui.input("Canales (coma)", value=job.canales).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "canales", e.value),
                    )
                    ui.input("Data dir", value=job.data_dir).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "data_dir", e.value),
                    )
                    ui.input(
                        "Recorte",
                        value=job.recorte,
                        placeholder="[-18.6, -56.45, -79.79, -53.0]",
                    ).on(
                        "change",
                        lambda e, idx=index: _update_job(idx, "recorte", e.value),
                    )
                geo_checkbox = ui.checkbox(
                    "Exportar GeoTIFF", value=job.geotiff_enabled
                )
                geo_checkbox.on(
                    "change",
                    lambda e, idx=index: _update_job(idx, "geotiff_enabled", e.value),
                )
                geo_section = ui.column().classes("gap-2 pl-6 border-l border-gray-600")
                geo_section.bind_visibility_from(geo_checkbox, "value")
                with geo_section:
                    ui.input("Producto", value=job.geotiff_producto).on(
                        "change",
                        lambda e, idx=index: _update_job(
                            idx, "geotiff_producto", e.value
                        ),
                    )
                    ui.input("Out dir", value=job.geotiff_out_dir).on(
                        "change",
                        lambda e, idx=index: _update_job(
                            idx, "geotiff_out_dir", e.value
                        ),
                    )
                    ui.input("Pattern", value=job.geotiff_filename_pattern).on(
                        "change",
                        lambda e, idx=index: _update_job(
                            idx, "geotiff_filename_pattern", e.value
                        ),
                    )
                ui.button(
                    "Eliminar job",
                    color="negative",
                    icon="delete",
                    on_click=lambda e, idx=index: asyncio.create_task(
                        _handle_remove_job(idx)
                    ),
                )


def _update_job(index: int, field_name: str, value: Any) -> None:
    job = state.jobs[index]
    if field_name == "geotiff_enabled":
        job.geotiff_enabled = bool(value)
    else:
        setattr(job, field_name, value or "")
    asyncio.create_task(_refresh_yaml_output())


with ui.splitter().classes("h-screen") as splitter:
    with splitter.before:
        with ui.column().classes("p-4 gap-4 max-w-xl"):
            ui.label("Defaults").classes("text-xl font-bold")
            ui.input("Tipo de imagen", value=state.defaults.tipo_imagen).on(
                "change", lambda e: _set_default("tipo_imagen", e.value)
            )
            ui.input("Satélite", value=state.defaults.satelite).on(
                "change", lambda e: _set_default("satelite", e.value)
            )
            ui.input("Data dir", value=state.defaults.data_dir).on(
                "change", lambda e: _set_default("data_dir", e.value)
            )
            ui.input("Recorte", value=state.defaults.recorte).on(
                "change", lambda e: _set_default("recorte", e.value)
            )
            with ui.row().classes("gap-4"):
                ui.input("Export out_dir", value=state.defaults.export_out_dir).on(
                    "change", lambda e: _set_default("export_out_dir", e.value)
                )
                ui.checkbox("Mostrar", value=state.defaults.export_show).on(
                    "change", lambda e: _set_default("export_show", e.value)
                )
            ui.input("Shapefile provincias", value=state.defaults.export_shp).on(
                "change", lambda e: _set_default("export_shp", e.value)
            )
            ui.separator()
            ui.label("Jobs").classes("text-xl font-bold")
            jobs_container = ui.column().classes("gap-4")
            render_jobs()
            add_job_button = ui.button(
                "Agregar job", icon="add", on_click=_handle_add_job
            )
    with splitter.after:
        with ui.column().classes("p-4 gap-4"):
            ui.label("Archivos de configuración").classes("text-xl font-bold")
            config_select = ui.select(options=[], label="Existentes").on(
                "change", _handle_select_change
            )
            with ui.row().classes("gap-2"):
                ui.button("Refrescar", icon="refresh", on_click=_handle_refresh_configs)
                ui.button("Cargar", icon="folder_open", on_click=_handle_load)
            config_name_input = ui.input(
                "Nombre de archivo", placeholder="ej: example.yml"
            )
            save_button = ui.button("Guardar", icon="save", on_click=_handle_save)
            run_button = ui.button(
                "Ejecutar", icon="play_arrow", color="positive", on_click=_handle_run
            )
            status_label = ui.label("Cargando...")
            yaml_area = (
                ui.textarea("YAML generado", value="")
                .props("rows=18")
                .classes("font-mono text-sm")
            )
            ui.separator()
            ui.label("Logs de ejecución").classes("text-xl font-bold")
            spinner = ui.spinner(size="lg")
            spinner.visible = False
            log_view = ui.log(max_lines=2000)


def _set_default(field_name: str, value: Any) -> None:
    setattr(
        state.defaults,
        field_name,
        value if field_name != "export_show" else bool(value),
    )
    asyncio.create_task(_refresh_yaml_output())


async def _startup() -> None:
    if config_select is None or config_name_input is None:
        return
    await _refresh_config_list(config_select)
    config_name_input.value = state.selected_config or ""
    await _refresh_yaml_output()


app.on_startup(_startup)


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    ui.run(host=host, port=port, title="GOES Configurator", reload=False)


if __name__ == "__main__":
    run()
