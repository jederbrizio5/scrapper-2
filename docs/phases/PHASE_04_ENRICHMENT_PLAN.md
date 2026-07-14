# Fase 4: Enriquecimiento Profundo de Empresas

## Estado

Pendiente — dividida en 5 etapas secuenciales.

---

## Objetivo General

Enriquecer las empresas descubiertas via Meta Ads Library con información profunda obtenida de:
1. **Meta Ads Library** (ya implementado, se renombra a `enrichment_library`)
2. **Redes sociales** (Facebook/Instagram) — bio, teléfono, email, links, seguidores reales
3. **Landing page** — teléfonos, emails, redes sociales, WhatsApp, ubicaciones, precios, formularios
4. **Dominio completo** — crawling multi-página del dominio

El objetivo final es tener un perfil completo de cada empresa para luego calcular un score de aptitud como cliente de bot/server-side-tracking/dashboards.

---

## Estructura de Etapas

| Etapa | Nombre | Depende de |
|-------|--------|------------|
| **4.1** | DTOs y modelo de datos | Fase 3.2 |
| **4.2** | Social Enrichment (FB/IG) | 4.1 + enrichment_library |
| **4.3** | Landing Enrichment | 4.1 |
| **4.4** | Domain Enrichment | 4.1 |
| **4.5** | Orquestación, CLI y serialización | 4.1, 4.2, 4.3, 4.4 |

---

## Etapa 4.1 — DTOs y Modelo de Datos

### Objetivo

Extender el modelo de datos para soportar los 3 nuevos tipos de enrichment. Renombrar `enrichment` a `enrichment_library` para ser explícitos.

### Archivos a crear

- `src/modules/meta_ads/dto/social_enrichment.py` — DTOs `SocialProfile`, `SocialEnrichment`
- `src/modules/meta_ads/dto/landing_enrichment.py` — DTO `LandingEnrichment`
- `src/modules/meta_ads/dto/domain_enrichment.py` — DTO `DomainEnrichment`

### Archivos a modificar

- `src/modules/meta_ads/dto/browser_ad.py` — extender `BrowserAdResult` con nuevos campos, renombrar `enrichment` → `enrichment_library`
- `src/modules/meta_ads/dto/__init__.py` — exportar nuevos DTOs
- `src/modules/meta_ads/acquisition/browser_runner.py` — actualizar serialización en `_save_checkpoint`, `_save_enrich_inplace`, `_write_split_index`

### DTOs detallados

```python
# src/modules/meta_ads/dto/social_enrichment.py

@dataclass
class SocialProfile:
    platform: str
    username: str
    display_name: str | None
    bio: str | None
    bio_links: list[str] | None
    links: list[str] | None
    phone: str | None
    email: str | None
    website: str | None
    followers: int | None
    following: int | None
    posts: int | None
    profile_url: str
    extracted_at: str | None

@dataclass
class SocialEnrichment:
    profiles: list[SocialProfile]
    extracted_at: str | None
```

```python
# src/modules/meta_ads/dto/landing_enrichment.py
@dataclass
class LandingEnrichment:
    landing_url: str
    phones: list[str]
    emails: list[str]
    social_links: list[dict]
    whatsapp: str | None
    locations: list[str]
    country: str | None
    prices: list[str]
    purchase_links: list[str]
    has_forms: bool
    forms: list[dict]
    business_category: str | None
    has_captcha_or_block: bool
    block_type: str | None
    extracted_at: str | None
```

```python
# src/modules/meta_ads/dto/domain_enrichment.py
@dataclass
class DomainEnrichment:
    domain: str
    pages_scraped: int
    phones: list[str]
    emails: list[str]
    social_links: list[dict]
    whatsapp: str | None
    locations: list[str]
    country: str | None
    prices: list[str]
    purchase_links: list[str]
    has_forms: bool
    forms: list[dict]
    business_category: str | None
    has_captcha_or_block: bool
    block_type: str | None
    extracted_at: str | None
```

### BrowserAdResult extendido

```python
@dataclass
class BrowserAdResult:
    discovery: BrowserAdDiscovery
    enrichment_library: BrowserAdEnrichment | None = None
    social_enrichment: SocialEnrichment | None = None
    landing_enrichments: list[LandingEnrichment] | None = None
    domain_enrichment: DomainEnrichment | None = None
```

### Serialización JSON

```json
{
  "discovery": { ... },
  "enrichment_library": { ... },
  "social_enrichment": {
    "profiles": [
      {
        "platform": "facebook",
        "username": "weyaacademy",
        "display_name": "Weya Academy",
        "bio": "Transformamos tu carrera...",
        "bio_links": ["https://weya.academy/curso"],
        "links": ["https://weya.academy"],
        "phone": null,
        "email": null,
        "website": "https://weya.academy",
        "followers": 1234,
        "following": 89,
        "posts": 45,
        "profile_url": "https://facebook.com/weyaacademy",
        "extracted_at": "13/07/2026 15:30:00 hs"
      }
    ],
    "extracted_at": "13/07/2026 15:30:00 hs"
  },
  "landing_enrichments": [
    {
      "landing_url": "https://weya.academy",
      "phones": ["+5491123456789"],
      "emails": ["info@weya.academy"],
      "social_links": [
        {"platform": "instagram", "url": "https://instagram.com/weyaacademy", "username": "weyaacademy"},
        {"platform": "facebook", "url": "https://facebook.com/weyaacademy", "username": "weyaacademy"}
      ],
      "whatsapp": "+5491123456789",
      "locations": ["Buenos Aires, Argentina"],
      "country": "AR",
      "prices": ["$15000", "$25000"],
      "purchase_links": ["https://weya.academy/comprar/curso"],
      "has_forms": true,
      "forms": [{"type": "contact", "action": "/contacto", "fields_count": 5}],
      "business_category": "infoproductor",
      "has_captcha_or_block": false,
      "block_type": null,
      "extracted_at": "13/07/2026 15:30:00 hs"
    }
  ],
  "domain_enrichment": {
    "domain": "weya.academy",
    "pages_scraped": 5,
    "phones": ["+5491123456789"],
    "emails": ["info@weya.academy"],
    "social_links": [...],
    "whatsapp": "+5491123456789",
    "locations": ["Buenos Aires, Argentina"],
    "country": "AR",
    "prices": ["$15000", "$25000"],
    "purchase_links": ["https://weya.academy/comprar/curso"],
    "has_forms": true,
    "forms": [{"type": "contact", "action": "/contacto", "fields_count": 5}],
    "business_category": "infoproductor",
    "has_captcha_or_block": false,
    "block_type": null,
    "extracted_at": "13/07/2026 15:30:00 hs"
  }
}
```

### Tests de Etapa 4.1

- `tests/unit/test_social_enrichment_dto.py` — creación, serialización, campos opcionales
- `tests/unit/test_landing_enrichment_dto.py` — creación, serialización, campos opcionales
- `tests/unit/test_domain_enrichment_dto.py` — creación, serialización, campos opcionales
- `tests/unit/test_browser_ad_result_extended.py` — `BrowserAdResult` con nuevos campos, renombrado `enrichment_library`

---

## Etapa 4.2 — Social Enrichment (Facebook/Instagram)

### Objetivo

Dado un `facebook_user` o `instagram_user` del `enrichment_library`, visitar el perfil real y extraer información pública.

### Archivos a crear

- `src/modules/meta_ads/enrichment/__init__.py`
- `src/modules/meta_ads/enrichment/social_enricher.py` — clase `SocialEnricher`
- `tests/unit/test_social_enricher.py`
- `tests/integration/test_social_enricher_real.py` — tests contra URLs reales

### Dependencias

- `enrichment_library` debe tener `facebook_user` o `instagram_user` para poder ejecutarse
- Si no hay usuarios sociales, el enrichment se salta gracefulmente

### Qué extrae

Para cada perfil social (FB e IG):

| Campo | Fuente | Método |
|-------|--------|--------|
| `display_name` | Heading del perfil | Selector CSS |
| `bio` | Bio/descripción | Selector CSS |
| `bio_links` | Links dentro del texto de la bio | Regex + selectores |
| `links` | Sección de links del perfil | Selectores CSS |
| `phone` | Botón/badge de teléfono | Selector + regex |
| `email` | Botón/badge de email | Selector + regex |
| `website` | Link del sitio web | Selector CSS |
| `followers` | Contador de seguidores | Selector + parse |
| `following` | Contador de seguidos | Selector + parse |
| `posts` | Contador de publicaciones | Selector + parse |

### Flujo de extracción

1. Navegar a `https://facebook.com/{username}` o `https://instagram.com/{username}`
2. Esperar carga de la página
3. Detectar bloqueos (login wall, rate limit, captcha)
4. Extraer datos del perfil via selectores CSS
5. Si hay botón de teléfono/email, clickear para revelar
6. Extraer links de la bio y sección de links
7. Cerrar sesión/navegador

### Anti-detección

- Mismos flags Chromium que Fase 3
- User-Agent realista
- Delays con jitter entre requests
- Proxies (reutilizar lógica de Fase 3.2)
- Timeout por perfil: 15s

### Login handling

- Env vars: `META_EMAIL`, `META_PASSWORD` (opcionales)
- Sesión separada de Playwright para social enrichment
- Si hay credenciales → intentar login en Instagram/Facebook
- Si no hay credenciales o login falla → modo público
- Si la cuenta se pierde (bloqueo/2FA) → desactivar social enrichment, log claro
- Las credenciales NUNCA se guardan en logs ni archivos

### Seguridad ante fallos

- Timeout por perfil: 15s
- Si Instagram/Facebook requiere login y no hay credenciales → devolver lo público
- Si la página no carga → log + saltar
- Si hay captcha/block → `has_captcha_or_block: True`, log, saltar
- Reintentos: 1 intento con backoff 3s
- Cada perfil es independiente: si FB falla, IG puede funcionar

### Tests

- `test_social_enricher_parse_profile`: parseo de datos mockeados
- `test_social_enricher_bio_links`: extracción de links de la bio
- `test_social_enricher_phone_button`: detección de teléfono como botón
- `test_social_enricher_login_required`: comportamiento sin login
- `test_social_enricher_real_facebook` (--run-real): navega a perfil real de FB
- `test_social_enricher_real_instagram` (--run-real): navega a perfil real de IG

---

## Etapa 4.2 — Social Enrichment (Facebook/Instagram)

### Objetivo

Dado un `facebook_user` o `instagram_user` del `enrichment_library`, visitar el perfil real y extraer información pública.

### Archivos a crear

- `src/modules/meta_ads/enrichment/__init__.py`
- `src/modules/meta_ads/enrichment/social_enricher.py` — clase `SocialEnricher`
- `tests/unit/test_social_enricher.py`
- `tests/integration/test_social_enricher_real.py` — tests contra URLs reales

### Dependencias

- `enrichment_library` debe tener `facebook_user` o `instagram_user` para poder ejecutarse
- Si no hay usuarios sociales, el enrichment se salta gracefulmente

### Qué extrae por perfil

| Campo | Fuente | Método |
|-------|--------|--------|
| `display_name` | Heading del perfil | Selector CSS |
| `bio` | Descripción del perfil | Selector CSS |
| `bio_links` | Links dentro del texto de la bio | Regex + selectores |
| `links` | Sección de links del perfil | Selectores CSS |
| `phone` | Botón/badge de teléfono | Selector + click para revelar |
| `email` | Botón/badge de email | Selector + click para revelar |
| `website` | Link del sitio web | Selector CSS |
| `followers` | Contador de seguidores | Selector + parse numérico |
| `following` | Contador de seguidos | Selector + parse numérico |
| `posts` | Contador de publicaciones | Selector + parse numérico |

### Flujo de extracción

1. Navegar a `https://facebook.com/{username}` o `https://instagram.com/{username}`
2. Esperar carga de la página (timeout: 15s)
3. Detectar bloqueos (login wall, rate limit, captcha)
4. Extraer datos del perfil via selectores CSS
5. Si hay botón de teléfono/email, clickear para revelar
6. Extraer links de la bio y sección de links
7. Cerrar sesión/página

### Anti-detección

- Mismos flags Chromium que Fase 3 (`--disable-blink-features=AutomationControlled`)
- User-Agent realista
- Delays con jitter entre requests
- Proxies (reutilizar `proxy_list` de Fase 3.2)
- Timeout por perfil: 15s
- Sesión separada de Playwright (no mezclar con Meta Ads Library)

### Login handling

```python
META_EMAIL = os.getenv("META_EMAIL")
META_PASSWORD = os.getenv("META_PASSWORD")
```

- Sesión separada de Playwright para social enrichment
- Si hay credenciales → intentar login en Instagram/Facebook
- Si no hay credenciales o login falla → modo público
- Si la cuenta se pierde (bloqueo/2FA) → desactivar social enrichment, log claro
- Las credenciales NUNCA se guardan en logs ni archivos
- El login se hace en una página/contexto aislado

### Seguridad ante fallos

- Timeout por perfil: 15s
- Si Instagram/Facebook requiere login y no hay credenciales → devolver lo público
- Si la página no carga → log + saltar
- Si hay captcha/block → `has_captcha_or_block: True`, log, saltar
- Reintentos: 1 intento con backoff 3s
- Cada perfil es independiente: si FB falla, IG puede funcionar
- Si la cuenta se pierde → desactivar social enrichment gracefulmente

### Tests

- `test_social_enricher_parse_profile`: parseo de datos mockeados
- `test_social_enricher_bio_links`: extracción de links de la bio
- `test_social_enricher_links_section`: extracción de links de la sección de links
- `test_social_enricher_phone_button`: detección de teléfono como botón
- `test_social_enricher_email_button`: detección de email como botón
- `test_social_enricher_login_required`: comportamiento sin login
- `test_social_enricher_followers_parse`: parseo de contadores
- `test_social_enricher_real_facebook` (--run-real): navega a perfil real de FB
- `test_social_enricher_real_instagram` (--run-real): navega a perfil real de IG

---

## Etapa 4.3 — Landing Enrichment

### Objetivo

Dada una `landing_url` del discovery, scrapear la página y extraer toda la información disponible de la empresa.

### Archivos a crear

- `src/modules/meta_ads/enrichment/landing_enricher.py` — clase `LandingEnricher`
- `tests/unit/test_landing_enricher.py`
- `tests/integration/test_landing_enricher_real.py` — tests contra URLs reales

### Dependencias

- Requiere `landing_url` en el discovery
- Si no hay landing, el enrichment se salta gracefulmente

### Qué extrae

| Campo | Fuente | Método |
|-------|--------|--------|
| `phones` | Texto, botones, meta tags | Regex + `phonenumbers` |
| `emails` | Texto, mailto links | Regex |
| `social_links` | Links a FB, IG, Twitter, LinkedIn, TikTok, YouTube, WhatsApp | Regex + selectores |
| `whatsapp` | Links wa.me, botones WhatsApp | Regex + selectores |
| `locations` | Direcciones, ciudades, provincias | Regex + meta tags |
| `country` | Prefijo telefónico, ccTLD, HTML lang, OG locale, moneda | Pipeline multi-capa |
| `prices` | Montos con símbolos de moneda | Regex |
| `purchase_links` | Botones de compra, "Comprar", "Shop Now" | Selectores + regex |
| `has_forms` | Detección de formularios | Selectores CSS |
| `forms` | Tipo, action, cantidad de campos | Selectores + regex |
| `business_category` | Categoría inferida | Keyword matching |
| `has_captcha_or_block` | Detección de bloqueos | Regex en body |
| `block_type` | Tipo de bloqueo | Regex en body |

### Country detection pipeline

| Prioridad | Método | Tecnología | Velocidad |
|-----------|--------|-----------|-----------|
| 1 | Prefijo telefónico | `phonenumbers` lib | Instantáneo |
| 2 | ccTLD del dominio | `.com.ar` → AR, `.es` → ES | Instantáneo |
| 3 | HTML lang attribute | `selectolax` | ~50ms |
| 4 | Open Graph locale | `og:locale: es_AR` | ~50ms |
| 5 | Moneda en contenido | regex ($, €, R$, S/) | ~100ms |
| 6 | Meta tags geográficos | `geo.placename`, `business:contact_data` | ~50ms |
| 7 | WHOIS domain | `whois` lib (fallback lento) | ~1-2s |

### Business categorization

| Categoría | Señales clave |
|-----------|---------------|
| `ecommerce` | Carrito, "comprar", "agregar al carrito", "tienda", productos con precio, stock, "envío" |
| `infoproductor` | Cursos, webinars, ebooks, membresías, "aprendé", "capacitación", "coach", "programa" |
| `servicio` | Consultoría, agencia, "contactanos", "presupuesto", servicios profesionales |
| `saas` | Dashboard, plataforma, "plan", "suscripción", "login", "software" |
| `lead_gen` | Formularios de contacto, cotización, "solicitá info", "descargá" |
| `contenido` | Blog, medios, afiliados, "leer más", artículos, noticias |

### Cloudflare/Captcha detection

```python
BLOCK_SIGNALS = (
    "verify you are human",
    "verifica que eres humano",
    "just a moment",
    "checking your browser",
    "cloudflare",
    "attention required",
    "atención requerida",
    "no soy un robot",
    "i'm not a robot",
    "recaptcha",
)
```

- Si se detecta → `has_captcha_or_block: True`, `block_type: "cloudflare"|"recaptcha"|"blocked"`
- Reintento con backoff (1, 3, 5s)
- Si persiste → saltar ese dominio, log claro
- No reintentar infinitamente

### Tests

- `test_social_enricher_parse_profile`: parseo de datos mockeados
- `test_social_enricher_bio_links`: extracción de links de la bio
- `test_social_enricher_links_section`: extracción de links de la sección de links
- `test_social_enricher_phone_button`: detección de teléfono como botón
- `test_social_enricher_email_button`: detección de email como botón
- `test_social_enricher_login_required`: comportamiento sin login
- `test_social_enricher_followers_parse`: parseo de contadores
- `test_social_enricher_real_facebook` (--run-real): navega a perfil real de FB
- `test_social_enricher_real_instagram` (--run-real): navega a perfil real de IG

---

## Etapa 4.3 — Landing Enrichment

### Objetivo

Dada una `landing_url` del discovery, scrapear la página y extraer toda la información disponible de la empresa.

### Archivos a crear

- `src/modules/meta_ads/enrichment/landing_enricher.py` — clase `LandingEnricher`
- `tests/unit/test_landing_enricher.py`
- `tests/integration/test_landing_enricher_real.py` — tests contra URLs reales

### Dependencias

- Requiere `landing_url` en el discovery
- Si no hay landing, el enrichment se salta gracefulmente

### Qué extrae

| Campo | Fuente | Método |
|-------|--------|--------|
| `phones` | Texto, botones, meta tags, schema.org | Regex + `phonenumbers` |
| `emails` | Texto, mailto links, meta tags | Regex |
| `social_links` | Links a FB, IG, Twitter/X, LinkedIn, TikTok, YouTube, WhatsApp | Regex + selectores |
| `whatsapp` | Links wa.me, botones WhatsApp | Regex + selectores |
| `locations` | Direcciones, ciudades, provincias, países | Regex + meta tags + schema.org |
| `country` | Prefijo telefónico, ccTLD, HTML lang, OG locale, moneda | Pipeline multi-capa |
| `prices` | Montos con símbolos de moneda | Regex |
| `purchase_links` | Botones de compra, "Comprar", "Shop Now", "Add to cart" | Selectores + regex |
| `has_forms` | Detección de formularios | Selectores CSS |
| `forms` | Tipo, action, cantidad de campos | Selectores + regex |
| `business_category` | Categoría inferida | Keyword matching |
| `has_captcha_or_block` | Detección de bloqueos | Regex en body |
| `block_type` | Tipo de bloqueo | Regex en body |

### Country detection pipeline

| Prioridad | Método | Tecnología | Velocidad |
|-----------|--------|-----------|-----------|
| 1 | Prefijo telefónico | `phonenumbers` lib | Instantáneo |
| 2 | ccTLD del dominio | `.com.ar` → AR, `.es` → ES | Instantáneo |
| 3 | HTML lang attribute | `selectolax` | ~50ms |
| 4 | Open Graph locale | `og:locale: es_AR` | ~50ms |
| 5 | Moneda en contenido | regex ($, €, R$, S/) | ~100ms |
| 6 | Meta tags geográficos | `geo.placename`, `business:contact_data` | ~50ms |
| 7 | WHOIS domain | `whois` lib (fallback lento) | ~1-2s |

### Business categorization

```python
BUSINESS_CATEGORIES = {
    "ecommerce": [
        "carrito", "comprar", "agregar al carrito", "tienda", "productos",
        "stock", "envío", "shop", "cart", "buy", "add to cart", "store"
    ],
    "infoproductor": [
        "curso", "webinar", "ebook", "membresía", "membresia",
        "aprendé", "aprende", "capacitación", "capacitacion",
        "coach", "coaching", "programa", "formación", "formacion"
    ],
    "servicio": [
        "consultoría", "consultoria", "agencia", "presupuesto",
        "servicio técnico", "servicio tecnico", "profesional",
        "asesoría", "asesoria"
    ],
    "saas": [
        "dashboard", "plataforma", "plan", "suscripción", "suscripcion",
        "login", "software", "app", "panel de control"
    ],
    "lead_gen": [
        "solicitá info", "solicita info", "descargá", "descarga",
        "cotización", "cotizacion", "presupuesto sin cargo",
        "recibí más info", "recibi mas info"
    ],
    "contenido": [
        "blog", "noticias", "artículos", "articulos",
        "leer más", "leer mas", "suscribite", "suscríbete"
    ]
}
```

### Cloudflare/Captcha detection

```python
BLOCK_SIGNALS = (
    "verify you are human",
    "verifica que eres humano",
    "just a moment",
    "checking your browser",
    "cloudflare",
    "attention required",
    "atención requerida",
    "no soy un robot",
    "i'm not a robot",
    "recaptcha",
)
```

- Si se detecta → `has_captcha_or_block: True`, `block_type: "cloudflare"|"recaptcha"|"blocked"`
- Reintento con backoff (1, 3, 5s)
- Si persiste → saltar ese dominio, log claro
- No reintentar infinitamente

### Tech stack

| Componente | Tecnología | Razón |
|-----------|-----------|-------|
| HTTP simple | `httpx` (sync) | Rápido, manejo de redirects, timeouts |
| JS-heavy | Playwright (reutilizar BrowserManager) | Misma base que Fase 3 |
| HTML parsing | `selectolax` | 10x más rápido que BeautifulSoup |
| Phone validation | `phonenumbers` | Google lib, detecta país por prefijo |
| Email extraction | regex | Simple y efectivo |
| Price extraction | regex + currency symbols | ARS, USD, EUR, BRL, etc. |
| Country detection | phonenumbers + ccTLD + lang + content | Pipeline multi-capa |

### Anti-ban strategy

| Técnica | Dónde se aplica |
|---------|-----------------|
| User-Agent realista | httpx + Playwright |
| Delays con jitter | Entre requests |
| Proxies rotativos | Reutilizar lógica de Fase 3.2 |
| Timeouts cortos | 10s landing, 15s social |
| Cache de URLs | No re-scrapear lo mismo |
| Graceful degradation | Cada enriquecedor es independiente |
| Sesiones separadas | Social ≠ Landing ≠ Domain |

### Tests

- `test_landing_enricher_phones`: extracción de teléfonos de HTML
- `test_landing_enricher_emails`: extracción de emails de HTML
- `test_landing_enricher_social_links`: detección de redes sociales
- `test_landing_enricher_whatsapp`: detección de WhatsApp
- `test_landing_enricher_locations`: extracción de ubicaciones
- `test_landing_enricher_country_phone`: detección de país por prefijo telefónico
- `test_landing_enricher_country_cctld`: detección de país por ccTLD
- `test_landing_enricher_country_lang`: detección de país por HTML lang
- `test_landing_enricher_prices`: extracción de precios
- `test_landing_enricher_purchase_links`: detección de links de compra
- `test_landing_enricher_forms`: detección de formularios
- `test_landing_enricher_business_category`: inferencia de categoría
- `test_landing_enricher_captcha_detection`: detección de bloqueos
- `test_landing_enricher_real_url` (--run-real): navega a URL real

---

## Etapa 4.3 — Landing Enrichment

### Objetivo

Dada una `landing_url` del discovery, scrapear la página y extraer toda la información disponible de la empresa.

### Archivos a crear

- `src/modules/meta_ads/enrichment/landing_enricher.py` — clase `LandingEnricher`
- `tests/unit/test_landing_enricher.py`
- `tests/integration/test_landing_enricher_real.py` — tests contra URLs reales

### Dependencias

- Requiere `landing_url` en el discovery
- Si no hay landing, el enrichment se salta gracefulmente

### Qué extrae

| Campo | Fuente | Método |
|-------|--------|--------|
| `phones` | Texto, botones, meta tags, schema.org | Regex + `phonenumbers` |
| `emails` | Texto, mailto links, meta tags | Regex |
| `social_links` | Links a FB, IG, Twitter/X, LinkedIn, TikTok, YouTube, WhatsApp | Regex + selectores |
| `whatsapp` | Links wa.me, botones WhatsApp | Regex + selectores |
| `locations` | Direcciones, ciudades, provincias, países | Regex + meta tags + schema.org |
| `country` | Prefijo telefónico, ccTLD, HTML lang, OG locale, moneda | Pipeline multi-capa |
| `prices` | Montos con símbolos de moneda | Regex |
| `purchase_links` | Botones de compra, "Comprar", "Shop Now", "Add to cart" | Selectores + regex |
| `has_forms` | Detección de formularios | Selectores CSS |
| `forms` | Tipo, action, cantidad de campos | Selectores + regex |
| `business_category` | Categoría inferida | Keyword matching |
| `has_captcha_or_block` | Detección de bloqueos | Regex en body |
| `block_type` | Tipo de bloqueo | Regex en body |

### Tech stack

| Componente | Tecnología | Razón |
|-----------|-----------|-------|
| HTTP simple | `httpx` (sync) | Rápido, manejo de redirects, timeouts |
| JS-heavy | Playwright (reutilizar BrowserManager) | Misma base que Fase 3 |
| HTML parsing | `selectolax` | 10x más rápido que BeautifulSoup |
| Phone validation | `phonenumbers` | Google lib, detecta país por prefijo |
| Email extraction | regex | Simple y efectivo |
| Price extraction | regex + currency symbols | ARS, USD, EUR, BRL, etc. |
| Country detection | phonenumbers + ccTLD + lang + content | Pipeline multi-capa |

### Anti-ban strategy

| Técnica | Dónde se aplica |
|---------|-----------------|
| User-Agent realista | httpx + Playwright |
| Delays con jitter | Entre requests |
| Proxies rotativos | Reutilizar lógica de Fase 3.2 |
| Timeouts cortos | 10s landing, 15s social |
| Cache de URLs | No re-scrapear lo mismo |
| Graceful degradation | Cada enriquecedor es independiente |
| Sesiones separadas | Social ≠ Landing ≠ Domain |

### Seguridad ante fallos

- Timeout por landing: 10s
- Si la página no responde → log + saltar
- Si hay captcha/block → `has_captcha_or_block: True`, log, saltar
- Reintentos: 1 intento con backoff 3s
- Cada landing es independiente: si una falla, las otras continúan
- Cache de URLs para no re-scrapear la misma landing

### Tests

- `test_landing_enricher_phones`: extracción de teléfonos de HTML
- `test_landing_enricher_emails`: extracción de emails de HTML
- `test_landing_enricher_social_links`: detección de redes sociales
- `test_landing_enricher_whatsapp`: detección de WhatsApp
- `test_landing_enricher_locations`: extracción de ubicaciones
- `test_landing_enricher_country_phone`: detección de país por prefijo telefónico
- `test_landing_enricher_country_cctld`: detección de país por ccTLD
- `test_landing_enricher_country_lang`: detección de país por HTML lang
- `test_landing_enricher_prices`: extracción de precios
- `test_landing_enricher_purchase_links`: detección de links de compra
- `test_landing_enricher_forms`: detección de formularios
- `test_landing_enricher_business_category`: inferencia de categoría
- `test_landing_enricher_captcha_detection`: detección de bloqueos
- `test_landing_enricher_real_url` (--run-real): navega a URL real

---

## Etapa 4.4 — Domain Enrichment

### Objetivo

Dado un `domain` del discovery, crawlear el dominio completo para obtener la misma información que landing pero a nivel dominio.

### Archivos a crear

- `src/modules/meta_ads/enrichment/domain_enricher.py` — clase `DomainEnricher`
- `tests/unit/test_domain_enricher.py`
- `tests/integration/test_domain_enricher_real.py` — tests contra URLs reales

### Dependencias

- Requiere `domain` en el discovery
- Si no hay dominio, el enrichment se salta gracefulmente

### Qué extrae

Mismos campos que `LandingEnrichment` pero a nivel dominio:

| Campo | Descripción |
|-------|-------------|
| `domain` | Dominio crawleado |
| `pages_scraped` | Cantidad de páginas scrapeadas |
| `phones` | Agregado de todos los teléfonos encontrados |
| `emails` | Agregado de todos los emails encontrados |
| `social_links` | Agregado de todas las redes sociales |
| `whatsapp` | WhatsApp encontrado |
| `locations` | Agregado de todas las ubicaciones |
| `country` | País inferido |
| `prices` | Agregado de todos los precios |
| `purchase_links` | Agregado de todos los links de compra |
| `has_forms` | Si hay formularios en alguna página |
| `forms` | Agregado de todos los formularios |
| `business_category` | Categoría inferida |
| `has_captcha_or_block` | Si hubo bloqueos |
| `block_type` | Tipo de bloqueo |

### Flujo de crawling

1. Detectar sitemap.xml, robots.txt
2. Crawlear páginas principales: home, about, contact, productos/servicios
3. Límite configurable de páginas (default 5, max 20)
4. Respetar robots.txt
5. Timeout por página: 10s
6. No crawlear subdominios externos
7. Cache de URLs para no re-scrapear

### Seguridad ante fallos

- Timeout por página: 10s
- Límite de páginas configurable (default 5, max 20)
- Respetar robots.txt
- Si una página falla, continuar con la siguiente
- Si hay captcha/block → `has_captcha_or_block: True`, log, saltar
- Cache de URLs para no re-scrapear

### Tests

- `test_domain_enricher_sitemap`: detección de sitemap.xml
- `test_domain_enricher_robots_txt`: respeto de robots.txt
- `test_domain_enricher_multi_page`: crawling multi-página
- `test_domain_enricher_deduplication`: deduplicación de datos entre páginas
- `test_domain_enricher_real_domain` (--run-real): crawlea dominio real

---

## Etapa 4.5 — Orquestación, CLI y Serialización

### Objetivo

Integrar todos los enriquecedores en el pipeline, agregar flags CLI, actualizar serialización y documentación.

### Archivos a modificar

- `src/modules/meta_ads/acquisition/browser_runner.py` — integrar nuevos enriquecedores
- `scripts/run_meta_ads_browser.py` — nuevos flags CLI
- `src/modules/meta_ads/dto/browser_ad.py` — extender `BrowserAdResult`

### Flags CLI nuevos

| Flag | Descripción | Default |
|------|-------------|---------|
| `--enrich-social` | Activar social enrichment | `False` |
| `--enrich-landing` | Activar landing enrichment | `False` |
| `--enrich-domain` | Activar domain enrichment | `False` |
| `--enrich-all` | Activar todos los enriquecedores | `False` |
| `--enrich-landing-only` | Solo landing enrichment (modo standalone) | `False` |
| `--enrich-domain-only` | Solo domain enrichment (modo standalone) | `False` |
| `--enrich-social-only` | Solo social enrichment (modo standalone) | `False` |
| `--max-pages` | Máximo de páginas a crawlear en domain | `5` |
| `--enrich-timeout` | Timeout por página de enrichment (s) | `10` |

### Integración en el pipeline

Los enriquecedores se ejecutan después del enrichment de Meta Ads Library, en el mismo `MetaAdsBrowserRunner.run()`:

```python
def run(self, ...):
    # ... discovery + enrichment_library existente ...

    if self.enrich_social and self._has_social_users(results):
        social = SocialEnricher(page=page, proxy=proxy)
        for result in results:
            result.social_enrichment = social.enrich(result.enrichment_library)

    if self.enrich_landing:
        landing = LandingEnricher(proxy=proxy)
        for result in results:
            result.landing_enrichments = landing.enrich(result.discovery.landing_url)

    if self.enrich_domain:
        domain = DomainEnricher(proxy=proxy, max_pages=self.max_pages)
        for result in results:
            result.domain_enrichment = domain.enrich(result.discovery.domain)
```

### Condiciones de ejecución

- **Social enrichment**: solo si `enrichment_library` tiene `facebook_user` o `instagram_user`
- **Landing enrichment**: solo si `discovery.landing_url` existe
- **Domain enrichment**: solo si `discovery.domain` existe
- Cada enriquecedor puede fallar independientemente sin afectar a los demás

### Serialización

La serialización en `_save_checkpoint` y `_save_enrich_inplace` debe incluir los nuevos campos:

```python
def _serialize_result(self, r: BrowserAdResult) -> dict:
    disc = asdict(r.discovery)
    disc.pop("ad_snapshot_url", None)
    enrich = asdict(r.enrichment_library) if r.enrichment_library else None
    if enrich:
        enrich.pop("advertiser_info", None)
        enrich.pop("login_required", None)

    result = {"discovery": disc, "enrichment_library": enrich}

    if r.social_enrichment:
        result["social_enrichment"] = asdict(r.social_enrichment)
    if r.landing_enrichments:
        result["landing_enrichments"] = [asdict(le) for le in r.landing_enrichments]
    if r.domain_enrichment:
        result["domain_enrichment"] = asdict(r.domain_enrichment)

    return result
```

### Continuidad de ejecución (resume/append)

El sistema actual soporta dos modos de guardado:
1. **Split por keyword** (carpeta `_parts/` con un JSON por keyword + `index.json`)
2. **Archivo único** (un solo JSON con todos los resultados)

Para Fase 4, la serialización debe:

1. **Preservar datos existentes**: al cargar resultados previos (modo append/resume), los campos `enrichment_library`, `social_enrichment`, `landing_enrichments`, `domain_enrichment` se cargan y preservan
2. **No re-enriquecer**: si un resultado ya tiene `social_enrichment`, no se vuelve a enriquecer
3. **Enriquecimiento incremental**: se puede ejecutar `--enrich-social` sobre resultados que ya tienen `enrichment_library` pero no `social_enrichment`
4. **Split por keyword**: los nuevos campos se guardan en los mismos archivos partidos

### Continuidad de ejecución

El sistema actual soporta dos modos de guardado:

1. **Split por keyword** (carpeta `_parts/` con un JSON por keyword + `index.json`)
2. **Archivo único** (un solo JSON con todos los resultados)

Para Fase 4, la serialización debe:

1. **Preservar datos existentes**: al cargar resultados previos (modo append/resume), los campos `enrichment_library`, `social_enrichment`, `landing_enrichments`, `domain_enrichment` se cargan y preservan
2. **No re-enriquecer**: si un resultado ya tiene `social_enrichment`, no se vuelve a enriquecer
3. **Enriquecimiento incremental**: se puede ejecutar `--enrich-social` sobre resultados que ya tienen `enrichment_library` pero no `social_enrichment`
4. **Split por keyword**: los nuevos campos se guardan en los mismos archivos partidos

### Condiciones de ejecución

- **Social enrichment**: solo si `enrichment_library` tiene `facebook_user` o `instagram_user`
- **Landing enrichment**: solo si `discovery.landing_url` existe
- **Domain enrichment**: solo si `discovery.domain` existe
- Cada enriquecedor puede fallar independientemente sin afectar a los demás

### Proxy support

- Reutilizar `proxy_list` de Fase 3.2
- Cada enriquecedor acepta `proxy: str | None`
- Round-robin si hay múltiples proxies

### Tests

- `test_orchestrator_social_condition`: solo se ejecuta si hay enrichment_library
- `test_orchestrator_landing_condition`: solo se ejecuta si hay landing_url
- `test_orchestrator_domain_condition`: solo se ejecuta si hay domain
- `test_orchestrator_independent_failures`: fallo de un enriquecedor no afecta a otros
- `test_orchestrator_serialization`: serialización correcta de todos los campos
- `test_orchestrator_append_preserves`: modo append preserva datos existentes
- `test_orchestrator_incremental_enrich`: enriquecimiento incremental

---

## Tech Stack General

| Componente | Tecnología | Razón |
|-----------|-----------|-------|
| HTTP simple | `httpx` (sync) | Rápido, manejo de redirects, timeouts |
| JS-heavy | Playwright (reutilizar BrowserManager) | Misma base que Fase 3 |
| HTML parsing | `selectolax` | 10x más rápido que BeautifulSoup |
| Phone validation | `phonenumbers` | Google lib, detecta país por prefijo |
| Email extraction | regex | Simple y efectivo |
| Price extraction | regex + currency symbols | ARS, USD, EUR, BRL, etc. |
| Country detection | phonenumbers + ccTLD + lang + content | Pipeline multi-capa |

### Anti-ban strategy

| Técnica | Dónde se aplica |
|---------|-----------------|
| User-Agent realista | httpx + Playwright |
| Delays con jitter | Entre requests |
| Proxies rotativos | Reutilizar lógica de Fase 3.2 |
| Timeouts cortos | 10s landing, 15s social |
| Cache de URLs | No re-scrapear lo mismo |
| Graceful degradation | Cada enriquecedor es independiente |
| Sesiones separadas | Social ≠ Landing ≠ Domain |

### Login handling

```bash
# Opcionales, para social enrichment
export META_EMAIL="tu_email@ejemplo.com"
export META_PASSWORD="tu_password"
```

- Sesión separada de Playwright para social enrichment
- Si hay credenciales → intentar login en Instagram/Facebook
- Si no hay credenciales o login falla → modo público
- Si la cuenta se pierde (bloqueo/2FA) → desactivar social enrichment, log claro
- Las credenciales NUNCA se guardan en logs ni archivos
- El login se hace en una página/contexto aislado

### Seguridad ante fallos general

- Cada enriquecedor es independiente → si uno falla, los otros siguen
- Timeouts por página, no globales
- Si una landing falla (timeout, 403, etc.), se loguea y se pasa a la siguiente
- Si Instagram/Facebook requiere login, se loguea y se devuelve lo que se pueda
- Si el dominio no responde, se loguea y se continúa
- Cache de resultados para no re-procesar la misma URL
- Reintentos con backoff exponencial (1, 3, 5s)
- Si persiste el bloqueo → saltar ese dominio/landing/perfil

### Tests

- `test_orchestrator_social_condition`: solo se ejecuta si hay enrichment_library
- `test_orchestrator_landing_condition`: solo se ejecuta si hay landing_url
- `test_orchestrator_domain_condition`: solo se ejecuta si hay domain
- `test_orchestrator_independent_failures`: fallo de un enriquecedor no afecta a otros
- `test_orchestrator_serialization`: serialización correcta de todos los campos
- `test_orchestrator_append_preserves`: modo append preserva datos existentes
- `test_orchestrator_incremental_enrich`: enriquecimiento incremental
- `test_orchestrator_cli_flags`: flags CLI funcionan correctamente

---

## Tech Stack General

| Componente | Tecnología | Razón |
|-----------|-----------|-------|
| HTTP simple | `httpx` (sync) | Rápido, manejo de redirects, timeouts |
| JS-heavy | Playwright (reutilizar BrowserManager) | Misma base que Fase 3 |
| HTML parsing | `selectolax` | 10x más rápido que BeautifulSoup |
| Phone validation | `phonenumbers` | Google lib, detecta país por prefijo |
| Email extraction | regex | Simple y efectivo |
| Price extraction | regex + currency symbols | ARS, USD, EUR, BRL, etc. |
| Country detection | phonenumbers + ccTLD + lang + content | Pipeline multi-capa |

### Anti-ban strategy

| Técnica | Dónde se aplica |
|---------|-----------------|
| User-Agent realista | httpx + Playwright |
| Delays con jitter | Entre requests |
| Proxies rotativos | Reutilizar lógica de Fase 3.2 |
| Timeouts cortos | 10s landing, 15s social |
| Cache de URLs | No re-scrapear lo mismo |
| Graceful degradation | Cada enriquecedor es independiente |
| Sesiones separadas | Social ≠ Landing ≠ Domain |

### Login handling

```bash
# Opcionales, para social enrichment
export META_EMAIL="tu_email@ejemplo.com"
export META_PASSWORD="tu_password"
```

- Sesión separada de Playwright para social enrichment
- Si hay credenciales → intentar login en Instagram/Facebook
- Si no hay credenciales o login falla → modo público
- Si la cuenta se pierde (bloqueo/2FA) → desactivar social enrichment, log claro
- Las credenciales NUNCA se guardan en logs ni archivos
- El login se hace en una página/contexto aislado

### Seguridad ante fallos general

- Cada enriquecedor es independiente → si uno falla, los otros siguen
- Timeouts por página, no globales
- Si una landing falla (timeout, 403, etc.), se loguea y se pasa a la siguiente
- Si Instagram/Facebook requiere login y no hay credenciales → modo público
- Si el dominio no responde, se loguea y se continúa
- Cache de resultados para no re-procesar la misma URL
- Reintentos con backoff exponencial (1, 3, 5s)
- Si persiste el bloqueo → saltar ese dominio/landing/perfil

### Tests reales (--run-real)

Los tests reales se ejecutan durante desarrollo con `--run-real`:

```bash
pytest tests/ -v --run-real
```

Cada test real:
1. Navega a una URL real conocida
2. Toma screenshot automático en `output/tests/{test_name}/{timestamp}.png`
3. Verifica que extrajo los datos esperados
4. Muestra resultados en CLI
5. Guarda errores en `output/tests/{test_name}/errors.json`

Los tests reales NO bloquean CI. Se ejecutan solo cuando se pasa `--run-real`.

---

## Criterios de Aceptación Generales

- `./scripts/check.sh` pasa sin errores
- Todos los DTOs nuevos tienen tests unitarios
- Cada enriquecedor tiene tests de extracción con datos mockeados
- Los tests reales (`--run-real`) funcionan contra URLs reales
- La serialización JSON incluye todos los campos nuevos
- El modo append preserva los datos de enrichment existentes
- El enriquecimiento incremental no re-procesa datos ya existentes
- Cada enriquecedor puede fallar independientemente
- Los flags CLI funcionan correctamente
- La documentación está actualizada

---

## Criterios de Aceptación por Etapa

### Etapa 4.1
- [ ] DTOs nuevos creados con todos los campos especificados
- [ ] `BrowserAdResult` extendido con `enrichment_library`, `social_enrichment`, `landing_enrichments`, `domain_enrichment`
- [ ] `enrichment` renombrado a `enrichment_library` en toda la base de código
- [ ] Serialización JSON incluye todos los campos nuevos
- [ ] Tests de DTOs pasan

### Etapa 4.2
- [ ] `SocialEnricher` extrae todos los campos del perfil
- [ ] Maneja bio_links y links section
- [ ] Detecta teléfono/email como botones
- [ ] Funciona en modo público sin login
- [ ] Login opcional con env vars
- [ ] Graceful degradation si falla
- [ ] Tests unitarios + tests reales pasan

### Etapa 4.3
- [ ] `LandingEnricher` extrae todos los campos especificados
- [ ] Country detection pipeline funciona
- [ ] Business categorization funciona
- [ ] Form detection funciona
- [ ] Cloudflare/captcha detection funciona
- [ ] Graceful degradation si falla
- [ ] Tests unitarios + tests reales pasan

### Etapa 4.4
- [ ] `DomainEnricher` crawlea múltiples páginas del dominio
- [ ] Límite de páginas configurable
- [ ] Respeto de robots.txt
- [ ] Deduplicación de datos entre páginas
- [ ] Graceful degradation si falla
- [ ] Tests unitarios + tests reales pasan

### Etapa 4.5
- [ ] Flags CLI funcionan correctamente
- [ ] Serialización incluye todos los campos nuevos
- [ ] Modo append preserva datos existentes
- [ ] Enriquecimiento incremental no re-procesa datos existentes
- [ ] Cada enriquecedor puede fallar independientemente
- [ ] `./scripts/check.sh` pasa

---

## Cómo se ejecuta

### Discovery + Enrichment completo (todas las etapas)

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --headless --enrich-all
```

### Discovery + Enrichment Library + Social

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --keyword "curso:30" --headless --enrich-social
```

### Solo Landing Enrichment sobre resultados existentes

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --enrich-landing-only output/resultados.json --headless
```

### Enriquecimiento incremental (agregar social a resultados existentes)

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --enrich-social-only output/resultados.json --headless
```

---

## Cómo se prueba

### Tests unitarios (siempre)

```bash
./scripts/test.sh
```

### Tests reales (desarrollo, con URLs reales)

```bash
pytest tests/ -v --run-real
```

Los tests reales:
1. Navegan a URLs reales conocidas
2. Toman screenshots automáticos en `output/tests/{test_name}/{timestamp}.png`
3. Verifican que extrajeron los datos esperados
4. Muestran resultados en CLI
5. Guardan errores en `output/tests/{test_name}/errors.json`

### Tests de extracción

```bash
pytest tests/unit/test_landing_enricher.py -v
pytest tests/unit/test_social_enricher.py -v
pytest tests/unit/test_domain_enricher.py -v
```

---

## Logs esperados

### Social Enrichment

```
SocialEnricher: enriqueciendo facebook_user=weyaacademy
SocialEnricher: perfil encontrado display_name="Weya Academy" followers=1234
SocialEnricher: bio_links encontrados: 1
SocialEnricher: phone no disponible (modo público)
SocialEnricher: enrichment completado facebook_user=weyaacademy en 3.2s
```

### Landing Enrichment

```
LandingEnricher: scrapeando https://weya.academy
LandingEnricher: phones encontrados: 1
LandingEnricher: emails encontrados: 1
LandingEnricher: social_links encontrados: 2
LandingEnricher: country detectado: AR (via phone prefix)
LandingEnricher: business_category: infoproductor
LandingEnricher: enrichment completado en 2.1s
```

### Domain Enrichment

```
DomainEnricher: crawleando dominio weya.academy
DomainEnricher: sitemap.xml encontrado con 12 URLs
DomainEnricher: páginas scrapeadas: 5/5
DomainEnricher: phones encontrados: 2
DomainEnricher: emails encontrados: 3
DomainEnricher: enrichment completado en 8.5s
```

### Bloqueo/Captcha

```
LandingEnricher: bloqueo detectado en https://ejemplo.com: cloudflare
LandingEnricher: reintento 1/3...
LandingEnricher: bloqueo persiste, saltando dominio
```

---

## Criterios de Aceptación

- `./scripts/check.sh` pasa sin errores
- Todos los DTOs nuevos tienen tests unitarios
- Cada enriquecedor tiene tests de extracción con datos mockeados
- Los tests reales (`--run-real`) funcionan contra URLs reales
- La serialización JSON incluye todos los campos nuevos
- El modo append preserva los datos de enrichment existentes
- El enriquecimiento incremental no re-procesa datos ya existentes
- Cada enriquecedor puede fallar independientemente
- Los flags CLI funcionan correctamente
- La documentación está actualizada

---

## Resultado Final

Completar al cerrar la fase con lo implementado realmente.
