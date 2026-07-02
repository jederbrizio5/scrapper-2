# Manual Maestro del Proyecto

Este archivo es la fuente de verdad para cualquier persona, IA o agente que trabaje en este proyecto.

Antes de modificar codigo, leer en este orden:

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

## Estado Actual

El proyecto esta estabilizado hasta Fase 3.2.

Implementado:

- Bootstrap de proyecto con scripts de instalacion, ejecucion, lint, formato, tests y check general.
- Configuracion por variables de entorno en `src/config/settings.py`.
- Base de datos SQLite con SQLAlchemy 2.x.
- Migraciones Alembic en `migrations/`.
- Modelos ORM: `Search`, `Domain`, `Company`, `Lead`.
- Repositorios: `SearchRepository`, `DomainRepository`, `CompanyRepository`, `LeadRepository`.
- Cliente Meta Ads Library desacoplado de persistencia.
- DTOs para requests/responses de Meta Ads.
- Parser de respuesta Graph API a DTOs.
- Adquisicion por navegador con Playwright: discovery y enrichment.
- Extraction de usuarios sociales (FB/IG) y seguidores desde Meta Ads Library.
- Tests unitarios e integracion mockeados.
- Fase 3.2: configuracion total por CLI, persistencia robusta con checkpoint y signal handler,
  enrichment-only, dedup cross-keyword, limites por keyword, bloqueo extra de dominios.

Decision importante:

- La API de Meta queda como componente secundario y testeado.
- La adquisicion principal se basa en navegador con Playwright, porque la API puede estar limitada a anuncios politicos o categorias que no cubren el objetivo comercial del proyecto.
- Meta Ads Library funciona sin sesion de Facebook para discovery y enrichment.

## Arquitectura Vigente

```text
src/
├── config/                 # Configuracion y variables de entorno
├── database/               # Engine, sesiones y base declarativa SQLAlchemy
├── models/                 # Modelos ORM
├── repositories/           # Persistencia encapsulada por entidad
└── modules/
    └── meta_ads/
        ├── client/         # Cliente HTTP Meta Ads Library (secundario)
        ├── dto/            # Objetos tipados de entrada/salida
        ├── parser/         # Parseo de JSON externo a DTOs internos
        ├── browser/        # Playwright: BrowserManager, SessionManager
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

## Flujo De Datos Actual

```text
SearchRequest
  -> MetaClient.search_ads()
  -> MetaParser.parse_search_response()
  -> SearchResponse[Ad]
```

Flujo de Fase 3 por navegador:

```text
keywords
  -> MetaAdsBrowserRunner
  -> AdsSearcher (busqueda en Meta Ads Library)
  -> AdsExtractor.extract_discovery_ads() (descubrimiento)
  -> AdsExtractor.enrich_ads() (enriquecimiento)
  -> BrowserAdResult[] (JSON de salida)
```

La persistencia existe pero todavia no hay un orquestador productivo que conecte busquedas Meta con guardado en base de datos. Esa conexion no debe meterse dentro de `MetaClient` ni dentro del scraper por navegador.

## Comandos Oficiales

- Instalar dependencias: `./scripts/install.sh`
- Ejecutar entrada principal: `./scripts/run.sh`
- Ejecutar scraper Fase 3: `python scripts/run_meta_ads_browser.py --keyword "curso" --limit 3 --headless`
- Ejecutar tests: `./scripts/test.sh`
- Formatear: `./scripts/format.sh`
- Lint: `./scripts/lint.sh`
- Validacion completa: `./scripts/check.sh`

## Checklist Para Agentes

Antes de finalizar una tarea, confirmar:

- `./scripts/check.sh` pasa.
- No se agregaron secretos.
- La rama de trabajo no es `main`.
- El Pull Request incluye pruebas, riesgos y rollback.
- No se mezclaron responsabilidades entre cliente, parser, repositorio y servicios.
- La documentacion fue actualizada si cambio arquitectura, fase o uso.
- `docs/DECISIONS.md` fue actualizado si hubo una decision relevante.

## Fase Actual

La fase actual es Fase 3 completada: adquisicion por navegador y extraccion inicial.

El objetivo fue abrir Meta Ads Library, aplicar filtros, extraer anuncios con landing externa y enriquecer desde el detalle.

La documentacion de la fase completa vive en `docs/phases/PHASE_03_BROWSER_ACQUISITION_PLAN.md`.
