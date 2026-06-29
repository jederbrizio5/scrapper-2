#!/bin/bash
set -e

source venv/bin/activate 2>/dev/null || true

echo "Ejecutando linter (ruff)..."
ruff check src/ tests/
echo "Linting finalizado exitosamente."
