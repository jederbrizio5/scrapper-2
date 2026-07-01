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

### Características implementadas en Fase 3

- **Anti-detección**: 9 flags Chromium, User-Agent Chrome 125 realista,
  `navigator.webdriver` override, viewport jitter, headers HTTP realistas,
  jitter ±30% en delays.
- **Landing URL desde botón CTA**: Prioriza `<a>` dentro de botones; solo
  cae a texto si no hay botones.
- **Engagement CTA detection**: Si cualquier `<a>` en la card apunta a
  WhatsApp/Messenger/tel, el anuncio se descarta automáticamente.
- **Descripción limpia**: Filtra ruido de UI (~30 líneas de noise), URLs
  (con o sin emoji), display URLs (`CEFOMIN.CL`), ofertas porcentuales;
  corta recolección (BREAK) al detectar footer.
- **Advertiser name**: Búsqueda backward desde library_id primero (evita
  falsos como "Transparencia de la UE"), fallback forward.
- **Enrichment**: Abre el diálogo de detalles, expande sección del
  anunciante, extrae usuarios FB/IG y seguidores con parseo de formato
  español (coma decimal, "mil"/"mill", punto separador).
- **Scroll**: Extrae más cards mediante scroll, filtra por dominio único
  (solo 1 resultado por dominio por ejecución).
- **Timing**: Log por keyword y total con `time.perf_counter()`.
- **12+ correcciones**: `ig.me` bloqueado, followers con "mill",
  decimal comma + "mil" con float math, descripción sin botones/nav,
  sin display URLs, sin URLs con emoji, sin WhatsApp CTAs falsas.

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
