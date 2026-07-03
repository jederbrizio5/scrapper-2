# Registro de Decisiones de Arquitectura (ADRs)

*El formato para nuevas decisiones debe ser:*
- **Fecha**: YYYY-MM-DD
- **Contexto**: ¿Cuál es el problema?
- **Decisión**: ¿Qué se decidió?
- **Consecuencias**: ¿Qué implicaciones tiene?

---

## 2024-XX-XX: Bootstrap del Proyecto
- **Contexto**: Se requería crear la estructura base para el sistema de prospección de Meta Ads que sea modular, testeable y preparada para ser extendida en fases.
- **Decisión**: Crear una arquitectura limpia con separación de responsabilidades (core, modules, services, config) y uso de scripts shell para la gestión de dependencias y ejecución de tareas.
- **Consecuencias**: Se estandarizan los comandos de ejecución (test, lint, format) a través de los scripts unificados.

## 2024-XX-XX: Implementación de Infraestructura de Datos (Fase 1)
- **Contexto**: Necesidad de establecer una capa de persistencia escalable, modular y tipada antes de abordar el scraper.
- **Decisión**: Utilizar SQLAlchemy 2.x por sus características mejoradas de tipado estático (`Mapped`), SQLite (fácil de integrar y transportar), Alembic (para migraciones limpias y atómicas) y el patrón Repositorio para encapsular la capa de persistencia fuera de la lógica de dominio o servicios.
- **Consecuencias**: Se facilita el testing con bases de datos en memoria y se desacoplan los objetos ORM del resto del código, lo que prevendrá bloqueos a futuro cuando la base de datos se mueva a un proveedor en la nube o migre de motor (ej. a PostgreSQL).

## 2024-XX-XX: SDK Interno de Cliente Meta Ads (Fase 2)
- **Contexto**: La extracción de información de Meta es una de las fuentes core de datos. Necesitábamos interactuar con Meta sin acoplar esa lógica de extracción a Playwright, a la persistencia o a la lógica de negocio general del crawler masivo.
- **Decisión**: Se encapsuló toda interacción con la API de Meta Ads Library en un SDK interno (`src/modules/meta_ads/client`). Este cliente implementa un patrón "Gateway" puro, devolviendo exclusivamente DTOs (`Data Transfer Objects`) inmutables, lo que aísla de dependencias externas. Se configuró todo por variables de entorno y se usó `responses` para mockear tests de red.
- **Consecuencias**: Otros módulos pueden depender de DTOs seguros sin preocuparse de si provienen de la Graph API, un mock o de un scraping por HTML. La separación obliga al sistema orquestador a encargarse de pedir la data a MetaClient y persistirla a través del Repositorio.

## 2026-06-29: Estabilizacion previa a Fase 3
- **Contexto**: El proyecto necesitaba quedar funcional antes de avanzar con extraccion de dominios. Los tests fallaban por un repositorio faltante y la documentacion contenia referencias desalineadas o contenido mezclado.
- **Decisión**: Se agrego `CompanyRepository`, se dejo `src/models/__init__.py` para registrar modelos en Alembic, se declaro `responses` como dependencia de desarrollo, se limpio el manual maestro y se agrego una guia de trabajo para agentes.
- **Consecuencias**: La base queda preparada para que futuros agentes puedan leer `README.md` y `docs/` y continuar por fases sin asumir funcionalidades inexistentes.

## 2026-06-29: Priorizar adquisicion por navegador
- **Contexto**: La API de Meta Ads Library no cubre de forma suficiente el caso comercial buscado y puede estar limitada a anuncios politicos o categorias especiales.
- **Decisión**: Mantener el cliente API como componente secundario, testeado y desacoplado, pero orientar Fase 3 a adquisicion por navegador con Playwright.
- **Consecuencias**: Fase 3 debe enfocarse en seguridad operativa, tiempos configurables, logs, modo visible/headless y extraccion robusta desde DOM.

## 2026-06-29: Documentacion obligatoria por fase
- **Contexto**: El proyecto sera trabajado por multiples agentes y necesita trazabilidad clara.
- **Decisión**: Crear `docs/phases/` con una plantilla y archivos por fase. Cada fase debe documentar objetivo, alcance, pruebas, logs esperados, ejecucion y resultado final.
- **Consecuencias**: Un agente nuevo puede continuar leyendo la fase correspondiente sin depender del historial del chat anterior.

## 2026-06-29: Implementacion completa de Fase 3
- **Contexto**: La Fase 3 requiere adquisicion robusta por navegador con verificacion de sesion, modo debug y estructura JSON documentada.
- **Decisión**: Implementar SessionManager con verificacion de sesion y espera de login, BrowserManager con soporte para modo debug (navegador visible, slow motion, logs detallados), y serializador JSON que produzca exactamente la estructura documentada eliminando campos adicionales.
- **Consecuencias**: La fase queda completa con todos los criterios de aceptacion cumplidos: verificacion de sesion, discovery, enrichment, modo debug, modo headless, y 20 tests pasando.

## 2026-06-30: Eliminar dependencia de sesion de Facebook
- **Contexto**: Meta Ads Library funciona sin sesión de Facebook para descubrimiento y enriquecimiento de anuncios. La lógica de login agregaba complejidad innecesaria y requería intervención manual del usuario.
- **Decisión**: Eliminar `ensure_session()`, `wait_for_login()` y timeout de login de SessionManager. Simplificar a creación de contexto/página. Eliminar parámetro `--login-timeout` del script CLI.
- **Consecuencias**: Ejecución sin intervención humana. Eliminación de 4 tests unitarios obsoletos. Simplificación del flujo de ejecución.

## 2026-06-30: Enrichment desde texto del diálogo no desde links
- **Contexto**: Los links en el diálogo de detalles no son confiables para extraer usuarios sociales. La sección "Información sobre el anunciante" muestra el texto correcto con `@username`, `Identificador:` y conteos de seguidores.
- **Decisión**: Reescribir extracción de enrichment para parsear el texto del diálogo expandido en lugar de buscar links. Facebook se detecta primero (`@username` o `Identificador: N`), Instagram segundo (`@username`). Los seguidores se parsean con soporte para "mil" (ej. "2,1 mil" → 2100).
- **Consecuencias**: Extracción confiable de usuarios sociales y seguidores. Mejora significativa en la tasa de enriquecimiento exitoso.

## 2026-06-30: Descripción completa sin truncamiento
- **Contexto**: El truncamiento de la descripción a 2000 caracteres perdía información valiosa del contenido del anuncio.
- **Decisión**: Eliminar límite de 2000 caracteres en `_extract_ad_description`. Devolver texto completo del anuncio.
- **Consecuencias**: Descripciones más largas en el JSON de salida. Información completa del anuncio disponible para procesamiento posterior.

## 2026-06-30: ad_library_url construida correctamente
- **Contexto**: La URL del anuncio se estaba copiando de la página en lugar de construirse con el library_id.
- **Decisión**: Construir `ad_library_url` como `https://www.facebook.com/ads/library/?id={library_id}` en lugar de copiar la URL de la página.
- **Consecuencias**: URLs de anuncios correctas y consistentes en todos los resultados.

## 2026-06-30: Manejo de "Ver detalles del resumen"
- **Contexto**: Algunos anuncios muestran un diálogo de resumen que requiere un clic adicional en "Ver detalles del anuncio" para acceder a la información completa del anunciante.
- **Decisión**: Implementar `_enter_from_summary()` que detecta el diálogo de resumen, clickea "Ver detalles del anuncio" interno, y busca el diálogo de detalles resultante. Se excluye el diálogo de resumen de la búsqueda posterior para evitar confusión.
- **Consecuencias**: Enriquecimiento exitoso para anuncios que muestran resumen en lugar de detalles directos.

## 2026-07-01: Anti-bloqueo con User-Agent, webdriver override y jitter
- **Contexto**: Meta Ads Library detecta automatización por `navigator.webdriver`, User-Agent de Playwright por defecto, viewport fijo y patrones de interacción determinísticos.
- **Decisión**: Agregar `REALISTIC_USER_AGENT` (Chrome 125 Windows), `--disable-blink-features=AutomationControlled` en args, `add_init_script` con override de `navigator.webdriver`/`plugins`/`languages`/`chrome.runtime`, viewport ±20px, extra HTTP headers, y `_jittered_delay()` con ±30% en todos los `wait_for_timeout`.
- **Consecuencias**: Menor probabilidad de bloqueo por Meta. Sin cambios estructurales en el flujo de extracción.

## 2026-07-01: `_parse_followers_count` con float math en vez de string concat
- **Contexto**: "275,7 mil" se parseaba como "2757" + "000" = "2757000" en vez de `275.7 * 1000 = 275700`. La coma decimal se ignoraba.
- **Decisión**: Reescribir `_parse_followers_count` para usar `float()` con coma→punto, eliminar separador de miles (punto seguido de 3 dígitos), y multiplicar por factor 1000/1000000.
- **Consecuencias**: "275,7 mil" → 275700, "1,4 mill" → 1400000, "1.473 mil" → 1473000.

## 2026-07-01: Advertiser name con backward search
- **Contexto**: `_extract_advertiser_name` buscaba líneas después del library ID, lo que seleccionaba "Transparencia de la UE" o "X anuncios usan este contenido" como nombre del anunciante.
- **Decisión**: Primero buscar hacia atrás desde el library ID (el nombre real está antes), luego fallback forward. Agregar "Transparencia" a `skip_prefixes`. Agregar `_is_valid_name()` con check de "anuncios usan este contenido".
- **Consecuencias**: Nombres de anunciante correctos en todos los casos observados.

## 2026-07-01: Engagement CTA detection sobre todos los anchors
- **Contexto**: Anuncios con CTA a WhatsApp tenían landing URL de texto secundario. El ad se aceptaba incorrectamente.
- **Decisión**: En `_extract_landing_url`, escanear TODOS los `<a href>` de la card para patrones `wa.me`/`whatsapp.com`/`m.me`/`tel:`. Si existe alguno, return None. Además, priorizar `<a>` dentro de botones CTA antes que cualquier otro anchor. Solo hacer fallback a texto si no hay botones.
- **Consecuencias**: Anuncios WhatsApp son descartados. Landing URLs vienen de botones CTA no de texto.

## 2026-07-01: BREAK en descripción al detectar URL/display/oferta
- **Contexto**: La descripción incluía display URLs como "CEFOMIN.CL", URLs con emoji como "📌 http://...", y ofertas como "15% OFF" del footer del card.
- **Decisión**: Agregar `_DISPLAY_URL_RE` (mayúsculas + punto) con BREAK, `_contains_url()` que detecta http/www incluso con prefijo emoji con BREAK, y `\d+% (OFF|desc)` con BREAK. Case-insensitive para "HTTPS://...".
- **Consecuencias**: Descripciones sin footer del card. Corta en la primera línea de footer, sin arrastrar contenido posterior.

## 2026-07-01: UI_NOISE_LINES expandido
- **Contexto**: Textos de botones como "Chatea con nosotros", "Send WhatsApp Message", "Visita el sitio web" aparecían en la descripción.
- **Decisión**: Agregar ~10 líneas nuevas a `UI_NOISE_LINES`: "Chatea con nosotros", "Send WhatsApp Message", "Visita el sitio web", "Registrarse", "Sign Up", "Shop Now", "Learn More", "See Details", "Comprar", "Reserva tu plaza", "Contact Us".
- **Consecuencias**: Descripciones más limpias sin texto de botones de interfaz.

## 2026-07-01: doc.phase.3.md — documento de algoritmo para IA
- **Contexto**: No existía documentación detallada del algoritmo de adquisición para que otra IA pueda entender y continuar el desarrollo.
- **Decisión**: Crear `docs/doc.phase.3.md` con 14 secciones: arquitectura completa, anti-detección, flujos de discovery y enrichment, 12 errores corregidos, limitaciones, decisiones de diseño, diagramas de flujo.
- **Consecuencias**: Cualquier agente futuro puede comprender el sistema sin leer el código fuente completo.

## 2026-07-02: Sesión nueva por keyword (prevención OOM)
- **Contexto**: El navegador acumulaba DOM de todas las keywords en una sola página/sesión, llevando a OOM (Out of Memory) en ejecuciones largas. Además, la EPIPE observada en logs era en realidad SIGTERM del tool bash por timeout, no del navegador.
- **Decisión**: Crear un nuevo contexto + página por cada keyword. Cerrar el contexto anterior antes de abrir el siguiente. Agregar try/except alrededor de cleanup para evitar que errores menores detengan el proceso. Mantener una sola sesión de navegador (chromium) reutilizable entre keywords.
- **Consecuencias**: Ejecuciones estables con 4+ keywords. Sin acumulación de DOM. La EPIPE real solo ocurre por timeouts externos (tool bash), no en producción.

## 2026-07-02: Skip library_ids en extractor antes de query_selector_all
- **Contexto**: Entre scrolls, las cards ya vistas se reprocesaban completamente (`_extract_discovery_from_card` con query_selector_all costoso). Esto desperdiciaba tiempo y recursos.
- **Decisión**: Extraer el library_id del texto de la card ANTES de llamar a `_extract_discovery_from_card`. Si el library_id ya está en el set `skip_library_ids`, se salta la card inmediatamente. Pasar `skip_library_ids` de la iteración anterior en cada nueva extracción.
- **Consecuencias**: Reducción drástica de reprocesamiento entre scrolls. Stat `disc_library_id_dup` eliminado (ahora siempre 0). Mejora de rendimiento en keywords con muchos anuncios.

## 2026-07-02: Per-keyword limits con `keyword:limite`
- **Contexto**: El límite global se aplicaba a todas las keywords por igual, sin posibilidad de asignar más recursos a keywords prioritarias.
- **Decisión**: Implementar sintaxis `--keyword "nombre:limite"` en CLI. El runner parsea con `rsplit(":", 1)`. Si no hay límite explícito, usa el global (`--limit`). Cada keyword se procesa con su propio límite en `_collect_discoveries_with_scroll`.
- **Consecuencias**: Control granular de la adquisición. Ej: `--keyword "curso:30" --keyword "curso marketing:100"`.

## 2026-07-02: max_scrolls=0 como scrolls infinitos
- **Contexto**: El límite de scrolls forzaba a calcular un número fijo que podía ser insuficiente para keywords con muchos anuncios o excesivo para otras.
- **Decisión**: Si `max_scroll_attempts == 0`, el while loop de scrolls solo corta por objetivo alcanzado o por 3 scrolls vacíos consecutivos. El número fijo es solo un seguro de fondo.
- **Consecuencias**: Una keyword con 100 anuncios objetivos puede scrollear hasta conseguirlos sin necesidad de adivinar el número de scrolls. Corte natural por agotamiento de resultados.

## 2026-07-02: Checkpoint por keyword + signal handler
- **Contexto**: Si el proceso moría (Ctrl+C, kill, timeout), se perdían todos los discoveries y enrichments de keywords ya completadas.
- **Decisión**: Implementar `_save_checkpoint()` que serializa y escribe el JSON completo después de cada keyword. Registrar signal handler para SIGINT y SIGTERM que guarda checkpoint antes de salir. El archivo se reescribe completo (no append de líneas) para consistencia.
- **Consecuencias**: Máxima pérdida de ~30s si el proceso muere durante una keyword. Datos de keywords completadas siempre a salvo.

## 2026-07-02: Modo enrich-only desde archivo JSON
- **Contexto**: A veces solo se necesita enriquecer discoveries ya extraídos sin volver a scrollear y descubrir.
- **Decisión**: Implementar `enrich_from_file(input_path, output_path)` en runner. Lee JSON con discoveries, navega a `ad_library_url` de cada uno, extrae enrichment, guarda resultados. CLI con `--enrich-only <archivo.json>`.
- **Consecuencias**: Separación clara entre discovery (costoso, requiere scroll) y enrichment (rápido, solo abrir detalles). Se puede hacer discovery una vez y enrichment múltiples veces.

## 2026-07-02: Modo append para retomar ejecuciones
- **Contexto**: No existía manera de continuar una ejecución anterior. Si se cortaba, había que empezar de cero.
- **Decisión**: Implementar `--mode append` que carga dominios y library_ids del archivo existente antes de comenzar. `--resume <archivo>` carga de un archivo externo. Ambos sets se combinan como conocidos antes de la primera keyword.
- **Consecuencias**: Ejecución retomable. Si se agregaron 30 dominios de "curso" y se cortó, al retomar no se repiten esos dominios. También sirve para bloquear dominios de campañas previas (dedup cross-ejecución).

## 2026-07-02: Filtros publisher_platforms + sort_mode probados efectivos
- **Contexto**: Sin filtros, Meta Ads Library devolvía pocos anuncios con landing externa (~7 dominios únicos para "curso").
- **Decisión**: Fijar `publisher_platforms=(facebook,instagram)` y `sort_mode=total_impressions` como defaults. Exponer `--sort-mode` en CLI. Mantener `--publisher-platforms` oculto (no cambiar sin evidencia).
- **Consecuencias**: "curso" pasó de 7 a 30 dominios únicos (4.3x mejora). Los filtros son críticos para densidad de landings.

## 2026-07-02: Bloqueo de dominios extra por CLI
- **Contexto**: Los dominios bloqueados (`BLOCKED_DOMAINS`) son fijos en la clase. No hay manera de agregar dominios específicos de una campaña sin modificar el código.
- **Decisión**: Agregar `extra_blocked_domains: set[str] | None = None` a `AdsExtractor.__init__`. Internamente construye `self._blocked_domains = tuple(sorted(set(BLOCKED_DOMAINS) | extra))`. CLI con `--blocked-domains "tiktok.com,x.com"`.
- **Consecuencias**: Bloqueo ad-hoc sin modificar código fuente. Ideal para campañas que compiten con dominios específicos.

## 2026-07-02: Dialog priority — "Detalles del anuncio" > "Vincular con un anuncio"
- **Contexto**: `_find_detail_dialog()` devolvía `dialog[1]` ("Vincular con un anuncio") porque también contiene el texto "Detalles del anuncio" (del botón "Ver detalles del anuncio"). El dialog correcto es `dialog[2]` ("Detalles del anuncio"), el único con sección "Información sobre el anunciante". La posición DOM no era confiable.
- **Decisión**: `_find_detail_dialog()` busca dialogs con "Detalles del anuncio"/"Ad details"/"Información sobre el anunciante" y **excluye** los que contengan "Vincular con un anuncio"/"Link to an ad". La selección se basa en **contenido**, no en posición DOM. Si no hay match, fallback al dialog "Vincular".
- **Consecuencias**: Enrichment exitoso para todos los ads. Dialog correcto se elige consistentemente incluso si Meta cambia el orden DOM.

## 2026-07-02: `_native_click()` via JS evaluate en vez de `force=True`
- **Contexto**: Los clicks con `btn.click(force=True)` de Playwright no disparaban los handlers de React en Facebook. Los botones de Meta son `<div>` con listeners JS, y `force=True` omite verificaciones de actionability pero no ejecuta el evento JS correcto.
- **Decisión**: Reemplazar todos los `click(force=True)` por `page.evaluate('el => el.click()')` envuelto en `_native_click()`. Aplicado en `_extract_enrichment_from_card`, `_click_inner_detail_button`, `_enter_from_summary`, `_click_advertiser_heading`.
- **Consecuencias**: Clicks funcionan correctamente en elementos React. Enrichment exitoso para ads donde antes no se abría el diálogo o no se expandía la sección del anunciante.

## 2026-07-02: `_expand_summaries()` para resúmenes coleccionables
- **Contexto**: Algunos anuncios tienen un botón "Ver detalles del resumen"/"Ver resumen" que expande ~5 sub-cards adicionales con library IDs propios. Sin clickearlos, se perdían esos ads.
- **Decisión**: Implementar `_expand_summaries()` que busca TODOS los botones con texto "Ver detalles del resumen"/"Ver resumen" y les hace click via `_native_click()`. Se llama en `extract_discovery_ads` antes de `_candidate_cards()` cada scroll. No se clickea "Ver más"/"See more" porque expanden descripciones, no resúmenes.
- **Consecuencias**: ~5 ads adicionales por resumen expandido. Mayor cobertura de discovery. Dedup por dominio evita duplicados de sub-cards.
