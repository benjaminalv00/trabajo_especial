from goes_rgb.aws_interface import download_goes_files_for_datetime
from goes_rgb.reader import open_goes_file
from goes_rgb.helpers import get_pixel_indices_from_latlon_bbox
import cartopy.crs as ccrs


class ABIImage:
    def __init__(
        self,
        dt,
        product="ABI-L2-MCMIPF",
        channels=[f"C{str(i).zfill(2)}" for i in range(1, 17)],
        satellite="noaa-goes16",
        local_dir="data",
    ):
        self.dt = dt
        self.product = product
        self.channels = channels
        self.satellite = satellite
        self.local_dir = local_dir
        self.files = []
        self.datasets = {}
        self.mcmi_ds = None  # Dataset para MCMI si se usa el producto L2. Ver de abstraerse y que todo quede en datasets

    def download(self):
        self.files = download_goes_files_for_datetime(
            self.dt, self.product, self.channels, self.satellite, self.local_dir
        )

    def open(self):
        if self.product == "ABI-L2-MCMIPF":
            # Abrir solo un archivo NetCDF MCMI y cargar todas las bandas
            self.mcmi_ds = open_goes_file(self.files[0])

            for ch in self.channels:
                var_name = f"CMI_{ch}"
                if var_name in self.mcmi_ds.variables:
                    band_variables = self.mcmi_ds.variables[var_name][:]
                    # Asegurarse de que sea 2D (puede tener shape (1, y, x))
                    if band_variables.ndim == 3:
                        band_variables = band_variables[0]
                    self.datasets[ch] = {
                        "band_array": band_variables.values,
                        "metadata": self.mcmi_ds.variables[var_name],
                        "ds": self.mcmi_ds,
                    }
                    # breakpoint()
            # self.mcmi_ds.close()
        else:
            # Modo clásico: archivos individuales por banda
            for path in self.files:
                ds = open_goes_file(path)
                band = f"C{ds.band_id.values.item():02}"
                metadata = ds.variables
                band_array = ds["Rad"].values
                if band_array.shape == (10848, 10848):  # resolucion 1 km
                    band_array = band_array[::2, ::2]
                elif band_array.shape == (21696, 21696):  # resolucion 0.5 km
                    band_array = band_array[::4, ::4]
                elif band_array.shape == (5424, 5424):  # resolucion 2 km
                    pass
                self.datasets[band] = {
                    "band_array": band_array,
                    "metadata": metadata,
                    "ds": ds,
                }
                ds.close()

    def get_band_array(self, band):
        return self.datasets[band]["band_array"]

    def get_projection_params(self):
        ch = self.channels[0]
        ds = self.datasets[ch]["ds"]
        if self.product == "ABI-L2-MCMIPF":
            # breakpoint()
            proj_attrs = ds["goes_imager_projection"].attrs
            # En MCMI, las coordenadas suelen estar como variables x/y
            altura = proj_attrs["perspective_point_height"]
            lon_cen = proj_attrs["longitude_of_projection_origin"]
            x = ds.variables["x"].values * altura
            y = ds.variables["y"].values * altura
        else:
            proj_attrs = ds["goes_imager_projection"].attrs
            altura = proj_attrs["perspective_point_height"]
            lon_cen = proj_attrs["longitude_of_projection_origin"]
            x = ds.coords["x"].values * altura
            y = ds.coords["y"].values * altura
            while x.shape != (5424,):
                x = x[::2]
                y = y[::2]
        crs = ccrs.Geostationary(central_longitude=lon_cen, satellite_height=altura)
        return crs, x, y

    def get_bbox_indices(self, lat_ini, lat_fin, lon_ini, lon_fin):
        crs, x, y = self.get_projection_params()
        return get_pixel_indices_from_latlon_bbox(
            lat_ini, lat_fin, lon_ini, lon_fin, x, y, crs
        )
