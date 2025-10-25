import sys
import types
import numpy as np
import pytest
from datetime import datetime

# Intentar importar config_runner; si falla por dependencias pesadas, saltar tests.
try:
    import config_runner as cr
except Exception as e:  # pragma: no cover
    cr = None
    IMPORT_ERR = e
else:
    IMPORT_ERR = None

skip_if_no_import = pytest.mark.skipif(
    cr is None, reason=f"No se pudo importar config_runner: {IMPORT_ERR}"
)


@skip_if_no_import
def test_format_ts():
    dt = datetime(2025, 8, 30, 18, 0)
    assert cr._format_ts(dt) == "20250830_1800"


@skip_if_no_import
def test_format_filename():
    assert (
        cr._format_filename("{producto}_{ts}.tif", "true_color", "20250830_1800")
        == "true_color_20250830_1800.tif"
    )


@skip_if_no_import
def test_salidas_deseadas():
    job = {"salidas": ["png", "video"]}
    out = cr._salidas_deseadas(job)
    assert out == {"PNG", "VIDEO"}


@skip_if_no_import
def test_select_geotiff_products():
    productos = ["true_color", "air_mass"]
    # productos explícitos
    cfg = {"productos": ["air_mass"]}
    assert cr._select_geotiff_products(cfg, productos) == {"air_mass"}
    # producto único
    cfg = {"producto": "true_color"}
    assert cr._select_geotiff_products(cfg, productos) == {"true_color"}
    # fallback a único producto
    assert cr._select_geotiff_products({}, ["true_color"]) == {"true_color"}
    # vacío si múltiples productos y sin config
    assert cr._select_geotiff_products({}, productos) == set()


@skip_if_no_import
def test_expand_datetimes_single():
    job = {"datetime": "2025-08-30T18:00:00"}
    dts = list(cr.expand_datetimes(job))
    assert len(dts) == 1
    assert dts[0] == datetime(2025, 8, 30, 18, 0)


@skip_if_no_import
def test_expand_datetimes_list():
    job = {"datetimes": ["2025-08-30T18:00:00", "2025-08-30T19:00:00"]}
    dts = list(cr.expand_datetimes(job))
    assert len(dts) == 2
    assert dts[0] == datetime(2025, 8, 30, 18, 0)
    assert dts[1] == datetime(2025, 8, 30, 19, 0)


@skip_if_no_import
def test_expand_datetimes_range():
    job = {
        "rango": {
            "inicio": "2025-08-30T18:00:00",
            "fin": "2025-08-30T19:00:00",
            "paso_minutos": 30,
        }
    }
    dts = list(cr.expand_datetimes(job))
    assert [d.strftime("%H:%M") for d in dts] == ["18:00", "18:30", "19:00"]


@skip_if_no_import
def test_normalize_rgb_frame():
    # 2D a 3 canales
    g = (np.ones((10, 10)) * 128).astype(np.uint8)
    fr = cr._normalize_rgb_frame(g)
    assert fr.shape == (10, 10, 3)
    assert fr.dtype == np.uint8

    # RGBA a RGB
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[..., 0] = 255
    fr = cr._normalize_rgb_frame(rgba)
    assert fr.shape == (4, 4, 3)
    assert np.all(fr[..., 0] == 255)

    # float -> uint8 clip
    fl = np.array([[[-1.0, 0.5, 2.0]]], dtype=np.float32) * 255.0
    fr = cr._normalize_rgb_frame(fl)
    assert fr.dtype == np.uint8
    assert fr.shape == (1, 1, 3)
    assert fr[0, 0, 0] == 0 and fr[0, 0, 1] == 127 and fr[0, 0, 2] == 255


@skip_if_no_import
def test_pad_frames_to_even_16():
    a = np.zeros((17, 33, 3), dtype=np.uint8)
    b = np.zeros((32, 16, 3), dtype=np.uint8)
    out = cr._pad_frames_to_even_16([a, b])
    h, w = out[0].shape[:2]
    h2, w2 = out[1].shape[:2]
    # Deben ser iguales y múltiplos de 16 y pares
    assert (h, w) == (h2, w2)
    assert h % 16 == 0 and w % 16 == 0
    assert h % 2 == 0 and w % 2 == 0
