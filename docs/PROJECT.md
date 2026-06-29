# Proyecto: Sistema de Prospección de Meta Ads

## Visión General
Este sistema tiene como objetivo principal la recolección, procesamiento y evaluación (scoring) de prospectos provenientes de Meta Ads.

El proyecto está diseñado para construirse modularmente en fases. Actualmente hemos completado la Fase 0 (Bootstrap), la Fase 1 (Infraestructura de datos) y la Fase 2 (Cliente Meta Ads / PoC navegador).

Nota de producto: la API de Meta no debe considerarse la fuente principal futura porque puede estar limitada a tipos de anuncios que no sirven al objetivo comercial. El camino principal sera lectura por navegador con controles de tiempo, logs y seguridad operativa.

## Estado Actual

Fase 0, Fase 1 y Fase 2 estan estabilizadas.

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
- **Desacoplamiento**: El cliente Meta NO conoce la base de datos ni hace persistencia, dejando esta tarea a los servicios de dominio de las futuras fases.
- **Testing**: Tests unitarios completos con `responses` que no requieren conexión a internet (Mocking).

### Implementado como PoC
- **Playwright**: `BrowserManager`, `SessionManager`, `AdsSearcher` y `AdsExtractor` existen como prueba de concepto. No son todavia scraper productivo.

### Pendiente
- **Fase 3**: Adquisicion robusta por navegador y extraccion inicial de anuncios.
- **Fase 4**: Extraccion de dominios y scraper de landings.
- **Fase 5**: Scoring de prospectos.
- **Fase 6**: CRM/exportacion.
- **Fase 7**: Automatizaciones.

## Criterio De Estabilidad

El proyecto se considera estable cuando `./scripts/check.sh` pasa sin errores.

## Documentacion Por Fase

Cada fase debe tener su archivo en `docs/phases/` con objetivo, alcance, pruebas, logs esperados y resultado final.
