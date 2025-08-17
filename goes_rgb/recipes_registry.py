from goes_rgb import rgb_recipes as rr

RECIPE_REGISTRY = {
    "true_color": rr.true_color,
    "microfisica_nocturna": rr.microfisica_nocturna,
    "daily_microphysics": rr.daily_microphysics,
    "fire_temperature": rr.fire_temperature,
    "air_mass": rr.air_mass,
    "ash": rr.ash,
    "day_cloud_convection": rr.day_cloud_convection,
    "day_convection": rr.day_convection,
    "day_land_cloud": rr.day_land_cloud,
    "day_land_cloud_fire": rr.day_land_cloud_fire,
    "day_snow_fog": rr.day_snow_fog,
    "simple_water_vapor": rr.simple_water_vapor,
    "dust": rr.dust,
    "differential_water_vapor": rr.differential_water_vapor,
}
