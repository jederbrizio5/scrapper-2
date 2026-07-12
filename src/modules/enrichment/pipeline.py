import asyncio
import json
import logging
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.modules.enrichment.dto import EnrichedDomain, PipelineState
from src.modules.landing_scraper import LandingScraper, LandingExtractionResult
from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner
from src.modules.meta_ads.dto import BrowserAdDiscovery
from src.modules.social_scraper import SocialProfileScraper
from src.modules.social_scraper.scraper import ScrapeResult

ARG_TZ = timezone(timedelta(hours=-3))
logger = logging.getLogger(__name__)


class EnrichmentPipeline:
    """Orquesta el pipeline completo: Discovery → Meta Enrichment → Landing → Social."""

    def __init__(
        self,
        browser_runner: MetaAdsBrowserRunner,
        landing_scraper: LandingScraper,
        social_scraper: SocialProfileScraper,
        output_path: str,
        split_by_keyword: bool = True,
        max_domains: int = 0,
        stage_limits: dict | None = None,
        delay_landing: float = 2.0,
        delay_social: float = 3.0,
    ):
        self.browser_runner = browser_runner
        self.landing_scraper = landing_scraper
        self.social_scraper = social_scraper
        self.output_path = Path(output_path)
        self.split_by_keyword = split_by_keyword
        self.max_domains = max_domains
        self.stage_limits = stage_limits or {"landing": 0, "social": 0}
        self.delay_landing = delay_landing
        self.delay_social = delay_social

        self.state: Optional[PipelineState] = None
        self._sig_state = None

    def run(
        self,
        keywords: list[tuple[str, int]] | None = None,
        input_path: str | None = None,
    ) -> list[EnrichedDomain]:
        """
        Ejecuta el pipeline completo.

        Args:
            keywords: Lista de (keyword, limit) para discovery nuevo
            input_path: Path a JSON/carpeta existente para resume

        Returns:
            Lista de EnrichedDomain completados
        """
        start_time = time.perf_counter()

        if input_path:
            logger.info(f"Modo RESUME desde: {input_path}")
            self._load_state(input_path)
            domains = self.state.domains
            # Filtrar solo dominios que necesitan más procesamiento
            pending_domains = [d for d in domains if d.pipeline_status != "completed"]
            logger.info(
                f"Dominios cargados: {len(domains)}, pendientes: {len(pending_domains)}"
            )
        else:
            if not keywords:
                raise ValueError("Se requiere keywords o input_path")
            logger.info(f"Modo DISCOVERY completo para {len(keywords)} keywords")
            domains = []
            pending_domains = []

        # Determinar etapas a ejecutar
        run_discovery = not input_path
        run_meta_enrichment = True  # Siempre si hay discovery
        run_landing = self.stage_limits.get("landing", 0) != 0
        run_social = self.stage_limits.get("social", 0) != 0

        # STAGE 1: Discovery (si es nuevo run)
        if run_discovery:
            logger.info("=" * 60)
            logger.info("STAGE 1: DISCOVERY (Meta Ads Library)")
            logger.info("=" * 60)
            discoveries = self._run_discovery(keywords)
            # Convertir a EnrichedDomain
            for disc in discoveries:
                domain = EnrichedDomain.from_discovery(disc)
                domains.append(domain)
                pending_domains.append(domain)
            self._save_checkpoint(domains, "discovery")
            logger.info(f"Discovery completado: {len(discoveries)} dominios únicos")

        # STAGE 2: Meta Enrichment
        if run_meta_enrichment:
            logger.info("=" * 60)
            logger.info("STAGE 2: META ENRICHMENT")
            logger.info("=" * 60)
            self._run_meta_enrichment(pending_domains)
            self._save_checkpoint(domains, "meta_enrichment")
            pending_domains = [
                d for d in domains if d.landing_enrichment_status != "completed"
            ]

        # STAGE 3: Landing Enrichment
        if run_landing:
            logger.info("=" * 60)
            logger.info("STAGE 3: LANDING ENRICHMENT")
            logger.info("=" * 60)
            self._run_landing_enrichment(pending_domains)
            self._save_checkpoint(domains, "landing_enrichment")
            pending_domains = [
                d for d in domains if d.social_enrichment_status != "completed"
            ]

        # STAGE 4: Social Enrichment
        if run_social:
            logger.info("=" * 60)
            logger.info("STAGE 4: SOCIAL ENRICHMENT")
            logger.info("=" * 60)
            self._run_social_enrichment(pending_domains)
            self._save_checkpoint(domains, "social_enrichment")

        # Final
        elapsed = time.perf_counter() - start_time
        self._log_final_summary(domains, elapsed)
        return domains

    def _run_discovery(
        self, keywords: list[tuple[str, int]]
    ) -> list[BrowserAdDiscovery]:
        """Ejecuta discovery usando el browser runner existente."""
        all_results = self.browser_runner.run(
            keywords=[f"{k}:{limit}" if limit else k for k, limit in keywords],
            output_path=None,  # No guardar, retornamos resultados
            mode="overwrite",
        )
        discoveries = []
        seen_domains = set()
        for result in all_results:
            disc = result.discovery
            if disc.domain not in seen_domains:
                discoveries.append(disc)
                seen_domains.add(disc.domain)
        return discoveries

    def _run_meta_enrichment(self, domains: list[EnrichedDomain]):
        """Ejecuta enriquecimiento de Meta Ads (abre detail dialogs)."""
        if not domains:
            return

        discoveries = [
            d.discovery for d in domains if d.discovery and not d.meta_enrichment
        ]
        if not discoveries:
            logger.info("Sin discoveries pendientes para meta enrichment")
            return

        logger.info(f"Enriqueciendo {len(discoveries)} anuncios en Meta Ads Library...")
        results = self.browser_runner.run_enrichment_only(discoveries)

        for domain, result in zip(
            [d for d in domains if d.discovery and not d.meta_enrichment], results
        ):
            if result.enrichment:
                domain.meta_enrichment = (
                    result.enrichment.to_dict()
                    if hasattr(result.enrichment, "to_dict")
                    else asdict(result.enrichment)
                )
                domain.meta_enrichment_status = "completed"
            else:
                domain.meta_enrichment_status = "failed"

    def _run_landing_enrichment(self, domains: list[EnrichedDomain]):
        """Ejecuta scraping de landing pages."""
        import asyncio

        pending = [
            d
            for d in domains
            if d.landing_enrichment_status == "pending" and d.discovery
        ]
        if not pending:
            logger.info("Sin dominios pendientes para landing enrichment")
            return

        limit = self.stage_limits.get("landing", 0)
        if limit > 0:
            pending = pending[:limit]

        logger.info(
            f"Scrapeando {len(pending)} landing pages (límite: {limit or 'sin límite'})..."
        )

        # Preparar URLs
        urls_to_scrape = []
        for domain in pending:
            landing_url = (
                domain.discovery.get("landing_url")
                if isinstance(domain.discovery, dict)
                else domain.discovery.landing_url
            )
            if landing_url:
                urls_to_scrape.append((domain.domain, landing_url))

        if not urls_to_scrape:
            logger.warning("No hay URLs de landing para scrapeear")
            return

        # Ejecutar en batch async
        results = asyncio.run(self._scrape_landings_batch(urls_to_scrape))

        for domain in pending:
            landing_url = (
                domain.discovery.get("landing_url")
                if isinstance(domain.discovery, dict)
                else domain.discovery.landing_url
            )
            if landing_url in results:
                ext_result = results[landing_url]
                domain.landing_enrichment = ext_result.to_dict()
                domain.landing_enrichment_status = ext_result.status
            else:
                domain.landing_enrichment_status = "failed"
                domain.landing_enrichment = {
                    "status": "failed",
                    "error": "no_result_returned",
                }

            time.sleep(self.delay_landing)

    async def _scrape_landings_batch(
        self, urls: list[tuple[str, str]]
    ) -> dict[str, LandingExtractionResult]:
        """Scrapea múltiples landings en paralelo limitado."""
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrentes

        async def scrape_one(domain: str, url: str):
            async with semaphore:
                result = await self.landing_scraper.scrape(url)
                return url, result

        tasks = [scrape_one(domain, url) for domain, url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Error en batch landing: {r}")
            else:
                url, result = r
                output[url] = result
        return output

    def _run_social_enrichment(self, domains: list[EnrichedDomain]):
        """Ejecuta scraping de perfiles sociales (FB/IG)."""
        pending = [
            d
            for d in domains
            if d.social_enrichment_status == "pending" and d.discovery
        ]
        if not pending:
            logger.info("Sin dominios pendientes para social enrichment")
            return

        limit = self.stage_limits.get("social", 0)
        if limit > 0:
            pending = pending[:limit]

        logger.info(
            f"Scrapeando perfiles sociales para {len(pending)} dominios (límite: {limit or 'sin límite'})..."
        )

        for domain in pending:
            fb_url = None
            ig_url = None

            # Obtener URLs sociales del meta_enrichment o discovery
            meta_enrich = domain.meta_enrichment or {}
            if isinstance(meta_enrich, dict):
                fb_user = meta_enrich.get("facebook_user")
                ig_user = meta_enrich.get("instagram_user")
                if fb_user:
                    fb_url = f"https://www.facebook.com/{fb_user}"
                if ig_user:
                    ig_url = f"https://www.instagram.com/{ig_user}"

            # Fallback: buscar en landing_enrichment
            if not fb_url or not ig_url:
                landing = domain.landing_enrichment or {}
                if isinstance(landing, dict):
                    fb_urls = landing.get("facebook_urls", [])
                    ig_urls = landing.get("instagram_urls", [])
                    if fb_urls and not fb_url:
                        fb_url = fb_urls[0]
                    if ig_urls and not ig_url:
                        ig_url = ig_urls[0]

            if not fb_url and not ig_url:
                logger.debug(f"Sin URLs sociales para {domain.domain}")
                domain.social_enrichment = {
                    "status": "skipped",
                    "error": "no_social_urls",
                }
                domain.social_enrichment_status = "skipped"
                continue

            # Scrapear
            social_result = self.social_scraper.scrape_both(fb_url, ig_url)

            fb_dto = self.social_scraper.to_dto(
                "facebook",
                social_result.get("facebook", ScrapeResult(success=False)),
                fb_url or "",
            )
            ig_dto = self.social_scraper.to_dto(
                "instagram",
                social_result.get("instagram", ScrapeResult(success=False)),
                ig_url or "",
            )

            domain.social_enrichment = {
                "facebook": fb_dto.to_dict() if fb_dto else {"status": "skipped"},
                "instagram": ig_dto.to_dict() if ig_dto else {"status": "skipped"},
                "status": "completed"
                if (fb_dto and fb_dto.status == "completed")
                or (ig_dto and ig_dto.status == "completed")
                else "partial",
            }
            domain.social_enrichment_status = (
                "completed"
                if domain.social_enrichment["status"] == "completed"
                else "partial"
            )

            time.sleep(self.delay_social)

    def _load_state(self, input_path: str):
        """Carga estado desde JSON/carpeta para resume."""
        path = Path(input_path)

        if path.is_dir():
            # Buscar el archivo más completo (social > landing > meta > discovery)
            candidates = [
                path / "stage_4_social_enrichment.json",
                path / "stage_3_landing_enrichment.json",
                path / "stage_2_meta_enrichment.json",
                path / "stage_1_discovery.json",
                path / "resultados.json",
            ]
            for c in candidates:
                if c.exists():
                    input_path = str(c)
                    break

        # Cargar JSON
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Detectar formato: array de entries o objeto con domains
        if isinstance(data, list):
            # Array de entries
            domains = [EnrichedDomain.from_existing_entry(entry) for entry in data]
        elif isinstance(data, dict) and "domains" in data:
            # PipelineState completo
            self.state = PipelineState.from_dict(data)
            return
        else:
            raise ValueError(f"Formato no reconocido en {input_path}")

        # Crear estado
        self.state = PipelineState(
            run_id=path.parent.name if path.parent else "resumed",
            started_at=datetime.now(ARG_TZ).strftime("%d/%m/%Y %H:%M:%S hs"),
            keywords=[],
            config={},
            domains=domains,
        )
        logger.info(f"Estado cargado: {len(domains)} dominios desde {input_path}")

    def _save_checkpoint(self, domains: list[EnrichedDomain], stage: str):
        """Guarda checkpoint en formato compatible (split por keyword o flat)."""
        output_data = [d.to_output_dict() for d in domains]

        if self.split_by_keyword:
            # Agrupar por keyword
            by_kw = {}
            for d in domains:
                kw = d.keyword or "unknown"
                by_kw.setdefault(kw, []).append(d.to_output_dict())

            parts_dir = self.output_path / f"{self.output_path.name}_parts"
            parts_dir.mkdir(parents=True, exist_ok=True)

            for kw, entries in by_kw.items():
                safe_kw = "".join(c if c.isalnum() or c in "_-" else "_" for c in kw)
                part_file = parts_dir / f"{safe_kw}.json"
                part_file.write_text(
                    json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
                )

            # Index
            index = {
                "run_id": self.output_path.name,
                "created_at": datetime.now(ARG_TZ).strftime("%d/%m/%Y %H:%M:%S hs"),
                "stage": stage,
                "total_results": len(domains),
                "parts": [
                    {"keyword": k, "file": f"{k}.json", "results": len(v)}
                    for k, v in by_kw.items()
                ],
            }
            (parts_dir / "index.json").write_text(
                json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            # Flat JSON
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.write_text(
                json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        logger.info(
            f"Checkpoint guardado: {stage} ({len(domains)} dominios) -> {self.output_path}"
        )

    def _log_final_summary(self, domains: list[EnrichedDomain], elapsed: float):
        total = len(domains)
        completed = sum(1 for d in domains if d.pipeline_status == "completed")
        partial = sum(1 for d in domains if d.pipeline_status == "partial")
        failed = sum(1 for d in domains if d.pipeline_status == "failed")

        logger.info("")
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETADO")
        logger.info("=" * 60)
        logger.info(f"Tiempo total: {elapsed:.0f}s ({elapsed/60:.1f}m)")
        logger.info(f"Dominios totales: {total}")
        logger.info(f"  Completados: {completed}")
        logger.info(f"  Parciales: {partial}")
        logger.info(f"  Fallidos: {failed}")
        logger.info(f"Output: {self.output_path}")
        logger.info("=" * 60)


# Helper para agregar método from_discovery a EnrichedDomain
def _add_from_discovery():
    @classmethod
    def from_discovery(cls, disc: BrowserAdDiscovery) -> "EnrichedDomain":
        disc_dict = asdict(disc) if hasattr(disc, "__dataclass_fields__") else disc
        return cls(
            domain=disc_dict.get("domain", ""),
            library_id=disc_dict.get("library_id"),
            keyword=disc_dict.get("keyword"),
            discovery=disc_dict,
            discovery_status="completed",
        )

    EnrichedDomain.from_discovery = from_discovery


_add_from_discovery()
