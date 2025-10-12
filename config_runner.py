import yaml
from pathlib import Path
from datetime import datetime, timedelta
from goes_rgb.l2_abi_image import ABIImageMCMI
from goes_rgb.l1b_abi_image import ABIImageL1b
from goes_rgb.rgb_processor import RGBProcessor
from goes_rgb.visualization import plot_rgb_with_coastlines, plot_band_with_coastlines

from goes_rgb.recipes_registry import RECIPE_REGISTRY
import imageio.v2 as imageio
import numpy as np
import math
from goes_rgb.helpers import save_rgb_geotiff  # NUEVO


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
    satelite = job.get("satelite", defaults.get("satelite", "GOES16")).upper()
    data_dir = job.get("data_dir", defaults.get("data_dir", "data"))
    if modo == "MCMI":
        return ABIImageMCMI(
            dt, satellite=f"noaa-{satelite.lower()}", local_dir=data_dir
        )
    if modo == "L1B":
        # aca queda laburo por hacer para L1B
        return ABIImageL1b(dt, "ABI-L1b-RadF", local_dir=data_dir)
    raise ValueError(f"tipo_imagen desconocido: {modo}")


def run_job(job, defaults):
    productos = job["productos"]
    recorte_conf = job.get("recorte", defaults.get("recorte"))

    # 1. Leer la lista explícita de salidas deseadas
    salidas_deseadas = {
        s.upper() for s in job.get("salidas", ["PNG"])
    }  # PNG por defecto

    # 2. Cargar configuraciones específicas por tipo de salida
    # Se fusionan los defaults con la configuración del job
    export_conf = {**defaults.get("png_conf", {}), **job.get("png_conf", {})}
    gif_conf = {**defaults.get("gif_conf", {}), **job.get("gif_conf", {})}
    video_conf = {**defaults.get("video_conf", {}), **job.get("video_conf", {})}
    geotiff_conf = {**defaults.get("geotiff_conf", {}), **job.get("geotiff_conf", {})}
    comp_conf = {
        **defaults.get("componentes_rgb_conf", {}),
        **job.get("componentes_rgb_conf", {}),
    }
    # Mapear producto -> lista de rutas PNG
    frames_por_producto = {}
    nombre_job = job.get("nombre", "job")

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
            # Índices del frame completo (para GeoTIFF)
            f0, f1, c0, c1 = 0, len(y) - 1, 0, len(x) - 1

        recipes = {p: RECIPE_REGISTRY[p]() for p in productos}
        processor = RGBProcessor(img, recipes, recorte=rec_tuple)
        processor.generate_all()

        out_dir = Path(export_conf.get("out_dir", "salidas"))
        out_dir.mkdir(parents=True, exist_ok=True)
        shp = export_conf.get("shapefile_provincias")

        for nombre in productos:
            rgb = processor.get_product(nombre)
            titulo = f"{job.get('nombre', nombre)} {nombre} {dt:%Y%m%d_%H%M}"
            png_path = out_dir / f"{nombre_job}_{nombre}_{dt:%Y%m%d_%H%M}.png"

            # 3. Generar PNG solo si está en las salidas deseadas
            if "PNG" in salidas_deseadas:
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

            # Exportar componentes R/G/B si está configurado
            # 4. Comprobar si se deben exportar componentes

            if "COMPONENTES_RGB" in salidas_deseadas and comp_conf:
                ccfg = comp_conf
                productos_cc = ccfg.get("productos")
                producto_c = ccfg.get("producto")
                exportar_comp = (
                    (productos_cc is not None and nombre in productos_cc)
                    or (producto_c is not None and nombre == producto_c)
                    or (
                        productos_cc is None
                        and producto_c is None
                        and len(productos) == 1
                    )
                )
                if exportar_comp:
                    comp_out = Path(ccfg.get("out_dir", "componentes"))
                    comp_out.mkdir(parents=True, exist_ok=True)
                    ts = dt.strftime("%Y%m%d_%H%M")
                    pattern = ccfg.get(
                        "filename_pattern", "{producto}_{ts}_{canal}.png"
                    )

                    # Soporte de cmap global o por canal
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

            # GeoTIFF (uno por fecha). Elegí producto con geotiff.producto o geotiff.productos
            # 5. Comprobar si se debe exportar GeoTIFF
            if "GEOTIFF" in salidas_deseadas and geotiff_conf:
                gt_cfg = geotiff_conf
                productos_gt = gt_cfg.get("productos")
                producto_gt = gt_cfg.get("producto")
                exportar_gt = (
                    (productos_gt is not None and nombre in productos_gt)
                    or (producto_gt is not None and nombre == producto_gt)
                    or (
                        productos_gt is None
                        and producto_gt is None
                        and len(productos) == 1
                    )
                )
                if exportar_gt:
                    gt_out = Path(gt_cfg.get("out_dir", out_dir))
                    gt_out.mkdir(parents=True, exist_ok=True)
                    ts = dt.strftime("%Y%m%d_%H%M")
                    pattern = gt_cfg.get("filename_pattern")
                    if pattern:
                        tif_name = pattern.replace("{producto}", nombre).replace(
                            "{ts}", ts
                        )
                    else:
                        tif_name = gt_cfg.get("filename", f"{nombre}_{ts}.tif")
                    tiff_path = gt_out / tif_name
                    # Guardar GeoTIFF usando helper existente
                    save_rgb_geotiff(rgb, x, y, f0, f1, c0, c1, crs, str(tiff_path))
                    print(f"GeoTIFF generado: {tiff_path}")

            # Acumular frames para GIF/Video del producto elegido
            # Esto se hace si PNG, GIF o VIDEO están en las salidas, ya que ambos dependen de los frames PNG
            if (
                "GIF" in salidas_deseadas
                and gif_conf
                and nombre == gif_conf.get("producto")
            ) or (
                "VIDEO" in salidas_deseadas
                and video_conf
                and nombre == video_conf.get("producto")
            ):
                # Si los PNG no se guardan, necesitamos una ruta temporal o manejar los frames en memoria.
                # Por ahora, asumimos que si se quiere GIF/Video, los PNG se generan.
                # Una mejora sería generar los PNG en una carpeta temporal si no se piden explícitamente.
                if "PNG" not in salidas_deseadas:
                    plot_rgb_with_coastlines(
                        rgb,
                        extent=extent,
                        crs_geo=crs,
                        title=titulo,
                        provincias_shp=shp,
                        show=False,
                        save_path=str(png_path),
                        save=True,
                    )

                frames_por_producto.setdefault(nombre, []).append(str(png_path))

    # Generar GIF si corresponde
    if "GIF" in salidas_deseadas and gif_conf:
        producto_gif = gif_conf.get("producto")
        gif_frames = frames_por_producto.get(producto_gif, [])
        if gif_frames:
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
                    # Normalizar a RGB uint8
                    if frame.ndim == 2:
                        frame = np.stack([frame] * 3, axis=-1)
                    if frame.shape[-1] == 4:
                        frame = frame[..., :3]
                    if frame.dtype != np.uint8:
                        frame = np.clip(frame, 0, 255).astype(np.uint8)
                    writer.append_data(frame)
            print(
                f"GIF generado: {gif_path} frames={len(gif_frames)} delay={frame_seconds}s loop={loop}"
            )

    # Generar MP4 si corresponde
    if "VIDEO" in salidas_deseadas and video_conf:
        producto_vid = video_conf.get("producto")
        vid_frames = frames_por_producto.get(producto_vid, [])
        if vid_frames:
            # fps desde frame_seconds si está definido
            frame_seconds = video_conf.get("frame_seconds")
            if frame_seconds is not None:
                fps = 1.0 / float(frame_seconds)
            else:
                fps = float(video_conf.get("fps", 1))
            fps = max(fps, 0.01)  # evitar -r 0.00

            codec = video_conf.get("codec", "libx264")
            pix_fmt = video_conf.get("pix_fmt", "yuv420p")
            crf = str(video_conf.get("crf", 23))
            preset = video_conf.get("preset", "medium")

            vid_out_dir = Path(video_conf.get("out_dir", "videos"))
            vid_out_dir.mkdir(parents=True, exist_ok=True)
            filename = video_conf.get("filename", f"{producto_vid}.mp4")
            video_path = vid_out_dir / filename

            norm = []
            max_h = max_w = 0
            for fp in vid_frames:
                fr = imageio.imread(fp)
                if fr.ndim == 2:
                    fr = np.stack([fr] * 3, axis=-1)
                if fr.shape[-1] == 4:
                    fr = fr[..., :3]
                if fr.dtype != np.uint8:
                    fr = np.clip(fr, 0, 255).astype(np.uint8)
                h, w = fr.shape[:2]
                max_h = max(max_h, h)
                max_w = max(max_w, w)
                norm.append(fr)
            # Target múltiplo de 16 y par (yuv420p)
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
            print(f"MP4 generado: {video_path} frames=8 fps={fps}")


def run_from_config(ruta):
    cfg = load_config(ruta)
    defaults = cfg.get("defaults", {})
    for job in cfg.get("jobs", []):
        run_job(job, defaults)
