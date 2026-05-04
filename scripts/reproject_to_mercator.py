import argparse
from pathlib import Path

try:
    from scripts.GeoTIFF_translate_coord_output import reproject_geotiff
except ModuleNotFoundError:
    from GeoTIFF_translate_coord_output import reproject_geotiff


def build_default_output(src_path: str) -> str:
    src = Path(src_path)
    return str(src.with_name(f"{src.stem}_3857.tif"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reproyecta un GeoTIFF a Web Mercator (EPSG:3857)."
        )
    )
    parser.add_argument("input", help="Ruta del GeoTIFF de entrada")
    parser.add_argument(
        "--output",
        help="Ruta del GeoTIFF de salida. Si no se indica, se genera automaticamente.",
    )

    args = parser.parse_args()
    src = Path(args.input)
    if not src.exists():
        raise FileNotFoundError(f"Archivo de entrada no encontrado: {src}")

    dst = args.output or build_default_output(args.input)

    reproject_geotiff(str(src), str(dst), "EPSG:3857")
    print(f"Archivo reproyectado generado: {dst}")


if __name__ == "__main__":
    main()
