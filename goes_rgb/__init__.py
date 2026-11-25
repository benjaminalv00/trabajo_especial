"""Procesador de productos RGB a partir de imágenes ABI de GOES-R.

Uso como módulo desde otro programa:

    from goes_rgb import run_from_config
    archivos = run_from_config("config/example.yml")
"""


def __getattr__(name):
    # Import diferido: `import goes_rgb.helpers` no carga el runner ni las
    # recetas; solo se resuelve cuando alguien pide run_from_config.
    if name == "run_from_config":
        from goes_rgb.runner import run_from_config

        return run_from_config
    raise AttributeError(f"module 'goes_rgb' has no attribute {name!r}")


__all__ = ["run_from_config"]
