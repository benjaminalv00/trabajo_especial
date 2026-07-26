from types import SimpleNamespace

import numpy as np

from goes_rgb.helpers import save_band_geotiff, save_rgb_geotiff


def _fake_crs():
    return SimpleNamespace(proj4_init="+proj=geos +lon_0=-75 +h=35786023")


def test_save_rgb_geotiff_writes_three_bands(tmp_path):
    imagen_rgb = np.array(
        [
            [[0.0, 0.5, 1.0], [0.25, 0.5, 0.75]],
            [[1.0, 0.25, 0.0], [0.5, 0.75, 0.25]],
        ]
    )
    x = np.array([10.0, 20.0, 30.0])
    y = np.array([40.0, 30.0, 20.0])
    output_path = tmp_path / "rgb.tif"

    save_rgb_geotiff(
        imagen_RGB=imagen_rgb,
        x=x,
        y=y,
        f0=0,
        f1=2,
        c0=0,
        c1=2,
        crs=_fake_crs(),
        output_path=output_path,
    )

    assert output_path.exists()

    import rasterio

    writer = rasterio._last_writer
    assert writer.kwargs["driver"] == "GTiff"
    assert writer.kwargs["count"] == 3
    assert writer.kwargs["dtype"] == "uint8"
    assert writer.kwargs["crs"].proj4_init == _fake_crs().proj4_init
    assert len(writer.writes) == 3
    assert writer.writes[0][0] == 1
    assert writer.writes[1][0] == 2
    assert writer.writes[2][0] == 3


def test_save_band_geotiff_writes_single_band(tmp_path):
    band = np.array([[1.5, 2.5], [3.5, 4.5]], dtype=float)
    x = np.array([10.0, 20.0, 30.0])
    y = np.array([40.0, 30.0, 20.0])
    output_path = tmp_path / "band.tif"

    save_band_geotiff(
        band_array=band,
        x=x,
        y=y,
        f0=0,
        f1=2,
        c0=0,
        c1=2,
        crs=_fake_crs(),
        output_path=output_path,
    )

    assert output_path.exists()

    import rasterio

    writer = rasterio._last_writer
    assert writer.kwargs["driver"] == "GTiff"
    assert writer.kwargs["count"] == 1
    assert writer.kwargs["dtype"] == "float32"
    assert writer.kwargs["crs"].proj4_init == _fake_crs().proj4_init
    assert len(writer.writes) == 1
    assert writer.writes[0][0] == 1
