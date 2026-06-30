# Fases De Desarrollo

* **Fase 0: Bootstrap** - Completada.
* **Fase 1: Base de datos** - Completada.
* **Fase 2: Cliente Meta Ads y PoC navegador** - Completada.
* **Fase 3: Adquisicion robusta por navegador** - Completada.

Las fases posteriores no quedan definidas en este documento. Se documentaran cuando producto lo indique.

## Criterio Para Cerrar Una Fase

Una fase se considera cerrada solo si:

* Tiene tests asociados.
* `./scripts/check.sh` pasa.
* La documentacion queda actualizada.
* Las decisiones tecnicas relevantes quedan en `docs/DECISIONS.md`.

## Archivos Por Fase

Los detalles de cada fase viven en `docs/phases/`.

* `docs/phases/PHASE_00_02_STABILIZED.md`: estado actual estabilizado (Fases 0-2).
* `docs/phases/PHASE_03_BROWSER_ACQUISITION_PLAN.md`: Fase 3 completada — adquisicion por navegador con discovery y enrichment.
* `docs/phases/TEMPLATE.md`: plantilla obligatoria para nuevas fases.
