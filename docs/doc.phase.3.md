# Fase 3: Algoritmo de Adquisición por Navegador

## Problema reportado

El bot solo obtiene entre 5 y 10 anuncios válidos por keyword cuando se le piden 25.
De ~140 cards detectadas, solo ~5 tienen landing externa (`landing_url`). El resto son anuncios internos de Facebook/Instagram sin landing útil.

Este documento describe exactamente cómo funciona el algoritmo para que otra IA pueda diagnosticar la causa raíz.

---

## 1. Arquitectura General

```
scripts/run_meta_ads_browser.py  (entry point, CLI argparse)
  -> MetaAdsBrowserRunner         (orquestación: navegador -> keyword loop -> scroll -> enrich)
    -> BrowserManager             (inicia/cierra Chromium)
    -> SessionManager             (crea contexto + página, sin login)
    -> AdsSearcher                (navega a URL de búsqueda)
    -> AdsExtractor               (extrae discovery + enrichment)
    -> DTOs                       (BrowserAdDiscovery, BrowserAdEnrichment, BrowserAdResult)
```

No hay base de datos ni persistencia. Salida: `output/meta_ads_browser_results.json`.

---

## 2. Flujo Paso a Paso

### 2.1 Inicio del Navegador (`BrowserManager.start`)

- Modo `headless` o `debug` (visible, slow_mo >= 200ms)
- Argumento Chromium: `--disable-blink-features=AutomationControlled`
- En debug: `--start-maximized`
- **No hay** otras medidas anti-detección (no se setea User-Agent, ni viewport aleatorio, ni se evita `navigator.webdriver`)

### 2.2 Búsqueda por Keyword (`AdsSearcher.search`)

- Construye URL: `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&content_languages[0]=es&country=ALL&is_targeted_country=false&media_type=all&q={keyword}&search_type=keyword_unordered&sort_data[direction]=desc&sort_data[mode]=relevancy_monthly_grouped`
- Navega con `page.goto(url, wait_until="networkidle")`
- Espera 7000ms (`wait_after_search_ms`) por defecto

### 2.3 Discovery con Scroll (`_collect_discoveries_with_scroll`)

```
por cada keyword:
  while (unicos < limit AND scroll_attempts < max_scroll_attempts):
    raw = extractor.extract_discovery_ads(keyword, limit + 20)
    para cada raw:
      si library_id ya visto -> skip (duplicado interno)
      si domain ya visto -> skip (dominio duplicado, log "Saltando dominio duplicado")
      si pasa ambos: agregar a all_discoveries

    si ya tenemos suficientes -> break

    scroll al fondo: page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    esperar 7000ms
    scroll_attempts += 1

    new_raw = extractor.extract_discovery_ads(keyword, limit=5)
    si no hay nuevos -> break (sin nuevos anuncios tras scroll)
```

Solo se consideran **dominios únicos**. Si dos anuncios distintos pertenecen al mismo dominio, solo el primero cuenta.

### 2.4 Extracción de Discovery por Card (`extract_discovery_ads`)

```
1. _candidate_cards():
   - Buscar div[role="article"] o div[data-testid="library-ad-card"]
   - Fallback: todos los "div"
   - Filtrar: debe contener "Identificador de la biblioteca" o "Library ID"
   - Filtrar: al menos 3 líneas de texto
   - Filtrar: texto <= 5000 caracteres (evita contenedores padre)

2. Por cada card válida:
   a. Extraer library_id (regex: "Identificador de la biblioteca: (\d+)")
   b. Extraer landing_url:
      - Buscar todos los <a href> dentro del card
      - Normalizar URL (quitar fragmentos, resolver l.facebook.com)
      - Verificar que NO sea un dominio bloqueado (BLOCKED_DOMAINS)
      - Si no hay landing externa -> DESCARTAR
   c. Extraer advertiser_name (primera línea significativa no-ruido)
   d. Extraer description (texto después de library_id, filtrando ruido UI)
   e. Extraer circulation_start (regex: "En circulación desde...")
   f. Construir ad_library_url = "https://www.facebook.com/ads/library/?id={library_id}"
```

### 2.5 Filtro de Landing URL (`_extract_landing_url`)

- Toma todos los `<a href>` dentro del card
- Intenta cada href
- Para cada uno:
  - Normaliza (resuelve `l.facebook.com/u=...`)
  - Verifica `_is_external_landing`: el dominio NO debe estar en `BLOCKED_DOMAINS`
  - `BLOCKED_DOMAINS` incluye: facebook.com, fb.com, fb.me, instagram.com, messenger.com, m.me, wa.me, wa.link, whatsapp.com, metastatus.com, about.fb.com, transparency.fb.com, privacymanager.io, forms.gle, forms.google.com, docs.google.com, drive.google.com, youtube.com, youtu.be, tiktok.com, twitter.com, x.com, linkedin.com, t.me, telegram.org, bit.ly, tinyurl.com, goo.gl

### 2.6 Enriquecimiento (`enrich_ads`)

```
por cada discovery:
  card = _find_card_by_library_id(cards, discovery.library_id)
  si no card -> enrichment = None (no se puede abrir detalle)

  button = _find_detail_button(card)
  si no button -> enrichment vacío

  button.click(timeout=5000, force=True)

  si button.text contiene "resumen":
    _enter_from_summary() -> busca dialog con "Ver detalles del anuncio", clickea botón interno
  si no:
    _find_detail_dialog() -> busca div[role=dialog] con "Detalles del anuncio"

  _click_advertiser_heading(dialog) -> busca [role=heading] con "anunciante"
  esperar 1500ms

  full_text = dialog.inner_text()
  parsear fb_user, ig_user desde texto
  parsear fb_followers, ig_followers desde texto
  cerrar dialog
```

---

## 3. Puntos Críticos Que Limitan la Recolección

### 3.1 La mayoría de anuncios en Meta Ads Library NO tienen landing externa

**Causa raíz más probable.** Meta Ads Library muestra:
- Anuncios que linkean a perfiles/pages de Facebook
- Anuncios que linkean a Instagram
- Anuncios que linkean a WhatsApp
- Anuncios que linkean a Messenger
- Anuncios que linkean a URLs acortadas (bit.ly, etc.)
- Anuncios que linkean a Google Forms/Docs

Todo lo anterior es filtrado por `BLOCKED_DOMAINS`. De ~140 cards, solo ~5-10 tienen un dominio externo válido (ej: `weya.academy`, `creatikaonline.com`).

**Posible solución:** Ampliar la búsqueda a keywords más comerciales o reducir `BLOCKED_DOMAINS`.

### 3.2 El scroll no siempre carga nuevos anuncios únicos

- Después del primer scroll, normalmente se cargan los mismos anuncios (duplicados por library_id y domain)
- El límite `max_scroll_attempts = 10` raramente se alcanza porque el detector de "sin nuevos" se activa antes
- Hay 7000ms de espera entre scrolls, pero muchas veces no hay nuevos cards

**Posible solución:** Usar `sort_data[mode]=relevancy_monthly_grouped` ya ordena por relevancia, y los anuncios con landing externa tienden a estar mezclados; scrolls adicionales no ayudan si no hay más anuncios con landing.

### 3.3 La detección de cards es frágil

- `div[role="article"]` y `div[data-testid="library-ad-card"]` son selectores que Meta puede cambiar
- El fallback a todos los `div` con filtro de texto es lento y puede traer falsos positivos
- El límite de 5000 caracteres puede descartar cards válidas si el DOM es profundo

### 3.4 Sin medidas anti-bot

- Solo se usa `--disable-blink-features=AutomationControlled`
- No se setea un User-Agent realista
- No se randomizan tiempos de espera
- `navigator.webdriver` puede estar detectable
- Meta podría estar limitando los resultados visibles (no bloqueando, sino mostrando menos)

### 3.5 Filtrado agresivo de dominios

`BLOCKED_DOMAINS` incluye dominios que algunos anuncios legítimos usan como landing:
- `forms.gle`, `docs.google.com` -> algunos usan Google Forms para leads
- `bit.ly`, `tinyurl.com`, `goo.gl` -> muchos usan acortadores
- `youtube.com`, `youtu.be` -> algunos anuncios linkean a videos

Cada uno de estos reduce el pool de anuncios válidos.

---

## 4. Datos Observados en Ejecución Real

Keyword "curso":
- Cards detectadas: 143
- Válidas (con landing externa): 5-6
- Dominios únicos obtenidos: ~5
- Filtradas por landing: ~137 (Facebook/IG/WA/blocked)

Keyword "masterclass":
- Cards detectadas: 145  
- Válidas (con landing externa): 5-7
- Dominios únicos obtenidos: ~5
- Filtradas por landing: ~138

**Ratio de conversión: ~3-4%** de cards a anuncios válidos.

---

## 5. Recomendaciones para Diagnosticar

1. **Agregar logging temporal** para contar cuántos anuncios se descartan por cada razón:
   - "Sin landing externa"
   - "Dominio bloqueado"
   - "Duplicado por library_id"
   - "Duplicado por domain"

2. **Inspeccionar manualmente** la página de Meta Ads Library para una keyword:
   - ¿Cuántos anuncios visibles tienen enlaces externos reales?
   - ¿Qué tipos de landing predominan?
   - ¿Meta está ocultando resultados por comportamiento automatizado?

3. **Probar con keywords más comerciales** que tienden a tener más landing externas:
   Ej: "comprar", "descuento", "oferta", "envío gratis", "suscríbete"

4. **Verificar el DOM real**: Ejecutar en modo debug y examinar los elementos que `_candidate_cards` encuentra versus los que tienen landing visible.

---

## 6. Estructura del Código

| Archivo | Rol |
|---------|-----|
| `scripts/run_meta_ads_browser.py` | Entry point, CLI args, serialización JSON |
| `src/modules/meta_ads/acquisition/browser_runner.py` | Orquestación: navegador → loop de keywords → scroll → enrich |
| `src/modules/meta_ads/acquisition/ads_searcher.py` | Construye URL de búsqueda, navega |
| `src/modules/meta_ads/acquisition/ads_extractor.py` | Lógica de extracción: cards, landing, enrichment |
| `src/modules/meta_ads/browser/browser_manager.py` | Chromium headless/debug |
| `src/modules/meta_ads/browser/session_manager.py` | Contexto y página (sin login) |
| `src/modules/meta_ads/dto/browser_ad.py` | DTOs: BrowserAdDiscovery, BrowserAdEnrichment, BrowserAdResult |

---

## 7. Configuración por Defecto (CLI)

| Parámetro | Default | Efecto |
|-----------|---------|--------|
| `--keyword` | (obligatorio) | Keywords a buscar |
| `--limit` | 3 | Máx. anuncios únicos por keyword |
| `--headless` | False | Modo sin interfaz |
| `--no-enrich` | False | Skipea enrichment |
| `--wait-ms` | 7000 | Espera tras búsqueda/scroll |
| `--action-delay-ms` | 1200 | Pausa entre clics |
| `--debug` | False | Navegador visible + logs DEBUG |
| `--slow-mo` | 0 | Slow motion de Playwright |
| `--output` | `output/meta_ads_browser_results.json` | Destino del JSON |

---

## 8. Pruebas

20 tests unitarios en `tests/unit/meta_ads/test_browser_acquisition.py`.
Ejecutar: `./scripts/check.sh` (lint + format + tests).

---

## 9. Hipótesis Sobre Por Qué Solo Se Obtienen 5-10 Anuncios

1. **Meta Ads Library no indexa muchos anuncios con landing externa.** La mayoría de anuncios en Meta son para engagement dentro de la plataforma (mensajes, leads, eventos) o linkean a perfiles de IG/FB.

2. **El filtro `BLOCKED_DOMAINS` es demasiado restrictivo.** Muchas landing reales usan Google Forms, YouTube o acortadores.

3. **Meta podría estar limitando resultados a navegadores automatizados.** Aunque no bloquea, podría servir menos anuncios comerciales.

4. **Las keywords usadas ("curso", "masterclass") pueden tener baja densidad de anuncios con landing externa.** Keywords más transaccionales pueden rendir mejor.

5. **El orden `relevancy_monthly_grouped` no prioriza anuncios con landing.** Cambiar a `sort_data[mode]=created_time_desc` podría mostrar más variedad.
