---
description: Ejecuta los tests del proyecto con pytest.
agent: tester
---

Ejecuta los tests del proyecto.

```bash
source venv/bin/activate && ./scripts/test.sh
```

Para tests especificos:
```bash
source venv/bin/activate && python -m pytest $ARGUMENTS -v
```
