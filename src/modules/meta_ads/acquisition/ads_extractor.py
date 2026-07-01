import logging
import random
import re
from datetime import datetime
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
        "Send Message",
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
        "<100",
        "0:00",
        "anuncios usan este contenido",
        "Ir al perfil",
        "API.WHATSAPP.COM",
        "FB.COM",
    )

    JITTER_RATIO = 0.3

    def __init__(self, page: Page, action_delay_ms: int = 1200):
        self.page = page
        self.action_delay_ms = action_delay_ms

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

    def extract_discovery_ads(
        self, keyword: str, limit: int = 3
    ) -> list[BrowserAdDiscovery]:
        """Extrae anuncios visibles que tengan una landing externa válida."""
        cards = self._candidate_cards()
        logger.info("Candidatos encontrados keyword=%s count=%s", keyword, len(cards))

        discoveries: list[BrowserAdDiscovery] = []
        seen_library_ids: set[str] = set()
        for card in cards:
            if len(discoveries) >= limit:
                break

            discovery = self._extract_discovery_from_card(card, keyword)
            if not discovery:
                continue
            if discovery.library_id in seen_library_ids:
                logger.debug(
                    "Descartando duplicado library_id=%s", discovery.library_id
                )
                continue

            seen_library_ids.add(discovery.library_id)
            discoveries.append(discovery)

        logger.info(
            "Extraccion discovery finalizada keyword=%s valid_ads=%s requested=%s",
            keyword,
            len(discoveries),
            limit,
        )
        return discoveries

    def enrich_ads(
        self, discoveries: list[BrowserAdDiscovery]
    ) -> list[BrowserAdResult]:
        """Abre detalles de anuncios seleccionados y agrega datos del anunciante."""
        cards = self._candidate_cards()
        logger.info("Cards para enriquecer count=%s", len(cards))
        results: list[BrowserAdResult] = []

        for discovery in discoveries:
            card = self._find_card_by_library_id(cards, discovery.library_id)
            if not card:
                logger.warning(
                    "No se encontro card para enriquecer library_id=%s",
                    discovery.library_id,
                )
            enrichment = None
            if card:
                enrichment = self._extract_enrichment_from_card(
                    card, discovery.library_id
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

        landing_url = self._extract_landing_url(card)
        if not landing_url:
            logger.debug(
                "Anuncio descartado sin landing externa library_id=%s", library_id
            )
            return None

        domain = self._domain_from_url(landing_url)
        if self._is_blocked_domain(domain):
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
        )

    def _extract_enrichment_from_card(
        self, card: ElementHandle, library_id: str
    ) -> BrowserAdEnrichment | None:
        try:
            button = self._find_detail_button(card)
            if not button:
                logger.warning(
                    "Boton de detalle no encontrado library_id=%s", library_id
                )
                return BrowserAdEnrichment(library_id=library_id)

            button.click(timeout=5000, force=True)
            self.page.wait_for_timeout(self._jittered_delay())

            btn_text = self._safe_inner_text(button).strip()
            if "resumen" in btn_text.lower():
                detail_dialog = self._enter_from_summary()
            else:
                detail_dialog = self._find_detail_dialog()

            if not detail_dialog:
                logger.warning(
                    "Dialog de detalles no encontrado library_id=%s", library_id
                )
                self._close_details()
                return BrowserAdEnrichment(library_id=library_id)

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
            )
        except Exception as exc:
            logger.warning(
                "No se pudo enriquecer library_id=%s error=%s", library_id, exc
            )
            self._close_details()
            return BrowserAdEnrichment(library_id=library_id)

    def _find_card_by_library_id(
        self, cards: list[ElementHandle], library_id: str
    ) -> ElementHandle | None:
        for card in cards:
            if library_id in self._safe_inner_text(card):
                return card
        return None

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
        dialogs = self.page.query_selector_all('div[role="dialog"]')
        for dialog in dialogs:
            try:
                text = self._safe_inner_text(dialog)
                if "Ver detalles del anuncio" not in text:
                    continue
                summary_id = id(dialog)
                buttons = dialog.query_selector_all("button, [role=button]")
                for btn in buttons:
                    btn_text = self._safe_inner_text(btn).strip()
                    if "detalles del anuncio" in btn_text.lower():
                        btn.click(timeout=5000, force=True)
                        self.page.wait_for_timeout(self._jittered_delay() + 2000)
                        detail = self._find_detail_dialog(exclude_id=summary_id)
                        if detail:
                            return detail
                        if "Información sobre el anunciante" in self._safe_inner_text(
                            dialog
                        ):
                            return dialog
                        return dialog
            except Exception:
                continue
        return None

    def _find_detail_dialog(
        self, *, exclude_id: int | None = None
    ) -> ElementHandle | None:
        dialogs = self.page.query_selector_all('div[role="dialog"]')
        for dialog in dialogs:
            try:
                if exclude_id is not None and id(dialog) == exclude_id:
                    continue
                text = self._safe_inner_text(dialog)
                if "Detalles del anuncio" in text or "Ad details" in text:
                    return dialog
            except Exception:
                continue
        return None

    def _click_advertiser_heading(self, dialog: ElementHandle) -> None:
        headings = dialog.query_selector_all("[role=heading]")
        for heading in headings:
            ht = self._safe_inner_text(heading).strip()
            if "anunciante" in ht.lower() or "advertiser" in ht.lower():
                heading.click(timeout=3000, force=True)
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
        anchors = card.query_selector_all("a[href]")
        for anchor in anchors:
            href = anchor.get_attribute("href")
            if not href:
                continue

            normalized = self._normalize_url(href)
            if normalized and self._is_external_landing(normalized):
                return normalized
        return None

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

    def _extract_ad_description(
        self, text: str, *, advertiser_name: str | None = None
    ) -> str | None:
        """Extrae solo el texto del anuncio (creative copy).

        Busca el contenido publicitario que aparece después del
        identificador de la biblioteca, excluyendo ruido de la UI.
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
            if line.startswith("http"):
                continue
            if line.startswith("www."):
                continue
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

    def _is_external_landing(self, url: str) -> bool:
        domain = self._domain_from_url(url)
        return bool(domain) and not self._is_blocked_domain(domain)

    def _is_blocked_domain(self, domain: str) -> bool:
        return any(
            domain == blocked or domain.endswith(f".{blocked}")
            for blocked in self.BLOCKED_DOMAINS
        )

    def _domain_from_url(self, url: str) -> str:
        return urlparse(url).netloc.lower().removeprefix("www.")

    def _safe_inner_text(self, element: ElementHandle) -> str:
        try:
            return element.inner_text().strip()
        except Exception:
            return ""
