# OpenCode Multi-Agent Engineering — Meta Ads Prospecting System

## Indice

1. [Vision General](#1-vision-general)
2. [Arquitectura Multi-Agente](#2-arquitectura-multi-agente)
3. [Configuracion Raiz: opencode.json](#3-configuracion-raiz-opencodejson)
4. [Subagentes](#4-subagentes)
5. [Skills](#5-skills)
6. [Commands](#6-commands)
7. [MCP Servers](#7-mcp-servers)
8. [References](#8-references)
9. [AGENTS.md — Contrato Global](#9-agentsmd--contrato-global)
10. [Flujo de Trabajo](#10-flujo-de-trabajo)
11. [Estrategia de Testing de la Infraestructura](#11-estrategia-de-testing-de-la-infraestructura)
12. [Roadmap Futuro](#12-roadmap-futuro)

---

## 1. Vision General

Este documento describe la **infraestructura enterprise multi-agente** disenada para el
**Meta Ads Prospecting System** sobre **opencode**. No es documentacion del producto
(scraping, base de datos, etc.), sino de **como los agentes de IA colaboran** en el proyecto.

### Principios de Diseno

| Principio | Descripcion |
|-----------|-------------|
| **Agent-Native** | opencode entiende el proyecto sin intervencion humana |
| **Auto-contexto** | Skills y references se autocargan cuando se necesitan |
| **Delegacion explicita** | El agente primary delega a subagentes especializados |
| **Validacion obligatoria** | `./scripts/check.sh` es el gatekeeper de calidad |
| **Sin modelo hardcodeado** | El primary agent usa el modelo por defecto de opencode |

### Que Resuelve

**Antes**: Cada vez que un agente nuevo tocaba el proyecto, debia:
1. Leer `README.md` manualmente
2. Leer 10+ archivos en `docs/`
3. Recordar reglas, arquitectura, fases, ADRs
4. No saber a quien preguntarle por temas especificos

**Ahora**: opencode sabe automaticamente:
- Que agentes estan disponibles y para que
- Que skills cargar segun el contexto (scraping, testing, DB)
- Donde buscar documentacion (references)
- Que comandos ejecutar
- Como conectar el Playwright MCP para debugging visual

---

## 2. Arquitectura Multi-Agente

```
                    ┌─────────────────────────┐
                    │     @primary (default)   │
                    │  Orquestador general     │
                    │  Permisos: bash allow    │
                    └──────────┬──────────────┘
                               │ delega
               ┌───────────────┼───────────────────┐
               │               │                   │
        ┌──────▼──────┐ ┌──────▼──────┐  ┌────────▼────────┐
        │  @scraper   │ │    @db      │  │    @tester      │
        │  Subagent   │ │  Subagent   │  │   Subagent      │
        │  Playwright │ │  SQLAlchemy │  │   pytest/mocks  │
        │  anti-detect│ │  Alembic    │  │   cobertura     │
        │  edit: ask  │ │  edit: ask  │  │   edit: ask     │
        └─────────────┘ └─────────────┘  └─────────────────┘
               │
        ┌──────▼──────┐
        │  @reviewer  │
        │  Subagent   │
        │  Solo lectura│
        │  edit: deny │
        └─────────────┘
```

### Mecanismo de Delegacion

El agente `@primary` decide cuando delegar basado en la tarea:

```python
# Ejemplo: El agente primary recibe "hay que agregar una columna a la DB"
# Analyse: tarea de base de datos
# Accion: invoca @db via task() con instrucciones detalladas
# @db edita, @primary valida con ./scripts/check.sh
# Antes de commit, @primary pide review a @reviewer
```

Cada subagente tiene **alcance limitado**:
- `@scraper`: solo toca `src/modules/meta_ads/acquisition/`, `browser/`, `dto/`, `parser/`
- `@db`: solo toca `src/models/`, `src/repositories/`, `src/database/`, `migrations/`
- `@tester`: solo toca `tests/`
- `@reviewer`: solo lee, nunca edita

---

## 3. Configuracion Raiz: opencode.json

`opencode.json` es el corazon de la infraestructura. opencode lo lee al arrancar.

### Estructura

```json
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "primary",
  "instructions": [...],
  "references": {...},
  "skills": { "paths": [".opencode/skills"] },
  "agent": {...},
  "command": {...},
  "mcp": {...}
}
```

### Detalle de Cada Campo

#### `default_agent: "primary"`
El agente que se activa por defecto al iniciar una sesion. Usa el modelo default de opencode (sin hardcodear).

#### `instructions`
Cargados automaticamente al inicio de cada sesion, en orden:
1. `AGENTS.md` — Contrato global: reglas, agentes, skills, flujo
2. `.opencode/agents/primary.md` — Rol del orquestador
3. `docs/MAESTRO.MD` — Manual maestro del proyecto
4. `docs/ARCHITECTURE.md` — Arquitectura del sistema

#### `references`
Tres referencias disponibles via `@`:
- `@docs` → `docs/` — Documentacion general
- `@phases` → `docs/phases/` — Fases del proyecto
- `@scripts` → `scripts/` — Scripts de automatizacion

Cada referencia tiene `description` para que opencode sepa **cuando** usarla.

#### `skills`
Un solo path: `.opencode/skills`. opencode escanea recursivamente por `**/SKILL.md`.

#### `agent`
5 agentes definidos inline (ver seccion 4).

#### `command`
4 comandos con `template` para que opencode ejecute acciones (ver seccion 6).

#### `mcp`
Playwright MCP server (ver seccion 7).

### Decisiones de Diseno

| Decision | Por que |
|----------|---------|
| **Agent definitions inline** (vs files) | Son pocos y simples. Los files serian overkill. |
| **Sin model en primary** | Usa el default de opencode. El usuario elige su modelo globalmente. |
| **commands con template** vs simple descripcion | El template le dice al agente exactamente que hacer cuando se invoca `/comando`. |
| **MCP playwright habilitado** | El proyecto ES un scraper de navegador. Tener MCP de Playwright permite debugging visual y acciones directas del agente en el browser. |

---

## 4. Subagentes

### 4.1 @primary — Orquestador General

| Campo | Valor |
|-------|-------|
| `mode` | `primary` |
| `model` | (default de opencode) |
| `permission` | `bash: allow` |

**Responsabilidades**:
- Planificar antes de ejecutar (leer docs, entender contexto)
- Delegar a `@scraper`, `@db`, `@tester`, `@reviewer`
- Validar con `./scripts/check.sh`
- Documentar cambios en `docs/` y `docs/DECISIONS.md`

**Cuando delegar**:
- Tarea de scraping/browser → `@scraper`
- Tarea de DB/modelos/migraciones → `@db`
- Tarea de tests → `@tester`
- Antes de commit/PR → `@reviewer`

### 4.2 @scraper — Especialista en Scraping

| Campo | Valor |
|-------|-------|
| `mode` | `subagent` |
| `permission` | `edit: ask`, `bash: ask` |

**Alcance**: `src/modules/meta_ads/acquisition/`, `browser/`, `dto/`, `parser/`, `client/`

**Experiencia**: Playwright, anti-deteccion Chromium, extraccion DOM, React clicks via native JS,
parseo de seguidores (mil/mill), navegacion Meta Ads Library.

### 4.3 @db — Especialista en Base de Datos

| Campo | Valor |
|-------|-------|
| `mode` | `subagent` |
| `permission` | `edit: ask`, `bash: ask` |

**Alcance**: `src/models/`, `src/repositories/`, `src/database/`, `migrations/`

**Experiencia**: SQLAlchemy 2.x, Alembic, SQLite, patron repositorio, SQLite in-memory testing.

### 4.4 @tester — Especialista en Testing

| Campo | Valor |
|-------|-------|
| `mode` | `subagent` |
| `permission` | `edit: ask`, `bash: ask` |

**Alcance**: `tests/`

**Experiencia**: pytest, `MagicMock` para Playwright, `responses` para HTTP mocking,
SQLite in-memory para DB tests.

### 4.5 @reviewer — Code Reviewer

| Campo | Valor |
|-------|-------|
| `mode` | `subagent` |
| `permission` | `edit: deny`, `bash: ask` |

**Alcance**: Solo lectura. NO edita archivos.

**Checklist**:
- `./scripts/check.sh` pasa
- Type hints en todas las funciones
- Sin imports no usados
- Sin `print()` (usar logging)
- Excepciones tipadas
- Tests para toda logica nueva
- `docs/DECISIONS.md` actualizado
- Sin secretos en el diff
- La rama no es `main`

---

## 5. Skills

Los skills son archivos `SKILL.md` en `.opencode/skills/<name>/`. opencode los autocarga
cuando detecta palabras clave en la conversacion.

### 5.1 project-guide

| Campo | Valor |
|-------|-------|
| `name` | `project-guide` |
| `ubicacion` | `.opencode/skills/project-guide/SKILL.md` |
| `trigger keywords` | MAESTRO, arquitectura, fases, ADR, decisiones, workflow, PR, branch, coding standard |
| `uso exclusivo` | Solo para este proyecto Meta Ads |

**Contenido**: MAESTRO.MD resumido, arquitectura playground, flujo de datos, principios obligatorios,
comandos oficiales, reglas de desarrollo permanentes.

### 5.2 scraper-dev

| Campo | Valor |
|-------|-------|
| `name` | `scraper-dev` |
| `ubicacion` | `.opencode/skills/scraper-dev/SKILL.md` |
| `trigger keywords` | playwright, browser, anti-deteccion, discovery, enrichment, native_click, jitter, viewport, ad_library_url |
| `uso exclusivo` | Solo para el scraper de Meta Ads Library |

**Contenido**: Pipeline completo Browser→Session→Search→Extract, anti-deteccion detallada (9 flags,
viewport jitter, navigator.webdriver override), algoritmo de discovery (filtros URL, UI noise, BREAKs),
algoritmo de enrichment (dialog priority, native_click, parseo seguidores), 12+ errores corregidos,
CLI reference completa.

### 5.3 testing-guide

| Campo | Valor |
|-------|-------|
| `name` | `testing-guide` |
| `ubicacion` | `.opencode/skills/testing-guide/SKILL.md` |
| `trigger keywords` | test, pytest, mock, MagicMock, responses, conftest, fixture |
| `uso exclusivo` | Solo para este proyecto Meta Ads |

**Contenido**: Estrategia de testing, reglas, comandos de ejecucion, tabla de tests actuales,
patrones de mock para Playwright.

### Mecanismo de Autocarga

Cuando un agente menciona "playwright", "browser", "scraper" en la conversacion,
opencode detecta que `scraper-dev` es relevante y lo inyecta en el contexto.
El agente no tiene que pedirlo explicitamente.

---

## 6. Commands

Los commands son accesibles via `/comando` en el chat de opencode.

### 6.1 `/scrape`

```markdown
---
description: Ejecuta el scraper de Meta Ads Library.
agent: scraper
---

source venv/bin/activate && python scripts/run_meta_ads_browser.py $ARGUMENTS
```

**Template**: Ejecuta el scraper CLI con los argumentos que el usuario pase.
Delega automaticamente a `@scraper`.

**Ejemplos**:
- `/scrape --keyword "curso:30" --headless --no-enrich`
- `/scrape --keyword "curso:30" --keyword "marketing:100" --headless --no-split --output resultados.json`
- `/scrape --enrich-only resultados.json --headless`

### 6.2 `/test`

```markdown
---
description: Ejecuta los tests del proyecto.
agent: tester
---

source venv/bin/activate && ./scripts/test.sh
```

**Template**: Corre tests y corrige errores hasta que pasen todos.
Delega a `@tester`.

### 6.3 `/lint`

```markdown
---
description: Ejecuta Ruff.
---

source venv/bin/activate && ./scripts/lint.sh
```

**Template**: Corre ruff linting y corrige todos los problemas encontrados.

### 6.4 `/check`

```markdown
---
description: Ejecuta format + lint + tests.
---

source venv/bin/activate && ./scripts/check.sh
```

**Template**: Validacion completa. Corre format, lint y tests. Corrige errores hasta que el proyecto quede limpio.

### Beneficios de los Commands

- **Estandarizacion**: Todos los agentes usan los mismos comandos
- **Autocorreccion**: Los templates incluyen "corrige los errores encontrados"
- **Delegacion automatica**: `/scrape` usa `@scraper`, `/test` usa `@tester`

---

## 7. MCP Servers

### 7.1 Playwright MCP

```json
{
  "playwright": {
    "type": "local",
    "command": ["npx", "-y", "@playwright/mcp"],
    "enabled": true,
    "env": { "BROWSER": "chromium" }
  }
}
```

**Que hace**: Expone herramientas de Playwright directamente al agente de IA.
El agente puede:
- Navegar a URLs
- Tomar screenshots
- Hacer click en elementos
- Extraer texto del DOM
- Debuggear visualmente el scraper

**Por que es util**: El proyecto ES un scraper de Meta Ads Library con Playwright.
Tener el MCP permite al agente:
1. Ver que esta pasando en el navegador durante el scraping
2. Debuggear problemas de extraccion visualmente
3. Probar selectores CSS sin modificar codigo

**Verificado**: `npx @playwright/mcp --help` responde correctamente. El MCP esta listo.

### 7.2 Futuros MCPs Posibles

| MCP | Utilidad | Prioridad |
|-----|----------|-----------|
| **Filesystem** | Leer/escribir archivos estructuradamente | Media |
| **Memory/Knowledge** | Persistir contexto entre sesiones | Baja |
| **Database (SQLite)** | Consultar DB directamente desde el agente | Baja (los repos ya abstraen) |

---

## 8. References

Las references registran directorios del proyecto como contexto buscable via `@`.

```json
{
  "docs": {
    "path": "docs",
    "description": "Documentacion del proyecto: arquitectura, fases, ADRs, guias para agentes y reglas de desarrollo."
  },
  "phases": {
    "path": "docs/phases",
    "description": "Documentacion detallada de cada fase completada y su implementacion."
  },
  "scripts": {
    "path": "scripts",
    "description": "Scripts de instalacion, ejecucion, tests, lint, formato y validacion."
  }
}
```

**Uso**: El agente puede escribir `@docs` y opencode le muestra los archivos disponibles
en ese directorio. Tambien se usan implicitamente cuando el agente busca informacion.

---

## 9. AGENTS.md — Contrato Global

`AGENTS.md` en la raiz del proyecto es el **contrato que todo agente debe seguir**.

### Orden de Lectura Obligatorio

```
1. README.md
2. opencode.json
3. AGENTS.md
4. docs/MAESTRO.MD
5. docs/PROJECT.md
6. docs/ARCHITECTURE.md
7-11. docs/PHASES.md, AGENT_WORKFLOW.md, GIT_WORKFLOW.md, DECISIONS.md, phases/
```

### Reglas Obligatorias

- No trabajar directo en `main` (rama por tarea)
- No mezclar fases
- `./scripts/check.sh` obligatorio antes de cerrar
- No hardcodear secretos
- Type hints obligatorios
- Docstrings Google format
- Logs con `logging.getLogger(__name__)` (no `print()`)
- Tests obligatorios
- Commits con prefijo (`feature/`, `fix/`, `docs/`, `test/`, `refactor/`, `chore/`)

### Tabla de Agentes y Skills

Incluida en AGENTS.md para referencia rapida del agente.

---

## 10. Flujo de Trabajo

### Para un Desarrollador Humano

```
1. git switch -c feature/mi-tarea
2. Iniciar opencode en el proyecto
3. @primary ya conoce el proyecto (instructions, references, skills)
4. Pedir tarea: "implementa X"
5. @primary planifica, delega a subagentes si es necesario
6. @primary valida con ./scripts/check.sh
7. git add + git commit -m "tipo: descripcion"
8. @reviewer hace code review
9. git push y abrir Pull Request
```

### Para un Agente (ejemplo concreto)

```
Usuario: "agrega bloqueo de dominio tiktok.com al scraper"

@primary:
  1. Lee skill scraper-dev para entender el algoritmo actual
  2. Delega a @scraper: "agrega 'tiktok.com' a BLOCKED_DOMAINS en ads_extractor.py"
  3. @scraper edita el archivo, agrega test
  4. @primary valida con ./scripts/check.sh (32 tests pasan)
  5. Pide review a @reviewer
  6. git add + git commit -m "feature: block tiktok.com domain"
```

### Diagrama de Flujo

```
Usuario ──> @primary
  │
  ├── planifica (project-guide skill, references)
  ├── delega a subagente
  │     ├── @scraper (scraper-dev skill)
  │     ├── @db
  │     ├── @tester (testing-guide skill)
  │     └── @reviewer
  ├── valida (./scripts/check.sh via /check)
  └── entrega resultado
       ├── git commit
       └── instrucciones para PR
```

---

## 11. Estrategia de Testing de la Infraestructura

### Tests que Pasaron

```
32 passed in 0.68s
- tests/integration/test_repositories.py ...   (3 tests)
- tests/unit/meta_ads/test_browser_acquisition.py  (27 tests)
- tests/unit/meta_ads/test_meta_client.py ...  (3 tests)
- tests/unit/meta_ads/test_parser.py ..        (2 tests)
```

### Validacion de la Configuracion opencode

| Que se valido | Como | Resultado |
|---------------|------|-----------|
| `opencode.json` es JSON valido | `python3 -c "import json; json.load(...)"` | OK |
| `./scripts/check.sh` pasa | Ejecucion completa | OK (32 tests) |
| Ruff format + lint | `ruff format && ruff check` | OK (42 files) |
| Playwright MCP existe | `npx @playwright/mcp --help` | OK |
| Modelo no hardcodeado | `grep -r "model.*ollama" .opencode/ opencode.json` | Removido |
| Archivos innecesarios | Revision manual | 6 eliminados |
| Git log | `git log --oneline` | Commits coherentes |

---

## 12. Roadmap Futuro

| Mejora | Descripcion | Prioridad |
|--------|-------------|-----------|
| **GitHub Actions CI** | CI que corra `./scripts/check.sh` en cada PR | Alta |
| **Docker Compose** | Contenedor con Chromium + dependencias | Media |
| **MCP Filesystem** | Herramientas de archivos adicionales | Baja |
| **Memory MCP** | Persistir contexto entre sesiones de agentes | Baja |
| **Tests de la config misma** | Validar que `opencode.json` es correcto contra schema | Baja |
| **Auto-generar skills** | Script que compile `docs/` en skills actualizados | Media |

---

## Apendice A: Arbol de Archivos de la Infraestructura

```
/
├── opencode.json              ← Configuracion raiz opencode
├── AGENTS.md                  ← Contrato global para agentes
├── .opencode/
│   ├── agents/
│   │   ├── primary.md         ← Agente orquestador
│   │   ├── scraper.md         ← Especialista Playwright
│   │   ├── db.md              ← Especialista SQLAlchemy
│   │   ├── tester.md          ← Especialista pytest
│   │   └── reviewer.md        ← Code reviewer (solo lectura)
│   ├── skills/
│   │   ├── project-guide/
│   │   │   └── SKILL.md       ← Contexto general del proyecto
│   │   ├── scraper-dev/
│   │   │   └── SKILL.md       ← Algoritmo de scraping detallado
│   │   └── testing-guide/
│   │       └── SKILL.md       ← Estrategia de testing
│   └── commands/
│       ├── scrape.md           ← /scrape comando
│       ├── test.md             ← /test comando
│       ├── lint.md             ← /lint comando
│       └── check.md            ← /check comando
└── docs/                      ← Documentacion del proyecto
    ├── MAESTRO.MD             ← Manual maestro
    ├── ARCHITECTURE.md        ← Arquitectura del sistema
    ├── PROJECT.md             ← Estado del proyecto
    ├── PHASES.md              ← Fases
    ├── AGENT_WORKFLOW.md      ← Workflow para agentes
    ├── GIT_WORKFLOW.md        ← Flujo git
    ├── DEVELOPMENT_RULES.md   ← Reglas de desarrollo
    ├── CODING_STANDARD.md     ← Estandares de codigo
    ├── DECISIONS.md           ← ADRs (20+ decisiones)
    ├── TESTING.md             ← Estrategia de testing
    ├── LOGGING_AND_OBSERVABILITY.md
    ├── CODE_DOCUMENTATION.md
    └── phases/                ← Fases completadas
```

## Apendice B: Mecanismo de Autocarga de Skills

```
opencode arranca
  → lee opencode.json
  → skills.paths = [".opencode/skills"]
  → escanea .opencode/skills/**/SKILL.md
  → registra:
      - project-guide (triggers: MAESTRO, fases, ADR, ...)
      - scraper-dev (triggers: playwright, browser, ...)
      - testing-guide (triggers: test, pytest, mock, ...)

Cuando el usuario/agente menciona "playwright":
  → opencode detecta keyword match con scraper-dev
  → inyecta scraper-dev SKILL.md en el contexto del agente
  → el agente tiene acceso inmediato al algoritmo detallado sin pedirlo
```

---

*Documento generado el 2026-07-07. Mantenimiento: actualizar cuando se agreguen o modifiquen agentes, skills, MCPs o commands.*
