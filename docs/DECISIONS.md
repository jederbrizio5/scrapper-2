# Registro de Decisiones de Arquitectura (ADRs)

*El formato para nuevas decisiones debe ser:*
- **Fecha**: YYYY-MM-DD
- **Contexto**: Cual es el problema?
- **Decision**: Que se decidio?
- **Consecuencias**: Que implicaciones tiene?

---

## 2024-XX-XX: Bootstrap del Proyecto
- **Contexto**: Se requeria crear la estructura base para el sistema de prospeccion de Meta Ads que sea modular, testeable y preparada para ser extendida en fases.
- **Decision**: Crear una arquitectura limpia con separacion de responsabilidades y uso de scripts shell para la gestion de dependencias y ejecucion de tareas.
- **Consecuencias**: Se estandarizan los comandos de ejecucion (test, lint, format) a traves de los scripts unificados.

## 2024-XX-XX: Implementacion de Infraestructura de Datos (Fase 1)
- **Contexto**: Necesidad de establecer una capa de persistencia escalable, modular y tipada antes de abordar el scraper.
- **Decision**: Utilizar SQLAlchemy 2.x (tipado estatico `Mapped`), SQLite, Alembic (migraciones atomicas) y patron Repositorio.
- **Consecuencias**: Se facilita el testing con bases de datos en memoria y se desacoplan los objetos ORM del resto del codigo.

## 2024-XX-XX: SDK Interno de Cliente Meta Ads (Fase 2)
- **Contexto**: Necesitabamos interactuar con Meta sin acoplar esa logica a Playwright, a la persistencia o a la logica de negocio general.
- **Decision**: Encapsular toda interaccion con la API de Meta Ads Library en un SDK interno (`src/modules/meta_ads/client`) con patron Gateway puro, devolviendo exclusivamente DTOs inmutables.
- **Consecuencias**: Otros modulos pueden depender de DTOs seguros sin preocuparse de si provienen de la Graph API, un mock o de un scraping por HTML.

## 2026-06-29: Estabilizacion previa a Fase 3
- **Contexto**: El proyecto necesitaba quedar funcional antes de avanzar con extraccion de dominios.
- **Decision**: Se agrego CompanyRepository, se dejo `src/models/__init__.py` para registrar modelos en Alembic, se declaro `responses` como dependencia de desarrollo.
- **Consecuencias**: La base queda preparada para que futuros agentes puedan continuar por fases.

## 2026-06-29: Priorizar adquisicion por navegador
- **Contexto**: La API de Meta Ads Library no cubre de forma suficiente el caso comercial buscado.
- **Decision**: Mantener el cliente API como componente secundario, testeado y desacoplado, pero orientar Fase 3 a adquisicion por navegador con Playwright.
- **Consecuencias**: Fase 3 debe enfocarse en seguridad operativa, tiempos configurables, logs, modo visible/headless y extraccion robusta desde DOM.

## 2026-06-29: Documentacion obligatoria por fase
- **Contexto**: El proyecto sera trabajado por multiples agentes y necesita trazabilidad clara.
- **Decision**: Crear `docs/phases/` con una plantilla y archivos por fase.
- **Consecuencias**: Un agente nuevo puede continuar leyendo la fase correspondiente sin depender del historial del chat anterior.

## 2026-06-29: Implementacion completa de Fase 3
- **Contexto**: La Fase 3 requiere adquisicion robusta por navegador.
- **Decision**: Implementar SessionManager, BrowserManager y serializador JSON que produzca exactamente la estructura documentada.
- **Consecuencias**: La fase queda completa con todos los criterios de aceptacion cumplidos y 20 tests pasando.

## 2026-06-30: Eliminar dependencia de sesion de Facebook
- **Contexto**: Meta Ads Library funciona sin sesion de Facebook para descubrimiento y enriquecimiento.
- **Decision**: Eliminar `ensure_session()`, `wait_for_login()` y timeout de login. Simplificar a creacion de contexto/pagina.
- **Consecuencias**: Ejecucion sin intervencion humana. Simplificacion del flujo.

## 2026-06-30: Enrichment desde texto del dialogo
- **Contexto**: Los links en el dialogo de detalles no son confiables para extraer usuarios sociales.
- **Decision**: Reescribir extraccion de enrichment para parsear el texto del dialogo expandido.
- **Consecuencias**: Extraccion confiable de usuarios sociales y seguidores.

## 2026-06-30: Descripcion completa sin truncamiento
- **Contexto**: El truncamiento de la descripcion a 2000 caracteres perdia informacion valiosa.
- **Decision**: Eliminar limite de 2000 caracteres en `_extract_ad_description`.
- **Consecuencias**: Descripciones mas largas en el JSON de salida.

## 2026-06-30: ad_library_url construida correctamente
- **Contexto**: La URL del anuncio se estaba copiando de la pagina en lugar de construirse con el library_id.
- **Decision**: Construir `ad_library_url` como `https://www.facebook.com/ads/library/?id={library_id}`.
- **Consecuencias**: URLs de anuncios correctas y consistentes.

## 2026-06-30: Manejo de "Ver detalles del resumen"
- **Contexto**: Algunos anuncios muestran un dialogo de resumen que requiere un clic adicional.
- **Decision**: Implementar `_enter_from_summary()` que detecta el dialogo de resumen y clickea "Ver detalles del anuncio".
- **Consecuencias**: Enriquecimiento exitoso para anuncios con resumen en lugar de detalles directos.

## 2026-07-02: Fase 3.2 - Mejoras de adquisicion
- **Contexto**: Se requerian mejoras operativas para ejecuciones largas y robustez ante bloqueos.
- **Decision**: Implementar per-keyword limits, scroll infinito configurable, modo append, resume cross-ejecucion, checkpoint por keyword, split por keyword, enrich in-place, reintentos con backoff, proxies, sesion compartida, timeout global, formato hora Argentina, output timestamp.
- **Consecuencias**: Ejecuciones mas largas y estables, capacidad de retomar ejecuciones interrumpidas, mejor anti-bloqueo.

## 2026-07-13: Estabilizacion post-Fase 3
- **Contexto**: Implementacion incorrecta de Fase 4 (hallucinada por IA) agrego modulos de enrichment, landing_scraper y social_scraper no documentados ni validados, junto con documentacion desfasada. Tambien se elimino el cliente HTTP de Meta API (no usado en produccion).
- **Decision**: Eliminar todos los modulos y documentacion de la Fase 4 incorrecta. Eliminar cliente HTTP Meta API, parser y DTOs asociados. Restaurar el proyecto al estado Fase 3.2 estabilizado. Actualizar documentacion completa.
- **Consecuencias**: El proyecto vuelve a un estado estable y documentado (28 tests, solo Playwright). Fase 4 queda pendiente de definicion.
