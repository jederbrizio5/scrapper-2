# Arquitectura del Sistema

La arquitectura esta dividida de forma modular para facilitar el mantenimiento y la escalabilidad.

## Estructura de Modulos

* **`src/config/`**: Variables de entorno y configuracion del sistema.
* **`src/database/`**: Conexion SQLAlchemy, sesiones y base declarativa.
* **`src/models/`**: Modelos ORM SQLAlchemy (Search, Domain, Company, Lead).
* **`src/repositories/`**: Operaciones de persistencia encapsuladas por entidad.
* **`src/modules/meta_ads/`**: Modulo de dominio para adquisicion de Meta Ads.
  * `dto/`: BrowserAdDiscovery, BrowserAdEnrichment, BrowserAdResult.
  * `exceptions/`: MetaException, RequestException.
  * `browser/`: BrowserManager y SessionManager (Playwright).
  * `acquisition/`: AdsSearcher, AdsExtractor, MetaAdsBrowserRunner.

Nota: `src/core/`, `src/services/` y `src/utils/` no existen actualmente.

## Flujo de Datos

### Flujo Principal (navegador, Fase 3)
```text
keywords
  -> MetaAdsBrowserRunner
  -> AdsSearcher (busqueda en Meta Ads Library)
  -> AdsExtractor.extract_discovery_ads() (descubrimiento)
  -> AdsExtractor.enrich_ads() (enriquecimiento)
  -> BrowserAdResult[] (JSON de salida)
```

### Flujo de Persistencia (Fase 1)
```text
Modelo ORM -> Repositorio -> Sesion SQLAlchemy -> SQLite
```

## Reglas Arquitectonicas

- No existe cliente HTTP de Meta API. Toda la adquisicion es via Playwright.
- La union entre adquisicion y persistencia debe vivir en un orquestador futuro.
- Playwright: tiempos configurables, reintentos limitados, logs con contexto, modo visible/headless.

## Caracteristicas de Fase 3.2

- Per-keyword limits, scroll infinito configurable, modo append, resume cross-ejecucion.
- Checkpoint por keyword con signal handler (SIGINT/SIGTERM).
- Split por keyword (archivos separados + index.json).
- Enrich in-place (modifica archivos originales).
- Reintentos con backoff exponencial y nueva sesion.
- Proxies (unico o lista rotativa round-robin).
- Sesion compartida (reutiliza contexto cada N keywords).
- Timeout global, formato hora Argentina, output con timestamp.
