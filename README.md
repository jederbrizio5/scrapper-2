# Meta Ads Prospecting System

## Descripción
Sistema modular de prospección de Meta Ads preparado para desarrollarse por fases mediante personas o agentes de IA.

El estado actual cubre bootstrap, infraestructura de datos, cliente Meta Ads Library y adquisición robusta por navegador (Fase 3 completa). Las fases siguientes deben continuar desde la documentación en `docs/`, especialmente `docs/MAESTRO.MD`.

## Instalación
Para instalar las dependencias necesarias:

`./scripts/install.sh`

Si Playwright necesita navegadores en tu entorno, ejecutar luego:

`source venv/bin/activate && playwright install chromium`

## Ejecución
Para iniciar el punto de entrada principal:

`./scripts/run.sh`

Para ejecutar la prueba de concepto de navegador:

`source venv/bin/activate && PYTHONPATH=. python scripts/run_poc.py`

Para ejecutar Fase 3 contra Meta Ads Library y traer 3 anuncios por keyword con landing externa:

`source venv/bin/activate && python scripts/run_meta_ads_browser.py --keyword "curso" --keyword "marketing" --limit 3 --headless`

Para ejecutar sin enriquecimiento (solo discovery):

`source venv/bin/activate && python scripts/run_meta_ads_browser.py --keyword "curso" --limit 3 --headless --no-enrich`

El resultado queda en `output/meta_ads_browser_results.json`. Para depurar visualmente, ejecutar sin `--headless`.

## Testing
Para correr la suite de tests (unitarios y de integración):

`./scripts/test.sh`

## Linting y Formato
Para revisar el código (lint):

`./scripts/lint.sh`

Para formatear el código:

`./scripts/format.sh`

Para comprobar que todo funciona (tests, lint):

`./scripts/check.sh`

Este comando es obligatorio antes de considerar cerrada cualquier tarea.

## Documentación Para Agentes
Antes de pedirle a otra IA/agente que implemente una fase, indicarle que lea:

- `docs/MAESTRO.MD`
- `docs/AGENT_WORKFLOW.md`
- `docs/GIT_WORKFLOW.md`
- `docs/PROJECT.md`
- `docs/ARCHITECTURE.md`
- `docs/PHASES.md`

Los agentes no deben trabajar directo sobre `main`. Cada tarea debe hacerse en una rama propia, validarse con `./scripts/check.sh` y cerrarse mediante Pull Request con pruebas, riesgos y plan de rollback.

## Estructura del Proyecto
- `src/`: Código fuente principal.
- `docs/`: Documentación del proyecto y reglas de desarrollo.
- `tests/`: Tests unitarios y de integración.
- `scripts/`: Scripts automatizados para instalación, ejecución y validación.
- `data/`: Datos crudos, procesados y caché.
- `logs/`: Archivos de log.
- `migrations/`: Migraciones Alembic.
- `requirements.txt`: Dependencias de runtime.
- `requirements-dev.txt`: Dependencias de desarrollo y testing.
