# Meta Ads Prospecting System

Sistema modular de prospeccion de anuncios via **Meta Ads Library** con adquisicion por navegador (Playwright), enrichment de anunciantes y persistencia estructurada.

---

## Instalacion

```bash
./scripts/install.sh
source venv/bin/activate && playwright install chromium
```

---

## Uso Rapido

```bash
# Scrapeo basico (default: output con timestamp + split por keyword)
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --keyword "marketing:30" --headless --no-enrich
```

Esto crea `output/DD-MM-YYYY_HHMMSS/resultados_parts/{keyword}.json` + `index.json`.

### Scrapeo clasico (un solo JSON, sin carpeta fecha)

```bash
python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --keyword "marketing:30" \
  --headless --no-enrich --no-split --output resultados.json
```

### Enriquecer resultados existentes (in-place)

```bash
# In-place: modifica los archivos originales (parts o JSON unico)
python scripts/run_meta_ads_browser.py \
  --enrich-only output/02-07-2026_192519/resultados.json --headless

# A nuevo archivo
python scripts/run_meta_ads_browser.py \
  --enrich-only resultados.json --output enriquecidos.json --headless
```

### Retomar ejecucion (append)

```bash
python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --mode append --headless --no-enrich
```

### Dejar andando de noche

```bash
nohup python scripts/run_meta_ads_browser.py \
  --keyword "curso:100" --keyword "marketing:100" \
  --keyword "programacion:100" --keyword "ingles:100" \
  --headless --no-enrich > output/night_run.log 2>&1 &
```

---

## Argumentos CLI

### Scrapeo

| Argumento | Default | Descripcion |
|-----------|---------|-------------|
| `--keyword` | (requerido) | `"nombre"` o `"nombre:limite"`. Repetible. |
| `--limit` | `30` | Limite global por keyword si no se especifica en `--keyword` |
| `--headless` | `False` | Modo sin ventana |
| `--no-enrich` | `False` | Solo discovery, sin enrichment |
| `--output` | `output/DD-MM-YYYY_HHMMSS/resultados.json` | Ruta de salida. Sin `--no-split`, los datos van a `_parts/` |
| `--no-split` | `False` | No dividir por keyword (un solo JSON plano) |
| `--mode` | `overwrite` | `append` para retomar desde ejecucion anterior |
| `--resume` | — | JSON o `_parts/` con dominios a dedup (cross-ejecucion) |

### Scroll

| Argumento | Default | Descripcion |
|-----------|---------|-------------|
| `--max-scrolls` | `0` | 0 = scrolls infinitos (corta solo por objetivo o 3 vacios) |
| `--empty-scrolls` | `3` | Cortar tras N scrolls consecutivos sin nuevos dominios |
| `--sort-mode` | `total_impressions` | Criterio de ordenamiento en Meta Ads Library. Alternativa: `relevancy_monthly_grouped` |

### Anti-bloqueo / Sesion

| Argumento | Default | Descripcion |
|-----------|---------|-------------|
| `--session-per-keywords` | `3` | Reutilizar sesion cada N keywords. 0 = sesion nueva por keyword |
| `--proxy` | — | Proxy unico: `http://user:pass@host:port` |
| `--proxy-list` | — | Archivo de proxies (uno por linea, `#` para comentarios). Round-robin entre ellos |
| `--max-retries` | `3` | Intentos por keyword fallida (incluye el primero). 0 = sin reintento |
| `--retry-delay` | `15` | Espera en segundos entre reintentos |
| `--global-timeout` | `0` (sin limite) | Timeout global en minutos. Al alcanzarlo guarda checkpoint y sale |
| `--blocked-domains` | — | Dominios extra a bloquear (separados por coma) |

### Enrichment

| Argumento | Default | Descripcion |
|-----------|---------|-------------|
| `--enrich-only` | — | Ruta a discoveries para enriquecer (archivo JSON, carpeta, o `_parts/`). Sin `--output` modifica in-place |
| `--wait-ms` | `7000` | Espera post-busqueda antes de extraer cards |
| `--action-delay-ms` | `1200` | Delay entre acciones (scrolls, clics) |

### Misc

| Argumento | Default | Descripcion |
|-----------|---------|-------------|
| `--force` | `False` | Sobreescribir sin preguntar |
| `--debug` | `False` | Logs detallados (DEBUG level) |
| `--slow-mo` | `0` | Slow motion de Playwright en ms |
| `--action-timeout` | `30000` | Timeout de Playwright por accion en ms |

---

## Comportamiento Detallado

### Output por defecto

Sin `--output`, se genera automaticamente:

```
output/02-07-2026_192519/
├── resultados_parts/
│   ├── curso.json
│   ├── marketing.json
│   └── index.json
```

Con `--no-split` o `--output` explicito, se escribe un solo JSON plano.

### Enrich in-place

- Sin `--output`: modifica los archivos originales (actualiza cada part file o sobreescribe el JSON unico).
- Con `--output`: escribe a un archivo nuevo, dejando los originales intactos.

### Append

`--mode append` detecta automaticamente `_parts/` hermano al path de salida y carga los resultados previos desde ahi, deduplicando por `library_id` y `domain`.

### Proxies

- `--proxy`: un proxy fijo para todas las sesiones.
- `--proxy-list`: archivo de proxies. Se rotan en round-robin entre keywords.
- Sin proxy: conexion directa.

### Sesion compartida

Con `--session-per-keywords 3`:
- Keywords 1-3 comparten la misma sesion de Playwright.
- Keyword 4 abre una nueva sesion.
- Reduce overhead de creacion de contextos.

### Reintentos

Cuando una keyword falla por timeout/error de red:
1. Se registra el error.
2. Espera `--retry-delay` segundos.
3. Abre nueva sesion (y nuevo proxy si hay) y reintenta.
4. Si persiste tras `--max-retries` intentos, marca la keyword como fallida y continua con la siguiente.

---

## Testing

```bash
./scripts/test.sh
# o directamente:
source venv/bin/activate && python -m pytest tests/ -v
```

## Linting y Formato

```bash
./scripts/lint.sh      # revisar
./scripts/format.sh    # formatear
./scripts/check.sh     # tests + lint + formato (obligatorio antes de cerrar tareas)
```

---

## Caracteristicas Implementadas

### Adquisicion por navegador (Fase 3)
- **Anti-deteccion**: 9 flags Chromium, User-Agent Chrome, `navigator.webdriver` override, viewport jitter, headers realistas.
- **Landing URL desde boton CTA**: Prioriza `<a>` dentro de botones.
- **Engagement CTA detection**: Descarta WhatsApp/Messenger/tel.
- **Descripcion limpia**: Filtra ~30 lineas de ruido UI.
- **Advertiser name**: Busqueda backward desde library ID.
- **Enrichment**: Dialogo de detalles, seccion del anunciante, usuarios FB/IG, seguidores.
- **Scroll incremental**: Extraccion con tolerancia a scrolls vacios.

### Persistencia y configuracion (Fase 3.2)
- **Per-keyword limits**: Control granular via `"nombre:limite"`.
- **Scrolls infinitos**: `--max-scrolls 0` corta solo por objetivo o agotamiento.
- **Modo append**: Retoma ejecucion sin duplicar.
- **Resume cross-ejecucion**: Dedup desde JSON de campana anterior.
- **Checkpoint por keyword**: Guarda tras cada keyword + cada scroll.
- **Signal handler**: SIGINT/SIGTERM guardan checkpoint antes de salir.
- **Split por keyword**: Archivos separados + index.json de metadatos.
- **Enrich in-place**: Modifica archivos originales, sin duplicar.
- **Reintentos**: Reintento automatico con backoff y nueva sesion.
- **Proxies**: Unico o lista rotativa round-robin.
- **Sesion compartida**: Reutiliza contexto Playwright cada N keywords.
- **Timeout global**: Limite de minutos para toda la ejecucion.
- **Formato hora Argentina**: `dd/mm/YYYY HH:MM:SS hs` en logs y datos.
- **Output con timestamp**: Carpeta `DD-MM-YYYY_HHMMSS` auto-generada.

---

## Estructura del Proyecto

- `src/`: Codigo fuente principal.
- `docs/`: Documentacion del proyecto y reglas de desarrollo.
- `tests/`: Tests unitarios y de integracion.
- `scripts/`: Instalacion, ejecucion y validacion.
- `data/`: Datos crudos, procesados y cache.
- `logs/`: Archivos de log.
- `migrations/`: Migraciones Alembic.
- `requirements.txt` / `requirements-dev.txt`: Dependencias.

## Documentacion para Agentes

Antes de implementar una fase, leer:

- `docs/MAESTRO.MD`
- `docs/AGENT_WORKFLOW.md`
- `docs/GIT_WORKFLOW.md`
- `docs/PROJECT.md`
- `docs/ARCHITECTURE.md`
- `docs/PHASES.md`

Cada tarea en rama propia, validar con `./scripts/check.sh`, cerrar mediante Pull Request.
