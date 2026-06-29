#!/bin/bash
set -e

echo "Iniciando comprobación general..."

echo "--- 1. Formateo ---"
./scripts/format.sh

echo "--- 2. Linter ---"
./scripts/lint.sh

echo "--- 3. Tests ---"
./scripts/test.sh

echo "Comprobación general completada sin errores."
