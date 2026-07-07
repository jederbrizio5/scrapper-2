---
description: Ejecuta el scraper de Meta Ads Library con argumentos CLI.
agent: scraper
---

Ejecuta el scraper de Meta Ads Library usando Playwright.

```bash
source venv/bin/activate && python scripts/run_meta_ads_browser.py $ARGUMENTS
```

Ejemplos de uso:
- `scrape --keyword "curso:30" --headless --no-enrich` — Scrapeo basico
- `scrape --keyword "curso:30" --keyword "marketing:100" --headless --no-split --output resultados.json` — Scrapeo multiple sin split
- `scrape --enrich-only resultados.json --headless` — Enriquecer resultados existentes
- `scrape --keyword "curso:30" --mode append --headless` — Retomar ejecucion
- `scrape --keyword "curso:100" --headless --no-enrich --proxy http://user:pass@host:port` — Con proxy
- `scrape --keyword "curso:30" --headless --debug` — Modo debug con logs detallados
