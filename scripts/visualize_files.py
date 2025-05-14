# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from goes_rgb.reader import open_goes_file, get_radiance_array
from goes_rgb.visualization import plot_radiance
import glob

# Buscar todos los archivos NetCDF en data/
archivos = glob.glob("data/*.nc")
if not archivos:
    print("No se encontraron archivos en la carpeta data/")
else:
    for path in archivos:
        print(f"Visualizando: {path}")
        try:
            ds = open_goes_file(path)
            rad = get_radiance_array(ds)
            plot_radiance(rad, titulo=path.split("/")[-1])
        except Exception as e:
            print(f"Error al procesar {path}: {e}")
