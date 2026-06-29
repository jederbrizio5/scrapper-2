# Estándares de Código

* **Lenguaje**: Python 3.10+
* **Linter y Formatter**: Ruff. Todos los archivos deben pasar la validación sin errores o advertencias.
* **Typing**: Se debe usar mypy u otra herramienta de análisis estático (configurado más adelante, pero el código debe tener type hints obligatoriamente).
* **Nomenclatura**:
  - Variables y funciones: `snake_case`
  - Clases: `PascalCase`
  - Constantes: `UPPER_SNAKE_CASE`
* **Docstrings**: Formato Google o Sphinx para modulos, clases, funciones publicas y funciones complejas.
* **Logs**: usar `logging.getLogger(__name__)`; no usar `print()` fuera de scripts de entrada simples.
* **Documentacion de fases**: todo cambio funcional debe actualizar `docs/phases/`.
