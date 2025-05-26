
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj import CRS as PyCRS

src_path = "output_rgb.tif"
dst_path = "output_rgb_epsg4326.tif"

with rasterio.open(src_path) as src:
    dst_crs = "EPSG:4326"  # WGS84 lat/lon
    transform, width, height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds
    )
    
    kwargs = src.meta.copy()
    kwargs.update({
        "crs": dst_crs,
        "transform": transform,
        "width": width,
        "height": height,
    })

    with rasterio.open(dst_path, "w", **kwargs) as dst:
        for i in range(1, src.count + 1):
            reproject(
                source=rasterio.band(src, i),
                destination=rasterio.band(dst, i),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest
            )