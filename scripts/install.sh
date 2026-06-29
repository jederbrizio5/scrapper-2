#!/bin/bash
set -e

echo "Preparando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activar el entorno virtual
source venv/bin/activate

echo "Instalando dependencias de desarrollo y producción..."
pip install -r requirements-dev.txt
echo "Dependencias instaladas exitosamente."
echo "IMPORTANTE: Para ejecutar los scripts manualmente, recuerda activar el entorno virtual con: source venv/bin/activate"
