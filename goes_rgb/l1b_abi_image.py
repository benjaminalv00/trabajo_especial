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

    def get_calibrated_data(self):
        # Aplica calibración a todas las bandas y las guarda en self.calibrated_data
        for band in self.channels:
            self.calibrated_data[band] = self.calibrate_band(
                band, self.datasets[band]["band_array"]
            )
            band_array = self.get_band_array(band)
            metadata = self.datasets[band]["metadata"]
            kind = "T" if band in ["C07", "C13", "C08", "C10", "C12"] else "Ref"
            self.calibrated_data[band] = calibrate_imag(
                band_array, metadata, U=kind
            )  # Ojo porque depende de la banda
        return self.calibrated_data

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
        return (
            crs,
            x,
        )
