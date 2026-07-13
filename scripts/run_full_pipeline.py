#!/usr/bin/env python
"""Pipeline completo: Discovery → Meta Enrichment → Landing Enrichment → Social Enrichment."""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from playwright.sync_api import sync_playwright

from src.modules.enrichment import EnrichmentPipeline
from src.modules.landing_scraper import LandingScraper
from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner, ARG_TZ
from src.modules.social_scraper import SocialProfileScraper


class ArgentinaFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=ARG_TZ)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%d/%m/%Y %H:%M:%S hs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Meta Ads Prospecting — Pipeline completo de enriquecimiento"
    )

    # Modo de operación
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--keyword", action="append",
        help='Keyword o "keyword:limite" (ej: "curso:30", "marketing digital")'
    )
    group.add_argument(
        "--resume-from",
        help="Carpeta de salida anterior o JSON para continuar pipeline (detecta etapas completadas)"
    )
    group.add_argument(
        "--enrich-only",
        help="Solo enriquecer (requiere discovery + meta_enrichment previos en JSON/carpeta)"
    )

    # Configuración general
    parser.add_argument("--limit", type=int, default=30,
                        help="Límite global por keyword (si no se especifica en --keyword)")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Modo headless (default: True)")
    parser.add_argument("--no-headless", action="store_false", dest="headless",
                        help="Modo visible (debug)")
    parser.add_argument("--debug", action="store_true", default=False,
                        help="Logs DEBUG level")

    # Output
    parser.add_argument("--output", default=None,
                        help="Carpeta de salida. Default: output/DD-MM-YYYY_HH-MM-SS/")
    parser.add_argument("--no-split", action="store_true", default=False,
                        help="No dividir por keyword (un solo JSON plano)")

    # Stage limits
    parser.add_argument("--max-domains", type=int, default=0,
                        help="Máximo dominios totales a procesar (0 = sin límite)")
    parser.add_argument("--max-landing", type=int, default=0,
                        help="Máximo landings a scrapeear (0 = sin límite)")
    parser.add_argument("--max-social", type=int, default=0,
                        help="Máximo perfiles sociales a scrapeear (0 = sin límite)")
    parser.add_argument("--stages", default="discovery,meta,landing,social",
                        help="Etapas a ejecutar: discovery,meta,landing,social (comma-separated)")

    # Timing / Anti-block
    parser.add_argument("--wait-ms", type=int, default=7000,
                        help="Espera post-búsqueda Meta (ms)")
    parser.add_argument("--action-delay-ms", type=int, default=1200,
                        help="Delay entre acciones Playwright (ms)")
    parser.add_argument("--delay-landing", type=float, default=2.0,
                        help="Delay entre landings (segundos)")
    parser.add_argument("--delay-social", type=float, default=3.0,
                        help="Delay entre perfiles sociales (segundos)")
    parser.add_argument("--timeout-landing", type=int, default=15000,
                        help="Timeout httpx landing (ms)")
    parser.add_argument("--timeout-social", type=int, default=30000,
                        help="Timeout Playwright social (ms)")
    parser.add_argument("--save-html", action="store_true", default=False,
                        help="Guardar HTML crudo en JSON (para debug)")

    # Meta Ads config
    parser.add_argument("--max-scrolls", type=int, default=0,
                        help="Máx scrolls por keyword (0 = infinito hasta objetivo/3 vacíos)")
    parser.add_argument("--empty-scrolls", type=int, default=3,
                        help="Cortar tras N scrolls vacíos consecutivos")
    parser.add_argument("--sort-mode", default="total_impressions",
                        choices=["total_impressions", "relevancy_monthly_grouped"],
                        help="Ordenamiento en Meta Ads Library")
    parser.add_argument("--session-per-keywords", type=int, default=3,
                        help="Reutilizar sesión cada N keywords (0 = nueva por keyword)")
    parser.add_argument("--session-per-ads", type=int, default=5,
                        help="Recrear sesión cada N ads en enrich-only (0 = sesión única)")

    # Proxies
    parser.add_argument("--proxy", help="Proxy único: http://user:pass@host:port")
    parser.add_argument("--proxy-list", help="Archivo con lista de proxies (uno por línea)")

    # Misc
    parser.add_argument("--force", action="store_true",
                        help="No preguntar al sobrescribir")
    parser.add_argument("--slow-mo", type=int, default=0,
                        help="Slow motion Playwright (ms)")

    return parser.parse_args()


def default_output() -> str:
    now = datetime.now(ARG_TZ).strftime("%d-%m-%Y_%H-%M-%S")
    return f"output/{now}"


def main() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(ArgentinaFormatter("%(asctime)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    logger = logging.getLogger(__name__)

    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    output_path = Path(args.output or default_output())
    output_path.mkdir(parents=True, exist_ok=True)

    # Parse stages
    stages = set(s.strip().lower() for s in args.stages.split(","))
    valid_stages = {"discovery", "meta", "landing", "social"}
    invalid = stages - valid_stages
    if invalid:
        parser.error(f"Etapas inválidas: {invalid}. Válidas: {valid_stages}")

    run_discovery = "discovery" in stages
    run_meta = "meta" in stages
    run_landing = "landing" in stages
    run_social = "social" in stages

    # Parse keywords
    keywords = []
    if args.keyword:
        for kw in args.keyword:
            if ":" in kw:
                name, lim = kw.rsplit(":", 1)
                try:
                    keywords.append((name, int(lim)))
                except ValueError:
                    keywords.append((kw, args.limit))
            else:
                keywords.append((kw, args.limit))

    # Proxies
    proxy_list = []
    if args.proxy:
        proxy_list.append(args.proxy)
    if args.proxy_list:
        try:
            with open(args.proxy_list) as f:
                proxy_list.extend(line.strip() for line in f if line.strip() and not line.startswith("#"))
        except FileNotFoundError:
            parser.error(f"Archivo de proxies no encontrado: {args.proxy_list}")

    # Stage limits
    stage_limits = {
        "landing": args.max_landing,
        "social": args.max_social,
    }

    # Lanzar Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=args.headless,
            slow_mo=args.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        try:
            # Browser runner (Meta Ads)
            runner = MetaAdsBrowserRunner(
                headless=args.headless,
                per_keyword_limit=args.limit,
                wait_after_search_ms=args.wait_ms,
                action_delay_ms=args.action_delay_ms,
                enrich=True,
                debug_mode=args.debug,
                slow_mo_ms=args.slow_mo,
                max_scroll_attempts=args.max_scrolls,
                consecutive_empty_scrolls=args.empty_scrolls,
                action_timeout=30000,
                max_retries=3,
                retry_delay=15,
                session_per_keywords=args.session_per_keywords,
                session_per_ads=args.session_per_ads,
                proxy_list=proxy_list if proxy_list else None,
                split_by_keyword=not args.no_split,
                browser=browser,  # Pass the browser instance
            )
            runner.sort_mode = args.sort_mode

            # Landing scraper (async)
            landing_scraper = LandingScraper(
                timeout_httpx=args.timeout_landing / 1000,
                timeout_pw=args.timeout_social / 1000,
                delay_between_requests=args.delay_landing,
                max_retries=2,
                playwright_browser=browser,
                save_html=args.save_html,
            )

            # Social scraper
            social_scraper = SocialProfileScraper(
                browser=browser,
                timeout=args.timeout_social / 1000,
                wait_after_load=3.0,
                headless=args.headless,
            )

            # Pipeline
            pipeline = EnrichmentPipeline(
                browser_runner=runner,
                landing_scraper=landing_scraper,
                social_scraper=social_scraper,
                output_path=str(output_path),
                split_by_keyword=not args.no_split,
                max_domains=args.max_domains,
                stage_limits=stage_limits,
                delay_landing=args.delay_landing,
                delay_social=args.delay_social,
            )

            if args.enrich_only:
                # Modo solo enriquecimiento desde JSON/carpeta existente
                logger.info(f"Modo ENRICH-ONLY desde: {args.enrich_only}")
                results = pipeline.run(input_path=args.enrich_only)
            elif args.resume_from:
                # Modo resume
                logger.info(f"Modo RESUME desde: {args.resume_from}")
                results = pipeline.run(input_path=args.resume_from)
            else:
                # Modo discovery completo
                if not keywords:
                    parser.error("Se requiere --keyword para modo discovery")
                logger.info(f"Modo DISCOVERY completo: {[f'{k}:{l}' for k,l in keywords]}")
                results = pipeline.run(keywords=keywords)

            # Guardar resultado final
            if args.no_split:
                final_file = output_path / "enriched_complete.json"
                final_file.write_text(
                    json.dumps([r.to_output_dict() for r in results], ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                logger.info(f"Resultado final guardado en: {final_file}")
            else:
                logger.info(f"Resultado final en carpeta: {output_path}")

            logger.info(f"Pipeline completado: {len(results)} dominios procesados")

        finally:
            browser.close()


if __name__ == "__main__":
    main()