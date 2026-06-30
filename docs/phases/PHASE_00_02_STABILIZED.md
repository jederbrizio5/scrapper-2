# Fases 0 A 2: Base Estabilizada

## Estado

Completada.

## Objetivo

Dejar una base funcional, testeable y documentada para continuar con fases futuras.

## Implementado

- Scripts de instalacion, ejecucion, formato, lint, tests y check general.
- Configuracion por variables de entorno.
- Base de datos SQLite con SQLAlchemy.
- Migraciones Alembic.
- Modelos `Search`, `Domain`, `Company`, `Lead`.
- Repositorios para esos modelos.
- Cliente HTTP para Meta Ads Library API.
- DTOs y parser para respuestas de Meta.
- PoC de navegador con Playwright.
- Tests unitarios e integracion mockeados.

## Importante Sobre La API De Meta

El cliente API existe y queda testeado, pero no debe asumirse como fuente principal para adquisicion comercial.

Motivo: la API de Meta Ads Library puede estar limitada a ciertos tipos de anuncios, como politicos o temas especiales, y no cubre el caso principal buscado por este proyecto.

Decision operativa: Fase 3 debe priorizar adquisicion por navegador con Playwright.

## Como Se Ejecuta

```bash
./scripts/run.sh
```

## Como Se Prueba

```bash
./scripts/check.sh
```

Resultado esperado actual:

```text
11 passed
All checks passed
```

## Resultado Final

La base esta lista para disenar Fase 3 con enfoque navegador.
