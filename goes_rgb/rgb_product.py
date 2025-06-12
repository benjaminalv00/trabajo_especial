import numpy as np
from goes_rgb.helpers import resample_to_shape


class RGBProduct:
    def __init__(self, abi_image, name, calibrated_images, recipe, recorte=None):
        self.image = abi_image
        self.name = name
        self.abi_image = abi_image
        self.recipe = recipe  # Dict con funciones R, G, B
        self.recorte = recorte  # Recorte de la imagen RGB
        self.calibrated_images = calibrated_images

    def build(self):

        R = self.recipe["R"](self.calibrated_images)
        G = self.recipe["G"](self.calibrated_images)
        B = self.recipe["B"](self.calibrated_images)

        # Aplicar recorte si se especifica
        if self.recorte is not None:
            f0, f1, c0, c1 = self.recorte
            R = R[f0:f1, c0:c1]
            G = G[f0:f1, c0:c1]
            B = B[f0:f1, c0:c1]
        rgb = np.stack([R, G, B], axis=-1)
        rgb = np.clip(rgb, 0, 1)

        return rgb
