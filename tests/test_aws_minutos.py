"""La descarga elige el escaneo más cercano a la fecha pedida, minutos incluidos."""

import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

import goes_rgb.aws_interface as aws_interface

PREFIJO = "noaa-goes16/ABI-L2-MCMIPF/2025/242/15/"


def _nombre_mcmi(minuto):
    return (
        f"OR_ABI-L2-MCMIPF-M6_G16_s202524215{minuto:02d}205"
        f"_e202524215{minuto + 9:02d}525_c202524215{minuto + 9:02d}599.nc"
    )


def _nombre_l1b(canal, minuto):
    return (
        f"OR_ABI-L1b-RadF-M6{canal}_G16_s202524215{minuto:02d}205"
        f"_e202524215{minuto + 9:02d}525_c202524215{minuto + 9:02d}599.nc"
    )


@pytest.fixture
def s3_falso(monkeypatch):
    """Reemplaza s3fs y la descarga; registra qué se bajó."""
    estado = {"archivos": [], "bajados": [], "listados": 0}

    class FakeFS:
        def __init__(self, anon=True):
            pass

        def ls(self, prefix):
            estado["listados"] += 1
            return [prefix + n for n in estado["archivos"]]

    def fake_download(fs, s3_url, local_path, chunk_size=512 * 1024):
        estado["bajados"].append(s3_url)
        with open(local_path, "w", encoding="utf-8") as f:
            f.write("x")

    monkeypatch.setitem(sys.modules, "s3fs", SimpleNamespace(S3FileSystem=FakeFS))
    monkeypatch.setattr(aws_interface, "download_file_with_progress", fake_download)
    return estado


def test_inicio_escaneo_se_lee_del_nombre():
    assert aws_interface._inicio_escaneo(_nombre_mcmi(30)) == datetime(
        2025, 8, 30, 15, 30, 20
    )
    assert aws_interface._inicio_escaneo("sin_fecha.nc") is None


def test_mcmi_baja_el_escaneo_mas_cercano_a_los_minutos(tmp_path, s3_falso):
    s3_falso["archivos"] = [_nombre_mcmi(m) for m in (0, 10, 20, 30, 40, 50)]

    files = aws_interface.download_goes_files_for_datetime(
        datetime(2025, 8, 30, 15, 30), local_dir=str(tmp_path)
    )

    assert files == [str(tmp_path / _nombre_mcmi(30))]
    assert s3_falso["bajados"] == ["s3://" + PREFIJO + _nombre_mcmi(30)]


def test_fechas_distintas_en_la_misma_hora_dan_archivos_distintos(tmp_path, s3_falso):
    s3_falso["archivos"] = [_nombre_mcmi(m) for m in (0, 10, 20, 30, 40, 50)]

    a = aws_interface.download_goes_files_for_datetime(
        datetime(2025, 8, 30, 15, 0), local_dir=str(tmp_path)
    )
    b = aws_interface.download_goes_files_for_datetime(
        datetime(2025, 8, 30, 15, 20), local_dir=str(tmp_path)
    )

    assert a != b


def test_mcmi_reutiliza_el_archivo_local_cercano_sin_ir_a_s3(tmp_path, s3_falso):
    (tmp_path / _nombre_mcmi(30)).write_text("x", encoding="utf-8")

    files = aws_interface.download_goes_files_for_datetime(
        datetime(2025, 8, 30, 15, 30), local_dir=str(tmp_path)
    )

    assert files == [str(tmp_path / _nombre_mcmi(30))]
    assert s3_falso["listados"] == 0
    assert s3_falso["bajados"] == []


def test_mcmi_no_reutiliza_un_archivo_local_de_otros_minutos(tmp_path, s3_falso):
    (tmp_path / _nombre_mcmi(0)).write_text("x", encoding="utf-8")
    s3_falso["archivos"] = [_nombre_mcmi(m) for m in (0, 10, 20, 30, 40, 50)]

    files = aws_interface.download_goes_files_for_datetime(
        datetime(2025, 8, 30, 15, 30), local_dir=str(tmp_path)
    )

    assert files == [str(tmp_path / _nombre_mcmi(30))]
    assert len(s3_falso["bajados"]) == 1


def test_l1b_reutiliza_archivos_locales_con_nombre_real(tmp_path, s3_falso):
    # En L1b el canal viene pegado al modo ("M6C13"); antes el patrón local no
    # lo reconocía y se volvía a descargar siempre.
    (tmp_path / _nombre_l1b("C13", 30)).write_text("x", encoding="utf-8")

    files = aws_interface.download_goes_files_for_datetime(
        datetime(2025, 8, 30, 15, 30),
        product="ABI-L1b-RadF",
        channels=["C13"],
        local_dir=str(tmp_path),
    )

    assert files == [str(tmp_path / _nombre_l1b("C13", 30))]
    assert s3_falso["bajados"] == []
