import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj import CRS as PyCRS


def reproject_geotiff(src_path, dst_path, dst_crs, resampling_method=Resampling.bilinear):
    """
    Reproyecta un archivo GeoTIFF a un sistema de coordenadas diferente.
    
    Parámetros:
    - src_path: ruta del archivo GeoTIFF de entrada
    - dst_path: ruta del archivo GeoTIFF de salida
    - dst_crs: sistema de coordenadas de destino (ej: "EPSG:4326", "EPSG:3857")
    - resampling_method: método de remuestreo (Resampling.nearest, .bilinear, .cubic, etc.)
    """
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )

        kwargs = src.meta.copy()
        kwargs.update(
            {
                "crs": dst_crs,
                "transform": transform,
                "width": width,
                "height": height,
            }
        )

        with rasterio.open(dst_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=resampling_method,
                )
    print(f"Reproyección completada: {dst_path}")


def reproject_to_web_mercator(src_path, dst_path=None):
    """
    Reproyecta a Web Mercator (EPSG:3857).
    Usado en Google Maps, OpenStreetMap y la mayoría de mapas web.
    
    Parámetros:
    - src_path: ruta del archivo GeoTIFF de entrada
    - dst_path: ruta del archivo de salida (opcional, genera nombre automático)
    """
    if dst_path is None:
        dst_path = src_path.replace(".tif", "_web_mercator.tif")
    
    reproject_geotiff(src_path, dst_path, "EPSG:3857")
    return dst_path


def reproject_to_world_mercator(src_path, dst_path=None):
    """
    Reproyecta a World Mercator (EPSG:3395).
    Proyección Mercator estándar/clásica.
    
    Parámetros:
    - src_path: ruta del archivo GeoTIFF de entrada
    - dst_path: ruta del archivo de salida (opcional, genera nombre automático)
    """
    if dst_path is None:
        dst_path = src_path.replace(".tif", "_world_mercator.tif")
    
    reproject_geotiff(src_path, dst_path, "EPSG:3395")
    return dst_path


def reproject_to_gauss_kruger_argentina(src_path, dst_path=None, faja=None):
    """
    Reproyecta a sistema Gauss-Krüger Argentina.
    
    Parámetros:
    - src_path: ruta del archivo GeoTIFF de entrada
    - dst_path: ruta del archivo de salida (opcional, genera nombre automático)
    - faja: número de faja (1-7), si es None se detecta automáticamente según el extent
    
    Fajas Gauss-Krüger Argentina:
    - Faja 1 (EPSG:22171): 72°W - centrada en Buenos Aires/centro-este
    - Faja 2 (EPSG:22172): 69°W - centrada en Mendoza/oeste
    - Faja 3 (EPSG:22173): 66°W - centrada en región de Cuyo/centro-oeste
    - Faja 4 (EPSG:22174): 63°W - región noreste
    - Faja 5 (EPSG:22175): 60°W - región este/Misiones
    - Faja 6 (EPSG:22176): 57°W - región atlántica
    - Faja 7 (EPSG:22177): 54°W - región patagónica sur/este
    """
    if faja is None:
        # Detectar faja automáticamente según el centro del extent
        with rasterio.open(src_path) as src:
            bounds = src.bounds
            # Convertir bounds a lat/lon si no lo están
            if src.crs != "EPSG:4326":
                from rasterio.warp import transform_bounds
                bounds = transform_bounds(src.crs, "EPSG:4326", *bounds)
            
            # Calcular longitud central
            lon_center = (bounds[0] + bounds[2]) / 2
            
            # Seleccionar faja según longitud
            if lon_center >= -70.5:
                faja = 1  # 72°W
            elif lon_center >= -67.5:
                faja = 2  # 69°W
            elif lon_center >= -64.5:
                faja = 3  # 66°W
            elif lon_center >= -61.5:
                faja = 4  # 63°W
            elif lon_center >= -58.5:
                faja = 5  # 60°W
            elif lon_center >= -55.5:
                faja = 6  # 57°W
            else:
                faja = 7  # 54°W
            
            print(f"Faja detectada automáticamente: {faja} (longitud central: {lon_center:.2f}°)")
    
    if faja not in range(1, 8):
        raise ValueError(f"Faja debe ser entre 1 y 7, se recibió: {faja}")
    
    epsg_code = f"EPSG:2217{faja}"
    
    if dst_path is None:
        dst_path = src_path.replace(".tif", f"_gauss_kruger_faja{faja}.tif")
    
    reproject_geotiff(src_path, dst_path, epsg_code)
    return dst_path


# Ejemplo de uso:
if __name__ == "__main__":
    src_path = "output_rgb.tif"
    
    # Opción 1: Web Mercator (para mapas web)
    reproject_to_web_mercator(src_path)
    
    # Opción 2: World Mercator (proyección estándar)
    reproject_to_world_mercator(src_path)
    
    # Opción 3: Gauss-Krüger Argentina (detección automática de faja)
    reproject_to_gauss_kruger_argentina(src_path)
    
    # Opción 4: Gauss-Krüger con faja específica
    reproject_to_gauss_kruger_argentina(src_path, faja=1)
    
    # Opción 5: Reproyección personalizada a cualquier CRS
    reproject_geotiff(src_path, "output_rgb_wgs84.tif", "EPSG:4326")
