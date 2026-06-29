# Documentacion De Codigo

Este proyecto debe poder ser entendido por una persona nueva o por un agente de IA sin depender de memoria externa.

## Regla General

Todo codigo nuevo debe explicar:

- Que hace.
- Que recibe.
- Que devuelve.
- Que errores puede lanzar o registrar.
- Como se prueba.
- Si lo ejecuta una persona, un script, un test o un orquestador futuro.

## Docstrings

Usar docstrings en modulos, clases y funciones relevantes.

Formato recomendado:

```python
def extract_domains(text: str) -> list[str]:
    """Extrae dominios normalizados desde texto libre.

    Args:
        text: Texto crudo obtenido desde un anuncio o landing.

    Returns:
        Lista de dominios validos, normalizados y sin duplicados.
    """
```

## Comentarios

No comentar lo obvio.

Mal ejemplo:

```python
count += 1  # suma uno
```

Buen ejemplo:

```python
# Meta cambia el DOM con frecuencia; este selector es fallback y debe mantenerse aislado.
```

## Logs

No usar `print()` en codigo productivo. Usar logging:

```python
import logging

logger = logging.getLogger(__name__)
```

Niveles:

- `logger.debug`: detalles tecnicos para diagnostico profundo.
- `logger.info`: pasos normales importantes.
- `logger.warning`: algo raro pero recuperable.
- `logger.error`: fallo que impide completar una accion.

Cada log importante debe incluir contexto: keyword, URL, dominio, fase, intento o selector cuando corresponda.

## Tests

Cada comportamiento nuevo debe tener tests.

Si una funcion toca red, navegador o APIs externas, el test por defecto debe usar mocks.

Los tests reales contra sitios externos deben quedar separados y ser opcionales.

## Documentacion Asociada

Cuando se agrega o cambia una feature, actualizar:

- archivo de fase en `docs/phases/`.
- `docs/PROJECT.md` si cambia el estado general.
- `docs/ARCHITECTURE.md` si cambia el flujo.
- `docs/TESTING.md` si cambia la forma de probar.
- `docs/DECISIONS.md` si se toma una decision tecnica relevante.
