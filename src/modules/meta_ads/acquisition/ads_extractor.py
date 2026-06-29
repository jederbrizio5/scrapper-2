import logging
from datetime import datetime
from typing import Optional
from playwright.sync_api import Page
from src.modules.meta_ads.dto import Ad, Page as DtoPage, Advertiser, Media

logger = logging.getLogger(__name__)


class AdsExtractor:
    """Responsable de extraer información del DOM y transformarla en DTOs."""

    def __init__(self, page: Page):
        self.page = page

    def extract_first_ad(self) -> Optional[Ad]:
        """Extrae únicamente el primer anuncio visible como prueba de concepto."""
        logger.info("Iniciando extracción del primer anuncio...")

        # Intentos de selectores en orden de especificidad
        selectors = [
            'div[class*="x1yztbdb"]',
            'div[class*="xh8yej3"]',
            "div.x1lliihq",
            'div[role="article"]',
            "div",  # Fallback absoluto
        ]

        ad_elements = []
        for selector in selectors:
            elements = self.page.query_selector_all(selector)
            # Filtramos elementos que tengan suficiente texto para ser un anuncio
            ad_elements = [el for el in elements if len(el.inner_text()) > 50]
            if ad_elements:
                break

        if not ad_elements:
            logger.warning("No se encontraron elementos que parezcan anuncios.")
            return None

        first_ad_el = ad_elements[0]

        try:
            text_content = first_ad_el.inner_text()

            # Nombre de página (intento)
            page_name_el = first_ad_el.query_selector("a span, h4, h3")
            page_name = page_name_el.inner_text() if page_name_el else "Unknown Page"

            # Cuerpo (intento)
            body_el = first_ad_el.query_selector('div[dir="auto"]')
            body_text = body_el.inner_text() if body_el else text_content[:150] + "..."

            # Imagen (intento)
            img_el = first_ad_el.query_selector("img")
            img_url = (
                img_el.get_attribute("src") if img_el else "http://example.com/mock.jpg"
            )

            logger.info("Primer anuncio extraído correctamente.")

            ad_dto = Ad(
                id=f"temp_id_{datetime.now().timestamp()}",
                status="active",
                body=body_text,
                page=DtoPage(id="temp_page_id", name=page_name),
                advertiser=Advertiser(id="temp_page_id", name=page_name),
                media=[Media(type="image", url=img_url)],
            )

            logger.info("DTO generado correctamente.")
            return ad_dto

        except Exception as e:
            logger.error(f"Fallo al extraer el primer anuncio: {e}")
            return None
