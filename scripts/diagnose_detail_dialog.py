#!/usr/bin/env python
"""Diagnóstico: ¿el diálogo de detalles contiene landing URLs?

Corrige el diagnóstico anterior que testeaba elementos hijo sin botón.
Ahora:
1. Encuentra cards VERDADERAS (las que tienen botón "Ver detalles")
2. Para cada una, extrae landing URL normal (desde el card)
3. Abre el diálogo y verifica SI HAY landing URL adicional/allí
4. Compara: ¿el diálogo aporta landings que no se ven en el card?
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
        logging.FileHandler("logs/diagnose_detail_dialog.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("dialog_diag")

OUTPUT_DIR = Path("output/audit")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class DetailDialogDiagnostic:
    """Diagnostica si el diálogo de detalles revela landing URLs ocultas."""

    def __init__(self, keyword="curso"):
        self.keyword = keyword
        self.results = {
            "keyword": keyword,
            "cards_tested": [],
            "summary": {
                "total_cards_con_landing_en_card": 0,
                "total_cards_sin_landing_en_card": 0,
                "dialog_revelo_landing_nueva": 0,
                "dialog_confirmo_misma_landing": 0,
                "dialog_sin_landing": 0,
                "total_unique_domains_in_card": 0,
                "total_unique_domains_in_dialog": 0,
            },
            "domain_distribution": {},
        }

    def run(self):
        bm = BrowserManager(headless=False, debug_mode=True, slow_mo_ms=0)
        with bm as browser:
            sm = SessionManager(browser, user_agent=bm.user_agent)
            page = sm.create_session()
            try:
                searcher = AdsSearcher(page=page, wait_after_search_ms=7000)
                extractor = AdsExtractor(page=page, action_delay_ms=1200)

                logger.info(
                    "=== DIAGNÓSTICO DETALLE DIALOG keyword=%s ===", self.keyword
                )
                searcher.search(self.keyword)

                # Scrolls para tener variedad de cards
                for i in range(6):
                    y = (i + 1) * 700
                    page.evaluate(
                        f"window.scrollTo({{top: {y}, behavior: 'smooth'}})"
                    )
                    page.wait_for_timeout(2000)

                page.wait_for_timeout(2000)

                # Encontrar cards CON botón de detalles
                self._find_and_test_cards(page, extractor)

                # Medir distribución
                self._measure_domain_distribution(page, extractor)

            finally:
                sm.close_session()

        self._save_report()
        self._print_summary()

    def _find_and_test_cards(self, page, extractor):
        """Encuentra cards con botón de detalles y las testea."""
        cards = extractor._candidate_cards()
        logger.info("Cards candidatas total: %d", len(cards))

        # Agrupar por library_id para evitar duplicados hijo/padre
        cards_by_lib = {}
        for card in cards:
            text = extractor._safe_inner_text(card)
            lib = extractor._extract_library_id(text)
            if not lib:
                continue
            # Guardar la card con más texto (la del padre, no el hijo)
            if lib not in cards_by_lib or len(text) > len(
                extractor._safe_inner_text(cards_by_lib[lib])
            ):
                cards_by_lib[lib] = card

        logger.info("Cards únicas por library_id: %d", len(cards_by_lib))

        # De esas, filtrar las que tienen botón de detalles
        testable = []
        for lib_id, card in cards_by_lib.items():
            button = extractor._find_detail_button(card)
            if button:
                testable.append((lib_id, card, button))
                if len(testable) >= 30:
                    break

        logger.info(
            "Cards con botón de detalles: %d (testeando hasta 30)", len(testable)
        )

        # Testear cada una
        for i, (lib_id, card, button) in enumerate(testable):
            logger.info(
                "--- Card %d/%d library_id=%s ---", i + 1, len(testable), lib_id
            )
            self._test_card(page, extractor, card, lib_id)

    def _test_card(self, page, extractor, card, library_id):
        """Para una card: extrae landing del card, luego del diálogo."""
        result = {
            "library_id": library_id,
            "advertiser": None,
            "landing_from_card": None,
            "domain_from_card": None,
            "dialog_opened": False,
            "anchors_in_dialog": 0,
            "landing_from_dialog": None,
            "domain_from_dialog": None,
            "dialog_matched_card": None,
            "error": None,
        }

        # ---- 1. Landing desde el card (flujo normal) ----
        landing_card = extractor._extract_landing_url(card)
        if landing_card:
            result["landing_from_card"] = landing_card
            result["domain_from_card"] = extractor._domain_from_url(landing_card)

        text = extractor._safe_inner_text(card)
        result["advertiser"] = extractor._extract_advertiser_name(text)

        # ---- 2. Abrir diálogo de detalles ----
        try:
            button = extractor._find_detail_button(card)
            if not button:
                result["error"] = "no_detail_button_after_find"
                self.results["cards_tested"].append(result)
                return

            btn_text = extractor._safe_inner_text(button).strip()
            button.click(timeout=5000, force=True)
            page.wait_for_timeout(2000)

            if "resumen" in btn_text.lower():
                detail_dialog = extractor._enter_from_summary()
            else:
                detail_dialog = extractor._find_detail_dialog()

            if not detail_dialog:
                result["error"] = "dialog_not_found"
                extractor._close_details()
                self.results["cards_tested"].append(result)
                return

            result["dialog_opened"] = True

            # Buscar anchors en el diálogo
            anchors = detail_dialog.query_selector_all("a[href]")
            result["anchors_in_dialog"] = len(anchors)

            for anchor in anchors:
                href = anchor.get_attribute("href") or ""
                normalized = extractor._normalize_url(href)
                if normalized and extractor._is_external_landing(normalized):
                    result["landing_from_dialog"] = normalized
                    result["domain_from_dialog"] = extractor._domain_from_url(
                        normalized
                    )

                    # ¿Es la misma landing que la del card?
                    if result["landing_from_card"]:
                        match = normalized == result["landing_from_card"]
                        result["dialog_matched_card"] = match
                    else:
                        result["dialog_matched_card"] = False
                    break

            extractor._close_details()

        except Exception as e:
            result["error"] = str(e)[:100]
            try:
                extractor._close_details()
            except Exception:
                pass

        # ---- Registrar resultados ----
        self.results["cards_tested"].append(result)

        if result["landing_from_card"]:
            self.results["summary"]["total_cards_con_landing_en_card"] += 1
        else:
            self.results["summary"]["total_cards_sin_landing_en_card"] += 1

        if result["landing_from_dialog"]:
            if not result["landing_from_card"]:
                self.results["summary"]["dialog_revelo_landing_nueva"] += 1
                logger.info(
                    "  >>> DIÁLOGO REVELÓ LANDING NUEVA: %s",
                    result["landing_from_dialog"],
                )
            elif result.get("dialog_matched_card"):
                self.results["summary"]["dialog_confirmo_misma_landing"] += 1
                logger.info(
                    "  >> Diálogo confirmó misma landing: %s",
                    result["landing_from_dialog"],
                )
        else:
            self.results["summary"]["dialog_sin_landing"] += 1
            if result["landing_from_card"]:
                logger.info(
                    "  Card tenía landing, diálogo sin landing nueva"
                )
            else:
                logger.info(
                    "  Card sin landing, diálogo tampoco tiene"
                )

    def _measure_domain_distribution(self, page, extractor):
        """Mide distribución de dominios en cards con landing."""
        cards = extractor._candidate_cards()
        domains_in_card = Counter()
        domains_in_dialog = Counter()
        total_landings = 0

        for card in cards:
            text = extractor._safe_inner_text(card)
            lib = extractor._extract_library_id(text)
            if not lib:
                continue

            landing = extractor._extract_landing_url(card)
            if landing:
                domain = extractor._domain_from_url(landing)
                if not extractor._is_blocked_domain(domain):
                    domains_in_card[domain] += 1
                    total_landings += 1

        self.results["domain_distribution"] = {
            "total_landing_urls": total_landings,
            "unique_domains_en_card": len(domains_in_card),
            "domains_en_card": dict(domains_in_card.most_common(20)),
        }
        self.results["summary"]["total_unique_domains_in_card"] = len(
            domains_in_card
        )

    def _print_summary(self):
        s = self.results["summary"]
        print()
        print("=" * 70)
        print("  DIAGNÓSTICO DETALLE DIALOG — RESUMEN")
        print("=" * 70)

        dd = self.results.get("domain_distribution", {})
        if dd:
            print()
            print("  DISTRIBUCIÓN DE DOMINIOS:")
            print(
                f"    Landing URLs totales: {dd.get('total_landing_urls', 0)}"
            )
            print(
                f"    Dominios únicos:       {dd.get('unique_domains_en_card', 0)}"
            )
            print()
            print("    Top dominios:")
            for domain, count in list(
                dd.get("domains_en_card", {}).items()
            )[:10]:
                bar = "#" * min(count, 30)
                print(f"      {domain:35s} {count:3d} {bar}")

        print()
        print("  RESULTADOS DEL TESTEO:")
        print(
            f"    Cards con landing en card:     {s['total_cards_con_landing_en_card']}"
        )
        print(
            f"    Cards SIN landing en card:      {s['total_cards_sin_landing_en_card']}"
        )
        print()
        print(f"    Diálogo reveló landing NUEVA:   {s['dialog_revelo_landing_nueva']}")
        print(
            f"    Diálogo confirmó misma landing: {s['dialog_confirmo_misma_landing']}"
        )
        print(f"    Diálogo sin landing:            {s['dialog_sin_landing']}")

        # Ratio de efectividad
        total_con_dialogo = (
            s["dialog_revelo_landing_nueva"]
            + s["dialog_confirmo_misma_landing"]
            + s["dialog_sin_landing"]
        )
        if total_con_dialogo > 0:
            pct = s["dialog_revelo_landing_nueva"] / total_con_dialogo * 100
            print()
            print(
                f"  EFECTIVIDAD: {pct:.0f}% de las cards SIN landing en card"
            )
            print(
                "  tienen landing accesible por diálogo."
            )
            if pct > 30:
                print("  RECOMENDACIÓN: Implementar extracción desde diálogo.")
                print("  Viabilidad: ALTA (el diálogo aporta landings nuevas).")
            else:
                print("  RECOMENDACIÓN: No implementar extracción desde diálogo.")
                print("  El diálogo casi nunca aporta landings nuevas.")
                print("  El cuello de botella es la densidad de Meta, no el algoritmo.")

        print()
        print("=" * 70)

    def _save_report(self):
        report_path = OUTPUT_DIR / "diagnose_detail_dialog.json"
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
                k: DetailDialogDiagnostic._make_serializable(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [
                DetailDialogDiagnostic._make_serializable(v) for v in obj
            ]
        if hasattr(obj, "__dict__"):
            return str(obj)
        return obj


if __name__ == "__main__":
    diag = DetailDialogDiagnostic(keyword="curso")
    diag.run()
