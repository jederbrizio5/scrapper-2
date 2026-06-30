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
