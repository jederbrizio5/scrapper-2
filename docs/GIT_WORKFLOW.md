# Flujo Seguro Con GitHub

Este flujo es obligatorio para personas y agentes de IA. El objetivo es poder revisar, mergear y volver atras sin arriesgar `main`.

## Regla Principal

No trabajar directo sobre `main`.

Todo cambio debe nacer en una rama corta, validarse localmente, abrir Pull Request y mergearse solo cuando el estado sea claro.

## Inicio De Cada Tarea

Antes de editar:

1. Confirmar rama y estado:

```bash
git status --short --branch
```

2. Actualizar `main`:

```bash
git switch main
git pull --ff-only origin main
```

3. Crear rama nueva:

```bash
git switch -c tipo/descripcion-corta
```

Tipos sugeridos:

- `feature/`: funcionalidad nueva.
- `fix/`: correccion de bug.
- `docs/`: documentacion.
- `test/`: pruebas.
- `refactor/`: cambio interno sin cambiar comportamiento.
- `chore/`: mantenimiento.

Ejemplo:

```bash
git switch -c feature/browser-acquisition-phase-03
```

## Contexto Obligatorio Para Agentes

Cada agente debe recibir el contexto de la rama y de la tarea.

Mensaje base recomendado:

```text
Estamos en la rama: [nombre-rama].
Objetivo: [objetivo concreto].

Lee primero README.md y docs/MAESTRO.MD. Luego revisa docs/AGENT_WORKFLOW.md, docs/GIT_WORKFLOW.md y la fase correspondiente en docs/phases/.

No trabajes directo en main. No mezcles fases. Antes de editar, revisa git status y archivos relacionados.
Implementa el cambio minimo, agrega o ajusta tests, ejecuta ./scripts/check.sh y documenta lo que cambie.

Al finalizar, informa:
- archivos modificados
- pruebas ejecutadas
- riesgos pendientes
- pasos de rollback
```

## Commits Seguros

Hacer commits pequenos y coherentes. No mezclar cambios de producto, formato masivo y documentacion si no son parte de la misma tarea.

Antes de commitear:

```bash
git status --short
git diff
./scripts/check.sh
```

Commit sugerido:

```bash
git add [archivos]
git commit -m "tipo: descripcion corta"
```

Ejemplos:

- `docs: add safe agent git workflow`
- `fix: handle empty meta ads response`
- `feature: add browser acquisition parser`

## Pull Request

Subir la rama:

```bash
git push -u origin nombre-rama
```

El Pull Request debe incluir:

- objetivo del cambio.
- fase afectada.
- archivos principales modificados.
- pruebas ejecutadas, especialmente `./scripts/check.sh`.
- riesgos o limites conocidos.
- plan de rollback.

No mergear si:

- `./scripts/check.sh` falla.
- hay secretos o tokens en el diff.
- se mezclan fases sin justificacion.
- falta actualizar documentacion cuando cambio arquitectura, uso o comportamiento.

## Merge Seguro

Preferir merge via Pull Request en GitHub.

Antes de mergear:

1. Revisar diff completo del PR.
2. Confirmar que la rama nace desde `main` actualizado o resolver conflictos.
3. Confirmar pruebas exitosas.
4. Confirmar que la documentacion refleja el estado real.

Despues del merge:

```bash
git switch main
git pull --ff-only origin main
git branch --delete nombre-rama
```

Si la rama remota ya no se necesita:

```bash
git push origin --delete nombre-rama
```

## Rollback

Para volver atras un cambio ya mergeado, usar `git revert`. No usar `git reset --hard` sobre ramas compartidas.

Rollback de un commit:

```bash
git switch main
git pull --ff-only origin main
git switch -c fix/revert-descripcion
git revert SHA_DEL_COMMIT
./scripts/check.sh
git push -u origin fix/revert-descripcion
```

Luego abrir Pull Request del revert.

Si el problema esta solo en una rama no mergeada, corregir con un nuevo commit en esa misma rama.

## Archivos Que No Deben Entrar Al PR

No commitear:

- `.env` ni secretos.
- `venv/`.
- caches como `.pytest_cache/` o `.ruff_cache/`.
- logs generados.
- salidas temporales o datos privados.

Si un archivo generado es necesario para el proyecto, documentar por que debe versionarse.

## Checklist Final Del Agente

Antes de pedir review o merge:

- La rama no es `main`.
- `git status --short --branch` fue revisado.
- El diff contiene solo cambios relacionados con la tarea.
- `./scripts/check.sh` fue ejecutado o se documento por que no pudo ejecutarse.
- `docs/` y `README.md` fueron actualizados si correspondia.
- El PR incluye rollback claro.
