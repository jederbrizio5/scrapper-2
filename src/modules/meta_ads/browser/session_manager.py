import logging
from playwright.sync_api import Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class SessionManager:
    """Maneja el contexto del navegador y la sesión."""

    def __init__(self, browser: Browser):
        self.browser = browser
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def create_session(self) -> Page:
        logger.info("Creando nueva sesión (contexto y página)...")
        self.context = self.browser.new_context(
            locale="es-ES", viewport={"width": 1920, "height": 1080}
        )
        self.page = self.context.new_page()
        return self.page

    def close_session(self) -> None:
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        logger.info("Sesión cerrada.")
