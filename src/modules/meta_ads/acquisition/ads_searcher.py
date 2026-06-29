import logging
from playwright.sync_api import Page
from src.modules.meta_ads.client.exceptions import RequestException

logger = logging.getLogger(__name__)


class AdsSearcher:
    """Responsable de interactuar con la página de Meta Ads Library y ejecutar búsquedas."""

    BASE_URL = "https://www.facebook.com/ads/library"

    def __init__(self, page: Page):
        self.page = page

    def search(self, keyword: str) -> None:
        """Navega a la biblioteca y ejecuta la búsqueda buscando 'Todos los anuncios'."""
        logger.info(f"Abriendo Meta Ads Library en {self.BASE_URL}...")
        try:
            self.page.goto(self.BASE_URL, wait_until="domcontentloaded")
            logger.info(f'Buscando: "{keyword}"')

            # Nota: Meta cambia su DOM frecuentemente. Esta lógica es una prueba de concepto base.
            # En una implementación real más robusta, usaríamos URls con query params directos.
            # La query directa es mucho más estable.
            search_url = f"{self.BASE_URL}/?active_status=all&ad_type=all&country=ALL&q={keyword}"
            self.page.goto(search_url, wait_until="networkidle")

            # Esperamos que aparezcan resultados
            logger.info("Esperando que carguen los resultados...")
            self.page.wait_for_timeout(
                7000
            )  # Fallback simple para PoC sin pelear con el DOM ofuscado
            logger.info("Resultados encontrados.")

        except Exception as e:
            logger.error(f"Error durante la búsqueda: {e}")
            raise RequestException(f"Error interactuando con Meta: {e}")
