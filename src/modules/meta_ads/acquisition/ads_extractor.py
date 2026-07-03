import logging
import random
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import ElementHandle, Page
from src.modules.meta_ads.dto import (
    Ad,
    Advertiser,
    BrowserAdDiscovery,
    BrowserAdEnrichment,
    BrowserAdResult,
    Media,
    Page as DtoPage,
)

ARG_TZ = timezone(timedelta(hours=-3))
logger = logging.getLogger(__name__)


class AdsExtractor:
    """Extrae anuncios de Meta Ads Library en dos etapas.

    Discovery: toma datos visibles del listado (solo anuncios con landing externa).
    Enrichment: abre el detalle del anuncio para obtener datos del anunciante.
    """

    BLOCKED_DOMAINS = (
        "facebook.com",
        "fb.com",
        "fb.me",
        "instagram.com",
        "messenger.com",
        "m.me",
        "wa.me",
        "wa.link",
        "whatsapp.com",
        "metastatus.com",
        "about.fb.com",
        "transparency.fb.com",
        "privacymanager.io",
        "forms.gle",
        "forms.google.com",
        "docs.google.com",
        "drive.google.com",
        "youtube.com",
        "youtu.be",
        "tiktok.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "t.me",
        "telegram.org",
        "bit.ly",
        "tinyurl.com",
        "goo.gl",
        "ig.me",
    )

    DETAIL_BUTTON_TEXTS = (
        "Ver detalles del anuncio",
        "See ad details",
        "Detalles del anuncio",
        "Ad details",
        "Ver detalles del resumen",
        "Ver más",
        "See more",
    )

    UI_NOISE_LINES = (
        "Informe de la biblioteca",
        "API de la biblioteca",
        "Buscar por palabra clave",
        "Todos los anuncios",
        "Ver detalles del anuncio",
        "Ver detalles",
        "Ver resumen",
        "Ver más",
        "Ver Mas",
        "Enviar mensaje de WhatsApp",
        "Enviar mensaje",
        "Más información",
        "Mas informacion",
        "Número de impresiones bajo",
        "Numero de impresiones bajo",
        "Impresiones:",
        "Impresiones: ",
        "Transparencia UE",
        "Transparencia de la",
        "Contenido de marca",
        "Publicidad",
        "Patrocinado",
        "Abrir menú",
        "Este anuncio tiene varias versiones",
        "Este anuncio tiene",
        "Chatea en Messenger",
        "Chatea con nosotros",
        "Send Message",
        "Send WhatsApp Message",
        "Chat on Messenger",
        "Call Now",
        "Llamar ahora",
        "Registrarse",
        "Sign Up",
        "Shop Now",
        "Learn More",
        "See Details",
        "Obtener oferta",
        "Obtener oferta",
        "Contact Us",
        "Comprar",
        "Reserva tu plaza",
        "Reservar",
        "Visita el sitio web",
        "<100",
        "0:00",
        "anuncios usan este contenido",
        "Ir al perfil",
        "API.WHATSAPP.COM",
        "FB.COM",
    )

    JITTER_RATIO = 0.3

    SHORT_URL_DOMAINS = ("bit.ly", "tinyurl.com", "goo.gl")

    _short_url_cache: dict[str, str] = {}

    class MetaBlockedError(Exception):
        """Meta bloqueo la IP, pide login o detecto automatizacion."""

    def __init__(
        self,
        page: Page,
        action_delay_ms: int = 1200,
        extra_blocked_domains: set[str] | None = None,
        action_timeout: int = 30000,
    ):
        self.page = page
        self.action_delay_ms = action_delay_ms
        self.action_timeout = action_timeout
        self.page.set_default_timeout(action_timeout)
        extra = extra_blocked_domains or set()
        self._blocked_domains = tuple(sorted(set(self.BLOCKED_DOMAINS) | extra))
        self.stats = {
            "cards_found": 0,
            "cards_processed": 0,
            "discarded_cta": 0,
            "discarded_blocked_domain": 0,
            "discarded_no_landing": 0,
            "short_urls_resolved": 0,
        }

    def check_blocked(self):
        """Detecta si Meta bloqueo la IP o pide login.

        Lanza MetaBlockedError si encuentra sennales en el body.
        """
        try:
            body = self.page.inner_text("body")
            signals = [
                "iniciar sesion",
                "log in",
                "bloqueado",
                "blocked",
                "verifica tu identidad",
                "confirm your identity",
                "demasiadas solicitudes",
                "too many requests",
            ]
            for sig in signals:
                if sig in body.lower():
                    logger.warning("Meta bloqueo detectado: '%s'", sig)
                    raise self.MetaBlockedError(f"Meta blocked: '{sig}'")
        except self.MetaBlockedError:
            raise
        except Exception:
            pass

    def _jittered_delay(self, base_ms: int | None = None) -> int:
        base = base_ms if base_ms is not None else self.action_delay_ms
        jitter = int(base * self.JITTER_RATIO * random.random())
        return base + jitter

    def extract_first_ad(self) -> Ad | None:
        """Mantiene compatibilidad con la PoC anterior devolviendo un DTO generico."""
        discoveries = self.extract_discovery_ads(keyword="poc", limit=1)
        if not discoveries:
            return None

        discovery = discoveries[0]
        return Ad(
            id=discovery.library_id,
            creation_time=datetime.now(),
            status="active",
            body=discovery.description or "",
            page=DtoPage(id=discovery.library_id, name=discovery.domain),
            advertiser=Advertiser(
                id=discovery.library_id,
                name=discovery.advertiser_name or discovery.domain,
            ),
            media=[Media(type="landing", url=discovery.landing_url)],
        )

    SUMMARY_BUTTON_TEXTS: tuple[str, ...] = (
        "Ver detalles del resumen",
        "Ver resumen",
    )

    def _expand_summaries(self) -> None:
        """Expande cards agrupados clickeando 'Ver detalles del resumen' / 'Ver más'.

        Algunos anuncios aparecen agrupados bajo un card resumen que requiere
        un click para revelar los anuncios individuales con su propio library_id.
        """
        for text in self.SUMMARY_BUTTON_TEXTS:
            try:
                buttons = self.page.query_selector_all(
                    f'button:text-is("{text}"), [role=button]:text-is("{text}"), div:text-is("{text}")'
                )
                for btn in buttons:
                    try:
                        if not self.page.evaluate(
                            "el => el.offsetParent !== null", btn
                        ):
                            continue
                        logger.debug("Expandiendo resumen: '%s'", text)
                        self._native_click(btn)
                        self.page.wait_for_timeout(800)
                    except Exception:
                        continue
            except Exception:
                continue
        self.page.wait_for_timeout(1500)

    def extract_discovery_ads(
        self,
        keyword: str,
        limit: int = 3,
        skip_library_ids: set[str] | None = None,
    ) -> list[BrowserAdDiscovery]:
        """Extrae anuncios visibles que tengan una landing externa válida.

        Args:
            keyword: Término de búsqueda actual.
            limit: Máximo de descubrimientos a devolver.
            skip_library_ids: Conjunto de library_id ya procesados en
                iteraciones anteriores (scrolls previos). Estos cards se
                saltan antes de la extracción costosa (query_selector_all).
        """
        skip = set(skip_library_ids) if skip_library_ids else set()
        self._expand_summaries()
        cards = self._candidate_cards()
        self.stats["cards_found"] += len(cards)
        logger.info("Candidatos encontrados keyword=%s count=%s", keyword, len(cards))

        discoveries: list[BrowserAdDiscovery] = []
        for card in cards:
            if len(discoveries) >= limit:
                break

            text = self._safe_inner_text(card)
            library_id = self._extract_library_id(text)
            if not library_id or library_id in skip:
                continue

            self.stats["cards_processed"] += 1
            discovery = self._extract_discovery_from_card(card, keyword)
            if not discovery:
                continue

            skip.add(discovery.library_id)
            discoveries.append(discovery)

        logger.info(
            "Extraccion discovery finalizada keyword=%s valid_ads=%s requested=%s "
            "stats=%s",
            keyword,
            len(discoveries),
            limit,
            self._format_stats(),
        )
        return discoveries

    def _format_stats(self) -> str:
        return (
            f"cards_found={self.stats['cards_found']} "
            f"processed={self.stats['cards_processed']} "
            f"no_landing={self.stats['discarded_no_landing']} "
            f"cta={self.stats['discarded_cta']} "
            f"blocked={self.stats['discarded_blocked_domain']} "
            f"short_urls={self.stats['short_urls_resolved']}"
        )

    def enrich_ads(
        self, discoveries: list[BrowserAdDiscovery]
    ) -> list[BrowserAdResult]:
        """Abre detalles de cada anuncio navegando a su URL individual.

        Despues del scroll las cards del discovery ya no estan en el DOM,
        por eso navegamos a la URL de cada ad en vez de buscar cards en la pagina actual.
        """
        logger.info(
            "Enriqueciendo %d discoveries navegando a cada URL", len(discoveries)
        )
        results: list[BrowserAdResult] = []

        for i, discovery in enumerate(discoveries, 1):
            enrichment = None
            try:
                self.page.goto(discovery.ad_library_url, wait_until="networkidle")
                self.page.wait_for_timeout(3000)

                cards = self._candidate_cards()
                card = self._find_card_by_library_id(cards, discovery.library_id)
                if card:
                    enrichment = self._extract_enrichment_from_card(
                        card, discovery.library_id
                    )

                logger.info(
                    "[%d/%d] Enriquecido library_id=%s %s",
                    i,
                    len(discoveries),
                    discovery.library_id,
                    "OK"
                    if enrichment
                    and (enrichment.facebook_user or enrichment.instagram_user)
                    else "sin datos",
                )
            except Exception as exc:
                logger.warning(
                    "Error enriqueciendo library_id=%s error=%s",
                    discovery.library_id,
                    exc,
                )

            results.append(BrowserAdResult(discovery=discovery, enrichment=enrichment))

        return results

    def _candidate_cards(self) -> list[ElementHandle]:
        """Busca cards individuales de anuncios en la página.

        Usa múltiples selectores y valida que cada elemento contenga
        un Library ID y no sea un contenedor padre.
        """
        selectors = [
            'div[role="article"]',
            'div[data-testid="library-ad-card"]',
        ]

        for selector in selectors:
            try:
                elements = self.page.query_selector_all(selector)
            except Exception as exc:
                logger.debug("Selector fallo selector=%s error=%s", selector, exc)
                continue

            filtered = self._filter_valid_cards(elements)
            if filtered:
                logger.info(
                    "Selector usado selector=%s cards=%s",
                    selector,
                    len(filtered),
                )
                return filtered

        all_elements = self.page.query_selector_all("div")
        filtered = self._filter_valid_cards(all_elements)
        if filtered:
            logger.info("Selector fallback div cards=%s", len(filtered))

        return filtered

    def _filter_valid_cards(self, elements: list[ElementHandle]) -> list[ElementHandle]:
        """Filtra elementos que sean cards válidas de anuncios."""
        valid = []
        for element in elements:
            text = self._safe_inner_text(element)
            if not text:
                continue

            has_library_id = (
                "Identificador de la biblioteca" in text or "Library ID" in text
            )
            if not has_library_id:
                continue

            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if len(lines) < 3:
                continue

            if len(text) > 5000:
                continue

            valid.append(element)

        return valid

    def _extract_discovery_from_card(
        self, card: ElementHandle, keyword: str
    ) -> BrowserAdDiscovery | None:
        text = self._safe_inner_text(card)
        library_id = self._extract_library_id(text)
        if not library_id:
            return None

        had_engagement = any(
            self._is_engagement_href(a) for a in card.query_selector_all("a[href]")
        )

        landing_url = self._extract_landing_url(card)
        if not landing_url:
            if had_engagement:
                self.stats["discarded_cta"] += 1
            else:
                self.stats["discarded_no_landing"] += 1
            logger.debug(
                "Anuncio descartado sin landing externa library_id=%s", library_id
            )
            return None

        landing_url = self._resolve_short_url(landing_url)

        domain = self._domain_from_url(landing_url)
        if self._is_blocked_domain(domain):
            self.stats["discarded_blocked_domain"] += 1
            logger.debug(
                "Anuncio descartado por dominio bloqueado library_id=%s domain=%s",
                library_id,
                domain,
            )
            return None

        advertiser_name = self._extract_advertiser_name(text)
        description = self._extract_ad_description(
            text, advertiser_name=advertiser_name
        )

        return BrowserAdDiscovery(
            keyword=keyword,
            library_id=library_id,
            description=description,
            circulation_start=self._extract_circulation_start(text),
            landing_url=landing_url,
            domain=domain,
            ad_library_url=f"https://www.facebook.com/ads/library/?id={library_id}",
            advertiser_name=advertiser_name,
            extracted_at=datetime.now(ARG_TZ).strftime("%d/%m/%Y %H:%M:%S hs"),
        )

    def _extract_enrichment_from_card(
        self, card: ElementHandle, library_id: str
    ) -> BrowserAdEnrichment | None:
        step = "init"
        try:
            button = self._find_detail_button(card)

            if button:
                step = "click_outer"
                self._native_click(button)
                self.page.wait_for_timeout(self._jittered_delay() + 2000)

            step = "find_dialog"
            detail_dialog = self._find_detail_dialog()

            if not detail_dialog:
                logger.warning("Dialog no encontrado library_id=%s", library_id)
                try:
                    self.page.screenshot(
                        path=f"debug_enrich_{library_id}.png", full_page=True
                    )
                except Exception:
                    pass
                self._close_details()
                return BrowserAdEnrichment(
                    library_id=library_id,
                    extracted_at=datetime.now(ARG_TZ).strftime("%d/%m/%Y %H:%M:%S hs"),
                )

            # Expand: clic al boton "Ver detalles del anuncio" DENTRO del dialogo
            # (el primer click abre el dialogo "Vincular con un anuncio",
            #  este segundo click revela la seccion del anunciante)
            step = "expand_inner"
            self._click_inner_detail_button(detail_dialog)

            step = "click_heading"
            self._click_advertiser_heading(detail_dialog)
            self.page.wait_for_timeout(1500)

            full_text = self._safe_inner_text(detail_dialog)
            fb_user, ig_user = self._parse_social_from_advertiser_section(full_text)
            fb_followers, ig_followers = self._parse_followers_from_advertiser_section(
                full_text
            )
            self._close_details()

            return BrowserAdEnrichment(
                library_id=library_id,
                facebook_user=fb_user,
                instagram_user=ig_user,
                facebook_followers=fb_followers,
                instagram_followers=ig_followers,
                advertiser_info=full_text[:2000] if full_text else None,
                extracted_at=datetime.now(ARG_TZ).strftime("%d/%m/%Y %H:%M:%S hs"),
            )
        except Exception as exc:
            logger.warning(
                "Excepcion en enrichment library_id=%s step=%s error=%s",
                library_id,
                step,
                exc,
            )
            self._close_details()
            return BrowserAdEnrichment(
                library_id=library_id,
                extracted_at=datetime.now(ARG_TZ).strftime("%d/%m/%Y %H:%M:%S hs"),
            )

    def _find_card_by_library_id(
        self, cards: list[ElementHandle], library_id: str
    ) -> ElementHandle | None:
        for card in cards:
            if library_id in self._safe_inner_text(card):
                return card
        return None

    def _native_click(self, element: ElementHandle, timeout: int = 5000) -> None:
        elem_text = ""
        try:
            elem_text = f" ({element.inner_text()[:50].strip()})"
        except Exception:
            pass
        try:
            element.evaluate("el => el.click()")
            logger.debug("Native JS click OK%s", elem_text)
        except Exception:
            logger.debug("Fallback click force%s", elem_text)
            element.click(timeout=timeout, force=True)

    def _click_inner_detail_button(self, dialog: ElementHandle) -> None:
        """Clickea 'Ver detalles del anuncio' dentro del dialogo para expandir info del anunciante."""
        for text in self.DETAIL_BUTTON_TEXTS:
            try:
                btn = dialog.query_selector(f'text="{text}"')
                if btn:
                    try:
                        self._native_click(btn)
                        self.page.wait_for_timeout(2000)
                    except Exception:
                        pass
                    return
            except Exception:
                continue

        for text in self.DETAIL_BUTTON_TEXTS:
            for _ in range(10):
                try:
                    btn = dialog.query_selector(f'text="{text}"')
                    if btn:
                        self._native_click(btn)
                        self.page.wait_for_timeout(2000)
                        return
                except Exception:
                    pass
                self.page.wait_for_timeout(500)

        try:
            buttons = dialog.query_selector_all("button, [role=button]")
            for btn in buttons:
                btn_text = self._safe_inner_text(btn).strip()
                if any(t.lower() in btn_text.lower() for t in self.DETAIL_BUTTON_TEXTS):
                    try:
                        self._native_click(btn)
                        self.page.wait_for_timeout(2000)
                    except Exception:
                        pass
                    return
        except Exception:
            pass

    def _find_detail_button(self, card: ElementHandle) -> ElementHandle | None:
        for text in self.DETAIL_BUTTON_TEXTS:
            button = card.query_selector(f'text="{text}"')
            if button:
                return button

        try:
            buttons = card.query_selector_all("button, [role=button]")
            for btn in buttons:
                btn_text = self._safe_inner_text(btn).strip()
                if any(t.lower() in btn_text.lower() for t in self.DETAIL_BUTTON_TEXTS):
                    return btn
        except Exception:
            pass

        return None

    def _enter_from_summary(self) -> ElementHandle | None:
        for selector in (
            'div[role="dialog"]',
            'div[aria-modal="true"]',
            'div[data-testid="ad-details-panel"]',
        ):
            try:
                elements = (
                    self.page.query_selector_all(selector)
                    if "role" in selector or "testid" in selector
                    else [self.page.query_selector(selector)]
                )
                for element in (
                    elements
                    if isinstance(elements, list)
                    else [elements]
                    if elements
                    else []
                ):
                    try:
                        text = self._safe_inner_text(element)
                        if "Ver detalles del anuncio" not in text:
                            continue
                        summary_id = id(element)
                        buttons = element.query_selector_all("button, [role=button]")
                        for btn in buttons:
                            btn_text = self._safe_inner_text(btn).strip()
                            if "detalles del anuncio" in btn_text.lower():
                                self._native_click(btn)
                                self.page.wait_for_timeout(
                                    self._jittered_delay() + 2000
                                )
                                detail = self._find_detail_dialog(exclude_id=summary_id)
                                if detail:
                                    return detail
                                if (
                                    "Información sobre el anunciante"
                                    in self._safe_inner_text(element)
                                ):
                                    return element
                                return element
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    def _find_detail_dialog(
        self, *, exclude_id: int | None = None
    ) -> ElementHandle | None:
        # Strategy 1: role=dialog (standard popup)
        # Preferir el dialog completo "Detalles del anuncio" sobre
        # el dialog limitado "Vincular con un anuncio".
        # Ambos contienen "Detalles del anuncio" (el limitado tiene el boton
        # "Ver detalles del anuncio"), asi que hay que excluir por "Vincular".
        dialogs = self.page.query_selector_all('div[role="dialog"]')

        # Phase 1: buscar dialog completo (tiene info del anunciante)
        for dialog in dialogs:
            try:
                if exclude_id is not None and id(dialog) == exclude_id:
                    continue
                text = self._safe_inner_text(dialog)
                if any(
                    t in text
                    for t in (
                        "Detalles del anuncio",
                        "Ad details",
                        "Información sobre el anunciante",
                    )
                ) and not any(
                    t in text
                    for t in (
                        "Vincular con un anuncio",
                        "Link to an ad",
                    )
                ):
                    logger.debug("Dialog encontrado via texto=Detalles del anuncio")
                    return dialog
            except Exception:
                continue

        # Phase 2: fallback al dialog limitado "Vincular con un anuncio"
        for dialog in dialogs:
            try:
                if exclude_id is not None and id(dialog) == exclude_id:
                    continue
                text = self._safe_inner_text(dialog)
                if any(
                    t in text
                    for t in (
                        "Vincular con un anuncio",
                        "Link to an ad",
                    )
                ):
                    logger.debug("Dialog encontrado via texto=Vincular con un anuncio")
                    return dialog
            except Exception:
                continue

        # Strategy 2: aria-modal or aria-label panels (used on ?id=... pages)
        for selector in (
            'div[aria-modal="true"]',
            'div[aria-label="Detalles"]',
            'div[aria-label="Details"]',
            'div[aria-label="Detalles del anuncio"]',
            'div[data-testid="ad-details-panel"]',
        ):
            try:
                container = self.page.query_selector(selector)
                if container is not None:
                    logger.debug("Dialog encontrado via selector=%s", selector)
                    return container
            except Exception:
                continue

        # Strategy 3: section/div with advertiser heading text
        try:
            for selector in ("section", 'div[role="complementary"]', "aside"):
                elements = self.page.query_selector_all(selector)
                for el in elements:
                    try:
                        text = self._safe_inner_text(el)
                        if (
                            "Información sobre el anunciante" in text
                            or "Advertiser Information" in text
                        ):
                            logger.debug(
                                "Dialog encontrado via texto advertiser en %s", selector
                            )
                            return el
                    except Exception:
                        continue
        except Exception:
            pass

        # Strategy 4: any visible element containing the advertiser heading
        # (some ads embed details inline instead of a modal dialog)
        try:
            body = self.page.query_selector("body")
            if body:
                for candidate in body.query_selector_all("div, section, article"):
                    try:
                        ct = self._safe_inner_text(candidate)
                        if (
                            "Información sobre el anunciante" in ct
                            or "Advertiser Information" in ct
                        ):
                            logger.debug(
                                "Dialog encontrado via texto advertiser en body fallback"
                            )
                            return candidate
                    except Exception:
                        continue
        except Exception:
            pass

        return None

    def _click_advertiser_heading(self, dialog: ElementHandle) -> None:
        headings = dialog.query_selector_all("h1, h2, h3, h4, [role=heading]")
        for heading in headings:
            ht = self._safe_inner_text(heading).strip()
            if "anunciante" in ht.lower() or "advertiser" in ht.lower():
                self._native_click(heading, timeout=3000)
                return

    @staticmethod
    def _parse_followers_count(raw: str) -> str:
        """Convierte texto de seguidores a numero.

        Maneja formatos:
          "1260" -> "1260"
          "2,1 mil" -> "2100"       (decimal comma + mil)
          "229,4 mil" -> "229400"
          "1,4 mill" -> "1400000"   (decimal comma + mill = millones)
          "159 mil" -> "159000"
          "275,7 mil" -> "275700"
          "1.473 mil" -> "1473000"  (dot thousands separator + mil)
        """
        has_mil = "mil" in raw.lower()
        has_mill = "mill" in raw.lower()

        cleaned = raw.strip()
        cleaned = re.sub(r"\s*(?:mil|mill)[^a-z]*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        # Spanish decimal comma -> dot
        cleaned = cleaned.replace(",", ".")
        # Remove thousands separator dots (followed by exactly 3 digits)
        cleaned = re.sub(r"\.(\d{3})", r"\1", cleaned)

        m = re.search(r"[\d.]+", cleaned)
        if not m:
            return raw

        num_str = m.group(0)

        if has_mill:
            return str(int(float(num_str) * 1000000))
        if has_mil:
            return str(int(float(num_str) * 1000))
        return str(int(float(num_str)))

    def _parse_social_from_advertiser_section(
        self, text: str
    ) -> tuple[str | None, str | None]:
        fb_user = None
        ig_user = None

        advertiser_section = False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if (
                "Información sobre el anunciante" in stripped
                or "Advertiser Information" in stripped
            ):
                advertiser_section = True
                continue
            if not advertiser_section:
                continue

            id_match = re.search(r"Identificador:\s*(\d+)", stripped)
            if id_match:
                fb_user = id_match.group(1)
                continue

            at_match = re.search(r"@(\w+)", stripped)
            if at_match:
                if not fb_user:
                    fb_user = at_match.group(1)
                elif not ig_user:
                    ig_user = at_match.group(1)

        return fb_user, ig_user

    def _parse_followers_from_advertiser_section(
        self, text: str
    ) -> tuple[str | None, str | None]:
        fb_followers = None
        ig_followers = None

        advertiser_section = False
        seen_fb = False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if (
                "Información sobre el anunciante" in stripped
                or "Advertiser Information" in stripped
            ):
                advertiser_section = True
                continue
            if not advertiser_section:
                continue

            followers_match = re.search(
                r"([\d\.,]+(?:\s*(?:mil|mill)[^\d]*)?)\s*seguidores",
                stripped,
                re.IGNORECASE,
            )
            if followers_match:
                raw = followers_match.group(1)
                count = self._parse_followers_count(raw)
                if not seen_fb:
                    fb_followers = count
                    seen_fb = True
                else:
                    ig_followers = count

        return fb_followers, ig_followers

    def _details_container(self) -> ElementHandle | None:
        dialogs = self.page.query_selector_all('div[role="dialog"]')
        for dialog in dialogs:
            try:
                text = self._safe_inner_text(dialog)
                if "Detalles del anuncio" in text or "Ad details" in text:
                    return dialog
            except Exception:
                continue
        for selector in (
            'div[aria-modal="true"]',
            'div[aria-label="Detalles"]',
            'div[aria-label="Details"]',
        ):
            container = self.page.query_selector(selector)
            if container:
                return container
        return None

    def _details_text(self) -> str:
        container = self._details_container()
        if container:
            return self._safe_inner_text(container)
        return ""

    def _details_links(self) -> list[str]:
        container = self._details_container()
        if not container:
            return []
        links: list[str] = []
        for anchor in container.query_selector_all("a[href]"):
            href = anchor.get_attribute("href")
            if href:
                links.append(href)
        return links

    def _close_details(self) -> None:
        for selector in (
            'div[aria-label="Cerrar"]',
            'div[aria-label="Close"]',
            'div[aria-label="Cerrar diálogo"]',
        ):
            button = self.page.query_selector(selector)
            if button:
                button.click(timeout=3000)
                self.page.wait_for_timeout(500)
                return

        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(500)
        except Exception:
            return

    def _extract_landing_url(self, card: ElementHandle) -> str | None:
        all_anchors = card.query_selector_all("a[href]")

        if any(self._is_engagement_href(anchor) for anchor in all_anchors):
            return None

        button_links = card.query_selector_all("button a[href], [role=button] a[href]")
        for anchor in button_links:
            href = anchor.get_attribute("href")
            if not href:
                continue
            normalized = self._normalize_url(href)
            if normalized and self._is_external_landing(normalized):
                return normalized

        for anchor in all_anchors:
            href = anchor.get_attribute("href")
            if not href:
                continue
            normalized = self._normalize_url(href)
            if normalized and self._is_external_landing(normalized):
                return normalized
        return None

    @staticmethod
    def _is_engagement_href(anchor: ElementHandle) -> bool:
        href = (anchor.get_attribute("href") or "").lower()
        for pattern in (
            "wa.me",
            "wa.link",
            "whatsapp.com",
            "m.me",
            "messenger.com",
            "tel:",
        ):
            if pattern in href:
                return True
        return False

    def _extract_library_id(self, text: str) -> str | None:
        patterns = [
            r"Identificador de la biblioteca[:\s]+(\d+)",
            r"Library ID[:\s]+(\d+)",
            r"ID de la biblioteca[:\s]+(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_circulation_start(self, text: str) -> str | None:
        patterns = [
            r"En circulaci[oó]n desde[^\n]*",
            r"Started running on[^\n]*",
            r"Activo desde[^\n]*",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    def _extract_advertiser_name(self, text: str) -> str | None:
        """Extrae el nombre del anunciante desde el texto del card.

        El nombre del anunciante aparece típicamente antes del
        Identificador de la biblioteca.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        library_id_idx = -1
        for i, line in enumerate(lines):
            if "Identificador de la biblioteca" in line or "Library ID" in line:
                library_id_idx = i
                break

        skip_prefixes = (
            "Activo",
            "Inactivo",
            "Patrocinado",
            "En circulaci",
            "Plataformas",
            "Categorías",
            "Categorias",
            "Tags",
            "Sistema",
            "Todos",
            "API",
            "Transparencia",
        )

        def _is_valid_name(candidate: str) -> bool:
            if self._is_noise_line(candidate):
                return False
            if len(candidate) < 3 or len(candidate) > 100:
                return False
            if re.match(r"^\d+$", candidate):
                return False
            if any(candidate.startswith(p) for p in skip_prefixes):
                return False
            if candidate.startswith("http") or candidate.startswith("www."):
                return False
            if any(kw in candidate.lower() for kw in self.SOCIAL_DOMAIN_KEYWORDS):
                return False
            if re.match(
                r"^\d+\s*(millones|mill|mil|k|m)?\s*seguidores",
                candidate,
                re.IGNORECASE,
            ):
                return False
            if "anuncios usan este contenido" in candidate.lower():
                return False
            return True

        if library_id_idx >= 0:
            for j in range(library_id_idx - 1, -1, -1):
                candidate = lines[j]
                if _is_valid_name(candidate):
                    return candidate

            for line in lines[library_id_idx + 1 :]:
                if _is_valid_name(line):
                    return line

        return None

    _DISPLAY_URL_RE = re.compile(r"^[A-Z][A-Z0-9./-]{2,59}$")

    def _extract_ad_description(
        self, text: str, *, advertiser_name: str | None = None
    ) -> str | None:
        """Extrae solo el texto del anuncio (creative copy).

        Busca el contenido publicitario que aparece después del
        identificador de la biblioteca, excluyendo ruido de la UI.
        Corta en cuanto detecta una línea propia del footer
        (display URL, página, etc.) para no arrastrar secciones
        posteriores del card.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        library_id_idx = -1
        for i, line in enumerate(lines):
            if "Identificador de la biblioteca" in line or "Library ID" in line:
                library_id_idx = i
                break

        if library_id_idx < 0:
            return None

        ad_lines = []
        for line in lines[library_id_idx + 1 :]:
            if self._is_noise_line(line):
                continue
            if len(line) < 3:
                continue
            if re.match(r"^\d+$", line):
                continue
            if re.match(
                r"^(En circulaci[oó]n|Started running|Activo|Inactivo|Plataformas)",
                line,
                re.IGNORECASE,
            ):
                continue
            if self._contains_url(line):
                break
            if re.match(
                r"^\d+\s*(millones|mill|mil|k|m)?\s*seguidores", line, re.IGNORECASE
            ):
                continue
            if advertiser_name and line.strip() == advertiser_name:
                continue
            if line.upper() in ("FB.COM", "API.WHATSAPP.COM"):
                continue
            if "anuncios usan este contenido" in line.lower():
                continue
            if self._DISPLAY_URL_RE.match(line) and "." in line:
                break
            if re.search(r"\d+%\s*(OFF|off|desc|Dto|Dto\.)", line):
                break
            ad_lines.append(line)

        if not ad_lines:
            return None

        return "\n".join(ad_lines) if ad_lines else None

    def _is_noise_line(self, line: str) -> bool:
        """Determina si una línea es ruido de la interfaz de Meta."""
        line_lower = line.lower().strip()
        return any(
            line_lower.startswith(noise.lower()) for noise in self.UI_NOISE_LINES
        )

    FB_NON_USER_PATHS = (
        "policies",
        "help",
        "privacy",
        "terms",
        "about",
        "login",
        "groups",
        "pages",
        "events",
        "marketplace",
        "gaming",
        "watch",
        "news",
        "fundraiser",
        "messenger",
        "business",
        "developers",
        "careers",
        "ads",
        "ad_library",
    )

    IG_NON_USER_PATHS = (
        "p",
        "reel",
        "stories",
        "explore",
        "accounts",
        "directory",
    )

    SOCIAL_DOMAIN_KEYWORDS = (
        "facebook.com",
        "fb.com",
        "fb.me",
        "instagram.com",
        "wa.me",
        "wa.link",
        "whatsapp.com",
        "m.me",
        "t.me",
        "telegram.org",
        "tiktok.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "youtube.com",
        "youtu.be",
    )

    def _extract_social_users(self, links: list[str]) -> tuple[str | None, str | None]:
        fb_user = None
        ig_user = None
        for link in links:
            normalized = self._normalize_url(link)
            if not normalized:
                continue
            parsed = urlparse(normalized)
            if "facebook.com" in parsed.netloc and "/ads/" not in parsed.path:
                parts = [part for part in parsed.path.split("/") if part]
                if (
                    parts
                    and parts[0].strip()
                    and parts[0] != "ads"
                    and parts[0].lower() not in self.FB_NON_USER_PATHS
                ):
                    fb_user = parts[0]
            if "instagram.com" in parsed.netloc:
                parts = [part for part in parsed.path.split("/") if part]
                if (
                    parts
                    and parts[0].strip()
                    and parts[0].lower() not in self.IG_NON_USER_PATHS
                ):
                    ig_user = parts[0]
        return fb_user, ig_user

    def _extract_followers_per_platform(
        self, text: str
    ) -> tuple[str | None, str | None]:
        fb_followers = None
        ig_followers = None
        sections = re.split(r"\n{2,}", text)
        for section in sections:
            lower = section.lower()
            pattern = r"([\d\.,]+\s*(?:millones|mill|mil|k|m)?\s*seguidores)"
            match = re.search(pattern, section, flags=re.IGNORECASE)
            if not match:
                continue
            followers_text = match.group(1).strip()
            if "facebook" in lower or "fb" in lower:
                fb_followers = followers_text
            elif "instagram" in lower or "ig" in lower:
                ig_followers = followers_text
            else:
                if fb_followers is None:
                    fb_followers = followers_text
                elif ig_followers is None:
                    ig_followers = followers_text
        return fb_followers, ig_followers

    def _normalize_url(self, url: str) -> str | None:
        if url.startswith("/"):
            url = f"https://www.facebook.com{url}"

        parsed = urlparse(url)
        if parsed.netloc in {"l.facebook.com", "lm.facebook.com"}:
            target = parse_qs(parsed.query).get("u", [None])[0]
            if target:
                return target

        if parsed.scheme not in {"http", "https"}:
            return None

        return parsed._replace(fragment="").geturl()

    def _resolve_short_url(self, url: str) -> str:
        """Sigue redirecciones para URLs acortadas (bit.ly, tinyurl, goo.gl).

        Usa cache global para evitar resolver la misma URL dos veces.
        """
        domain = self._domain_from_url(url)
        if domain not in self.SHORT_URL_DOMAINS:
            return url

        cached = self._short_url_cache.get(url)
        if cached is not None:
            logger.debug("URL acortada cache %s -> %s", url, cached)
            return cached

        try:
            req = urllib.request.Request(
                url,
                method="HEAD",
                headers={"User-Agent": "Mozilla/5.0 (compatible)"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                resolved = resp.url
                self._short_url_cache[url] = resolved
                logger.debug("URL acortada resuelta %s -> %s", url, resolved)
                self.stats["short_urls_resolved"] += 1
                return resolved
        except Exception as exc:
            self._short_url_cache[url] = url
            logger.debug("No se pudo resolver URL acortada %s error=%s", url, exc)
            return url

    def _is_external_landing(self, url: str) -> bool:
        domain = self._domain_from_url(url)
        return bool(domain) and not self._is_blocked_domain(domain)

    def _is_blocked_domain(self, domain: str) -> bool:
        return any(
            domain == blocked or domain.endswith(f".{blocked}")
            for blocked in self._blocked_domains
        )

    def _domain_from_url(self, url: str) -> str:
        return urlparse(url).netloc.lower().removeprefix("www.")

    @staticmethod
    def _contains_url(line: str) -> bool:
        stripped = line.lstrip()
        if not stripped:
            return False
        first_word = stripped.split()[0].lower()
        if first_word.startswith("http"):
            return True
        if first_word.startswith("www."):
            return True
        return False

    def _safe_inner_text(self, element: ElementHandle) -> str:
        try:
            return element.inner_text().strip()
        except Exception:
            return ""
