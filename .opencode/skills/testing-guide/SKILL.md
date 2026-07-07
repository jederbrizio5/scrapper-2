---
name: testing-guide
description: "Use when writing or running tests with pytest. Triggered by keywords: test, pytest, testing, mock, MagicMock, responses, unit test, integration test, cobertura, conftest, fixture, assert, test descubrimiento. Use ONLY for this Meta Ads prospecting project."
---

# Testing Guide — Meta Ads Prospecting System

## Estrategia

El proyecto usa `pytest` para pruebas automatizadas.

## Reglas

- Toda funcion/metodo nuevo debe tener al menos un test unitario
- Tests deben ser rapidos (no depender de internet real)
- Tests lentos o de integracion deben ir en `tests/integration/`
- Usar `MagicMock` para Playwright (browser, page, context)
- Usar `responses` para mockear HTTP a Meta API
- Tests de DB con SQLite in-memory (ver `tests/integration/conftest.py`)
- No agregar dependencias de test sin justificarlo en `docs/DECISIONS.md`

## Ejecucion

```bash
./scripts/test.sh                        # Todos los tests
python -m pytest tests/ -v              # Directo con pytest
python -m pytest tests/unit/meta_ads/test_browser_acquisition.py -v --tb=long  # Test especifico
./scripts/check.sh                      # Validacion completa (format + lint + tests)
```

## Tests Actuales

| Archivo | Tipo | Descripcion |
|---------|------|-------------|
| `tests/unit/meta_ads/test_browser_acquisition.py` | Unitario | 33 tests para BrowserManager, SessionManager, AdsSearcher, AdsExtractor, BrowserRunner con MagicMock |
| `tests/unit/meta_ads/test_meta_client.py` | Unitario | 3 tests para MetaClient con responses |
| `tests/unit/meta_ads/test_parser.py` | Unitario | 2 tests para MetaParser |
| `tests/integration/test_repositories.py` | Integracion | CRUD de repositorios con SQLite in-memory |

## Patrones de Mock

```python
from unittest.mock import MagicMock, AsyncMock

# Mock de Playwright page
page = MagicMock()
page.goto = AsyncMock()
page.query_selector_all = MagicMock(return_value=[])
page.evaluate = AsyncMock()
```
