# Estrategia de Testing

El proyecto utiliza `pytest` para las pruebas automatizadas.

## Reglas de Testing
* Todas las funciones y métodos nuevos deben tener al menos un test unitario asociado.
* Los tests deben correr rápidamente. Los tests lentos o de integración que dependan de APIs externas deben aislarse en la carpeta `tests/integration/` y ejecutarse de forma condicional o estar mockeados por defecto.
* La cobertura debe mantenerse en niveles aceptables.

## Ejecución
* Para ejecutar todos los tests: `./scripts/test.sh`
* Para validar formato, lint y tests juntos: `./scripts/check.sh`

## Tests Actuales

* Unitarios de cliente Meta Ads con `responses`, sin llamadas reales a internet.
* Unitarios de parser Meta Ads.
* Unitarios de componentes Playwright mockeados (BrowserManager, SessionManager, AdsSearcher, AdsExtractor).
* Unitarios de verificacion de sesion y modo debug.
* Integracion de repositorios con SQLite en memoria.

## Dependencias De Testing

Las dependencias de test estan en `requirements-dev.txt`.

No agregar dependencias nuevas sin justificarlo en `docs/DECISIONS.md` si afectan arquitectura o flujo de desarrollo.
