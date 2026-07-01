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
- `sort_data[mode]=relevancy_monthly_grouped`

Navega a la URL y espera 7s (`wait_after_search_ms`) a que carguen resultados.

### 2.4 AdsExtractor (`ads_extractor.py`)

Clase principal con dos etapas: Discovery y Enrichment.

### 2.5 BrowserRunner (`browser_runner.py`)

Orquestador que:
1. Inicializa BrowserManager + SessionManager + AdsSearcher + AdsExtractor
2. Por cada keyword: search -> collect_discoveries_with_scroll -> enrich
3. Loggea timing por keyword y total
4. Retorna lista de `BrowserAdResult`

### 2.6 DTOs (`dto/browser_ad.py`)

- `BrowserAdDiscovery`: keyword, library_id, description, circulation_start,
  landing_url, domain, ad_library_url, advertiser_name
- `BrowserAdEnrichment`: library_id, facebook_user, instagram_user,
  facebook_followers, instagram_followers, advertiser_info
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
3. Si no alcanza el limite, hace scroll y re-intenta
4. Si tras scroll no hay nuevos dominios -> corta
5. Maximo `max_scroll_attempts` intentos (default 10)

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

De ~140 cards visibles por busqueda, solo ~7-8 tienen landing URLs externas
validas. La mayoria de anuncios en Meta Ads Library linkean a Facebook,
Instagram o WhatsApp. Esto es una caracteristica inherente a Meta Ads Library,
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

---

## 12. Estructura de Archivos

```
src/modules/meta_ads/
  acquisition/
    ads_extractor.py       # Logica principal de extraccion (940 lineas)
    ads_searcher.py        # Construccion de URL y navegacion (71 lineas)
    browser_runner.py      # Orquestacion con scroll + timing (176 lineas)
  browser/
    browser_manager.py     # Inicializacion Chromium + anti-detection (95 lineas)
    session_manager.py     # Contexto/pagina + overrides JS (66 lineas)
  dto/
    browser_ad.py          # DTOs: BrowserAdDiscovery, Enrichment, Result
scripts/
  run_meta_ads_browser.py # Entry point CLI
tests/
  unit/meta_ads/
    test_browser_acquisition.py  # 20 tests
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
