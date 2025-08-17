import yaml
from pathlib import Path
from datetime import datetime, timedelta
from goes_rgb.l2_abi_image import ABIImageMCMI
from goes_rgb.l1b_abi_image import ABIImageL1b
from goes_rgb.rgb_processor import RGBProcessor
from goes_rgb.visualization import plot_rgb_with_coastlines
from goes_rgb.recipes_registry import RECIPE_REGISTRY
import imageio.v2 as imageio
import numpy as np


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def expand_datetimes(job):
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


def build_image(dt, defaults, job):
    modo = job.get("tipo_imagen", defaults.get("tipo_imagen", "MCMI")).upper()
    if modo == "MCMI":
        return ABIImageMCMI(dt)
    if modo == "L1B":
        return ABIImageL1b(dt, "ABI-L1b-RadF")
    raise ValueError(f"tipo_imagen desconocido: {modo}")


def run_job(job, defaults):
    productos = job["productos"]
    recorte_conf = job.get("recorte", defaults.get("recorte"))
    export_conf = {**defaults.get("export", {}), **job.get("export", {})}

    gif_conf = job.get("gif")
    gif_frames = []  # rutas a PNG (o podrías guardar arrays si prefieres)

    for dt in expand_datetimes(job):
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

        recipes = {p: RECIPE_REGISTRY[p]() for p in productos}
        processor = RGBProcessor(img, recipes, recorte=rec_tuple)
        processor.generate_all()

        out_dir = Path(export_conf.get("out_dir", "salidas"))
        out_dir.mkdir(parents=True, exist_ok=True)
        shp = export_conf.get("shapefile_provincias")

        for nombre in productos:
            rgb = processor.get_product(nombre)
            titulo = f"{job.get('nombre', nombre)} {nombre} {dt:%Y%m%d_%H%M}"
            png_path = out_dir / f"{nombre}_{dt:%Y%m%d_%H%M}.png"
            plot_rgb_with_coastlines(
                rgb,
                extent=extent,
                crs_geo=crs,
                title=titulo,
                provincias_shp=shp,
                show=export_conf.get("show", False),
                save_path=str(png_path),
                save=True,
            )
            # Acumular frames para el GIF del producto elegido
            if gif_conf and nombre == gif_conf.get("producto"):
                gif_frames.append(str(png_path))

    # Generar GIF si corresponde
    if gif_conf and gif_frames:
        loop = gif_conf.get("loop", 0)
        # Prioridad: frame_seconds > fps
        frame_seconds = gif_conf.get("frame_seconds")
        if frame_seconds is None:
            fps = gif_conf.get("fps", 1)  # default 1 fps
            frame_seconds = 1.0 / float(fps)
        gif_out_dir = Path(gif_conf.get("out_dir", "gifs"))
        gif_out_dir.mkdir(parents=True, exist_ok=True)
        filename = gif_conf.get("filename", f"{gif_conf['producto']}.gif")
        gif_path = gif_out_dir / filename

        import imageio.v2 as imageio

        # Streaming writer (menos RAM)
        with imageio.get_writer(
            gif_path, mode="I", loop=loop, duration=frame_seconds
        ) as writer:
            for fp in gif_frames:
                frame = imageio.imread(fp)
                writer.append_data(frame)
        print(
            f"GIF generado: {gif_path} frames={len(gif_frames)} delay={frame_seconds}s loop={loop}"
        )


def run_from_config(ruta):
    cfg = load_config(ruta)
    defaults = cfg.get("defaults", {})
    for job in cfg.get("jobs", []):
        run_job(job, defaults)
