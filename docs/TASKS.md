# Backlog de Tareas y Plan de Ruta (TASKS.md)

Este archivo registra las tareas prioritarias del proyecto, organizadas por fases de desarrollo, con estados y criterios de éxito claros.

---

## 1. Fase Actual: Fase 3.2 (Estabilización) - COMPLETADA
* [x] **Tarea 3.2.1**: Implementar per-keyword limits (`--keyword "nombre:limite"`).
* [x] **Tarea 3.2.2**: Agregar checkpoints automáticos tras procesar cada keyword.
* [x] **Tarea 3.2.3**: Registrar signal handlers para SIGINT/SIGTERM para guardar datos parciales.
* [x] **Tarea 3.2.4**: Implementar modo `append` y dedup cross-ejecución con `--resume`.
* [x] **Tarea 3.2.5**: Crear modo `--enrich-only` in-place.

---

## 2. Próxima Fase: Fase 4 — Persistencia y Scraping de Landings (PENDIENTE)

### Fase 4.1: Integración con Base de Datos (Persistencia)
* **Objetivo**: Guardar los resultados JSON generados por el scraper de forma estructurada en la base de datos SQLite utilizando la capa de repositorios existente.
* **Tareas**:
  * [ ] **Tarea 4.1.1**: Diseñar un script orquestador (`src/modules/meta_ads/acquisition/persist_runner.py` o dentro de `src/main.py`) que consuma un archivo JSON de resultados o corra el runner directamente, y guarde los datos.
  * [ ] **Tarea 4.1.2**: Implementar la lógica para crear/actualizar un registro de `Search` (Búsqueda) por cada keyword procesada.
  * [ ] **Tarea 4.1.3**: Implementar el guardado de dominios en la tabla `domains`, asegurando que no se dupliquen (deduplicación por campo `dominio`).
  * [ ] **Tarea 4.1.4**: Crear la entidad `Company` ligada al dominio, usando el `advertiser_name` extraído y completando campos básicos (idioma, país).
  * [ ] **Tarea 4.1.5**: Registrar un nuevo `Lead` asociado a la empresa, con estado inicial "new" y fecha de descubrimiento.
  * [ ] **Tarea 4.1.6**: Escribir tests de integración completos para validar que la persistencia funciona sin romper la base de datos ni duplicar registros.

### Fase 4.2: Scraper de Landings (Scraper Landing)
* **Objetivo**: Navegar automáticamente a las landing pages válidas de los anunciantes y extraer información de contacto, redes sociales, industria y stack tecnológico.
* **Tareas**:
  * [ ] **Tarea 4.2.1**: Crear el módulo `src/modules/landing_scraper/` con una clase `LandingScraper`.
  * [ ] **Tarea 4.2.2**: Implementar la lectura de dominios pendientes de scraping desde la base de datos (domains activos sin lead enriquecido o con datos vacíos).
  * [ ] **Tarea 4.2.3**: Utilizar `httpx` (rápido, modo texto) con fallback a `Playwright` (si requiere renderizado de JS) para cargar la landing page.
  * [ ] **Tarea 4.2.4**: Parsear el HTML de la landing para extraer:
    * Correos electrónicos (mediante expresiones regulares optimizadas).
    * Teléfonos (patrones internacionales de WhatsApp/contacto).
    * Links de redes sociales (Linkedin, Facebook, Instagram, Twitter/X).
    * Título y meta description de la página (para clasificación de industria/propósito).
  * [ ] **Tarea 4.2.5**: Guardar la información enriquecida en la base de datos (actualizando campos de la empresa o agregando registros detallados de contacto).
  * [ ] **Tarea 4.2.6**: Añadir tests unitarios y de integración para el scraper de landings con páginas mockeadas.

---

## 3. Criterios de Aceptación para Phase 4
- El pipeline completo debe ejecutarse con un único comando.
- Ningún dominio debe duplicarse en la base de datos.
- Las búsquedas fallidas deben registrar su error y estado `failed` en la tabla `searches`.
- El scraper de landings debe respetar tiempos prudenciales (jitter) para no saturar los sitios web objetivo.
- `./scripts/check.sh` pasa al 100%.
