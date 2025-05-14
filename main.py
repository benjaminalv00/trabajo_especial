from datetime import datetime
from goes_rgb.aws_interface import *

download_goes_files_for_datetime(datetime(2023, 8, 8, 18),channels=["C01"])

# archivos = list_goes_files_2("ABI-L1b-RadC", datetime(2023, 8, 8, 18))

# for archivo in archivos:
#     print(archivo)
#     print("\n")

