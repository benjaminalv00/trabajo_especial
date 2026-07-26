from types import SimpleNamespace

import numpy as np

import goes_rgb.helpers as helpers
from goes_rgb.helpers import band_is_emissive, realce_percentil, realce_gama


def test_realce_percentil_returns_zeros_for_all_nan():
    arr = np.array([[np.nan, np.nan], [np.nan, np.nan]])

    out = realce_percentil(arr)

    assert np.array_equal(out, np.zeros_like(arr))


def test_realce_percentil_scales_and_clips_values():
    arr = np.array([0.0, 5.0, 10.0, 20.0])

    out = realce_percentil(arr, p=0)

    assert out.shape == arr.shape
    assert np.isclose(out[0], 0.0)
    assert np.isclose(out[-1], 1.0)
    assert np.all((out >= 0) & (out <= 1))


def test_realce_gama_clips_to_unit_interval():
    arr = np.array([-10.0, 0.0, 5.0, 10.0, 30.0])

    out = realce_gama(arr, A=1, gama=1, Vmin=0, Vmax=10)

    assert np.isclose(out[0], 0.0)
    assert np.isclose(out[1], 0.0)
    assert np.isclose(out[3], 1.0)
    assert np.isclose(out[4], 1.0)
    assert np.all((out >= 0) & (out <= 1))


def test_band_is_emissive_matches_goes_channels():
    assert band_is_emissive("C07")
    assert band_is_emissive("C15")
    assert not band_is_emissive("C02")


def test_realce_p_scales_and_clips_values():
    vec = np.array([0.0, 5.0, 10.0, 20.0])

    out = helpers.realce_p(vec, p=25)

    assert out.shape == vec.shape
    assert np.isclose(out[0], 0.0)
    assert np.isclose(out[-1], 1.0)
    assert np.all((out >= 0) & (out <= 1))


def test_calibrate_imag_uses_temperature_branch():
    imagen = np.array([[10.0, 12.0], [14.0, 16.0]])
    metadato = {
        "band_id": "7",
        "planck_fk1": SimpleNamespace(values=1.0),
        "planck_fk2": SimpleNamespace(values=2.0),
        "planck_bc1": SimpleNamespace(values=3.0),
        "planck_bc2": SimpleNamespace(values=4.0),
    }

    out = helpers.calibrate_imag(imagen, metadato)

    expected = (2.0 / (np.log((1.0 / imagen) + 1)) - 3.0) / 4.0 - 273.15
    assert np.allclose(out, expected)


def test_calibrate_imag_uses_reflectance_branch():
    imagen = np.array([[1.0, 2.0], [3.0, 4.0]])
    metadato = {
        "band_id": "1",
        "kappa0": SimpleNamespace(data=0.5),
    }

    out = helpers.calibrate_imag(imagen, metadato, U="Ref")

    assert np.allclose(out, imagen * 0.5)


def test_calibrate_imag_radiance_branch_is_not_implemented():
    imagen = np.array([[1.0]])
    metadato = {"band_id": "1"}

    try:
        helpers.calibrate_imag(imagen, metadato, U="Rad")
    except NotImplementedError as exc:
        assert "Radiancia" in str(exc)
    else:
        raise AssertionError("Se esperaba NotImplementedError")


def test_get_pixel_indices_from_latlon_bbox_uses_closest_coordinates():
    x = np.array([0.0, 5.0, 10.0, 15.0])
    y = np.array([10.0, 5.0, 0.0, -5.0])
    crs_geo = SimpleNamespace()

    f0, f1, c0, c1 = helpers.get_pixel_indices_from_latlon_bbox(
        lat_min=-10,
        lat_max=8,
        lon_min=4,
        lon_max=12,
        x=x,
        y=y,
        crs_geo=crs_geo,
    )

    assert (f0, f1, c0, c1) == (0, 3, 1, 2)


def test_resample_to_shape_changes_shape():
    source = np.array([[1.0, 2.0], [3.0, 4.0]])

    out = helpers.resample_to_shape(source, (4, 4))

    assert out.shape == (4, 4)


def test_save_rgb_geotiff_and_band_geotiff_touch_output_files(tmp_path):
    crs = SimpleNamespace(proj4_init="+proj=geos")
    x = np.array([10.0, 20.0, 30.0])
    y = np.array([40.0, 30.0, 20.0])

    rgb_path = tmp_path / "rgb.tif"
    band_path = tmp_path / "band.tif"

    helpers.save_rgb_geotiff(
        np.ones((2, 2, 3), dtype=float),
        x,
        y,
        0,
        1,
        0,
        1,
        crs,
        rgb_path,
    )
    helpers.save_band_geotiff(
        np.ones((2, 2), dtype=float),
        x,
        y,
        0,
        1,
        0,
        1,
        crs,
        band_path,
    )

    import rasterio

    assert rgb_path.exists()
    assert band_path.exists()
    assert rasterio._last_writer.kwargs["driver"] == "GTiff"
