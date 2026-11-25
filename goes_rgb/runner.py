import yaml
from pathlib import Path
from datetime import datetime, timedelta
from goes_rgb.recipes_registry import RECIPE_REGISTRY

# GOES-19 reemplazó a GOES-16 como GOES-East el 7 de abril de 2025. Si el YAML
# no indica `satelite`, se usa el GOES-East vigente en la fecha pedida.
INICIO_GOES19_ESTE = datetime(2025, 4, 7)

# Archivos que trae el repositorio (shapefile de provincias). Se resuelven
# relativos a la raíz del repo y no al directorio de trabajo, para que el
# procesador funcione cuando se lo llama desde otro programa.
RAIZ_REPO = Path(__file__).resolve().parent.parent
SHP_PROVINCIAS = RAIZ_REPO / "shapefiles/provincias/linea_de_limite_070111Line.shp"


def ruta_del_repo(ruta):
    """Devuelve la ruta tal cual si existe; si es relativa y no existe desde
    el directorio de trabajo, la busca desde la raíz del repositorio."""
    p = Path(ruta)
    if p.is_absolute() or p.exists():
        return str(p)
    candidata = RAIZ_REPO / p
    return str(candidata) if candidata.exists() else str(p)


# Claves que el procesador lee de `defaults` y de cada job.
CLAVES_CONOCIDAS = {
    "nombre",
    "productos",
    "datetime",
    "datetimes",
    "rango",
    "satelite",
    "tipo_imagen",
    "canales",
    "recorte",
    "data_dir",
    "salidas",
    "png_conf",
    "gif_conf",
    "video_conf",
    "geotiff_conf",
    "componentes_rgb_conf",
}

# Claves de versiones anteriores que hoy se ignoran, con su reemplazo.
CLAVES_VIEJAS = {
    "export": "png_conf",
    "gif": "gif_conf",
    "video": "video_conf",
    "geotiff": "geotiff_conf",
    "componentes_rgb": "componentes_rgb_conf",
}


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


def satelite_por_defecto(dt):
    """Devuelve el GOES-East vigente en la fecha `dt`."""
    return "GOES19" if dt >= INICIO_GOES19_ESTE else "GOES16"


def avisar_claves_desconocidas(bloque, donde):
    """Avisa las claves que el procesador no va a usar, para que no fallen en silencio."""
    avisos = []
    for clave in bloque:
        if clave in CLAVES_VIEJAS:
            avisos.append(
                f"Aviso: en {donde}, la clave '{clave}' ya no se usa; "
                f"usá '{CLAVES_VIEJAS[clave]}'."
            )
        elif clave not in CLAVES_CONOCIDAS:
            avisos.append(
                f"Aviso: en {donde}, la clave '{clave}' no se reconoce y se ignora."
            )
    for aviso in avisos:
        print(aviso)
    return avisos


def build_image(dt, defaults, job, bandas=None):
    """
    Construye la imagen ABI del tipo pedido por el job.

    `bandas` es el conjunto de bandas que las recetas van a necesitar. Solo se
    usa para L1b, donde cada banda es un NetCDF aparte y acotar los canales
    evita descargar y abrir archivos que nadie va a mirar. En MCMI es un unico
    archivo multibanda y el ahorro lo da la lectura perezosa de
    ABIImageMCMI.get_band_array.
    """
    from goes_rgb.l2_abi_image import ABIImageMCMI
    from goes_rgb.l1b_abi_image import ABIImageL1b

    modo = job.get("tipo_imagen", defaults.get("tipo_imagen", "MCMI")).upper()
    satelite = job.get("satelite", defaults.get("satelite")) or satelite_por_defecto(dt)
    satelite = str(satelite).upper()
    data_dir = job.get("data_dir", defaults.get("data_dir", "data"))
    channels = job.get("canales", defaults.get("canales", None))
    if channels is None and bandas:
        channels = sorted(bandas)
    if modo == "MCMI":
        return ABIImageMCMI(
            dt, satellite=f"noaa-{satelite.lower()}", local_dir=data_dir
        )
    if modo == "L1B":
        return ABIImageL1b(
            dt,
            "ABI-L1b-RadF",
            channels=channels,
            satellite=f"noaa-{satelite.lower()}",
            local_dir=data_dir,
        )
    raise ValueError(f"tipo_imagen desconocido: {modo}")


def _build_output_confs(job, defaults, productos):
    """Fusiona defaults + job para cada tipo de salida (seam de configuración)."""
    confs = {
        "PNG": {**defaults.get("png_conf", {}), **job.get("png_conf", {})},
        "GIF": {**defaults.get("gif_conf", {}), **job.get("gif_conf", {})},
        "VIDEO": {**defaults.get("video_conf", {}), **job.get("video_conf", {})},
        "GEOTIFF": {
            **defaults.get("geotiff_conf", {}),
            **job.get("geotiff_conf", {}),
        },
        "COMPONENTES_RGB": {
            **defaults.get("componentes_rgb_conf", {}),
            **job.get("componentes_rgb_conf", {}),
        },
    }
    # Si no se definieron productos para componentes, usar todos los del job
    comp_conf = confs["COMPONENTES_RGB"]
    if comp_conf.get("productos") is None and comp_conf.get("producto") is None:
        comp_conf["productos"] = list(productos)
    return confs


def _acquire_image(dt, defaults, job, bandas=None):
    """Descarga y abre la imagen ABI para una fecha (seam de adquisición)."""
    img = build_image(dt, defaults, job, bandas=bandas)
    img.download()
    img.open()
    crs, x, y = img.get_projection_params()
    return img, crs, x, y


def _compute_roi(img, recorte_conf, x, y):
    """Calcula índices de recorte y extent para el frame (seam de ROI)."""
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
    return rec_tuple, extent, f0, f1, c0, c1


def _build_processor(img, recipes, rec_tuple):
    """Genera los productos RGB solicitados para un frame (seam de generación)."""
    from goes_rgb.rgb_processor import RGBProcessor

    processor = RGBProcessor(img, recipes, recorte=rec_tuple)
    processor.generate_all()
    return processor


def run_job(job, defaults):
    if not job.get("productos"):
        raise ValueError(
            f"El job '{job.get('nombre', 'sin nombre')}' no define 'productos'."
        )
    from goes_rgb.output_handlers import (
        FrameContext,
        FRAME_OUTPUT_REGISTRY,
        ACCUMULATOR_OUTPUT_REGISTRY,
    )

    productos = job["productos"]
    recorte_conf = job.get("recorte", defaults.get("recorte"))
    generated_files = []

    # Las recetas se resuelven una sola vez para todo el job (no cambian entre
    # fechas) y de ellas sale el conjunto de bandas realmente necesarias.
    recipes = {p: RECIPE_REGISTRY[p]() for p in productos}
    bandas = {b for receta in recipes.values() for b in receta["bands"]}

    salidas_deseadas = {s.upper() for s in job.get("salidas", ["PNG"])}
    confs = _build_output_confs(job, defaults, productos)
    frames_por_producto = {}
    nombre_job = job.get("nombre", "job")

    for dt in expand_datetimes(job):
        img, crs, x, y = _acquire_image(dt, defaults, job, bandas=bandas)
        rec_tuple, extent, f0, f1, c0, c1 = _compute_roi(img, recorte_conf, x, y)
        if rec_tuple is not None:
            # Con la ventana fijada, la imagen entrega las bandas ya recortadas,
            # asi que RGBProduct no tiene que volver a recortar (recorte=None).
            img.set_window(*rec_tuple)
            processor = _build_processor(img, recipes, None)
        else:
            processor = _build_processor(img, recipes, rec_tuple)

        out_dir = Path(confs["PNG"].get("out_dir", "salidas"))
        out_dir.mkdir(parents=True, exist_ok=True)
        shp = ruta_del_repo(confs["PNG"].get("shapefile_provincias", SHP_PROVINCIAS))

        for nombre in productos:
            rgb = processor.get_product(nombre)
            titulo = f"{job.get('nombre', nombre)} {nombre} {dt:%Y%m%d_%H%M}"
            png_path = out_dir / f"{nombre_job}_{nombre}_{dt:%Y%m%d_%H%M}.png"

            ctx = FrameContext(
                rgb=rgb,
                nombre=nombre,
                dt=dt,
                extent=extent,
                crs=crs,
                x=x,
                y=y,
                f0=f0,
                f1=f1,
                c0=c0,
                c1=c1,
                productos=productos,
                out_dir=out_dir,
                shp=shp,
                titulo=titulo,
                png_path=png_path,
            )

            for nombre_salida, handler in FRAME_OUTPUT_REGISTRY.items():
                conf = confs.get(nombre_salida, {})
                if handler.activo(salidas_deseadas, conf):
                    generated_files.extend(handler.exportar(ctx, conf))

            # Acumular frame para GIF/Video si algún acumulador lo pide para
            # este producto (se hace una sola vez, aunque GIF y VIDEO
            # coincidan en el mismo producto).
            quiere_frame = any(
                acc_nombre in salidas_deseadas
                and confs.get(acc_nombre)
                and handler.frame_deseado(nombre, confs[acc_nombre])
                for acc_nombre, handler in ACCUMULATOR_OUTPUT_REGISTRY.items()
            )
            if quiere_frame:
                if "PNG" not in salidas_deseadas:
                    from goes_rgb.visualization import plot_rgb_with_coastlines

                    plot_rgb_with_coastlines(
                        rgb,
                        extent=extent,
                        crs_geo=crs,
                        title=titulo,
                        provincias_shp=shp,
                        show=False,
                        # Mismo origen que PngOutputHandler, para que el frame
                        # del GIF y el PNG suelto salgan con la misma grilla.
                        lon_interval=confs["PNG"].get("lon_interval", 10),
                        lat_interval=confs["PNG"].get("lat_interval", 10),
                        save_path=str(png_path),
                        save=True,
                    )
                frames_por_producto.setdefault(nombre, []).append(str(png_path))

    for acc_nombre, handler in ACCUMULATOR_OUTPUT_REGISTRY.items():
        conf = confs.get(acc_nombre)
        if acc_nombre in salidas_deseadas and conf:
            frames = frames_por_producto.get(conf.get("producto"), [])
            generated_files.extend(handler.finalizar(frames, conf))

    return generated_files


def run_from_config(ruta):
    cfg = load_config(ruta)
    total_generated_files = []
    defaults = cfg.get("defaults") or {}
    avisar_claves_desconocidas(defaults, "defaults")
    for i, job in enumerate(cfg.get("jobs") or [], start=1):
        if not isinstance(job, dict):
            raise ValueError(f"El job número {i} de {ruta} está vacío o mal escrito.")
        avisar_claves_desconocidas(job, f"el job '{job.get('nombre', i)}'")
        generated_files = run_job(job, defaults)
        total_generated_files.extend(generated_files)
    return total_generated_files
