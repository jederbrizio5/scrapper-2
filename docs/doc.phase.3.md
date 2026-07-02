# Fase 3 — Algoritmo de Adquisición por Navegador (Meta Ads Library)

## 1. Visión General

La Fase 3 implementa un sistema de adquisición de anuncios desde Meta Ads
Library usando Playwright (Chromium). Reemplaza la Fase 2 (API oficial) porque
la API de Meta no expone landing URLs ni datos de redes sociales del anunciante.

Pipeline completo:

```
BrowserManager -> SessionManager -> AdsSearcher -> AdsExtractor -> DTOs -> JSON
                     |
              Anti-deteccion
              (UA, args, headers,
               override scripts,
               viewport jitter)
```

---

## 2. Arquitectura

### 2.1 BrowserManager (`browser_manager.py`)

Inicializa Chromium con:
- **ANTI_DETECTION_ARGS**: 9 flags anti-bot
  (`--disable-blink-features=AutomationControlled`,
  `--no-sandbox`, `--disable-infobars`, etc.)
- **REALISTIC_USER_AGENT**: `Mozilla/5.0 (Windows NT 10.0; Win64; x64)
  AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36`
- Modo debug: navegador visible + `--start-maximized` + slow_mo minimo 200ms

Soporta context manager (`with bm as browser`).

### 2.2 SessionManager (`session_manager.py`)

Crea un contexto y una pagina con:
- **Viewport base** 1920x1080 +/- 20px (jitter)
- **navigator.webdriver** -> `undefined` (via `add_init_script`)
- **navigator.plugins** -> array de 5 elementos (simula plugins reales)
- **navigator.languages** -> `['es-ES', 'es', 'en']`
- **Extra headers**: `Accept-Language: es-ES` y `Accept` realista
- **chrome.runtime** -> objeto vacio (simula Chrome extension API)

### 2.3 AdsSearcher (`ads_searcher.py`)

Construye la URL de busqueda con filtros:
- `active_status=active`, `ad_type=all`, `country=ALL`
- `content_languages[0]=es`, `search_type=keyword_unordered`
- `sort_data[mode]=total_impressions` (desde Fase 3.2, configurable via CLI)
- `publisher_platforms[0]=facebook`, `publisher_platforms[1]=instagram`

Navega a la URL y espera 7s (`wait_after_search_ms`) a que carguen resultados.

### 2.4 AdsExtractor (`ads_extractor.py`)

Clase principal con dos etapas: Discovery y Enrichment.

### 2.5 BrowserRunner (`browser_runner.py`)

Orquestador que:
1. Inicializa BrowserManager + SessionManager + AdsSearcher + AdsExtractor
2. Por cada keyword: search -> collect_discoveries_with_scroll -> enrich
3. Checkpoint por keyword (guarda JSON tras cada una)
4. Signal handler para SIGINT/SIGTERM
5. Modos append/resume para retomar ejecuciones
6. Modo enrich-only desde archivo JSON
7. Log de configuracion al inicio y resumen final
8. Retorna lista de `BrowserAdResult`

### 2.6 DTOs (`dto/browser_ad.py`)

- `BrowserAdDiscovery`: keyword, library_id, description, circulation_start,
  landing_url, domain, ad_library_url, advertiser_name, extracted_at
- `BrowserAdEnrichment`: library_id, facebook_user, instagram_user,
  facebook_followers, instagram_followers, advertiser_info, extracted_at
- `BrowserAdResult`: discovery + enrichment (ambos opcionales)

---

## 3. Discovery — Algoritmo de Extraccion

### 3.1 Seleccion de Candidatos (`_candidate_cards`)

1. Intenta `div[role="article"]` y `div[data-testid="library-ad-card"]`
2. Si ningun selector devuelve elementos, fallback a todos los `div`
3. Filtra con `_filter_valid_cards`:
   - Texto interno no vacio
   - Contiene "Identificador de la biblioteca" o "Library ID"
   - Minimo 3 lineas de texto
   - Texto <= 5000 caracteres

### 3.2 Filtros de Descarte en Discovery (`_extract_discovery_from_card`)

Cada card pasa por estos filtros en orden:

```
1. Tiene library_id?            No -> DESCARTAR
2. Tiene landing URL?           No -> DESCARTAR
3. Dominio bloqueado?           Si -> DESCARTAR
4. Engagement CTA en card?      Si -> DESCARTAR
5. Extraer advertiser_name
6. Extraer description
7. -> ACEPTAR
```

### 3.3 Engagement CTA Detection (`_is_engagement_href`)

Dentro de `_extract_landing_url` se escanean TODOS los `<a href>` de la card.
Si alguno contiene en su href los patrones `wa.me`, `wa.link`, `whatsapp.com`,
`m.me`, `messenger.com`, `tel:`, la card se descarta. Esto evita que anuncios
con CTA a WhatsApp capturen una landing URL de texto secundario.

### 3.4 Landing URL Extraction (`_extract_landing_url`)

Proceso en 2 pasos:

1. **Deteccion de Engagement**: si ANY `<a>` tiene href a WhatsApp/Messenger
   -> return None (card descartada)
2. **Botones CTA primero**: busca `<a>` dentro de `button` o `[role=button]`
   -> si encuentra landing externa valida -> la usa
3. **Fallback general**: si hay botones pero todos bloqueados, return None.
   Solo si NO hay botones, busca en TODOS los `<a>` de la card.

Esto asegura que:
- Anuncios con CTA a WhatsApp se descartan (paso 1)
- Anuncios con boton a landing externa usan la URL del boton (paso 2)
- Anuncios sin boton CTA pero con link en texto caen en fallback (paso 3)

### 3.5 Normalizacion de URLs (`_normalize_url`)

- URLs relativas (`/...`) -> antepone `https://www.facebook.com`
- Links de `l.facebook.com` / `lm.facebook.com` -> extrae destino real del
  parametro `u`
- Solo acepta esquemas `http` y `https`
- Elimina fragmentos (`#...`)

### 3.6 Dominios Bloqueados (`BLOCKED_DOMAINS`)

```
facebook.com, fb.com, fb.me, instagram.com, messenger.com, m.me,
wa.me, wa.link, whatsapp.com, metastatus.com, about.fb.com,
transparency.fb.com, privacymanager.io, forms.gle, forms.google.com,
docs.google.com, drive.google.com, youtube.com, youtu.be,
tiktok.com, twitter.com, x.com, linkedin.com, t.me, telegram.org,
bit.ly, tinyurl.com, goo.gl, ig.me
```

Match exacto o subdominio (`domain.endswith(f".{blocked}")`).

---

## 4. Extraccion de Descripcion (`_extract_ad_description`)

### 4.1 Flujo

1. Divide el texto del card en lineas
2. Localiza el indice de "Identificador de la biblioteca" / "Library ID"
3. Itera lineas despues del library_id
4. Por cada linea aplica filtros en orden:
   - **Noise line** (`_is_noise_line`): prefix match contra UI_NOISE_LINES
   - **Longitud < 3** -> skip
   - **Solo digitos** -> skip
   - **Circulacion / estado** (`En circulacion`, `Started running`, etc.) -> skip
   - **Contiene URL** (`_contains_url`): primera palabra empieza con http o www
     (con o sin emoji prefijo) -> BREAK (corta toda recoleccion)
   - **Seguidores** (`123 seguidores`) -> skip
   - **Coincide con advertiser_name** -> skip
   - **FB.COM / API.WHATSAPP.COM** -> skip
   - **"anuncios usan este contenido"** -> skip
   - **Display URL** (`_DISPLAY_URL_RE`): mayusculas + contiene punto -> BREAK
   - **Oferta porcentual** (`20% OFF`, `15% desc`) -> BREAK
5. Lineas restantes -> join con `\n`

### 4.2 UI_NOISE_LINES

Lista de ~30 prefijos de lineas de interfaz que se filtran:
- Botones: "Registrarse", "Sign Up", "Shop Now", "Learn More",
  "See Details", "Comprar", "Reserva tu plaza", "Contact Us"
- WhatsApp: "Enviar mensaje de WhatsApp", "Send WhatsApp Message",
  "Chatea con nosotros", "Chatea en Messenger"
- Meta UI: "Informe de la biblioteca", "API de la biblioteca",
  "Buscar por palabra clave", "Numero de impresiones bajo"
- Transparencia: "Transparencia UE", "Transparencia de la",
  "Contenido de marca"
- CTA: "Visita el sitio web", "Mas informacion", "Mas informacion"
- Otros: "anuncios usan este contenido", "Ir al perfil", "FB.COM"

### 4.3 Display URL Regex (`_DISPLAY_URL_RE`)

```
^[A-Z][A-Z0-9./-]{2,59}$
```

Detecta lineas como `CEFOMIN.CL`, `LAURAKOLODNYFONO.COM`,
`DAXUS.COM/INMERSION-IA` que son la URL mostrada en el footer del card.
Corta la recoleccion (BREAK) para no incluir el footer ni contenido posterior.

### 4.4 URL Detection (`_contains_url`)

```python
stripped = line.lstrip()
first_word = stripped.split()[0].lower()
if first_word.startswith("http") or first_word.startswith("www."):
    return True
```

Maneja:
- URLs normales: `https://ejemplo.com`
- URLs en mayusculas: `HTTPS://EJEMPLO.COM`
- URLs con emoji: `:pushpin: http://ejemplo.com`
- www: `:globe_with_meridians: www.ejemplo.com`

---

## 5. Extraccion de Nombre del Anunciante (`_extract_advertiser_name`)

### 5.1 Estrategia: Backward Search First

1. Localiza library_id en el texto
2. Busca **hacia atras** desde library_id hasta el inicio
3. Para cada linea, valida con `_is_valid_name`:
   - No es noise line
   - Longitud 3-100
   - No solo digitos
   - No empieza con skip_prefixes (Activo, Inactivo, Patrocinado,
     En circulaci, Plataformas, Transparencia, etc.)
   - No es URL (http, www)
   - No contiene social domain keywords
   - No es "123 seguidores"
   - No contiene "anuncios usan este contenido"
4. Si backward no encuentra, fallback **forward** (lineas despues de
   library_id)

### 5.2 Justificacion

En el HTML de Meta Ads Library, el nombre real del anunciante aparece
ANTES del Library ID. Buscar hacia atras primero evita falsos como
"Transparencia de la UE" o "X anuncios usan este contenido" que aparecen
despues.

---

## 6. Enrichment (Datos Sociales)

### 6.1 Flujo

1. Busca boton "Ver detalles del anuncio" / "See ad details" en la card
2. Click con `force=True` (Meta tiene divs superpuestos)
3. Espera dialogo de detalles
4. Si es "Ver detalles del resumen" -> sub-flujo `_enter_from_summary`
5. Dentro del dialogo, busca heading con "anunciante" / "advertiser"
6. Click para expandir seccion del anunciante
7. Extrae datos de la seccion expandida

### 6.2 Extraccion de Usuarios Sociales (`_parse_social_from_advertiser_section`)

Busca en el texto de la seccion del anunciante:
- **Facebook**: primer `@username` encontrado, o `Identificador: N`
  (numerico)
- **Instagram**: segundo `@username` encontrado
- Orden: FB siempre aparece primero en el dialogo

### 6.3 Extraccion de Seguidores (`_parse_followers_from_advertiser_section`)

Busca patron `N seguidores` en la seccion del anunciante:
- Primer match -> Facebook
- Segundo match -> Instagram
- Usa `_parse_followers_count` para convertir a numero

### 6.4 Parseo de Seguidores (`_parse_followers_count`)

Maneja formatos en espanol:

| Texto       | Resultado   | Logica                        |
|-------------|-------------|-------------------------------|
| `1260`      | `"1260"`    | Numero plano                  |
| `2,1 mil`   | `"2100"`    | Coma decimal + mil            |
| `229,4 mil` | `"229400"`  | Coma decimal + mil            |
| `275,7 mil` | `"275700"`  | Coma decimal + mil            |
| `1,4 mill`  | `"1400000"` | Coma decimal + millones       |
| `159 mil`   | `"159000"`  | Mil sin decimal               |
| `1.473 mil` | `"1473000"` | Punto separador + mil         |

Algoritmo:
1. Detecta "mil" (x1000) o "mill" (x1.000.000)
2. Elimina sufijo "mil"/"mill"
3. Convierte coma decimal -> punto
4. Elimina puntos de separador de miles (`.` seguido de 3 digitos)
5. Extrae numero con regex
6. Multiplica por factor correspondiente
7. Convierte a entero -> string

---

## 7. Scroll y Recoleccion con Dominios Unicos

### `_collect_discoveries_with_scroll`

1. Extrae hasta `per_keyword_limit + 20` discoveries
2. Filtra por:
   - **library_id unico** (evita duplicados de cards diferentes)
   - **dominio unico** (solo un resultado por dominio)
3. Si no alcanza el limite, hace scroll incremental y re-intenta
4. Corta solo tras N scrolls consecutivos sin novedades (default 3)
5. Maximo `max_scroll_attempts` intentos (default 50, 0 = scrolls infinitos)
6. Incluye flag `consecutive_empty_scrolls` para configurar tolerancia
7. Acepta `skip_library_ids` para evitar reprocesar cards entre scrolls
8. Acepta `kw_limit` para limite especifico por keyword

### Mejoras Fase 3.1 (Optimización de Adquisición)

| # | Mejora | Descripción |
|---|--------|-------------|
| 1 | **Scroll incremental** | Ya no salta directo al fondo. Scrolla 70-110% del viewport por vez, activando lazy loading progresivo de Meta. |
| 2 | **Tolerancia a scrolls vacios** | No corta en el primer scroll sin novedades. Requiere `consecutive_empty_scrolls` (default 3) intentos consecutivos sin nuevos dominios. |
| 3 | **Espera inteligente** | Combina `wait_for_function` (observar aparicion de nuevas cards) + timeout con jitter como fallback. |
| 4 | **Eliminacion de doble extraccion** | Se elimino la segunda extraccion con `limit=5` que era redundante y desperdiciaba recursos. Ahora se mide el nuevo crecimiento directamente del resultado de la extraccion principal. |
| 5 | **Navegacion humana** | Scroll con `behavior: smooth`, incremento variable aleatorio, micro-movimientos al llegar al fondo para disparar lazy loading residual. |
| 6 | **Resolucion de URLs acortadas** | `bit.ly`, `tinyurl.com` y `goo.gl` se resuelven automaticamente siguiendo redirecciones HTTP HEAD. La URL final se almacena siempre, nunca la acortada. |
| 7 | **Observabilidad detallada** | Metricas por extraccion: cards encontradas, procesadas, descartadas por CTA/dominio bloqueado/duplicado/sin landing, URLs acortadas resueltas, nuevos dominios por scroll. |

### Diagrama de flujo mejorado

```
while not suficientes AND quedan intentos:
    extract_discovery_ads(limit=per_keyword_limit + 20)

    para cada discovery:
        si library_id ya visto -> saltar
        si dominio ya visto -> saltar
        agregar a coleccion

    si suficientes -> break
    si 0 nuevos en este paso:
        consecutive_empty++
        si consecutive_empty >= limite -> break (corte por agotamiento)
    si no:
        consecutive_empty = 0

    scroll incremental (70-110% viewport, smooth)
    esperar nuevas cards (wait_for_function + timeout con jitter)
```

---

## 8. Anti-Deteccion y Anti-Bloqueo

### 8.1 A nivel de navegador (BrowserManager)

- 9 flags Chromium anti-bot
- User-Agent Chrome 125 Windows realista

### 8.2 A nivel de sesion (SessionManager)

- **navigator.webdriver** -> `undefined`
- **navigator.plugins** -> simulado con 5 elementos
- **navigator.languages** -> `['es-ES', 'es', 'en']`
- **chrome.runtime** -> objeto `{}`
- Viewport con jitter +/-20px
- Headers HTTP realistas

### 8.3 A nivel de interaccion (AdsExtractor)

- **Jitter en delays**: `_jittered_delay()` agrega +/-30% aleatorio
- **force=True** en clicks (evita bloqueo por elementos superpuestos)
- Multiples selectores CSS para encontrar elementos (fallback progresivo)

---

## 9. Errores Conocidos Corregidos

| # | Error | Sintoma | Correccion |
|---|-------|---------|------------|
| 1 | `ig.me` no bloqueado | Dominio `ig.me` entraba como landing | Agregado a `BLOCKED_DOMAINS` |
| 2 | `advertiser_name` eligia "Transparencia de la UE" | Nombre incorrecto en resultados | Busqueda backward primero, "Transparencia" en skip_prefixes, `_is_valid_name()` con check de "anuncios usan" |
| 3 | "mill" (millones) no soportado | Followers como "1,4 mill" no se parseaban | Regex acepta "mill", multiplicador x1.000.000 |
| 4 | Decimal comma + "mil" daba erroneo | "275,7 mil" -> "2757000" (x10 mal) | Float math: `float(275.7) * 1000` en vez de concatenacion de string |
| 5 | Descripcion incluia botones/nav | "Registrarse", "Learn More", etc. en desc | +10 lineas en `UI_NOISE_LINES` |
| 6 | Display URL en descripcion | "CEFOMIN.CL", "DAXUS.COM/..." en desc | `_DISPLAY_URL_RE` con BREAK |
| 7 | URL mayuscula no filtrada | "HTTPS://..." pasaba `startswith("http")` | `_contains_url()` con `line.lstrip().split()[0].lower()` |
| 8 | URL con emoji no filtrada | ":pushpin: http://..." pasaba filtros | `_contains_url()` con `first_word` tras lstrip |
| 9 | WhatsApp CTA aceptado | Anuncio con boton WhatsApp tenia landing de texto | `_is_engagement_href` escanea TODOS los `<a>` de la card |
| 10 | Landing de texto, no de boton | Landing incorrecta cuando boton iba a WhatsApp | Botones CTA primero, fallback solo si no hay botones |
| 11 | Callout promocional en desc | "Inscripciones abiertas 15% OFF" en desc | BREAK en `\d+% (OFF|desc|Dto)` |
| 12 | CTA text en desc | "Visita el sitio web para mas informacion" | Agregado "Visita el sitio web" a `UI_NOISE_LINES` |

---

## 10. Limitaciones Conocidas

### 10.1 Baja densidad de landing URLs externas

Sin filtros: de ~140 cards visibles por busqueda, solo ~7-8 tienen landing URLs
externas validas. Con filtros `publisher_platforms=(facebook,instagram)` +
`sort_mode=total_impressions` (default desde Fase 3.2), se alcanzan ~30 dominios
unicos (4.3x mejora). Esto es una caracteristica inherente a Meta Ads Library,
no un error del algoritmo.

### 10.2 Rendimiento

- Cada ejecucion toma ~55-90s por keyword (navegador real + scroll + enrichment)
- El modo debug (visible) es aun mas lento por `slow_mo` forzado a 200ms

### 10.3 Dependencia del DOM de Meta

Los selectores CSS y la estructura esperada del HTML pueden cambiar con
actualizaciones de Meta Ads Library. Los fallback progresivos mitigan esto
pero no lo eliminan.

### 10.4 Enrichment inconsistente

No todas las cards tienen boton "Ver detalles del anuncio" funcional. El
dialogo de detalles puede no contener la seccion "Informacion sobre el
anunciante" expandible.

---

## 11. Decisiones de Diseno Clave

1. **Sin login requerido**: Meta Ads Library funciona sin sesion de Facebook
   para busqueda y enrichment. Simplifica la implementacion y evita riesgos
   de cuenta.

2. **Backward search para advertiser_name**: El nombre real del anunciante
   esta ANTES del library ID en el DOM. Buscar hacia atras primero evita
   falsos positivos.

3. **CTA button first para landing URL**: La URL del boton CTA es la landing
   autoritativa. Solo caer a texto si no hay botones.

4. **Engagement detection sobre TODOS los anchors**: Un solo link a WhatsApp
   en cualquier parte del card hace que se descarte. Esto es intencional:
   los anuncios con CTA a WhatsApp no deben tener landing externa.

5. **force=True en clicks**: Meta usa divs superpuestos e imagenes que
   interceptan clicks. `force=True` evita el error "element is not
   clickable".

6. **Float math para followers**: "275,7 mil" se computa como
   `float("275.7") * 1000 = 275700.0`. Evita errores de concatenacion
   de strings.

7. **BREAK vs CONTINUE en descripcion**: Una vez que se detecta una URL,
   display URL u oferta porcentual, se corta la recoleccion (BREAK). Esto
   asume que estas lineas siempre estan al final del card, despues del
   contenido real.

8. **Jitter en delays**: Todos los `wait_for_timeout` usan +/-30% aleatorio
    para evitar patrones deterministicos de bot.

9. **Scroll incremental**: No saltar directamente al fondo. Scrolls de
    70-110% del viewport con `behavior: smooth` activan mejor el lazy
    loading de Meta y evitan que el algoritmo se salte batches de cards.

10. **Tolerancia a scrolls vacios**: No cortar en el primer scroll sin
    novedades. Requerir N consecutivos (default 3) reduce falsos
    negativos por latencia de red o renderizado diferido.

11. **Resolucion de URLs acortadas**: `bit.ly`, `tinyurl.com` y `goo.gl`
    se resuelven via HTTP HEAD request desde Python. Siempre se almacena
    la URL final, nunca la acortada. Esto evita dominios acortadores en
    los resultados y maximiza la calidad del dato.

12. **Observabilidad en el extractor**: `AdsExtractor.stats` acumula
    contadores por tipo de descarte. Cada llamada a `extract_discovery_ads`
    logea el estado completo, permitiendo diagnosticar bottlenecks sin
    necesidad de depuracion externa.

---

## 12. Estructura de Archivos

```
src/modules/meta_ads/
  acquisition/
    ads_extractor.py       # Logica principal de extraccion (~1028 lineas)
    ads_searcher.py        # Construccion de URL y navegacion (71 lineas)
    browser_runner.py      # Orquestacion con scroll + timing (~571 lineas)
  browser/
    browser_manager.py     # Inicializacion Chromium + anti-detection (95 lineas)
    session_manager.py     # Contexto/pagina + overrides JS (66 lineas)
  dto/
    browser_ad.py          # DTOs: BrowserAdDiscovery, Enrichment, Result
scripts/
  run_meta_ads_browser.py # Entry point CLI (124 lineas)
tests/
  unit/meta_ads/
    test_browser_acquisition.py  # 24 tests (18 nuevos Fase 3.2)
    test_meta_client.py          # 3 tests
    test_parser.py               # 2 tests
docs/
  doc.phase.3.md           # Este documento
```

---

## 13. Diagrama de Flujo de Discovery

```
_candidate_cards()
  |
  +-> selectores: [div[role="article"], div[data-testid]]
  |   |
  |   +-> filter_valid_cards:
  |   |   - Tiene library_id?
  |   |   - >= 3 lineas?
  |   |   - <= 5000 chars?
  |   |
  |   +-> lista de ElementHandle
  |
  +-> extract_discovery_ads(keyword, limit)
       |
       +-> por cada card:
            |
         +-> _extract_discovery_from_card(card, keyword)
                  |
                  +-> _extract_library_id(text)
                  |   regex: "Identificador de la biblioteca: (d+)"
                  |
                  +-> _extract_landing_url(card)
                  |   1. _is_engagement_href en TODOS los <a>
                  |      -> si hay wa.me/whatsapp/etc -> return None
                  |   2. button <a href> -> external landing?
                  |      -> si, return
                  |   3. todos los <a href> -> external landing?
                  |      -> si, return
                  |      -> no, return None
                  |
                  +-> _resolve_short_url(landing_url)       [NUEVO]
                  |   bit.ly/tinyurl/goo.gl -> HTTP HEAD
                  |   -> sigue redireccion -> URL final
                  |
                  +-> _is_blocked_domain(domain)
                  |   match exacto o subdominio contra BLOCKED_DOMAINS
                  |
                  +-> _extract_advertiser_name(text)
                  |   backward search from library_id
                  |
                  +-> _extract_ad_description(text, advertiser_name)
                      filtros en orden -> BREAK en URL/display/oferta
```

---

## 14. Diagrama de Flujo de Enrichment


```
enrich_ads(discoveries)
  |
  +-> _candidate_cards() (re-lee cards actualizadas)
  |
  +-> por cada discovery:
       |
       +-> _find_card_by_library_id(cards, library_id)
       |
       +-> _extract_enrichment_from_card(card, library_id)
            |
            +-> _find_detail_button(card)
            |   busca por texto: "Ver detalles del anuncio", etc.
            |
            +-> click(force=True)
            |
            +-> "resumen" en texto del boton?
            |   si -> _enter_from_summary()
            |   no  -> _find_detail_dialog()
            |
            +-> _click_advertiser_heading(dialog)
            |   busca [role=heading] con "anunciante"/"advertiser"
            |
            +-> _parse_social_from_advertiser_section(text)
            |   FB: @username o Identificador: N
            |   IG: segundo @username
            |
            +-> _parse_followers_from_advertiser_section(text)
            |   FB: primer "N seguidores"
            |   IG: segundo "N seguidores"
            |   -> _parse_followers_count(raw)
            |
            +-> _close_details()
```

---

## 15. Fase 3.2 — Configuración Total, Persistencia Robusta y Enrichment-Only

### 15.1 Novedades respecto a Fase 3

| # | Feature | Descripción |
|---|---------|-------------|
| 1 | **Per-keyword limits** | `--keyword "nombre:limite"` asigna límite específico por keyword. Sin `:`, usa el global `--limit`. |
| 2 | **max_scrolls=0 = scrolls infinitos** | Si `0`, solo corta por objetivo alcanzado o 3 scrolls vacíos consecutivos. Sin límite de scrolls máximo. |
| 3 | **Modo append** | `--mode append` carga dominios y library_ids del archivo existente para no repetirlos. |
| 4 | **Resume** | `--resume <archivo>` carga dominios de un archivo externo para dedup cross-ejecución. |
| 5 | **Enrichment-only** | `--enrich-only <archivo.json>` lee discoveries guardados y los enriquece sin volver a scrollear. |
| 6 | **Checkpoint por keyword** | Guarda el JSON completo después de cada keyword. Si el proceso muere, lo máximo perdido es ~30s. |
| 7 | **Signal handler** | SIGINT (Ctrl+C) y SIGTERM guardan checkpoint automático antes de salir. |
| 8 | **extracted_at** | Cada discovery y enrichment lleva `extracted_at` en formato ISO 8601. |
| 9 | **Sesión nueva por keyword** | Previene OOM cerrando contexto + página entre keywords. |
| 10 | **Skip library_ids** | Las cards ya vistas entre scrolls se saltan antes de la extracción costosa (query_selector_all). |
| 11 | **Log de configuración** | Todos los parámetros activos se muestran al inicio del bot. |
| 12 | **Resumen final** | Tiempo total formateado, keywords procesadas, empresas únicas, desglose por keyword. |
| 13 | **Bloqueo extra por CLI** | `--blocked-domains "tiktok.com,x.com"` agrega dominios a BLOCKED_DOMAINS sin modificar código. |
| 14 | **Sort mode configurable** | `--sort-mode total_impressions|relevancy_monthly_grouped`. Default: `total_impressions`. |
| 15 | **Force overwrite** | `--force` salta la confirmación al sobreescribir archivo existente. |

### 15.2 Filtros Efectivos

Los filtros `publisher_platforms=(facebook,instagram)` + `sort_mode=total_impressions`
son críticos para la densidad de landings externas. Pruebas con "curso":

| Filtro | Dominios únicos | Mejora |
|--------|-----------------|--------|
| Sin filtros | ~7 | — |
| Con filtros | ~30 | 4.3x |

### 15.3 Pipeline Fase 3.2

```
CLI (run_meta_ads_browser.py)
  |
  +-> MetaAdsBrowserRunner.run(keywords, output_path, mode, ...)
       |
       +-> _load_existing()        [si mode=append o resume_path]
       |   carga dominios previos -> known_domains + known_library_ids
       |
       +-> _log_config()           [muestra todos los parametros]
       |
       +-> loop por keyword:
       |   |
       |   +-> _process_keyword(kw, limit_por_keyword)
       |   |   |
       |   |   +-> BrowserManager.start()
       |   |   +-> SessionManager.create_session()
       |   |   +-> AdsSearcher.search(keyword)
       |   |   +-> _collect_discoveries_with_scroll(limit)
       |   |   |   while not enough AND (max_scrolls==0 OR attempts < max):
       |   |   |       extract_discovery_ads(skip_library_ids=seen)
       |   |   |       filter new library_ids not in known / not duplicate
       |   |   |       if new == 0: consecutive_empty++
       |   |   |       scroll()
       |   |   |
       |   |   +-> enrich_ads(discoveries) [si no --no-enrich]
       |   |   +-> SessionManager.close_session()
       |   |
       |   +-> _save_checkpoint()   [guarda JSON completo]
       |   +-> _register_signal_handler()  [SIGINT/SIGTERM -> checkpoint]
       |
       +-> _log_final_summary()
```

### 15.4 Estructura de Archivos Actualizada

```
src/modules/meta_ads/
  acquisition/
    ads_extractor.py       # ~1028 lineas (+extra_blocked_domains, extracted_at)
    ads_searcher.py        # 71 lineas (sin cambios)
    browser_runner.py      # ~571 lineas (refactor mayor)
  browser/
    browser_manager.py     # 95 lineas (sin cambios)
    session_manager.py     # 66 lineas (sin cambios)
  dto/
    browser_ad.py          # DTOs con extracted_at
scripts/
  run_meta_ads_browser.py # 124 lineas (CLI completo)
tests/
  unit/meta_ads/
    test_browser_acquisition.py  # 24 tests (18 nuevos)
    test_meta_client.py          # 3 tests (sin cambios)
    test_parser.py               # 2 tests (sin cambios)
docs/
  doc.phase.3.md           # Este documento (+seccion 15)
  phases/PHASE_03_2_CONFIG_PERSIST_ENRICH.md  # Documento de fase dedicado
```

### 15.5 Tabla de Argumentos CLI

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--keyword` | (requerido) | `"nombre"` o `"nombre:limite"` |
| `--limit` | 30 | Límite global por keyword |
| `--max-scrolls` | 50 | 0 = scrolls infinitos |
| `--empty-scrolls` | 3 | Cortar tras N scrolls vacíos consecutivos |
| `--sort-mode` | `total_impressions` | `relevancy_monthly_grouped` |
| `--mode` | `overwrite` | `append` para retomar |
| `--resume` | — | JSON con dominios a bloquear (dedup) |
| `--enrich-only` | — | JSON de discoveries para enriquecer |
| `--blocked-domains` | — | Dominios extra, separados por coma |
| `--headless` | `False` | Modo sin ventana |
| `--no-enrich` | `False` | Solo discovery, sin enrichment |
| `--force` | `False` | Sobreescribir sin preguntar |
| `--debug` | `False` | Logs detallados (DEBUG level) |
| `--slow-mo` | 0 | Delay entre acciones (ms) |
| `--wait-ms` | 7000 | Espera post-búsqueda |
| `--action-delay-ms` | 1200 | Delay entre clics |

### 15.6 Log de Configuración (inicio)

```
======================================================================
  INICIO DE ADQUISICION — META ADS LIBRARY
======================================================================
  Keywords            : "curso:30", "curso marketing:50", "curso ingles"
  Modo                : append (retomando archivo existente)
  Resume desde        : output/anterior.json (12 dominios cargados)
  Archivo salida      : output/resultados.json
  Limite global       : 30
  Scrolls maximos     : 50 (0=infinito)
  Cortar tras vacios  : 3
  Plataformas         : facebook, instagram
  Ordenamiento        : total_impressions
  Enriquecimiento     : si
  Modo debug          : no
  Navegador           : headless
  Dominios bloqueados : 29 default + 2 extra (tiktok.com, x.com)
  Dominios conocidos  : 0 (sin previos)
  Library IDs previos : 0
======================================================================
  ESTADISTICAS DE DESCARTE:
    • sin_landing       – Sin enlace externo
    • solo_cta          – Solo WhatsApp/Messenger/tel
    • dominio_bloq.     – En BLOCKED_DOMAINS
    • url_acortada      – bit.ly/tinyurl resuelta
======================================================================
```

### 15.7 Log de Resumen Final

```
======================================================================
  RESUMEN FINAL
======================================================================
  Tiempo total              : 24m 32s
  Keywords procesadas       : 4/4
  Resultados totales        : 107
  Empresas (dominios) unicas: 89
  Archivo de salida         : output/resultados.json (modo: overwrite)
  Dominios cargados previos : 0

  KEYWORD                     EMPRESAS   TIEMPO    SCROLLS  ESTADO
  ----------------------------------------------------------------
  curso                          30    4m 53s      6     objetivo
  curso marketing                30    7m 30s     10     objetivo
  curso programacion             30    8m 13s      8     objetivo
  curso ingles                   17    4m 42s      8     3 vacios

  ESTADISTICAS DE EXTRACCION:
    Cards vistas                  : 9,896
    Cards nuevas evaluadas        : 5,906
    Descartadas sin landing       : 5,232 (88.6%)
    Descartadas solo CTA          : 194   (3.3%)
    Descartadas dominio bloq.     : 0     (0.0%)
    URLs acortadas resueltas      : 0     (0.0%)
    Tasa conversion (unicos/eval) : 1.5%
======================================================================
```
