# Proyecto: Sistema de Prospección de Meta Ads

## Visión General
Este sistema tiene como objetivo principal la recoleccion estructurada de anuncios provenientes de Meta Ads Library.

El proyecto está diseñado para construirse modularmente en fases. Actualmente hemos completado la Fase 0 (Bootstrap), la Fase 1 (Infraestructura de datos), la Fase 2 (Cliente Meta Ads / PoC navegador) y la Fase 3 (Adquisicion robusta por navegador).

Nota de producto: la API de Meta no debe considerarse la fuente principal futura porque puede estar limitada a tipos de anuncios que no sirven al objetivo comercial. El camino principal es lectura por navegador con controles de tiempo, logs y seguridad operativa.

## Estado Actual

Fase 0, Fase 1, Fase 2 y Fase 3 estan completadas y estabilizadas.

### Implementado (Fase 0)
- **Scripts**: instalacion, ejecucion, tests, lint, formato y check general.
- **Dependencias**: `requirements.txt` y `requirements-dev.txt`.
- **Configuracion**: variables de entorno cargadas desde `.env` mediante `src/config/settings.py`.

### Implementado (Fase 1)
- **Base de Datos y ORM**: SQLite, SQLAlchemy 2.x.
- **Modelos**: Tablas base `Search`, `Domain`, `Company` y `Lead`.
- **Repositorios**: Arquitectura de Repositorios genéricos y específicos.
- **Migraciones**: Alembic configurado en `migrations/` y migración inicial.
- **Tests**: Testing completo de base de datos.

### Implementado (Fase 2)
- **MetaClient**: Cliente HTTP genérico para interactuar con la Meta Ads Library, totalmente configurado mediante variables de entorno en `settings.py`.
- **Excepciones Tipadas**: Clases específicas para manejar autenticación (`AuthenticationException`), límites (`RateLimitException`) y problemas de formato.
- **Parser y DTOs**: Capa estricta de parseo transformando la respuesta de la Graph API a Data Transfer Objects (Ads, Page, Advertiser, Media).
- **Desacoplamiento**: El cliente Meta NO conoce la base de datos ni hace persistencia.
- **Testing**: Tests unitarios completos con `responses` que no requieren conexión a internet (Mocking).

### Implementado (Fase 3)
- **Adquisicion por navegador**: Sistema completo de discovery y enrichment desde Meta Ads Library con Playwright.
- **Discovery**: Extracción de anuncios con landing externa, descripción completa, domain, advertiser_name y ad_library_url construida.
- **Enrichment**: Extracción de usuarios sociales (Facebook/Instagram) y conteo de seguidores desde el diálogo de detalles.
- **Sin sesión requerida**: Meta Ads Library funciona sin login de Facebook.
- **Modo Debug**: Navegador visible, ejecución lenta, logs detallados.
- **Modo Headless**: Ejecución normal sin intervención visual.
- **CLI**: Script `run_meta_ads_browser.py` con argumentos configurables.
- **DTOs**: `BrowserAdDiscovery`, `BrowserAdEnrichment`, `BrowserAdResult` con serialización JSON.
- **Tests**: 20 tests pasando, `./scripts/check.sh` sin errores.

## Criterio De Estabilidad

El proyecto se considera estable cuando `./scripts/check.sh` pasa sin errores.

## Documentacion Por Fase

Cada fase debe tener su archivo en `docs/phases/` con objetivo, alcance, pruebas, logs esperados y resultado final.
