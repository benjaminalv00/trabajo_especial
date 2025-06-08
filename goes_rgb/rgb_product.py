import numpy as np
from goes_rgb.helpers import resample_to_shape

class RGBProduct:
    def __init__(self, abi_image, name, recipe,recorte=None):
        self.image = abi_image
        self.name = name
        self.recipe = recipe  # Dict con funciones R, G, B
        self.recorte = recorte # Recorte de la imagen RGB 

    def build(self):
        R = self.recipe["R"](self.image)
        G = self.recipe["G"](self.image)
        B = self.recipe["B"](self.image)
        # Asegurar que las bandas tengan la misma forma, capaz es mejor hacerlo dentro de la receta
        if R.shape != G.shape or R.shape != B.shape:
            #cambiar la resolucion de la roja
            R = resample_to_shape(R, G.shape)
        # Aplicar recorte si se especifica
        if self.recorte is not None:
            f0, f1, c0, c1 = self.recorte
            R = R[f0:f1, c0:c1]
            G = G[f0:f1, c0:c1]
            B = B[f0:f1, c0:c1]
        rgb = np.stack([R, G, B], axis=-1)
        rgb = np.clip(rgb, 0, 1)
        return rgb
