# Arquitectura del Sistema

La arquitectura está dividida de forma modular para facilitar el mantenimiento y la escalabilidad.

## Estructura de Módulos

* **`src/core/`**: Lógica central y abstracciones base que son reutilizadas por los demás módulos.
* **`src/config/`**: Gestión de variables de entorno y configuración del sistema (nada hardcodeado).
* **`src/database/`**: Conexiones a bases de datos (SQL/NoSQL) y capa de repositorios.
* **`src/modules/`**: Módulos específicos del dominio de negocio (ej. Crawler, Scraper, CRM).
* **`src/models/`**: Modelos ORM SQLAlchemy.
* **`src/repositories/`**: Operaciones de persistencia encapsuladas.

Nota: `src/core/`, `src/services/` y `src/utils/` estan reservados para futuras fases si hacen falta, pero no existen actualmente.

## Flujo de Datos

Flujo implementado para Meta Ads API:

```text
SearchRequest -> MetaClient -> MetaParser -> SearchResponse[Ad]
```

Flujo implementado para persistencia:

```text
Modelo ORM -> Repositorio -> Sesion SQLAlchemy -> SQLite
```

Regla arquitectonica: `MetaClient` no debe importar repositorios ni modelos ORM. La union entre adquisicion y persistencia debe vivir en un orquestador futuro.

## Direccion Arquitectonica Futura

La adquisicion principal futura debe basarse en navegador con Playwright, no en la API de Meta, porque la API puede no cubrir anuncios comerciales utiles para este proyecto.

Flujo objetivo para Fase 3:

```text
Configuracion de busqueda
  -> BrowserManager / SessionManager
  -> AdsSearcher
  -> AdsExtractor
  -> DTOs internos
  -> orquestador futuro
```

Reglas para navegador:

* tiempos configurables.
* reintentos limitados.
* logs con contexto.
* modo visible para depuracion.
* tests unitarios con mocks.
