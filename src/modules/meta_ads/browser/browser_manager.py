import logging
from typing import Optional
from playwright.sync_api import sync_playwright, Playwright, Browser

logger = logging.getLogger(__name__)


class BrowserManager:
    """Administra la inicialización y cierre del navegador."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    def start(self) -> Browser:
        logger.info(f"Iniciando navegador (headless={self.headless})...")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        return self._browser

    def stop(self) -> None:
        if self._browser:
            self._browser.close()
            logger.info("Navegador cerrado.")
            self._browser = None

        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> Browser:
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
