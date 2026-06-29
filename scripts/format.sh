#!/bin/bash
set -e

source venv/bin/activate 2>/dev/null || true

echo "Ejecutando formateador (ruff format)..."
ruff format src/ tests/
echo "Formateo finalizado exitosamente."
