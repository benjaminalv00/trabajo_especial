# Mejoras y Optimización (GOES RGB)

## 1. Gestión de Memoria
- Cerrar figuras Matplotlib (plt.close) cuando show=False.
- Guardar PNG y descartar arrays RGB inmediatamente (del / gc.collect()).
- Convertir productos a float32 antes de graficar.
- Evitar acumular todos los productos en `processor.products` (eliminar tras uso).
- Cerrar datasets NetCDF (`img.close()` si existe).
- Usar escritor GIF en streaming (`imageio.get_writer`) en lugar de cargar todos los frames.
- Desactivar `show` en procesos batch.
- Limitar timestamps de prueba antes de correr series largas.
- Añadir swap (ej.: 4–8 GB) en máquinas pequeñas si es necesario.
- Downsample (resize) si no se requiere resolución completa.

## 2. Generación de GIF
Configuración YAML (ejemplo):
```yaml
gif:
  producto: true_color
  fps: 2
  filename: anim.gif
  out_dir: gifs/
  loop: 0
```
Flujo:
1. Se generan PNG por timestamp.
2. Se acumulan rutas solo del producto objetivo.
3. Al final se escribe GIF en streaming (baja RAM).
4. Opcional futuro: permitir varios GIF (lista de bloques `gif`).

## 3. Oportunidades Futuras
- Multiples GIF por job.
- Parámetro `scale` o `resize` (p.ej. 0.5).
- Cache de bandas calibradas compartida entre productos.
- Uso de Dask/xarray con chunks para bandas grandes.
- Modo headless: variable de entorno (ej. `MPLBACKEND=Agg`).
- Validación de config (esquema) antes de ejecutar.
- CLI: `--only-gif` para regenerar animación desde PNG existentes.
- Opción para exportar a MP4 (imageio + ffmpeg).
- Logs estructurados (logging + niveles).
- Test unitarios de recipes (rangos esperados / shape).
- Métrica de tiempo y memoria por paso.

## 4. Checklist Rápido (antes de correr series largas)
- [ ] Config verificada (timestamps razonables).
- [ ] show=False.
- [ ] swap disponible (si RAM < 8GB).
- [ ] shapefile accesible.
- [ ] out_dir y gifs/ existen (o se crean).
- [ ] GIF no necesita demasiados frames (≤ 60 al inicio).
- [ ] Sin figuras abiertas (len(plt.get_fignums()) == 0).

## 5. Comandos Útiles
Crear swap (ejemplo 4G):
```
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

Limpiar caché Python en sesión larga:
```python
import gc, matplotlib.pyplot as plt
plt.close('all'); gc.collect()
```

## 6. Convenciones Recomendadas
- Nombres de archivos: `{producto}_{YYYYmmdd_HHMM}.png`
- GIF: `{nombre_job|producto}.gif`
- Mantener recipes puras (sin I/O) para testear fácilmente.