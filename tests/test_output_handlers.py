"""
Tests unitarios de los handlers de salida.

A diferencia de test_config_runner.py, que ejercita los handlers de forma
indirecta a traves de run_job(), estos tests los verifican de forma
aislada: esa es justamente la propiedad que el refactor a
Strategy + Registry buscaba habilitar.
"""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import goes_rgb.helpers as real_helpers
from goes_rgb.output_handlers import (
    ACCUMULATOR_OUTPUT_REGISTRY,
    FRAME_OUTPUT_REGISTRY,
    ComponentesRgbOutputHandler,
    FrameContext,
    GeoTiffOutputHandler,
    GifOutputHandler,
    PngOutputHandler,
    VideoOutputHandler,
    _normalize_frame,
)


def _ctx(tmp_path, nombre="true_color", productos=None):
    """Construye un FrameContext minimo para los tests."""
    return FrameContext(
        rgb=np.ones((2, 2, 3), dtype=float),
        nombre=nombre,
        dt=datetime(2026, 1, 1, 12, 30),
        extent=(0, 1, 0, 1),
        crs=SimpleNamespace(proj4_init="+proj=geos"),
        x=np.array([10.0, 20.0]),
        y=np.array([40.0, 30.0]),
        f0=0,
        f1=1,
        c0=0,
        c1=1,
        productos=productos if productos is not None else [nombre],
        out_dir=tmp_path,
        shp="shapefiles/dummy.shp",
        titulo="titulo",
        png_path=tmp_path / "frame.png",
    )


# --------------------------------------------------------------------------
# Registries
# --------------------------------------------------------------------------


def test_registries_contienen_las_cinco_salidas():
    assert set(FRAME_OUTPUT_REGISTRY) == {"PNG", "COMPONENTES_RGB", "GEOTIFF"}
    assert set(ACCUMULATOR_OUTPUT_REGISTRY) == {"GIF", "VIDEO"}


def test_orden_del_registry_por_frame_define_el_orden_de_generated_files():
    # run_job itera FRAME_OUTPUT_REGISTRY en orden de insercion, y de ese
    # orden depende el orden de la lista que devuelve run_job (valor de
    # retorno publico). Reordenar el dict seria un cambio de comportamiento.
    assert list(FRAME_OUTPUT_REGISTRY) == ["PNG", "COMPONENTES_RGB", "GEOTIFF"]


def test_cada_handler_declara_el_nombre_con_el_que_esta_registrado():
    for nombre, handler in FRAME_OUTPUT_REGISTRY.items():
        assert handler.nombre == nombre
    for nombre, handler in ACCUMULATOR_OUTPUT_REGISTRY.items():
        assert handler.nombre == nombre


# --------------------------------------------------------------------------
# activo(): PNG es asimetrico respecto del resto
# --------------------------------------------------------------------------


def test_png_se_activa_aunque_no_haya_configuracion():
    # Comportamiento heredado del codigo original: PNG se genera aunque no
    # exista png_conf, a diferencia del resto de las salidas.
    assert PngOutputHandler().activo({"PNG"}, {}) is True


def test_png_no_se_activa_si_no_fue_pedido():
    assert PngOutputHandler().activo({"GEOTIFF"}, {"out_dir": "x"}) is False


@pytest.mark.parametrize(
    "handler", [ComponentesRgbOutputHandler(), GeoTiffOutputHandler()]
)
def test_resto_de_handlers_requieren_configuracion_no_vacia(handler):
    assert handler.activo({handler.nombre}, {}) is False
    assert handler.activo({handler.nombre}, {"out_dir": "x"}) is True


# --------------------------------------------------------------------------
# _normalize_frame
# --------------------------------------------------------------------------


def test_normalize_frame_expande_escala_de_grises_a_rgb():
    out = _normalize_frame(np.zeros((2, 2), dtype=np.uint8))
    assert out.shape == (2, 2, 3)


def test_normalize_frame_descarta_el_canal_alfa():
    out = _normalize_frame(np.zeros((2, 2, 4), dtype=np.uint8))
    assert out.shape == (2, 2, 3)


def test_normalize_frame_convierte_a_uint8_saturando():
    out = _normalize_frame(np.array([[[-5.0, 300.0, 128.0]]]))
    assert out.dtype == np.uint8
    assert out.tolist() == [[[0, 255, 128]]]


# --------------------------------------------------------------------------
# ComponentesRgbOutputHandler: logica de decision de tres ramas
# --------------------------------------------------------------------------


def _mock_band_writer(monkeypatch, escritos):
    def fake_save_band_geotiff(band_array, x, y, f0, f1, c0, c1, crs, output_path):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("band", encoding="utf-8")
        escritos.append(output_path)

    monkeypatch.setattr(real_helpers, "save_band_geotiff", fake_save_band_geotiff)


def test_componentes_exporta_los_tres_canales_cuando_el_producto_esta_en_la_lista(
    tmp_path, monkeypatch
):
    escritos = []
    _mock_band_writer(monkeypatch, escritos)

    rutas = ComponentesRgbOutputHandler().exportar(
        _ctx(tmp_path),
        {"productos": ["true_color"], "out_dir": str(tmp_path / "comp")},
    )

    assert len(rutas) == 3
    assert [Path(r).name[-5] for r in rutas] == ["R", "G", "B"]


def test_componentes_no_exporta_si_el_producto_no_fue_seleccionado(
    tmp_path, monkeypatch
):
    escritos = []
    _mock_band_writer(monkeypatch, escritos)

    rutas = ComponentesRgbOutputHandler().exportar(
        _ctx(tmp_path, nombre="air_mass", productos=["air_mass", "true_color"]),
        {"productos": ["true_color"], "out_dir": str(tmp_path / "comp")},
    )

    assert rutas == []
    assert escritos == []


def test_componentes_exporta_por_defecto_si_el_job_tiene_un_solo_producto(
    tmp_path, monkeypatch
):
    # Tercera rama: sin 'productos' ni 'producto' definidos, se exporta
    # unicamente si el job procesa un solo producto.
    escritos = []
    _mock_band_writer(monkeypatch, escritos)

    rutas = ComponentesRgbOutputHandler().exportar(
        _ctx(tmp_path, productos=["true_color"]),
        {"out_dir": str(tmp_path / "comp")},
    )

    assert len(rutas) == 3


def test_componentes_no_exporta_por_defecto_con_varios_productos(tmp_path, monkeypatch):
    escritos = []
    _mock_band_writer(monkeypatch, escritos)

    rutas = ComponentesRgbOutputHandler().exportar(
        _ctx(tmp_path, productos=["true_color", "air_mass"]),
        {"out_dir": str(tmp_path / "comp")},
    )

    assert rutas == []


# --------------------------------------------------------------------------
# GeoTiffOutputHandler
# --------------------------------------------------------------------------


def _mock_geotiff_writers(monkeypatch, reproyectados=None):
    def fake_save_rgb_geotiff(rgb, x, y, f0, f1, c0, c1, crs, output_path):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("tif", encoding="utf-8")

    def fake_reproject_geotiff(src, dst, epsg):
        Path(dst).write_text("reproj", encoding="utf-8")
        if reproyectados is not None:
            reproyectados.append(epsg)

    monkeypatch.setattr(real_helpers, "save_rgb_geotiff", fake_save_rgb_geotiff)
    monkeypatch.setitem(
        __import__("sys").modules,
        "scripts.GeoTIFF_translate_coord_output",
        SimpleNamespace(reproject_geotiff=fake_reproject_geotiff),
    )


def test_geotiff_exporta_y_reproyecta(tmp_path, monkeypatch):
    reproyectados = []
    _mock_geotiff_writers(monkeypatch, reproyectados)

    rutas = GeoTiffOutputHandler().exportar(
        _ctx(tmp_path),
        {
            "productos": ["true_color"],
            "out_dir": str(tmp_path / "tif"),
            "reproyecciones": [{"epsg": "EPSG:3857", "suffix": "_wm"}],
        },
    )

    assert len(rutas) == 2  # el original + el reproyectado
    assert reproyectados == ["EPSG:3857"]


def test_geotiff_ignora_productos_no_seleccionados(tmp_path, monkeypatch):
    _mock_geotiff_writers(monkeypatch)

    rutas = GeoTiffOutputHandler().exportar(
        _ctx(tmp_path, nombre="air_mass", productos=["air_mass", "true_color"]),
        {"productos": ["true_color"], "out_dir": str(tmp_path / "tif")},
    )

    assert rutas == []


def test_geotiff_no_exporta_sin_producto_resoluble(tmp_path, monkeypatch):
    # Sin 'productos', sin 'producto' y con mas de un producto en el job no
    # hay forma de decidir cual exportar.
    _mock_geotiff_writers(monkeypatch)

    rutas = GeoTiffOutputHandler().exportar(
        _ctx(tmp_path, productos=["true_color", "air_mass"]),
        {"out_dir": str(tmp_path / "tif")},
    )

    assert rutas == []


def test_geotiff_sobrevive_a_una_reproyeccion_fallida(tmp_path, monkeypatch):
    def fake_save_rgb_geotiff(rgb, x, y, f0, f1, c0, c1, crs, output_path):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("tif", encoding="utf-8")

    def fake_reproject_geotiff(src, dst, epsg):
        raise RuntimeError("EPSG invalido")

    monkeypatch.setattr(real_helpers, "save_rgb_geotiff", fake_save_rgb_geotiff)
    monkeypatch.setitem(
        __import__("sys").modules,
        "scripts.GeoTIFF_translate_coord_output",
        SimpleNamespace(reproject_geotiff=fake_reproject_geotiff),
    )

    rutas = GeoTiffOutputHandler().exportar(
        _ctx(tmp_path),
        {
            "productos": ["true_color"],
            "out_dir": str(tmp_path / "tif"),
            "reproyecciones": [{"epsg": "EPSG:9999", "suffix": "_x"}],
        },
    )

    # El GeoTIFF base se conserva aunque la reproyeccion falle.
    assert len(rutas) == 1


# --------------------------------------------------------------------------
# Acumuladores
# --------------------------------------------------------------------------


@pytest.mark.parametrize("handler", [GifOutputHandler(), VideoOutputHandler()])
def test_acumuladores_solo_piden_frames_de_su_producto(handler):
    conf = {"producto": "true_color"}
    assert handler.frame_deseado("true_color", conf) is True
    assert handler.frame_deseado("air_mass", conf) is False


@pytest.mark.parametrize("handler", [GifOutputHandler(), VideoOutputHandler()])
def test_acumuladores_no_generan_nada_sin_frames(handler, tmp_path):
    rutas = handler.finalizar([], {"producto": "x", "out_dir": str(tmp_path)})

    assert rutas == []
    assert list(tmp_path.iterdir()) == []
