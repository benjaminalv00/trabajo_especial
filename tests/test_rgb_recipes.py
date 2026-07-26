import numpy as np
import pytest

from goes_rgb import rgb_recipes


RECIPE_FACTORY_NAMES = [
    "microfisica_nocturna",
    "daily_microphysics",
    "true_color",
    "fire_temperature",
    "air_mass",
    "ash",
    "day_cloud_convection",
    "day_convection",
    "day_land_cloud",
    "day_land_cloud_fire",
    "day_snow_fog",
    "simple_water_vapor",
    "dust",
    "differential_water_vapor",
]


def _sample_bands():
    base = np.array([[1.0, 2.0], [3.0, 4.0]])
    return {f"C{str(index).zfill(2)}": base.copy() for index in range(1, 16)}


@pytest.mark.parametrize("factory_name", RECIPE_FACTORY_NAMES)
def test_recipe_factories_return_the_expected_contract(factory_name):
    recipe = getattr(rgb_recipes, factory_name)()

    assert set(recipe) == {"funcs", "bands", "emissive_units"}
    assert set(recipe["funcs"]) == {"R", "G", "B"}
    assert all(callable(recipe["funcs"][channel]) for channel in "RGB")
    assert isinstance(recipe["bands"], list)
    assert isinstance(recipe["emissive_units"], dict)

    image = _sample_bands()
    for channel in "RGB":
        output = recipe["funcs"][channel](image)
        assert output.shape == (2, 2)
        assert np.all(output >= 0)
        assert np.all(output <= 1)


def test_true_color_uses_expected_bands():
    recipe = rgb_recipes.true_color()

    assert recipe["bands"] == ["C01", "C02", "C03"]
    assert recipe["emissive_units"] == {}
