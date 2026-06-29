# Guia De Trabajo Para Agentes

Esta guia explica como continuar el proyecto por fases usando agentes de IA sin perder contexto ni romper lo ya estable.

## Como Empezar Un Chat Nuevo

Mensaje sugerido para pegar al iniciar un nuevo chat/agente:

```text
Lee primero README.md y toda la carpeta docs/. La fuente principal es docs/MAESTRO.MD.
No implementes nada todavia. Primero resume el estado actual, la fase que corresponde y propon una ruta corta de trabajo.
Respeta scripts/check.sh como validacion final obligatoria.
```

Si ya queres ejecutar una fase concreta:

```text
Lee README.md y docs/. Vamos a trabajar Fase X: [nombre].
Antes de editar, identifica archivos existentes relacionados, propone cambios minimos y luego implementa con tests.
No modifiques fases futuras salvo que sea estrictamente necesario.
Al terminar, ejecuta ./scripts/check.sh y actualiza docs/DECISIONS.md si corresponde.
```

## Ruta De Trabajo Por Fase

Cada fase debe cerrarse con este orden:

1. Definir objetivo concreto de la fase.
2. Revisar arquitectura existente.
3. Escribir o ajustar tests primero cuando sea posible.
4. Implementar el cambio minimo.
5. Ejecutar `./scripts/check.sh`.
6. Actualizar documentacion.
7. Registrar decisiones importantes en `docs/DECISIONS.md`.
8. Actualizar o crear el archivo correspondiente en `docs/phases/`.

## Como Guardar Una Fase

Al terminar una fase, actualizar:

- `docs/PROJECT.md`: estado funcional real.
- `docs/PHASES.md`: fase completada, fase siguiente y criterios.
- `docs/ARCHITECTURE.md`: solo si cambio estructura o flujo.
- `docs/TESTING.md`: si se agregaron comandos, fixtures o tipos de tests.
- `docs/DECISIONS.md`: si hubo una decision tecnica relevante.
- `README.md`: si cambio instalacion, ejecucion o forma de probar.
- `docs/phases/PHASE_XX_*.md`: detalle de la fase, pruebas y resultado.

## Regla De Alcance

No mezclar fases.

Ejemplo: en Fase 3 se puede crear extraccion de dominios y tests. No se debe implementar scoring, CRM o automatizaciones.

## Fase 3 Recomendada

Objetivo: fortalecer adquisicion por navegador desde Meta Ads Library.

Motivo:

- La API de Meta no cubre bien el objetivo comercial del proyecto.
- La lectura por navegador permite observar anuncios disponibles en la interfaz web.

Base documental:

- `docs/phases/PHASE_03_BROWSER_ACQUISITION_PLAN.md`

Reglas clave:

- tiempos configurables.
- logs claros.
- tests mockeados.
- modo visible/headless configurable.
- no mezclar con scoring ni CRM.

## Fase 4 Recomendada

Objetivo: extraer dominios y visitar landings.

Entrada:

- DTOs de anuncios obtenidos por navegador.

Salida:

- dominios normalizados.
- informacion basica de landing.
- datos candidatos para `Company`.

Salida:

- datos para `Company` y futuras senales de scoring.

Regla: usar HTTP simple primero para landings; Playwright solo como fallback cuando haga falta renderizado.

## Fase 5 Recomendada

Objetivo: calcular score de prospectos con reglas deterministicas iniciales.

Entrada:

- empresa, dominio y senales de landing.

Salida:

- `Lead` con `score` y `estado`.

Regla: no usar IA para scoring hasta tener datos confiables y criterios manuales validados.
