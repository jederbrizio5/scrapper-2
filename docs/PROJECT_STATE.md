# Estado del Proyecto (PROJECT_STATE.md)

Este archivo actúa como la memoria persistente del estado actual de desarrollo. Mantiene un registro claro de lo que está implementado, lo que está en progreso, la calidad actual del código y las métricas de rendimiento.

---

## 1. Resumen Ejecutivo
* **Última actualización**: 2026-07-07
* **Fase Actual**: Fase 3.2 (Completada y Estabilizada)
* **Objetivo de la Fase**: Adquisición por navegador robusta usando Playwright con dedup, checkpoint, signal handling y per-keyword limits.
* **Estado de Ejecución**: Todos los tests unitarios e integrados pasan (33/33). `./scripts/check.sh` limpio.

---

## 2. Estado de Módulos y Funcionalidades

| Módulo / Componente | Estado | Cobertura de Tests | Descripción |
|---------------------|--------|---------------------|-------------|
| **Core & Config** | Estable | 100% | Configuración mediante variables de entorno en `settings.py`. |
| **Base de Datos (ORM)** | Estable | 100% (Integration) | SQLite con SQLAlchemy 2.x, Alembic migrations y modelos (Search, Domain, Company, Lead). |
| **Repositorios DB** | Estable | 100% (Integration) | CRUD encapsulado para todas las entidades en `src/repositories/`. |
| **Meta Ads HTTP Client** | Estable | 100% (Unit Mocks) | SDK desacoplado secundario (Graph API). |
| **Browser Acquisition** | Estable | 95% (Unit Mocks) | Algoritmo Playwright con anti-detección, discovery y enrichment robustos. |
| **CLI Runner** | Estable | 90% | Script `run_meta_ads_browser.py` con argumentos granulares para control total. |
| **Persistence Integrator**| Pendiente | 0% | Conectar los resultados JSON del scraper con la base de datos (Fase 4.1). |
| **Landing Scraper** | Pendiente | 0% | Extracción de información de contacto e industria desde landing pages (Fase 4.2). |

---

## 3. Métricas y Calidad
* **Linter**: Ruff (100% cumplimiento, 0 errores).
* **Formatter**: Ruff format (100% alineado).
* **Coverage de Código**: ~90% (todos los flujos críticos de la lógica de negocio y Playwright mockeados están probados).
* **Seguridad**:
  * 0 tokens o credenciales hardcodeadas (verificado).
  * Anti-detección implementado y verificado en auditorías locales (`scripts/audit_acquisition.py`).
  * Dominios de engagement (WhatsApp, Telegram) y dominios sociales/competidores en `BLOCKED_DOMAINS`.

---

## 4. Historial de Fases
* **Fase 0 (Bootstrap)**: Setup inicial, ruff, pytest, dotenv. (Completado)
* **Fase 1 (Base de Datos)**: SQLAlchemy ORM, Alembic migrations, Repositorios. (Completado)
* **Fase 2 (MetaClient & PoC)**: Cliente Graph API, DTOs, primer test browser. (Completado)
* **Fase 3 (Browser Acquisition)**: Algoritmo Playwright, Anti-detección, Discovery y Enrichment de seguidores y redes sociales. (Completado)
* **Fase 3.2 (Config, Checkpoint & CLI)**: CLI robusto, checkpoints, signal handling, proxies, resume/append, in-place enrichment. (Completado)
* **Fase 4 (Persistencia & Scraper Landing)**: Integración ORM y scraping web de landings. (Siguiente Fase)

---

## 5. Decisiones Clave Pendientes
1. **Migración a PostgreSQL**: Se evaluará si el volumen de datos en SQLite excede los 500,000 registros de leads/empresas.
2. **Infraestructura de Docker**: Se implementará si se requiere despliegue en servidor (VPS/Cloud), por ahora el desarrollo es 100% local.
