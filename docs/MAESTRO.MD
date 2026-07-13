# Manual Maestro del Proyecto

Este archivo es la fuente de verdad absoluta para cualquier persona, IA o agente que trabaje en este proyecto.

## Orden de Lectura Obligatorio

Antes de modificar codigo, leer los siguientes documentos en este orden estricto:

1. `README.md`
2. `docs/MAESTRO.MD`
3. `docs/PROJECT.md`
4. `docs/ARCHITECTURE.md`
5. `docs/PHASES.md`
6. `docs/AGENT_WORKFLOW.md`
7. `docs/GIT_WORKFLOW.md`
8. `docs/CODE_DOCUMENTATION.md`
9. `docs/LOGGING_AND_OBSERVABILITY.md`
10. `docs/TESTING.md`
11. `docs/DEVELOPMENT_RULES.md`
12. `docs/CODING_STANDARD.md`
13. `docs/DECISIONS.md`
14. `docs/phases/`

## Estado Actual del Proyecto

El proyecto esta estabilizado hasta Fase 3 (completada). La Fase 4 no ha comenzado.

### Fase 0 - Bootstrap
- Scripts de instalacion, ejecucion, lint, formato, tests y check general.
- Configuracion por variables de entorno en `src/config/settings.py`.
- Dependencias gestionadas via `requirements.txt` y `requirements-dev.txt`.

### Fase 1 - Infraestructura de Datos
- Base de datos SQLite con SQLAlchemy 2.x y Alembic para migraciones.
- Modelos ORM: `Search`, `Domain`, `Company`, `Lead`.
- Repositorios: `SearchRepository`, `DomainRepository`, `CompanyRepository`, `LeadRepository`.
- Tests unitarios y de integracion con base de datos mockeada.

### Fase 2 - Cliente Meta Ads API (eliminado)
- Cliente HTTP `MetaClient` fue eliminado. No se utiliza en produccion.
- La adquisicion se realiza exclusivamente via navegador (Playwright).

### Fase 3 - Adquisicion por Navegador (Playwright)
- Sistema completo de discovery y enrichment desde Meta Ads Library.
- Anti-deteccion: flags Chromium, User-Agent realista, `navigator.webdriver` override.
- Discovery: extraccion de anuncios con landing externa, descripcion, domain, advertiser_name.
- Enrichment: dialogo de detalles, usuarios sociales (FB/IG), seguidores.
- Sin sesion de Facebook requerida.
- Modos headless y visible (debug).
- CLI via `scripts/run_meta_ads_browser.py`.

### Fase 3.2 - Mejoras de Adquisicion (completada)
- Per-keyword limits via `"keyword:limite"`.
- Scroll infinito configurable (`--max-scrolls`, `--empty-scrolls`).
- Modo append para retomar ejecuciones.
- Resume cross-ejecucion con deduplicacion.
- Checkpoint por keyword con signal handler (SIGINT/SIGTERM).
- Split por keyword en archivos separados + index.json.
- Enrich in-place (modifica archivos originales sin duplicar).
- Reintentos automaticos con backoff exponencial y nueva sesion.
- Proxies: unico o lista rotativa round-robin.
- Sesion compartida (reutiliza contexto Playwright cada N keywords).
- Timeout global configurable.
- Formato hora Argentina en logs y datos.
- Output con timestamp automatico.

### Decisiones Arquitectonicas Clave

- Toda la adquisicion se basa en navegador con Playwright (Meta Ads Library).
- Meta Ads Library funciona sin sesion de Facebook.
- No existe cliente HTTP de Meta API — fue eliminado por no usarse en produccion.
- La conexion entre adquisicion y persistencia debe vivir en un orquestador futuro.

## Arquitectura Vigente

```text
src/
├── config/                 # Configuracion y variables de entorno
├── database/               # Engine, sesiones y base declarativa SQLAlchemy
├── models/                 # Modelos ORM
├── repositories/           # Persistencia encapsulada por entidad
└── modules/
    └── meta_ads/
        ├── dto/            # BrowserAdDiscovery, BrowserAdEnrichment, BrowserAdResult
        ├── exceptions/     # MetaException, RequestException
        ├── browser/        # BrowserManager, SessionManager (Playwright)
        └── acquisition/    # AdsSearcher, AdsExtractor, MetaAdsBrowserRunner
```

## Principios Obligatorios

- No hardcodear tokens, URLs privadas ni secretos.
- Usar variables de entorno para configuracion.
- No usar diccionarios raw en logica de negocio si corresponde un DTO.
- Mantener cliente Meta desacoplado de base de datos.
- Persistir solo a traves de repositorios.
- Cada nueva funcion o metodo debe tener type hints.
- Cada clase, modulo o funcion relevante debe tener docstring.
- Cada proceso importante debe tener logs utiles para diagnostico.
- Cada nueva logica debe tener test unitario o de integracion segun corresponda.
- Antes de cerrar cualquier tarea, ejecutar `./scripts/check.sh`.
- No trabajar directo en `main`; usar ramas y Pull Requests segun `docs/GIT_WORKFLOW.md`.
- Cualquier integracion nueva debe documentar riesgos, plan de rollback y pasos de verificacion.

## Flujo De Datos

### Flujo Principal (navegador)
```text
keywords
  -> MetaAdsBrowserRunner
  -> AdsSearcher (busqueda en Meta Ads Library)
  -> AdsExtractor.extract_discovery_ads() (descubrimiento)
  -> AdsExtractor.enrich_ads() (enriquecimiento)
  -> BrowserAdResult[] (JSON de salida)
```

La persistencia existe pero todavia no hay un orquestador productivo que conecte busquedas Meta con guardado en base de datos.

## Comandos Oficiales

| Comando | Descripcion |
|---------|-------------|
| `./scripts/install.sh` | Instalar dependencias |
| `./scripts/run.sh` | Ejecutar entrada principal |
| `python scripts/run_meta_ads_browser.py --keyword "curso" --limit 3 --headless` | Ejecutar scraper Fase 3 |
| `./scripts/test.sh` | Ejecutar tests |
| `./scripts/format.sh` | Formatear codigo |
| `./scripts/lint.sh` | Lint |
| `./scripts/check.sh` | Validacion completa (obligatorio antes de cerrar tareas) |

## Checklist Para Agentes

Antes de finalizar cualquier tarea:

- [ ] `./scripts/check.sh` pasa sin errores.
- [ ] No se agregaron secretos ni credenciales al repositorio.
- [ ] La rama de trabajo no es `main`.
- [ ] El Pull Request incluye pruebas, riesgos y plan de rollback.
- [ ] No se mezclaron responsabilidades entre cliente, parser, repositorio y servicios.
- [ ] La documentacion fue actualizada si cambio arquitectura, fase o uso.
- [ ] `docs/DECISIONS.md` fue actualizado si hubo una decision relevante.
- [ ] No hay archivos, modulos o tests huerfanos que no correspondan a la fase actual.

## Fase Actual

**Fase 3 completada.** Proxima: **Fase 4 (no iniciada)**.

Documentacion de fase completada en `docs/phases/PHASE_03_BROWSER_ACQUISITION_PLAN.md`.

La planificacion de Fase 4 se definira cuando el producto lo indique.
