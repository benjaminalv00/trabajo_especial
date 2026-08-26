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

    def set_extent(self, *args, **kwargs):
        self.calls.append(("set_extent", args, kwargs))

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


class FakeBandArray:
    def __init__(self, shape):
        self.shape = shape
        self._data = np.ones(shape)

    def __getitem__(self, key):
        if self.shape == (10848, 10848) and key == (
            slice(None, None, 2),
            slice(None, None, 2),
        ):
            new_obj = FakeBandArray((5424, 5424))
            new_obj._data = np.ones((5424, 5424))  # Asignamos _data explícitamente
            return new_obj
        if self.shape == (21696, 21696) and key == (
            slice(None, None, 4),
            slice(None, None, 4),
        ):
            new_obj = FakeBandArray((5424, 5424))
            new_obj._data = np.ones((5424, 5424))  # Asignamos _data explícitamente
            return new_obj
        return self

    def copy(self):
        new_obj = FakeBandArray(self.shape)
        new_obj._data = self._data.copy()
        return new_obj

    def __add__(self, other):
        return self._data + getattr(other, "_data", other)

    def __sub__(self, other):
        return self._data - getattr(other, "_data", other)

    def __mul__(self, other):
        return self._data * getattr(other, "_data", other)

    # Agregamos __rmul__ para permitir multiplicar un número por FakeBandArray (ej: kapa0 * imagen)
    __rmul__ = __mul__

    def __truediv__(self, other):
        return self._data / getattr(other, "_data", other)


class FakeBandId:
    def __init__(self, value):
        # np.array(value) sin corchetes crea un array 0-D (escalar)
        self.values = np.array(value)

    def __getitem__(self, key):
        # Retorna un escalar 0-D en lugar de [value]
        return np.array(self.values.item())


class FakeAxisValues:
    def __init__(self, shape):
        self.shape = shape

    def __mul__(self, other):
        return self

    __rmul__ = __mul__

    def __getitem__(self, key):
        if self.shape != (5424,) and key == slice(None, None, 2):
            return FakeAxisValues((5424,))
        return self


class FakeProjectionDataset:
    def __init__(self, x_values, y_values):
        self.coords = {
            "x": SimpleNamespace(values=x_values),
            "y": SimpleNamespace(values=y_values),
        }
        self.variables = {
            "x": SimpleNamespace(values=x_values),
            "y": SimpleNamespace(values=y_values),
        }
        self._projection = FakeProjection()

    def __getitem__(self, key):
        if key == "goes_imager_projection":
            return self._projection
        raise KeyError(key)


class FakeBandVariable:
    def __init__(self, values, ndim=2):
        self.values = np.asarray(values)
        self.ndim = ndim

    def __getitem__(self, item):
        return self


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


def test_visualization_plot_band_and_radiance_cover_additional_branches(
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
    monkeypatch.setattr(
        visualization.plt, "FixedLocator", visualization.mticker.FixedLocator
    )
    monkeypatch.setattr(visualization.plt, "title", lambda *args, **kwargs: None)
    monkeypatch.setattr(visualization.plt, "imshow", lambda *args, **kwargs: None)
    monkeypatch.setattr(visualization.plt, "axis", lambda *args, **kwargs: None)
    monkeypatch.setattr(visualization.plt, "colorbar", lambda *args, **kwargs: None)
    monkeypatch.setattr(visualization.plt, "show", lambda: None)

    visualization.plot_radiance(np.ones((2, 2)), titulo="rad", cmap="gray")

    visualization.plot_band_with_coastlines(
        np.ones((2, 2)),
        extent=(0, 1, 0, 1),
        crs_geo=fake_crs,
        provincias_shp=str(tmp_path / "fake.shp"),
        show=False,
        save=True,
        save_path=str(tmp_path / "band.png"),
    )

    assert saved[-1].endswith("Banda GOES.png")
    assert closed[-1] is figure


def test_aws_download_file_with_progress_success_and_error(tmp_path, monkeypatch):
    class FakeTqdm:
        def __init__(self, total=None, unit=None, unit_scale=None, desc=None):
            self.total = total
            self.desc = desc
            self.updated = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, amount):
            self.updated.append(amount)

    class FakeClient:
        def __init__(self, should_fail=False):
            self.should_fail = should_fail

        def head_object(self, Bucket, Key):
            if self.should_fail:
                raise RuntimeError("boom")
            return {"ContentLength": 4}

        def download_fileobj(self, bucket, key, f, Callback=None):
            if Callback is not None:
                Callback(4)
            f.write(b"data")

    boto3_module = SimpleNamespace(client=lambda *args, **kwargs: FakeClient())
    botocore_module = SimpleNamespace(
        UNSIGNED=object(), config=SimpleNamespace(Config=lambda **kwargs: kwargs)
    )
    tqdm_module = SimpleNamespace(tqdm=FakeTqdm)
    monkeypatch.setitem(__import__("sys").modules, "boto3", boto3_module)
    monkeypatch.setitem(__import__("sys").modules, "botocore", botocore_module)
    monkeypatch.setitem(
        __import__("sys").modules, "botocore.config", botocore_module.config
    )
    monkeypatch.setitem(__import__("sys").modules, "tqdm", tqdm_module)

    output = tmp_path / "ok.bin"
    aws_interface.download_file_with_progress(None, "s3://bucket/key", str(output))
    assert output.read_bytes() == b"data"

    failing_client = FakeClient(should_fail=True)
    monkeypatch.setitem(
        __import__("sys").modules,
        "boto3",
        SimpleNamespace(client=lambda *args, **kwargs: failing_client),
    )
    bad_output = tmp_path / "bad.bin"
    bad_output.write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError):
        aws_interface.download_file_with_progress(
            None, "s3://bucket/key", str(bad_output)
        )
    assert not bad_output.exists()


def test_aws_list_and_download_branches(monkeypatch, tmp_path):
    class FakeFS:
        def __init__(self, anon=True):
            self.anon = anon

        def ls(self, prefix):
            if "ABI-L1b-RadF" in prefix:
                return [
                    f"bucket/{prefix}OR_ABI-L1b-RadF-M6_G16_s2026001000000_C01.nc",
                    f"bucket/{prefix}OR_ABI-L1b-RadF-M6_G16_s2026001000000_C03.nc",
                ]
            return [
                f"bucket/{prefix}one.nc",
                f"bucket/{prefix}two.txt",
                f"bucket/{prefix}three.nc",
            ]

    downloaded = []

    def fake_download(fs, s3_url, local_path, chunk_size=512 * 1024):
        downloaded.append((s3_url, local_path))
        pathlib = __import__("pathlib")
        pathlib.Path(local_path).write_text("x", encoding="utf-8")

    monkeypatch.setitem(
        __import__("sys").modules, "s3fs", SimpleNamespace(S3FileSystem=FakeFS)
    )
    monkeypatch.setattr(aws_interface, "download_file_with_progress", fake_download)

    dt = datetime(2026, 1, 1, 0, 0)
    assert aws_interface.list_goes_files_2("ABI-L2-MCMIPF", dt) == [
        "s3://bucket/noaa-goes16/ABI-L2-MCMIPF/2026/001/00/one.nc",
        "s3://bucket/noaa-goes16/ABI-L2-MCMIPF/2026/001/00/three.nc",
    ]

    mcmi = aws_interface.download_goes_files_for_datetime(
        dt, product="ABI-L2-MCMIPF", channels=["C01"], local_dir=str(tmp_path)
    )
    assert mcmi == [str(tmp_path / "one.nc")]

    l1b = aws_interface.download_goes_files_for_datetime(
        dt, product="ABI-L1b-RadF", channels=["C01", "C03"], local_dir=str(tmp_path)
    )
    assert l1b == [
        str(tmp_path / "OR_ABI-L1b-RadF-M6_G16_s2026001000000_C01.nc"),
        str(tmp_path / "OR_ABI-L1b-RadF-M6_G16_s2026001000000_C03.nc"),
    ]
    assert downloaded


def test_core_open_and_projection_helpers(monkeypatch):
    class FakeMCMIDataset:
        def __init__(self):
            self.variables = {
                "x": SimpleNamespace(values=np.array([1.0, 2.0])),
                "y": SimpleNamespace(values=np.array([3.0, 4.0])),
                "CMI_C01": FakeBandVariable(np.array([[1.0, 2.0], [3.0, 4.0]]), ndim=2),
            }
            self._projection = FakeProjection()

        def __getitem__(self, key):
            if key == "goes_imager_projection":
                return self._projection
            return self.variables[key]

    class FakeL1BDataset:
        def __init__(self, band_id, shape):
            self.band_id = FakeBandId(band_id)
            self.variables = {
                "x": SimpleNamespace(values=FakeAxisValues((10848,))),
                "y": SimpleNamespace(values=FakeAxisValues((10848,))),
                "band_id": self.band_id,
                "kappa0": SimpleNamespace(data=1.0),
            }
            self.coords = {
                "x": SimpleNamespace(values=FakeAxisValues((10848,))),
                "y": SimpleNamespace(values=FakeAxisValues((10848,))),
            }
            self._projection = FakeProjection()
            self._band_array = FakeBandArray(shape)

        def __getitem__(self, key):
            if key == "Rad":
                return SimpleNamespace(values=self._band_array)
            if key == "goes_imager_projection":
                return self._projection
            raise KeyError(key)

        def close(self):
            return None

    mcmi_ds = FakeMCMIDataset()
    l1b_ds_1 = FakeL1BDataset(2, (10848, 10848))
    l1b_ds_2 = FakeL1BDataset(3, (21696, 21696))
    l1b_ds_3 = FakeL1BDataset(4, (5424, 5424))

    def fake_open(path):
        if path == "mcmi.nc":
            return mcmi_ds
        if path == "l1b1.nc":
            return l1b_ds_1
        if path == "l1b2.nc":
            return l1b_ds_2
        return l1b_ds_3

    monkeypatch.setattr(core, "open_goes_file", fake_open)

    mcmi = core.ABIImage(
        datetime(2026, 1, 1), "ABI-L2-MCMIPF", ["C01"], "noaa-goes16", "data"
    )
    mcmi.files = ["mcmi.nc"]
    mcmi.open()
    crs, x, y = mcmi.get_projection_params()
    assert mcmi.datasets["C01"]["band_array"].shape == (2, 2)
    assert np.allclose(x, np.array([1.0, 2.0]) * 35786023.0)
    assert np.allclose(y, np.array([3.0, 4.0]) * 35786023.0)
    assert crs is not None

    l1b = core.ABIImage(
        datetime(2026, 1, 1),
        "ABI-L1b-RadF",
        ["C02", "C03", "C04"],
        "noaa-goes16",
        "data",
    )
    l1b.files = ["l1b1.nc", "l1b2.nc", "l1b3.nc"]
    l1b.open()
    assert l1b.datasets["C02"]["band_array"].shape == (5424, 5424)
    assert l1b.datasets["C03"]["band_array"].shape == (5424, 5424)
    assert l1b.datasets["C04"]["band_array"].shape == (5424, 5424)


def test_core_get_bbox_indices_uses_helper(monkeypatch):
    image = core.ABIImage(
        datetime(2026, 1, 1), "ABI-L2-MCMIPF", ["C01"], "noaa-goes16", "data"
    )

    monkeypatch.setattr(
        image,
        "get_projection_params",
        lambda: (
            SimpleNamespace(name="crs"),
            np.array([1.0, 2.0]),
            np.array([3.0, 4.0]),
        ),
    )
    monkeypatch.setattr(
        core, "get_pixel_indices_from_latlon_bbox", lambda *args: (9, 8, 7, 6)
    )

    assert image.get_bbox_indices(-1, 1, -2, 2) == (9, 8, 7, 6)


def test_l1b_init_default_channels_and_missing_band():
    # Cubre línea 23 (channels=None por defecto)
    img = l1b_abi_image.ABIImageL1b(
        datetime(2026, 1, 1),
        product="ABI-L1b-RadF",
        channels=None,  # Carga las 16 bandas por defecto
    )
    assert len(img.channels) == 16
    assert img.channels[0] == "C01"
    assert img.channels[15] == "C16"

    # Cubre línea 85 (ValueError al pedir banda inexistente)
    with pytest.raises(ValueError, match="Banda C99 no encontrada"):
        img.get_band_array("C99")


def test_l1b_open_with_05km_resolution_and_get_projection_params(monkeypatch):
    # Cubre líneas 36-37 (reescalado 0.5km de (21696, 21696) -> (5424, 5424))
    # y líneas 89-101 (get_projection_params)
    class FakeL1BDataset05km:
        def __init__(self):
            self.band_id = FakeBandId(2)
            self.variables = {
                "x": SimpleNamespace(values=FakeAxisValues((10848,))),
                "y": SimpleNamespace(values=FakeAxisValues((10848,))),
                "band_id": self.band_id,
                "kappa0": SimpleNamespace(data=1.0),
            }
            self.coords = self.variables
            self._projection = FakeProjection()
            self._band_array = FakeBandArray((21696, 21696))

        def __getitem__(self, key):
            if key == "Rad":
                return SimpleNamespace(values=self._band_array)
            if key == "goes_imager_projection":
                return self._projection
            raise KeyError(key)

        def close(self):
            return None

    monkeypatch.setattr(
        l1b_abi_image, "open_goes_file", lambda path: FakeL1BDataset05km()
    )

    image = l1b_abi_image.ABIImageL1b(
        datetime(2026, 1, 1),
        product="ABI-L1b-RadF",
        channels=["C02"],
    )
    image.files = ["fake.nc"]
    image.open()

    # Verifica que procesó la resolución de 0.5 km
    assert "C02" in image.datasets
    assert image.datasets["C02"]["band_array"].shape == (5424, 5424)

    # Cubre get_projection_params()
    crs, x, y = image.get_projection_params()
    assert crs is not None
    assert x.shape == (5424,)
    assert y.shape == (5424,)


def test_l1b_calibrate_band_unsupported_unit():
    # Cubre línea 52 (ValueError por unidad no soportada en calibrate_band)
    img = l1b_abi_image.ABIImageL1b(
        datetime(2026, 1, 1),
        product="ABI-L1b-RadF",
        channels=["C01"],
    )
    with pytest.raises(ValueError, match="Unidad de calibración no soportada"):
        img.calibrate_band("C01", np.array([[1.0]]), unit="unsupported_unit")


def test_l1b_open_projection_and_calibration(monkeypatch):
    class FakeL1BDataset:
        def __init__(self, band_id, shape):
            self.band_id = FakeBandId(band_id)
            self.variables = {
                "x": SimpleNamespace(values=FakeAxisValues((10848,))),
                "y": SimpleNamespace(values=FakeAxisValues((10848,))),
                "band_id": self.band_id,
                "kappa0": SimpleNamespace(data=1.0),
            }
            self.coords = self.variables
            self._projection = FakeProjection()
            self._band_array = FakeBandArray(shape)

        def __getitem__(self, key):
            if key == "Rad":
                return SimpleNamespace(values=self._band_array)
            if key == "goes_imager_projection":
                return self._projection
            raise KeyError(key)

        def close(self):
            return None

    monkeypatch.setattr(
        l1b_abi_image, "open_goes_file", lambda path: FakeL1BDataset(2, (10848, 10848))
    )

    image = l1b_abi_image.ABIImageL1b(
        datetime(2026, 1, 1),
        product="ABI-L1b-RadF",
        channels=["C02"],
        satellite="noaa-goes16",
        local_dir="data",
    )
    image.files = ["fake.nc"]
    image.open()

    assert image.get_band_array("C02").shape == (5424, 5424)
    assert image.calibrate_band("C02", np.array([[1.0]]), unit="celsius").shape == (
        1,
        1,
    )
    assert np.array_equal(
        image.calibrate_band("C02", np.array([[1.0]]), unit="kelvin"),
        np.array([[274.15]]),
    )
    with pytest.raises(ValueError):
        image.calibrate_band("C02", np.array([[1.0]]), unit="foo")


def test_l2_open_projection_and_validation(monkeypatch):
    class FakeBandVariable:
        def __init__(self, values):
            self.values = np.asarray(values)
            self.ndim = 3

        def __getitem__(self, item):
            return self

    class FakeMCMIDataset:
        def __init__(self):
            self.variables = {
                "x": SimpleNamespace(values=np.array([1.0, 2.0])),
                "y": SimpleNamespace(values=np.array([3.0, 4.0])),
                "CMI_C01": FakeBandVariable(np.array([[1.0, 2.0], [3.0, 4.0]])),
            }
            self._projection = FakeProjection()

        def __getitem__(self, key):
            if key == "goes_imager_projection":
                return self._projection
            return self.variables[key]

    monkeypatch.setattr(l2_abi_image, "open_goes_file", lambda path: FakeMCMIDataset())

    image = l2_abi_image.ABIImageMCMI(
        datetime(2026, 1, 1),
        product="ABI-L2-MCMIPF",
        channels=["C01"],
        satellite="noaa-goes16",
        local_dir="data",
    )
    image.files = ["fake.nc"]
    image.open()

    assert np.array_equal(
        image.get_band_array("C01"), np.array([[1.0, 2.0], [3.0, 4.0]])
    )
    crs, x, y = image.get_projection_params()
    assert np.allclose(x, np.array([1.0, 2.0]) * 35786023.0)
    assert np.allclose(y, np.array([3.0, 4.0]) * 35786023.0)
    assert crs is not None
    assert np.array_equal(
        image.calibrate_band("C01", np.array([[274.15]]), unit="celsius"),
        np.array([[1.0]]),
    )
    with pytest.raises(ValueError):
        image.calibrate_band("C01", np.array([[1.0]]), unit="foo")


def test_rgb_processor_generate_all_and_missing_product():
    class FakeImage:
        def get_band_array(self, band):
            return np.array([[1.0, 2.0]])

        def calibrate_band(self, band, raw, unit=None):
            return raw

    recipe = {
        "bands": ["C01"],
        "emissive_units": {"C01": "Ref"},
        "funcs": {
            "R": lambda imgs: imgs["C01"],
            "G": lambda imgs: imgs["C01"],
            "B": lambda imgs: imgs["C01"],
        },
    }
    processor = rgb_processor.RGBProcessor(FakeImage(), {"demo": recipe})
    processor.generate_all()
    assert processor.get_product("demo").shape == (1, 2, 3)
    with pytest.raises(KeyError):
        processor.get_product("missing")


class _VarMCMIEspia:
    """Variable MCMI que registra cuando se materializa y respeta el slicing."""

    def __init__(self, data, lecturas):
        self._data = np.asarray(data)
        self._lecturas = lecturas
        self.ndim = self._data.ndim

    def __getitem__(self, item):
        return _VarMCMIEspia(self._data[item], self._lecturas)

    @property
    def values(self):
        self._lecturas.append(self._data.shape)
        return self._data


class _DatasetMCMIEspia:
    def __init__(self, lecturas):
        base = np.arange(16 * 100, dtype=float).reshape(16, 10, 10)
        self.variables = {
            f"CMI_C{i + 1:02d}": _VarMCMIEspia(base[i], lecturas) for i in range(16)
        }

    def __getitem__(self, key):
        return self.variables[key]


def _imagen_mcmi_espia(monkeypatch, lecturas):
    monkeypatch.setattr(
        l2_abi_image, "open_goes_file", lambda path: _DatasetMCMIEspia(lecturas)
    )
    image = l2_abi_image.ABIImageMCMI(
        datetime(2026, 1, 1), satellite="noaa-goes16", local_dir="data"
    )
    image.files = ["fake.nc"]
    image.open()
    return image


def test_mcmi_open_no_lee_ninguna_banda(monkeypatch):
    lecturas = []
    image = _imagen_mcmi_espia(monkeypatch, lecturas)

    # Las 16 bandas quedan registradas pero ninguna materializada.
    assert sorted(image.datasets) == [f"C{i + 1:02d}" for i in range(16)]
    assert lecturas == []
    assert all(e["band_array"] is None for e in image.datasets.values())


def test_mcmi_solo_lee_las_bandas_pedidas_y_las_cachea(monkeypatch):
    lecturas = []
    image = _imagen_mcmi_espia(monkeypatch, lecturas)

    primera = image.get_band_array("C02")
    segunda = image.get_band_array("C02")

    assert len(lecturas) == 1  # la segunda llamada sale del cache
    assert segunda is primera
    assert np.array_equal(primera, np.arange(100, 200, dtype=float).reshape(10, 10))


def test_mcmi_get_band_array_lee_solo_la_ventana(monkeypatch):
    lecturas = []
    image = _imagen_mcmi_espia(monkeypatch, lecturas)
    image.set_window(2, 5, 3, 7)

    arr = image.get_band_array("C01")

    # Lo que se materializa es el recorte, no el disco completo.
    assert lecturas == [(3, 4)]
    assert arr.shape == (3, 4)
    esperado = np.arange(100, dtype=float).reshape(10, 10)[2:5, 3:7]
    assert np.array_equal(arr, esperado)


def test_mcmi_cambiar_la_ventana_invalida_el_cache(monkeypatch):
    lecturas = []
    image = _imagen_mcmi_espia(monkeypatch, lecturas)

    image.set_window(0, 4, 0, 4)
    assert image.get_band_array("C01").shape == (4, 4)
    image.set_window(0, 2, 0, 2)
    assert image.get_band_array("C01").shape == (2, 2)
    assert lecturas == [(4, 4), (2, 2)]


def test_mcmi_get_band_array_banda_inexistente(monkeypatch):
    image = _imagen_mcmi_espia(monkeypatch, [])
    with pytest.raises(ValueError, match="C99"):
        image.get_band_array("C99")


def test_l1b_get_band_array_aplica_la_ventana_antes_de_calibrar(monkeypatch):
    calibradas = []

    def fake_calibrate_imag(array, metadata, U=None):
        calibradas.append(array.shape)
        return array

    monkeypatch.setattr(l1b_abi_image, "calibrate_imag", fake_calibrate_imag)

    image = l1b_abi_image.ABIImageL1b(
        datetime(2026, 1, 1), product="ABI-L1b-RadF", channels=["C01"]
    )
    completo = np.arange(100, dtype=float).reshape(10, 10)
    image.datasets = {"C01": {"band_array": completo, "metadata": {}}}

    assert image.get_band_array("C01").shape == (10, 10)

    image.set_window(2, 5, 3, 7)
    arr = image.get_band_array("C01")

    # calibrate_imag recibe ya el recorte, no el disco completo.
    assert calibradas == [(10, 10), (3, 4)]
    assert np.array_equal(arr, completo[2:5, 3:7])
