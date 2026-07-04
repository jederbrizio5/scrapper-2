#!/usr/bin/env python
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner, ARG_TZ

DEFAULT_OUTPUT = None  # se genera en main con fecha+hora


class ArgentinaFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=ARG_TZ)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%d/%m/%Y %H:%M:%S hs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Meta Ads Library — adquisicion por navegador"
    )

    parser.add_argument(
        "--keyword", action="append",
        help='Keyword o "keyword:limite" (ej: "curso:30", "curso marketing")',
    )
    parser.add_argument("--limit", type=int, default=30,
                        help="Limite global por keyword (si no se especifica en --keyword)")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--no-enrich", action="store_true", default=False)
    parser.add_argument("--wait-ms", type=int, default=7000)
    parser.add_argument("--action-delay-ms", type=int, default=1200)
    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument("--slow-mo", type=int, default=0)
    parser.add_argument("--output", default=None,
                        help="Ruta de salida. Default: output/DD-MM-YYYY_HHMMSS/resultados.json")
    parser.add_argument(
        "--max-scrolls", type=int, default=0,
        help="Maximo de scrolls por keyword (0 = infinito, corta solo por 3 vacios u objetivo)",
    )
    parser.add_argument(
        "--empty-scrolls", type=int, default=3,
        help="Cortar tras N scrolls consecutivos sin nuevos dominios",
    )
    parser.add_argument(
        "--sort-mode", default="total_impressions",
        choices=["total_impressions", "relevancy_monthly_grouped"],
        help="Criterio de ordenamiento en Meta Ads Library",
    )
    parser.add_argument(
        "--mode", default="overwrite", choices=["overwrite", "append"],
        help="append: retoma archivo existente y agrega resultados nuevos",
    )
    parser.add_argument(
        "--resume",
        help="JSON con dominios a bloquear (dedup cross-ejecucion)",
    )
    parser.add_argument(
        "--enrich-only",
        help="Modo solo enrichment: archivo JSON con discoveries a enriquecer",
    )
    parser.add_argument(
        "--blocked-domains",
        help="Dominios extra a bloquear (separados por coma)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="No preguntar al sobreescribir archivo existente",
    )
    parser.add_argument(
        "--action-timeout", type=int, default=30000,
        help="Timeout de Playwright por accion (ms). Default 30000 (30s)",
    )
    parser.add_argument(
        "--global-timeout", type=int, default=0,
        help="Timeout global del script en minutos (0 = sin timeout). "
             "Ej: --global-timeout 10 = maximo 10 minutos",
    )
    parser.add_argument(
        "--max-retries", type=int, default=3,
        help="Reintentos por keyword fallida (default 3, recomendado 3-5, 0 = sin reintento)",
    )
    parser.add_argument(
        "--retry-delay", type=int, default=15,
        help="Espera en segundos entre reintentos (default 15, recomendado 10-30)",
    )
    parser.add_argument(
        "--session-per-keywords", type=int, default=3,
        help="Reutilizar sesion cada N keywords (default 3, recomendado 3-5, 0 = sesion nueva por keyword)",
    )
    parser.add_argument(
        "--session-per-ads", type=int, default=5,
        help="Recrear sesion cada N ads en modo enrich-only (default 5, recomendado 3-8, 0 = sesion unica para todos los ads)",
    )
    parser.add_argument(
        "--proxy",
        help="Proxy unico: http://user:pass@host:port",
    )
    parser.add_argument(
        "--proxy-list",
        help="Archivo con lista de proxies (uno por linea). "
             "Formato: http://user:pass@host:port",
    )
    parser.add_argument(
        "--no-split", action="store_true",
        help="No dividir salida por keyword (un solo JSON)",
    )

    parser.add_argument("--publisher-platforms", default="facebook,instagram",
                        help=argparse.SUPPRESS)
    return parser.parse_args()


def _default_output() -> str:
    now = datetime.now(ARG_TZ).strftime("%d-%m-%Y_%H-%M-%S")
    return f"output/{now}/resultados.json"


def main() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(ArgentinaFormatter("%(asctime)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.enrich_only and not args.keyword:
        parser.error("Se requiere --keyword (o --enrich-only para modo enrichment)")

    split_by_keyword = not args.no_split

    if args.enrich_only:
        output_path = args.output
    else:
        output_path = args.output or _default_output()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    extra_blocked = set()
    if args.blocked_domains:
        extra_blocked = {d.strip() for d in args.blocked_domains.split(",") if d.strip()}

    proxy_list: list[str] = []
    if args.proxy:
        proxy_list.append(args.proxy)
    if args.proxy_list:
        try:
            with open(args.proxy_list) as f:
                proxy_list.extend(line.strip() for line in f if line.strip() and not line.startswith("#"))
        except FileNotFoundError:
            parser.error(f"Archivo de proxies no encontrado: {args.proxy_list}")

    runner = MetaAdsBrowserRunner(
        headless=args.headless,
        per_keyword_limit=args.limit,
        wait_after_search_ms=args.wait_ms,
        action_delay_ms=args.action_delay_ms,
        enrich=not args.no_enrich,
        debug_mode=args.debug,
        slow_mo_ms=args.slow_mo,
        max_scroll_attempts=args.max_scrolls,
        consecutive_empty_scrolls=args.empty_scrolls,
        extra_blocked_domains=extra_blocked,
        action_timeout=args.action_timeout,
        global_timeout_minutes=args.global_timeout,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        session_per_keywords=args.session_per_keywords,
        session_per_ads=args.session_per_ads,
        proxy_list=proxy_list if proxy_list else None,
        split_by_keyword=split_by_keyword,
    )
    runner.sort_mode = args.sort_mode

    if args.enrich_only:
        results = runner.enrich_from_file(
            input_path=args.enrich_only,
            output_path=args.output,
            headless=args.headless,
        )
        if args.output:
            dest = args.output
        else:
            dest = args.enrich_only
        logging.info(
            "Enrichment completado: %d resultados en %s",
            len(results), dest,
        )
        return

    results = runner.run(
        keywords=args.keyword,
        output_path=output_path,
        mode=args.mode,
        resume_path=args.resume,
        force=args.force,
    )
    logging.info(
        "Proceso completado: %d resultados en %s",
        len(results), output_path,
    )


if __name__ == "__main__":
    main()
