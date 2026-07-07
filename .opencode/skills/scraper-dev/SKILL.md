---
name: scraper-dev
description: "Use when working on browser acquisition, Playwright scraping, anti-detection, or enrichment logic. Triggered by keywords: scraper, scraping, playwright, browser, anti-deteccion, anti-bloqueo, discovery, enrichment, ads_extractor, browser_runner, ads_searcher, browser_manager, session_manager, native_click, jitter, viewport, user-agent, webdriver, checkpoint, signal handler, proxy, enrichment, followers, landing URL, CTA, ad_library_url, library_id, dialog, advertiser. Use ONLY for the Meta Ads Library scraper in src/modules/meta_ads/acquisition/ and browser/."
---

# Scraper Development Guide — Meta Ads Library Acquisition

## Pipeline

```
BrowserManager -> SessionManager -> AdsSearcher -> AdsExtractor -> DTOs -> JSON
                      |
               Anti-deteccion
               (UA, args, headers, override scripts, viewport jitter)
```

## Anti-deteccion

- **BrowserManager**: 9 flags Chromium (`--disable-blink-features=AutomationControlled`, `--no-sandbox`, etc.), User-Agent Chrome 125 Windows
- **SessionManager**: viewport 1920x1080 +/-20px, `navigator.webdriver` -> undefined, `navigator.plugins` -> array 5 plugins, `navigator.languages` -> es-ES/es/en, `chrome.runtime` -> objeto vacio, headers Accept-Language realistas
- **Delays**: todos los `wait_for_timeout` con jitter +/-30% via `_jittered_delay()`

## Discovery (extract_discovery_ads)

1. Navegar a Meta Ads Library URL con filtros
2. Esperar 7s post-busqueda
3. Expandir resumenes ("Ver detalles del resumen"/"Ver resumen") via native_click
4. Extraer candidate cards
5. Por cada card: extraer library_id, landing URL (desde boton CTA, filtro engagement), description (con BREAK en URLs/display/ofertas), advertiser_name (backward search), ad_library_url construida
6. Scroll y repetir hasta limite o 3 scrolls vacios
7. Checkpoint por keyword

### Filtros de busqueda
- `active_status=active`, `ad_type=all`, `country=ALL`
- `content_languages[0]=es`, `search_type=keyword_unordered`
- `sort_data[mode]=total_impressions` (default)
- `publisher_platforms[0]=facebook`, `publisher_platforms[1]=instagram`

### Filtros de landing URL
- **Engagement CTA**: si existe href wa.me/whatsapp.com/m.me/tel: en cualquier anchor -> descartar
- **Blocked domains**: facebook.com, instagram.com, youtube.com, twitter.com, x.com, tiktok.com, linkedin.com, whatsapp.com, wa.me, m.me, ig.me, bit.ly, tinyurl.com, goo.gl, ow.ly
- **Display URL**: mayusculas + punto -> BREAK en descripcion
- **Ofertas**: `\d+% (OFF|desc)` -> BREAK en descripcion
- **UI Noise**: ~30 lineas de texto de botones filtradas

## Enrichment (enrich_ads)

1. Por cada ad navegar a ad_library_url
2. Buscar dialogo "Detalles del anuncio" (excluir "Vincular con un anuncio")
3. Si aparece dialogo resumen -> click "Ver detalles del anuncio" interno
4. Expandir "Informacion sobre el anunciante" via native_click (JS evaluate)
5. Extraer: Facebook username (@username o Identificador: N), Instagram username (@username), followers count (mil/mill con coma decimal)

### Errores corregidos (historico)
- `ig.me` agregado a BLOCKED_DOMAINS
- advertiser_name con backward search (evita "Transparencia de la UE")
- Followers con "mill" soportado (x1,000,000)
- Decimal comma + "mil" con float math
- ~30 lineas en UI_NOISE_LINES
- Display URLs cortadas con BREAK
- URLs mayuscula/emoji detectadas
- WhatsApp CTAs descartados en TODOS los anchors
- Landing URL desde boton CTA, no desde texto
- Dialog priority: contenido sobre posicion DOM
- native_click() via JS evaluate para React

## CLI Reference

```bash
python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" \
  --keyword "marketing:100" \
  --headless \
  --no-enrich \
  --output resultados.json \
  --mode append \
  --max-scrolls 0 \
  --sort-mode total_impressions \
  --proxy http://user:pass@host:port \
  --session-per-keywords 3 \
  --global-timeout 30
```

## Estructura de Archivos Clave

- `src/modules/meta_ads/browser/browser_manager.py`
- `src/modules/meta_ads/browser/session_manager.py`
- `src/modules/meta_ads/acquisition/ads_searcher.py`
- `src/modules/meta_ads/acquisition/ads_extractor.py` (~1488 lines)
- `src/modules/meta_ads/acquisition/browser_runner.py` (~1050 lines)
- `src/modules/meta_ads/dto/browser_ad.py`
- `scripts/run_meta_ads_browser.py`
