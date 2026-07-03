# Arquitectura del Sistema

La arquitectura está dividida de forma modular para facilitar el mantenimiento y la escalabilidad.

## Estructura de Módulos

* **`src/core/`**: Lógica central y abstracciones base que son reutilizadas por los demás módulos.
* **`src/config/`**: Gestión de variables de entorno y configuración del sistema (nada hardcodeado).
* **`src/database/`**: Conexiones a bases de datos (SQL/NoSQL) y capa de repositorios.
* **`src/modules/`**: Modulos especificos del dominio de negocio.
* **`src/models/`**: Modelos ORM SQLAlchemy.
* **`src/repositories/`**: Operaciones de persistencia encapsuladas.

## Flujo de Datos

Flujo implementado para adquisicion por navegador (Playwright):

```text
Configuracion de busqueda (CLI)
  -> BrowserManager / SessionManager (anti-deteccion)
  -> AdsSearcher (navegacion + filtros)
  -> AdsExtractor.discovery (scroll + cards + resumenes)
  -> AdsExtractor.enrichment (dialogo + seccion anunciante)
  -> DTOs BrowserAdResult (discovery + enrichment)
  -> JSON (checkpoint por keyword)
```

Flujo secundario para Meta Ads API:

```text
SearchRequest -> MetaClient -> MetaParser -> SearchResponse[Ad]
```

Regla arquitectonica: `MetaClient` no debe importar repositorios ni modelos ORM. La union entre adquisicion y persistencia debe vivir en un orquestador futuro.

## Enrichment

El enrichment abre cada `ad_library_url` individualmente, busca el dialogo
"Detalles del anuncio" (excluyendo "Vincular con un anuncio"), expande la
seccion "Informacion sobre el anunciante" via `_native_click()`, y extrae
usuarios sociales FB/IG y seguidores del texto de la seccion expandida.

Los resumenes ("Ver detalles del resumen") se expanden automaticamente
durante discovery para revelar sub-cards.

Reglas:

* tiempos configurables.
* reintentos limitados.
* logs con contexto.
* modo visible para depuracion.
* tests unitarios con mocks.

Reglas para navegador:

* tiempos configurables.
* reintentos limitados.
* logs con contexto.
* modo visible para depuracion.
* tests unitarios con mocks.
