#!/usr/bin/env python
import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner


def parse_args() -> argparse.Namespace:
    """Parsea argumentos para ejecutar el scraper por navegador."""
    parser = argparse.ArgumentParser(description="Meta Ads Library browser scraper")
    parser.add_argument("--keyword", action="append", required=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--no-enrich", action="store_true", default=False)
    parser.add_argument("--wait-ms", type=int, default=7000)
    parser.add_argument("--action-delay-ms", type=int, default=1200)
    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument("--slow-mo", type=int, default=0)
    parser.add_argument("--output", default="output/meta_ads_browser_results.json")
    return parser.parse_args()


def serialize_result(result) -> dict:
    """Serializa un BrowserAdResult a la estructura exacta documentada.

    Estructura:
    {
      "discovery": { ... },
      "enrichment": { ... }
    }
    """
    discovery = asdict(result.discovery)
    enrichment = asdict(result.enrichment) if result.enrichment else None

    if enrichment:
        enrichment.pop("advertiser_info", None)
        enrichment.pop("login_required", None)

    discovery.pop("ad_snapshot_url", None)

    return {
        "discovery": discovery,
        "enrichment": enrichment,
    }


def main() -> None:
    """Ejecuta dos etapas: discovery del listado y enriquecimiento de detalles."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("Modo debug activado: logs detallados habilitados")

    runner = MetaAdsBrowserRunner(
        headless=args.headless,
        per_keyword_limit=args.limit,
        wait_after_search_ms=args.wait_ms,
        action_delay_ms=args.action_delay_ms,
        enrich=not args.no_enrich,
        debug_mode=args.debug,
        slow_mo_ms=args.slow_mo,
    )
    results = runner.run(args.keyword)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            [serialize_result(result) for result in results],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logging.info("Resultados guardados path=%s count=%s", output_path, len(results))


if __name__ == "__main__":
    main()
