import numpy as np
import pytest

from goes_rgb.recipes_registry import RECIPE_REGISTRY


def _bands(c02, c03, c06):
    return {
        "C02": np.array(c02, dtype=float),
        "C03": np.array(c03, dtype=float),
        "C06": np.array(c06, dtype=float),
    }


def _recipe():
    return RECIPE_REGISTRY["burn_scar"]()


def test_recipe_contract():
    recipe = _recipe()

    assert set(recipe) == {"funcs", "bands", "emissive_units"}
    assert set(recipe["funcs"]) == {"R", "G", "B"}
    assert recipe["bands"] == ["C02", "C03", "C06"]
    assert recipe["emissive_units"] == {}


def test_r_channel_high_for_burned_pixel():
    # NIR bajo (C03), SWIR alto (C06) -> NBR muy negativo -> R alto (cicatriz)
    img = _bands(c02=[[0.1]], c03=[[0.1]], c06=[[0.4]])
    r = _recipe()["funcs"]["R"](img)
    assert r[0, 0] == pytest.approx(1.0)


def test_r_channel_low_for_healthy_vegetation():
    # NIR alto (C03), SWIR bajo (C06) -> NBR alto -> R bajo (vegetacion sana)
    img = _bands(c02=[[0.05]], c03=[[0.5]], c06=[[0.05]])
    r = _recipe()["funcs"]["R"](img)
    assert r[0, 0] == pytest.approx(0.0)


def test_r_channel_masks_deep_water():
    # C03 + C06 < 0.02 -> se fuerza R = 0 sin importar el NBR resultante
    img = _bands(c02=[[0.01]], c03=[[0.005]], c06=[[0.005]])
    r = _recipe()["funcs"]["R"](img)
    assert r[0, 0] == 0.0


def test_r_channel_boundary_is_not_masked():
    # (C03 + C06) == 0.02 -> valido (umbral es estrictamente "< 0.02")
    # y NBR = 0 (neutro) -> R = 0 con el offset calibrado (Vmin=0.0)
    img = _bands(c02=[[0.0]], c03=[[0.01]], c06=[[0.01]])
    r = _recipe()["funcs"]["R"](img)
    assert r[0, 0] == pytest.approx(0.0)


def test_r_channel_saturates_at_threshold():
    # NBR = -0.15 (Vmax de realce_gama) -> R satura en 1
    img = _bands(c02=[[0.0]], c03=[[0.425]], c06=[[0.575]])
    r = _recipe()["funcs"]["R"](img)
    assert r[0, 0] == pytest.approx(1.0)


def test_r_channel_stays_saturated_beyond_threshold():
    # NBR = -0.30 (mas negativo que el umbral) -> sigue clipeado en R = 1
    img = _bands(c02=[[0.0]], c03=[[0.35]], c06=[[0.65]])
    r = _recipe()["funcs"]["R"](img)
    assert r[0, 0] == pytest.approx(1.0)


def test_r_channel_partial_response_is_nonlinear():
    # NBR = -0.075 (mitad del umbral) -> Vaux = 0.5, gama=0.5 (exponente 2)
    # comprime el rango medio: R = 0.5 ** 2 = 0.25, no 0.5 (no lineal a
    # proposito, para que solo lo mas extremo llegue a rojo pleno)
    img = _bands(c02=[[0.0]], c03=[[0.4625]], c06=[[0.5375]])
    r = _recipe()["funcs"]["R"](img)
    assert r[0, 0] == pytest.approx(0.25)


def test_g_and_b_scale_and_clip():
    img = _bands(c02=[[0.2, 0.8]], c03=[[0.25, 1.0]], c06=[[0.1, 0.1]])
    g = _recipe()["funcs"]["G"](img)
    b = _recipe()["funcs"]["B"](img)

    assert g[0, 0] == pytest.approx(0.5)  # 0.25 / 0.5
    assert g[0, 1] == 1.0  # clip(1.0 / 0.5 = 2.0, 0, 1)
    assert b[0, 0] == pytest.approx(0.5)  # 0.2 / 0.4
    assert b[0, 1] == 1.0  # clip(0.8 / 0.4 = 2.0, 0, 1)
