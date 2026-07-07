---
name: project-guide
description: "Use when you need to understand the project architecture, phases, ADRs, development rules, or agent workflow. Triggered by keywords: MAESTRO, arquitectura, fases, ADR, decisiones, reglas, workflow, git workflow, PR, pull request, branch, coding standard, code style, logging, observabilidad, documentacion. Use ONLY for this specific Meta Ads prospecting project."
---

# Project Guide — Meta Ads Prospecting System

## Estado Actual

El proyecto esta estabilizado hasta Fase 3.2.
Implementado: Bootstrap, DB (SQLite + SQLAlchemy + Alembic), Meta Ads API Client, Browser Acquisition con Playwright (discovery + enrichment), checkpoint system, CLI completo, anti-deteccion.

## Arquitectura Vigente

```
src/
├── config/settings.py       # Variables de entorno
├── database/                # SQLAlchemy engine, sesiones, base declarativa
├── models/                  # ORM: Search, Domain, Company, Lead
├── repositories/            # BaseRepository + repos especificos
└── modules/meta_ads/
    ├── client/              # Cliente HTTP Meta Ads API (secundario)
    ├── dto/                 # Dataclasses tipadas
    ├── parser/              # Parseo JSON -> DTOs
    ├── browser/             # Playwright: BrowserManager, SessionManager
    └── acquisition/         # AdsSearcher, AdsExtractor, BrowserRunner
```

## Flujo de Datos (Browser)

```
keywords
  -> MetaAdsBrowserRunner
  -> AdsSearcher (busqueda en Meta Ads Library)
  -> AdsExtractor.extract_discovery_ads() (descubrimiento)
  -> AdsExtractor.enrich_ads() (enriquecimiento)
  -> BrowserAdResult[] (JSON de salida)
```

## Principios Obligatorios

- No hardcodear tokens, URLs privadas ni secretos.
- Usar variables de entorno para configuracion.
- No usar diccionarios raw si corresponde un DTO.
- Mantener cliente Meta desacoplado de base de datos.
- Persistir solo a traves de repositorios.
- Type hints obligatorios.
- Docstrings en formato Google.
- Tests unitarios o de integracion para toda logica nueva.
- `./scripts/check.sh` antes de cerrar cualquier tarea.
- No trabajar directo en `main`; usar ramas y Pull Requests.

## Comandos Oficiales

- `./scripts/install.sh` — Instalar dependencias
- `./scripts/run.sh` — Ejecutar entrada principal
- `python scripts/run_meta_ads_browser.py --keyword "curso" --limit 3 --headless` — Ejecutar scraper
- `./scripts/test.sh` — Tests
- `./scripts/format.sh` — Formatear
- `./scripts/lint.sh` — Lint
- `./scripts/check.sh` — Validacion completa

## Primary Agents

| Agente | Modo | Uso |
|--------|------|-----|
| `build` | primary | Implementar, ejecutar, orquestar pipeline |
| `plan` | primary | Analizar, disenar, revisar (solo lectura) |

Switchear con Tab.

## Subagentes

| Agente | Rol |
|--------|-----|
| `@scraper` | Playwright, anti-deteccion, DTOs |
| `@db` | SQLAlchemy, Alembic, repositorios |
| `@tester` | pytest, mocks, cobertura |
| `@reviewer` | Code review (solo lectura) |
| `@git` | Ramas, commits, PRs |
| `@docs` | Documentacion, ADRs |
| `@security` | Secrets, tokens, hardcodes |

## Pipeline Enterprise

1. PLAN → plan mode (analisis)
2. IMPLEMENTAR → build + subagentes
3. TESTEAR → @tester (pytest)
4. REVISAR → @reviewer (calidad)
5. SEGURIDAD → @security (secrets)
6. CHECK → ./scripts/check.sh
7. COMMIT → @git
8. ESPERAR → usuario aprueba merge

## Reglas de Desarrollo Permanentes

1. SRP: cada modulo una responsabilidad.
2. DRY: no duplicar logica.
3. KISS: no escribir codigo muerto.
4. Type hints estrictos.
5. Manejo de errores con try-except tipados + logging.
6. Configuracion por variables de entorno, nada hardcodeado.
7. ADRs en `docs/DECISIONS.md` para decisiones importantes.
8. Fases documentadas en `docs/phases/` con objetivo, alcance, pruebas, resultado.
9. Priorizar navegador Playwright sobre API Meta.
10. Todo PR con pruebas ejecutadas, riesgos y rollback.
