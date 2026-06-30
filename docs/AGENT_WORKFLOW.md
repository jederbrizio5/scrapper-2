# Guia De Trabajo Para Agentes

Esta guia explica como continuar el proyecto por fases usando agentes de IA sin perder contexto ni romper lo ya estable.

## Como Empezar Un Chat Nuevo

Mensaje sugerido para pegar al iniciar un nuevo chat/agente:

```text
Estamos en la rama: [nombre-rama].
Lee primero README.md y toda la carpeta docs/. La fuente principal es docs/MAESTRO.MD.
Revisa tambien docs/GIT_WORKFLOW.md antes de editar.
No implementes nada todavia. Primero resume el estado actual, la fase que corresponde y propon una ruta corta de trabajo.
Respeta scripts/check.sh como validacion final obligatoria.
```

Si ya queres ejecutar una fase concreta:

```text
Estamos en la rama: [nombre-rama].
Lee README.md y docs/. Vamos a trabajar Fase X: [nombre].
Antes de editar, identifica archivos existentes relacionados, propone cambios minimos y luego implementa con tests.
No documentes fases posteriores salvo instruccion explicita de producto.
Al terminar, ejecuta ./scripts/check.sh y actualiza docs/DECISIONS.md si corresponde.
```

## Seguridad Con GitHub

El flujo seguro de ramas, Pull Requests, merges y rollback esta definido en `docs/GIT_WORKFLOW.md`.

Reglas minimas:

- No trabajar directo en `main`.
- Crear una rama por tarea o fase.
- Pasar el nombre de la rama al agente como parte del contexto.
- Revisar `git status --short --branch` antes y despues de editar.
- Abrir Pull Request con pruebas ejecutadas, riesgos y rollback.
- Usar `git revert` para deshacer cambios ya mergeados.

## Ruta De Trabajo Por Fase

Cada fase debe cerrarse con este orden:

1. Definir objetivo concreto de la fase.
2. Revisar arquitectura existente.
3. Escribir o ajustar tests primero cuando sea posible.
4. Implementar el cambio minimo.
5. Ejecutar `./scripts/check.sh`.
6. Revisar `git status --short --branch` y el diff.
7. Actualizar documentacion.
8. Registrar decisiones importantes en `docs/DECISIONS.md`.
9. Actualizar o crear el archivo correspondiente en `docs/phases/`.
10. Abrir Pull Request siguiendo `docs/GIT_WORKFLOW.md`.

## Como Guardar Una Fase

Al terminar una fase, actualizar:

- `docs/PROJECT.md`: estado funcional real.
- `docs/PHASES.md`: fase completada, fase actual y criterios.
- `docs/ARCHITECTURE.md`: solo si cambio estructura o flujo.
- `docs/TESTING.md`: si se agregaron comandos, fixtures o tipos de tests.
- `docs/DECISIONS.md`: si hubo una decision tecnica relevante.
- `README.md`: si cambio instalacion, ejecucion o forma de probar.
- `docs/phases/PHASE_XX_*.md`: detalle de la fase, pruebas y resultado.

## Regla De Alcance

No mezclar fases. Trabajar solo el alcance indicado por producto.

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
- discovery rapido desde listado.
- enriquecimiento posterior desde detalles solo cuando haga falta.
