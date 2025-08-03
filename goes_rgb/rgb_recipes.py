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

    return {"R": R, "G": G, "B": B}


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

    return {"R": R, "G": G, "B": B}


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

    return {"R": R, "G": G, "B": B}


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

    return {"R": R, "G": G, "B": B}


def fire_temperature_2():

    def R(img):
        imag_cal_C13 = img["C13"]
        realce_red = realce_gama(imag_cal_C13, 1, 0.4, 0, 60)
        return realce_red

    def G(img):
        imag_cal_C06 = img["C06"]
        realce_green = realce_gama(imag_cal_C06, 1, 1, 0, 1)
        return realce_green

    def B(img):
        imag_cal_C05 = img["C05"]
        realce_blue = realce_gama(imag_cal_C05, 1, 1, 0, 0.75)
        return realce_blue

    return {"R": R, "G": G, "B": B}


def fire_temperature_3():

    def R(img):
        imag_cal_C14 = img["C14"]
        realce_red = realce_gama(imag_cal_C14, 1, 0.4, 0, 60)
        return realce_red

    def G(img):
        imag_cal_C06 = img["C06"]
        realce_green = realce_gama(imag_cal_C06, 1, 1, 0, 1)
        return realce_green

    def B(img):
        imag_cal_C05 = img["C05"]
        realce_blue = realce_gama(imag_cal_C05, 1, 1, 0, 0.75)
        return realce_blue

    return {"R": R, "G": G, "B": B}


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

    return {"R": R, "G": G, "B": B}
