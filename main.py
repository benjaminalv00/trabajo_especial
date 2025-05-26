# Vamos a generar un producto RGB de microfisica diurna 

from datetime import datetime
from goes_rgb.aws_interface import *
from goes_rgb.reader import *
from goes_rgb.helpers import *
from goes_rgb.processor import *
from goes_rgb.visualization import *
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs  # Plot maps
import cartopy.feature as cfeature
from pyproj import Proj, transform


# Primero, vamos a descargar los archivos GOES para una fecha y hora especifica
archivos = download_goes_files_for_datetime(datetime(2018, 12, 13, 7, 0),channels=["C07","C15","C13"],product="ABI-L1b-RadF",satellite="noaa-goes16",local_dir="data")
# Listar los archivos descargados
print("Archivos descargados:")
for archivo in archivos:    
    print(archivo)

imagenobj7 = open_goes_file(archivos[0])
imagenobj15 = open_goes_file(archivos[1])
imagenobj13 = open_goes_file(archivos[2])

metadato7 = imagenobj7.variables
metadato15 = imagenobj15.variables
metadato13 = imagenobj13.variables

########################################ES IGUAL PARA LAS 3 BANDAS ################
proyeccion=metadato13['goes_imager_projection'].attrs
altura=proyeccion['perspective_point_height']
semieje_may=proyeccion['semi_major_axis']
semieje_men=proyeccion['semi_minor_axis']
lon_cen=proyeccion['longitude_of_projection_origin']


x = imagenobj13.coords['x'].values * altura  
y = imagenobj13.coords['y'].values * altura

pol=semieje_may*altura/(semieje_may+altura)
ecu=semieje_men*altura/(semieje_may+altura)


# Definir la proyección geostacionaria
crs = ccrs.Geostationary(central_longitude=lon_cen, satellite_height=altura)#proyeccion geoestacionaria para Goes16


#### Recortes en lat/lon img original
# lat_ini, lat_fin = -18.6, -56.45
# lon_ini, lon_fin = -79.79, -50

### Recortes en lat/lon cordoba
lat_ini, lat_fin = -29.3, -35.5
lon_ini, lon_fin = -60.5, -66.46


f0_from_latlon, f1_from_latlon, c0_from_latlon, c1_from_latlon = get_pixel_indices_from_latlon_bbox(lat_ini, lat_fin, lon_ini, lon_fin, x, y, crs)

#print(f0_from_latlon, f1_from_latlon, c0_from_latlon, c1_from_latlon)
imagen13 = get_radiance_array(imagenobj13) #metadato13['Rad'][:].data
imagen15 = get_radiance_array(imagenobj15) #metadato15['Rad'][:].data
imagen7 = get_radiance_array(imagenobj7) #metadato7['Rad'][:].data


imag_calibrate13 = calibrate_imag(imagen13[f0_from_latlon:f1_from_latlon, c0_from_latlon:c1_from_latlon], metadato13)
imag_calibrate15 = calibrate_imag(imagen15[f0_from_latlon:f1_from_latlon, c0_from_latlon:c1_from_latlon], metadato15)
imag_calibrate7 =calibrate_imag(imagen7[f0_from_latlon:f1_from_latlon, c0_from_latlon:c1_from_latlon], metadato7)

[filas,columnas] = imag_calibrate7.shape

imagen_RGB=np.zeros([filas,columnas,3])

red_imagen = imag_calibrate15 - imag_calibrate13
green_imagen = imag_calibrate13 - imag_calibrate7
blue_imagen = imag_calibrate13

realce_red = realce_gama(red_imagen, 1, 1, -6.7, 2.6)
realce_green = realce_gama(green_imagen, 1, 1, -3.1, 5.2)
realce_blue = realce_gama(blue_imagen, 1,  1, -29.6, 19.5)


imagen_RGB[:,:,0] = realce_red
imagen_RGB[:,:,1] = realce_green
imagen_RGB[:,:,2] = realce_blue

output_path = os.path.join("products", "Microfisica_nocturna.tif")

# Guardamos en GeoTIFF
save_rgb_geotiff(imagen_RGB, x, y, f0_from_latlon, f1_from_latlon, c0_from_latlon, c1_from_latlon, crs, output_path)
# Ploteamos
img_plot_extent = (x[c0_from_latlon], x[c1_from_latlon], y[f1_from_latlon], y[f0_from_latlon]) # (xmin, xmax, ymin, ymax)
plot_rgb_with_coastlines(imagen_RGB, img_plot_extent, crs,
                         title="RGB Microfisica Nocturna CBA",
                         provincias_shp="shapefiles/provincias/linea_de_limite_070111Line.shp",
                         show=True
                         )
