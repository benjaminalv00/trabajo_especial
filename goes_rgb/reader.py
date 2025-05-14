# goes_rgb/reader.py

import xarray as xr
import numpy as np

def open_goes_file(path):
    return xr.open_dataset(path, engine="netcdf4")

def get_radiance_array(dataset):
    # La variable típica para radiancia en L1b es "Rad"
    return dataset['Rad'].values

def get_geolocation(dataset):
    lat = dataset['x'].values
    lon = dataset['y'].values
    return lat, lon