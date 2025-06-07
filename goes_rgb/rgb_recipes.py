from goes_rgb.helpers import calibrate_imag
from goes_rgb.helpers import realce_gama
import numpy as np
def microfisica_nocturna():
    def R(img): 
        imag_cal_C15 = calibrate_imag(img.get_band_array("C15"),img.datasets["C15"]["metadata"])
        imag_cal_C13 = calibrate_imag(img.get_band_array("C13"),img.datasets["C13"]["metadata"])
        realce_red = realce_gama(imag_cal_C15 - imag_cal_C13,1,1,-6.7,2.6)
        return realce_red 
    def G(img): 
        imag_cal_C13 = calibrate_imag(img.get_band_array("C13"),img.datasets["C13"]["metadata"])
        imag_cal_C07 = calibrate_imag(img.get_band_array("C07"),img.datasets["C07"]["metadata"])
        realce_green = realce_gama(imag_cal_C13 - imag_cal_C07,1,1,-3.1,5.2)
        return realce_green
    def B(img): 
        imag_cal_C13 = calibrate_imag(img.get_band_array("C13"),img.datasets["C13"]["metadata"])
        realce_blue = realce_gama(imag_cal_C13,1,1,-29.6,19.5)
        return realce_blue
    
    return {"R": R, "G": G, "B": B}

def true_color():
    #voy a tener que reescalar las bandas por la resolucion
    def R(img): 
        imag_cal_C02 = calibrate_imag(img.get_band_array("C02"),img.datasets["C02"]["metadata"])
        return imag_cal_C02
    def G(img): 
        imag_cal_C03 = calibrate_imag(img.get_band_array("C03"),img.datasets["C03"]["metadata"])
        imag_cal_C02 = calibrate_imag(img.get_band_array("C02"),img.datasets["C02"]["metadata"])
        imag_cal_C01 = calibrate_imag(img.get_band_array("C01"),img.datasets["C01"]["metadata"])
        return 0.45*imag_cal_C02 + 0.1*imag_cal_C03 + 0.45*imag_cal_C01
    def B(img):
        imag_cal_C01 = calibrate_imag(img.get_band_array("C01"),img.datasets["C01"]["metadata"])
        return imag_cal_C01

    return {"R": R, "G": G, "B": B}
