# Fase 3: Adquisición por Navegador y Extracción Inicial

## Estado

Completada.

---

# Objetivo

Implementar una adquisición robusta de anuncios desde Meta Ads Library utilizando Playwright.

La API oficial de Meta no cubre las necesidades del proyecto, por lo que esta fase obtiene anuncios reales directamente desde la interfaz web sin requerir sesión de Facebook.

La fase se divide en dos procesos completamente independientes:

- Discovery
- Enrichment

---

# Alcance

Durante esta fase se implementa:

- Gestión del navegador (headless/debug/slow_mo).
- Búsqueda por keywords en Meta Ads Library.
- Descubrimiento de anuncios con landing externa.
- Enriquecimiento de anuncios (usuarios sociales, seguidores).
- Generación del JSON de salida.

No se implementa almacenamiento definitivo ni procesamiento posterior.

---

# Discovery

## Objetivo

Discovery obtiene únicamente la información visible desde el listado de resultados de Meta Ads Library.

No abre detalles para obtener información adicional.

## Datos obtenidos

Para cada anuncio válido se obtiene:

- `keyword`
- `library_id`
- `description` (texto completo del anuncio, sin truncamiento)
- `circulation_start`
- `landing_url`
- `domain`
- `ad_library_url` (construida como `https://www.facebook.com/ads/library/?id={library_id}`)
- `advertiser_name`

## Reglas

La descripción corresponde únicamente al contenido del anuncio.

No incluye textos de la interfaz de Meta (Publicidad, impresiones, Transparencia UE, etc.).

El `advertiser_name` se extrae del card y se filtran:
- Prefijos `www.`
- Dominios sociales (`facebook.com`, `fb.com`, `wa.me`, `instagram.com`, etc.)
- Líneas de ruido ("2 anuncios usan este contenido", "Ir al perfil", etc.)

---

# Enrichment

## Objetivo

Enrichment trabaja sobre los anuncios obtenidos por Discovery.

Abre el detalle del anuncio y obtiene información adicional del anunciante desde la sección "Información sobre el anunciante".

## Datos obtenidos

- `library_id`
- `facebook_user` (username o ID numérico)
- `instagram_user`
- `facebook_followers`
- `instagram_followers`

Si alguno de estos datos no está disponible se devuelve `null`.

## Flujo de extracción

1. Click en "Ver detalles del anuncio" o "Ver más" en el card
2. Se busca el diálogo de detalles que contenga "Detalles del anuncio"
3. Se maneja el caso "Ver detalles del resumen" (diálogo intermedio)
4. Se busca y clickea el heading "Información sobre el anunciante"
5. Se parsea el texto del diálogo expandido

## Extracción de usuarios sociales

Los datos se leen del texto del diálogo, no de links:

- **Facebook**: Detectado primero — ya sea `@username` o `Identificador: N` (ID numérico)
- **Instagram**: Detectado segundo — `@username` después de Facebook

El orden en el diálogo es siempre: Facebook primero, Instagram segundo.

## Extracción de seguidores

Los conteos de seguidores se parsean del texto:
- "1260 seguidores" → `1260`
- "2,1 mil seguidores" → `2100`
- "229,4 mil seguidores" → `229400`
- "1.473 mil seguidores" → `1473000`

El primer conteo corresponde a Facebook, el segundo a Instagram.

---

# No se requiere sesión

Meta Ads Library funciona sin sesión de Facebook para descubrimiento y enriquecimiento de anuncios.

`SessionManager` se ha simplificado a creación de contexto/página sin lógica de login.

---

# Modo Debug

- Navegador visible.
- Ejecución lenta configurable (`--slow-mo`).
- Logs detallados de cada paso.
- Visualización de selectores utilizados.

---

# Modo Normal

Ejecución headless procesando múltiples keywords con límite de anuncios válidos.

---

# Salida JSON

```json
{
  "discovery": {
    "keyword": "curso",
    "library_id": "998522296404709",
    "description": "Texto completo del anuncio...",
    "circulation_start": "En circulación desde el 29 jun. 2026",
    "landing_url": "https://ejemplo.com/producto",
    "domain": "ejemplo.com",
    "ad_library_url": "https://www.facebook.com/ads/library/?id=998522296404709",
    "advertiser_name": "Nombre del Anunciante"
  },
  "enrichment": {
    "library_id": "998522296404709",
    "facebook_user": "142980128905510",
    "instagram_user": "weyaacademy",
    "facebook_followers": "169",
    "instagram_followers": "1971"
  }
}
```

---

# Criterios de aceptación

- Discovery obtiene anuncios reales desde Meta Ads Library.
- Los textos extraídos no contienen elementos de UI de Meta.
- Los anuncios inválidos son descartados automáticamente.
- Enrichment extrae usuarios sociales (FB/IG) y seguidores.
- El `ad_library_url` se construye correctamente.
- El `advertiser_name` no contiene dominios o ruido.
- La descripción incluye el texto completo del anuncio.
- Existe modo Debug y modo Headless.
- `./scripts/check.sh` pasa (20 tests).

---

# Componentes Implementados

## BrowserManager (`src/modules/meta_ads/browser/browser_manager.py`)

- Soporte para modo debug con navegador visible
- Slow motion configurable
- Argumento `--disable-blink-features=AutomationControlled`
- Logs detallados en modo debug

## SessionManager (`src/modules/meta_ads/browser/session_manager.py`)

- Creación de contexto y página
- Sin lógica de login (no requerido)

## AdsSearcher (`src/modules/meta_ads/acquisition/ads_searcher.py`)

- Construcción de URL de búsqueda con filtros
- Navegación a Meta Ads Library
- Espera de resultados

## AdsExtractor (`src/modules/meta_ads/acquisition/ads_extractor.py`)

- Extracción de discovery desde cards
- Extracción de enrichment desde diálogo de detalles
- Parsing de usuarios sociales (FB/IG)
- Parsing de seguidores con soporte "mil"
- Manejo de "Ver detalles del resumen"
- Filtrado de dominios bloqueados
- Extracción de advertiser_name limpia

## MetaAdsBrowserRunner (`src/modules/meta_ads/acquisition/browser_runner.py`)

- Orquestación de discovery y enrichment
- Scroll para paginación
- Deduplicación por library_id
- Modo headless/debug/slow_mo

## DTOs (`src/modules/meta_ads/dto/browser_ad.py`)

- `BrowserAdDiscovery`: datos de descubrimiento
- `BrowserAdEnrichment`: datos de enriquecimiento (con `advertiser_info`)
- `BrowserAdResult`: resultado combinado con serialización JSON

## Script de Ejecución (`scripts/run_meta_ads_browser.py`)

- Argumentos: `--keyword`, `--limit`, `--headless`, `--debug`, `--slow-mo`, `--action-delay-ms`, `--enrich`, `--no-enrich`
- Serialización JSON conforme a estructura documentada

---

# Tests

20 tests pasan exitosamente:

- `test_browser_manager_debug_mode`: configuración de modo debug
- `test_browser_ad_result_serialization`: estructura de resultados
- `test_browser_ad_result_with_enrichment`: serialización con enrichment
- `test_browser_ad_result_without_enrichment`: serialización sin enrichment
- `test_browser_ad_discovery_all_fields`: campos de discovery
- `test_browser_ad_enrichment_all_fields`: campos de enrichment
- `test_browser_ad_enrichment_partial`: enrichment parcial
- `test_browser_ad_discovery_optional_fields`: campos opcionales
- `test_browser_runner_headless`: runner en modo headless
- `test_browser_runner_debug`: runner en modo debug
- `test_browser_runner_slow_mo`: runner con slow motion
- `test_browser_runner_action_delay`: runner con delay
- `test_browser_runner_enrich_enabled`: runner con enrichment
- `test_browser_runner_enrich_disabled`: runner sin enrichment
- `test_browser_runner_multiple_keywords`: runner con múltiples keywords
- `test_browser_runner_limit`: runner con límite
- `test_browser_runner_headless_and_debug`: headless + debug
- `test_browser_runner_custom_action_delay`: delay personalizado
- `test_browser_runner_default_action_delay`: delay por defecto
- `test_ads_extractor_enrichment_reads_social_users`: enriquecimiento de usuarios sociales

---

# Ejecución

### Normal (Headless)

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --keyword "curso" --keyword "marketing" --limit 3 --headless
```

### Debug (Navegador Visible)

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --keyword "curso" --limit 2 --debug --slow-mo 300
```

### Sin Enriquecimiento

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py \
  --keyword "curso" --limit 3 --headless --no-enrich
```

---

# Resultado Final

La fase se ha completado con éxito. Todos los criterios de aceptación se cumplen:

1. **Discovery**: Obtiene anuncios reales desde Meta Ads Library sin sesión
2. **Limpieza de textos**: Descripciones sin elementos de UI de Meta
3. **Filtrado automático**: Anuncios inválidos descartados (sin landing, dominios bloqueados)
4. **Enrichment**: Extrae usuarios sociales FB/IG y seguidores desde el diálogo de detalles
5. **Manejo de resumen**: Soporte para "Ver detalles del resumen"
6. **ad_library_url**: Construida correctamente con library_id
7. **advertiser_name**: Limpia de dominios y ruido
8. **Descripción completa**: Sin truncamiento
9. **JSON válido**: Estructura exacta conforme a documentación
10. **Modo Debug**: Navegador visible, ejecución lenta, logs detallados
11. **Modo Headless**: Ejecución normal sin intervención visual
12. **Tests**: 20 tests pasan exitosamente, `./scripts/check.sh` sin errores
