# goes_rgb/aws_interface.py
import os
from glob import glob
from datetime import datetime
from goes_rgb.logging_utils import get_logger


logger = get_logger(__name__)


def download_file_with_progress(fs, s3_url, local_path, chunk_size=512*1024):
    """
    Descarga un archivo de S3 mostrando barra de progreso usando boto3 anónimo.
    
    Args:
        fs: S3FileSystem object (no se usa, mantenido por compatibilidad)
        s3_url: URL del archivo en S3 (ej: s3://bucket/key)
        local_path: Ruta local donde guardar
        chunk_size: Tamaño del chunk en bytes
    """
    try:
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config
        from tqdm import tqdm

        # Parsear URL de S3
        s3_path = s3_url.replace("s3://", "")
        bucket, key = s3_path.split("/", 1)

        # Crear cliente S3 anónimo (sin credenciales)
        s3_client = boto3.client(
            "s3",
            config=Config(signature_version=UNSIGNED, retries={"max_attempts": 3}),
        )
        
        # Obtener tamaño del archivo
        response = s3_client.head_object(Bucket=bucket, Key=key)
        total_size = response["ContentLength"]
        
        # Descargar con barra de progreso
        with open(local_path, "wb") as f:
            with tqdm(total=total_size, unit="B", unit_scale=True, 
                     desc=os.path.basename(local_path)) as pbar:
                
                def progress_callback(bytes_amount):
                    pbar.update(bytes_amount)
                
                s3_client.download_fileobj(
                    bucket, key, f, 
                    Callback=progress_callback
                )
    except Exception as e:
        logger.exception("Error al descargar archivo desde %s", s3_url)
        if os.path.exists(local_path):
            os.remove(local_path)
        raise


def list_goes_files(product, year, day_of_year, hour, satellite="noaa-goes16"):
    import s3fs

    fs = s3fs.S3FileSystem(anon=True)
    prefix = f"{satellite}/{product}/{year}/{day_of_year:03d}/{hour:02d}/"
    files = fs.ls(prefix)
    return ["s3://" + f for f in files if f.endswith(".nc")]


def list_goes_files_2(product, dt, satellite="noaa-goes16"):
    import s3fs

    fs = s3fs.S3FileSystem(anon=True)
    year = dt.year
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour
    prefix = f"{satellite}/{product}/{year}/{day_of_year:03d}/{hour:02d}/"
    # preguntar aca que tanto importa la hora
    files = fs.ls(prefix)
    return ["s3://" + f for f in files if f.endswith(".nc")]


def _find_local_goes_files(local_dir, product, dt, channel=None):
    year = dt.year
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour
    pattern = f"OR_{product}-M6_G*_s{year}{day_of_year:03d}{hour:02d}*.nc"
    if channel:
        pattern = f"OR_{product}-M6_G*{channel}*_s{year}{day_of_year:03d}{hour:02d}*.nc"
    return sorted(glob(os.path.join(local_dir, pattern)))


def download_goes_files_for_datetime(
    dt,
    product="ABI-L2-MCMIPF",
    channels=[f"C{str(i).zfill(2)}" for i in range(1, 16)],
    satellite="noaa-goes16",
    local_dir="data",
):
    os.makedirs(local_dir, exist_ok=True)
    year = dt.year
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour

    downloaded_files = []

    if product == "ABI-L2-MCMIPF":
        local_matches = _find_local_goes_files(local_dir, product, dt)
        if local_matches:
            logger.info(
                "Usando archivo local existente: %s",
                os.path.basename(local_matches[0]),
            )
            return local_matches[:1]

        import s3fs

        fs = s3fs.S3FileSystem(anon=True)
        prefix = f"{satellite}/{product}/{year}/{day_of_year:03d}/{hour:02d}/"
        try:
            files = fs.ls(prefix)
        except FileNotFoundError:
            logger.warning("No files found for prefix: %s", prefix)
            return []

        matched = [f for f in files if f.endswith(".nc")]
        if not matched:
            logger.warning("No se encontraron archivos para %s", dt)
            return []
        s3_url = "s3://" + matched[0]
        filename = os.path.basename(matched[0])
        local_path = os.path.join(local_dir, filename)
        download_file_with_progress(fs, s3_url, local_path)
        downloaded_files.append(local_path)

    elif product == "ABI-L1b-RadF":
        import s3fs

        fs = s3fs.S3FileSystem(anon=True)
        prefix = f"{satellite}/{product}/{year}/{day_of_year:03d}/{hour:02d}/"
        try:
            files = fs.ls(prefix)
        except FileNotFoundError:
            logger.warning("No files found for prefix: %s", prefix)
            return []

        for channel in channels:
            local_matches = _find_local_goes_files(local_dir, product, dt, channel=channel)
            if local_matches:
                logger.info(
                    "Usando archivo local existente para %s: %s",
                    channel,
                    os.path.basename(local_matches[0]),
                )
                downloaded_files.append(local_matches[0])
                continue

            matched = [f for f in files if channel in f and f.endswith(".nc")]
            if not matched:
                logger.warning("Canal %s no encontrado para %s", channel, dt)
                continue
            s3_url = "s3://" + matched[0]
            filename = os.path.basename(matched[0])
            local_path = os.path.join(local_dir, filename)
            download_file_with_progress(fs, s3_url, local_path)
            downloaded_files.append(local_path)

    return downloaded_files
