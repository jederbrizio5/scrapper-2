# Fases De Desarrollo

* **Fase 0: Bootstrap** - Completada.
* **Fase 1: Base de datos** - Completada.
* **Fase 2: Cliente Meta Ads y PoC navegador** - Completada.
* **Fase 3: Adquisicion robusta por navegador** - Pendiente.
* **Fase 4: Extraccion de dominios y scraper landing** - Pendiente.
* **Fase 5: Scoring** - Pendiente.
* **Fase 6: CRM** - Pendiente.
* **Fase 7: Automatización** - Pendiente.

## Criterio Para Cerrar Una Fase

Una fase se considera cerrada solo si:

* Tiene tests asociados.
* `./scripts/check.sh` pasa.
* La documentacion queda actualizada.
* Las decisiones tecnicas relevantes quedan en `docs/DECISIONS.md`.

## Archivos Por Fase

Los detalles de cada fase viven en `docs/phases/`.

* `docs/phases/PHASE_00_02_STABILIZED.md`: estado actual estabilizado.
* `docs/phases/PHASE_03_BROWSER_ACQUISITION_PLAN.md`: plan recomendado para la siguiente fase.
* `docs/phases/TEMPLATE.md`: plantilla obligatoria para nuevas fases.
