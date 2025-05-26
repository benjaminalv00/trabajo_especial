import numpy as np
from pyproj import Transformer
from rasterio.transform import from_bounds,from_origin
from rasterio.crs import CRS
import rasterio

def realce_gama(V, A, gama, Vmin, Vmax):
    Vaux = (V - Vmin) / (Vmax - Vmin)
    Vaux[Vaux<0] = 0
    Vaux[Vaux>1] = 1
    Vout = A * Vaux**gama
    return Vout


def get_pixel_indices_from_latlon_bbox(lat_min, lat_max, lon_min, lon_max, x, y, crs_geo):
    # Crear transformador de WGS84 → proyección geoestacionaria
    transformer = Transformer.from_crs("EPSG:4326", crs_geo, always_xy=True)

    # Transformar las esquinas del bounding box (en lon/lat) a x/y (en metros)
    x0, y0 = transformer.transform(lon_min, lat_max)  # esquina superior izquierda
    x1, y1 = transformer.transform(lon_max, lat_min)  # esquina inferior derecha

    # Buscar índices más cercanos en los arrays x e y
    c0 = np.argmin(np.abs(x - x0))
    c1 = np.argmin(np.abs(x - x1))
    f0 = np.argmin(np.abs(y - y0))
    f1 = np.argmin(np.abs(y - y1))

    # Asegurar orden correcto (de menor a mayor)
    f0, f1 = sorted([f0, f1])
    c0, c1 = sorted([c0, c1])

    return f0, f1, c0, c1

def save_rgb_geotiff(imagen_RGB, x, y, f0, f1, c0, c1, crs, output_path):
    # Convertir a uint8 y transponer a (3, height, width)
    rgb_array = (imagen_RGB * 255).astype("uint8").transpose(2, 0, 1)

    height, width = rgb_array.shape[1:]
    crs_rio = CRS.from_string(crs.proj4_init)
    img_extent_recorte = (x[c0], y[f1], x[c1], y[f0])
    transform = from_bounds(*img_extent_recorte, width=width, height=height)
    pixel_width = (x[c1] - x[c0]) / width
    pixel_height = (y[f0] - y[f1]) / height  # cuidado con el signo
    transform = from_origin(x[c0], y[f0], pixel_width, pixel_height)

    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype="uint8",
        crs=crs_rio,
        transform=transform,
    ) as dst:
        dst.write(rgb_array[0], 1)
        dst.write(rgb_array[1], 2)
        dst.write(rgb_array[2], 3)
