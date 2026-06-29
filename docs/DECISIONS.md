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
- **Consecuencias**: Las proximas fases deben enfocarse en seguridad operativa, tiempos configurables, logs, modo visible/headless y extraccion robusta desde DOM.

## 2026-06-29: Documentacion obligatoria por fase
- **Contexto**: El proyecto sera trabajado por multiples agentes y necesita trazabilidad clara.
- **Decisión**: Crear `docs/phases/` con una plantilla y archivos por fase. Cada fase debe documentar objetivo, alcance, pruebas, logs esperados, ejecucion y resultado final.
- **Consecuencias**: Un agente nuevo puede continuar leyendo la fase correspondiente sin depender del historial del chat anterior.
