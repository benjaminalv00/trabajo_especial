__SAFE_RECIPE__ = True
import numpy as np
from goes_rgb.helpers import realce_gama


def recipe():
    """
    Cicatriz de quemado (Burn Scar RGB), producto no oficial de NOAA.

    Basado en el NBR (Normalized Burn Ratio, Key & Benson, 2006):
        NBR = (C03 - C06) / (C03 + C06)
    Adaptación a bandas ABI según Roy, D.P., Li, Z., Giglio, L., Boschetti, L.,
    Huang, H. (2021), "Spectral and diurnal temporal suitability of GOES ABI
    reflectance for burned area mapping", Int. J. Applied Earth Observation
    and Geoinformation 96:102271, doi:10.1016/j.jag.2020.102271.

    R = realce_gama(NBR, A=1, gama=0.5, Vmin=0.0, Vmax=-0.15)
        -- invertido y no lineal: NBR >= 0 (neutro/vegetacion) -> R = 0;
           NBR <= -0.15 (quemado) -> R satura en 1; gama=0.5 concentra el
           contraste hacia el extremo negativo, igual que hace `fire_temperature`
           con su propio canal termico.
    G = clip(C03 / 0.5, 0, 1)  -- reflectancia NIR (0.86 um)
    B = clip(C02 / 0.4, 0, 1)  -- reflectancia rojo (0.64 um)

    Ajuste empirico (calibrado contra una escena real de Cordoba, GOES-16,
    2024-09-24): el offset original R = 0.6 - NBR pintaba con rojo notorio
    (R=0.6) cualquier pixel con NBR neutro, que en esta escena es ~48% del
    area -- diluyendo la cicatriz real. Los umbrales Vmin=0.0/Vmax=-0.15 se
    fijaron mirando el histograma de NBR de esa escena: el 96%+ de los
    valores negativos caen dentro de [-0.15, 0), asi que saturar en -0.15
    deja la cola realmente extrema (<0.2% de los pixeles) en rojo pleno sin
    tocar el fondo neutro. Sujeto a validarse con mas escenas.

    Sobre agua profunda C03 y C06 tienden a 0 y el NBR se vuelve inestable;
    se enmascara donde (C03 + C06) < 0.02 y se fuerza R = 0 ahi.
    """

    def R(img):
        c03 = img["C03"]
        c06 = img["C06"]
        denom = c03 + c06
        valid = denom >= 0.02
        nbr = np.zeros_like(denom, dtype=float)
        nbr[valid] = (c03[valid] - c06[valid]) / denom[valid]
        r = realce_gama(nbr, 1, 0.5, 0.0, -0.15)
        r[~valid] = 0
        return r

    def G(img):
        return np.clip(img["C03"] / 0.5, 0, 1)

    def B(img):
        return np.clip(img["C02"] / 0.4, 0, 1)

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C02", "C03", "C06"],
        "emissive_units": {},
    }
