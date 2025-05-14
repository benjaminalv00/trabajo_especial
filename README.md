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
├── tests/                  # Tests unitarios (si aplicás TDD o testing)
├── environment.yml         # 📦 Definición de entorno Conda (recomendado)
├── requirements.txt        # Alternativa si usás pip
├── README.md               # Documentación general
└── main.py                 # Script principal para correr todo el pipeline
```
