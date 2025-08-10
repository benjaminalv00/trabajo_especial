from goes_rgb.helpers import calibrate_imag
from goes_rgb.helpers import realce_gama, realce_p, realce_percentil
import numpy as np


def microfisica_nocturna():

    def R(img):
        imag_cal_C15 = img["C15"]
        imag_cal_C13 = img["C13"]
        # primero pasamos de kelvin a celsius (localmente)
        realce_red = realce_gama(imag_cal_C15 - imag_cal_C13, 1, 1, -6.7, 2.6)
        return realce_red

    def G(img):
        imag_cal_C13 = img["C13"]
        imag_cal_C07 = img["C07"]
        # primero pasamos de kelvin a celsius (localmente)
        realce_green = realce_gama(imag_cal_C13 - imag_cal_C07, 1, 1, -3.1, 5.2)
        return realce_green

    def B(img):
        imag_cal_C13 = img["C13"]
        # primero pasamos de kelvin a celsius (localmente)
        realce_blue = realce_gama(imag_cal_C13, 1, 1, -29.6, 19.5)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C07", "C13", "C15"],
        "emissive_units": {"C07": "celsius", "C13": "celsius", "C15": "celsius"},
    }


def daily_microphysics():

    def R(img):
        imag_cal_C13 = img["C13"]
        # como la banda 13 es
        realce_red = realce_gama(imag_cal_C13, 1, 1, 7.5, -53.5)
        return realce_red

    def G(img):
        imag_cal_C02 = img["C02"]
        realce_green = realce_gama(imag_cal_C02, 1, 1, 0, 0.78)
        return realce_green

    def B(img):
        imag_cal_C05 = img["C05"]
        realce_blue = realce_gama(imag_cal_C05, 1, 1, 0.01, 0.59)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C13", "C02", "C05"],
        "emissive_units": {"C13": "celsius"},
    }


def true_color():
    # voy a tener que reescalar las bandas por la resolucion
    def R(img):
        # breakpoint()
        imag_cal_C02 = img["C02"]
        realce_red = realce_percentil(imag_cal_C02)
        return realce_red

    def G(img):
        imag_cal_C03 = img["C03"]
        imag_cal_C02 = img["C02"]
        imag_cal_C01 = img["C01"]
        algebra = 0.45 * imag_cal_C02 + 0.1 * imag_cal_C03 + 0.45 * imag_cal_C01
        return realce_percentil(algebra)

    def B(img):
        imag_cal_C01 = img["C01"]
        return realce_percentil(imag_cal_C01)

    # return {"R": R, "G": G, "B": B}
    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C01", "C02", "C03"],
        "emissive_units": {},
    }


def fire_temperature():

    def R(img):
        imag_cal_C07 = img["C07"]
        realce_red = realce_gama(imag_cal_C07, 1, 0.4, 0, 60)
        return realce_red

    def G(img):
        imag_cal_C06 = img["C06"]
        realce_green = realce_gama(imag_cal_C06, 1, 1, 0, 1)
        return realce_green

    def B(img):
        imag_cal_C05 = img["C05"]
        realce_blue = realce_gama(imag_cal_C05, 1, 1, 0, 0.75)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C07", "C06", "C05"],
        "emissive_units": {"C07": "celsius"},
    }


def air_mass():

    def R(img):
        imag_cal_C08 = img["C08"]  # 6.2
        imag_cal_C10 = img["C10"]  # 7.3
        realce_red = realce_gama(imag_cal_C08 - imag_cal_C10, 1, 1, -26.2, 0.6)
        return realce_red

    def G(img):
        imag_cal_C12 = img["C12"]  # 9.6
        imag_cal_C13 = img["C13"]  # 10.3
        realce_green = realce_gama(imag_cal_C12 - imag_cal_C13, 1, 1, -43.2, 6.7)
        return realce_green

    def B(img):
        imag_cal_C08 = img["C08"]  # va invertida
        realce_blue = realce_gama((1 - imag_cal_C08), 1, 1, -29.25, -64.65)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C08", "C10", "C12", "C13"],
        "emissive_units": {
            "C08": "celsius",
            "C10": "celsius",
            "C12": "celsius",
            "C13": "celsius",
        },
    }


def ash():

    def R(img):
        imag_cal_C15 = img["C15"]
        imag_cal_C13 = img["C13"]
        realce_red = realce_gama(imag_cal_C15 - imag_cal_C13, 1, 1, -6.7, 2.6)
        return realce_red

    def G(img):
        imag_cal_C14 = img["C14"]
        imag_cal_C11 = img["C11"]
        realce_green = realce_gama(imag_cal_C14 - imag_cal_C11, 1, 1, -6.0, 6.3)
        return realce_green

    def B(img):
        imag_cal_C13 = img["C13"]
        realce_blue = realce_gama(imag_cal_C13, 1, 1, 243.6, 302.4)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C15", "C13", "C14", "C11"],
        "emissive_units": {
            "C15": "kelvin",
            "C13": "kelvin",
            "C14": "kelvin",
            "C11": "kelvin",
        },
    }


def day_cloud_convection():
    """
    Esta receta es para el producto de convección de nubes diurnas.
    """

    def R(img):
        imag_cal_C02 = img["C02"]
        realce_red = realce_gama(imag_cal_C02, 1, 1.7, 0, 1)
        return realce_red

    def G(img):
        imag_cal_C02 = img["C02"]
        realce_green = realce_gama(imag_cal_C02, 1, 1.7, 0, 1)
        return realce_green

    def B(img):
        imag_cal_C13 = img["C13"]
        realce_blue = realce_gama(imag_cal_C13, 1, 1, 49.85, -70.15)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C02", "C02", "C13"],
        "emissive_units": {"C13": "celsius"},
    }


def day_convection():
    """
    Esta receta es para el producto de convección diurna.
    """

    def R(img):
        # 6.2 - 7.3
        imag_cal_C08 = img["C08"]
        imag_cal_C10 = img["C10"]
        realce_red = realce_gama(imag_cal_C08 - imag_cal_C10, 1, 1, -35.0, 5.0)
        return realce_red

    def G(img):
        # 3.9 - 10.3
        imag_cal_C07 = img["C07"]
        imag_cal_C13 = img["C13"]
        realce_green = realce_gama(imag_cal_C07 - imag_cal_C13, 1, 1, -5.0, 60.0)
        return realce_green

    def B(img):
        # 1.6 - 0.64
        imag_cal_C05 = img["C05"]
        imag_cal_C02 = img["C02"]
        realce_blue = realce_gama(imag_cal_C05 - imag_cal_C02, 1, 1, -0.75, 0.25)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C08", "C10", "C07", "C13", "C05", "C02"],
        "emissive_units": {
            "C07": "celsius",
            "C08": "celsius",
            "C10": "celsius",
            "C13": "celsius",
        },
    }


def day_land_cloud():

    def R(img):
        # 1.6
        imag_cal_C05 = img["C05"]
        realce_red = realce_gama(imag_cal_C05, 1, 1, 0, 0.975)
        return realce_red

    def G(img):
        # 0.86
        imag_cal_C03 = img["C03"]
        realce_green = realce_gama(imag_cal_C03, 1, 1, 0, 1.086)
        return realce_green

    def B(img):
        # 0.64
        imag_cal_C02 = img["C02"]
        realce_blue = realce_gama(imag_cal_C02, 1, 1, 0, 1)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C02", "C03", "C05"],
        "emissive_units": {},
    }


def day_land_cloud_fire():

    def R(img):
        # 2.2
        imag_cal_C05 = img["C06"]
        realce_red = realce_gama(imag_cal_C05, 1, 1, 0, 1)
        return realce_red

    def G(img):
        # 0.86
        imag_cal_C03 = img["C03"]
        realce_green = realce_gama(imag_cal_C03, 1, 1, 0, 1)
        return realce_green

    def B(img):
        # 0.64
        imag_cal_C02 = img["C02"]
        realce_blue = realce_gama(imag_cal_C02, 1, 1, 0, 1)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C02", "C03", "C06"],
        "emissive_units": {},
    }


def day_snow_fog():

    def R(img):
        # 0.86
        imag_cal_C05 = img["C03"]
        realce_red = realce_gama(imag_cal_C05, 1, 1.7, 0, 1)
        return realce_red

    def G(img):
        # 1.6
        imag_cal_C03 = img["C05"]
        realce_green = realce_gama(imag_cal_C03, 1, 1.7, 0, 0.7)
        return realce_green

    def B(img):
        # 3.9-10.3
        imag_cal_C07 = img["C07"]
        imag_cal_C13 = img["C13"]
        realce_blue = realce_gama(imag_cal_C07 - imag_cal_C13, 1, 1.7, 0, 30)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C03", "C05", "C07", "C13"],
        "emissive_units": {"C07": "celsius", "C13": "celsius"},
    }


def simple_water_vapor():
    """
    Esta receta es para el producto de vapor de agua simple.
    """

    def R(img):
        imag_cal_C13 = img["C13"]
        realce_red = realce_gama(imag_cal_C13, 1, 1, 5.81, -70.86)
        return realce_red

    def G(img):
        imag_cal_C08 = img["C08"]
        realce_green = realce_gama(imag_cal_C08, 1, 1, -30.48, -58.49)
        return realce_green

    def B(img):
        imag_cal_C10 = img["C10"]
        realce_blue = realce_gama(imag_cal_C10, 1, 1, -12.12, -28.03)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C13", "C08", "C10"],
        "emissive_units": {"C13": "celsius", "C08": "celsius", "C10": "celsius"},
    }


def dust():
    """
    Esta receta es para el producto de polvo.
    """

    def R(img):
        # 12.3-10.3
        imag_cal_C15 = img["C15"]
        imag_cal_C13 = img["C13"]
        realce_red = realce_gama(imag_cal_C15 - imag_cal_C13, 1, 1, -6.7, 2.6)
        return realce_red

    def G(img):
        # 11.2-8.4
        imag_cal_C14 = img["C14"]
        imag_cal_C11 = img["C11"]
        realce_green = realce_gama(imag_cal_C14 - imag_cal_C11, 1, 2.5, -0.5, 20.0)
        return realce_green

    def B(img):
        # 10.3
        imag_cal_C13 = img["C13"]
        realce_blue = realce_gama(imag_cal_C13, 1, 1, -11.95, 15.55)
        return realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C11", "C13", "C14", "C15"],
        "emissive_units": {
            "C11": "celsius",
            "C13": "celsius",
            "C14": "celsius",
            "C15": "celsius",
        },
    }


def differential_water_vapor():

    def R(img):
        # 7.3-6.2
        imag_cal_C10 = img["C10"]
        imag_cal_C08 = img["C08"]
        realce_red = realce_gama(imag_cal_C10 - imag_cal_C08, 1, 0.2587, 30, -3)

        return 1 - realce_red

    def G(img):
        # 7.3
        imag_cal_C10 = img["C10"]
        realce_green = realce_gama(imag_cal_C10, 1, 0.4, 5, -60)
        return 1 - realce_green

    def B(img):
        # 6.2
        imag_cal_C08 = img["C08"]
        realce_blue = realce_gama(imag_cal_C08, 1, 0.4, -29.25, -64.65)
        return 1 - realce_blue

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C08", "C10"],
        "emissive_units": {"C08": "celsius", "C10": "celsius"},
    }
