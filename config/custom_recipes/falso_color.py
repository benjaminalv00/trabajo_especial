__SAFE_RECIPE__ = True
from goes_rgb.helpers import realce_percentil


def recipe():
    """Falso color rápido: C05 -> R, C03 -> G, C02 -> B."""

    def R(img):
        return realce_percentil(img["C05"])

    def G(img):
        return realce_percentil(img["C03"])

    def B(img):
        return realce_percentil(img["C02"])

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C02", "C03", "C05"],
        "emissive_units": {},
    }
