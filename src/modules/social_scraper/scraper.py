import logging
import time
from typing import Optional, Literal
from dataclasses import dataclass

from playwright.sync_api import Page, Browser, BrowserContext

from src.modules.social_scraper.dto import SocialProfileResult
from src.modules.social_scraper.extractors import (
    parse_facebook_profile,
    parse_instagram_profile,
)

logger = logging.getLogger(__name__)

LOGIN_MODAL_SELECTORS = {
    "facebook": [
        'div[role="dialog"]:has-text("Iniciar sesión")',
        'div[role="dialog"]:has-text("Log in")',
        'div[role="dialog"]:has-text("Inicia sesión")',
        'div[xstyle*="modal"]:has-text("Iniciar")',
        '[data-testid="login_dialog"]',
    ],
    "instagram": [
        'div[role="dialog"]:has-text("Iniciar sesión")',
        'div[role="dialog"]:has-text("Log in")',
        'div[role="dialog"]:has-text("Inicia sesión")',
        '[aria-label="Iniciar sesión"]',
    ],
}

CLOSE_MODAL_SELECTORS = {
    "facebook": [
        'div[aria-label="Cerrar"]',
        'div[aria-label="Close"]',
        'div[aria-label="Cerrar diálogo"]',
        'button[aria-label="Cerrar"]',
        'button[aria-label="Close"]',
        '[data-testid="close_button"]',
    ],
    "instagram": [
        'button[aria-label="Close"]',
        'button[aria-label="Cerrar"]',
        'svg[aria-label="Close"]',
        'svg[aria-label="Cerrar"]',
        '[role="button"][tabindex="0"] svg[aria-label="Close"]',
    ],
}


@dataclass
class ScrapeResult:
    """Resultado interno de scraping."""

    success: bool
    profile_data: dict
    error: Optional[str] = None
    status: str = "completed"


class SocialProfileScraper:
    """Scraper de perfiles sociales (Facebook/Instagram) con manejo anti-login."""

    def __init__(
        self,
        browser: Browser,
        context: Optional[BrowserContext] = None,
        timeout: float = 30.0,
        wait_after_load: float = 3.0,
        headless: bool = True,
    ):
        self.browser = browser
        self.context = context
        self.timeout = timeout * 1000  # ms
        self.wait_after_load = wait_after_load
        self.headless = headless
        self._own_context = context is None

    def _create_context(self) -> BrowserContext:
        """Crea un contexto con configuración anti-detección."""
        ctx = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="es-ES",
            timezone_id="America/Argentina/Buenos_Aires",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            },
        )
        # Anti-detection
        ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en']});
            window.chrome = {runtime: {}};
        """)
        return ctx

    def _close_login_modal(
        self, page: Page, platform: Literal["facebook", "instagram"]
    ) -> bool:
        """Intenta cerrar modal de login si aparece."""
        # Primero intentar con Escape
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
        except Exception:
            pass

        # Luego buscar botones de cerrar
        for selector in CLOSE_MODAL_SELECTORS.get(platform, []):
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(1000)
                    logger.debug(
                        f"Cerrado modal login {platform} con selector: {selector}"
                    )
                    return True
            except Exception:
                continue

        # Buscar "Ahora no" / "Not now" en el modal
        try:
            not_now_texts = [
                "Ahora no",
                "Not now",
                "Más tarde",
                "Maybe later",
                "Cancelar",
                "Cancel",
            ]
            for text in not_now_texts:
                btn = page.query_selector(
                    f'button:has-text("{text}"), div[role="button"]:has-text("{text}")'
                )
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(1000)
                    logger.debug(f"Clickeado '{text}' en modal {platform}")
                    return True
        except Exception:
            pass

        return False

    def _detect_login_wall(
        self, page: Page, platform: Literal["facebook", "instagram"]
    ) -> bool:
        """Detecta si hay muro de login bloqueando el contenido."""
        for selector in LOGIN_MODAL_SELECTORS.get(platform, []):
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    return True
            except Exception:
                continue

        # Heurística adicional: poco contenido visible
        try:
            body_text = page.inner_text("body")
            if len(body_text) < 500:
                # Verificar si hay texto de login prominente
                login_indicators = [
                    "Iniciar sesión",
                    "Log in",
                    "Inicia sesión",
                    "Regístrate",
                    "Sign up",
                ]
                if any(ind in body_text for ind in login_indicators):
                    return True
        except Exception:
            pass

        return False

    def _wait_for_content(
        self, page: Page, platform: Literal["facebook", "instagram"]
    ) -> bool:
        """Espera a que cargue el contenido principal del perfil."""
        content_selectors = {
            "facebook": [
                '[data-testid="profile_intro_card_bio"]',
                '[data-pagelet="ProfileTilesFeedUnit_0"]',
                'div[role="main"]',
            ],
            "instagram": [
                'section[aria-label="Profile"]',
                'header[role="banner"]',
                'article[role="presentation"]',
            ],
        }

        for selector in content_selectors.get(platform, []):
            try:
                page.wait_for_selector(selector, timeout=int(self.timeout * 0.5))
                return True
            except Exception:
                continue
        return False

    def scrape_facebook(self, profile_url: str) -> ScrapeResult:
        """Scrapea un perfil de Facebook."""
        if not profile_url.startswith("http"):
            profile_url = f"https://www.facebook.com/{profile_url}"

        context = self.context or self._create_context()
        page = context.new_page()
        page.set_default_timeout(self.timeout)

        try:
            logger.info(f"Scrapeando Facebook: {profile_url}")
            page.goto(profile_url, wait_until="networkidle", timeout=self.timeout)
            page.wait_for_timeout(int(self.wait_after_load * 1000))

            # Manejar login wall
            if self._detect_login_wall(page, "facebook"):
                logger.warning(f"Login wall detectado en Facebook: {profile_url}")
                if self._close_login_modal(page, "facebook"):
                    logger.info("Modal de login cerrado, reintentando extracción")
                    page.wait_for_timeout(2000)
                else:
                    return ScrapeResult(
                        success=False,
                        profile_data={},
                        error="login_required",
                        status="login_required",
                    )

            # Esperar contenido
            self._wait_for_content(page, "facebook")

            # Parsear
            data = parse_facebook_profile(page)
            return ScrapeResult(success=True, profile_data=data, status="completed")

        except Exception as e:
            logger.error(f"Error scrapeando Facebook {profile_url}: {e}")
            return ScrapeResult(
                success=False, profile_data={}, error=str(e), status="failed"
            )
        finally:
            page.close()
            if self._own_context:
                context.close()

    def scrape_instagram(self, profile_url: str) -> ScrapeResult:
        """Scrapea un perfil de Instagram."""
        if not profile_url.startswith("http"):
            profile_url = f"https://www.instagram.com/{profile_url}/"

        context = self.context or self._create_context()
        page = context.new_page()
        page.set_default_timeout(self.timeout)

        try:
            logger.info(f"Scrapeando Instagram: {profile_url}")
            page.goto(profile_url, wait_until="networkidle", timeout=self.timeout)
            page.wait_for_timeout(int(self.wait_after_load * 1000))

            # Manejar login wall
            if self._detect_login_wall(page, "instagram"):
                logger.warning(f"Login wall detectado en Instagram: {profile_url}")
                if self._close_login_modal(page, "instagram"):
                    logger.info("Modal de login cerrado, reintentando extracción")
                    page.wait_for_timeout(2000)
                else:
                    return ScrapeResult(
                        success=False,
                        profile_data={},
                        error="login_required",
                        status="login_required",
                    )

            # Esperar contenido
            self._wait_for_content(page, "instagram")

            # Parsear
            data = parse_instagram_profile(page)
            return ScrapeResult(success=True, profile_data=data, status="completed")

        except Exception as e:
            logger.error(f"Error scrapeando Instagram {profile_url}: {e}")
            return ScrapeResult(
                success=False, profile_data={}, error=str(e), status="failed"
            )
        finally:
            page.close()
            if self._own_context:
                context.close()

    def scrape_both(
        self,
        fb_url: Optional[str] = None,
        ig_url: Optional[str] = None,
    ) -> dict[Literal["facebook", "instagram"], ScrapeResult]:
        """Scrapea ambos perfiles secuencialmente."""
        results = {}

        if fb_url:
            results["facebook"] = self.scrape_facebook(fb_url)
            # Pequeña pausa entre requests
            time.sleep(1)

        if ig_url:
            results["instagram"] = self.scrape_instagram(ig_url)

        return results

    def to_dto(
        self,
        platform: Literal["facebook", "instagram"],
        result: ScrapeResult,
        profile_url: str,
    ) -> SocialProfileResult:
        """Convierte ScrapeResult a SocialProfileResult DTO."""
        from datetime import datetime

        if not result.success:
            return SocialProfileResult(
                platform=platform,
                profile_url=profile_url,
                status=result.status,
                error=result.error,
                scraped_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S hs"),
            )

        data = result.profile_data
        return SocialProfileResult(
            platform=platform,
            profile_url=profile_url,
            username=data.get("username"),
            bio=data.get("bio"),
            followers_count=data.get("followers_count"),
            following_count=data.get("following_count"),
            posts_count=data.get("posts_count"),
            is_verified=data.get("is_verified", False),
            is_business_account=data.get("is_business_account", False),
            category=data.get("category"),
            profile_image_url=data.get("profile_image_url"),
            external_links=data.get("external_links", []),
            status="completed",
            scraped_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S hs"),
        )
