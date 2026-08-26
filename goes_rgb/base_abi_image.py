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
        # Ventana de lectura (f0, f1, c0, c1) en indices de pixel, o None
        # para el disco completo. Ver set_window().
        self.window = None

    def download(self):
        # manejar mejor que pasa si no hay archivos
        self.files = download_goes_files_for_datetime(
            self.dt, self.product, self.channels, self.satellite, self.local_dir
        )
        if not self.files:
            raise FileNotFoundError(
                "No files were found for the specified date and product."
            )

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def get_projection_params(self):
        pass

    @abstractmethod
    def calibrate_band(self, band, raw_data, unit=None):
        """
        Método abstracto para calibrar una banda específica.
        Cada clase concreta debe implementar su propia lógica de calibración.
        """
        pass

    def set_window(self, f0, f1, c0, c1):
        """
        Limita la lectura de bandas a la ventana [f0:f1, c0:c1].

        Fijarla antes de pedir bandas evita leer y procesar el disco completo
        cuando solo interesa un recorte: las subclases leen del NetCDF unicamente
        ese bloque. Invalida las bandas perezosas ya materializadas, porque
        quedaron cacheadas con la ventana anterior.
        """
        nueva = (int(f0), int(f1), int(c0), int(c1))
        if nueva == self.window:
            return
        self.window = nueva
        for entrada in self.datasets.values():
            if isinstance(entrada, dict) and entrada.get("lazy"):
                entrada["band_array"] = None

    def _aplicar_window(self, arr):
        """Recorta un array 2D a la ventana activa (no-op si no hay ventana)."""
        if self.window is None:
            return arr
        f0, f1, c0, c1 = self.window
        return arr[f0:f1, c0:c1]

    def get_band_array(self, band):
        # Método común opcional
        return self.datasets[band]["band_array"]

    def get_bbox_indices(self, lat_ini, lat_fin, lon_ini, lon_fin):
        crs, x, y = self.get_projection_params()
        return get_pixel_indices_from_latlon_bbox(
            lat_ini, lat_fin, lon_ini, lon_fin, x, y, crs
        )
