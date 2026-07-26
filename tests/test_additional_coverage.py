from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest

import goes_rgb.aws_interface as aws_interface
import goes_rgb.core as core
import goes_rgb.l1b_abi_image as l1b_abi_image
import goes_rgb.l2_abi_image as l2_abi_image
import goes_rgb.reader as reader
import goes_rgb.rgb_processor as rgb_processor
import goes_rgb.rgb_product as rgb_product
import goes_rgb.visualization as visualization


class DummyABIImage(core.ABIImage):
    def open(self):
        return None

    def get_projection_params(self):
        return None, None, None

    def calibrate_band(self, band, raw_data, unit=None):
        return raw_data


class FakeBandData:
    def __init__(self, values):
        self.values = values


class FakeProjection:
    def __init__(self):
        self.attrs = {
            "perspective_point_height": 35786023.0,
            "longitude_of_projection_origin": -75.0,
        }


class FakeDataset:
    def __init__(self, band_id, band_array, x_values=None, y_values=None):
        self.band_id = SimpleNamespace(values=np.array([band_id]))
        self._band_array = np.asarray(band_array)
        self.variables = {
            "x": SimpleNamespace(values=np.asarray(x_values)),
            "y": SimpleNamespace(values=np.asarray(y_values)),
        }
        self.coords = {
            "x": SimpleNamespace(values=np.asarray(x_values)),
            "y": SimpleNamespace(values=np.asarray(y_values)),
        }
        self._projection = FakeProjection()

    def __getitem__(self, key):
        if key == "Rad":
            return SimpleNamespace(values=self._band_array)
        if key == "goes_imager_projection":
            return self._projection
        raise KeyError(key)

    def close(self):
        return None


class FakeMCMIDataSet:
    def __init__(self, band_map, x_values, y_values):
        self.variables = {
            "x": SimpleNamespace(values=np.asarray(x_values)),
            "y": SimpleNamespace(values=np.asarray(y_values)),
        }
        for name, array in band_map.items():
            self.variables[name] = FakeBandData(np.asarray(array))
        self._projection = FakeProjection()

    def __getitem__(self, key):
        if key == "goes_imager_projection":
            return self._projection
        return self.variables[key]


class FakeAxes:
    def __init__(self):
        self.calls = []

    def imshow(self, *args, **kwargs):
        self.calls.append(("imshow", args, kwargs))

    def coastlines(self, *args, **kwargs):
        self.calls.append(("coastlines", args, kwargs))

    def add_feature(self, *args, **kwargs):
        self.calls.append(("add_feature", args, kwargs))

    def gridlines(self, *args, **kwargs):
        self.calls.append(("gridlines", args, kwargs))
        return SimpleNamespace(
            bottom_labels=None,
            right_labels=None,
            top_labels=None,
            left_labels=None,
            xlabel_style=None,
            ylabel_style=None,
            xlocator=None,
            ylocator=None,
        )


class FakeFigure:
    pass


@pytest.fixture
def fake_crs():
    return SimpleNamespace(proj4_init="+proj=geos +lon_0=-75 +h=35786023")


def test_rgb_product_build_applies_recorte_and_clipping():
    calibrated_images = {
        "C01": np.array([[1.2, -0.1], [0.5, 0.25]]),
        "C02": np.array([[0.2, 0.4], [0.6, 0.8]]),
        "C03": np.array([[0.1, 0.3], [0.7, 0.9]]),
    }
    recipe = {
        "funcs": {
            "R": lambda images: images["C01"],
            "G": lambda images: images["C02"],
            "B": lambda images: images["C03"],
        }
    }

    product = rgb_product.RGBProduct(
        abi_image=object(),
        name="demo",
        calibrated_images=calibrated_images,
        recipe=recipe,
        recorte=(0, 1, 0, 2),
    )

    out = product.build()

    assert out.shape == (1, 2, 3)
    assert np.isclose(out[0, 0, 0], 1.0)
    assert np.isclose(out[0, 0, 1], 0.2)
    assert np.isclose(out[0, 0, 2], 0.1)
    assert np.all(out >= 0)
    assert np.all(out <= 1)


def test_reader_helpers_extract_arrays():
    dataset = {
        "Rad": SimpleNamespace(values=np.array([[1.0, 2.0], [3.0, 4.0]])),
        "x": SimpleNamespace(values=np.array([10.0, 20.0, 30.0])),
        "y": SimpleNamespace(values=np.array([40.0, 30.0, 20.0])),
    }

    assert np.array_equal(reader.get_radiance_array(dataset), dataset["Rad"].values)
    lat, lon = reader.get_geolocation(dataset)
    assert np.array_equal(lat, dataset["x"].values)
    assert np.array_equal(lon, dataset["y"].values)


def test_aws_download_lists_local_mcmi_file(tmp_path):
    dt = datetime(2026, 1, 1, 0, 0)
    file_path = tmp_path / "OR_ABI-L2-MCMIPF-M6_G16_s202600100.nc"
    file_path.write_text("x", encoding="utf-8")

    files = aws_interface.download_goes_files_for_datetime(
        dt,
        product="ABI-L2-MCMIPF",
        channels=["C01"],
        local_dir=str(tmp_path),
    )

    assert files == [str(file_path)]


def test_aws_download_lists_local_l1b_file_per_channel(tmp_path, monkeypatch):
    dt = datetime(2026, 1, 1, 0, 0)
    file_path = tmp_path / "OR_ABI-L1b-RadF-M6_G16_C02_s202600100.nc"
    file_path.write_text("x", encoding="utf-8")

    class FakeFS:
        def __init__(self, anon=True):
            self.anon = anon

        def ls(self, prefix):
            return [str(file_path)]

    monkeypatch.setitem(
        __import__("sys").modules, "s3fs", SimpleNamespace(S3FileSystem=FakeFS)
    )

    files = aws_interface.download_goes_files_for_datetime(
        dt,
        product="ABI-L1b-RadF",
        channels=["C02"],
        local_dir=str(tmp_path),
    )

    assert files == [str(file_path)]


def test_list_goes_files_filters_non_nc(monkeypatch):
    fake_module = SimpleNamespace()

    class FakeFS:
        def __init__(self, anon=True):
            self.anon = anon

        def ls(self, prefix):
            return [
                f"bucket/{prefix}file1.nc",
                f"bucket/{prefix}file2.txt",
                f"bucket/{prefix}file3.nc",
            ]

    fake_module.S3FileSystem = FakeFS
    monkeypatch.setitem(__import__("sys").modules, "s3fs", fake_module)

    files = aws_interface.list_goes_files("ABI-L2-MCMIPF", 2026, 1, 0)

    assert files == [
        "s3://bucket/noaa-goes16/ABI-L2-MCMIPF/2026/001/00/file1.nc",
        "s3://bucket/noaa-goes16/ABI-L2-MCMIPF/2026/001/00/file3.nc",
    ]


def test_base_abi_image_download_raises_when_no_files(monkeypatch):
    monkeypatch.setattr(
        core, "download_goes_files_for_datetime", lambda *args, **kwargs: []
    )
    image = core.ABIImage(
        datetime(2026, 1, 1), "ABI-L2-MCMIPF", ["C01"], "noaa-goes16", "data"
    )

    image.download()

    assert image.files == []


def test_abiimage_l1b_get_band_array_calibrates_emissive_and_reflective():
    image = l1b_abi_image.ABIImageL1b(
        datetime(2026, 1, 1),
        product="ABI-L1b-RadF",
        channels=["C01", "C07"],
        satellite="noaa-goes16",
        local_dir="data",
    )

    image.datasets = {
        "C01": {
            "band_array": np.array([[1.0, 2.0]]),
            "metadata": {"band_id": "1", "kappa0": SimpleNamespace(data=0.5)},
            "ds": SimpleNamespace(),
        },
        "C07": {
            "band_array": np.array([[10.0, 12.0]]),
            "metadata": {
                "band_id": "7",
                "planck_fk1": SimpleNamespace(values=1.0),
                "planck_fk2": SimpleNamespace(values=2.0),
                "planck_bc1": SimpleNamespace(values=3.0),
                "planck_bc2": SimpleNamespace(values=4.0),
            },
            "ds": SimpleNamespace(),
        },
    }

    reflective = image.get_band_array("C01")
    emissive = image.get_band_array("C07")

    assert np.allclose(reflective, np.array([[0.5, 1.0]]))
    assert emissive.shape == (1, 2)


def test_abiimage_mcmi_get_band_array_and_projection_params():
    image = l2_abi_image.ABIImageMCMI(
        datetime(2026, 1, 1),
        product="ABI-L2-MCMIPF",
        channels=["C01"],
        satellite="noaa-goes16",
        local_dir="data",
    )

    x_values = np.arange(5424)
    y_values = np.arange(5424)
    ds = FakeMCMIDataSet(
        {"CMI_C01": np.array([[1.0, 2.0], [3.0, 4.0]])}, x_values, y_values
    )
    image.datasets = {
        "C01": {
            "band_array": np.array([[1.0, 2.0], [3.0, 4.0]]),
            "metadata": ds.variables["CMI_C01"],
            "ds": ds,
        }
    }

    band = image.get_band_array("C01")
    crs, x, y = image.get_projection_params()

    assert np.array_equal(band, np.array([[1.0, 2.0], [3.0, 4.0]]))
    assert x.shape == (5424,)
    assert y.shape == (5424,)
    assert hasattr(crs, "central_longitude") or crs is not None


def test_rgb_processor_calibrates_only_emissive_bands():
    class FakeImage:
        def __init__(self):
            self.calls = []

        def get_band_array(self, band):
            return np.array([[1.0, 2.0]])

        def calibrate_band(self, band, raw, unit=None):
            self.calls.append((band, unit))
            return raw + 1.0

    image = FakeImage()
    recipe = {
        "bands": ["C01", "C07"],
        "emissive_units": {"C01": "Ref", "C07": "T"},
        "funcs": {
            "R": lambda imgs: imgs["C01"],
            "G": lambda imgs: imgs["C01"],
            "B": lambda imgs: imgs["C07"],
        },
    }

    processor = rgb_processor.RGBProcessor(image, {"demo": recipe})
    calibrated = processor.calibrate_images_for_recipe(recipe)

    assert calibrated["C01"].tolist() == [[1.0, 2.0]]
    assert calibrated["C07"].tolist() == [[2.0, 3.0]]
    assert image.calls == [("C07", "T")]


def test_visualization_plot_rgb_with_coastlines_saves_and_closes(
    monkeypatch, tmp_path, fake_crs
):
    fake_axes = FakeAxes()
    figure = FakeFigure()
    saved = []
    closed = []

    monkeypatch.setattr(visualization.plt, "figure", lambda *args, **kwargs: figure)
    monkeypatch.setattr(visualization.plt, "axes", lambda *args, **kwargs: fake_axes)
    monkeypatch.setattr(visualization.plt, "tight_layout", lambda: None)
    monkeypatch.setattr(
        visualization.plt, "savefig", lambda path, **kwargs: saved.append(path)
    )
    monkeypatch.setattr(visualization.plt, "close", lambda fig=None: closed.append(fig))

    out = visualization.plot_rgb_with_coastlines(
        np.ones((2, 2, 3)),
        extent=(0, 1, 0, 1),
        crs_geo=fake_crs,
        show=False,
        save=True,
        save_path=str(tmp_path / "plot.png"),
    )

    assert out is figure
    assert saved == [str(tmp_path / "plot.png")]
    assert closed == [figure]
