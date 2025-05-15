# trabajo_final
Repositorio con el código para el trabajo final de la Licenciatura en Ciencias de la Computación (FaMAF - UNC)
```
trabajo_final/
├── data/                   # Archivos descargados (NetCDF, etc.)
├── notebooks/              # Notebooks para pruebas, visualización, informes
├── goes_rgb/               # Código fuente del procesador
│   ├── __init__.py
│   ├── aws_interface.py    # Funciones para buscar/descargar desde AWS S3
│   ├── reader.py           # Abrir y leer archivos GOES (xarray, netCDF4)
│   ├── processor.py        # Procesamiento de canales, composición RGB
│   ├── visualization.py    # Funciones para mostrar imágenes
│   └── utils.py            # Helpers generales (normalización, paths, etc.)
├── tests/                  # Tests unitarios
├── environment.yml         # 📦 Definición de entorno Conda
├── README.md               # Documentación general
└── main.py                 # Script principal para correr todo el pipeline
```

#· Flujo lógico (en principio)

**aws_interface.py**: lista archivos disponibles y descarga.

**reader.py**: abre archivos .nc con xarray o netCDF4.

**processor.py**: selecciona canales, normaliza, arma RGB.

**visualization.py**: grafica la imagen o la guarda.

**main.py**: usa todo lo anterior para una fecha/canal.


## Como activar el environment
```
conda env create -f environment.yml
conda activate goes-env
```
