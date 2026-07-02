#!/usr/bin/env python
"""Diagnóstico de cards 'sin anchors': ¿tienen landing oculta?

Pasos:
1. Encontrar cards sin <a href> pero con library_id y CTA visible
2. Click en el CTA y verificar si aparecen <a href> nuevos
3. Click en "Ver detalles" y buscar landing en el diálogo
4. Medir distribución de anuncios por dominio
"""

import json
import logging
import os
import sys
import time
from collections import Counter
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
        logging.FileHandler("logs/diagnose_sin_anchors.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("diagnose")

OUTPUT_DIR = Path("output/audit")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SinAnchorsDiagnostic:
    """Diagnostica cards 'sin anchors' buscando landings ocultas."""

    def __init__(self, keyword="curso"):
        self.keyword = keyword
        self.results = {
            "keyword": keyword,
            "cards_sin_anchors": [],
            "cta_click_test": {
                "total_tested": 0,
                "anchors_appeared_after_click": 0,
                "landing_found_after_click": 0,
                "results": [],
            },
            "detail_dialog_test": {
                "total_tested": 0,
                "dialog_opened": 0,
                "dialog_has_anchors": 0,
                "dialog_has_landing": 0,
                "results": [],
            },
            "domain_distribution": {},
            "total_cards_analyzed": 0,
            "total_with_library_id": 0,
            "total_sin_anchors": 0,
            "total_with_landing": 0,
        }

    def run(self):
        bm = BrowserManager(headless=False, debug_mode=True, slow_mo_ms=0)
        with bm as browser:
            sm = SessionManager(browser, user_agent=bm.user_agent)
            page = sm.create_session()
            try:
                searcher = AdsSearcher(page=page, wait_after_search_ms=7000)
                extractor = AdsExtractor(page=page, action_delay_ms=1200)

                logger.info("=== DIAGNÓSTICO SIN ANCHORS keyword=%s ===", self.keyword)
                searcher.search(self.keyword)
                page.wait_for_timeout(5000)

                # Hacer scrolls para cargar suficientes cards
                for i in range(5):
                    page.evaluate(
                        f"window.scrollTo({{top: { (i + 1) * 700 }, behavior: 'smooth'}})"
                    )
                    page.wait_for_timeout(3000)

                page.wait_for_timeout(3000)

                # ---- PASO 3: Medir distribución de dominios primero ----
                self._measure_domain_distribution(page, extractor)

                # ---- PASO 1 y 2: Cards sin anchors ----
                self._diagnose_sin_anchors_cards(page, extractor)

            finally:
                sm.close_session()

        self._save_report()
        self._print_summary()

    def _measure_domain_distribution(self, page, extractor):
        """Mide cuántos anuncios hay por dominio."""
        logger.info("--- Midiendo distribución de dominios ---")
        cards = extractor._candidate_cards()
        self.results["total_cards_analyzed"] = len(cards)
        logger.info("Cards candidatas: %d", len(cards))

        domain_counter = Counter()
        landing_urls = []

        for card in cards:
            text = extractor._safe_inner_text(card)
            library_id = extractor._extract_library_id(text)
            if not library_id:
                continue
            self.results["total_with_library_id"] += 1

            landing = extractor._extract_landing_url(card)
            if not landing:
                continue

            domain = extractor._domain_from_url(landing)
            if extractor._is_blocked_domain(domain):
                continue

            domain_counter[domain] += 1
            landing_urls.append(
                {
                    "library_id": library_id,
                    "landing_url": landing,
                    "domain": domain,
                    "advertiser": extractor._extract_advertiser_name(text),
                }
            )

        self.results["total_with_landing"] = len(landing_urls)
        self.results["domain_distribution"] = {
            "total_landing_urls": len(landing_urls),
            "unique_domains": len(domain_counter),
            "domains": dict(domain_counter.most_common()),
            "landing_urls_sample": landing_urls[:30],
            "top_domains_pct": self._calc_concentration(domain_counter),
        }

        logger.info(
            "Distribución: %d landing URLs, %d dominios únicos",
            len(landing_urls),
            len(domain_counter),
        )
        for domain, count in domain_counter.most_common(10):
            logger.info("  %s: %d anuncios", domain, count)

    def _calc_concentration(self, counter):
        """Calcula cuántos dominios acumulan el 80% de los anuncios."""
        if not counter:
            return {}
        total = sum(counter.values())
        sorted_items = counter.most_common()
        cumulative = 0
        for i, (_, count) in enumerate(sorted_items):
            cumulative += count
            if cumulative >= total * 0.8:
                return {
                    "dominios_para_80pct": i + 1,
                    "total_dominios": len(sorted_items),
                    "total_anuncios": total,
                    "porcentaje_acumulado_primeros_5": sum(
                        c for _, c in sorted_items[:5]
                    )
                    / total
                    * 100,
                }
        return {}

    def _diagnose_sin_anchors_cards(self, page, extractor):
        """Encuentra y diagnostica cards sin <a href>."""
        logger.info("--- Diagnosticando cards sin anchors ---")
        cards = extractor._candidate_cards()
        sin_anchors_cards = []

        for card in cards:
            text = extractor._safe_inner_text(card)
            library_id = extractor._extract_library_id(text)
            if not library_id:
                continue

            anchors = card.query_selector_all("a[href]")
            if len(anchors) == 0:
                sin_anchors_cards.append(
                    {"card": card, "library_id": library_id, "text": text}
                )
                if len(sin_anchors_cards) >= 25:
                    break

        self.results["total_sin_anchors"] = len(sin_anchors_cards)
        logger.info(
            "Cards sin anchors encontradas: %d (buscando 20+5 de respaldo)",
            len(sin_anchors_cards),
        )

        # Probar las primeras 20
        test_count = min(20, len(sin_anchors_cards))
        for i, item in enumerate(sin_anchors_cards[:test_count]):
            logger.info(
                "--- Diagnóstico card %d/%d library_id=%s ---",
                i + 1,
                test_count,
                item["library_id"],
            )
            self._diagnose_single_card(page, extractor, item["card"], item["library_id"])

    def _diagnose_single_card(self, page, extractor, card, library_id):
        """Diagnostica una card: CTA click test + detail dialog test."""
        card_result = {
            "library_id": library_id,
            "text_preview": extractor._safe_inner_text(card)[:300],
            "cta_click": None,
            "detail_dialog": None,
        }

        # ---- Paso 1: Click en CTA + buscar anchors nuevos ----
        card_result["cta_click"] = self._test_cta_click(page, card, library_id)

        # ---- Paso 2: Abrir diálogo de detalles ----
        card_result["detail_dialog"] = self._test_detail_dialog(
            page, extractor, card, library_id
        )

        self.results["cta_click_test"]["results"].append(
            {
                "library_id": library_id,
                **card_result["cta_click"],
            }
        )
        self.results["detail_dialog_test"]["results"].append(
            {
                "library_id": library_id,
                **card_result["detail_dialog"],
            }
        )

    def _test_cta_click(self, page, card, library_id):
        """Hace click en botones CTA y busca nuevos anchors."""
        result = {
            "buttons_found": 0,
            "anchors_before": 0,
            "anchors_after": 0,
            "new_anchors": [],
            "landing_found": None,
        }

        try:
            # Buscar todos los botones en la card
            buttons = card.query_selector_all(
                "button, [role=button], a[href]"
            )
            result["anchors_before"] = len(
                card.query_selector_all("a[href]")
            )
            result["buttons_found"] = len(buttons)

            # Intentar click en cada botón (máximo 3)
            clicked = 0
            for btn in buttons:
                if clicked >= 3:
                    break
                try:
                    btn_text = (btn.inner_text() or "").strip().lower()
                    # Solo click en CTAs relevantes
                    if any(
                        kw in btn_text
                        for kw in [
                            "mas informacion",
                            "más información",
                            "registrarse",
                            "comprar",
                            "reserva",
                            "contact",
                            "visita",
                            "inscrib",
                            "ver mas",
                            "ver más",
                            "shop",
                            "learn",
                            "sign up",
                            "call",
                            "llamar",
                            "obtener",
                            "abrir",
                            "ir al",
                            "detalles",
                        ]
                    ):
                        btn.click(timeout=3000, force=True)
                        page.wait_for_timeout(500)
                        clicked += 1
                except Exception:
                    continue

            if clicked > 0:
                page.wait_for_timeout(500)
                new_anchors = card.query_selector_all("a[href]")
                result["anchors_after"] = len(new_anchors)
                result["new_anchors"] = [
                    a.get_attribute("href") or "" for a in new_anchors
                ]

                # Verificar si algún anchor nuevo tiene landing externa
                for anchor in new_anchors:
                    href = anchor.get_attribute("href") or ""
                    normalized = extractor._normalize_url(href)
                    if normalized and extractor._is_external_landing(
                        normalized
                    ):
                        result["landing_found"] = normalized
                        break

                if result["landing_found"]:
                    self.results["cta_click_test"][
                        "landing_found_after_click"
                    ] += 1
                    logger.info(
                        "  >> CTA CLICK: landing encontrada! %s",
                        result["landing_found"],
                    )
                elif result["anchors_after"] > result["anchors_before"]:
                    logger.info(
                        "  >> CTA CLICK: %d anchors nuevos (sin landing externa)",
                        result["anchors_after"] - result["anchors_before"],
                    )
                else:
                    logger.info(
                        "  >> CTA CLICK: sin cambios en anchors"
                    )

            self.results["cta_click_test"]["total_tested"] += 1
            if result["anchors_after"] > result["anchors_before"]:
                self.results["cta_click_test"][
                    "anchors_appeared_after_click"
                ] += 1

        except Exception as e:
            logger.warning("Error en CTA click test: %s", e)

        return result

    def _test_detail_dialog(self, page, extractor, card, library_id):
        """Abre el diálogo de detalles y busca landing URLs."""
        result = {
            "dialog_opened": False,
            "anchors_in_dialog": 0,
            "landing_in_dialog": None,
            "error": None,
        }

        self.results["detail_dialog_test"]["total_tested"] += 1

        try:
            button = extractor._find_detail_button(card)
            if not button:
                result["error"] = "no_detail_button"
                logger.info("  >> DIALOG: sin botón de detalles")
                return result

            button.click(timeout=5000, force=True)
            page.wait_for_timeout(2000)

            # Buscar el diálogo
            btn_text = extractor._safe_inner_text(button).strip()
            if "resumen" in btn_text.lower():
                detail_dialog = extractor._enter_from_summary()
            else:
                detail_dialog = extractor._find_detail_dialog()

            if not detail_dialog:
                result["error"] = "dialog_not_found"
                extractor._close_details()
                logger.info("  >> DIALOG: no se encontró")
                return result

            result["dialog_opened"] = True
            self.results["detail_dialog_test"]["dialog_opened"] += 1

            # Buscar anchors en el diálogo
            anchors = detail_dialog.query_selector_all("a[href]")
            result["anchors_in_dialog"] = len(anchors)

            if anchors:
                self.results["detail_dialog_test"][
                    "dialog_has_anchors"
                ] += 1

            for anchor in anchors:
                href = anchor.get_attribute("href") or ""
                normalized = extractor._normalize_url(href)
                if normalized and extractor._is_external_landing(
                    normalized
                ):
                    result["landing_in_dialog"] = normalized
                    self.results["detail_dialog_test"][
                        "dialog_has_landing"
                    ] += 1
                    logger.info(
                        "  >> DIALOG: landing encontrada! %s",
                        normalized,
                    )
                    break

            if not result["landing_in_dialog"]:
                logger.info(
                    "  >> DIALOG: abierto, %d anchors, sin landing externa",
                    len(anchors),
                )

            extractor._close_details()

        except Exception as e:
            result["error"] = str(e)[:100]
            logger.warning("Error en detail dialog test: %s", e)
            try:
                extractor._close_details()
            except Exception:
                pass

        return result

    def _print_summary(self):
        print()
        print("=" * 70)
        print("  DIAGNÓSTICO SIN ANCHORS — RESUMEN")
        print("=" * 70)

        dd = self.results["domain_distribution"]
        if dd:
            print()
            print("  DISTRIBUCIÓN DE DOMINIOS:")
            print(f"    Landing URLs encontradas: {dd.get('total_landing_urls', 0)}")
            print(f"    Dominios únicos:           {dd.get('unique_domains', 0)}")
            print()
            print("    Top dominios:")
            for domain, count in list(dd.get("domains", {}).items())[:10]:
                bar = "#" * min(count, 30)
                print(f"      {domain:35s} {count:3d} {bar}")

            conc = dd.get("top_domains_pct", {})
            if conc:
                print()
                print(
                    f"    {conc.get('dominios_para_80pct', '?')} dominios acumulan "
                    f"el 80% de los {conc.get('total_anuncios', 0)} anuncios"
                )
                print(
                    f"    Los primeros 5 dominios concentran el "
                    f"{conc.get('porcentaje_acumulado_primeros_5', 0):.1f}%"
                )

        cta = self.results["cta_click_test"]
        dia = self.results["detail_dialog_test"]

        print()
        print("  TEST CTA CLICK (¿aparecen anchors tras click?):")
        print(f"    Cards testeadas:         {cta.get('total_tested', 0)}")
        print(f"    Anclas aparecieron:      {cta.get('anchors_appeared_after_click', 0)}")
        print(f"    Landing encontrada:      {cta.get('landing_found_after_click', 0)}")

        print()
        print("  TEST DIÁLOGO DE DETALLES:")
        print(f"    Cards testeadas:         {dia.get('total_tested', 0)}")
        print(f"    Diálogo abierto:         {dia.get('dialog_opened', 0)}")
        print(f"    Con anchors en diálogo:  {dia.get('dialog_has_anchors', 0)}")
        print(f"    Landing en diálogo:      {dia.get('dialog_has_landing', 0)}")

        print()
        print(f"  Reporte completo: {OUTPUT_DIR / 'diagnose_results.json'}")
        print("=" * 70)

    def _save_report(self):
        report_path = OUTPUT_DIR / "diagnose_results.json"
        serializable = self._make_serializable(self.results)
        report_path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Reporte guardado en %s", report_path)

    @staticmethod
    def _make_serializable(obj):
        if isinstance(obj, dict):
            return {
                k: SinAnchorsDiagnostic._make_serializable(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [SinAnchorsDiagnostic._make_serializable(v) for v in obj]
        if hasattr(obj, "__dict__"):
            return str(obj)
        return obj


if __name__ == "__main__":
    diag = SinAnchorsDiagnostic(keyword="curso")
    diag.run()
