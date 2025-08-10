from datetime import datetime
from goes_rgb.l2_abi_image import ABIImageMCMI
from goes_rgb.l1b_abi_image import ABIImageL1b
from goes_rgb.rgb_processor import RGBProcessor
from goes_rgb.rgb_recipes import (
    microfisica_nocturna,
    true_color,
    fire_temperature,
    daily_microphysics,
    air_mass,
    ash,
    day_cloud_convection,
    day_convection,
    day_land_cloud,
    day_land_cloud_fire,
    day_snow_fog,
    simple_water_vapor,
    dust,
    differential_water_vapor,
)
from goes_rgb.visualization import plot_rgb_with_coastlines
from goes_rgb.helpers import save_rgb_geotiff
import numpy as np

# Instanciar imagen ABI
# bands = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C13", "C14", "C15"]
# bands = ["C02","C13"]
img = ABIImageMCMI(datetime(2022, 9, 21, 18, 0))
# img = ABIImageL1b(datetime(2018, 7, 13, 18, 0), "ABI-L1b-RadF", bands)

img.download()
img.open()
# productos RGB seleccionados
recipes = {
    # "Microfisica Nocturna": microfisica_nocturna(),
    # "Color Real": true_color(),
    # "Temperatura de Fuego": fire_temperature(),
    # "Microfisica Diurna": daily_microphysics(),
    # "Masa de aire": air_mass(),
    # "Cenizas": ash()
    # "Convección de Nubes Diurna": day_cloud_convection(),
    # "Conveccion Diurna": day_convection()
    # "Nubes de dia": day_land_cloud()
    # "Nubes de dia y fuego": day_land_cloud_fire()
    # "Nubes de dia y nieve": day_snow_fog()
    # "vapor de agua simple": simple_water_vapor()
    # "Polvo": dust()
    "vapor de agua diferencial": differential_water_vapor()
}

# Obtener parámetros de proyección
# breakpoint()
crs, x, y = img.get_projection_params()

# Recorte por lat/lon (Arg)
f0, f1, c0, c1 = img.get_bbox_indices(-18.6, -56.45, -79.79, -50.0)

# Recorte CBA
# f0, f1, c0, c1 = img.get_bbox_indices(-28, -36, -66, -61)
# breakpoint()
processor = RGBProcessor(abi_image=img, recipes=recipes, recorte=(f0, f1, c0, c1))
processor.generate_all()
# Acceder al producto

for recipe in recipes:
    print(f"Producto: {recipe}")
    rgb = processor.get_product(recipe)
    # Guardar como GeoTIFF
    plot_rgb_with_coastlines(
        rgb,
        extent=(x[c0], x[c1], y[f1], y[f0]),
        crs_geo=crs,
        title=f"RGB - {recipe}",
        provincias_shp="shapefiles/provincias/linea_de_limite_070111Line.shp",
        show=True,
    )
# rgb = processor.get_product(
#     "Microfisica Nocturna" #"Color Real"  # "Microfisica Diurna"  # Cambiar a "Microfisica Nocturna" o "Temperatura de Fuego" según sea necesario
# )  # Cambiar a "Microfisica Nocturna" o "Temperatura de Fuego" según sea necesario
# Visualizar
# extent = (x[c0], x[c1], y[f1], y[f0])
# plot_rgb_with_coastlines(
#     rgb,
#     extent,
#     crs,
#     title="RGB",
#     provincias_shp="shapefiles/provincias/linea_de_limite_070111Line.shp",
#     show=True,
# )
