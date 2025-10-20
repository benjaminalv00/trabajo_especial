#!/usr/bin/env python3
import yaml
import re
from datetime import datetime
from pathlib import Path
from config_runner import run_from_config
from goes_rgb.recipes_registry import RECIPE_REGISTRY

# ============================================================
# Utilidades
# ============================================================


def normalizar_fecha(s: str) -> str:
    """Limpia caracteres invisibles o codificación UTF-8 errónea."""
    if not s:
        return s
    s = s.replace(" ", " ").replace("–", "-").replace("−", "-")
    s = s.encode("utf-8", "ignore").decode("utf-8", "ignore")
    s = re.sub(r"[^\d\s:-]", "", s)
    return s.strip()


def parse_fecha_from_filename(filename):
    """Extrae fecha UTC a partir del nombre del archivo GOES."""
    match = re.search(r"s(\d{4})(\d{3})(\d{2})(\d{2})(\d{2})", filename)
    if not match:
        return None
    year, doy, hh, mm, ss = map(int, match.groups())
    dt = datetime.strptime(
        f"{year}{doy:03d} {hh:02d}:{mm:02d}:{ss:02d}", "%Y%j %H:%M:%S"
    )
    return dt


def listar_imagenes_locales(data_dir="data"):
    from pathlib import Path

    archivos = sorted(Path(data_dir).rglob("*.nc"))
    imagenes = []
    for f in archivos:
        dt = parse_fecha_from_filename(f.name)
        if dt:
            sat = re.search(r"G(\d{2})", f.name)
            sat_name = f"GOES{sat.group(1)}" if sat else "GOES?"
            tipo = "L1B" if "L1b" in f.name else "MCMI" if "MCMI" in f.name else "?"
            imagenes.append((dt, f.name, sat_name, tipo))
    imagenes.sort()
    return imagenes


# ============================================================
# Preguntas interactivas
# ============================================================


def preguntar_fecha():
    print("\n📅 Selección de fecha:")
    print("1) Usar una imagen ya descargada (/data)")
    print("2) Ingresar una fecha manual")
    print("3) Usar un rango de fechas")
    op = input("Elegí una opción (1-3): ").strip()

    if op == "1":
        imagenes = listar_imagenes_locales()
        if not imagenes:
            print("⚠️ No se encontraron archivos en /data, se solicitará fecha manual.")
            op = "2"
        else:
            print("\nImágenes disponibles:")
            for i, (dt, name, sat, tipo) in enumerate(imagenes, start=1):
                print(f"{i:2d}) {dt:%Y-%m-%d %H:%M UTC} ({sat}, {tipo})  {name}")
            sel = input("\nSeleccioná el número de imagen: ").strip()
            try:
                dt, _, _, tipo = imagenes[int(sel) - 1]
                return {"datetime": dt.strftime("%Y-%m-%d %H:%M"), "tipo_imagen": tipo}
            except (ValueError, IndexError):
                print("Opción inválida, se pedirá fecha manual.")
                op = "2"

    if op == "2":
        fecha = normalizar_fecha(input("Ingresá fecha y hora (YYYY-MM-DD HH:MM UTC): "))
        return {"datetime": fecha, "tipo_imagen": None}

    elif op == "3":
        ini = normalizar_fecha(input("Fecha inicio (YYYY-MM-DD HH:MM UTC): "))
        fin = normalizar_fecha(input("Fecha fin (YYYY-MM-DD HH:MM UTC): "))
        paso = input("Paso en minutos [30]: ").strip() or "30"
        return {
            "rango": {"inicio": ini, "fin": fin, "paso_minutos": int(paso)},
            "tipo_imagen": None,
        }

    else:
        print("Opción inválida, se usará fecha manual.")
        fecha = normalizar_fecha(input("Ingresá fecha y hora (YYYY-MM-DD HH:MM UTC): "))
        return {"datetime": fecha, "tipo_imagen": None}


def preguntar_recorte():
    print("\n🌍 Selección de recorte geográfico:")
    presets = {
        "1": ("Cono Sur", [10.0, -60.0, -90.0, -30.0]),
        "2": ("Argentina", [-20.0, -56.0, -75.0, -53.0]),
        "3": ("Córdoba", [-30.0, -34.0, -67.0, -62.0]),
        "4": ("Sudamérica", [15.0, -60.0, -90.0, -30.0]),
        "5": ("Personalizado", None),
        "6": ("Sin recorte", None),
    }

    for key, (name, _) in presets.items():
        print(f"{key}) {name}")

    op = input("Elegí una opción (1-6): ").strip()
    if op not in presets:
        print("Opción inválida. No se aplicará recorte.")
        return None

    nombre, coords = presets[op]
    if nombre == "Sin recorte":
        return None
    elif nombre == "Personalizado":
        print("Ingresá coordenadas personalizadas:")
        latN = float(input("Latitud norte: "))
        latS = float(input("Latitud sur: "))
        lonW = float(input("Longitud oeste: "))
        lonE = float(input("Longitud este: "))
        return [latN, latS, lonW, lonE]
    else:
        print(f"✅ Se usará el recorte predefinido: {nombre}")
        print(f"   Coordenadas: {coords}")
        return coords


def preguntar_productos():
    print("\n🎨 Selección de productos RGB disponibles:\n")
    productos_disponibles = sorted(RECIPE_REGISTRY.keys())
    for i, nombre in enumerate(productos_disponibles, start=1):
        print(f"  {i:2d}) {nombre}")

    seleccion = input(
        "\nIngresá los números de los productos separados por coma (ej: 1,3): "
    ).strip()
    try:
        indices = [int(x.strip()) for x in seleccion.split(",") if x.strip()]
        seleccionados = [
            productos_disponibles[i - 1]
            for i in indices
            if 0 < i <= len(productos_disponibles)
        ]
    except ValueError:
        print("⚠️ Entrada inválida, se usará 'TrueColor' por defecto.")
        seleccionados = ["TrueColor"]

    if not seleccionados:
        seleccionados = ["TrueColor"]

    print(f"\n✅ Productos seleccionados: {', '.join(seleccionados)}")
    return seleccionados


# ============================================================
# Flujo principal
# ============================================================


def main():
    print("=== Generador interactivo de configuraciones GOES RGB ===")

    nombre_job = input("\nNombre del job (ej: 'ejemplo_png'): ").strip() or "job"
    fechas_info = preguntar_fecha()
    productos = preguntar_productos()
    recorte = preguntar_recorte()
    satelite = input("\nSatélite [GOES16]: ").strip() or "GOES16"

    tipo_imagen = fechas_info.get("tipo_imagen") or "MCMI"

    defaults = {
        "data_dir": "data",
        "tipo_imagen": tipo_imagen,
        "satelite": satelite,
        "png_conf": {"out_dir": "salidas"},
        "geotiff_conf": {"out_dir": "geotiffs"},
    }

    job = {
        "nombre": nombre_job,
        "tipo_imagen": tipo_imagen,
        "productos": productos,
        "salidas": ["PNG", "GEOTIFF"],
        "satelite": satelite,
    }

    if recorte:
        job["recorte"] = recorte

    # agregar datetime o rango
    if "rango" in fechas_info:
        job["rango"] = fechas_info["rango"]
    elif "datetime" in fechas_info:
        job["datetime"] = fechas_info["datetime"]

    config = {"defaults": defaults, "jobs": [job]}

    out_path = Path("config/config_temp.yaml")
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)

    print(f"\n✅ Configuración guardada en {out_path.resolve()}")
    print("🚀 Ejecutando trabajo...\n")

    run_from_config(out_path)
    print("\n🎉 Proceso finalizado con éxito (solo PNG y GeoTIFF).")


if __name__ == "__main__":
    main()
