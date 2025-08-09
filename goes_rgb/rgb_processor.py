from goes_rgb.rgb_product import RGBProduct
from goes_rgb.helpers import calibrate_imag, band_is_emissive


class RGBProcessor:
    def __init__(self, abi_image, recipes, recorte=None):
        """
        recipes: dict {product_name: recipe_dict}
        """
        self.abi_image = abi_image
        self.recipes = recipes
        self.recorte = recorte
        self.products = {}
        # formas de hacerlo eficientes: solo calibrar segun las recipes
        # Ojo aca porque en realidad la calibracion depende de la banda
        # Preguntar a sergio si esto es cierto, o puedo calibrar bandas random por
        # Cualquier cosa

    def calibrate_images_for_recipe(self, recipe):
        """
        Calibra solo las bandas necesarias para una receta específica.
        """
        bands_needed = recipe["bands"]
        units = recipe["emissive_units"]
        calibrated = {}

        for band in bands_needed:
            raw = self.abi_image.get_band_array(band)
            # Calibrar segun unidad que pide la receta
            if band_is_emissive(band):
                arr = self.abi_image.calibrate_band(band, raw, units[band])
            else:
                arr = raw
            calibrated[band] = arr

        return calibrated

    def generate_all(self):
        for name, recipe in self.recipes.items():
            calibrated_images = self.calibrate_images_for_recipe(recipe)
            product = RGBProduct(
                abi_image=self.abi_image,
                name=name,
                recipe=recipe,
                recorte=self.recorte,
                calibrated_images=calibrated_images,
            )
            self.products[name] = product.build()

    def get_product(self, name):
        return self.products[name]
