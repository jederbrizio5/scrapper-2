import logging
from src.config.settings import settings
from src.modules.meta_ads.client.base_client import BaseClient
from src.modules.meta_ads.client.exceptions import (
    AuthenticationException,
    RateLimitException,
    MetaException,
)
from src.modules.meta_ads.dto import SearchRequest, SearchResponse
from src.modules.meta_ads.parser.parser import MetaParser

logger = logging.getLogger(__name__)


class MetaClient(BaseClient):
    """Cliente específico para Meta Ads Library."""

    def __init__(self):
        headers = {"User-Agent": settings.META_USER_AGENT, "Accept": "application/json"}
        super().__init__(
            base_url=settings.META_ADS_API_URL,
            headers=headers,
            timeout=settings.META_TIMEOUT_SECONDS,
        )
        self.access_token = settings.META_ACCESS_TOKEN

        if not self.access_token:
            logger.warning("META_ACCESS_TOKEN no está configurado.")

    def search_ads(self, request: SearchRequest) -> SearchResponse:
        """Busca anuncios en Meta Ads Library devolviendo DTOs."""
        params = {
            "search_terms": request.keyword,
            "ad_reached_countries": f"['{request.country}']"
            if request.country != "ALL"
            else "['ALL']",
            "search_type": "KEYWORD_UNORDERED",
            "access_token": self.access_token,
            "limit": request.limit,
        }

        # Omitimos el idioma porque la Graph API base no soporta directamente el filtro
        # en el endpoint de /ads_archive salvo configuraciones específicas,
        # pero recibimos el parámetro para compatibilidad futura.
        if request.cursor:
            params["after"] = request.cursor

        logger.info(f"Buscando anuncios para keyword '{request.keyword}'")

        response = self._get("", params=params)

        # Manejo de errores específicos
        if response.status_code == 401:
            raise AuthenticationException("Token de acceso inválido o expirado.")
        elif response.status_code == 429:
            raise RateLimitException(
                "Se excedió el límite de peticiones de la API de Meta."
            )
        elif response.status_code != 200:
            error_message = response.text
            logger.error(
                f"Error de Meta API: HTTP {response.status_code} - {error_message}"
            )
            raise MetaException(f"Error de Meta API (HTTP {response.status_code})")

        try:
            data = response.json()
        except ValueError as e:
            raise MetaException(f"Respuesta de Meta no es JSON válido: {str(e)}")

        return MetaParser.parse_search_response(data)
