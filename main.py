from datetime import datetime
from goes_rgb.aws_interface import *
from goes_rgb.reader import *
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs  # Plot maps

# Vamos a hacer un pipeline simple de descarga de archivos GOES y posterior visualizacion
# Basandonos en el practico 6 de satelitales 

# Primero, vamos a descargar los archivos GOES para una fecha y hora especifica
download_goes_files_for_datetime(datetime(2018, 4, 6, 15),channels=["C07","C13","C15"],product="ABI-L1b-RadF",satellite="noaa-goes16",local_dir="data")

# Listar los archivos descargados
archivos = os.listdir("data")
print("Archivos descargados:")
for archivo in archivos:    
    print(archivo)


#%% Comenzando el procesamiento

for archivo in archivos:
    print ('Importando la imagen: %s' %archivo)
    imagenobj = open_goes_file(os.path.join("data",archivo))

    metadato = imagenobj.variables
    #breakpoint()
    proyeccion = imagenobj['goes_imager_projection']
    altura=proyeccion.perspective_point_height
    semieje_may = proyeccion.semi_major_axis
    semieje_men = proyeccion.semi_minor_axis
    lon_cen = proyeccion.longitude_of_projection_origin

    img_extent = (-5434894.67527,5434894.67527,-5434894.67527,5434894.67527) # De donde sale esto?
    pol = semieje_may*altura/(semieje_may+altura)
    ecu = semieje_men*altura/(semieje_may+altura)

    icanal = int(metadato['band_id'][:])
    print ('Canal %d' %icanal)

    imagen = metadato['Rad'][:].data


    # Nos salteamos la calibracion de la imagen por el momento 
    print ('Calibrando la imagen')
    if icanal >= 7:
        #Parámetros de calibracion
        fk1 = metadato['planck_fk1'].values # DN -> K
        fk2 = metadato['planck_fk2'].values
        bc1 = metadato['planck_bc1'].values
        bc2 = metadato['planck_bc2'].values


        imag_cal = (fk2 / (np.log((fk1 / imagen) + 1)) - bc1 ) / bc2 - 273.15 # K -> C
        Unit = "Temperatura de Brillo [°C]"
    else:
        raise("Not implemented yet")
        pendiente= metadato['Rad'].scale_factor
        ordenada= metadato['Rad'].add_offset
        imag_cal =imagen*pendiente+ordenada
        Unit = "Radiancia ["+metadato['Rad'].units+"]"

    # print("Graficando")

    # No plotea igual que el practico 6, no se xq 
    # plt.figure()

    crs = ccrs.Geostationary(central_longitude=lon_cen, satellite_height=altura)#proyeccion geoestacionaria para Goes16
    # ax = plt.axes(projection=crs)
    # ax.gridlines() #agrega linea de meridianos y paralelos
    # ax.coastlines(resolution='10m',color='blue') #agrega líneas de costa

    # img = plt.imshow(imagen,extent=img_extent,vmin=-100.,vmax=30.,cmap='Greys')

    # # Add a colorbar
    # plt.colorbar(img, label='Brightness Temperatures (°C)', extend='both', orientation='vertical', pad=0.05, fraction=0.05)

    # plt.show()


#%% Recortes crudos
psize = 2000 # lado de pixel de referencia en m
N = 5424 #numero de pixeles de referencia

Nx = 2500 #numero de puntos del recorte en x
Ny = 2000 #numero de puntos del recorte en x

esc = int(imag_cal.shape[0]/N)

x0 = -1700000 # Coordenada x del limite superior izquierdo en m
y0 = -100000 # Coordenada y del limite superior izquierdo en m

f0 = int((img_extent[1] - y0) / psize*esc) #fila del angulo superior izquierdo
c0 = int((img_extent[3] + x0) / psize*esc) #columna del angulo superior izquierdo
f1 = int(f0 + Nx*esc) #fila del angulo inferior derecho
c1 = int(c0 + Ny*esc) #columna del angulo inferior derecho

img_extentr=[x0,x0+Nx*psize*esc,y0-Ny*psize*esc,y0]

indf=range(f0,f1,esc)
indc=range(c0,c1,esc)
im_rec=imag_cal[indf[0]:indf[-1],indc[0]:indc[-1]]

fig, axs = plt.subplots(1, 2, figsize=(14, 6))

# Primer subplot: imagen recortada simple
img1 = axs[0].imshow(im_rec, vmin=-100., vmax=30., cmap='Greys')
axs[0].set_title("Recorte crudo")
fig.colorbar(img1, ax=axs[0], label='Brightness Temperatures (°C)', extend='both', orientation='vertical', pad=0.05, fraction=0.05)

# Segundo subplot: imagen con proyección
ax2 = plt.subplot(1, 2, 2, projection=crs)
ax2.gridlines()
ax2.coastlines(resolution='10m', color='blue')
img2 = ax2.imshow(im_rec, transform=crs, extent=img_extentr, vmin=-100., vmax=30., cmap='Greys')
fig.colorbar(img2, ax=ax2, label='Brightness Temperatures (°C)', extend='both', orientation='vertical', pad=0.05, fraction=0.05)
ax2.set_title("Recorte con proyección")

plt.tight_layout()
plt.show()



