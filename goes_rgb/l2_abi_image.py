from goes_rgb.base_abi_image import BaseABIImage
from goes_rgb.reader import open_goes_file
import cartopy.crs as ccrs


class ABIImageMCMI(BaseABIImage):
    """
    Clase concreta para representar imágenes ABI de tipo MCMI.
    Implementa los métodos necesarios para descargar, abrir y calibrar bandas.
    """

    def __init__(
        self,
        dt,
        product="ABI-L2-MCMIPF",
        channels=None,
        satellite="noaa-goes16",
        local_dir="data",
    ):
        if channels is None:
            channels = [f"C{str(i).zfill(2)}" for i in range(1, 17)]
        super().__init__(dt, product, channels, satellite, local_dir)

    def open(self):
        # Abrir solo un archivo NetCDF MCMI y cargar todas las bandas
        self.mcmi_ds = open_goes_file(self.files[0])
        for ch in self.channels:
            var_name = f"CMI_{ch}"
            if var_name in self.mcmi_ds.variables:
                band_variables = self.mcmi_ds.variables[var_name][:]
                # Asegurarse de que sea 2D (puede tener shape (1, y, x)) ??
                if band_variables.ndim == 3:
                    band_variables = band_variables[0]
                self.datasets[ch] = {
                    "band_array": band_variables.values,
                    "metadata": self.mcmi_ds.variables[var_name],
                    "ds": self.mcmi_ds,
                }

    def calibrate_band(self, band, raw_data, unit=None):
        """
        Calibrar una banda específica según la unidad requerida.
        """
        if unit is None:
            unit = "celsius"
        if unit == "celsius":
            # Convertir de Kelvin a Celsius
            return raw_data - 273.15
        elif unit == "kelvin":
            # No se requiere conversión, retornar el array original
            return raw_data
        else:
            raise ValueError(f"Unidad de calibración no soportada: {unit}")

    def get_band_array(self, band):
        """
        Devuelve el array de datos de la banda solicitada.
        """
        if band in self.datasets:
            return self.datasets[band]["band_array"]
        else:
            raise ValueError(f"Banda {band} no encontrada en los datasets.")

    def get_projection_params(self):
        # Implementación específica para obtener parámetros de proyección de MCMI (ligeramente diferente a L1b)
        ch = self.channels[0]
        ds = self.datasets[ch]["ds"]
        proj_attrs = ds["goes_imager_projection"].attrs
        # En MCMI, las coordenadas suelen estar como variables x/y
        altura = proj_attrs["perspective_point_height"]
        lon_cen = proj_attrs["longitude_of_projection_origin"]
        x = ds.variables["x"].values * altura
        y = ds.variables["y"].values * altura

        crs = ccrs.Geostationary(central_longitude=lon_cen, satellite_height=altura)
        return crs, x, y
