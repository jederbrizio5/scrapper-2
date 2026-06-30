import logging
from urllib.parse import urlencode

from playwright.sync_api import Page
from src.modules.meta_ads.client.exceptions import RequestException

logger = logging.getLogger(__name__)


class AdsSearcher:
    """Responsable de interactuar con la página de Meta Ads Library y ejecutar búsquedas."""

    BASE_URL = "https://www.facebook.com/ads/library"

    def __init__(self, page: Page, wait_after_search_ms: int = 7000):
        self.page = page
        self.wait_after_search_ms = wait_after_search_ms

    @staticmethod
    def build_search_url_static(keyword: str) -> str:
        """Construye una URL de busqueda sin necesidad de una instancia."""
        return AdsSearcher.__build_search_url(keyword)

    def build_search_url(self, keyword: str) -> str:
        """Construye una URL de busqueda con filtros estables por query string."""
        return self.__build_search_url(keyword)

    @staticmethod
    def __build_search_url(keyword: str) -> str:
        """Construye una URL de busqueda con filtros estables por query string.

        Args:
            keyword: Texto a buscar en Meta Ads Library.

        Returns:
            URL con todos los paises, todos los anuncios, idioma espanol y orden reciente.
        """
        query = urlencode(
            {
                "active_status": "active",
                "ad_type": "all",
                "content_languages[0]": "es",
                "country": "ALL",
                "is_targeted_country": "false",
                "media_type": "all",
                "q": keyword,
                "search_type": "keyword_unordered",
                "sort_data[direction]": "desc",
                "sort_data[mode]": "relevancy_monthly_grouped",
            }
        )
        return f"{AdsSearcher.BASE_URL}/?{query}"

    def search(self, keyword: str) -> None:
        """Navega a Meta Ads Library y ejecuta la busqueda con filtros requeridos."""
        logger.info(f"Abriendo Meta Ads Library en {self.BASE_URL}...")
        try:
            logger.info(
                'Buscando keyword="%s" country="ALL" ad_type="all" language="es" sort="created_time_desc"',
                keyword,
            )
            search_url = self.build_search_url(keyword)
            self.page.goto(search_url, wait_until="networkidle")

            logger.info("Esperando resultados wait_ms=%s", self.wait_after_search_ms)
            self.page.wait_for_timeout(self.wait_after_search_ms)
            logger.info("Busqueda cargada url=%s", search_url)

        except Exception as e:
            logger.error(f"Error durante la búsqueda: {e}")
            raise RequestException(f"Error interactuando con Meta: {e}")
