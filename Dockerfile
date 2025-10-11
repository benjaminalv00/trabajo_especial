# --- Etapa 1: Definir el Entorno Base ---
FROM mambaorg/micromamba:1.5.8 as builder

WORKDIR /app

# --- Etapa 2: Copiar TODO el código fuente ---
# Copiamos todo primero, para que setup.py esté disponible durante la instalación.
COPY . .

# --- Etapa 3: Ajustar Permisos ---
# Cambiamos al usuario root para poder cambiar el propietario de los archivos.
USER root
# Damos permisos de la carpeta /app al usuario de mamba.
RUN chown -R $MAMBA_USER:$MAMBA_USER /app
# Volvemos al usuario normal y seguro.
USER $MAMBA_USER

# --- Etapa 4: Instalar Dependencias ---
# Ahora sí, al ejecutar la instalación, pip encontrará setup.py y podrá
# instalar tu paquete 'goes_rgb' en modo editable.
RUN micromamba install -y -n base -f environment.yml && \
    micromamba clean --all --yes

# --- Etapa 5: Definir el Comando de Ejecución ---
# El punto de entrada sigue siendo tu script principal.
# Le damos la ruta completa al ejecutable de Python dentro del entorno de Conda.
ENTRYPOINT ["/opt/conda/bin/python", "main.py"]