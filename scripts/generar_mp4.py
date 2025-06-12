from datetime import datetime
from goes_rgb.core import ABIImage
from goes_rgb.rgb_processor import RGBProcessor
from goes_rgb.rgb_recipes import microfisica_nocturna, true_color, fire_temperature
from goes_rgb.visualization import plot_rgb_with_coastlines
from goes_rgb.helpers import save_rgb_geotiff
import numpy as np

# #limpiamos la memoria
# import gc
# gc.collect()
# # Instanciar imagen ABI
# #full_bands = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C13", "C14", "C15"]
bands = ["C07", "C06", "C05"]
# bands = ['C03', 'C02', 'C01']  # Bandas para el producto RGB Color Real
# #bands = ['C15', 'C13', 'C07']  # Bandas para el producto RGB Microfisica Nocturna
# #img = ABIImage(datetime(2024, 9, 21, 7, 0), "ABI-L1b-RadF", full_bands)

# img = ABIImage(datetime(2024, 9, 21, 18, 0), "ABI-L1b-RadF", bands)

# img.download()
# img.open()
# # productos RGB seleccionados
recipes = {
    # "Microfisica Nocturna": microfisica_nocturna(),
    # "Color Real": true_color(),
    "Temperatura de Fuego": fire_temperature(),
}

# # Obtener parámetros de proyección
# crs, x, y = img.get_projection_params()

# # Recorte por lat/lon (Arg)
# #f0, f1, c0, c1 = img.get_bbox_indices(-18.6, -56.45, -79.79, -50.0)

# # Recorte CBA
# f0, f1, c0, c1 = img.get_bbox_indices(-28, -36, -66, -61)

# processor = RGBProcessor(abi_image=img, recipes=recipes,recorte=(f0, f1, c0, c1))
# processor.generate_all()
# # Acceder al producto
# rgb = processor.get_product("Color Real")  # Cambiar a "Microfisica Nocturna" o "Temperatura de Fuego" según sea necesario
# # Visualizar
# extent = (x[c0], x[c1], y[f1], y[f0])
# plot_rgb_with_coastlines(rgb, extent, crs,
#     title="RGB Color Real",
#     provincias_shp="shapefiles/provincias/linea_de_limite_070111Line.shp",
#     show=True)

# # Guardar como GeoTIFF
# #output_path = "products/color_real.tif"
# #save_rgb_geotiff(rgb, x, y, f0, f1, c0, c1, crs, output_path)
import imageio
import matplotlib.pyplot as plt

# 1. Define las fechas
fechas = [
    datetime(2024, 9, 21, 15, 0),
    datetime(2024, 9, 21, 16, 0),
    datetime(2024, 9, 21, 17, 0),
    datetime(2024, 9, 21, 18, 0),
    datetime(2024, 9, 21, 19, 0),
    datetime(2024, 9, 21, 20, 0),
    datetime(2024, 9, 21, 21, 0),
    datetime(2024, 9, 21, 22, 0),
    datetime(2024, 9, 21, 23, 0),
    datetime(2024, 9, 22, 0, 0),
    datetime(2024, 9, 22, 1, 0),
]

imagenes_rgb = []

for fecha in fechas:
    img = ABIImage(fecha, "ABI-L1b-RadF", bands)
    img.download()
    img.open()
    crs, x, y = img.get_projection_params()
    f0, f1, c0, c1 = img.get_bbox_indices(-28, -36, -66, -61)
    processor = RGBProcessor(abi_image=img, recipes=recipes, recorte=(f0, f1, c0, c1))
    processor.generate_all()
    rgb = processor.get_product(
        "Temperatura de Fuego"
    )  # Cambia según el producto deseado
    # extent = (x[c0], x[c1], y[f1], y[f0])
    # plot_rgb_with_coastlines(rgb, extent, crs,
    #     title="RGB Color Real",
    #     provincias_shp="shapefiles/provincias/linea_de_limite_070111Line.shp",
    #     show=True)
    imagenes_rgb.append(
        (rgb, x, y, crs)
    )  # Guarda también x, y, crs si quieres usar extent

# 4. Crear animación GIF
frames = []
for rgb, x, y, crs in imagenes_rgb:
    fig, ax = plt.subplots(figsize=(6, 6))
    extent = (x[c0], x[c1], y[f1], y[f0])
    ax.imshow(rgb, extent=extent, origin="upper")
    ax.set_title("RGB Color Real")
    ax.axis("off")
    fig.canvas.draw()
    frame = np.array(fig.canvas.renderer.buffer_rgba())
    frames.append(frame)
    plt.close(fig)

# Guardar como GIF
imageio.mimsave("animacion_rgb.mp4", frames, fps=2)  # duration en segundos por frame
