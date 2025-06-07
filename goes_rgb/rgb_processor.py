from goes_rgb.rgb_product import RGBProduct
from goes_rgb.helpers import calibrate_imag

class RGBProcessor:
    def __init__(self, abi_image, recipes,recorte=None):
        """
        recipes: dict {product_name: recipe_dict}
        """
        self.abi_image = abi_image
        self.recipes = recipes
        self.recorte = recorte
        self.products = {}
    # Ojoo
    def calibrate_images(self):
        for band in self.abi_image.channels:
            self.abi_image.get_band_array(band)
            self.abi_image.datasets[band]["data"] = calibrate_imag(self.abi_image.get_band_array(band), 
                           self.abi_image.datasets[band]["metadata"])
    def generate_all(self):
        for name, recipe in self.recipes.items():
            product = RGBProduct(self.abi_image, name, recipe,self.recorte)
            self.products[name] = product.build()

    def get_product(self, name):
        return self.products[name]
