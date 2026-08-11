import numpy as np

from goes_rgb.recipes_registry import RECIPE_REGISTRY


def _sample_bands():
    base = np.array([[1.0, 2.0], [3.0, 4.0]])
    return {f"C{str(index).zfill(2)}": base.copy() for index in range(1, 16)}


def test_registry_contains_builtin_and_custom_recipes():
    expected_names = {
        "true_color",
        "microfisica_nocturna",
        "daily_microphysics",
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
        "falso_color",
        "true_color_personalizado",
        "burn_scar",
    }

    assert expected_names.issubset(RECIPE_REGISTRY)


def test_registry_entries_return_valid_recipes():
    image = _sample_bands()

    for name, loader in RECIPE_REGISTRY.items():
        recipe = loader()

        assert set(recipe) == {"funcs", "bands", "emissive_units"}
        assert set(recipe["funcs"]) == {"R", "G", "B"}
        assert all(callable(recipe["funcs"][channel]) for channel in "RGB")
        assert isinstance(recipe["bands"], list)
        assert isinstance(recipe["emissive_units"], dict)

        for channel in "RGB":
            output = recipe["funcs"][channel](image)
            assert output.shape == (2, 2)
            assert np.all(output >= 0)
            assert np.all(output <= 1)
