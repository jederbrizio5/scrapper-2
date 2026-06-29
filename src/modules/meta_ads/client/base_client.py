import logging
import requests
from src.modules.meta_ads.client.exceptions import RequestException

logger = logging.getLogger(__name__)


class BaseClient:
    """Cliente HTTP base genérico para peticiones, con logging estructurado."""

    def __init__(self, base_url: str, headers: dict = None, timeout: int = 30):
        self.base_url = base_url
        self.headers = headers or {}
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get(self, endpoint: str, params: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}" if endpoint else self.base_url
        logger.info(f"Iniciando GET a {url} con params: {params}")

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            logger.info(f"Fin GET a {url}. Status: {response.status_code}")
            return response
        except requests.RequestException as e:
            logger.error(f"Error de red en GET {url}: {str(e)}")
            raise RequestException(f"Error de red: {str(e)}")
