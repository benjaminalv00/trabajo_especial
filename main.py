import argparse
from config_runner import run_from_config
from goes_rgb.logging_utils import setup_logging, get_logger


logger = get_logger(__name__)


def run_manual_demo():
    from datetime import datetime
    from goes_rgb.l2_abi_image import ABIImageMCMI
    from goes_rgb.rgb_processor import RGBProcessor
    from goes_rgb.rgb_recipes import true_color
    from goes_rgb.visualization import plot_rgb_with_coastlines

    logger.info("Iniciando demo manual")
    img = ABIImageMCMI(datetime(2022, 9, 21, 18, 0))
    img.download()
    img.open()
    crs, x, y = img.get_projection_params()
    f0, f1, c0, c1 = img.get_bbox_indices(-18.6, -56.45, -79.79, -50.0)
    recipes = {"true_color": true_color()}
    processor = RGBProcessor(img, recipes, recorte=(f0, f1, c0, c1))
    processor.generate_all()
    rgb = processor.get_product("true_color")
    plot_rgb_with_coastlines(
        rgb,
        extent=(x[c0], x[c1], y[f1], y[f0]),
        crs_geo=crs,
        title="Demo manual",
        provincias_shp="shapefiles/provincias/linea_de_limite_070111Line.shp",
        show=True,
    )
    logger.info("Demo manual finalizada")


def main():
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Ruta a YAML de batch.")
    parser.add_argument("--demo", action="store_true", help="Ejecuta demo manual.")
    args = parser.parse_args()
    try:
        if args.demo:
            run_manual_demo()
        elif args.config:
            logger.info("Ejecutando desde configuración: %s", args.config)
            run_from_config(args.config)
        else:
            parser.error("Usar --config archivo.yml o --demo")
    except Exception:
        logger.exception("Fallo la ejecución principal")
        raise


if __name__ == "__main__":
    main()
