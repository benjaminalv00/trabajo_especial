from goes_rgb.helpers import calibrate_imag
from goes_rgb.helpers import realce_gama,realce_p,realce_percentil
import numpy as np
def microfisica_nocturna():
    def R(img): 
        imag_cal_C15 = img["C15"]
        imag_cal_C13 = img["C13"]
        realce_red = realce_gama(imag_cal_C15 - imag_cal_C13,1,1,-6.7,2.6)
        return realce_red 
    def G(img): 
        imag_cal_C13 = img["C13"]
        imag_cal_C07 = img["C07"]
        realce_green = realce_gama(imag_cal_C13 - imag_cal_C07,1,1,-3.1,5.2)
        return realce_green
    def B(img): 
        imag_cal_C13 = img["C13"]
        realce_blue = realce_gama(imag_cal_C13,1,1,-29.6,19.5)
        return realce_blue
    
    return {"R": R, "G": G, "B": B}

def true_color():
    #voy a tener que reescalar las bandas por la resolucion
    def R(img): 
        imag_cal_C02 = img["C02"]
        realce_red = realce_percentil(imag_cal_C02)
        return realce_red
    def G(img): 
        imag_cal_C03 = img["C03"]
        imag_cal_C02 = img["C02"]
        imag_cal_C01 = img["C01"]
        algebra = 0.45*imag_cal_C02 + 0.1*imag_cal_C03 + 0.45*imag_cal_C01
        return realce_percentil(algebra)
    def B(img):
        imag_cal_C01 = img["C01"]
        return realce_percentil(imag_cal_C01)

    return {"R": R, "G": G, "B": B}


# def fire_temperature():
#     def R(img):

