# Meta Ads Prospecting System

Sistema modular de prospeccion comercial via **Meta Ads Library**. Adquisicion por navegador (Playwright) con discovery, enrichment, y pipeline de datos estructurados.

**Estado actual:** Fase 3 completada (adquisicion por navegador). Proxima: Fase 4 (no iniciada).

---

## Instalacion

```bash
./scripts/install.sh
source venv/bin/activate && playwright install chromium
```

## Uso Rapido

```bash
# Scrapeo basico con enrichment, split por keyword
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --keyword "marketing:30" --headless
```

```bash
# Solo discovery, sin enrichment
python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --headless --no-enrich
```

```bash
# Enriquecer resultados existentes (in-place)
python scripts/run_meta_ads_browser.py \
  --enrich-only output/mis_resultados.json --headless
```

```bash
# Modo append (retomar ejecucion)
python scripts/run_meta_ads_browser.py \
  --keyword "curso:100" --mode append --headless
```

## Scripts

| Comando | Descripcion |
|---------|-------------|
| `./scripts/install.sh` | Instalar dependencias |
| `./scripts/run.sh` | Ejecutar entrada principal |
| `./scripts/test.sh` | Ejecutar tests (unitarios + integracion) |
| `./scripts/format.sh` | Formatear codigo (ruff) |
| `./scripts/lint.sh` | Lint (ruff) |
| `./scripts/check.sh` | Validacion completa (obligatorio pre-commit) |

## Testing

```bash
./scripts/test.sh
# o directamente:
source venv/bin/activate && python -m pytest tests/ -v
```

28 tests (25 unitarios + 3 integracion) que pasan sin conexion externa.

## Estructura del Proyecto

```
src/
├── config/                 # Variables de entorno (settings.py)
├── database/               # SQLAlchemy engine, sesiones, base declarativa
├── models/                 # Modelos ORM: Search, Domain, Company, Lead
├── repositories/           # Persistencia encapsulada por entidad
└── modules/
    └── meta_ads/
        ├── dto/            # BrowserAdDiscovery, BrowserAdEnrichment, BrowserAdResult
        ├── exceptions/     # MetaException, RequestException
        ├── browser/        # BrowserManager, SessionManager (Playwright)
        └── acquisition/    # AdsSearcher, AdsExtractor, MetaAdsBrowserRunner
docs/                       # Documentacion y reglas de desarrollo
tests/                      # Tests unitarios y de integracion
scripts/                    # Instalacion, ejecucion, validacion
migrations/                 # Migraciones Alembic
```

## Documentacion para Agentes

Antes de implementar cambios, leer en orden:

1. `docs/MAESTRO.MD` — fuente de verdad del proyecto
2. `docs/PROJECT.md` — vision general y estado
3. `docs/ARCHITECTURE.md` — arquitectura del sistema
4. `docs/PHASES.md` — fases del proyecto
5. `docs/AGENT_WORKFLOW.md` — workflow para agentes
6. `docs/GIT_WORKFLOW.md` — flujo de trabajo git
7. `docs/DEVELOPMENT_RULES.md` — reglas de desarrollo
8. `docs/CODING_STANDARD.md` — estandar de codigo
9. `docs/DECISIONS.md` — registro de decisiones arquitectonicas
10. `docs/phases/` — documentacion por fase completada
