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

## Agentes Disponibles

| Agente | Uso |
|--------|-----|
| `@primary` | Agente principal. Orquestacion general. |
| `@scraper` | Playwright, anti-deteccion, extraction, DTOs. |
| `@db` | Modelos SQLAlchemy, migraciones, repositorios. |
| `@tester` | Tests con pytest, mocks, cobertura. |
| `@reviewer` | Code review (solo lectura). |

Usa `@agent-name` para delegar tareas especificas.

## Skills Disponibles

| Skill | Contenido |
|-------|-----------|
| `project-guide` | MAESTRO.MD, arquitectura, fases, ADRs, reglas, git workflow, coding standard. |
| `scraper-dev` | Algoritmo detallado de Fase 3: anti-deteccion, discovery, enrichment, errores corregidos. |
| `testing-guide` | Estrategia de testing, reglas, dependencias. |

## Flujo de Trabajo Tipico

1. `git switch -c feature/mi-tarea` (nunca en main)
2. Leer documentacion relevante (docs/MAESTRO.MD, skill correspondiente)
3. Implementar cambio minimo con tests
4. `./scripts/check.sh` (format + lint + tests)
5. `git add` + `git commit -m "tipo: descripcion"`
6. Abrir Pull Request segun `docs/GIT_WORKFLOW.md`
