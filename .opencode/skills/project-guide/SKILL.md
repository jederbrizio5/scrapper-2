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
- `./scripts/check.sh` — Validacion completa (format + lint + tests + mypy + metrics)

## Primary Agents (switch con Tab)

| Agente | Modo | Uso |
|--------|------|-----|
| `build` | primary | Implementar, ejecutar, orquestar pipeline |
| `plan` | primary | Analizar, disenar, revisar (solo lectura) |

Switchear con Tab.

## Subagentes (invocar con @)

| Agente | Rol | Skill que Carga | Permisos Clave | Steps |
|--------|-----|-----------------|----------------|-------|
| `@scraper` | Playwright, anti-deteccion, DTOs | `scraper-dev` | `edit: allow`, `bash: python scripts/run_meta_ads*` | 25 |
| `@db` | SQLAlchemy, Alembic, repositorios | `project-guide` | `edit: allow`, `bash: alembic*` | 20 |
| `@tester` | pytest, mocks, cobertura | `testing-guide` | `edit: allow`, `bash: pytest*` | 20 |
| `@reviewer` | Code review (solo lectura) | `project-guide` | `edit: deny`, `bash: git diff*, grep*, rg*` | 15 |
| `@git` | Ramas, commits, PRs, merge | _(ninguno)_ | `edit: deny`, `bash: git* / gh pr*` | 15 |
| `@docs` | Documentacion, ADRs, fases | `project-guide` | `edit: allow`, `bash: deny; git diff*` | 15 |
| `@security` | Secrets, tokens, hardcodes | `project-guide` | `edit: deny`, `bash: rg / grep / git diff*` | 15 |

## Pipeline Enterprise (10 pasos obligatorios)

Cada tarea sigue este orden. **No saltees pasos.**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. PLAN  (plan mode o @plan)                                                 │
│    build se pone en plan mode (Tab) o consulta a @plan                       │
│    Analiza: arquitectura, modulos afectados, riesgos                         │
│    Propone solucion: archivos a modificar, orden                             │
├──────────────────────────────────────────────────────────────────────────────┤
│ 2. IMPLEMENTAR  (build + subagentes)                                         │
│    build carga skill("project-guide") y codifica                             │
│    Delegar a @scraper (carga scraper-dev) o @db segun la tarea               │
│    Cambio minimo, type hints, docstrings, logging                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ 3. TESTEAR  (@tester)                                                        │
│    @tester carga skill("testing-guide")                                      │
│    Escribe tests unitarios/integracion                                       │
│    Ejecuta pytest, corrige fallas                                            │
│    Si falla → volver a paso 2                                                │
├──────────────────────────────────────────────────────────────────────────────┤
│ 4. REVISAR  (@reviewer)                                                      │
│    @reviewer carga skill("project-guide")                                    │
│    Code review: type hints, SRP, DRY, KISS, logging, docstrings             │
│    Sin print(), excepciones tipadas, sin imports muertos                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ 5. SEGURIDAD  (@security)                                                    │
│    @security carga skill("project-guide")                                    │
│    Escanea: API keys, tokens, .env, hardcodes en el diff                     │
│    Alerta si encuentra secretos                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 6. DOCUMENTAR  (@docs)                                                       │
│    @docs carga skill("project-guide")                                        │
│    Lee git diff para entender los cambios                                    │
│    Actualiza ADRs en docs/DECISIONS.md si corresponde                        │
│    Actualiza docs/phases/ si cambio de fase                                  │
│    Actualiza README.md si cambio instalacion/uso                             │
│    **Verifica skills en .opencode/skills/ si cambió arquitectura**          │
├──────────────────────────────────────────────────────────────────────────────┤
│ 7. CHECK  (./scripts/check.sh)                                               │
│    build ejecuta: ruff format + ruff check + pytest + mypy + metrics        │
│    TODO DEBE PASAR. Si falla → volver a paso 2                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ 8. COMMIT  (@git)                                                            │
│    git add + git commit -m "tipo: descripcion"                               │
│    git push -u origin rama                                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ 9. INFORMAR  (build)                                                         │
│    build compila informe final con:                                          │
│    - Que problema se resolvio                                                │
│    - Como se soluciono (archivos, modulos)                                   │
│    - Tests: resultado                                                        │
│    - Review: resultado                                                       │
│    - Seguridad: resultado                                                    │
│    - Documentacion: que se actualizo                                         │
│    - Rama: nombre y estado                                                   │
│    build entrega el informe al usuario                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ 10. ESPERAR ORDEN DE MERGE                                                  │
│     build informa: rama lista, cambios hechos                                │
│     USUARIO revisa, prueba, dice "merge a main"                              │
│     @git hace merge + push a main                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Reglas de Desarrollo Permanentes

1. **SRP**: cada modulo una responsabilidad.
2. **DRY**: no duplicar logica.
3. **KISS**: no escribir codigo muerto.
4. **Type hints estrictos**.
5. **Manejo de errores** con try-except tipados + logging.
6. **Configuracion** por variables de entorno, nada hardcodeado.
7. **ADRs** en `docs/DECISIONS.md` para decisiones importantes.
8. **Fases** documentadas en `docs/phases/` con objetivo, alcance, pruebas, resultado.
9. **Priorizar navegador Playwright** sobre API Meta.
10. **Todo PR** con pruebas ejecutadas, riesgos y rollback.

## Auto-Loading de Skills (Obligatorio)

Cada agente DEBE cargar su skill correspondiente AL INICIAR:

- `build` → `skill("project-guide")` al iniciar tarea
- `@scraper` → `skill("scraper-dev")` al iniciar
- `@tester` → `skill("testing-guide")` al iniciar
- `@db`, `@reviewer`, `@docs`, `@security` → `skill("project-guide")` al iniciar
- `@plan` → `skill("project-guide")` al iniciar
- `@git` → no requiere skill (operativo puro)

Si un agente no carga su skill, trabaja sin contexto completo → error probable.

## Informe Final (PASO 9 - Template Obligatorio)

Cuando termines el pipeline, compila y entrega este informe al usuario:

```markdown
## Resumen de la Tarea

**Problema:** [que se resolvio]

**Solucion:** [como se implemento, archivos modificados]

**Tests:** [resultado: X/Y pasando]

**Review:** [resultado: OK/observaciones]

**Seguridad:** [sin secretos / hallazgos]

**Documentacion:** [que se actualizo: ADRs, fases, README]

**Rama:** `[nombre-de-rama]` — pusheada, esperando merge a main
```

## Sync Skills ↔ Docs (Regla de Oro)

> **Si cambias arquitectura en `docs/`, actualiza `.opencode/skills/`. Si cambias skills, verifica `docs/`.**

Archivos espejo:
- `docs/MAESTRO.MD` + `docs/ARCHITECTURE.MD` + `docs/PHASES.MD` ↔ `.opencode/skills/project-guide/SKILL.md`
- `docs/doc.phase.3.md` ↔ `.opencode/skills/scraper-dev/SKILL.md`
- `docs/TESTING.md` ↔ `.opencode/skills/testing-guide/SKILL.md`

El PASO 6 (DOCUMENTAR) incluye verificación de este sync.