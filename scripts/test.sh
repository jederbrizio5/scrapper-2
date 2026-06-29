#!/bin/bash
set -e

source venv/bin/activate 2>/dev/null || true

echo "Ejecutando tests unitarios..."
PYTHONPATH=. pytest tests/
echo "Tests finalizados."
