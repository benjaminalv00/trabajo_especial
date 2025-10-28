# GOES RGB Processor 
Herramienta para descargar, procesar y exportar productos RGB de GOES-16/18/19 a partir de archivos L1b/L2. Permite generar imágenes PNG, animaciones GIF, videos MP4 y salidas GeoTIFF georreferenciadas, todo configurable vía GUI y YAML.

[Referencias de productos
](https://rammb2.cira.colostate.edu/training/visit/quick_reference/#tab17)

Por sugerencias o dudas, contactarse a benjamin.alvarez@mi.unc.edu.ar


## Como ejecutar el procesador mediante interfaz grafica con Docker
Si no tiene instalado Docker, puede dirigirse a el siguiente [link](https://docs.docker.com/desktop/) para descargarlo

una vez instalado Docker, desde el directorio raiz de este repositorio, ejecutar 
```
docker compose build
```

Luego, correr

```
UID=$(id -u) GID=$(id -g) docker compose up -d goes-ui
```

Si estas tratando de ejecutar docker con windows, seguir los siguientes pasos:
1) en el archivo ```docker-compose.yml``` habra que comenta o eliminar las líneas user: "${UID}:${GID}" de los DOS servicios.  
Con esto ya tenemos la aplicación corriendo.
2)  correr ``` docker compose up -d goes-ui ```

Para acceder al front-end, en el navegador ingresar a 
```
http://localhost:8501/
```

## Estructura del Proyecto
```
trabajo_especial/
├── config/                 # Ejemplos de configuración YAML
├── componentes/            # Salidas de componentes RGB (GeoTIFF)
├── data/                   # Descargas NetCDF (entrada)
├── geotiffs/               # Salidas GeoTIFF (si se configuran)
├── gifs/                   # Salidas GIF
├── videos/                 # Salidas MP4
├── salidas/                # PNG por producto/fecha
├── goes_rgb/               # Código fuente del procesador
│   ├── visualization.py    # Plot y guardado de imágenes
│   ├── recipes_registry.py # Productos RGB disponibles
│   ├── helpers.py          # Utilidades (GeoTIFF, etc.)
│   └── ...
├── app.py                  # <-- Interfaz gráfica principal (Streamlit)
├── config_runner.py        # Lógica para ejecutar jobs desde configuración
├── environment.yml         # 📦 Entorno Conda
└── README.md               # Este archivo
```

## Requisitos e instalación

Se recomienda usar Conda (canal conda-forge) para instalar dependencias nativas como cartopy, rasterio y GDAL.

### Prerrequisitos
- Tener Conda instalado (Anaconda o Miniconda).
- Este proyecto asume el uso del entorno goes-env definido en `environment.yml`.
	- Si el entorno ya fue creado previamente, simplemente actívalo antes de ejecutar cualquier comando:
		```
		conda activate goes-env
		```
	- Si aún no está creado, seguí los pasos de abajo para crearlo/actualizarlo.

1) Crear el entorno
- Si no existe el entorno:
```
conda env create -f environment.yml
```
- Para actualizar un entorno existente:
```
conda env update -n goes-env -f environment.yml --prune
```
- Activar:
```
conda activate goes-env
```

## Uso rápido

0) Asegurate de tener el entorno activo:
```
conda activate goes-env
```

1) Ejecutar una demo manual (sin YAML):
```
python main.py --demo
```

2) Ejecutar con YAML de configuración:
```
python main.py --config config/example.yml
```

### Ejemplos de YAML de configuración

Imagen única (PNG y GeoTIFF):
```
defaults:
  tipo_imagen: MCMI
  recorte: [-18.6, -56.45, -79.79, -50.0]

jobs:
  - nombre: serie_geotiff
    datetime: 2022-09-21T12:00:00
    productos: [true_color, air_mass]
    # 1. Especificamos que la única salida deseada es GeoTIFF
    salidas: [GeoTIFF,PNG] 

    # 2. Configuramos los detalles del GeoTIFF
    png_conf:
      productos: [true_color, air_mass]
      shapefile_provincias: shapefiles/provincias/linea_de_limite_070111Line.shp
    geotiff_conf:
      productos: [true_color, air_mass]
      out_dir: geotiffs/
      filename_pattern: "{producto}_{ts}.tif"
```

## Como ejecutar el procesador mediante interfaz grafica sin Docker
Asumiendo que ya tiene el entorno activado, simplemente correr 

```
streamlit run app.py
```

## Salidas
- PNG por producto/fecha: en salidas/ , nombre: {nombre_job}_{producto}_{YYYYMMDD_HHMM}.png
- GIF: en gifs/ 
- MP4: en videos/
- GeoTIFF: en geotiffs/ ; con CRS y transform del producto (CRS nativo GOES)
- Componentes RGB: en componentes/ , 3 GeoTIFF por producto/fecha (R/G/B)

## Notas de proyección y recorte
- El raster se mantiene en el CRS nativo geostacionario de GOES (no hay warp a EPSG:4326).
- El recorte se define en lon/lat; se transforma a índices de píxel y se aplica al generar el RGB. El extent usado para plot y GeoTIFF es consistente con ese recorte.
- Los shapefiles se proyectan al vuelo (Cartopy) sobre el lienzo del producto.

## Consejos y resolución de problemas
- MP4 se ve “raro” o no abre:
	- Asegura fps > 0 (o usa frame_seconds razonable). El código limita a un mínimo interno.
	- Para compatibilidad H.264 (yuv420p), las dimensiones del video deben ser pares; el writer agrega padding si hace falta.
- Advertencia macro_block_size=16:
	- Es normal si las dimensiones no son múltiplos de 16. Se puede ignorar o padear a múltiplos de 16.
- “not enough frames to estimate rate”:
	- Ocurre con muy pocos frames; define fps/frame_seconds y/o agrega más frames.
- GeoTIFF vacío o desalineado:
	- Verifica recorte y extent; el helper usa x/y y los índices del recorte para construir el transform.
- Falta FFmpeg:
	- Instala imageio-ffmpeg (Conda/pip) o FFmpeg del sistema.

## Desarrollo
- Ejecutar con otra config:
```
python main.py --config config/video_example.yml
```

## Como ejecutar con docker (sin GUI)
Desde el directorio raiz, ejecutar 
```
docker-compose build
```
Luego, correr
```
UID=$(id -u) GID=$(id -g) docker-compose run --rm goes-processor --config /app/config/example.yml
```
