# goes_rgb/visualization.py
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from cartopy.feature import ShapelyFeature
import matplotlib.ticker as mticker


def plot_radiance(radiancia, titulo="Radiancia", cmap="gray"):
    plt.figure(figsize=(8, 6))
    plt.imshow(radiancia, cmap=cmap)
    plt.title(titulo)
    plt.axis("off")
    plt.colorbar(label="Radiancia")
    plt.show()


def plot_rgb_with_coastlines(
    imagen_rgb,
    extent,
    crs_geo,
    title="Imagen GOES",
    provincias_shp=None,
    show=True,
    lon_interval=2,
    lat_interval=2,
    save=False,
    save_path=None,
):
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

    ax.imshow(
        imagen_rgb, origin="upper", extent=extent, transform=crs_geo, vmin=0, vmax=1
    )

    ax.coastlines(resolution="50m", color="red")
    # Límites de países (mismo color que provincias)
    ax.add_feature(cfeature.BORDERS, edgecolor="#00FF00", linewidth=1)

    gl = ax.gridlines(
        draw_labels=True, color="gray", alpha=0.8, linestyle="--", linewidth=1.5
    )
    gl.bottom_labels = True
    gl.right_labels = False
    gl.top_labels = False
    gl.left_labels = True

    # Agrandar los ticks de lat/lon
    gl.xlabel_style = {"size": 20}
    gl.ylabel_style = {"size": 20}

    # cada cuántos grados ponemos las líneas:
    import numpy as np

    gl.xlocator = mticker.FixedLocator(np.arange(-180, 181, lon_interval))
    gl.ylocator = mticker.FixedLocator(np.arange(-90, 91, lat_interval))

    # Agregar límites de provincias si se proporciona el shapefile
    if provincias_shp is not None:
        shp = shpreader.Reader(provincias_shp)
        provincias = ShapelyFeature(
            shp.geometries(),
            ccrs.PlateCarree(),
            edgecolor="#00FF00",
            facecolor="none",
            linewidth=1,
        )
        ax.add_feature(provincias)

    plt.tight_layout()
    # plt.title(title, fontsize=20)
    # Save plot to file en carpeta products
    output_file = save_path if save_path else os.path.join("products", f"{title}.png")
    # breakpoint()
    if save:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Gráfico guardado en {output_file}")
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig


def plot_band_with_coastlines(
    banda,
    extent,
    crs_geo,
    title="Banda GOES",
    provincias_shp=None,
    show=True,
    lon_interval=2,
    lat_interval=2,
    save=False,
    cmap="gray",
    save_path=None,
):
    """
    Muestra una banda (2D) con líneas de costa y líneas de latitud/longitud.

    Parámetros:
    - banda: array 2D (H, W)
    - extent: (xmin, xmax, ymin, ymax) en coordenadas del CRS de la imagen
    - crs_geo: instancia de cartopy.crs.Geostationary
    - title: título opcional del gráfico
    - provincias_shp: ruta al shapefile de provincias (opcional)
    - show: mostrar el gráfico (bool)
    - lon_interval: intervalo de líneas de longitud
    - lat_interval: intervalo de líneas de latitud
    - save: guardar el gráfico (bool)
    - cmap: colormap para la banda
    """
    fig = plt.figure(figsize=(10, 10))
    ax = plt.axes(projection=crs_geo)

    im = ax.imshow(banda, origin="upper", extent=extent, transform=crs_geo, cmap=cmap)
    ax.coastlines(resolution="50m", color="red")
    ax.add_feature(cfeature.BORDERS, edgecolor="#00FF00", linewidth=1)

    gl = ax.gridlines(
        draw_labels=True, color="gray", alpha=0.8, linestyle="--", linewidth=1.5
    )
    gl.bottom_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 20}
    gl.ylabel_style = {"size": 20}

    import numpy as np

    gl.xlocator = plt.FixedLocator(np.arange(-180, 181, lon_interval))
    gl.ylocator = plt.FixedLocator(np.arange(-90, 91, lat_interval))

    if provincias_shp is not None:
        shp = shpreader.Reader(provincias_shp)
        provincias = ShapelyFeature(
            shp.geometries(),
            ccrs.PlateCarree(),
            edgecolor="#00FF00",
            facecolor="none",
            linewidth=1,
        )
        ax.add_feature(provincias)

    plt.tight_layout()
    plt.title(title, fontsize=20)
    # cbar = plt.colorbar(im, ax=ax, orientation='vertical', fraction=0.046, pad=0.04)
    # cbar.set_label("Valor de banda", fontsize=16)

    output_file = os.path.join("products", f"{title}.png")
    if save:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Gráfico guardado en {output_file}")
    if show:
        plt.show()
    else:
        # print(f"Gráfico guardado en {output_file}")
        plt.close(fig)

    return fig
