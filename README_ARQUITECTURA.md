# Arquitectura de `config_runner`

Este documento resume el diseño y flujo de `config_runner.py` tras la refactorización.

## Visión general

- API pública estable:
  - `run_from_config(path) -> List[str]`: Ejecuta todos los jobs del YAML y devuelve rutas generadas.
  - `run_job(job, defaults) -> List[str]`: Ejecuta un job individual.
- El resto son helpers internos para mantener `run_job` simple y testeable.

## Flujo de procesamiento

1. `run_from_config` carga el YAML (con `load_config`) y orquesta múltiples `run_job`.
2. `run_job`:
   - Valida el job (`_validate_job`).
   - Normaliza salidas (`_salidas_deseadas`).
   - Fusiona configuraciones por salida (PNG/GIF/VIDEO/GeoTIFF/COMPONENTES).
   - Itera fechas (`expand_datetimes`) y delega a `_process_datetime`.
   - Al final, compone animaciones: `_generate_gif_from_frames`, `_generate_video_from_frames`.

## Helpers clave

- Fechas y nombres
  - `expand_datetimes(job)`: Genera datetimes desde `datetime`, `datetimes` o `rango`.
  - `_format_ts(dt)`: `YYYYMMDD_HHMM`.
  - `_format_filename(pattern, producto, ts)`: Sustitución simple en patrones.
- Salidas y validación
  - `_validate_job(job, defaults)`: Reglas mínimas (productos válidos, rango/fecha presente).
  - `_salidas_deseadas(job)`: Set en mayúsculas de tipos de salida.
  - `OutputType(Enum)`: Evita strings mágicos.
- Preparación
  - `_prepare_image(dt, defaults, job, recorte_conf)`: Descarga/abre imagen, proyección, recorte y `extent`.
  - `_select_geotiff_products(geotiff_conf, productos)`: Determina productos a exportar como GeoTIFF.
- Exportadores
  - `_generate_png(...)`
  - `_export_componentes_rgb(...)`
  - `_export_geotiff_single(...)`
  - `_ensure_frame_png(...)`: PNG auxiliar cuando sólo se necesita como frame.
- Animación
  - `_normalize_rgb_frame(frame)`: Asegura RGB `uint8`.
  - `_pad_frames_to_even_16(frames)`: Tamaño común válido para `yuv420p`.
  - `_generate_gif_from_frames(gif_conf, frames_por_producto)`
  - `_generate_video_from_frames(video_conf, frames_por_producto)`

## Consideraciones

- Registro: usa `logging.getLogger(__name__)` y evita `print`.
- Errores: cada timestamp se protege con `try/except` y `logger.exception`, el job continúa.
- Comportamiento preservado: rutas, patrones y selección de productos se mantienen.

## Extensiones futuras

- Dataclasses para validar y tipar configuraciones de salidas.
- Tests adicionales de integración (con datos pequeños) y contratos de archivos generados.
- Soporte explícito de zona horaria (UTC).