import argparse
from config_runner import run_from_config


def run_manual_demo():
    from datetime import datetime
    from goes_rgb.l2_abi_image import ABIImageMCMI
    from goes_rgb.rgb_processor import RGBProcessor
    from goes_rgb.rgb_recipes import true_color
    from goes_rgb.visualization import plot_rgb_with_coastlines

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Ruta a YAML de batch.")
    parser.add_argument("--demo", action="store_true", help="Ejecuta demo manual.")
    parser.add_argument(
        "--api",
        action="store_true",
        help="Inicia la API web para construir configuraciones.",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Inicia la interfaz NiceGUI para construir configuraciones.",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host para la API web (por defecto 0.0.0.0)."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Puerto para la API web (por defecto 8000).",
    )
    args = parser.parse_args()

    if args.api and args.ui:
        parser.error("Usá sólo una de las opciones --api o --ui a la vez.")

    if args.api:
        import uvicorn

        uvicorn.run("web.server:app", host=args.host, port=args.port)
        return

    if args.ui:
        from web import nice_app_session as nice_app

        nice_app.run(host=args.host, port=args.port)
        return

    if args.demo:
        run_manual_demo()
    elif args.config:
        run_from_config(args.config)
    else:
        parser.error("Usar --config archivo.yml, --demo o --api")


if __name__ == "__main__":
    main()
