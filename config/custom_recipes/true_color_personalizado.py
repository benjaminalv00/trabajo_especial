__SAFE_RECIPE__ = True
from goes_rgb.helpers import realce_percentil


def recipe():
    """True color personalizado simple, autosuficiente y seguro para auto-registro."""

    def R(img):
        return realce_percentil(img["C02"])

    def G(img):
        c03 = img["C03"]
        c02 = img["C02"]
        c01 = img["C01"]
        mezcla = 0.45 * c02 + 0.10 * c03 + 0.45 * c01
        return realce_percentil(mezcla)

    def B(img):
        return realce_percentil(img["C01"])

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C01", "C02", "C03"],
        "emissive_units": {},
    }
