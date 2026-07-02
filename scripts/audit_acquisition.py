#!/usr/bin/env python
"""Auditoría completa del algoritmo de adquisición.

NO modifica el código de producción.
Instrumenta cada etapa del pipeline y genera un informe detallado
con métricas, muestras de cards descartadas y evidencia del cuello de botella.
"""

import json
import logging
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from src.modules.meta_ads.acquisition.ads_extractor import AdsExtractor
from src.modules.meta_ads.acquisition.ads_searcher import AdsSearcher
from src.modules.meta_ads.browser.browser_manager import BrowserManager
from src.modules.meta_ads.browser.session_manager import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs/audit_acquisition.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("audit")

OUTPUT_DIR = Path("output/audit")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_DIR = OUTPUT_DIR / "samples"
SAMPLE_DIR.mkdir(exist_ok=True)

REPORT_PATH = OUTPUT_DIR / "audit_report.json"


class AcquisitionAuditor:
    """Instrumenta cada etapa del pipeline y recolecta métricas."""

    def __init__(self, keyword: str, per_keyword_limit: int = 30):
        self.keyword = keyword
        self.per_keyword_limit = per_keyword_limit

        self.metrics = {
            "keyword": keyword,
            "per_keyword_limit": per_keyword_limit,
            "scrolls": [],
            "extraction_passes": [],
            "total_cards_seen": 0,
            "total_cards_with_library_id": 0,
            "total_cards_analyzed": 0,
            "total_cta_discards": 0,
            "total_no_landing_discards": 0,
            "total_blocked_domain_discards": 0,
            "total_landing_valid": 0,
            "total_unique_domains": 0,
            "dominio_repetido_discards": 0,
            "library_id_duplicate_discards": 0,
            "no_landing_samples": [],
            "timing_ms": {},
            "dom_virtualization_detected": False,
            "loaders_detected": [],
            "scroll_effectiveness": [],
        }
        self.sample_counter = 0
        self._start_time = None

    def run(self):
        self._start_time = time.perf_counter()
        bm = BrowserManager(headless=False, debug_mode=True, slow_mo_ms=0)

        with bm as browser:
            session_manager = SessionManager(browser, user_agent=bm.user_agent)
            page = session_manager.create_session()

            try:
                searcher = AdsSearcher(page=page, wait_after_search_ms=7000)
                extractor = AdsExtractor(page=page, action_delay_ms=1200)

                logger.info("=== INICIANDO AUDITORIA keyword=%s ===", self.keyword)
                searcher.search(self.keyword)

                self._audit_scroll_cycle(page, extractor)

            finally:
                session_manager.close_session()

        elapsed = time.perf_counter() - self._start_time
        self.metrics["timing_ms"]["total"] = int(elapsed * 1000)
        self._save_report()
        self._print_summary()
        return self.metrics

    def _audit_scroll_cycle(self, page, extractor):
        """Ciclo principal: scroll + extracción con instrumentación."""
        all_discoveries = []
        seen_library_ids = set()
        seen_domains = set()
        scroll_attempt = 0
        consecutive_empty = 0
        max_scrolls = 15
        max_consecutive_empty = 3

        while (
            len(all_discoveries) < self.per_keyword_limit
            and scroll_attempt < max_scrolls
        ):
            scroll_attempt += 1
            logger.info("--- Scroll attempt %d ---", scroll_attempt)

            scroll_metrics = {
                "attempt": scroll_attempt,
                "cards_before_wait": 0,
                "cards_after_wait": 0,
                "cards_net_new": 0,
                "cards_removed": 0,
                "loaders_present": False,
                "loader_type": None,
                "dom_stable_time_ms": 0,
                "cards_new_from_previous": 0,
                "extraction": None,
            }

            # ---- FASE 1: Medir DOM antes del scroll ----
            cards_before = self._count_cards(page)
            scroll_metrics["cards_before_wait"] = cards_before
            logger.info("  Cards antes del scroll: %d", cards_before)

            # ---- FASE 2: Scroll incremental ----
            self._perform_scroll(page)
            scroll_start = time.perf_counter()

            # ---- FASE 3: Monitorear DOM durante la espera ----
            dom_stable = False
            prev_count = cards_before
            loaders_found = []
            samples_taken = 0

            for tick in range(15):  # 15 ticks de ~500ms = 7.5s máximo
                time.sleep(0.5)
                current_count = self._count_cards(page)

                # Detectar loaders
                loader = self._detect_loader(page)
                if loader:
                    loaders_found.append({"tick": tick, "type": loader})
                    if not scroll_metrics["loaders_present"]:
                        scroll_metrics["loaders_present"] = True
                        scroll_metrics["loader_type"] = loader

                # Detectar eliminación de cards (DOM virtualization)
                if current_count < prev_count and current_count > 0:
                    removed = prev_count - current_count
                    scroll_metrics["cards_removed"] += removed
                    if not self.metrics["dom_virtualization_detected"]:
                        self.metrics["dom_virtualization_detected"] = True
                        logger.info(
                            "  *** DOM VIRTUALIZATION DETECTADA: "
                            "se eliminaron %d cards (prev=%d actual=%d)",
                            removed,
                            prev_count,
                            current_count,
                        )

                # Si el conteo se estabiliza, registrar
                if current_count == prev_count and current_count > cards_before:
                    if not dom_stable:
                        stable_ms = int((time.perf_counter() - scroll_start) * 1000)
                        scroll_metrics["dom_stable_time_ms"] = stable_ms
                        dom_stable = True

                # Tomar muestras de cards descartadas "sin landing"
                # Solo en los primeros scrolls para no saturar
                if (
                    scroll_attempt <= 3
                    and samples_taken < 5
                    and current_count > prev_count
                ):
                    # Inspeccionar las cards nuevas
                    fresh_cards = current_count - prev_count
                    if fresh_cards > 0:
                        self._sample_no_landing_cards(page, extractor, count=3)
                        samples_taken += 1

                prev_count = current_count

            scroll_metrics["cards_after_wait"] = prev_count
            scroll_metrics["cards_net_new"] = max(0, prev_count - cards_before)
            scroll_metrics["loaders_detected"] = loaders_found

            logger.info(
                "  Cards despues de espera: %d (+%d net nuevas)",
                prev_count,
                scroll_metrics["cards_net_new"],
            )
            if scroll_metrics["cards_removed"] > 0:
                logger.info(
                    "  Cards eliminadas del DOM: %d", scroll_metrics["cards_removed"]
                )

            # ---- FASE 4: Extracción instrumentada ----
            extraction_metrics = self._audit_extraction(page, extractor)
            scroll_metrics["extraction"] = extraction_metrics

            # ---- FASE 5: Integrar en colección global ----
            new_for_global = 0
            for d in extraction_metrics["discoveries"]:
                if d.library_id in seen_library_ids:
                    self.metrics["library_id_duplicate_discards"] += 1
                    continue
                if d.domain in seen_domains:
                    self.metrics["dominio_repetido_discards"] += 1
                    continue
                seen_library_ids.add(d.library_id)
                seen_domains.add(d.domain)
                all_discoveries.append(d)
                new_for_global += 1
                if len(all_discoveries) >= self.per_keyword_limit:
                    break

            scroll_metrics["new_unique_domains_this_scroll"] = new_for_global
            self.metrics["scrolls"].append(scroll_metrics)
            self.metrics["scroll_effectiveness"].append(
                {
                    "attempt": scroll_attempt,
                    "cards_before": cards_before,
                    "cards_after": prev_count,
                    "net_new_cards": scroll_metrics["cards_net_new"],
                    "new_unique_domains": new_for_global,
                }
            )

            logger.info(
                "  >> Unicos acumulados: %d (nuevos en este scroll: %d)",
                len(all_discoveries),
                new_for_global,
            )

            if len(all_discoveries) >= self.per_keyword_limit:
                logger.info("  Limite de dominios alcanzado, cortando")
                break

            if new_for_global == 0:
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    logger.info(
                        "  Corte por %d scrolls consecutivos sin novedades",
                        consecutive_empty,
                    )
                    break
            else:
                consecutive_empty = 0

        self.metrics["total_unique_domains"] = len(set(seen_domains))
        self.metrics["unique_domains_list"] = sorted(seen_domains)
        self.metrics["total_discoveries_collected"] = len(all_discoveries)

    def _audit_extraction(self, page, extractor):
        """Instrumenta extract_discovery_ads con estadísticas detalladas."""
        metrics = {
            "total_candidate_cards": 0,
            "with_library_id": 0,
            "with_cta_engagement": 0,
            "with_landing_url": 0,
            "blocked_domain": 0,
            "valid_landing": 0,
            "no_landing_detail": {
                "no_anchors": 0,
                "engagement_only": 0,
                "no_external_url": 0,
                "internal_only": 0,
            },
            "discoveries": [],
            "samples_saved": 0,
            "processing_time_ms": 0,
        }

        t0 = time.perf_counter()

        try:
            # Obtener todas las cards candidatas
            cards = extractor._candidate_cards()
            metrics["total_candidate_cards"] = len(cards)

            for card in cards:
                text = extractor._safe_inner_text(card)
                if not text:
                    continue

                # 1. Tiene library_id?
                library_id = extractor._extract_library_id(text)
                if not library_id:
                    continue
                metrics["with_library_id"] += 1

                # 2. Tiene anchors en la card?
                all_anchors = card.query_selector_all("a[href]")
                if not all_anchors:
                    metrics["no_landing_detail"]["no_anchors"] += 1
                    self._save_discarded_sample(
                        card, library_id, "sin_anchors", text
                    )
                    continue

                # 3. Engagement CTA?
                has_engagement = any(
                    extractor._is_engagement_href(a) for a in all_anchors
                )
                if has_engagement:
                    metrics["with_cta_engagement"] += 1
                    self._save_discarded_sample(
                        card, library_id, "cta_engagement", text
                    )
                    continue

                # 4. Landing URL?
                landing_url = extractor._extract_landing_url(card)
                if not landing_url:
                    # Clasificar por qué no hay landing
                    if has_engagement:
                        metrics["no_landing_detail"]["engagement_only"] += 1
                    else:
                        # Verificar si hay anchors internos (facebook.com)
                        has_external = False
                        for a in all_anchors:
                            href = extractor._normalize_url(
                                a.get_attribute("href") or ""
                            )
                            if href and extractor._is_external_landing(href):
                                has_external = True
                                break
                        if has_external:
                            metrics["no_landing_detail"]["internal_only"] += 1
                        else:
                            metrics["no_landing_detail"]["no_external_url"] += 1

                    self._save_discarded_sample(
                        card, library_id, "sin_landing", text
                    )
                    metrics["samples_saved"] += 1
                    continue
                metrics["with_landing_url"] += 1

                # 5. Dominio bloqueado?
                domain = extractor._domain_from_url(landing_url)
                if extractor._is_blocked_domain(domain):
                    metrics["blocked_domain"] += 1
                    self._save_discarded_sample(
                        card, library_id, f"bloqueado_{domain}", text
                    )
                    continue
                metrics["valid_landing"] += 1

            metrics["processing_time_ms"] = int((time.perf_counter() - t0) * 1000)

            # Actualizar métricas globales
            self.metrics["total_cards_seen"] += metrics["total_candidate_cards"]
            self.metrics["total_cards_with_library_id"] += metrics["with_library_id"]
            self.metrics["total_cards_analyzed"] += metrics["total_candidate_cards"]
            self.metrics["total_cta_discards"] += metrics["with_cta_engagement"]
            self.metrics["total_blocked_domain_discards"] += metrics["blocked_domain"]
            self.metrics["total_landing_valid"] += metrics["valid_landing"]
            self.metrics["total_no_landing_discards"] += (
                metrics["no_landing_detail"]["no_anchors"]
                + metrics["no_landing_detail"]["no_external_url"]
                + metrics["no_landing_detail"]["internal_only"]
            )

            logger.info(
                "  Extraction audit: cards=%d library_id=%d cta=%d landing=%d "
                "blocked=%d valid=%d",
                metrics["total_candidate_cards"],
                metrics["with_library_id"],
                metrics["with_cta_engagement"],
                metrics["with_landing_url"],
                metrics["blocked_domain"],
                metrics["valid_landing"],
            )

            # Extraer discoveries normales para devolverlos
            raw_discoveries = extractor.extract_discovery_ads(
                keyword=self.keyword,
                limit=self.per_keyword_limit + 20,
            )
            metrics["discoveries"] = raw_discoveries

        except Exception as e:
            logger.error("Error en extraction audit: %s", e)
            import traceback
            traceback.print_exc()

        self.metrics["extraction_passes"].append(metrics)
        return metrics

    def _sample_no_landing_cards(self, page, extractor, count=3):
        """Toma muestras de cards que no tienen landing."""
        cards = extractor._candidate_cards()
        sampled = 0
        for card in cards:
            if sampled >= count:
                break
            text = extractor._safe_inner_text(card)
            library_id = extractor._extract_library_id(text)
            if not library_id:
                continue
            landing = extractor._extract_landing_url(card)
            if not landing:
                self._save_discarded_sample(
                    card, library_id, "no_landing_spot_check", text
                )
                sampled += 1

    def _save_discarded_sample(self, card, library_id, reason, text):
        """Guarda HTML de una card descartada para revisión manual."""
        if self.sample_counter >= 100:
            return

        self.sample_counter += 1
        try:
            html = card.inner_html()
        except Exception:
            html = "<error retrieving html>"

        sample = {
            "sample_id": self.sample_counter,
            "library_id": library_id,
            "reason": reason,
            "text": text[:2000],
            "html": html[:5000],
            "scroll_attempt": len(self.metrics["scrolls"]) + 1,
            "timestamp": datetime.now().isoformat(),
        }

        filename = SAMPLE_DIR / f"sample_{self.sample_counter:03d}_{reason}_{library_id}.json"
        filename.write_text(
            json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self.metrics["no_landing_samples"].append(
            {
                "sample_id": self.sample_counter,
                "library_id": library_id,
                "reason": reason,
                "text_preview": text[:300],
                "file": str(filename),
            }
        )

    def _count_cards(self, page):
        """Cuenta cantidad de elementos que parecen cards en el DOM."""
        try:
            return page.evaluate(
                """() => {
                    const cards = document.querySelectorAll(
                        'div[role="article"], div[data-testid="library-ad-card"]'
                    );
                    return cards.length;
                }"""
            )
        except Exception:
            return 0

    def _detect_loader(self, page):
        """Detecta indicadores de carga en la página."""
        try:
            result = page.evaluate(
                """() => {
                    // Loaders/spinners comunes
                    const spinners = document.querySelectorAll(
                        '[aria-busy="true"], '
                        '.spinner, '
                        '[data-testid="loader"], '
                        '.x1n2onr6, '  // clase común de skeleton
                        'div[role="progressbar"]'
                    );
                    if (spinners.length > 0) return 'spinner';

                    // Texto de carga
                    const body = document.body.innerText || '';
                    if (body.includes('Cargando') || body.includes('Loading')) {
                        return 'loading_text';
                    }

                    // Skeleton cards (divs vacíos con aspecto de card)
                    const emptyCards = document.querySelectorAll(
                        'div[role="article"]:empty, '
                        'div[data-testid="library-ad-card"]:empty'
                    );
                    if (emptyCards.length > 5) return 'skeleton_cards';

                    return null;
                }"""
            )
            return result
        except Exception:
            return None

    def _perform_scroll(self, page):
        """Scroll incremental (misma lógica que el algoritmo optimizado)."""
        try:
            viewport_h = page.evaluate("window.innerHeight")
            total_h = page.evaluate("document.body.scrollHeight")
            current_y = page.evaluate("window.scrollY")

            ratio = random.uniform(0.7, 1.1)
            scroll_by = int(viewport_h * ratio)
            max_y = max(0, total_h - viewport_h)
            next_y = min(current_y + scroll_by, max_y)

            if next_y <= current_y and current_y >= max_y:
                backup = int(viewport_h * random.uniform(0.2, 0.4))
                page.evaluate(f"window.scrollBy(0, -{backup})")
                time.sleep(0.3 + random.random() * 0.4)
                page.evaluate(
                    f"window.scrollTo({{top: {max_y}, behavior: 'smooth'}})"
                )
            else:
                page.evaluate(
                    f"window.scrollTo({{top: {next_y}, behavior: 'smooth'}})"
                )
        except Exception as e:
            logger.warning("Error en scroll: %s", e)

    def _print_summary(self):
        """Imprime resumen de la auditoría."""
        m = self.metrics
        print()
        print("=" * 70)
        print("  INFORME DE AUDITORIA DE ADQUISICION")
        print("=" * 70)
        print(f"  Keyword:                 {m['keyword']}")
        print(f"  Limite solicitado:       {m['per_keyword_limit']}")
        print(f"  Dominios unicos encontrados: {m['total_unique_domains']}")
        print(f"  Scrolls ejecutados:      {len(m['scrolls'])}")
        print(f"  Cards vistas total:      {m['total_cards_seen']}")
        print(f"  Cards con Library ID:    {m['total_cards_with_library_id']}")
        print(f"  Cards con landing valida:{m['total_landing_valid']}")
        print(f"  Descartadas por CTA:     {m['total_cta_discards']}")
        print(f"  Descartadas sin landing: {m['total_no_landing_discards']}")
        print(f"  Descartadas bloqueadas:  {m['total_blocked_domain_discards']}")
        print(f"  Muestras guardadas:      {len(m['no_landing_samples'])}")
        print(f"  DOM virtualization:      {m['dom_virtualization_detected']}")
        print(f"  Tiempo total (ms):       {m['timing_ms'].get('total', 'N/A')}")
        print()

        if m["scroll_effectiveness"]:
            print("  Efectividad por scroll:")
            print(
                f"  {'Attempt':>7} {'CardsBefore':>12} {'CardsAfter':>11} "
                f"{'NetNew':>7} {'NewDomains':>10}"
            )
            print("  " + "-" * 55)
            for s in m["scroll_effectiveness"]:
                print(
                    f"  {s['attempt']:>7} {s['cards_before']:>12} "
                    f"{s['cards_after']:>11} {s['net_new_cards']:>7} "
                    f"{s['new_unique_domains']:>10}"
                )

        if m["unique_domains_list"]:
            print()
            print("  Dominios unicos encontrados:")
            for d in m["unique_domains_list"]:
                print(f"    - {d}")

        print()
        print(f"  Muestras guardadas en: {SAMPLE_DIR}")
        print(f"  Reporte completo en:   {REPORT_PATH}")
        print("=" * 70)

    def _save_report(self):
        """Guarda el reporte completo como JSON."""
        serializable = self._make_serializable(self.metrics)
        REPORT_PATH.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Reporte guardado en %s", REPORT_PATH)

    @staticmethod
    def _make_serializable(obj):
        """Convierte objetos no serializables (ej. ElementHandle)."""
        if isinstance(obj, dict):
            return {k: AcquisitionAuditor._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [AcquisitionAuditor._make_serializable(v) for v in obj]
        if hasattr(obj, "__dict__"):
            return str(obj)
        return obj


if __name__ == "__main__":
    auditor = AcquisitionAuditor(keyword="curso", per_keyword_limit=30)
    auditor.run()
