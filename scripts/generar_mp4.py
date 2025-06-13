from datetime import datetime,timedelta
from goes_rgb.core import ABIImage
from goes_rgb.rgb_processor import RGBProcessor
from goes_rgb.rgb_recipes import microfisica_nocturna, true_color, fire_temperature
from goes_rgb.visualization import plot_rgb_with_coastlines
from goes_rgb.helpers import save_rgb_geotiff
import numpy as np
import imageio
import matplotlib.pyplot as plt

bands = ["C07", "C06", "C05"]
recipes = {
    # "Microfisica Nocturna": microfisica_nocturna(),
    # "Color Real": true_color(),
    "Temperatura de Fuego": fire_temperature(),
}

# 1. Definimos las fechas
inicio = datetime(2024, 9, 21, 15, 0)
fin = datetime(2024, 9, 22, 15, 0)
delta = timedelta(minutes=60)  # Cambia a 10, 15, 60 según lo que necesites

fechas = []
actual = inicio
while actual <= fin:
    fechas.append(actual)
    actual += delta

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
imageio.mimsave("animacion_rgb.gif", frames, fps=1)  # duration en segundos por frame
