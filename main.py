from datetime import datetime
from goes_rgb.core import ABIImage
from goes_rgb.rgb_processor import RGBProcessor
from goes_rgb.rgb_recipes import microfisica_nocturna, true_color
from goes_rgb.visualization import plot_rgb_with_coastlines
# Instanciar imagen ABI
full_bands = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C13", "C14", "C15"]
#bands = ['C07','C06','C05']
#bands = ['C03', 'C02', 'C01']  # Bandas para el producto RGB Color Real
#bands = ['C15', 'C13', 'C07']  # Bandas para el producto RGB Microfisica Nocturna
#img = ABIImage(datetime(2024, 9, 21, 7, 0), "ABI-L1b-RadF", full_bands)

img = ABIImage(datetime(2018, 12, 13, 7, 0), "ABI-L1b-RadF", full_bands)

img.download()
img.open()

# productos RGB seleccionados
recipes = {
    #"Microfisica Nocturna": microfisica_nocturna(),
    "Color Real": true_color(),
}

# Obtener parámetros de proyección
crs, x, y = img.get_projection_params()

# Recorte por lat/lon
f0, f1, c0, c1 = img.get_bbox_indices(-18.6, -56.45, -79.79, -50.0)
processor = RGBProcessor(abi_image=img, recipes=recipes)
processor.generate_all()
# Acceder al producto
rgb = processor.get_product("Microfisica Nocturna")
# Visualizar
extent = (x[c0], x[c1], y[f1], y[f0])

plot_rgb_with_coastlines(rgb, extent, crs,
    title="RGB Microfisica Nocturna",
    provincias_shp="shapefiles/provincias/linea_de_limite_070111Line.shp",
    show=True)
