# Recetas RGB personalizadas (manual)

Esta guía describe el flujo actual para agregar recetas custom sin modificar la lógica de procesamiento.

## Resumen rápido

1. Crear el archivo de receta en `config/custom_recipes/`.
2. Registrar la receta en `goes_rgb/recipes_registry.py`.
3. Usar el nombre en `productos` dentro de tu YAML.

## 1) Crear una receta custom

Creá un archivo, por ejemplo:

- `config/custom_recipes/mi_falso_color.py`

Plantilla mínima:

```python
from goes_rgb.helpers import realce_percentil


def recipe():
    def R(img):
        return realce_percentil(img["C05"])

    def G(img):
        return realce_percentil(img["C03"])

    def B(img):
        return realce_percentil(img["C02"])

    return {
        "funcs": {"R": R, "G": G, "B": B},
        "bands": ["C02", "C03", "C05"],
        "emissive_units": {},
    }
```

Contrato esperado de `recipe()`:

- Debe devolver un `dict` con:
  - `funcs`: contiene callables `R`, `G`, `B`.
  - `bands`: lista de bandas requeridas.
  - `emissive_units`: unidades para bandas emisivas (o `{}` si no aplica).

## 2) Registrar en el registry

Editar `goes_rgb/recipes_registry.py` y agregar una entrada al diccionario `RECIPE_REGISTRY`.

Patrón recomendado:

```python
RECIPE_REGISTRY["mi_falso_color"] = _load_custom_recipe(
    "config.custom_recipes.mi_falso_color",
    "config/custom_recipes/mi_falso_color.py",
)
```

Notas:

- La clave (`"mi_falso_color"`) es el nombre que luego usarás en YAML.
- El archivo puede exponer `recipe()` o `RECIPE`.

## 3) Usar la receta en YAML

Ejemplo de job:

```yaml
defaults:
  tipo_imagen: MCMI
  recorte: [-18.6, -56.45, -79.79, -53.0]

jobs:
  - nombre: prueba_custom
    datetime: 2025-08-30T15:00:21
    productos: [mi_falso_color]
    salidas: [PNG]
```

## Errores comunes

- `KeyError` de producto:
  - La receta no está registrada en `goes_rgb/recipes_registry.py`.
- Error de banda faltante:
  - Revisar que `bands` contenga todas las bandas usadas en `R/G/B`.
- Error de import:
  - Verificar ruta y nombre del archivo en `_load_custom_recipe(...)`.

## Convención sugerida

- Guardar todas las custom en `config/custom_recipes/`.
- Usar nombres descriptivos y estables para las claves de `RECIPE_REGISTRY`.
- Mantener recetas pequeñas y reutilizar helpers de `goes_rgb.helpers` cuando sea posible.
