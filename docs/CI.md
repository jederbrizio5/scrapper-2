# Guía de Integración Continua (CI.md)

Este documento detalla el flujo de validación automática que se debe ejecutar en cada cambio de código.

---

## 1. Integración Continua Local (CLI)
Dado que no existe una infraestructura de CI/CD en la nube configurada por el momento, la verificación de calidad se realiza de manera local. 

Antes de realizar un commit o abrir un Pull Request, es obligatorio ejecutar el validador general:
```bash
./scripts/check.sh
```

Este comando ejecuta de forma secuencial:
1. **Formateo**: Aplica ruff format para estandarizar indentaciones y espaciados.
2. **Linter**: Corre ruff check para buscar bugs potenciales, importaciones sin usar o variables sin definir.
3. **Tests**: Corre pytest sobre la carpeta `tests/` para asegurar que ningún cambio rompió las funcionalidades existentes.

Si alguno de estos pasos falla, el script se detendrá inmediatamente e indicará el error. Debes resolverlo antes de guardar tus cambios.

---

## 2. Configuración Futura (GitHub Actions)
Si en el futuro decides mover este repositorio a GitHub, puedes añadir un flujo de GitHub Actions para automatizar este proceso.

Crea un archivo `.github/workflows/ci.yml` con el siguiente contenido:

```yaml
name: CI Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        ./scripts/install.sh
    - name: Install Playwright Browsers
      run: |
        source venv/bin/activate
        playwright install chromium
    - name: Run Quality Checks
      run: |
        ./scripts/check.sh
```
