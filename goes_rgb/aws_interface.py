# goes_rgb/aws_interface.py
import os 
import s3fs
from datetime import datetime

def list_goes_files(product, year, day_of_year, hour, satellite="noaa-goes16"):
    fs = s3fs.S3FileSystem(anon=True)
    prefix = f"{satellite}/{product}/{year}/{day_of_year:03d}/{hour:02d}/"
    files = fs.ls(prefix)
    return ["s3://" + f for f in files if f.endswith(".nc")]

def list_goes_files_2(product, dt, satellite="noaa-goes16"):
    fs = s3fs.S3FileSystem(anon=True)
    year = dt.year
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour
    prefix = f"{satellite}/{product}/{year}/{day_of_year:03d}/{hour:02d}/"
    #preguntar aca que tanto importa la hora
    files = fs.ls(prefix)
    return ["s3://" + f for f in files if f.endswith(".nc")]

def download_goes_files_for_datetime(dt, product="ABI-L1b-RadC", channels=["C01", "C02", "C03"], satellite="noaa-goes16", local_dir="data"):
    os.makedirs(local_dir, exist_ok=True)
    fs = s3fs.S3FileSystem(anon=True)
    year = dt.year
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour

    prefix = f"{satellite}/{product}/{year}/{day_of_year:03d}/{hour:02d}/"
    try:
        files = fs.ls(prefix)
        # breakpoint()
    except FileNotFoundError:
        print(f"No files found for prefix: {prefix}")
        return []

    downloaded_files = []
    for channel in channels:
        matched = [f for f in files if f"M6{channel}" in f and f.endswith(".nc")]
        if not matched:
            print(f"Canal {channel} no encontrado para {dt}.")
            continue
        s3_url = "s3://" + matched[0]
        filename = os.path.basename(matched[0]) # se queda con el primer archivo de la hora
        local_path = os.path.join(local_dir, filename)
        if not os.path.exists(local_path):
            with fs.open(s3_url, 'rb') as s3_file, open(local_path, 'wb') as out_file:
                out_file.write(s3_file.read())
        downloaded_files.append(local_path)

    return downloaded_files

def download_goes_files_for_datetime_2(
    dt,
    product="ABI-L1b-RadC",
    channels=["C01", "C02", "C03"],
    satellite="noaa-goes16",
    local_dir="data",
    mode="M6",  # Nuevo parámetro explícito
):
    import os
    import s3fs

    os.makedirs(local_dir, exist_ok=True)
    fs = s3fs.S3FileSystem(anon=True)
    year = dt.year
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour

    prefix = f"{satellite}/{product}/{year}/{day_of_year:03d}/{hour:02d}/"
    try:
        files = fs.ls(prefix)
    except FileNotFoundError:
        print(f"No files found for prefix: {prefix}")
        return []

    downloaded_files = []
    for channel in channels:
        pattern = f"{mode}{channel}"
        matched = [f for f in files if pattern in f and f.endswith(".nc")]
        if not matched:
            print(f"Canal {channel} no encontrado para {dt} con modo {mode}.")
            continue
        s3_url = "s3://" + matched[0]
        filename = os.path.basename(matched[0])
        local_path = os.path.join(local_dir, filename)
        if not os.path.exists(local_path):
            with fs.open(s3_url, 'rb') as s3_file, open(local_path, 'wb') as out_file:
                out_file.write(s3_file.read())
        downloaded_files.append(local_path)

    return downloaded_files



