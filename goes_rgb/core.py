from goes_rgb.aws_interface import download_goes_files_for_datetime
from goes_rgb.reader import open_goes_file
from goes_rgb.helpers import get_pixel_indices_from_latlon_bbox
import cartopy.crs as ccrs

class ABIImage:
    def __init__(self, dt, product, channels=["C01","C02","C03"], satellite="noaa-goes16", local_dir="data"):
        self.dt = dt
        self.product = product
        self.channels = channels
        self.satellite = satellite
        self.local_dir = local_dir
        self.files = []
        self.datasets = {}

    def download(self):
        self.files = download_goes_files_for_datetime(
            self.dt, self.product, self.channels, self.satellite, self.local_dir
        )

    def open(self):
        for path in self.files:
            ds = open_goes_file(path)
            band = f"C{ds.band_id.values.item():02}"
            metadata = ds.variables
            self.datasets[band] = {"ds":ds, "metadata":metadata}

    def get_band_array(self, band):
        return self.datasets[band]["ds"]["Rad"].values

    def get_projection_params(self):
        ch = self.channels[0] # o cualquier canal (ojo con la resolucion)
        ds = self.datasets[ch]["ds"]  # Dataset del primer canal como ejemplo
        proj_attrs = ds['goes_imager_projection'].attrs
        altura = proj_attrs['perspective_point_height']
        lon_cen = proj_attrs['longitude_of_projection_origin']
        x = ds.coords['x'].values * altura
        y = ds.coords['y'].values * altura
        crs = ccrs.Geostationary(central_longitude=lon_cen, satellite_height=altura)
        return crs, x, y

    def get_bbox_indices(self, lat_ini, lat_fin, lon_ini, lon_fin):
        crs, x, y = self.get_projection_params()
        return get_pixel_indices_from_latlon_bbox(lat_ini, lat_fin, lon_ini, lon_fin, x, y, crs)
