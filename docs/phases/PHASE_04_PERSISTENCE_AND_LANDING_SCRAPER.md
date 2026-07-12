# Fase 4: Persistencia y Scraping de Landings

## Estado

Pendiente

## Objetivo

Unir la adquisición de anuncios por navegador (Fase 3/3.2) con la base de datos relacional SQLite (Fase 1) para guardar búsquedas, dominios, empresas y leads de forma estructurada, y desarrollar un scraper web secundario que extraiga información de contacto (correos, teléfonos, redes sociales) desde las landing pages de los anunciantes.

---

## Alcance

Esta fase se divide en dos sub-fases principales:

### Sub-Fase 4.1: Persistencia en Base de Datos
* **Orquestador de Persistencia**: Crear un componente que reciba la lista de `BrowserAdResult` (o ejecute el runner) y guarde los datos en la base de datos local SQLite utilizando la capa de repositorios.
* **Modelo Search**: Registrar cada ejecución de keyword en la tabla `searches` con fecha, idioma, país y estado (`completed` o `failed`).
* **Modelo Domain**: Registrar los dominios descubiertos en la tabla `domains`, asegurando deduplicación a nivel de dominio.
* **Modelo Company**: Crear la empresa asociada al dominio con el `advertiser_name` obtenido, el idioma y el país correspondientes.
* **Modelo Lead**: Crear una oportunidad de Lead asociada a la empresa con score inicial `0.0` y estado `new`.

### Sub-Fase 4.2: Scraper de Landings
* **Clase LandingScraper**: Crear una clase capaz de leer dominios descubiertos y sin procesar de la base de datos, abrir su Landing URL (usando `httpx` para velocidad o `Playwright` para sitios con JS), y parsear su contenido.
* **Extracción de Contacto**:
  * Correos electrónicos (mediante expresiones regulares).
  * Teléfonos de contacto (patrones de número telefónico y botones de WhatsApp/Messenger).
  * Enlaces a redes sociales adicionales (LinkedIn, Twitter/X).
* **Actualización en DB**: Guardar la información enriquecida actualizando el registro de `Company` o `Lead`.

---

## Fuera De Alcance

* Algoritmo de scoring avanzado (se mantendrá en `0.0` o con una ponderación simple de seguidores por el momento; se definirá en la Fase 5).
* Despliegue en VPS o Docker (se mantiene local con SQLite).
* Panel de administración visual (se mantiene ejecución por consola/CLI).

---

## Archivos A Crear O Modificar

- `src/modules/meta_ads/acquisition/persist_runner.py`: Nuevo orquestador que realiza la persistencia en base de datos.
- `src/modules/landing_scraper/scraper.py`: Nuevo scraper para extraer datos de contacto desde las landing pages.
- `src/main.py`: Modificar para incluir el flujo completo: Búsqueda -> Scraper Meta -> Persistencia en DB -> Scraping de Landings.
- `tests/integration/test_persistence_flow.py`: Pruebas de integración del flujo de guardado.
- `tests/unit/test_landing_scraper.py`: Pruebas unitarias para la extracción en landing pages.
- `docs/phases/PHASE_04_PERSISTENCE_AND_LANDING_SCRAPER.md`: Este documento.
- `docs/PROJECT_STATE.md`: Actualizar tras la finalización.

---

## Como Se Ejecuta

### Ejecución de Persistencia (Sub-Fase 4.1)
Se creará un nuevo script de consola o se integrará en `src/main.py`:
```bash
# Ejecutar búsqueda en Meta Ads y guardar directamente en SQLite
python src/main.py --keyword "curso:10" --keyword "marketing:10" --headless
```

### Ejecución del Scraper de Landings (Sub-Fase 4.2)
```bash
# Procesar dominios pendientes en la base de datos y extraer información de contacto
python scripts/run_landing_scraper.py --limit 20
```

---

## Como Se Prueba

```bash
# Ejecutar todos los tests (incluyendo los nuevos)
./scripts/test.sh

# Ejecutar específicamente el flujo de integración de persistencia
pytest tests/integration/test_persistence_flow.py -v
```

---

## Logs Esperados

```text
2026-07-07 10:00:00 INFO  Iniciando proceso de prospección...
2026-07-07 10:00:01 INFO  Registrando búsqueda para keyword='curso' en base de datos.
2026-07-07 10:00:05 INFO  Ejecutando scraper Meta Ads...
2026-07-07 10:01:20 INFO  Adquisición finalizada. Procesando 15 resultados...
2026-07-07 10:01:21 INFO  Persistiendo dominio='ejemplo.com' -> Registrado en DB.
2026-07-07 10:01:21 INFO  Creando empresa='Ejemplo Academia' asociada al dominio.
2026-07-07 10:01:22 INFO  Registrando lead para la empresa (ID=1).
2026-07-07 10:01:25 INFO  Persistencia completada. 15 leads registrados.
2026-07-07 10:01:25 INFO  Iniciando Scraping de Landings para 15 dominios pendientes...
2026-07-07 10:01:30 INFO  Scrapeando landing='https://ejemplo.com'...
2026-07-07 10:01:32 INFO  Contacto extraído para ejemplo.com: email='contacto@ejemplo.com', phone='+5411223344'
2026-07-07 10:01:32 INFO  Actualizando datos de empresa ID=1 en DB.
2026-07-07 10:02:00 INFO  Proceso de prospección y scraping de landings finalizado con éxito.
```

---

## Criterios De Aceptacion

- [ ] `./scripts/check.sh` pasa limpio al 100%.
- [ ] La base de datos SQLite registra correctamente búsquedas, dominios, empresas y leads sin duplicar entradas.
- [ ] El scraper de landings extrae correctamente correos electrónicos y teléfonos de ejemplo de páginas locales mockeadas.
- [ ] Se capturan y manejan excepciones de red (timeouts, error 404, error 500) en el scraper de landings para no romper la ejecución.
- [ ] La documentación se actualiza con los resultados de la implementación.
