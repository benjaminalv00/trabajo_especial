import streamlit as st
import yaml
from pathlib import Path
from datetime import datetime
from config_runner import run_from_config
from goes_rgb.recipes_registry import RECIPE_REGISTRY

# ============================================================
# Utilidades
# ============================================================


def fecha_a_iso(fecha_str):
    """Convierte 'YYYY-MM-DD HH:MM' a 'YYYY-MM-DDTHH:MM:SS' (ISO 8601)."""
    fecha_str = fecha_str.strip().replace(" ", "T")
    if len(fecha_str.split(":")) == 2:
        fecha_str += ":00"
    return fecha_str


def obtener_recorte(nombre):
    """Devuelve coordenadas [latN, latS, lonW, lonE] según preset."""
    presets = {
        "América del sur": [10.0, -60.0, -90.0, -30.0],
        "Argentina": [-20.0, -56.0, -75.0, -53.0],
        "Córdoba": [-30.0, -34.0, -67.0, -62.0],
        "Sin recorte": None,
    }
    return presets.get(nombre, None)


# ============================================================
# Interfaz
# ============================================================

st.title("🌎 Procesador de Imágenes GOES RGB")

st.markdown(
    "Generá configuraciones y ejecutá el procesador GOES RGB sin editar YAML. "
    "El sistema produce automáticamente imágenes PNG y/o GeoTIFF."
)

# Parámetros generales
nombre = st.text_input("Nombre del job", "demo")
satelite = st.selectbox("Satélite", ["GOES16", "GOES18", "GOES19"])
productos_disponibles = sorted(RECIPE_REGISTRY.keys())
productos = st.multiselect(
    "Productos RGB",
    options=productos_disponibles,
    default=(
        ["TrueColor"]
        if "TrueColor" in productos_disponibles
        else [productos_disponibles[0]]
    ),
)

# Selección de tipo de salida
salidas = st.multiselect("Salidas deseadas", ["PNG", "GeoTIFF"], ["PNG", "GeoTIFF"])

# Fecha o rango
modo_fecha = st.radio("Modo de fecha", ["Única", "Rango"])
if modo_fecha == "Única":
    fecha = st.text_input("Fecha (YYYY-MM-DD HH:MM UTC)", "2025-08-30 18:00")
    fecha_conf = {"datetime": fecha_a_iso(fecha)}
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        ini = st.text_input("Inicio (YYYY-MM-DD HH:MM UTC)", "2025-08-30 12:00")
    with col2:
        fin = st.text_input("Fin (YYYY-MM-DD HH:MM UTC)", "2025-08-30 18:00")
    with col3:
        paso = st.number_input(
            "Paso (minutos)", min_value=5, max_value=120, value=30, step=5
        )
    fecha_conf = {
        "rango": {
            "inicio": fecha_a_iso(ini),
            "fin": fecha_a_iso(fin),
            "paso_minutos": paso,
        }
    }

# Recorte
recorte_nombre = st.selectbox(
    "Recorte", ["Cono Sur", "Argentina", "Córdoba", "Sin recorte"]
)
recorte = obtener_recorte(recorte_nombre)

# Configuración de GeoTIFF específica
if "GeoTIFF" in salidas:
    st.subheader("🗺️ Configuración de salida GeoTIFF")
    modo_geotiff = st.radio(
        "Modo de selección de productos", ["Un producto", "Varios productos"]
    )
    if modo_geotiff == "Un producto":
        geotiff_producto = st.selectbox("Producto a exportar como GeoTIFF", productos)
        geotiff_productos = None
    else:
        geotiff_productos = st.multiselect(
            "Seleccioná productos a exportar como GeoTIFF", productos, default=productos
        )
        geotiff_producto = None
    geotiff_outdir = st.text_input("Carpeta de salida", "geotiffs/")
    geotiff_pattern = st.text_input("Patrón de nombre", "{producto}_{ts}.tif")
else:
    geotiff_producto = None
    geotiff_productos = None

# ============================================================
# Ejecución
# ============================================================

if st.button("🚀 Ejecutar procesamiento"):
    defaults = {
        "data_dir": "data",
        "tipo_imagen": "MCMI",
        "satelite": satelite,
        "png_conf": {"out_dir": "salidas"},
        "geotiff_conf": {"out_dir": "geotiffs"},
    }

    job = {
        "nombre": nombre,
        "tipo_imagen": "MCMI",
        "productos": productos,
        "salidas": salidas,
        "satelite": satelite,
    }

    # Añadir recorte
    if recorte:
        job["recorte"] = recorte

    # Añadir fecha o rango
    job.update(fecha_conf)

    # Añadir configuración específica GeoTIFF
    if "GeoTIFF" in salidas:
        geo_conf = {
            "out_dir": geotiff_outdir,
            "filename_pattern": geotiff_pattern,
        }
        if geotiff_producto:
            geo_conf["producto"] = geotiff_producto
        if geotiff_productos:
            geo_conf["productos"] = geotiff_productos
        job["geotiff_conf"] = geo_conf

    config = {"defaults": defaults, "jobs": [job]}

    # Guardar YAML
    yaml_path = Path("config_temp.yaml")
    yaml_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
    st.subheader("🧾 Configuración generada")
    st.code(yaml.safe_dump(config, sort_keys=False), language="yaml")

    # Ejecutar
    try:
        run_from_config(yaml_path)
        st.success("✅ Procesamiento finalizado con éxito (PNG y GeoTIFF generados).")
    except Exception as e:
        st.error(f"❌ Error durante la ejecución: {e}")
