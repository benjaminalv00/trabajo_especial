from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import tempfile
import threading
from pathlib import Path
from typing import AsyncGenerator, Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator

from config_runner import run_from_config

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _ensure_directories() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)


_ensure_directories()

app = FastAPI(title="GOES RGB Configurator", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
async def root() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="No se encontró la aplicación web.")
    return FileResponse(index_path)


class SavePayload(BaseModel):
    name: str
    content: str

    @validator("name")
    def validate_name(cls, value: str) -> str:
        if not re.match(r"^[\w\-.]+\.(ya?ml)$", value, flags=re.IGNORECASE):
            raise ValueError(
                "El nombre debe terminar en .yml o .yaml y usar solo letras, números, guiones o puntos."
            )
        resolved = (CONFIG_DIR / value).resolve()
        if not str(resolved).startswith(str(CONFIG_DIR.resolve())):
            raise ValueError("Nombre de archivo inválido.")
        return value


class RunPayload(BaseModel):
    content: str
    name: Optional[str] = None
    save: bool = False

    @validator("name")
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        SavePayload(name=value, content="dummy")  # reutiliza la validación
        return value


@app.get("/api/configs")
def list_configs() -> dict:
    configs = sorted(
        {path.name for path in CONFIG_DIR.glob("*.yml")}
        | {path.name for path in CONFIG_DIR.glob("*.yaml")}
    )
    return {"configs": configs}


def _resolve_config_path(name: str) -> Path:
    candidate = (CONFIG_DIR / name).resolve()
    config_root = CONFIG_DIR.resolve()
    if not str(candidate).startswith(str(config_root)) or not candidate.exists():
        raise HTTPException(
            status_code=404, detail="Archivo de configuración no encontrado."
        )
    return candidate


@app.get("/api/configs/{name}")
def load_config_file(name: str) -> dict:
    path = _resolve_config_path(name)
    return {"name": path.name, "content": path.read_text(encoding="utf-8")}


def _validate_yaml(content: str) -> None:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"YAML inválido: {exc}") from exc
    if not isinstance(data, dict) or "jobs" not in data:
        raise HTTPException(
            status_code=400,
            detail="La configuración debe contener al menos la clave 'jobs'.",
        )


@app.post("/api/save")
def save_config(payload: SavePayload) -> dict:
    _validate_yaml(payload.content)
    path = (CONFIG_DIR / payload.name).resolve()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.content, encoding="utf-8")
    return {"status": "ok", "message": f"Configuración guardada en {path.name}"}


async def _stream_run_config(path: Path) -> AsyncGenerator[str, None]:
    queue: "asyncio.Queue[Optional[str]]" = asyncio.Queue()
    loop = asyncio.get_running_loop()

    async def runner() -> None:
        def _blocking() -> None:
            stdout_fd = sys.stdout.fileno()
            stderr_fd = sys.stderr.fileno()
            stdout_backup = os.dup(stdout_fd)
            stderr_backup = os.dup(stderr_fd)
            pipe_r, pipe_w = os.pipe()

            def forward() -> None:
                with os.fdopen(pipe_r, "rb", closefd=True) as reader:
                    while True:
                        chunk = reader.read(4096)
                        if not chunk:
                            break
                        decoded = chunk.decode("utf-8", errors="replace")
                        loop.call_soon_threadsafe(queue.put_nowait, decoded)
                loop.call_soon_threadsafe(queue.put_nowait, None)

            reader_thread = threading.Thread(target=forward, daemon=True)
            reader_thread.start()

            try:
                os.dup2(pipe_w, stdout_fd)
                os.dup2(pipe_w, stderr_fd)
                os.close(pipe_w)
                logging.captureWarnings(True)
                run_from_config(str(path))
            except Exception as exc:  # pylint: disable=broad-except
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

        await asyncio.to_thread(_blocking)

    task = asyncio.create_task(runner())

    try:
        yield f"== Ejecutando {path.name} ==\n"
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk
    finally:
        await task


@app.post("/api/run")
async def run_config(payload: RunPayload) -> dict:
    _validate_yaml(payload.content)

    temp_path: Optional[Path] = None
    result_path: Path

    if payload.save and payload.name:
        save_config(SavePayload(name=payload.name, content=payload.content))
        result_path = (CONFIG_DIR / payload.name).resolve()
    else:
        suffix = "_frontend.yml"
        if payload.name and payload.name.endswith((".yml", ".yaml")):
            suffix = f"_{payload.name}"
        tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115 close immediately
            mode="w",
            encoding="utf-8",
            suffix=suffix,
            prefix="webcfg_",
            dir=CONFIG_DIR,
            delete=False,
        )
        with tmp:
            tmp.write(payload.content)
        temp_path = Path(tmp.name)
        result_path = temp_path

    try:
        chunks = []
        async for chunk in _stream_run_config(result_path):
            chunks.append(chunk)
        logs = "".join(chunks)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(
            status_code=500, detail=f"Error al ejecutar la configuración: {exc}"
        ) from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)

    response = {"status": "ok", "logs": logs}
    if payload.save and payload.name:
        response["saved_as"] = payload.name
    return response


@app.post("/api/run-stream")
async def run_config_stream(payload: RunPayload) -> StreamingResponse:
    _validate_yaml(payload.content)

    temp_path: Optional[Path] = None
    result_path: Path

    if payload.save and payload.name:
        save_config(SavePayload(name=payload.name, content=payload.content))
        result_path = (CONFIG_DIR / payload.name).resolve()
    else:
        suffix = "_frontend.yml"
        if payload.name and payload.name.endswith((".yml", ".yaml")):
            suffix = f"_{payload.name}"
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=suffix,
            prefix="webcfg_",
            dir=CONFIG_DIR,
            delete=False,
        )
        with tmp:
            tmp.write(payload.content)
        temp_path = Path(tmp.name)
        result_path = temp_path

    async def streamer() -> AsyncGenerator[bytes, None]:
        try:
            async for chunk in _stream_run_config(result_path):
                yield chunk.encode("utf-8")
            if payload.save and payload.name:
                yield f"\n== Configuración guardada como {payload.name} ==\n".encode(
                    "utf-8"
                )
            yield b"\n== Proceso finalizado ==\n"
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")
