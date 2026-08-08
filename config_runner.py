import yaml
from pathlib import Path
from datetime import datetime, timedelta
from goes_rgb.recipes_registry import RECIPE_REGISTRY
from goes_rgb.logging_utils import get_logger


logger = get_logger(__name__)


def load_config(path):
    logger.info("Cargando configuración desde %s", path)
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
    from goes_rgb.l2_abi_image import ABIImageMCMI
    from goes_rgb.l1b_abi_image import ABIImageL1b

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


def run_job(job, defaults):
    import math
    from goes_rgb.rgb_processor import RGBProcessor
    from goes_rgb.visualization import plot_rgb_with_coastlines

    nombre_job = job.get("nombre", "job")
    logger.info("Iniciando job %s", nombre_job)
    productos = job["productos"]
    recorte_conf = job.get("recorte", defaults.get("recorte"))
    generated_files = []

    # 1. Leer la lista explícita de salidas deseadas
    salidas_deseadas = {
        s.upper() for s in job.get("salidas", ["PNG"])
    }  # PNG por defecto

    # 2. Cargar configuraciones específicas por tipo de salida
    # Se fusionan los defaults con la configuración del job
    png_conf = {**defaults.get("png_conf", {}), **job.get("png_conf", {})}
    gif_conf = {**defaults.get("gif_conf", {}), **job.get("gif_conf", {})}
    video_conf = {**defaults.get("video_conf", {}), **job.get("video_conf", {})}
    geotiff_conf = {**defaults.get("geotiff_conf", {}), **job.get("geotiff_conf", {})}
    comp_conf = {
        **defaults.get("componentes_rgb_conf", {}),
        **job.get("componentes_rgb_conf", {}),
    }
    # Si no se definieron productos para componentes, usar todos los productos del job
    if comp_conf.get("productos") is None and comp_conf.get("producto") is None:
        comp_conf["productos"] = list(productos)
    # Mapear producto -> lista de rutas PNG
    frames_por_producto = {}
    for dt in expand_datetimes(job):
        logger.info("Procesando datetime %s para job %s", dt.isoformat(), nombre_job)
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

        out_dir = Path(png_conf.get("out_dir", "salidas"))
        out_dir.mkdir(parents=True, exist_ok=True)
        shp = png_conf.get(
            "shapefile_provincias",
            "shapefiles/provincias/linea_de_limite_070111Line.shp",
        )
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
                    show=png_conf.get("show", False),
                    lon_interval=10,
                    lat_interval=10,
                    save_path=str(png_path),
                    save=True,
                )
                generated_files.append(str(png_path))

            # Exportar componentes R/G/B si está configurado
            # 4. Comprobar si se deben exportar componentes

            if "COMPONENTES_RGB" in salidas_deseadas and comp_conf:
                from goes_rgb.helpers import save_band_geotiff

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

                    canales = {"R": rgb[..., 0], "G": rgb[..., 1], "B": rgb[..., 2]}
                    for canal, data in canales.items():
                        fname = (
                            pattern.replace("{producto}", nombre)
                            .replace("{ts}", ts)
                            .replace("{canal}", canal)
                        )
                        out_path = comp_out / fname
                        save_band_geotiff(
                            data, x, y, f0, f1, c0, c1, crs, str(out_path)
                        )
                        logger.info("Componente GeoTIFF generado: %s", out_path)
                        generated_files.append(str(out_path))

            # GeoTIFF (uno por fecha). Elegí producto con geotiff.producto o geotiff.productos
            # 5. Comprobar si se debe exportar GeoTIFF
            if "GEOTIFF" in salidas_deseadas and geotiff_conf:
                from goes_rgb.helpers import save_rgb_geotiff
                from scripts.GeoTIFF_translate_coord_output import reproject_geotiff

                gt_cfg = geotiff_conf
                productos_gt = gt_cfg.get("productos")
                producto_gt = gt_cfg.get("producto")
                lista_gt = None
                if productos_gt:
                    lista_gt = list(productos_gt)
                elif producto_gt:
                    lista_gt = [producto_gt]
                elif len(productos) == 1:
                    lista_gt = [productos[0]]

                if lista_gt:
                    gt_out = Path(gt_cfg.get("out_dir", out_dir))
                    gt_out.mkdir(parents=True, exist_ok=True)
                    ts = dt.strftime("%Y%m%d_%H%M")
                    pattern = gt_cfg.get("filename_pattern", "{producto}_{ts}.tif")
                    for nombre_gt in lista_gt:
                        if nombre_gt != nombre:
                            continue
                        tif_name = pattern.replace("{producto}", nombre_gt).replace(
                            "{ts}", ts
                        )
                        tiff_path = gt_out / tif_name
                        save_rgb_geotiff(rgb, x, y, f0, f1, c0, c1, crs, str(tiff_path))
                        logger.info("GeoTIFF generado: %s", tiff_path)
                        generated_files.append(str(tiff_path))
                        
                        # Reproyectar si está configurado
                        reproyecciones = gt_cfg.get("reproyecciones", [])
                        if reproyecciones:
                            for reproj_conf in reproyecciones:
                                epsg = reproj_conf.get("epsg")
                                suffix = reproj_conf.get("suffix", "")
                                if epsg:
                                    # Generar nombre del archivo reproyectado
                                    reproj_name = tif_name.replace(".tif", f"{suffix}.tif")
                                    reproj_path = gt_out / reproj_name
                                    try:
                                        reproject_geotiff(str(tiff_path), str(reproj_path), epsg)
                                        logger.info(
                                            "GeoTIFF reproyectado: %s a %s",
                                            reproj_path,
                                            epsg,
                                        )
                                        generated_files.append(str(reproj_path))
                                    except Exception as e:
                                        logger.exception(
                                            "Error al reproyectar %s a %s",
                                            tiff_path,
                                            epsg,
                                        )

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
                import imageio.v2 as imageio
                import numpy as np

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
        # breakpoint()
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
            logger.info(
                "GIF generado: %s frames=%s delay=%ss loop=%s",
                gif_path,
                len(gif_frames),
                frame_seconds,
                loop,
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
                logger.info("MP4 generado: %s frames=%s fps=%s", video_path, len(padded), fps)

            logger.info("Job %s finalizado. Archivos generados: %s", nombre_job, len(generated_files))
    return generated_files


def run_from_config(ruta):
    cfg = load_config(ruta)
    total_generated_files = []
    defaults = cfg.get("defaults", {})
    for job in cfg.get("jobs", []):
        try:
            generated_files = run_job(job, defaults)
            total_generated_files.extend(generated_files)
        except Exception:
            logger.exception("Fallo el job %s", job.get("nombre", "job"))
            raise
    logger.info("Ejecución completa. Total de archivos generados: %s", len(total_generated_files))
    return total_generated_files
