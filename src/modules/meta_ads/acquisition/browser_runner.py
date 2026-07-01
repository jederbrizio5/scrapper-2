import logging
import time

from src.modules.meta_ads.acquisition.ads_extractor import AdsExtractor
from src.modules.meta_ads.acquisition.ads_searcher import AdsSearcher
from src.modules.meta_ads.browser.browser_manager import BrowserManager
from src.modules.meta_ads.browser.session_manager import SessionManager
from src.modules.meta_ads.dto import BrowserAdResult

logger = logging.getLogger(__name__)


class MetaAdsBrowserRunner:
    """Orquesta la adquisicion por navegador sin persistir en base de datos.

    Incluye verificación de sesión, modo debug, scroll para más resultados
    y generación de JSON conforme a la estructura documentada en la Fase 3.
    """

    def __init__(
        self,
        headless: bool = True,
        per_keyword_limit: int = 3,
        wait_after_search_ms: int = 7000,
        action_delay_ms: int = 1200,
        enrich: bool = True,
        debug_mode: bool = False,
        slow_mo_ms: int = 0,
        max_scroll_attempts: int = 10,
        known_domains: set | None = None,
        known_library_ids: set | None = None,
    ):
        self.headless = headless
        self.per_keyword_limit = per_keyword_limit
        self.wait_after_search_ms = wait_after_search_ms
        self.action_delay_ms = action_delay_ms
        self.enrich = enrich
        self.debug_mode = debug_mode
        self.slow_mo_ms = slow_mo_ms
        self.max_scroll_attempts = max_scroll_attempts
        self.known_domains = known_domains or set()
        self.known_library_ids = known_library_ids or set()

    def run(self, keywords: list[str]) -> list[BrowserAdResult]:
        """Ejecuta discovery y enriquecimiento para una o mas keywords.

        Incluye scroll para cargar más anuncios y filtrado por dominios únicos.
        """
        start_time = time.perf_counter()
        results: list[BrowserAdResult] = []

        bm = BrowserManager(
            headless=self.headless,
            debug_mode=self.debug_mode,
            slow_mo_ms=self.slow_mo_ms,
        )
        with bm as browser:
            session_manager = SessionManager(browser, user_agent=bm.user_agent)
            page = session_manager.create_session()

            try:
                searcher = AdsSearcher(
                    page=page, wait_after_search_ms=self.wait_after_search_ms
                )
                extractor = AdsExtractor(
                    page=page, action_delay_ms=self.action_delay_ms
                )

                for keyword in keywords:
                    logger.info("Iniciando keyword=%s", keyword)
                    searcher.search(keyword)

                    discoveries = self._collect_discoveries_with_scroll(
                        extractor, keyword
                    )

                    if self.enrich:
                        enriched = extractor.enrich_ads(discoveries)
                        results.extend(enriched)
                    else:
                        results.extend(
                            BrowserAdResult(discovery=d) for d in discoveries
                        )
                    page.wait_for_timeout(self.action_delay_ms)

            finally:
                session_manager.close_session()

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Ejecucion completada en %.1fs total_results=%s", elapsed, len(results)
        )
        return results

    def _collect_discoveries_with_scroll(
        self, extractor: AdsExtractor, keyword: str
    ) -> list:
        """Realiza scroll para cargar más anuncios y recolecta descubrimientos únicos."""
        all_discoveries = []
        seen_library_ids: set[str] = set()
        seen_domains: set[str] = set()
        scroll_attempts = 0

        while (
            len(all_discoveries) < self.per_keyword_limit
            and scroll_attempts < self.max_scroll_attempts
        ):
            raw_discoveries = extractor.extract_discovery_ads(
                keyword=keyword,
                limit=self.per_keyword_limit + 20,
            )

            for d in raw_discoveries:
                if d.library_id in seen_library_ids:
                    continue
                if d.domain in seen_domains:
                    logger.debug(
                        "Saltando dominio duplicado domain=%s library_id=%s",
                        d.domain,
                        d.library_id,
                    )
                    continue

                seen_library_ids.add(d.library_id)
                seen_domains.add(d.domain)
                all_discoveries.append(d)

                if len(all_discoveries) >= self.per_keyword_limit:
                    break

            if len(all_discoveries) >= self.per_keyword_limit:
                break

            previous_count = len(all_discoveries)
            extractor.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            extractor.page.wait_for_timeout(self.wait_after_search_ms)
            scroll_attempts += 1

            new_raw = extractor.extract_discovery_ads(keyword=keyword, limit=5)
            new_count = sum(
                1
                for d in new_raw
                if d.library_id not in seen_library_ids and d.domain not in seen_domains
            )

            if new_count == 0 and len(all_discoveries) == previous_count:
                logger.info(
                    "Sin nuevos anuncios tras scroll keyword=%s attempts=%s",
                    keyword,
                    scroll_attempts,
                )
                break

            logger.info(
                "Scroll keyword=%s attempt=%s total_unicos=%s",
                keyword,
                scroll_attempts,
                len(all_discoveries),
            )

        logger.info(
            "Recolección finalizada keyword=%s unicos=%s solicitados=%s",
            keyword,
            len(all_discoveries),
            self.per_keyword_limit,
        )
        return all_discoveries
