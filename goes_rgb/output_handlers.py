"""
Handlers de salida para el pipeline de procesamiento GOES RGB.

Cada tipo de salida (PNG, COMPONENTES_RGB, GEOTIFF, GIF, VIDEO) se modela
como un handler resuelto por nombre desde un registry, replicando el mismo
patron Strategy + Registry que goes_rgb.recipes_registry usa para las
recetas RGB. Hay dos familias de handlers segun su ciclo de vida dentro de
config_runner.run_job:

- FrameOutputHandler: se resuelven una vez por cada par (fecha, producto),
  dentro del loop principal (PNG, COMPONENTES_RGB, GEOTIFF).
- AccumulatorOutputHandler: acumulan un frame por cada fecha durante el
  loop, y generan su salida final una unica vez despues de que el loop
  termina (GIF, VIDEO), porque combinan frames de multiples fechas.

Las importaciones de librerias externas (plot_rgb_with_coastlines,
save_band_geotiff, save_rgb_geotiff, reproject_geotiff, imageio) se
mantienen dentro de cada metodo, no al tope del modulo: la suite de tests
de config_runner las reemplaza en tiempo de ejecucion via
`monkeypatch.setitem(sys.modules, ...)` y `monkeypatch.setattr` sobre el
modulo real, lo cual requiere que el import se re-ejecute en cada llamada
en vez de resolverse una unica vez al cargar este modulo.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import math
import numpy as np


@dataclass
class FrameContext:
    """Datos de un (fecha, producto) ya generado, listos para exportar."""

    rgb: Any
    nombre: str
    dt: Any
    extent: tuple
    crs: Any
    x: Any
    y: Any
    f0: int
    f1: int
    c0: int
    c1: int
    productos: list
    out_dir: Path
    shp: str
    titulo: str
    png_path: Path


def _normalize_frame(frame):
    """Normaliza un frame leido de disco a RGB uint8 (usado por GIF y VIDEO)."""
    if frame.ndim == 2:
        frame = np.stack([frame] * 3, axis=-1)
    if frame.shape[-1] == 4:
        frame = frame[..., :3]
    if frame.dtype != np.uint8:
        frame = np.clip(frame, 0, 255).astype(np.uint8)
    return frame


class FrameOutputHandler(ABC):
    """Salida resuelta una vez por cada (fecha, producto)."""

    nombre: str

    def activo(self, salidas_deseadas: set, conf: dict) -> bool:
        return self.nombre in salidas_deseadas and bool(conf)

    @abstractmethod
    def exportar(self, ctx: FrameContext, conf: dict) -> list:
        """Genera la salida para un frame y devuelve las rutas creadas."""


class PngOutputHandler(FrameOutputHandler):
    nombre = "PNG"

    def activo(self, salidas_deseadas, conf):
        # A diferencia del resto de las salidas, PNG se genera aunque no
        # haya png_conf definido: asi era el comportamiento original.
        return self.nombre in salidas_deseadas

    def exportar(self, ctx, conf):
        from goes_rgb.visualization import plot_rgb_with_coastlines

        plot_rgb_with_coastlines(
            ctx.rgb,
            extent=ctx.extent,
            crs_geo=ctx.crs,
            title=ctx.titulo,
            provincias_shp=ctx.shp,
            show=conf.get("show", False),
            lon_interval=10,
            lat_interval=10,
            save_path=str(ctx.png_path),
            save=True,
        )
        return [str(ctx.png_path)]


class ComponentesRgbOutputHandler(FrameOutputHandler):
    nombre = "COMPONENTES_RGB"

    def exportar(self, ctx, conf):
        from goes_rgb.helpers import save_band_geotiff

        productos_cc = conf.get("productos")
        producto_c = conf.get("producto")
        exportar_comp = (
            (productos_cc is not None and ctx.nombre in productos_cc)
            or (producto_c is not None and ctx.nombre == producto_c)
            or (productos_cc is None and producto_c is None and len(ctx.productos) == 1)
        )
        if not exportar_comp:
            return []

        comp_out = Path(conf.get("out_dir", "componentes"))
        comp_out.mkdir(parents=True, exist_ok=True)
        ts = ctx.dt.strftime("%Y%m%d_%H%M")
        pattern = conf.get("filename_pattern", "{producto}_{ts}_{canal}.png")

        generados = []
        canales = {"R": ctx.rgb[..., 0], "G": ctx.rgb[..., 1], "B": ctx.rgb[..., 2]}
        for canal, data in canales.items():
            fname = (
                pattern.replace("{producto}", ctx.nombre)
                .replace("{ts}", ts)
                .replace("{canal}", canal)
            )
            out_path = comp_out / fname
            save_band_geotiff(
                data,
                ctx.x,
                ctx.y,
                ctx.f0,
                ctx.f1,
                ctx.c0,
                ctx.c1,
                ctx.crs,
                str(out_path),
            )
            print(f"Componente GeoTIFF generado: {out_path}")
            generados.append(str(out_path))
        return generados


class GeoTiffOutputHandler(FrameOutputHandler):
    nombre = "GEOTIFF"

    def exportar(self, ctx, conf):
        from goes_rgb.helpers import save_rgb_geotiff
        from scripts.GeoTIFF_translate_coord_output import reproject_geotiff

        productos_gt = conf.get("productos")
        producto_gt = conf.get("producto")
        lista_gt = None
        if productos_gt:
            lista_gt = list(productos_gt)
        elif producto_gt:
            lista_gt = [producto_gt]
        elif len(ctx.productos) == 1:
            lista_gt = [ctx.productos[0]]

        if not lista_gt:
            return []

        gt_out = Path(conf.get("out_dir", ctx.out_dir))
        gt_out.mkdir(parents=True, exist_ok=True)
        ts = ctx.dt.strftime("%Y%m%d_%H%M")
        pattern = conf.get("filename_pattern", "{producto}_{ts}.tif")

        generados = []
        for nombre_gt in lista_gt:
            if nombre_gt != ctx.nombre:
                continue
            tif_name = pattern.replace("{producto}", nombre_gt).replace("{ts}", ts)
            tiff_path = gt_out / tif_name
            save_rgb_geotiff(
                ctx.rgb,
                ctx.x,
                ctx.y,
                ctx.f0,
                ctx.f1,
                ctx.c0,
                ctx.c1,
                ctx.crs,
                str(tiff_path),
            )
            print(f"GeoTIFF generado: {tiff_path}")
            generados.append(str(tiff_path))

            reproyecciones = conf.get("reproyecciones", [])
            if reproyecciones:
                for reproj_conf in reproyecciones:
                    epsg = reproj_conf.get("epsg")
                    suffix = reproj_conf.get("suffix", "")
                    if epsg:
                        reproj_name = tif_name.replace(".tif", f"{suffix}.tif")
                        reproj_path = gt_out / reproj_name
                        try:
                            reproject_geotiff(str(tiff_path), str(reproj_path), epsg)
                            print(f"GeoTIFF reproyectado: {reproj_path}")
                            generados.append(str(reproj_path))
                        except Exception as e:
                            print(f"Error al reproyectar a {epsg}: {e}")
        return generados


class AccumulatorOutputHandler(ABC):
    """Salida que acumula un frame por fecha y se genera una unica vez al final."""

    nombre: str

    def frame_deseado(self, nombre_producto: str, conf: dict) -> bool:
        return nombre_producto == conf.get("producto")

    @abstractmethod
    def finalizar(self, frames: list, conf: dict) -> list:
        """Genera la salida final a partir de los frames acumulados."""


class GifOutputHandler(AccumulatorOutputHandler):
    nombre = "GIF"

    def finalizar(self, frames, conf):
        if not frames:
            return []

        import imageio.v2 as imageio

        producto_gif = conf.get("producto")
        loop = conf.get("loop", 0)
        frame_seconds = conf.get("frame_seconds")
        if frame_seconds is None:
            fps = float(conf.get("fps", 1))
            fps = max(fps, 0.01)
            frame_seconds = 1.0 / fps
        gif_out_dir = Path(conf.get("out_dir", "gifs"))
        gif_out_dir.mkdir(parents=True, exist_ok=True)
        filename = conf.get("filename", f"{producto_gif}.gif")
        gif_path = gif_out_dir / filename

        with imageio.get_writer(
            gif_path, mode="I", loop=loop, duration=frame_seconds
        ) as writer:
            for fp in frames:
                frame = imageio.imread(fp)
                frame = _normalize_frame(frame)
                writer.append_data(frame)
        print(
            f"GIF generado: {gif_path} frames={len(frames)} delay={frame_seconds}s loop={loop}"
        )
        return [str(gif_path)]


class VideoOutputHandler(AccumulatorOutputHandler):
    nombre = "VIDEO"

    def finalizar(self, frames, conf):
        if not frames:
            return []

        import imageio.v2 as imageio

        producto_vid = conf.get("producto")
        frame_seconds = conf.get("frame_seconds")
        if frame_seconds is not None:
            fps = 1.0 / float(frame_seconds)
        else:
            fps = float(conf.get("fps", 1))
        fps = max(fps, 0.01)  # evitar -r 0.00

        codec = conf.get("codec", "libx264")
        pix_fmt = conf.get("pix_fmt", "yuv420p")
        crf = str(conf.get("crf", 23))
        preset = conf.get("preset", "medium")

        vid_out_dir = Path(conf.get("out_dir", "videos"))
        vid_out_dir.mkdir(parents=True, exist_ok=True)
        filename = conf.get("filename", f"{producto_vid}.mp4")
        video_path = vid_out_dir / filename

        norm = []
        max_h = max_w = 0
        for fp in frames:
            fr = imageio.imread(fp)
            fr = _normalize_frame(fr)
            h, w = fr.shape[:2]
            max_h = max(max_h, h)
            max_w = max(max_w, w)
            norm.append(fr)
        # Target multiplo de 16 y par (yuv420p)
        tgt_h = int(math.ceil(max_h / 16) * 16)
        tgt_w = int(math.ceil(max_w / 16) * 16)
        if tgt_h % 2:
            tgt_h += 1
        if tgt_w % 2:
            tgt_w += 1
        padded = []
        for fr in norm:
            h, w = fr.shape[:2]
            pad_h = tgt_h - h
            pad_w = tgt_w - w
            if pad_h or pad_w:
                fr = np.pad(fr, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
            padded.append(fr)

        with imageio.get_writer(
            video_path,
            format="ffmpeg",
            fps=fps,
            codec=codec,
            pixelformat=pix_fmt,
            ffmpeg_params=["-crf", crf, "-preset", preset],
        ) as writer:
            for fr in padded:
                writer.append_data(fr)
        print(f"MP4 generado: {video_path} frames={len(padded)} fps={fps}")
        return [str(video_path)]


FRAME_OUTPUT_REGISTRY = {
    "PNG": PngOutputHandler(),
    "COMPONENTES_RGB": ComponentesRgbOutputHandler(),
    "GEOTIFF": GeoTiffOutputHandler(),
}

ACCUMULATOR_OUTPUT_REGISTRY = {
    "GIF": GifOutputHandler(),
    "VIDEO": VideoOutputHandler(),
}
