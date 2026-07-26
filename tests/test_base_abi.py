import pytest
from datetime import datetime
from types import SimpleNamespace

# Importa tu clase base
import goes_rgb.base_abi_image as base_module


# Subclase concreta ficticia para probar la funcionalidad no abstracta
class DummyABIImage(base_module.BaseABIImage):
    def open(self):
        pass

    def get_projection_params(self):
        return SimpleNamespace(name="fake_crs"), [1.0, 2.0], [3.0, 4.0]

    def calibrate_band(self, band, raw_data, unit=None):
        return raw_data


def test_base_abi_image_cannot_instantiate_directly():
    # Intenta instanciar la clase abstracta directamente (debe fallar)
    with pytest.raises(TypeError):
        base_module.BaseABIImage(
            dt=datetime(2026, 1, 1),
            product="ABI-L2-MCMIPF",
            channels=["C01"],
            satellite="noaa-goes16",
            local_dir="data",
        )


def test_base_abi_image_download_success(monkeypatch):
    # Mockea download_goes_files_for_datetime para que devuelva una lista con archivos
    monkeypatch.setattr(
        base_module,
        "download_goes_files_for_datetime",
        lambda *args, **kwargs: ["/path/to/file1.nc", "/path/to/file2.nc"],
    )

    image = DummyABIImage(
        dt=datetime(2026, 1, 1),
        product="ABI-L2-MCMIPF",
        channels=["C01"],
        satellite="noaa-goes16",
        local_dir="data",
    )

    image.download()
    assert image.files == ["/path/to/file1.nc", "/path/to/file2.nc"]


def test_base_abi_image_download_raises_file_not_found(monkeypatch):
    # Mockea download_goes_files_for_datetime para que devuelva una lista vacía
    monkeypatch.setattr(
        base_module,
        "download_goes_files_for_datetime",
        lambda *args, **kwargs: [],
    )

    image = DummyABIImage(
        dt=datetime(2026, 1, 1),
        product="ABI-L2-MCMIPF",
        channels=["C01"],
        satellite="noaa-goes16",
        local_dir="data",
    )

    # Verifica que levanta FileNotFoundError con el mensaje adecuado
    with pytest.raises(FileNotFoundError, match="No files were found"):
        image.download()


def test_base_abi_image_get_band_array_and_bbox_indices(monkeypatch):
    image = DummyABIImage(
        dt=datetime(2026, 1, 1),
        product="ABI-L2-MCMIPF",
        channels=["C01"],
        satellite="noaa-goes16",
        local_dir="data",
    )

    # Preparamos datasets para get_band_array
    fake_array = [[1, 2], [3, 4]]
    image.datasets = {"C01": {"band_array": fake_array}}

    # Probar get_band_array de la clase base
    assert image.get_band_array("C01") == fake_array

    # Mockear get_pixel_indices_from_latlon_bbox para probar get_bbox_indices
    monkeypatch.setattr(
        base_module,
        "get_pixel_indices_from_latlon_bbox",
        lambda lat_i, lat_f, lon_i, lon_f, x, y, crs: (0, 10, 0, 10),
    )

    indices = image.get_bbox_indices(-30, -20, -60, -50)
    assert indices == (0, 10, 0, 10)
