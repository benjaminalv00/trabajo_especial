from goes_rgb.rgb_product import RGBProduct
from goes_rgb.helpers import calibrate_imag


class RGBProcessor:
    def __init__(self, abi_image, recipes, recorte=None):
        """
        recipes: dict {product_name: recipe_dict}
        """
        self.abi_image = abi_image
        self.recipes = recipes
        self.recorte = recorte
        self.products = {}
        self.calibrated_images = {}
        # formas de hacerlo eficientes: solo calibrar segun las recipes
        # Ojo aca porque en realidad la calibracion depende de la banda
        # Preguntar a sergio si esto es cierto, o puedo calibrar bandas random por
        # Cualquier cosa

        self.calibrate_images()

    def calibrate_images(self):
        self.calibrated_images = self.abi_image.get_calibrated_data()

    def generate_all(self):
        for name, recipe in self.recipes.items():
            product = RGBProduct(
                abi_image=self.abi_image,
                name=name,
                recipe=recipe,
                recorte=self.recorte,
                calibrated_images=self.calibrated_images,
            )
            self.products[name] = product.build()

    def get_product(self, name):
        return self.products[name]
