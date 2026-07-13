# Fases de Desarrollo

| Fase | Descripcion | Estado |
|------|-------------|--------|
| **Fase 0** | Bootstrap del proyecto | Completada |
| **Fase 1** | Infraestructura de datos (SQLite, SQLAlchemy, Alembic) | Completada |
| **Fase 2** | Cliente Meta Ads API (eliminado, no usado en produccion) | Completada |
| **Fase 3** | Adquisicion robusta por navegador (Playwright) | Completada |
| **Fase 3.2** | Mejoras de adquisicion (checkpoint, proxies, split, retry) | Completada |
| **Fase 4** | Por definir (no iniciada) | Pendiente |

## Criterio para Cerrar una Fase

Una fase se considera cerrada solo si:
- Tiene tests asociados.
- `./scripts/check.sh` pasa.
- La documentacion queda actualizada.
- Las decisiones tecnicas relevantes quedan en `docs/DECISIONS.md`.

## Archivos por Fase

- `docs/phases/PHASE_00_02_STABILIZED.md`: Fases 0-2 estabilizadas.
- `docs/phases/PHASE_03_BROWSER_ACQUISITION_PLAN.md`: Fase 3 completada.

- `docs/phases/TEMPLATE.md`: Plantilla para nuevas fases.
