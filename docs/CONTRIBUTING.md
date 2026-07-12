# Guía de Contribución (CONTRIBUTING.md)

¡Bienvenido al proyecto! Para mantener la calidad de código empresarial (Fortune 100) y asegurar que tanto humanos como agentes de IA puedan colaborar de forma eficiente, sigue estas normas obligatorias.

---

## 1. Convención de Commits (Conventional Commits)
Todos los commits deben seguir la especificación [Conventional Commits](https://www.conventionalcommits.org/):

`tipo(alcance): descripción corta en minúsculas`

### Tipos permitidos:
* **feat**: Nueva funcionalidad para el usuario final (ej. `feat(meta_ads): agregar rotación de proxies`).
* **fix**: Corrección de un bug (ej. `fix(enrichment): corregir selector de segudores en Instagram`).
* **docs**: Cambios únicamente en documentación (ej. `docs(agents): actualizar guías de prompts`).
* **style**: Cambios estéticos o de formateo sin alterar lógica (ej. `style: aplicar ruff format`).
* **refactor**: Cambios en código que no corrigen bugs ni añaden funcionalidades (ej. `refactor(db): simplificar base de repositorios`).
* **test**: Añadir o modificar pruebas unitarias o de integración (ej. `test(unit): añadir mocks para extractor`).
* **chore**: Tareas de mantenimiento o configuración (ej. `chore(deps): actualizar versión de playwright`).

---

## 2. Flujo de Git (Git Workflow)
Seguimos una estrategia simplificada de **Trunk-Based Development** combinada con ramas de características cortas.

1. **Crear rama**: Crea una rama descriptiva desde `main` (ej. `feature/fase-4-persistencia` o `bugfix/selector-boton`).
2. **Desarrollar y probar**: Realiza tus cambios y asegúrate de que todos los tests pasen de forma local.
3. **Validación automática**: Corre `./scripts/check.sh` antes de subir tus cambios.
4. **Abrir Pull Request (PR)**: Crea un PR hacia `main`. Explica los cambios realizados, los riesgos identificados y cómo probarlos.
5. **Revisión y Fusión**: Una vez aprobado y verificado que el CI pasa, se fusiona la rama en `main`.

---

## 3. Revisión de Calidad (Checklist Obligatorio)
Antes de solicitar revisión de un PR, confirma:
* [ ] `./scripts/check.sh` pasa sin advertencias.
* [ ] Todo el código nuevo cuenta con type hints y docstrings descriptivos.
* [ ] Se han añadido pruebas unitarias que validan la nueva lógica.
* [ ] No se incluyen secretos, tokens ni credenciales privadas en el historial de Git.
