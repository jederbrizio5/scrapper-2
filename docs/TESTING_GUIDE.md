# Guía de Pruebas y Validación (TESTING_GUIDE.md)

Este documento explica cómo está estructurado el sistema de testing del proyecto y cómo escribir pruebas limpias para nuevos módulos.

---

## 1. Estructura de Pruebas
Las pruebas viven en la carpeta `tests/` y se dividen en dos categorías:

* **Pruebas Unitarias (`tests/unit/`)**:
  * Evalúan componentes aislados de lógica de negocio (ej. parsing de textos, validación de DTOs, comportamiento del runner).
  * No tocan la base de datos ni hacen peticiones HTTP o de red reales.
  * Utilizan **mocks** para simular respuestas de Playwright o llamadas a la API de Meta.
* **Pruebas de Integración (`tests/integration/`)**:
  * Evalúan la interacción de múltiples componentes (ej. repositorios guardando en base de datos).
  * Utilizan una base de datos SQLite en memoria (`sqlite:///:memory:`) para que las pruebas sean rápidas, aisladas y no dejen residuos en tu máquina.

---

## 2. Ejecutar Pruebas
Para correr todas las pruebas del proyecto, utiliza el script de testing:
```bash
./scripts/test.sh
```

Para ejecutar un grupo específico de pruebas de manera detallada:
```bash
source venv/bin/activate
# Solo tests de adquisición
pytest tests/unit/meta_ads/ -v
# Solo tests de base de datos
pytest tests/integration/ -v
```

---

## 3. Reglas de Oro para Escribir Tests
1. **Deterministas**: Un test debe pasar el 100% de las veces si no se ha cambiado el código de producción. Evita dependencias de tiempo real o red.
2. **Aislados**: Cada prueba debe ejecutarse de forma independiente. Limpia el estado de la base de datos o mocks al finalizar cada test (esto se maneja automáticamente usando fixtures de pytest como `session`).
3. **Rápidos**: La suite completa de tests debe correr en pocos segundos.
4. **Mock de Red**: Si tu código usa `requests` o `playwright`, utiliza la librería `responses` o fixtures para mockear la llamada. Nunca pegues a un endpoint real en un test automatizado.
