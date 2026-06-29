# Fase 3: Adquisicion Por Navegador Y Extraccion Inicial

## Estado

Pendiente.

## Objetivo

Construir una adquisicion robusta desde Meta Ads Library usando navegador, porque la API de Meta no cubre de forma suficiente el caso comercial del proyecto.

## Alcance

- Mejorar `BrowserManager`, `SessionManager`, `AdsSearcher` y `AdsExtractor`.
- Agregar tiempos configurables entre acciones.
- Agregar logs claros de navegacion, carga, selectores y extraccion.
- Permitir modo visible/headless configurable.
- Extraer anuncios visibles a DTOs internos.
- Preparar la salida para Fase 4 o para un extractor de dominios.

## Fuera De Alcance

- No implementar scoring.
- No implementar CRM.
- No automatizar envios masivos.
- No guardar datos sin un orquestador definido.

## Seguridad Operativa

La fase debe evitar comportamiento agresivo:

- No hacer requests en loop sin pausas.
- No usar tiempos fijos dispersos en el codigo.
- Usar limites de intentos.
- Registrar bloqueos, timeouts y cambios de DOM.
- Poder ejecutar en modo visible para inspeccion manual.

## Archivos Probables

- `src/modules/meta_ads/browser/browser_manager.py`
- `src/modules/meta_ads/browser/session_manager.py`
- `src/modules/meta_ads/acquisition/ads_searcher.py`
- `src/modules/meta_ads/acquisition/ads_extractor.py`
- `tests/unit/meta_ads/test_browser_acquisition.py`
- nuevos tests unitarios si se agregan clases auxiliares.

## Como Se Ejecutaria

Comando actual de PoC:

```bash
source venv/bin/activate
PYTHONPATH=. python scripts/run_poc.py
```

La fase puede agregar un script nuevo si hace falta, pero debe documentarse en `README.md`.

## Como Se Prueba

Tests obligatorios:

- tests unitarios con mocks de Playwright.
- tests de parsing/extraccion con HTML fixture si se agrega.
- `./scripts/check.sh` como validacion final.

## Logs Esperados

- inicio de busqueda.
- URL visitada.
- keyword buscada.
- tiempo de espera aplicado.
- selector que encontro resultados.
- cantidad de anuncios candidatos.
- cantidad de anuncios convertidos a DTO.
- motivo si no se encontraron anuncios.

## Criterios De Aceptacion

- El navegador puede abrir Meta Ads Library en modo visible o headless.
- La extraccion no depende de un unico selector fragil.
- Los errores quedan logueados con contexto.
- Los tests mockeados pasan.
- `./scripts/check.sh` pasa.
