import logging
from typing import Optional
from playwright.sync_api import sync_playwright, Playwright, Browser

logger = logging.getLogger(__name__)


class BrowserManager:
    """Administra la inicialización y cierre del navegador.

    Soporta modo debug con navegador visible, ejecución lenta y logs detallados.
    """

    def __init__(
        self,
        headless: bool = True,
        debug_mode: bool = False,
        slow_mo_ms: int = 0,
    ):
        self.headless = headless
        self.debug_mode = debug_mode
        self.slow_mo_ms = slow_mo_ms
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    def start(self) -> Browser:
        effective_headless = False if self.debug_mode else self.headless
        effective_slow_mo = (
            max(self.slow_mo_ms, 200) if self.debug_mode else self.slow_mo_ms
        )

        logger.info(
            "Iniciando navegador headless=%s debug=%s slow_mo=%sms",
            effective_headless,
            self.debug_mode,
            effective_slow_mo,
        )

        self._playwright = sync_playwright().start()
        launch_args = ["--disable-blink-features=AutomationControlled"]
        if self.debug_mode:
            launch_args.append("--start-maximized")

        self._browser = self._playwright.chromium.launch(
            headless=effective_headless,
            slow_mo=effective_slow_mo,
            args=launch_args,
        )

        if self.debug_mode:
            logger.info(
                "Modo debug activo: navegador visible, ejecucion lenta, "
                "logs detallados habilitados"
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
