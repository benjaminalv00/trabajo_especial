from goes_rgb.helpers import calibrate_imag
from goes_rgb.helpers import realce_gama
import numpy as np
def microfisica_nocturna():
    def R(img): 
        imag_cal_C15 = img["C15"]
        imag_cal_C13 = img["C13"]
        realce_red = realce_gama(imag_cal_C15 - imag_cal_C13,1,1,-6.7,2.6)
        breakpoint()
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
        imag_cal_C02 = img["C02"][::4,::4]
        realce_red = realce_gama(imag_cal_C02, Vmin=imag_cal_C02.min(), Vmax=imag_cal_C02.max(), A=1, gama=1)
        return imag_cal_C02
    def G(img): 
        #imag_cal_C03 = img["C03"][::2,::2]
        #imag_cal_C02 = img["C02"][::4,::4]
        #imag_cal_C01 = img["C01"][::2,::2]
        #algebra = 0.45*imag_cal_C02 + 0.1*imag_cal_C03 + 0.45*imag_cal_C01
        #realce_green = realce_gama(algebra, Vmin=algebra.min(), Vmax=algebra.max(), A=1, gama=1)
        return np.zeros_like(img["C01"][::2,::2])  # Placeholder, no se usa C03 en true color
    def B(img):
        imag_cal_C01 = img["C01"][::2,::2]
        realce_blue = realce_gama(imag_cal_C01, Vmin=imag_cal_C01.min(), Vmax=imag_cal_C01.max(), A=1, gama=1)
        return np.zeros_like(imag_cal_C01)

    return {"R": R, "G": G, "B": B}


# def fire_temperature():

#     def R(img):

