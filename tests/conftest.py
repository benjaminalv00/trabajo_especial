import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _install_pyproj_stub():
    module = types.ModuleType("pyproj")
    module.__path__ = []

    exceptions_module = types.ModuleType("pyproj.exceptions")

    class ProjError(Exception):
        pass

    exceptions_module.ProjError = ProjError

    class _Transformer:
        @staticmethod
        def from_crs(*args, **kwargs):
            class _IdentityTransformer:
                def transform(self, x, y):
                    return x, y

            return _IdentityTransformer()

    class _CRS:
        def __init__(self, srs=""):
            self.srs = srs

        @staticmethod
        def from_user_input(value, **kwargs):
            return _CRS(str(value))

        @staticmethod
        def from_string(value):
            return _CRS(str(value))

        @property
        def proj4_init(self):
            return self.srs

    class _Geod:
        def __init__(self, *args, **kwargs):
            pass

        def inv(self, *args, **kwargs):
            return 0.0, 0.0, 0.0

    module.Transformer = _Transformer
    module.CRS = _CRS
    module.Geod = _Geod
    sys.modules["pyproj"] = module
    sys.modules["pyproj.exceptions"] = exceptions_module


def _install_rasterio_stub():
    rasterio_module = types.ModuleType("rasterio")
    transform_module = types.ModuleType("rasterio.transform")
    crs_module = types.ModuleType("rasterio.crs")

    def _from_bounds(*args, **kwargs):
        return args

    def _from_origin(*args, **kwargs):
        return args

    class _CRS:
        def __init__(self, proj4_init=""):
            self.proj4_init = proj4_init

        @staticmethod
        def from_string(value):
            return _CRS(value)

    class _DatasetWriter:
        def __init__(self, output_path, **kwargs):
            self.output_path = Path(output_path)
            self.kwargs = kwargs
            self.writes = []

        def __enter__(self):
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.touch(exist_ok=True)
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, array, band_index):
            self.writes.append((band_index, array))

    def _open(output_path, *args, **kwargs):
        writer = _DatasetWriter(output_path, **kwargs)
        rasterio_module._last_writer = writer
        return writer

    transform_module.from_bounds = _from_bounds
    transform_module.from_origin = _from_origin
    crs_module.CRS = _CRS
    rasterio_module.open = _open
    rasterio_module._DatasetWriter = _DatasetWriter

    sys.modules["rasterio"] = rasterio_module
    sys.modules["rasterio.transform"] = transform_module
    sys.modules["rasterio.crs"] = crs_module


def _install_scipy_stub():
    scipy_module = types.ModuleType("scipy")
    ndimage_module = types.ModuleType("scipy.ndimage")

    def _zoom(array, factors, order=1):
        import numpy as _np

        result = _np.asarray(array)
        for axis, factor in enumerate(factors):
            target_size = max(1, int(round(result.shape[axis] * factor)))
            indices = _np.linspace(0, result.shape[axis] - 1, target_size).astype(int)
            result = _np.take(result, indices, axis=axis)
        return result

    ndimage_module.zoom = _zoom
    scipy_module.ndimage = ndimage_module

    sys.modules["scipy"] = scipy_module
    sys.modules["scipy.ndimage"] = ndimage_module


def _install_cartopy_stub():
    cartopy_module = types.ModuleType("cartopy")
    cartopy_module.__path__ = []

    crs_module = types.ModuleType("cartopy.crs")
    feature_module = types.ModuleType("cartopy.feature")
    io_module = types.ModuleType("cartopy.io")
    shapereader_module = types.ModuleType("cartopy.io.shapereader")

    class _Geostationary:
        def __init__(self, central_longitude=None, satellite_height=None):
            self.central_longitude = central_longitude
            self.satellite_height = satellite_height

    class _PlateCarree:
        def __init__(self, *args, **kwargs):
            pass

    class _ShapelyFeature:
        def __init__(self, geometries, crs, **kwargs):
            self.geometries = list(geometries)
            self.crs = crs
            self.kwargs = kwargs

    class _Reader:
        def __init__(self, path):
            self.path = path

        def geometries(self):
            return []

    crs_module.Geostationary = _Geostationary
    crs_module.PlateCarree = _PlateCarree
    feature_module.BORDERS = object()
    feature_module.ShapelyFeature = _ShapelyFeature
    shapereader_module.Reader = _Reader
    io_module.shapereader = shapereader_module

    cartopy_module.crs = crs_module
    cartopy_module.feature = feature_module
    cartopy_module.io = io_module

    sys.modules["cartopy"] = cartopy_module
    sys.modules["cartopy.crs"] = crs_module
    sys.modules["cartopy.feature"] = feature_module
    sys.modules["cartopy.io"] = io_module
    sys.modules["cartopy.io.shapereader"] = shapereader_module


# Los entornos locales pueden tener estas dependencias instaladas pero
# mal configuradas (por ejemplo, PROJ/GDAL sin base de datos). Para que
# la suite sea determinista, forzamos stubs livianos en tests.
_install_pyproj_stub()
_install_rasterio_stub()
_install_scipy_stub()
_install_cartopy_stub()
