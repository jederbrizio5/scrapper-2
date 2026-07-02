# Fase 3.2: Configuracion Total, Persistencia Robusta y Enrichment-Only

## Estado

Completada

## Objetivo

Agregar configuracion granular por CLI, persistencia incremental con checkpoint y signal handler, modo enrichment-only, dedup cross-keyword, y limites por keyword.

## Alcance

- Per-keyword limits con sintaxis `--keyword "nombre:limite"`
- `max_scrolls=0` como scrolls infinitos (corte solo por objetivo o 3 vacios)
- `--mode append` para retomar archivo existente
- `--resume` para dedup cross-ejecucion
- `--enrich-only` para enriquecer discoveries existentes
- `--blocked-domains` para dominios extra bloqueados por CLI
- `--sort-mode` configurable (`total_impressions`, `relevancy_monthly_grouped`)
- `--force` para sobreescritura automatica sin preguntar
- Checkpoint por keyword (guarda JSON completo tras cada keyword)
- Signal handler (SIGINT/SIGTERM guarda checkpoint antes de salir)
- `extracted_at` ISO timestamp en cada discovery y enrichment
- Sesion nueva por keyword (prevencion OOM)
- Skip library_ids en extractor (evita reprocesar cards entre scrolls)
- Log de configuracion al inicio del bot
- Log de resumen final con tiempo formateado y estadisticas detalladas

## Fuera De Alcance

- Envio a base de datos (seguir usando JSON como persistencia principal)
- Interfaz grafica o web
- Cache de enrichment entre ejecuciones

## Archivos Creados O Modificados

- `src/modules/meta_ads/dto/browser_ad.py`: +`extracted_at` en BrowserAdDiscovery y BrowserAdEnrichment
- `src/modules/meta_ads/acquisition/ads_extractor.py`: +`extra_blocked_domains` param, `_blocked_domains` dinámico, `extracted_at` inyectado en cada DTO
- `src/modules/meta_ads/acquisition/browser_runner.py`: refactor mayor (~571 lineas) — checkpoint, signal, max_scrolls=0, limits por keyword, resume, append, enrich-only, confirm overwrite, startup log, final summary
- `scripts/run_meta_ads_browser.py`: CLI completo con todos los flags documentados
- `tests/unit/meta_ads/test_browser_acquisition.py`: 18 tests nuevos (24 total en el archivo)
- `docs/DECISIONS.md`: nuevas decisiones registradas
- `docs/PHASES.md`: Fase 3.2 agregada
- `docs/doc.phase.3.md`: seccion Fase 3.2 agregada
- `README.md`: documentacion de uso completa

## Como Se Ejecuta

```bash
# Uso basico
python scripts/run_meta_ads_browser.py \
  --keyword "curso" --keyword "curso marketing:50" \
  --headless --no-enrich --output resultados.json

# Retomar ejecucion anterior
python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --mode append \
  --output resultados.json --headless --no-enrich

# Bloquear dominios de campana previa
python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --resume campana_anterior.json \
  --output nueva_campana.json --headless --no-enrich

# Solo enriquecer discoveries existentes
python scripts/run_meta_ads_browser.py \
  --enrich-only discoveries.json --output enriquecidos.json --headless

# Dejar andando de noche (scrolls infinitos)
nohup python scripts/run_meta_ads_browser.py \
  --keyword "curso:100" --keyword "marketing:100" \
  --keyword "programacion:100" --keyword "ingles:100" \
  --max-scrolls 0 --headless --no-enrich \
  --output output/night_run.json > output/night_run.log 2>&1 &
```

## Como Se Prueba

```bash
source venv/bin/activate && python -m pytest tests/unit/meta_ads/ -v
```

## Logs Esperados

```
2026-07-02 12:00:00 INFO ======================================================
2026-07-02 12:00:00 INFO   INICIO DE ADQUISICION — META ADS LIBRARY
2026-07-02 12:00:00 INFO ======================================================
2026-07-02 12:00:00 INFO   Keywords            : "curso:30", "curso marketing"
2026-07-02 12:00:00 INFO   Modo                : append
2026-07-02 12:00:00 INFO   Archivo salida      : output/resultados.json
2026-07-02 12:00:00 INFO   Limite global       : 30
2026-07-02 12:00:00 INFO   Scrolls maximos     : 50 (0=infinito)
2026-07-02 12:00:00 INFO   Plataformas         : facebook, instagram
2026-07-02 12:00:00 INFO   Ordenamiento        : total_impressions
```

## Criterios De Aceptacion

- `./scripts/check.sh` pasa.
- 29 tests pasan (24 en browser_acquisition + 5 en otros modulos).
- Documentacion actualizada.
- No se agregan secretos.

## Resultado Final

Fase 3.2 implementada completamente. Todos los cambios del plan ejecutados:

1. DTO con `extracted_at` en discovery y enrichment
2. `AdsExtractor` acepta `extra_blocked_domains`, construye `_blocked_domains` dinamicamente, inyecta `extracted_at` en cada DTO
3. `MetaAdsBrowserRunner` refactorizado con checkpoint, signal handler, max_scrolls=0, per-keyword limits, resume, append, enrich-only, confirm overwrite, startup log, final summary
4. CLI completo con todos los flags documentados
5. 24 tests unitarios (18 nuevos para Fase 3.2 + 11 existentes de Fase 3)
6. Documentacion actualizada: README.md, DECISIONS.md, PHASES.md, doc.phase.3.md, phase file dedicado
7. ruff check + ruff format + pytest: todo OK (29/29 tests pasando)
