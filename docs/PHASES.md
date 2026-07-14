# Fases de Desarrollo

| Fase | Descripcion | Estado |
|------|-------------|--------|
| **Fase 0** | Bootstrap del proyecto | Completada |
| **Fase 1** | Infraestructura de datos (SQLite, SQLAlchemy, Alembic) | Completada |
| **Fase 2** | Cliente Meta Ads API (eliminado, no usado en produccion) | Completada |
| **Fase 3** | Adquisicion robusta por navegador (Playwright) | Completada |
| **Fase 3.2** | Mejoras de adquisicion (checkpoint, proxies, split, retry) | Completada |
| **Fase 4** | Enriquecimiento profundo de empresas | Pendiente (5 etapas) |
| **Fase 4.1** | DTOs y modelo de datos (renombrar enrichment, nuevos DTOs) | Pendiente |
| **Fase 4.2** | Social Enrichment (FB/IG: bio, telefono, email, links) | Pendiente |
| **Fase 4.3** | Landing Enrichment (phones, emails, social, forms, categoria) | Pendiente |
| **Fase 4.4** | Domain Enrichment (crawling multi-pagina) | Pendiente |
| **Fase 4.5** | Orquestacion, CLI y serializacion | Pendiente |

## Nota sobre Fase 4

La Fase 4 esta dividida en 5 etapas secuenciales. Cada etapa tiene sus propios criterios de aceptacion y puede ser implementada y mergeada de forma independiente, siempre que no rompa la compatibilidad con las etapas anteriores.

Ver `docs/phases/PHASE_04_ENRICHMENT_PLAN.md` para el detalle completo.

## Criterio para Cerrar una Fase

Una fase se considera cerrada solo si:
- Tiene tests asociados.
- `./scripts/check.sh` pasa.
- La documentacion queda actualizada.
- Las decisiones tecnicas relevantes quedan en `docs/DECISIONS.md`.

## Archivos por Fase

- `docs/phases/PHASE_00_02_STABILIZED.md`: Fases 0-2 estabilizadas.
- `docs/phases/PHASE_03_BROWSER_ACQUISITION_PLAN.md`: Fase 3 completada.
- `docs/phases/PHASE_04_ENRICHMENT_PLAN.md`: Fase 4 (en progreso).

- `docs/phases/TEMPLATE.md`: Plantilla para nuevas fases.
