import yaml
import logging
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Set, Tuple

import imageio.v2 as imageio
import numpy as np
import math

from goes_rgb.l2_abi_image import ABIImageMCMI
from goes_rgb.l1b_abi_image import ABIImageL1b
from goes_rgb.rgb_processor import RGBProcessor
from goes_rgb.visualization import (
    plot_rgb_with_coastlines,
    plot_band_with_coastlines,
)
from goes_rgb.recipes_registry import RECIPE_REGISTRY
from goes_rgb.helpers import save_rgb_geotiff  # NUEVO


logger = logging.getLogger(__name__)


class OutputType(str, Enum):
    """Tipos de salida permitidos."""

    PNG = "PNG"
    GIF = "GIF"
    VIDEO = "VIDEO"
    GEOTIFF = "GEOTIFF"
    COMPONENTES_RGB = "COMPONENTES_RGB"


def load_config(path: Path | str) -> Dict:
    """Carga un archivo YAML y devuelve el dict de configuración."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def expand_datetimes(job: Dict) -> Iterable[datetime]:
    """Devuelve una secuencia de fechas a procesar a partir de la configuración del job."""
    if "datetime" in job:
        yield datetime.fromisoformat(str(job["datetime"]))
    if "datetimes" in job:
        for d in job["datetimes"]:
            yield datetime.fromisoformat(str(d))
    if "rango" in job:
        r = job["rango"]
        ini = datetime.fromisoformat(str(r["inicio"]))
        fin = datetime.fromisoformat(str(r["fin"]))
        paso = int(r.get("paso_minutos", 30))
        cur = ini
        while cur <= fin:
            yield cur
            cur += timedelta(minutes=paso)


def _format_ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%d_%H%M")


def _format_filename(pattern: str, producto: str, ts: str) -> str:
    return pattern.replace("{producto}", producto).replace("{ts}", ts)


def _normalize_rgb_frame(frame: np.ndarray) -> np.ndarray:
    """Normaliza un frame a RGB uint8 sin canal alpha."""
    if frame.ndim == 2:
        frame = np.stack([frame] * 3, axis=-1)
    if frame.shape[-1] == 4:
        frame = frame[..., :3]
    if frame.dtype != np.uint8:
        frame = np.clip(frame, 0, 255).astype(np.uint8)
    return frame


def _pad_frames_to_even_16(frames: List[np.ndarray]) -> List[np.ndarray]:
    """Acolcha a un tamaño común múltiplo de 16 y par (requerido por yuv420p)."""
    if not frames:
        return frames
    max_h = max(fr.shape[0] for fr in frames)
    max_w = max(fr.shape[1] for fr in frames)
    tgt_h = int(np.ceil(max_h / 16) * 16)
    tgt_w = int(np.ceil(max_w / 16) * 16)
    if tgt_h % 2:
        tgt_h += 1
    if tgt_w % 2:
        tgt_w += 1
    padded: List[np.ndarray] = []
    for fr in frames:
        h, w = fr.shape[:2]
        pad_h = tgt_h - h
        pad_w = tgt_w - w
        if pad_h or pad_w:
            fr = np.pad(fr, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
        padded.append(fr)
    return padded


def _validate_job(job: Dict, defaults: Dict) -> None:
    """Valida la configuración mínima del job y lanza ValueError si falta algo crítico."""
    # productos
    productos = job.get("productos")
    if not productos or not isinstance(productos, (list, tuple)):
        raise ValueError("El job debe definir una lista 'productos'.")
    # productos válidos
    invalid = [p for p in productos if p not in RECIPE_REGISTRY]
    if invalid:
        raise ValueError(
            f"Productos no registrados: {invalid}. Disponibles: {sorted(RECIPE_REGISTRY.keys())}"
        )

    # fecha o rango
    if not (
        job.get("datetime")
        or job.get("datetimes")
        or (
            isinstance(job.get("rango"), dict)
            and job["rango"].get("inicio")
            and job["rango"].get("fin")
        )
    ):
        raise ValueError(
            "Debe definirse 'datetime', 'datetimes' o 'rango' con 'inicio' y 'fin'."
        )


def _salidas_deseadas(job: Dict) -> Set[str]:
    """Normaliza la lista de salidas a un set en mayúsculas."""
    salidas = job.get("salidas", [OutputType.PNG.value])
    return {str(s).upper() for s in salidas}


def _select_geotiff_products(geotiff_conf: Dict, productos: List[str]) -> Set[str]:
    """Determina qué productos se deben exportar a GeoTIFF según la config.

    - Si geotiff_conf['productos'] existe: usar ese conjunto
    - Si geotiff_conf['producto'] existe: usar ese único
    - Si no hay configuración y hay un solo producto en 'productos': usar ese
    - Si nada aplica: set vacío
    """
    productos_gt: Set[str] = set()
    if not geotiff_conf:
        return productos_gt
    productos_gt_cfg = geotiff_conf.get("productos")
    producto_gt_cfg = geotiff_conf.get("producto")
    if productos_gt_cfg:
        productos_gt = set(productos_gt_cfg)
    elif producto_gt_cfg:
        productos_gt = {str(producto_gt_cfg)}
    elif len(productos) == 1:
        productos_gt = {productos[0]}
    return productos_gt


def _prepare_image(
    dt: datetime,
    defaults: Dict,
    job: Dict,
    recorte_conf: Optional[Tuple[float, float, float, float]],
) -> Tuple[
    object,
    object,
    np.ndarray,
    np.ndarray,
    Tuple[float, float, float, float],
    int,
    int,
    int,
    int,
    Optional[Tuple[int, int, int, int]],
]:
    """Construye la imagen y devuelve parámetros de proyección y recorte."""
    img = build_image(dt, defaults, job)
    img.download()
    img.open()
    crs, x, y = img.get_projection_params()

    if recorte_conf:
        latN, latS, lonW, lonE = recorte_conf
        f0, f1, c0, c1 = img.get_bbox_indices(latN, latS, lonW, lonE)
        rec_tuple = (f0, f1, c0, c1)
        extent = (x[c0], x[c1], y[f1], y[f0])
    else:
        rec_tuple = None
        extent = (x[0], x[-1], y[-1], y[0])
        f0, f1, c0, c1 = 0, len(y) - 1, 0, len(x) - 1

    return img, crs, x, y, extent, f0, f1, c0, c1, rec_tuple


def _generate_png(
    rgb: np.ndarray,
    extent: Tuple[float, float, float, float],
    crs,
    shp: Optional[str],
    png_path: Path,
    titulo: str,
    png_conf: Dict,
    generated_files: List[str],
) -> None:
    plot_rgb_with_coastlines(
        rgb,
        extent=extent,
        crs_geo=crs,
        title=titulo,
        provincias_shp=shp,
        show=png_conf.get("show", False),
        lon_interval=10,
        lat_interval=10,
        save_path=str(png_path),
        save=True,
    )
    generated_files.append(str(png_path))


def _export_componentes_rgb(
    nombre: str,
    rgb: np.ndarray,
    extent: Tuple[float, float, float, float],
    crs,
    shp: Optional[str],
    ts: str,
    comp_conf: Dict,
    productos: List[str],
) -> None:
    ccfg = comp_conf
    productos_cc = ccfg.get("productos")
    producto_c = ccfg.get("producto")
    exportar_comp = (
        (productos_cc is not None and nombre in productos_cc)
        or (producto_c is not None and nombre == producto_c)
        or (productos_cc is None and producto_c is None and len(productos) == 1)
    )
    if not exportar_comp:
        return
    comp_out = Path(ccfg.get("out_dir", "componentes"))
    comp_out.mkdir(parents=True, exist_ok=True)
    pattern = ccfg.get("filename_pattern", "{producto}_{ts}_{canal}.png")

    # cmap global o por canal
    cmap_cfg = ccfg.get("cmap", "gray")
    cmaps = (
        cmap_cfg
        if isinstance(cmap_cfg, dict)
        else {"R": cmap_cfg, "G": cmap_cfg, "B": cmap_cfg}
    )

    canales = {"R": rgb[..., 0], "G": rgb[..., 1], "B": rgb[..., 2]}
    for canal, data in canales.items():
        # asegurar [0,1]
        if np.issubdtype(data.dtype, np.floating):
            band = np.clip(data, 0, 1)
        else:
            band = np.clip(data.astype(np.float32) / 255.0, 0, 1)
        fname = (
            pattern.replace("{producto}", nombre)
            .replace("{ts}", ts)
            .replace("{canal}", canal)
        )
        out_path = comp_out / fname
        plot_band_with_coastlines(
            band,
            extent=extent,
            crs_geo=crs,
            title=f"{nombre} {canal} {ts}",
            provincias_shp=shp,
            show=False,
            save=True,
            cmap=cmaps.get(canal, "gray"),
            save_path=str(out_path),
        )


def _export_geotiff_single(
    nombre: str,
    rgb: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    f0: int,
    f1: int,
    c0: int,
    c1: int,
    crs,
    geotiff_conf: Dict,
    out_dir: Path,
    ts: str,
    generated_files: List[str],
) -> None:
    pattern = geotiff_conf.get("filename_pattern", "{producto}_{ts}.tif")
    tif_name = _format_filename(pattern, nombre, ts)
    tiff_path = out_dir / tif_name
    save_rgb_geotiff(rgb, x, y, f0, f1, c0, c1, crs, str(tiff_path))
    logger.info("GeoTIFF generado: %s", tiff_path)
    generated_files.append(str(tiff_path))


def _ensure_frame_png(
    rgb: np.ndarray,
    extent: Tuple[float, float, float, float],
    crs,
    shp: Optional[str],
    png_path: Path,
) -> None:
    plot_rgb_with_coastlines(
        rgb,
        extent=extent,
        crs_geo=crs,
        title="",
        provincias_shp=shp,
        show=False,
        save_path=str(png_path),
        save=True,
    )


def _process_datetime(
    dt: datetime,
    job: Dict,
    defaults: Dict,
    productos: List[str],
    recorte_conf: Optional[Tuple[float, float, float, float]],
    salidas_deseadas: Set[str],
    png_conf: Dict,
    gif_conf: Dict,
    video_conf: Dict,
    geotiff_conf: Dict,
    comp_conf: Dict,
    frames_por_producto: Dict[str, List[str]],
    nombre_job: str,
) -> List[str]:
    """Procesa un timestamp y devuelve archivos generados en esa iteración."""
    generated_files: List[str] = []

    img, crs, x, y, extent, f0, f1, c0, c1, rec_tuple = _prepare_image(
        dt, defaults, job, recorte_conf
    )
    recipes = {p: RECIPE_REGISTRY[p]() for p in productos}
    processor = RGBProcessor(img, recipes, recorte=rec_tuple)
    processor.generate_all()

    out_dir = Path(png_conf.get("out_dir", "salidas"))
    out_dir.mkdir(parents=True, exist_ok=True)
    shp = png_conf.get("shapefile_provincias")

    productos_gt = _select_geotiff_products(geotiff_conf, productos)
    ts = _format_ts(dt)

    for nombre in productos:
        rgb = processor.get_product(nombre)
        titulo = f"{job.get('nombre', nombre)} {nombre} {ts}"
        png_path = out_dir / f"{nombre_job}_{nombre}_{ts}.png"

        # PNG
        if OutputType.PNG.value in salidas_deseadas:
            _generate_png(
                rgb, extent, crs, shp, png_path, titulo, png_conf, generated_files
            )

        # Componentes RGB
        if OutputType.COMPONENTES_RGB.value in salidas_deseadas and comp_conf:
            _export_componentes_rgb(
                nombre, rgb, extent, crs, shp, ts, comp_conf, productos
            )

        # GeoTIFF por producto seleccionado
        if (
            OutputType.GEOTIFF.value in salidas_deseadas
            and geotiff_conf
            and nombre in productos_gt
        ):
            gt_out = Path(geotiff_conf.get("out_dir", out_dir))
            gt_out.mkdir(parents=True, exist_ok=True)
            _export_geotiff_single(
                nombre,
                rgb,
                x,
                y,
                f0,
                f1,
                c0,
                c1,
                crs,
                geotiff_conf,
                gt_out,
                ts,
                generated_files,
            )

        # Frames para GIF/VIDEO
        necesita_anim = (
            OutputType.GIF.value in salidas_deseadas
            and gif_conf
            and nombre == gif_conf.get("producto")
        ) or (
            OutputType.VIDEO.value in salidas_deseadas
            and video_conf
            and nombre == video_conf.get("producto")
        )
        if necesita_anim:
            if OutputType.PNG.value not in salidas_deseadas:
                _ensure_frame_png(rgb, extent, crs, shp, png_path)
            frames_por_producto.setdefault(nombre, []).append(str(png_path))

    return generated_files


def _generate_gif_from_frames(
    gif_conf: Dict, frames_por_producto: Dict[str, List[str]]
) -> None:
    producto_gif = gif_conf.get("producto")
    gif_frames = frames_por_producto.get(producto_gif, [])
    if not gif_frames:
        return
    loop = gif_conf.get("loop", 0)
    frame_seconds = gif_conf.get("frame_seconds")
    if frame_seconds is None:
        fps = float(gif_conf.get("fps", 1))
        fps = max(fps, 0.01)
        frame_seconds = 1.0 / fps
    gif_out_dir = Path(gif_conf.get("out_dir", "gifs"))
    gif_out_dir.mkdir(parents=True, exist_ok=True)
    filename = gif_conf.get("filename", f"{producto_gif}.gif")
    gif_path = gif_out_dir / filename

    with imageio.get_writer(
        gif_path, mode="I", loop=loop, duration=frame_seconds
    ) as writer:
        for fp in gif_frames:
            frame = imageio.imread(fp)
            writer.append_data(_normalize_rgb_frame(frame))
    logger.info(
        "GIF generado: %s frames=%d delay=%ss loop=%s",
        gif_path,
        len(gif_frames),
        frame_seconds,
        loop,
    )


def _generate_video_from_frames(
    video_conf: Dict, frames_por_producto: Dict[str, List[str]]
) -> None:
    producto_vid = video_conf.get("producto")
    vid_frames = frames_por_producto.get(producto_vid, [])
    if not vid_frames:
        return
    frame_seconds = video_conf.get("frame_seconds")
    if frame_seconds is not None:
        fps = 1.0 / float(frame_seconds)
    else:
        fps = float(video_conf.get("fps", 1))
    fps = max(fps, 0.01)

    codec = video_conf.get("codec", "libx264")
    pix_fmt = video_conf.get("pix_fmt", "yuv420p")
    crf = str(video_conf.get("crf", 23))
    preset = video_conf.get("preset", "medium")

    vid_out_dir = Path(video_conf.get("out_dir", "videos"))
    vid_out_dir.mkdir(parents=True, exist_ok=True)
    filename = video_conf.get("filename", f"{producto_vid}.mp4")
    video_path = vid_out_dir / filename

    frames: List[np.ndarray] = []
    for fp in vid_frames:
        fr = imageio.imread(fp)
        frames.append(_normalize_rgb_frame(fr))
    frames = _pad_frames_to_even_16(frames)

    with imageio.get_writer(
        video_path,
        format="ffmpeg",
        fps=fps,
        codec=codec,
        pixelformat=pix_fmt,
        ffmpeg_params=["-crf", crf, "-preset", preset],
    ) as writer:
        for fr in frames:
            writer.append_data(fr)
    logger.info("MP4 generado: %s frames=%d fps=%s", video_path, len(frames), fps)


def build_image(dt: datetime, defaults: Dict, job: Dict):
    """Construye la instancia de imagen según el modo solicitado."""
    modo = job.get("tipo_imagen", defaults.get("tipo_imagen", "MCMI")).upper()
    # NOTE: The default satellite has been changed from "GOES19" to "GOES16".
    # This change may affect existing configurations that relied on the previous default.
    # Please update your configuration if you require a different satellite.
    # Justification: GOES16 is now the recommended/available default for this workflow.
    satelite = job.get("satelite", defaults.get("satelite", "GOES16")).upper()
    data_dir = job.get("data_dir", defaults.get("data_dir", "data"))
    channels = job.get("canales", defaults.get("canales", None))
    if modo == "MCMI":
        return ABIImageMCMI(
            dt, satellite=f"noaa-{satelite.lower()}", local_dir=data_dir
        )
    if modo == "L1B":
        # Ensure ABIImageL1b implementation properly handles the channels parameter
        return ABIImageL1b(dt, "ABI-L1b-RadF", channels=channels, local_dir=data_dir)
    raise ValueError(f"tipo_imagen desconocido: {modo}")


def run_job(job: Dict, defaults: Dict) -> List[str]:
    """Ejecuta un job de procesamiento en base a la configuración provista."""
    _validate_job(job, defaults)

    productos: List[str] = list(job["productos"])  # tipo explícito
    recorte_conf = job.get("recorte", defaults.get("recorte"))
    generated_files: List[str] = []

    # 1) Salidas deseadas
    salidas_deseadas = _salidas_deseadas(job)

    # 2) Configuraciones por salida (merge defaults <- job)
    png_conf = {**defaults.get("png_conf", {}), **job.get("png_conf", {})}
    gif_conf = {**defaults.get("gif_conf", {}), **job.get("gif_conf", {})}
    video_conf = {**defaults.get("video_conf", {}), **job.get("video_conf", {})}
    geotiff_conf = {**defaults.get("geotiff_conf", {}), **job.get("geotiff_conf", {})}
    comp_conf = {
        **defaults.get("componentes_rgb_conf", {}),
        **job.get("componentes_rgb_conf", {}),
    }

    # Frames acumulados por producto para GIF/VIDEO
    frames_por_producto: Dict[str, List[str]] = {}
    nombre_job = job.get("nombre", "job")

    for dt in expand_datetimes(job):
        try:
            gen = _process_datetime(
                dt,
                job,
                defaults,
                productos,
                recorte_conf,
                salidas_deseadas,
                png_conf,
                gif_conf,
                video_conf,
                geotiff_conf,
                comp_conf,
                frames_por_producto,
                nombre_job,
            )
            generated_files.extend(gen)
        except Exception as exc:
            logger.exception(
                "Error procesando dt=%s para job=%s: %s", dt, nombre_job, exc
            )
            continue

    if OutputType.GIF.value in salidas_deseadas and gif_conf:
        _generate_gif_from_frames(gif_conf, frames_por_producto)

    if OutputType.VIDEO.value in salidas_deseadas and video_conf:
        _generate_video_from_frames(video_conf, frames_por_producto)

    return generated_files


def run_from_config(ruta: Path | str) -> List[str]:
    """Ejecuta todos los jobs definidos en un archivo YAML de configuración."""
    cfg = load_config(ruta)
    total_generated_files: List[str] = []
    defaults = cfg.get("defaults", {})
    for job in cfg.get("jobs", []):
        generated_files = run_job(job, defaults)
        total_generated_files.extend(generated_files)
    return total_generated_files
