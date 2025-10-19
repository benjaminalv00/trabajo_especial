## GOES RGB Processor – generación de PNG, GIF, MP4 y GeoTIFF

Herramienta para descargar, procesar y exportar productos RGB de GOES-16/18/19 a partir de archivos L1b/L2. Permite generar imágenes PNG, animaciones GIF, videos MP4 y salidas GeoTIFF georreferenciadas, todo configurable vía YAML.

## Estructura del proyecto

```
trabajo_especial/
├── config/                 # Ejemplos de configuración YAML
│   ├── example.yml
│   ├── gif_example.yml
│   ├── video_example.yml
│   └── geotiff.yml
├── data/                   # Descargas NetCDF (entrada)
├── geotiffs/               # Salidas GeoTIFF (si se configuran)
├── gifs/                   # Salidas GIF
├── videos/                 # Salidas MP4
├── salidas/                # PNG por producto/fecha
├── goes_rgb/               # Código fuente
│   ├── visualization.py    # Plot y guardado de imágenes
│   ├── recipes_registry.py # Productos RGB disponibles
│   ├── helpers.py          # Utilidades (GeoTIFF, reproyección puntual)
│   └── ...
├── main.py                 # Entrada principal (CLI)
├── config_runner.py        # Ejecuta jobs desde YAML
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

2) Notas sobre dependencias clave
- GeoTIFF: requiere rasterio, pyproj y GDAL.
- MP4: usa imageio + ffmpeg. Se recomienda tener imageio-ffmpeg o ffmpeg del sistema instalado.
- Gráficos: cartopy, shapely, matplotlib.

Si tu environment.yml es mínimo, asegúrate de incluir: numpy, matplotlib, pyyaml, rasterio, pyproj, cartopy, gdal, imageio, imageio-ffmpeg, netCDF4, boto3, s3fs, xarray, scipy, pandas (según tus necesidades).

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

## Interfaz para crear y ejecutar configuraciones

Tenés dos opciones según prefieras trabajar sólo con Python o mantener la SPA anterior:

### NiceGUI (recomendada, todo-Python)
1. Activá el entorno e instalá las dependencias actualizadas (`conda env update -n goes-env -f environment.yml --prune`).
2. Levantá la interfaz:
	```bash
	python main.py --ui --host 0.0.0.0 --port 8000
	```
3. Abrí [http://localhost:8000](http://localhost:8000). Desde la aplicación NiceGUI podés:
	- Completar *defaults* y agregar/eliminar jobs.
	- Ver la vista previa del YAML generado en tiempo real (mantiene listas inline y fechas ISO).
	- Guardar directamente en `config/` o ejecutar el pipeline al vuelo con logs en vivo.

### API + SPA (implementación anterior)
Si querés seguir usando el front-end estático anterior:
1. Activá el entorno y ejecutá:
	```bash
	python main.py --api
	```
2. Abrí [http://localhost:8000](http://localhost:8000) para acceder a la SPA vanilla JS.

> ⚠️ Ambas interfaces cubren los campos más comunes (defaults, jobs, productos, salidas y GeoTIFF). Para opciones avanzadas, editá el YAML manualmente.

## Formato de configuración (YAML)

Un archivo YAML declara defaults y una lista de jobs. Cada job indica qué productos generar y en qué fechas.

- defaults
	- tipo_imagen: MCMI | L1B (por ahora MCMI es el flujo principal)
	- recorte: [latN, latS, lonW, lonE] en grados (opcional)
	- export:
		- out_dir: carpeta para PNG
		- shapefile_provincias: ruta a shapefile opcional para delinear provincias
		- show: false/true (mostrar interactivamente)

- jobs[n]
	- nombre: etiqueta del job
	- satelite: GOES16 | GOES18 | GOES19 (por defecto GOES19)
	- tipo_imagen: MCMI | L1B (opcional, sobrescribe defaults)
	- productos: [lista de nombres] que existen en recipes_registry.py (p.ej. true_color, day_convection, daily_microphysics)
	- Fechas (elige una de estas):
		- datetime: "YYYY-MM-DDTHH:MM:SS"
		- datetimes: [ ... varias fechas ... ]
		- rango: { inicio, fin, paso_minutos }
	- Opciones de salida por job (todas opcionales):
		- gif: { producto, fps | frame_seconds, out_dir, filename, loop }
		- video: { producto, fps | frame_seconds, out_dir, filename, codec, crf, preset, pix_fmt }
		- geotiff: { producto | productos, out_dir, filename | filename_pattern }
		- componentes_rgb: { producto | productos, out_dir, filename_pattern, cmap }

### Ejemplos

Imagen única (PNG y GeoTIFF):
```
defaults:
	tipo_imagen: MCMI
	recorte: [-18.6, -56.45, -79.79, -53.0]
	export:
		out_dir: salidas/
		shapefile_provincias: shapefiles/provincias/linea_de_limite_070111Line.shp
		show: false

jobs:
	- nombre: true_color_1500
		datetime: 2025-08-30T15:00:00
		productos: [true_color]
		geotiff:
			producto: true_color
			out_dir: geotiffs/
			filename: true_color_20250830_1500.tif
```

Serie temporal con MP4 y componentes RGB:
```
jobs:
	- nombre: serie_con_video
		rango:
			inicio: 2022-09-21T12:00:00
			fin: 2022-09-21T14:00:00
			paso_minutos: 60
		productos: [day_convection, true_color]
		video:
			producto: day_convection
			frame_seconds: 1.5
			out_dir: videos/
			filename: serie_day_convection.mp4
			codec: libx264
			crf: 23
			preset: medium
			pix_fmt: yuv420p
		componentes_rgb:
			productos: [day_convection]
			out_dir: componentes/
			filename_pattern: "{producto}_{ts}_{canal}.png"
			cmap: gray
```

Serie con GeoTIFF por fecha:
```
jobs:
	- nombre: serie_geotiff
		rango:
			inicio: 2022-09-21T12:00:00
			fin: 2022-09-21T14:00:00
			paso_minutos: 60
		productos: [day_convection, true_color]
		geotiff:
			producto: day_convection
			out_dir: geotiffs/
			filename_pattern: "{producto}_{ts}.tif"
```

## Salidas
- PNG por producto/fecha: en salidas/ (o el directorio definido en export.out_dir), nombre: {nombre_job}_{producto}_{YYYYMMDD_HHMM}.png
- GIF: en gifs/ o video.gif_conf.out_dir
- MP4: en videos/ o video.out_dir (H.264 yuv420p, fps derivado de frame_seconds o fps)
- GeoTIFF: en geotiffs/ o geotiff.out_dir; con CRS y transform del producto (CRS nativo GOES)
- Componentes RGB: en componentes/ (o componentes_rgb.out_dir), 3 PNG por producto/fecha (R/G/B)

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
- Estilo/código: se sugiere usar black y pre-commit si están en el entorno.
- 

## Como ejecutar con docker
Desde el directorio raiz, ejecutar 
```
docker-compose build
```
Luego, correr
```
UID=$(id -u) GID=$(id -g) docker-compose run --rm goes-processor --config /app/config/example.yml
```
