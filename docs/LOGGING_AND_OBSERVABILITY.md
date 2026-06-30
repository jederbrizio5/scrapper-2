# Logs Y Observabilidad

El objetivo de los logs es descubrir rapido que fallo, donde fallo y con que datos.

## Regla Principal

Todo proceso importante debe registrar inicio, resultado y errores.

Ejemplo:

```text
Iniciando busqueda en Meta Ads Library keyword="curso" country="ALL"
Pagina cargada correctamente url="..."
Extraccion finalizada ads_found=12 duration_ms=8400
```

## Que Loguear

- Inicio y fin de cada fase ejecutable.
- Keyword, pais, idioma y URL cuando aplique.
- Cantidad de resultados encontrados.
- Tiempo de espera aplicado.
- Reintentos.
- Selector usado si se trabaja con DOM.
- Motivo de fallo si una extraccion no encuentra datos.

## Que No Loguear

- Tokens.
- Cookies.
- Passwords.
- Headers sensibles.
- Datos personales innecesarios.

## Navegador Y Anti-Bloqueo

Los procesos basados en navegador deben priorizar seguridad operativa:

- Tiempos de espera configurables, no valores magicos dispersos.
- Pausas entre acciones para evitar comportamiento robotico.
- Reintentos limitados.
- Logs de cada intento.
- Posibilidad de correr en modo visible para depurar.
- No intentar evadir sistemas de seguridad de forma agresiva.

## Resultado Esperado

Ante un fallo, el log debe permitir responder:

- Que keyword o dominio se estaba procesando.
- En que paso fallo.
- Que selector o URL estaba usando.
- Si fue bloqueo, timeout, cambio de DOM, red o parser.
- Si el proceso puede reintentarse.
