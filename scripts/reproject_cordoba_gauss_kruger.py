import argparse
from pathlib import Path

try:
    # Cuando se ejecuta como modulo desde la raiz del proyecto.
    from scripts.GeoTIFF_translate_coord_output import (
        reproject_to_gauss_kruger_argentina,
    )
except ModuleNotFoundError:
    # Cuando se ejecuta como script directo dentro de la carpeta scripts.
    from GeoTIFF_translate_coord_output import reproject_to_gauss_kruger_argentina


DEFAULT_FAJA_CORDOBA = 4


def build_default_output(src_path: str, faja: int) -> str:
    src = Path(src_path)
    return str(src.with_name(f"{src.stem}_cordoba_faja{faja}.tif"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reproyecta un GeoTIFF al sistema Gauss-Kruger para Cordoba. "
            "Por defecto usa faja 4 (EPSG:22174)."
        )
    )
    parser.add_argument("input", help="Ruta del GeoTIFF de entrada")
    parser.add_argument(
        "--output",
        help="Ruta del GeoTIFF de salida. Si no se indica, se genera automaticamente.",
    )
    parser.add_argument(
        "--faja",
        type=int,
        default=DEFAULT_FAJA_CORDOBA,
        choices=range(1, 8),
        help="Faja Gauss-Kruger (1-7). Para Cordoba suele usarse 4.",
    )

    args = parser.parse_args()
    output = args.output or build_default_output(args.input, args.faja)

    result = reproject_to_gauss_kruger_argentina(
        src_path=args.input,
        dst_path=output,
        faja=args.faja,
    )
    print(f"Archivo reproyectado generado: {result}")


if __name__ == "__main__":
    main()
