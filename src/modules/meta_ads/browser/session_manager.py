import logging
import random

from playwright.sync_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

BASE_VIEWPORT = {"width": 1920, "height": 1080}
VIEWPORT_JITTER = 20

EXTRA_HEADERS = {
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

WEBDRIVER_OVERRIDE_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en'] });
// Override chrome runtime
window.chrome = { runtime: {} };
"""


class SessionManager:
    """Maneja el contexto del navegador y la pagina.

    Aplica medidas antidetectión: User-Agent realista, override de
    navigator.webdriver, viewport con variación mínima y headers realistas.
    """

    def __init__(self, browser: Browser, user_agent: str | None = None):
        self.browser = browser
        self.user_agent = user_agent
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def create_session(self) -> Page:
        logger.info("Creando sesion (contexto y pagina)...")

        viewport = {
            "width": BASE_VIEWPORT["width"]
            + random.randint(-VIEWPORT_JITTER, VIEWPORT_JITTER),
            "height": BASE_VIEWPORT["height"]
            + random.randint(-VIEWPORT_JITTER, VIEWPORT_JITTER),
        }

        context_args = {
            "locale": "es-ES",
            "viewport": viewport,
            "extra_http_headers": dict(EXTRA_HEADERS),
        }
        if self.user_agent:
            context_args["user_agent"] = self.user_agent

        self.context = self.browser.new_context(**context_args)
        self.page = self.context.new_page()
        self.page.add_init_script(WEBDRIVER_OVERRIDE_SCRIPT)
        return self.page

    def close_session(self) -> None:
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        logger.info("Sesion cerrada.")
