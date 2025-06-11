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
        self.calibrated_images = {}
        #formas de hacerlo eficientes: solo calibrar segun las recipes
        #self.calibrate_images()

    def calibrate_images(self):
        for band in self.abi_image.channels:
            band_array = self.abi_image.get_band_array(band)
            metadata = self.abi_image.datasets[band]["metadata"]
            self.calibrated_images[band] = calibrate_imag(band_array, metadata)
    def generate_all(self):
        for name, recipe in self.recipes.items():
            product = RGBProduct(abi_image=self.abi_image, name=name, recipe=recipe, recorte=self.recorte, calibrated_images=self.calibrated_images)
            self.products[name] = product.build()

    def get_product(self, name):
        return self.products[name]
