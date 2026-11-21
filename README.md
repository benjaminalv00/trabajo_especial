# GOES RGB Processor

Herramienta para descargar, procesar y exportar productos RGB a partir de imágenes del instrumento ABI de los satélites GOES-16/18/19 (productos de Nivel 1b y MCMI de Nivel 2). Genera imágenes PNG, GeoTIFF georreferenciados (con reproyección opcional), componentes R/G/B por separado, animaciones GIF y videos MP4. Se configura con archivos YAML y tiene tres interfaces: línea de comandos, menú interactivo y aplicación web.

Guías de los productos RGB: [CIRA Quick Guides](https://rammb2.cira.colostate.edu/training/visit/quick_reference/#tab17)

Por sugerencias o dudas, escribir a benjamin.alvarez@mi.unc.edu.ar

---

## Requisitos

- **Linux o WSL** con **Conda** (canal conda-forge), o bien **Docker**.
- **Internet:** los datos se descargan del bucket público de NOAA en AWS (`noaa-goes16`, `noaa-goes18`, `noaa-goes19`). La primera ejecución también descarga los mapas de Natural Earth que usa cartopy.
- **Disco:** un archivo MCMI de disco completo pesa unos 350 MB por fecha; en L1b se descarga un archivo por banda.
- **Ejecutar siempre desde la raíz del repositorio:** las rutas a recetas propias, shapefiles y carpetas de salida son relativas.

---

## Primeros pasos

### Con Conda

```bash
conda env create -f environment.yml      # la primera vez
conda activate goes-env
python main.py --config config/example.yml
```

Para actualizar un entorno ya creado: `conda env update -n goes-env -f environment.yml --prune`.

**Qué esperar:** se descarga un NetCDF a `data/` (si ya está, se reutiliza) y quedan dos PNG en `salidas/`:

- `prueba_color_real_nombre_true_color_20250830_1500.png`
- `microfisica_diurna_1500_daily_microphysics_20250830_1500.png`

### Con Docker

```bash
docker compose build
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose run --rm goes-processor --config /app/config/example_docker.yml
```

Las salidas aparecen en las carpetas del repositorio (`salidas/`, `gifs/`, `geotiffs/`, `videos/`, `componentes/`, `componentes_rgb/`), porque están montadas como volúmenes.

> **Por qué `HOST_UID` y no `UID`:** en bash `UID` es una variable de solo lectura, así que `UID=$(id -u) docker compose ...` falla y el contenedor termina corriendo como root, dejando los archivos generados con dueño root. Con `HOST_UID`/`HOST_GID` esto no ocurre. En Windows (PowerShell) no hace falta definir nada: `docker-compose.yml` usa `1000:1000` por defecto.

---

## Interfaces

Las tres terminan llamando a la misma función (`run_from_config`), así que producen los mismos resultados.

| Interfaz | Cómo se lanza | Para qué |
|---|---|---|
| Línea de comandos | `python main.py --config <archivo.yml>` | Trabajos reproducibles y en lote |
| Demo rápida | `python main.py --demo` | Prueba sin YAML: guarda `salidas/demo_true_color.png` |
| Menú interactivo | `python menu_interactivo.py` | Armar un trabajo respondiendo preguntas en la terminal |
| Aplicación web | `streamlit run app.py` y abrir http://localhost:8501/ | Uso con interfaz gráfica |

La aplicación web también corre en Docker:

```bash
docker compose build
HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose up -d goes-ui
```

---

## Configuración YAML

Un archivo tiene dos bloques:

- `defaults`: valores comunes a todos los trabajos.
- `jobs`: lista de trabajos. Lo que defina un job pisa a `defaults`; los bloques `*_conf` se combinan clave por clave.

```yaml
defaults:
  tipo_imagen: MCMI
  recorte: [-28, -35, -67, -61.0]   # [latN, latS, lonW, lonE]
  png_conf:
    out_dir: salidas/

jobs:
  - nombre: cordoba
    datetime: 2025-08-30T15:00:00
    productos: [true_color, daily_microphysics]
    salidas: [PNG, GEOTIFF]
    geotiff_conf:
      producto: true_color
```

### Claves

| Clave | Ejemplo | Si no se indica | Nota |
|---|---|---|---|
| `nombre` | `cordoba` | `job` | Prefijo de los PNG |
| `productos` | `[true_color, air_mass]` | **obligatorio** | Ver [Productos disponibles](#productos-disponibles) |
| `datetime` | `2025-08-30T15:00:00` | — | Fecha y hora en UTC |
| `datetimes` | lista de fechas | — | Varias fechas sueltas |
| `rango` | `{inicio, fin, paso_minutos}` | paso de 30 min | Serie temporal (para GIF y video) |
| `satelite` | `GOES19` | según la fecha | GOES16 hasta el 6/4/2025, GOES19 desde el 7/4/2025 |
| `tipo_imagen` | `MCMI` o `L1B` | `MCMI` | |
| `canales` | `["C01", "C02", "C03"]` | las bandas que piden las recetas | Solo L1B |
| `recorte` | `[latN, latS, lonW, lonE]` | disco completo | En grados; sur y oeste negativos |
| `data_dir` | `data` | `data` | Descargas y caché local |
| `salidas` | `[PNG, GEOTIFF, COMPONENTES_RGB, GIF, VIDEO]` | `[PNG]` | No distingue mayúsculas |
| `png_conf` | ver abajo | | |
| `geotiff_conf` | ver abajo | | **Sin este bloque no se genera GeoTIFF** |
| `componentes_rgb_conf` | ver abajo | | |
| `gif_conf` | ver abajo | | Necesita `producto` |
| `video_conf` | ver abajo | | Necesita `producto` |

Si una clave no se reconoce, o es de una versión anterior (`export`, `gif`, `video`, `geotiff`, `componentes_rgb`), el procesador avisa por pantalla y dice dónde va esa configuración.

### Bloques de salida

| Bloque | Claves | Valores por defecto |
|---|---|---|
| `png_conf` | `out_dir`, `shapefile_provincias`, `show`, `lon_interval`, `lat_interval` | `salidas`, shapefile del repo, `false`, 10, 10 |
| `geotiff_conf` | `producto` o `productos`, `out_dir`, `filename_pattern` (`{producto}`, `{ts}`), `reproyecciones` | `out_dir` de los PNG, `{producto}_{ts}.tif` |
| `componentes_rgb_conf` | `producto` o `productos`, `out_dir`, `filename_pattern` (`{producto}`, `{ts}`, `{canal}`) | todos los productos, `componentes` |
| `gif_conf` | `producto`, `fps` o `frame_seconds`, `loop`, `filename`, `out_dir` | 1 cuadro por segundo, `loop: 0` (sin fin), `gifs` |
| `video_conf` | `producto`, `fps` o `frame_seconds`, `codec`, `crf`, `preset`, `pix_fmt`, `filename`, `out_dir` | `libx264`, 23, `medium`, `yuv420p`, `videos` |

Reproyecciones del GeoTIFF (además del original en la proyección del satélite):

```yaml
geotiff_conf:
  producto: true_color
  reproyecciones:
    - epsg: "EPSG:3857"        # Web Mercator (Google Maps, OpenStreetMap)
      suffix: "_web_mercator"
```

---

## Ejemplos incluidos

| Archivo | Qué muestra |
|---|---|
| `config/example.yml` | Lo básico: dos productos en PNG |
| `config/example_gif.yml` | Animación GIF de una secuencia horaria |
| `config/example_video.yml` | Video MP4 de los incendios de Córdoba (21/09/2024) |
| `config/example_geotiff_reprojection.yml` | GeoTIFF y sus reproyecciones (para QGIS o Google Earth) |
| `config/example_componentes.yml` | Componentes R, G y B por separado |
| `config/example_custom.yml` | Una receta propia |
| `config/example_load_l1b.yml` | Productos L1b |
| `config/example_docker.yml`, `config/example_load_l1b_docker.yml` | Los mismos, para Docker |
| `config/tesis/` | Configuraciones usadas para las figuras del trabajo final |

---

## Productos disponibles

**Recetas oficiales** (siguen las guías de NOAA/CIRA): `true_color`, `daily_microphysics`, `microfisica_nocturna`, `fire_temperature`, `air_mass`, `ash`, `dust`, `day_cloud_convection`, `day_convection`, `day_land_cloud`, `day_land_cloud_fire`, `day_snow_fog`, `simple_water_vapor`, `differential_water_vapor`.

**Recetas propias** (en `config/custom_recipes/`): `burn_scar` (cicatriz de quemado), `falso_color`, `true_color_personalizado`.

---

## Salidas

| Salida | Carpeta por defecto | Nombre |
|---|---|---|
| PNG | `salidas/` | `{nombre}_{producto}_{AAAAMMDD_HHMM}.png` |
| GeoTIFF | la de los PNG (o `out_dir`) | `{producto}_{AAAAMMDD_HHMM}.tif`, más un archivo por reproyección |
| Componentes R/G/B | `componentes/` | un GeoTIFF por canal (conviene un `filename_pattern` terminado en `.tif`) |
| GIF | `gifs/` | `{producto}.gif` o `filename` |
| MP4 | `videos/` | `{producto}.mp4` o `filename` |

---

## Recetas propias

1. Crear el archivo en `config/custom_recipes/`, con una función `recipe()` que devuelva un diccionario con `funcs` (funciones `R`, `G` y `B`), `bands` y `emissive_units`.
2. Registrarla en `goes_rgb/recipes_registry.py`.
3. Usar su nombre en `productos`.

No hace falta tocar el resto del procesador. Guía paso a paso: [`docs/CUSTOM_RECIPES.md`](docs/CUSTOM_RECIPES.md).

---

## Tests

```bash
conda activate goes-env
python -m pytest                       # toda la suite
python -m pytest --cov=goes_rgb        # con cobertura
```

Usar `python -m pytest` (y no `pytest` a secas) asegura que se use el Python del entorno.

---

## Notas técnicas

- **Fecha y escaneo:** se usa el escaneo cuyo inicio está más cerca de la fecha pedida, dentro de esa hora (en modo 6 hay uno cada 10 minutos). Un archivo ya descargado se reutiliza si empezó a lo sumo 5 minutos antes o después.
- **Proyección:** el PNG y el GeoTIFF base quedan en la proyección nativa del satélite (geoestacionaria). El GeoTIFF se puede reproyectar a otros sistemas con `reproyecciones`.
- **Recorte:** las esquinas en latitud y longitud se convierten a índices de la grilla del ABI, y se recorta por índices.
- **Resoluciones:** las bandas de 0,5 y 1 km se llevan a la grilla de 2 km por decimación.
- **Reflectancia:** las bandas reflectivas de L1b se calibran al factor de reflectancia (κ₀ × radiancia), sin corrección por ángulo cenital solar.

---

## Problemas frecuentes

- **"No se encontraron archivos para…":** revisar fecha, hora (en UTC) y satélite. GOES-16 dejó de ser GOES-East en abril de 2025; para fechas posteriores corresponde `GOES19`.
- **Aviso de clave que no tiene efecto:** el mensaje dice en qué bloque va esa configuración (por ejemplo, `export` → `png_conf`).
- **No se genera el GeoTIFF:** falta el bloque `geotiff_conf`, o el job tiene varios productos y no se indicó `producto`/`productos`.
- **El MP4 se ve raro o no abre:** usar `fps` mayor a 0 (o un `frame_seconds` razonable). Para H.264 (`yuv420p`) las dimensiones deben ser pares: el procesador agrega relleno si hace falta. El aviso `macro_block_size=16` es normal y se puede ignorar.
- **"not enough frames to estimate rate":** hay muy pocos cuadros; definir `fps`/`frame_seconds` o agregar fechas.
- **Falta FFmpeg:** instalar `imageio-ffmpeg` o FFmpeg del sistema (`environment.yml` ya lo incluye).
- **Errores de rutas o recetas propias que no se encuentran:** ejecutar desde la raíz del repositorio.

---

## Estructura del proyecto

```
trabajo_especial/
├── main.py                  # Línea de comandos
├── menu_interactivo.py      # Menú en la terminal
├── app.py                   # Aplicación web (Streamlit)
├── config_runner.py         # Orquestador: lee el YAML y ejecuta cada job
├── goes_rgb/                # Núcleo del procesador
│   ├── aws_interface.py     # Descarga desde AWS y caché local
│   ├── base_abi_image.py    # Clase abstracta de imagen ABI
│   ├── l1b_abi_image.py     # Productos L1b (calibración)
│   ├── l2_abi_image.py      # Productos MCMI (lectura acotada al recorte)
│   ├── rgb_processor.py     # Calibra solo las bandas que pide cada receta
│   ├── rgb_product.py       # Compone el RGB a partir de una receta
│   ├── rgb_recipes.py       # Recetas oficiales
│   ├── recipes_registry.py  # Registro de recetas (oficiales y propias)
│   ├── output_handlers.py   # Salidas: PNG, GeoTIFF, componentes, GIF, MP4
│   ├── visualization.py     # Dibujo con costas, límites y grilla
│   └── helpers.py           # Calibración, realces, recorte, GeoTIFF
├── config/                  # Ejemplos YAML, recetas propias y config/tesis/
├── docs/                    # Documentación (recetas propias)
├── scripts/                 # Utilidades (reproyección de GeoTIFF)
├── shapefiles/              # Límites provinciales
├── tests/                   # Tests (pytest)
├── data/                    # Descargas NetCDF
├── salidas/ geotiffs/ componentes/ gifs/ videos/   # Salidas
├── Dockerfile, docker-compose.yml
└── environment.yml          # Entorno Conda
```
