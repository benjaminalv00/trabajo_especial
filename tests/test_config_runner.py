from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest

import config_runner
import goes_rgb.helpers as real_helpers


def test_load_config_reads_yaml(tmp_path):
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        """
defaults:
  tipo_imagen: MCMI
jobs:
  - nombre: prueba
    datetime: 2026-01-01T12:30:00
""".strip(),
        encoding="utf-8",
    )

    cfg = config_runner.load_config(config_path)

    assert cfg["defaults"]["tipo_imagen"] == "MCMI"
    assert cfg["jobs"][0]["nombre"] == "prueba"


def test_expand_datetimes_handles_datetime_datetimes_and_range():
    job = {
        "datetime": "2026-01-01T12:30:00",
        "datetimes": ["2026-01-01T13:00:00", "2026-01-01T13:30:00"],
        "rango": {
            "inicio": "2026-01-01T14:00:00",
            "fin": "2026-01-01T15:00:00",
            "paso_minutos": 30,
        },
    }

    values = list(config_runner.expand_datetimes(job))

    assert values == [
        datetime(2026, 1, 1, 12, 30),
        datetime(2026, 1, 1, 13, 0),
        datetime(2026, 1, 1, 13, 30),
        datetime(2026, 1, 1, 14, 0),
        datetime(2026, 1, 1, 14, 30),
        datetime(2026, 1, 1, 15, 0),
    ]


def test_run_from_config_dispatches_each_job(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        """
defaults:
  tipo_imagen: MCMI
jobs:
  - nombre: job_1
    datetime: 2026-01-01T12:30:00
  - nombre: job_2
    datetime: 2026-01-01T13:30:00
""".strip(),
        encoding="utf-8",
    )

    calls = []

    def fake_run_job(job, defaults):
        calls.append((job, defaults))
        return [job["nombre"]]

    monkeypatch.setattr(config_runner, "run_job", fake_run_job)

    result = config_runner.run_from_config(config_path)

    assert result == ["job_1", "job_2"]
    assert len(calls) == 2
    assert calls[0][0]["nombre"] == "job_1"
    assert calls[1][0]["nombre"] == "job_2"
    assert calls[0][1]["tipo_imagen"] == "MCMI"


def test_build_image_selects_correct_constructor(monkeypatch):
    calls = []

    class FakeMCMI:
        def __init__(self, dt, satellite=None, local_dir=None):
            calls.append(("MCMI", dt, satellite, local_dir))

    class FakeL1B:
        def __init__(self, dt, product, channels=None, local_dir=None):
            calls.append(("L1B", dt, product, channels, local_dir))

    monkeypatch.setitem(
        sys.modules, "goes_rgb.l2_abi_image", SimpleNamespace(ABIImageMCMI=FakeMCMI)
    )
    monkeypatch.setitem(
        sys.modules, "goes_rgb.l1b_abi_image", SimpleNamespace(ABIImageL1b=FakeL1B)
    )

    dt = datetime(2026, 1, 1, 12, 30)
    config_runner.build_image(dt, {"tipo_imagen": "MCMI"}, {})
    config_runner.build_image(
        dt,
        {
            "tipo_imagen": "L1B",
            "satelite": "GOES18",
            "data_dir": "data2",
            "canales": ["C02"],
        },
        {},
    )

    assert calls[0] == ("MCMI", dt, "noaa-goes16", "data")
    assert calls[1] == ("L1B", dt, "ABI-L1b-RadF", ["C02"], "data2")


def test_build_image_rejects_unknown_mode(monkeypatch):
    class FakeMCMI:
        def __init__(self, *args, **kwargs):
            raise AssertionError("No se esperaba construir MCMI")

    class FakeL1B:
        def __init__(self, *args, **kwargs):
            raise AssertionError("No se esperaba construir L1B")

    monkeypatch.setitem(
        sys.modules, "goes_rgb.l2_abi_image", SimpleNamespace(ABIImageMCMI=FakeMCMI)
    )
    monkeypatch.setitem(
        sys.modules, "goes_rgb.l1b_abi_image", SimpleNamespace(ABIImageL1b=FakeL1B)
    )

    with pytest.raises(ValueError, match="tipo_imagen desconocido"):
        config_runner.build_image(
            datetime(2026, 1, 1, 12, 30), {}, {"tipo_imagen": "XYZ"}
        )


def test_run_job_covers_main_output_branches(tmp_path, monkeypatch):
    class FakeImage:
        def download(self):
            return None

        def open(self):
            return None

        def get_projection_params(self):
            return (
                SimpleNamespace(proj4_init="+proj=geos"),
                np.array([10.0, 20.0]),
                np.array([40.0, 30.0]),
            )

        def get_bbox_indices(self, *args):
            return (0, 1, 0, 1)

    class FakeProcessor:
        def __init__(self, abi_image, recipes, recorte=None):
            self.recipes = recipes

        def generate_all(self):
            return None

        def get_product(self, name):
            return np.ones((2, 2, 3), dtype=float)

    generated = []
    written_frames = []

    def fake_expand_datetimes(job):
        yield datetime(2026, 1, 1, 12, 30)

    def fake_build_image(dt, defaults, job):
        return FakeImage()

    def fake_plot_rgb_with_coastlines(rgb, **kwargs):
        path = Path(kwargs["save_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("png", encoding="utf-8")
        generated.append(path)
        return SimpleNamespace()

    def fake_save_band_geotiff(band_array, x, y, f0, f1, c0, c1, crs, output_path):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("band", encoding="utf-8")
        generated.append(path)

    def fake_save_rgb_geotiff(imagen_RGB, x, y, f0, f1, c0, c1, crs, output_path):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("rgb", encoding="utf-8")
        generated.append(path)

    def fake_reproject_geotiff(src, dst, epsg):
        Path(dst).write_text(f"reprojected {epsg}", encoding="utf-8")
        generated.append(Path(dst))

    class FakeWriter:
        def __init__(self, path, **kwargs):
            self.path = Path(path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("video", encoding="utf-8")
            generated.append(self.path)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def append_data(self, frame):
            written_frames.append(frame)

    fake_imageio = SimpleNamespace(
        get_writer=lambda *args, **kwargs: FakeWriter(args[0], **kwargs),
        imread=lambda fp: np.ones((2, 2, 3), dtype=np.uint8),
    )

    monkeypatch.setattr(config_runner, "expand_datetimes", fake_expand_datetimes)
    monkeypatch.setattr(config_runner, "build_image", fake_build_image)
    monkeypatch.setitem(
        sys.modules,
        "goes_rgb.rgb_processor",
        SimpleNamespace(RGBProcessor=FakeProcessor),
    )
    monkeypatch.setitem(
        sys.modules,
        "goes_rgb.visualization",
        SimpleNamespace(plot_rgb_with_coastlines=fake_plot_rgb_with_coastlines),
    )
    monkeypatch.setattr(real_helpers, "save_band_geotiff", fake_save_band_geotiff)
    monkeypatch.setattr(real_helpers, "save_rgb_geotiff", fake_save_rgb_geotiff)
    monkeypatch.setitem(
        sys.modules,
        "scripts.GeoTIFF_translate_coord_output",
        SimpleNamespace(reproject_geotiff=fake_reproject_geotiff),
    )
    monkeypatch.setitem(sys.modules, "imageio", SimpleNamespace(v2=fake_imageio))
    monkeypatch.setitem(sys.modules, "imageio.v2", fake_imageio)

    job = {
        "nombre": "job_export",
        "productos": ["true_color"],
        "salidas": ["PNG", "COMPONENTES_RGB", "GEOTIFF", "GIF", "VIDEO"],
        "png_conf": {"out_dir": str(tmp_path / "png")},
        "componentes_rgb_conf": {"out_dir": str(tmp_path / "comp")},
        "geotiff_conf": {
            "out_dir": str(tmp_path / "tif"),
            "productos": ["true_color"],
            "reproyecciones": [{"epsg": 4326, "suffix": "_4326"}],
        },
        "gif_conf": {
            "producto": "true_color",
            "out_dir": str(tmp_path / "gif"),
            "filename": "out.gif",
        },
        "video_conf": {
            "producto": "true_color",
            "out_dir": str(tmp_path / "video"),
            "filename": "out.mp4",
        },
    }

    defaults = {
        "png_conf": {},
        "geotiff_conf": {},
        "gif_conf": {},
        "video_conf": {},
        "componentes_rgb_conf": {},
    }

    result = config_runner.run_job(job, defaults)

    assert result
    assert any(path.suffix == ".png" for path in generated)
    assert any(path.suffix == ".tif" for path in generated)
    assert any(path.suffix == ".mp4" for path in generated)
    assert any(path.suffix == ".gif" for path in generated)
    assert len(written_frames) >= 1

    # Las animaciones tambien se reportan en el valor de retorno, que es lo
    # que la GUI muestra al usuario como "Archivos generados".
    assert any(r.endswith(".gif") for r in result)
    assert any(r.endswith(".mp4") for r in result)
