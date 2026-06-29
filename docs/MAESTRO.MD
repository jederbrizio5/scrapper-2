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

El proyecto esta estabilizado hasta Fase 2.

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
- Componentes Playwright basicos para prueba de concepto del navegador.
- Tests unitarios e integracion mockeados.

Decision importante:

- La API de Meta queda como componente secundario y testeado, pero no sera la fuente principal para las proximas fases comerciales.
- La adquisicion futura debe basarse en navegador con Playwright, porque la API puede estar limitada a anuncios politicos o categorias que no cubren el objetivo comercial del proyecto.

No implementado todavia:

- Fase 3: extraccion robusta de dominios desde anuncios.
- Fase 4: scraper de landings.
- Fase 5: scoring de prospectos.
- Fase 6: CRM/exportacion.
- Fase 7: automatizacion.

## Arquitectura Vigente

```text
src/
├── config/                 # Configuracion y variables de entorno
├── database/               # Engine, sesiones y base declarativa SQLAlchemy
├── models/                 # Modelos ORM
├── repositories/           # Persistencia encapsulada por entidad
└── modules/
    └── meta_ads/
        ├── client/         # Cliente HTTP Meta Ads Library
        ├── dto/            # Objetos tipados de entrada/salida
        ├── parser/         # Parseo de JSON externo a DTOs internos
        ├── browser/        # Playwright y sesiones de navegador
        └── acquisition/    # PoC de busqueda/extraccion por navegador
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

La persistencia existe pero todavia no hay un orquestador productivo que conecte busquedas Meta con guardado en base de datos. Esa conexion debe hacerse en fases futuras sin meter persistencia dentro de `MetaClient`.

## Comandos Oficiales

- Instalar dependencias: `./scripts/install.sh`
- Ejecutar entrada principal: `./scripts/run.sh`
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

## Proxima Fase Recomendada

La siguiente fase natural es Fase 3: adquisicion por navegador y extraccion inicial.

Debe partir de `docs/phases/PHASE_03_BROWSER_ACQUISITION_PLAN.md`.

El objetivo es fortalecer la lectura de Meta Ads Library por navegador antes de extraer dominios, landings o scoring.
