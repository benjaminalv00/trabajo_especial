from goes_rgb.base_abi_image import BaseABIImage
from goes_rgb.reader import open_goes_file
from goes_rgb.helpers import calibrate_imag

import cartopy.crs as ccrs


class ABIImageL1b(BaseABIImage):
    """
    Clase concreta para representar imágenes ABI de tipo L1b.
    Implementa los métodos necesarios para descargar, abrir y calibrar bandas.
    """

    def __init__(
        self,
        dt,
        product="ABI-L1b-RadF",
        channels=None,
        satellite="noaa-goes16",
        local_dir="data",
    ):
        if channels is None:
            channels = [f"C{str(i).zfill(2)}" for i in range(1, 17)]
        super().__init__(dt, product, channels, satellite, local_dir)

    def open(self):
        # Abrir archivos individuales por banda y cargar los datos
        for path in self.files:
            ds = open_goes_file(path)
            band = f"C{ds.band_id.values.item():02}"
            metadata = ds.variables
            band_array = ds["Rad"].values
            # Reescalado según resolución de la banda
            if band_array.shape == (10848, 10848):  # 1 km
                band_array = band_array[::2, ::2]
            elif band_array.shape == (21696, 21696):  # 0.5 km
                band_array = band_array[::4, ::4]
            # Si es 2 km, no hace falta reescalar
            self.datasets[band] = {
                "band_array": band_array,
                "metadata": metadata,
                "ds": ds,
            }
            ds.close()

    def calibrate_band(self, band, raw_data, unit=None):
        """
        Calibrar una banda específica según la unidad requerida.
        Como sabemos, la calibracion de l1b es a Celsius
        """
        if unit is None:
            unit = "celsius"
        if unit == "celsius":
            # Convertir de Kelvin a Celsius
            return raw_data
        elif unit == "kelvin":
            # No se requiere conversión, retornar el array original
            return raw_data + 273.15
        else:
            raise ValueError(f"Unidad de calibración no soportada: {unit}")

    def get_band_array(self, band):
        """
        Devuelve el array de datos de la banda solicitada.

        A diferencia de MCMI, L1b trae un NetCDF por banda y open() los lee
        completos, asi que aca la ventana no ahorra I/O: se aplica antes de
        calibrar para que calibrate_imag opere solo sobre el recorte.
        """
        if band in self.datasets:
            emissive_bands = [
                "C07",
                "C08",
                "C09",
                "C10",
                "C11",
                "C12",
                "C13",
                "C14",
                "C15",
                "C16",
            ]
            return calibrate_imag(
                self._aplicar_window(self.datasets[band]["band_array"]),
                self.datasets[band]["metadata"],
                U="Ref" if band not in emissive_bands else "T",
            )
        else:
            raise ValueError(f"Banda {band} no encontrada en los datasets.")

    def get_projection_params(self):
        # Obtiene los parámetros de proyección para L1b
        ch = self.channels[0]
        ds = self.datasets[ch]["ds"]
        proj_attrs = ds["goes_imager_projection"].attrs
        altura = proj_attrs["perspective_point_height"]
        lon_cen = proj_attrs["longitude_of_projection_origin"]
        x = ds.coords["x"].values * altura
        y = ds.coords["y"].values * altura
        # Reescalado para igualar shape si es necesario
        while x.shape != (5424,):
            x = x[::2]
            y = y[::2]
        crs = ccrs.Geostationary(central_longitude=lon_cen, satellite_height=altura)
        return crs, x, y
