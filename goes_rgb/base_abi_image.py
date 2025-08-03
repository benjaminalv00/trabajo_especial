from abc import ABC, abstractmethod
from goes_rgb.helpers import get_pixel_indices_from_latlon_bbox
from goes_rgb.aws_interface import download_goes_files_for_datetime


class BaseABIImage(ABC):
    """
    Clase base abstracta para representar imágenes ABI de GOES.

    Define la interfaz mínima que deben implementar todas las clases concretas
    para manejar distintos tipos de productos (L1b, MCMI, etc).

    Métodos abstractos:
        - download(): Descarga los archivos necesarios para la imagen.
        - open(): Abre y prepara los datos para su uso.
        - calibrate_band(band, array): Aplica la calibración correspondiente a una banda.

    Métodos comunes:
        - get_band_array(band): Devuelve el array de datos de la banda solicitada.
        - get_bbox_indices(lat_ini, lat_fin, lon_ini, lon_fin):
            Calcula los índices de píxeles correspondientes a un bounding box definido por coordenadas lat/lon.

    """

    def __init__(self, dt, product, channels, satellite, local_dir):
        self.dt = dt
        self.product = product
        self.channels = channels
        self.satellite = satellite
        self.local_dir = local_dir
        self.files = []
        self.datasets = {}
        self.calibrated_data = {}  # Almacena datos calibrados por banda

    def download(self):
        self.files = download_goes_files_for_datetime(
            self.dt, self.product, self.channels, self.satellite, self.local_dir
        )

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def get_calibrated_data(self):
        """
        Método abstracto para obtener los datos calibrados de las bandas.
        Cada clase concreta debe implementar su propia lógica de calibración.
        """
        pass

    @abstractmethod
    def get_projection_params(self):
        pass

    def get_band_array(self, band):
        # Método común opcional
        return self.datasets[band]["band_array"]

    def get_bbox_indices(self, lat_ini, lat_fin, lon_ini, lon_fin):
        crs, x, y = self.get_projection_params()
        return get_pixel_indices_from_latlon_bbox(
            lat_ini, lat_fin, lon_ini, lon_fin, x, y, crs
        )
