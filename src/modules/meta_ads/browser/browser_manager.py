import logging
from typing import Optional
from playwright.sync_api import sync_playwright, Playwright, Browser

logger = logging.getLogger(__name__)

REALISTIC_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

ANTI_DETECTION_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-session-crashed-bubble",
    "--disable-crash-reporter",
    "--no-first-run",
    "--no-default-browser-check",
    "--no-sandbox",
    "--disable-infobars",
    "--disable-gpu",
    "--disable-dev-shm-usage",
]


class BrowserManager:
    """Administra la inicialización y cierre del navegador.

    Incorpora medidas antidetectión: User-Agent realista, flags anti-bot
    y modo debug para inspección visual.
    """

    def __init__(
        self,
        headless: bool = True,
        debug_mode: bool = False,
        slow_mo_ms: int = 0,
        user_agent: str | None = None,
    ):
        self.headless = headless
        self.debug_mode = debug_mode
        self.slow_mo_ms = slow_mo_ms
        self.user_agent = user_agent or REALISTIC_USER_AGENT
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
        logger.debug("User-Agent: %s", self.user_agent)

        self._playwright = sync_playwright().start()
        launch_args = list(ANTI_DETECTION_ARGS)
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
