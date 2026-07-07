# Meta Ads Prospecting System — Instrucciones Globales para Agentes

Eres un agente trabajando en el **Meta Ads Prospecting System**. Sigue estas reglas en cada interaccion.

## Orden de Lectura Obligatorio

Si no conoces el proyecto, lee en este orden:
1. `README.md`
2. `opencode.json`
3. `AGENTS.md`
4. `docs/MAESTRO.MD`
5. `docs/PROJECT.md`
6. `docs/ARCHITECTURE.md`
7. `docs/PHASES.md`
8. `docs/AGENT_WORKFLOW.md`
9. `docs/GIT_WORKFLOW.md`
10. `docs/DECISIONS.md`
11. `docs/phases/` (segun la fase activa)

## Reglas Obligatorias

- **No trabajes directo en `main`**. Crea una rama por tarea.
- **No mezcles fases**. Trabaja solo el alcance indicado.
- **`./scripts/check.sh`** debe pasar antes de cerrar cualquier tarea.
- **No hardcodees tokens, URLs privadas ni secretos.** Usa `src/config/settings.py` con variables de entorno.
- **No importes repositorios ni ORM desde `MetaClient` o el scraper.** La union entre adquisicion y persistencia debe vivir en un orquestador futuro.
- **Type hints obligatorios** en toda funcion o metodo nuevo.
- **Docstrings** en formato Google para modulos, clases, funciones publicas y complejas.
- **Logs** con `logging.getLogger(__name__)`. No `print()`.
- **Tests** obligatorios para toda logica nueva. Unitarios con mock, integracion con SQLite in-memory.
- **Commits pequeños y coherentes.** Prefijo: `feature/`, `fix/`, `docs/`, `test/`, `refactor/`, `chore/`.

## Arquitectura del Proyecto

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

## Primary Agents (switch con Tab)

| Agente | Modo | Acceso | Uso |
|--------|------|--------|-----|
| `build` | primary | Full (edit + bash) | Implementacion, codificar, ejecutar, orquestar pipeline |
| `plan` | primary | Solo lectura | Analisis, arquitectura, diseno, code review previo |

`build` es el default. Usa **Tab** para switchear a `plan` y volver.

## Subagentes (invocar con @)

| Agente | Rol | Permisos Clave | Steps |
|--------|-----|----------------|-------|
| `@scraper` | Playwright, anti-deteccion, DTOs | `edit: allow`, `bash: python scripts/run_meta_ads*` | 25 |
| `@db` | SQLAlchemy, Alembic, repositorios | `edit: allow`, `bash: alembic*` | 20 |
| `@tester` | pytest, mocks, cobertura | `edit: allow`, `bash: pytest*` | 20 |
| `@reviewer` | Code review (solo lectura) | `edit: deny`, `bash: git diff*` | 15 |
| `@git` | Ramas, commits, PRs, merge | `edit: deny`, `bash: git* / gh pr*` | 15 |
| `@docs` | Documentacion, ADRs, fases | `edit: allow`, `bash: deny` | 15 |
| `@security` | Secrets, tokens, hardcodes | `edit: deny`, `bash: rg / grep` | 15 |

## Pipeline Enterprise (obligatorio)

Cada tarea sigue este pipeline estricto. `build` lo orquesta completo.

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. PLAN  (plan mode o @plan)                                     │
│    build se pone en plan mode (Tab)                              │
│    Analiza: arquitectura, modulos afectados, riesgos             │
│    Propone solucion: archivos a modificar, orden                 │
├──────────────────────────────────────────────────────────────────┤
│ 2. IMPLEMENTAR  (build + subagentes)                             │
│    build codifica o delega a @scraper / @db segun la tarea       │
│    Cambio minimo, type hints, docstrings, logging                │
├──────────────────────────────────────────────────────────────────┤
│ 3. TESTEAR  (@tester)                                            │
│    Escribe tests unitarios/integracion                           │
│    Ejecuta pytest, corrige fallas                                │
│    Si falla → volver a paso 2                                    │
├──────────────────────────────────────────────────────────────────┤
│ 4. REVISAR  (@reviewer)                                          │
│    Code review: type hints, SRP, DRY, KISS, logging             │
│    Sin print(), excepciones tipadas, sin imports muertos         │
├──────────────────────────────────────────────────────────────────┤
│ 5. SEGURIDAD  (@security)                                        │
│    Escanea: API keys, tokens, .env, hardcodes en el diff         │
│    Alerta si encuentra secretos                                  │
├──────────────────────────────────────────────────────────────────┤
│ 6. CHECK  (./scripts/check.sh)                                   │
│    build ejecuta: ruff format + ruff check + pytest              │
│    TODO DEBE PASAR. Si falla → volver a paso 2                   │
├──────────────────────────────────────────────────────────────────┤
│ 7. COMMIT  (@git)                                                │
│    git add + git commit -m "tipo: descripcion"                   │
│    git push -u origin rama                                       │
├──────────────────────────────────────────────────────────────────┤
│ 8. ESPERAR ORDEN DE MERGE                                       │
│    build informa: rama lista, cambios hechos                     │
│    USUARIO revisa, prueba, dice "merge a main"                   │
│    @git hace merge + push a main                                 │
└──────────────────────────────────────────────────────────────────┘
```

## Skills Disponibles

| Skill | Contenido |
|-------|-----------|
| `project-guide` | MAESTRO.MD, arquitectura, fases, ADRs, reglas, git workflow, coding standard. |
| `scraper-dev` | Algoritmo detallado de Fase 3: anti-deteccion, discovery, enrichment, errores corregidos. |
| `testing-guide` | Estrategia de testing, reglas, dependencias. |

## MCPs Disponibles

| MCP | Tipo | Uso |
|-----|------|-----|
| Playwright | local | Debugging visual del scraper, screenshots, navegacion |
| GitHub | remote (OAuth) | PRs, issues, merge management para @git |

## Flujo de Trabajo Enterprise

```text
USUARIO: "hoy implementamos bloqueo de dominio x.com"

1. build arranca, se pone en plan mode (Tab)
2. plan analiza: ads_extractor.py → BLOCKED_DOMAINS
3. plan presenta: 1 archivo, 1 linea, sin riesgos
4. USUARIO: "ejecuta"
5. build: Tab → build mode, implementa
6. build → @tester: "verifica tests"
7. @tester corre pytest, pasa
8. build → @reviewer: "revisa"
9. @reviewer: type hints OK, SRP OK
10. build → @security: "escanea"
11. @security: sin secrets
12. build: ./scripts/check.sh → OK
13. build → @git: "commit y push"
14. @git: git add + git commit + git push
15. USUARIO: "merge a main"
16. @git: merge a main + push
```

## Principios SOLID Aplicados

- **S** — Single Responsibility: cada modulo hace una cosa (scraper no sabe de DB)
- **O** — Open/Closed: nuevos orígenes de datos sin modificar existentes
- **L** — Liskov: DTOs y repositorios son intercambiables
- **I** — Interface Segregation: cada subagente tiene solo los permisos que necesita
- **D** — Dependency Inversion: MetaClient no conoce DB, repositorios no conocen HTTP
