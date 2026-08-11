import importlib
from pathlib import Path


def _lazy_recipe(module_path, func_name):
    def _recipe():
        module = importlib.import_module(module_path)
        return getattr(module, func_name)()

    return _recipe


RECIPE_REGISTRY = {
    "true_color": _lazy_recipe("goes_rgb.rgb_recipes", "true_color"),
    "microfisica_nocturna": _lazy_recipe(
        "goes_rgb.rgb_recipes", "microfisica_nocturna"
    ),
    "daily_microphysics": _lazy_recipe("goes_rgb.rgb_recipes", "daily_microphysics"),
    "fire_temperature": _lazy_recipe("goes_rgb.rgb_recipes", "fire_temperature"),
    "air_mass": _lazy_recipe("goes_rgb.rgb_recipes", "air_mass"),
    "ash": _lazy_recipe("goes_rgb.rgb_recipes", "ash"),
    "day_cloud_convection": _lazy_recipe(
        "goes_rgb.rgb_recipes", "day_cloud_convection"
    ),
    "day_convection": _lazy_recipe("goes_rgb.rgb_recipes", "day_convection"),
    "day_land_cloud": _lazy_recipe("goes_rgb.rgb_recipes", "day_land_cloud"),
    "day_land_cloud_fire": _lazy_recipe("goes_rgb.rgb_recipes", "day_land_cloud_fire"),
    "day_snow_fog": _lazy_recipe("goes_rgb.rgb_recipes", "day_snow_fog"),
    "simple_water_vapor": _lazy_recipe("goes_rgb.rgb_recipes", "simple_water_vapor"),
    "dust": _lazy_recipe("goes_rgb.rgb_recipes", "dust"),
    "differential_water_vapor": _lazy_recipe(
        "goes_rgb.rgb_recipes", "differential_water_vapor"
    ),
}


def _load_custom_recipe(module_name: str, file_path: str):
    import importlib.util

    p = Path(file_path)
    spec = importlib.util.spec_from_file_location(module_name, str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "recipe") and callable(mod.recipe):
        return mod.recipe
    if hasattr(mod, "RECIPE"):
        const = getattr(mod, "RECIPE")
        return lambda c=const: c
    raise ValueError(f"No se encontró recipe() ni RECIPE en {file_path}")


RECIPE_REGISTRY["falso_color"] = _load_custom_recipe(
    "config.custom_recipes.falso_color", "config/custom_recipes/falso_color.py"
)
RECIPE_REGISTRY["true_color_personalizado"] = _load_custom_recipe(
    "config.custom_recipes.true_color_personalizado",
    "config/custom_recipes/true_color_personalizado.py",
)
RECIPE_REGISTRY["cicatriz_quemado"] = _load_custom_recipe(
    "config.custom_recipes.cicatriz_quemado",
    "config/custom_recipes/cicatriz_quemado.py",
)
