# Proyecto: Sistema de Prospeccion de Meta Ads

## Vision General
Sistema de recoleccion estructurada de anuncios desde Meta Ads Library, disenado modularmente por fases.

**Estado actual:** Fase 0, 1, 2, 3 y 3.2 completadas y estabilizadas. Fase 4 no iniciada.

Nota de producto: la API de Meta no debe considerarse la fuente principal futura. El camino principal es lectura por navegador con Playwright.

## Implementado

### Fase 0 - Bootstrap
- Scripts: instalacion, ejecucion, tests, lint, formato y check general.
- Dependencias: `requirements.txt` y `requirements-dev.txt`.
- Configuracion: variables de entorno via `src/config/settings.py`.

### Fase 1 - Infraestructura de Datos
- SQLite + SQLAlchemy 2.x + Alembic.
- Modelos: Search, Domain, Company, Lead.
- Repositorios genericos y especificos.
- Tests de base de datos mockeada.

### Fase 2 - Cliente Meta Ads API
- MetaClient HTTP desacoplado de persistencia.
- Excepciones tipadas: AuthenticationException, RateLimitException.
- Parser y DTOs estrictos.
- Tests con `responses` (sin conexion externa).

### Fase 3 - Adquisicion por Navegador
- Discovery: anuncios con landing externa, descripcion, domain, advertiser_name.
- Enrichment: usuarios sociales (FB/IG) y seguidores desde dialogo de detalles.
- Sin sesion de Facebook requerida.
- Modos headless y visible (debug).
- Anti-deteccion: flags Chromium, User-Agent realista, override de webdriver.
- CLI via `scripts/run_meta_ads_browser.py`.

### Fase 3.2 - Mejoras de Adquisicion
- Per-keyword limits, scroll infinito, modo append.
- Resume cross-ejecucion con deduplicacion.
- Checkpoint por keyword + signal handler.
- Split por keyword + index.json.
- Enrich in-place.
- Reintentos con backoff + nueva sesion.
- Proxies (unico o lista rotativa).
- Sesion compartida (cada N keywords).
- Timeout global, formato hora Argentina, output timestamp.

## Criterio de Estabilidad

El proyecto se considera estable cuando `./scripts/check.sh` pasa sin errores (28 tests: 25 unitarios + 3 integracion).

## Proxima Fase

**Fase 4: No definida** (no iniciada). Pendiente de definicion por producto.

## Documentacion por Fase

Cada fase tiene su archivo en `docs/phases/` con objetivo, alcance, pruebas y resultado final.
