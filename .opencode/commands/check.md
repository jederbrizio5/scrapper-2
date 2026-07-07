---
description: Ejecuta validacion completa: format + lint + tests. Obligatorio antes de cerrar cualquier tarea.
---

Ejecuta validacion completa del proyecto:

```bash
source venv/bin/activate && ./scripts/check.sh
```

Esto ejecuta en orden:
1. ruff format (check)
2. ruff lint
3. pytest

Si falla, revisa los errores, corrige, y vuelve a ejecutar `check`.
