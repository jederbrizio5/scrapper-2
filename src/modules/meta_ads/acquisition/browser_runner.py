import json
import logging
import random
import signal
import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.modules.meta_ads.acquisition.ads_extractor import AdsExtractor
from src.modules.meta_ads.acquisition.ads_searcher import AdsSearcher
from src.modules.meta_ads.browser.browser_manager import BrowserManager
from src.modules.meta_ads.browser.session_manager import SessionManager
from src.modules.meta_ads.dto import (
    BrowserAdDiscovery,
    BrowserAdEnrichment,
    BrowserAdResult,
)

ARG_TZ = timezone(timedelta(hours=-3))
logger = logging.getLogger(__name__)

_KEYWORD_LIMIT_SEP = ":"


class MetaAdsBrowserRunner:
    """Orquesta la adquisicion por navegador.

    Cada keyword abre una sesion (contexto + pagina) propia para evitar
    acumulacion de memoria entre busquedas.  Los resultados se guardan
    incrementalmente tras cada keyword y tras cada scroll si hay cambios.
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
        max_scroll_attempts: int = 0,
        consecutive_empty_scrolls: int = 3,
        known_domains: set | None = None,
        known_library_ids: set | None = None,
        extra_blocked_domains: set[str] | None = None,
        action_timeout: int = 30000,
        global_timeout_minutes: int = 0,
        max_retries: int = 3,
        retry_delay: int = 15,
        session_per_keywords: int = 3,
        proxy_list: list[str] | None = None,
        split_by_keyword: bool = False,
    ):
        self.headless = headless
        self.per_keyword_limit = per_keyword_limit
        self.wait_after_search_ms = wait_after_search_ms
        self.action_delay_ms = action_delay_ms
        self.enrich = enrich
        self.debug_mode = debug_mode
        self.slow_mo_ms = slow_mo_ms
        self.max_scroll_attempts = max_scroll_attempts
        self.consecutive_empty_scrolls = consecutive_empty_scrolls
        self.known_domains = known_domains or set()
        self.known_library_ids = known_library_ids or set()
        self.extra_blocked_domains = extra_blocked_domains or set()
        self.action_timeout = action_timeout
        self.global_timeout_seconds = (
            global_timeout_minutes * 60 if global_timeout_minutes > 0 else 0
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session_per_keywords = session_per_keywords
        self._proxy_cycle = list(proxy_list) if proxy_list else []
        self.split_by_keyword = split_by_keyword
        self.publisher_platforms = ("facebook", "instagram")
        self.sort_mode = "total_impressions"

    def _next_proxy(self) -> str | None:
        if not self._proxy_cycle:
            return None
        return random.choice(self._proxy_cycle)

    # ── entrada principal ────────────────────────────────────────────────

    def run(
        self,
        keywords: list[str],
        output_path: str | None = None,
        mode: str = "overwrite",
        resume_path: str | None = None,
        force: bool = False,
    ) -> list[BrowserAdResult]:
        start = time.perf_counter()
        results: list[BrowserAdResult] = []
        self._sig_results = results
        self._sig_output = output_path
        self._register_signal_handler()
        self._register_global_timeout()

        kw_parsed = self._parse_keywords(keywords, self.per_keyword_limit)
        known_domains, known_ids = self._load_existing(output_path, mode, resume_path)
        self.known_domains |= known_domains
        self.known_library_ids |= known_ids

        if mode == "append" and output_path:
            parts_dir = Path(output_path).parent / (Path(output_path).stem + "_parts")
            if parts_dir.is_dir():
                loaded = 0
                for f in sorted(parts_dir.glob("*.json")):
                    if f.stem == "index":
                        continue
                    raw = json.loads(f.read_text(encoding="utf-8"))
                    for entry in raw:
                        disc_data = entry.get("discovery", entry)
                        enrich_data = entry.get("enrichment")
                        d = BrowserAdDiscovery(**disc_data)
                        e = BrowserAdEnrichment(**enrich_data) if enrich_data else None
                        results.append(BrowserAdResult(discovery=d, enrichment=e))
                    loaded += len(raw)
                logger.info(
                    "Append: cargados %d resultados desde %s/", loaded, parts_dir.name
                )
            elif Path(output_path).exists():
                try:
                    raw = json.loads(Path(output_path).read_text(encoding="utf-8"))
                    for entry in raw:
                        disc_data = entry.get("discovery", entry)
                        enrich_data = entry.get("enrichment")
                        d = BrowserAdDiscovery(**disc_data)
                        e = BrowserAdEnrichment(**enrich_data) if enrich_data else None
                        results.append(BrowserAdResult(discovery=d, enrichment=e))
                    logger.info(
                        "Append: cargados %d resultados previos desde %s",
                        len(raw),
                        output_path,
                    )
                except (FileNotFoundError, json.JSONDecodeError) as exc:
                    logger.warning("No se pudieron cargar resultados previos: %s", exc)

        if (
            mode == "overwrite"
            and output_path
            and Path(output_path).exists()
            and not force
        ):
            if not self._confirm_overwrite(output_path):
                logger.info("Abortado por el usuario")
                return []

        self._log_config(kw_parsed, mode, resume_path, output_path)

        kw_stats: dict[str, dict] = {}

        bm = BrowserManager(
            headless=self.headless,
            debug_mode=self.debug_mode,
            slow_mo_ms=self.slow_mo_ms,
        )
        with bm as browser:
            shared_page = None
            shared_session = None
            keywords_in_session = 0

            for i, (keyword, kw_limit) in enumerate(kw_parsed, 1):
                kw_start = time.perf_counter()
                kw_ok = True
                kw_results = []
                skip_remaining = False

                # ── manejo de sesion compartida ──
                if (
                    self.session_per_keywords > 0
                    and keywords_in_session >= self.session_per_keywords
                ):
                    if shared_session:
                        try:
                            shared_session.close_session()
                        except Exception:
                            pass
                    shared_session = None
                    shared_page = None
                    keywords_in_session = 0

                if self.session_per_keywords > 0 and shared_session is None:
                    proxy = self._next_proxy()
                    shared_session = SessionManager(
                        browser, user_agent=bm.user_agent, proxy=proxy
                    )
                    shared_page = shared_session.create_session()

                # ── reintentos ──
                last_exc = None
                for attempt in range(1, self.max_retries + 1):
                    try:
                        kw_results, extractor = self._process_keyword(
                            browser,
                            bm,
                            keyword,
                            kw_limit,
                            page=shared_page if self.session_per_keywords > 0 else None,
                        )
                        s = dict(extractor.stats)
                        s.pop("_scrolls_used", None)
                        kw_stats[keyword] = {
                            "results": len(kw_results),
                            "time_s": time.perf_counter() - kw_start,
                            "scrolls": extractor.stats.get("_scrolls_used", 0),
                            **s,
                        }
                        results.extend(kw_results)
                        last_exc = None
                        break
                    except AdsExtractor.MetaBlockedError as block_exc:
                        logger.error(
                            "Meta bloqueado  keyword=%s  error=%s  saltando keyword",
                            keyword,
                            block_exc,
                        )
                        skip_remaining = True
                        break
                    except Exception as attempt_exc:
                        last_exc = attempt_exc
                        if attempt < self.max_retries:
                            logger.warning(
                                "Reintento %d/%d  keyword=%s  error=%s",
                                attempt,
                                self.max_retries - 1,
                                keyword,
                                attempt_exc,
                            )
                            time.sleep(self.retry_delay)
                        else:
                            logger.error(
                                "Keyword fallo tras %d intentos  keyword=%s  error=%s",
                                self.max_retries,
                                keyword,
                                attempt_exc,
                                exc_info=self.debug_mode,
                            )

                if last_exc:
                    kw_ok = False

                if shared_page is None or self.session_per_keywords == 0:
                    keywords_in_session = 0
                else:
                    keywords_in_session += 1

                elapsed = time.perf_counter() - start
                total_unique = len({r.discovery.domain for r in results})
                status = "OK" if kw_ok else "FALL"
                logger.info(
                    "[%d/%d] keyword=%-20s %s  tiempo=%s  empresas_acum=%d  esta=%d",
                    i,
                    len(kw_parsed),
                    keyword,
                    status,
                    self._fmt_time(elapsed),
                    total_unique,
                    len(kw_results),
                )
                if output_path:
                    self._save_checkpoint(
                        results, output_path, keyword if self.split_by_keyword else None
                    )

                if skip_remaining:
                    logger.warning("Bloqueo detectado, saltando keywords restantes")
                    break

            if shared_session:
                try:
                    shared_session.close_session()
                except Exception:
                    pass

        signal.alarm(0)  # desarma timeout global

        elapsed_total = time.perf_counter() - start
        self._log_final_summary(
            results, kw_parsed, kw_stats, elapsed_total, output_path, mode
        )
        return results

    @staticmethod
    def _resolve_enrich_source(input_path: str):
        """Detecta si la entrada es carpeta, _parts/ hermano, o archivo único."""
        ip = Path(input_path)
        parts_dir: Path | None = None

        if ip.is_dir():
            # Busca _parts/ dentro o usa el directorio directamente
            candidate = (
                ip / (ip.name + "_parts") if not ip.name.endswith("_parts") else ip
            )
            if candidate.is_dir():
                parts_dir = candidate
            else:
                parts_dir = ip  # usa el directorio como está
        else:
            candidate = ip.parent / (ip.stem + "_parts")
            if candidate.is_dir():
                parts_dir = candidate

        if parts_dir:
            raw = []
            for f in sorted(parts_dir.glob("*.json")):
                if f.stem == "index":
                    continue
                raw.extend(json.loads(f.read_text(encoding="utf-8")))
            return raw, parts_dir, f"{parts_dir.name}/"

        raw = json.loads(ip.read_text(encoding="utf-8"))
        return raw, None, str(ip)

    def _save_enrich_inplace(self, results, parts_dir, single_file):
        """Escribe resultados enriquecidos en los archivos de origen."""
        by_kw: dict[str, list] = {}
        for r in results:
            by_kw.setdefault(r.discovery.keyword, []).append(r)

        if parts_dir:
            for kw, kw_results in by_kw.items():
                safe_kw = "".join(c if c.isalnum() or c in "_-" else "_" for c in kw)
                part_file = parts_dir / f"{safe_kw}.json"
                serialized = []
                for r in kw_results:
                    disc = asdict(r.discovery)
                    disc.pop("ad_snapshot_url", None)
                    enrich = asdict(r.enrichment) if r.enrichment else None
                    if enrich:
                        enrich.pop("advertiser_info", None)
                        enrich.pop("login_required", None)
                    serialized.append({"discovery": disc, "enrichment": enrich})
                part_file.write_text(
                    json.dumps(serialized, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.info(
                    "Part actualizado  keyword=%s  path=%s  resultados=%d",
                    kw,
                    part_file,
                    len(serialized),
                )
            self._write_split_index(results, parts_dir)
        else:
            # Archivo único: lo sobreescribe con datos enriquecidos
            path = Path(single_file)
            serialized = []
            for r in results:
                disc = asdict(r.discovery)
                disc.pop("ad_snapshot_url", None)
                enrich = asdict(r.enrichment) if r.enrichment else None
                if enrich:
                    enrich.pop("advertiser_info", None)
                    enrich.pop("login_required", None)
                serialized.append({"discovery": disc, "enrichment": enrich})
            path.write_text(
                json.dumps(serialized, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                "Archivo actualizado  path=%s  resultados=%d", path, len(results)
            )

    def enrich_from_file(
        self,
        input_path: str,
        output_path: str | None = None,
        headless: bool = True,
    ) -> list[BrowserAdResult]:
        """Modo solo enrichment: enriquece discoveries y escribe en los mismos archivos."""
        raw, parts_dir, source = self._resolve_enrich_source(input_path)

        logger.info("Enrichment-only: %d discoveries desde %s", len(raw), source)
        discoveries = []
        for entry in raw:
            disc = entry.get("discovery", entry)
            discoveries.append(
                type(
                    "_Discovery",
                    (),
                    {
                        "library_id": disc.get("library_id", ""),
                        "ad_library_url": disc.get(
                            "ad_library_url",
                            f"https://www.facebook.com/ads/library/?id={disc.get('library_id', '')}",
                        ),
                        "keyword": disc.get("keyword", ""),
                        "description": disc.get("description"),
                        "circulation_start": disc.get("circulation_start"),
                        "landing_url": disc.get("landing_url", ""),
                        "domain": disc.get("domain", ""),
                        "advertiser_name": disc.get("advertiser_name"),
                        "extracted_at": disc.get("extracted_at"),
                    },
                )
            )

        results: list[BrowserAdResult] = []
        bm = BrowserManager(headless=headless, debug_mode=False, slow_mo_ms=0)
        with bm as browser:
            for i, disc in enumerate(discoveries, 1):
                try:
                    session = SessionManager(browser, user_agent=bm.user_agent)
                    page = session.create_session()
                    try:
                        extractor = AdsExtractor(
                            page=page,
                            action_delay_ms=self.action_delay_ms,
                            extra_blocked_domains=self.extra_blocked_domains,
                        )
                        page.goto(disc.ad_library_url, wait_until="networkidle")
                        page.wait_for_timeout(3000)
                        cards = extractor._candidate_cards()
                        card = extractor._find_card_by_library_id(
                            cards, disc.library_id
                        )
                        enrichment = None
                        if card:
                            enrichment = extractor._extract_enrichment_from_card(
                                card, disc.library_id
                            )
                        discovery = BrowserAdDiscovery(
                            keyword=disc.keyword,
                            library_id=disc.library_id,
                            description=disc.description,
                            circulation_start=disc.circulation_start,
                            landing_url=disc.landing_url,
                            domain=disc.domain,
                            ad_library_url=disc.ad_library_url,
                            advertiser_name=disc.advertiser_name,
                            extracted_at=disc.extracted_at,
                        )
                        results.append(
                            BrowserAdResult(discovery=discovery, enrichment=enrichment)
                        )
                        logger.info(
                            "[%d/%d] Enriquecido library_id=%s %s",
                            i,
                            len(discoveries),
                            disc.library_id,
                            "OK"
                            if enrichment and enrichment.facebook_user
                            else "sin datos",
                        )
                    finally:
                        session.close_session()
                except Exception as exc:
                    logger.error(
                        "Error enriqueciendo library_id=%s error=%s",
                        disc.library_id,
                        exc,
                        exc_info=self.debug_mode,
                    )

        if output_path:
            self._save_checkpoint(results, output_path)
        else:
            self._save_enrich_inplace(results, parts_dir, source)
        return results

    # ── helpers internos ─────────────────────────────────────────────────

    def _process_keyword(self, browser, bm, keyword: str, kw_limit: int, page=None):
        own_session = page is None
        if own_session:
            proxy = self._next_proxy()
            session_mgr = SessionManager(browser, user_agent=bm.user_agent, proxy=proxy)
            page = session_mgr.create_session()
        try:
            searcher = AdsSearcher(
                page=page,
                wait_after_search_ms=self.wait_after_search_ms,
                publisher_platforms=self.publisher_platforms,
                sort_mode=self.sort_mode,
            )
            extractor = AdsExtractor(
                page=page,
                action_delay_ms=self.action_delay_ms,
                extra_blocked_domains=self.extra_blocked_domains,
                action_timeout=self.action_timeout,
            )
            extractor.check_blocked()
            searcher.search(keyword)
            discoveries, scrolls_used = self._collect_discoveries_with_scroll(
                extractor, keyword, kw_limit
            )
            extractor.stats["_scrolls_used"] = scrolls_used
            if self.enrich:
                return extractor.enrich_ads(discoveries), extractor
            return [BrowserAdResult(discovery=d) for d in discoveries], extractor
        finally:
            if own_session:
                session_mgr.close_session()

    def _collect_discoveries_with_scroll(self, extractor, keyword, kw_limit):
        all_discoveries = []
        seen_library_ids = set(self.known_library_ids)
        seen_domains = set(self.known_domains)
        scroll_attempts = 0
        consecutive_empty = 0
        max_empty = self.consecutive_empty_scrolls

        while len(all_discoveries) < kw_limit and (
            self.max_scroll_attempts == 0 or scroll_attempts < self.max_scroll_attempts
        ):
            raw = extractor.extract_discovery_ads(
                keyword=keyword,
                limit=kw_limit + 20,
                skip_library_ids=seen_library_ids,
            )

            new_in_pass = 0
            for d in raw:
                if d.library_id in seen_library_ids or d.domain in seen_domains:
                    continue
                seen_library_ids.add(d.library_id)
                seen_domains.add(d.domain)
                all_discoveries.append(d)
                new_in_pass += 1
                if len(all_discoveries) >= kw_limit:
                    break

            if len(all_discoveries) >= kw_limit:
                break

            if new_in_pass == 0:
                consecutive_empty += 1
                if consecutive_empty >= max_empty:
                    logger.info(
                        "Corte por %d scrolls vacios consecutivos  keyword=%s",
                        consecutive_empty,
                        keyword,
                    )
                    break
            else:
                consecutive_empty = 0

            scroll_attempts += 1
            self._perform_human_scroll(extractor)
            self._wait_after_scroll(extractor, keyword)

            logger.info(
                "Scroll %d/%s  keyword=%-20s  unicos_acum=%d  nuevos=%d  cards_pag=%d",
                scroll_attempts,
                self.max_scroll_attempts if self.max_scroll_attempts else "inf",
                keyword,
                len(all_discoveries),
                new_in_pass,
                extractor.stats["cards_found"],
            )

        motivo = self._razon_corte(
            all_discoveries, consecutive_empty, scroll_attempts, kw_limit
        )
        logger.info(
            "Recoleccion terminada  keyword=%-20s  unicos=%d/%d  scrolls=%d  motivo=%s",
            keyword,
            len(all_discoveries),
            kw_limit,
            scroll_attempts,
            motivo,
        )
        return all_discoveries, scroll_attempts

    @staticmethod
    def _razon_corte(discoveries, consecutive_empty, scrolls, objetivo):
        if len(discoveries) >= objetivo:
            return f"objetivo ({len(discoveries)} unicos)"
        if consecutive_empty >= 3:
            return f"{consecutive_empty} scrolls vacios"
        return f"limite {scrolls} scrolls"

    # ── scroll ───────────────────────────────────────────────────────────

    def _perform_human_scroll(self, extractor):
        page = extractor.page
        try:
            vh = page.evaluate("window.innerHeight")
            th = page.evaluate("document.body.scrollHeight")
            cy = page.evaluate("window.scrollY")
        except Exception:
            logger.debug("Error scroll dims (posible EPIPE)", exc_info=True)
            return

        ratio = random.uniform(0.7, 1.1)
        sb = int(vh * ratio)
        mx = max(0, th - vh)
        ny = min(cy + sb, mx)

        try:
            if ny <= cy and cy >= mx:
                bk = int(vh * random.uniform(0.2, 0.4))
                page.evaluate(f"window.scrollBy(0, -{bk})")
                page.wait_for_timeout(300 + int(random.random() * 400))
                page.evaluate(f"window.scrollTo({{top: {mx}, behavior: 'smooth'}})")
                return
            page.evaluate(f"window.scrollTo({{top: {ny}, behavior: 'smooth'}})")
        except Exception:
            logger.debug("Error durante scroll", exc_info=True)

    def _wait_after_scroll(self, extractor, keyword):
        page = extractor.page
        wb = self.wait_after_search_ms
        try:
            page.wait_for_function(
                '() => {const c=document.querySelectorAll(\'div[role="article"],'
                ' div[data-testid="library-ad-card"]\'); return c.length > 0;}',
                timeout=wb,
            )
        except Exception:
            pass
        jitter = int(wb * 0.3 * random.random())
        try:
            page.wait_for_timeout(wb + jitter)
        except Exception:
            logger.debug("Error wait_for_timeout tras scroll", exc_info=True)

    # ── persistencia ─────────────────────────────────────────────────────

    def _save_checkpoint(self, results, output_path, keyword_hint=None):
        serialized = []
        for r in results:
            disc = asdict(r.discovery)
            disc.pop("ad_snapshot_url", None)
            enrich = asdict(r.enrichment) if r.enrichment else None
            if enrich:
                enrich.pop("advertiser_info", None)
                enrich.pop("login_required", None)
            serialized.append({"discovery": disc, "enrichment": enrich})

        if keyword_hint and self.split_by_keyword and output_path:
            base = Path(output_path)
            part_dir = base.parent / (base.stem + "_parts")
            part_dir.mkdir(parents=True, exist_ok=True)
            safe_kw = "".join(
                c if c.isalnum() or c in "_-" else "_" for c in keyword_hint
            )
            kw_serialized = [
                s for s in serialized if s["discovery"].get("keyword") == keyword_hint
            ]
            part_file = part_dir / f"{safe_kw}.json"
            part_file.write_text(
                json.dumps(kw_serialized, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                "Checkpoint part  keyword=%s  path=%s  resultados=%d",
                keyword_hint,
                part_file,
                len(kw_serialized),
            )
            self._write_split_index(results, part_dir)
        else:
            path = Path(output_path) if output_path else Path("output/emergency.json")
            if output_path:
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(serialized, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(
                "Checkpoint guardado  path=%s  resultados=%d", path, len(results)
            )

    def _write_split_index(self, results, part_dir):
        """Escribe/actualiza index.json con metadatos de las partes."""
        parts = []
        by_kw: dict[str, list] = {}
        for r in results:
            kw = r.discovery.keyword
            by_kw.setdefault(kw, []).append(r)
        for f in sorted(part_dir.glob("*.json")):
            stem = f.stem
            if stem == "index":
                continue
            kw_results = by_kw.get(stem, [])
            parts.append(
                {
                    "keyword": stem,
                    "file": str(f.relative_to(part_dir.parent)),
                    "results": len(kw_results),
                    "unique_domains": len({r.discovery.domain for r in kw_results}),
                    "size_bytes": f.stat().st_size,
                }
            )
        index = {
            "run_id": part_dir.parent.stem,
            "created_at": datetime.now(ARG_TZ).strftime("%d/%m/%Y %H:%M:%S hs"),
            "total_results": len(results),
            "total_parts": len(parts),
            "parts": parts,
        }
        index_file = part_dir / "index.json"
        index_file.write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Index actualizado  path=%s  partes=%d", index_file, len(parts))

    @staticmethod
    def _load_domains_from_file(filepath: str) -> tuple[set[str], set[str]]:
        """Lee un JSON de resultados y extrae dominios + library_ids."""
        domains: set[str] = set()
        ids: set[str] = set()
        try:
            data = json.loads(Path(filepath).read_text(encoding="utf-8"))
            for entry in data:
                disc = entry.get("discovery", entry)
                if dom := disc.get("domain"):
                    domains.add(dom)
                if lid := disc.get("library_id"):
                    ids.add(lid)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning("No se pudo cargar resume %s: %s", filepath, exc)
        return domains, ids

    def _load_existing(self, output_path, mode, resume_path):
        known_domains: set[str] = set()
        known_ids: set[str] = set()

        for label, path in [("Resume", resume_path), ("Append", output_path)]:
            if not path or not Path(path).exists():
                continue
            if label == "Append" and mode != "append":
                continue

            parts_dir = Path(path).parent / (Path(path).stem + "_parts")
            if parts_dir.is_dir():
                for f in sorted(parts_dir.glob("*.json")):
                    if f.stem == "index":
                        continue
                    d, i = self._load_domains_from_file(str(f))
                    known_domains |= d
                    known_ids |= i
                logger.info(
                    "%s (parts)  %s/*.json  dominios=%d library_ids=%d",
                    label,
                    parts_dir.name,
                    len(known_domains),
                    len(known_ids),
                )
            elif Path(path).is_file():
                d, i = self._load_domains_from_file(path)
                known_domains |= d
                known_ids |= i
                logger.info(
                    "%s  %s  dominios=%d library_ids=%d", label, path, len(d), len(i)
                )

        return known_domains, known_ids

    # ── parseo de keywords ───────────────────────────────────────────────

    @staticmethod
    def _parse_keywords(keywords: list[str], global_limit: int | None = None):
        """Convierte ``["curso:30", "curso marketing"]`` en
        ``[("curso", 30), ("curso marketing", global_limit)]``."""
        result = []
        for kw in keywords:
            if _KEYWORD_LIMIT_SEP in kw:
                name, lim_str = kw.rsplit(_KEYWORD_LIMIT_SEP, 1)
                try:
                    result.append((name, int(lim_str)))
                except ValueError:
                    result.append((kw, global_limit))
            else:
                result.append((kw, global_limit))
        return result

    # ── signal ───────────────────────────────────────────────────────────

    def _register_signal_handler(self):
        def handler(signum, frame):
            logger.warning("Sennal %s recibida, guardando checkpoint...", signum)
            out = getattr(self, "_sig_output", None) or "output/emergency.json"
            if getattr(self, "_sig_results", None):
                self._save_checkpoint(self._sig_results, out)
            sys.exit(128 + signum)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def _register_global_timeout(self):
        if self.global_timeout_seconds <= 0:
            return

        def handler(signum, frame):
            logger.warning(
                "Timeout global alcanzado (%ds), guardando checkpoint...",
                self.global_timeout_seconds,
            )
            out = getattr(self, "_sig_output", None) or "output/emergency.json"
            if getattr(self, "_sig_results", None):
                self._save_checkpoint(self._sig_results, out)
            sys.exit(124)

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(self.global_timeout_seconds)
        logger.info(
            "Timeout global activado: %ds (%d min)",
            self.global_timeout_seconds,
            self.global_timeout_seconds // 60,
        )

    # ── confirmacion ─────────────────────────────────────────────────────

    @staticmethod
    def _confirm_overwrite(path: str) -> bool:
        try:
            resp = input(f"El archivo {path} ya existe. Sobreescribir? (s/N): ")
            return resp.strip().lower() == "s"
        except (EOFError, KeyboardInterrupt):
            return False

    # ── logging ──────────────────────────────────────────────────────────

    def _log_config(self, kw_parsed, mode, resume_path, output_path):
        logger.info("")
        logger.info("=" * 70)
        logger.info("  INICIO DE ADQUISICION — META ADS LIBRARY")
        logger.info("=" * 70)
        logger.info(
            "  Keywords            : %s",
            ", ".join(f'"{k}:{lim}"' if lim else f'"{k}"' for k, lim in kw_parsed),
        )
        logger.info("  Modo                : %s", mode)
        if resume_path:
            logger.info("  Resume desde        : %s", resume_path)
        logger.info("  Archivo salida      : %s", output_path)
        logger.info("  Limite global       : %d", self.per_keyword_limit)
        if self.max_scroll_attempts:
            logger.info("  Scrolls maximos     : %d", self.max_scroll_attempts)
        else:
            logger.info(
                "  Scrolls maximos     : infinito (corta solo por objetivo o 3 vacios)"
            )
        logger.info("  Cortar tras vacios  : %d", self.consecutive_empty_scrolls)
        logger.info("  Plataformas         : %s", ", ".join(self.publisher_platforms))
        logger.info("  Ordenamiento        : %s", self.sort_mode)
        logger.info("  Timeout Playwright  : %d ms", self.action_timeout)
        if self.global_timeout_seconds:
            logger.info(
                "  Timeout global      : %ds (%d min)",
                self.global_timeout_seconds,
                self.global_timeout_seconds // 60,
            )
        else:
            logger.info("  Timeout global      : sin limite")
        logger.info(
            "  Reintentos          : %d (espera %ds entre intentos)",
            self.max_retries - 1,
            self.retry_delay,
        )
        logger.info(
            "  Sesion cada N kw    : %s",
            f"{self.session_per_keywords} keywords"
            if self.session_per_keywords
            else "1 keyword (propia)",
        )
        logger.info("  Proxies disponibles : %d", len(self._proxy_cycle))
        logger.info(
            "  Split por keyword   : %s", "si" if self.split_by_keyword else "no"
        )
        logger.info("  Enriquecimiento     : %s", "si" if self.enrich else "no")
        logger.info("  Debug               : %s", "si" if self.debug_mode else "no")
        logger.info(
            "  Navegador           : %s", "visible" if self.debug_mode else "headless"
        )
        logger.info(
            "  Dominios bloqueados  : %d default + %d extra = %d",
            29,
            len(self.extra_blocked_domains),
            29 + len(self.extra_blocked_domains),
        )
        logger.info("  Dominios conocidos  : %d", len(self.known_domains))
        logger.info("  Library IDs conocidos: %d", len(self.known_library_ids))
        logger.info("")
        logger.info("  DESCARTES:")
        logger.info("    sin_landing     — Sin enlace externo (solo Meta)")
        logger.info("    solo_cta        — Solo WhatsApp/Messenger/telefono")
        logger.info("    dominio_bloq.   — Youtube/TikTok/Twitter/etc.")
        logger.info("    url_acortada    — bit.ly/tinyurl resuelta via HEAD")
        logger.info("")
        logger.info("  NOTAS:")
        logger.info("    • Sin timeout externo (solo timeouts de Playwright)")
        logger.info("    • Keywords fallidas se saltan")
        logger.info("    • Checkpoint tras cada keyword + cada scroll")
        logger.info("=" * 70)
        logger.info("")

    def _log_final_summary(
        self, results, kw_parsed, kw_stats, elapsed, output_path, mode="overwrite"
    ):
        total_unique = len({r.discovery.domain for r in results})
        kw_ok = sum(
            1 for k, _ in kw_parsed if k in kw_stats and kw_stats[k]["results"] > 0
        )

        logger.info("")
        logger.info("=" * 70)
        logger.info("  RESUMEN FINAL")
        logger.info("=" * 70)
        logger.info("  Tiempo total            : %s", self._fmt_time(elapsed))
        logger.info("  Keywords procesadas     : %d/%d", kw_ok, len(kw_parsed))
        logger.info("  Resultados totales      : %d", len(results))
        logger.info("  Empresas (dominios) un. : %d", total_unique)
        if output_path:
            logger.info(
                "  Archivo de salida       : %s (mode: %s)",
                output_path,
                mode,
            )
        logger.info("")
        if kw_stats:
            logger.info(
                "  %-25s %8s %8s %7s %s",
                "KEYWORD",
                "EMPRESAS",
                "TIEMPO",
                "SCROLL",
                "ESTADO",
            )
            logger.info("  " + "-" * 70)
            for k, _ in kw_parsed:
                s = kw_stats.get(k)
                if s:
                    t = self._fmt_time(s.get("time_s", 0))
                    st = "completa" if s["results"] > 0 else "fallo"
                    logger.info(
                        "  %-25s %4d unicos %8s %4d %s",
                        k,
                        s["results"],
                        t,
                        s.get("scrolls", 0),
                        st,
                    )
                else:
                    logger.info("  %-25s %8s %8s %7s %s", k, "-", "-", "-", "fallo")

        totals = {
            k: sum(s.get(k, 0) for s in kw_stats.values())
            for k in [
                "cards_found",
                "cards_processed",
                "discarded_no_landing",
                "discarded_cta",
                "discarded_blocked_domain",
                "short_urls_resolved",
            ]
        }
        if totals["cards_found"]:
            logger.info("")
            logger.info("  ESTADISTICAS DE EXTRACCION:")
            logger.info("    Cards vistas                  : %d", totals["cards_found"])
            logger.info(
                "    Cards nuevas evaluadas        : %d", totals["cards_processed"]
            )
            logger.info(
                "    Descartadas sin landing       : %d", totals["discarded_no_landing"]
            )
            logger.info(
                "    Descartadas solo CTA          : %d", totals["discarded_cta"]
            )
            logger.info(
                "    Descartadas dominio bloqueado : %d",
                totals["discarded_blocked_domain"],
            )
            logger.info(
                "    URLs acortadas resueltas      : %d", totals["short_urls_resolved"]
            )
            tasa = f"{total_unique / max(totals['cards_processed'], 1) * 100:.1f}%"
            logger.info("    Tasa conversion (unicos/proc) : %s", tasa)
        logger.info("=" * 70)
        logger.info("")

    # ── utilidades ───────────────────────────────────────────────────────

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s"
        m, s = divmod(int(seconds), 60)
        if m < 60:
            return f"{m}m {s}s"
        h, m = divmod(m, 60)
        return f"{h}h {m}m {s}s"
