---
description: Ejecuta el scraper de Meta Ads Library con argumentos CLI.
agent: scraper
---

Ejecuta el scraper de Meta Ads Library usando Playwright.

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py $ARGUMENTS
```

Ejemplos:
- `scrape --keyword "curso:30" --headless --no-enrich`
- `scrape --keyword "curso:30" --keyword "marketing:100" --headless --no-split --output resultados.json`
- `scrape --enrich-only resultados.json --headless`
- `scrape --keyword "curso:30" --mode append --headless`
