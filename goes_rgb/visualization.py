# goes_rgb/visualization.py
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from cartopy.feature import ShapelyFeature


def plot_radiance(radiancia, titulo="Radiancia", cmap="gray"):
    plt.figure(figsize=(8, 6))
    plt.imshow(radiancia, cmap=cmap)
    plt.title(titulo)
    plt.axis("off")
    plt.colorbar(label="Radiancia")
    plt.show()

def plot_rgb_with_coastlines(imagen_rgb, extent, crs_geo, title="Imagen GOES",provincias_shp=None,show=True):
    """
    Muestra una imagen RGB con líneas de costa y líneas de latitud/longitud.

    Parámetros:
    - imagen_rgb: array (H, W, 3)
    - extent: (xmin, xmax, ymin, ymax) en coordenadas del CRS de la imagen
    - crs_geo: instancia de cartopy.crs.Geostationary
    - title: título opcional del gráfico
    """
    fig = plt.figure(figsize=(10, 10))
    ax = plt.axes(projection=crs_geo)

    ax.imshow(imagen_rgb, origin='upper', extent=extent, transform=crs_geo,vmin=0, vmax=1)

    ax.coastlines(resolution='50m', color='red')
    # Límites de países (mismo color que provincias)
    ax.add_feature(cfeature.BORDERS, edgecolor='#00FF00', linewidth=1)
    
    gl = ax.gridlines(draw_labels=True, color='gray', alpha=0.8, linestyle='--', linewidth=1.5)
    gl.top_labels = False
    gl.right_labels = False

    # Agrandar los ticks de lat/lon
    gl.xlabel_style = {'size': 16}
    gl.ylabel_style = {'size': 20}

    # Agregar límites de provincias si se proporciona el shapefile
    if provincias_shp is not None:
        shp = shpreader.Reader(provincias_shp)
        provincias = ShapelyFeature(shp.geometries(), ccrs.PlateCarree(), edgecolor='#00FF00', facecolor='none', linewidth=1)
        ax.add_feature(provincias)
    
    
    
    

    plt.tight_layout()
    #plt.title(title)
    # Save plot to file en carpeta products
    output_file = os.path.join("products", f"{title}.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    if show:
        plt.show()
    else:
        print(f"Gráfico guardado en {output_file}")
