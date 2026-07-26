import sys
import types
from pathlib import Path


def _install_pyproj_stub():
    module = types.ModuleType("pyproj")

    class _Transformer:
        @staticmethod
        def from_crs(*args, **kwargs):
            class _IdentityTransformer:
                def transform(self, x, y):
                    return x, y

            return _IdentityTransformer()

    module.Transformer = _Transformer
    sys.modules["pyproj"] = module


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
        return array

    ndimage_module.zoom = _zoom
    scipy_module.ndimage = ndimage_module

    sys.modules["scipy"] = scipy_module
    sys.modules["scipy.ndimage"] = ndimage_module


try:
    import pyproj  # noqa: F401
except ModuleNotFoundError:
    _install_pyproj_stub()

try:
    import rasterio  # noqa: F401
except ModuleNotFoundError:
    _install_rasterio_stub()

try:
    from scipy import ndimage  # noqa: F401
except ModuleNotFoundError:
    _install_scipy_stub()
