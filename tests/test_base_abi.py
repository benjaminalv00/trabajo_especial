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


def test_set_window_guarda_ventana_e_invalida_bandas_perezosas():
    image = DummyABIImage(
        dt=datetime(2026, 1, 1),
        product="ABI-L2-MCMIPF",
        channels=["C01", "C02"],
        satellite="noaa-goes16",
        local_dir="data",
    )
    assert image.window is None

    # Una banda perezosa ya materializada y otra eager (L1b) que no debe tocarse.
    image.datasets = {
        "C01": {"band_array": [[1, 2], [3, 4]], "lazy": True},
        "C02": {"band_array": [[5, 6], [7, 8]]},
    }

    image.set_window(10, 20, 30, 40)

    assert image.window == (10, 20, 30, 40)
    assert image.datasets["C01"]["band_array"] is None
    assert image.datasets["C02"]["band_array"] == [[5, 6], [7, 8]]

    # Repetir la misma ventana no vuelve a invalidar nada.
    image.datasets["C01"]["band_array"] = [[9]]
    image.set_window(10, 20, 30, 40)
    assert image.datasets["C01"]["band_array"] == [[9]]


def test_aplicar_window_recorta_solo_si_hay_ventana():
    import numpy as np

    image = DummyABIImage(
        dt=datetime(2026, 1, 1),
        product="ABI-L2-MCMIPF",
        channels=["C01"],
        satellite="noaa-goes16",
        local_dir="data",
    )
    arr = np.arange(100).reshape(10, 10)

    assert image._aplicar_window(arr) is arr

    image.set_window(2, 5, 3, 7)
    recortado = image._aplicar_window(arr)
    assert recortado.shape == (3, 4)
    assert np.array_equal(recortado, arr[2:5, 3:7])
