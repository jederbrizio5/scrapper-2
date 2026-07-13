import hashlib
import logging
import time
from typing import Optional

import httpx
from playwright.sync_api import Browser

from src.modules.landing_scraper.dto import LandingExtractionResult
from src.modules.landing_scraper.extractors import (
    extract_emails,
    extract_phones,
    extract_whatsapp_urls,
    extract_social_urls,
    extract_pricing_urls,
    extract_pricing_text,
    extract_country,
    extract_addresses,
    extract_tech_stack,
    extract_forms,
    detect_spa,
    infer_price_range,
)

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


class LandingScraper:
    """Scraper de landing pages con estrategia dual: httpx (rápido) + Playwright fallback."""

    def __init__(
        self,
        timeout_httpx: float = 15.0,
        timeout_pw: float = 30.0,
        delay_between_requests: float = 2.0,
        max_retries: int = 2,
        user_agent: str = DEFAULT_HEADERS["User-Agent"],
        follow_redirects: bool = True,
        verify_ssl: bool = True,
        playwright_browser: Optional[Browser] = None,
        save_html: bool = False,
    ):
        self.timeout_httpx = timeout_httpx
        self.timeout_pw = timeout_pw
        self.delay_between_requests = delay_between_requests
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.follow_redirects = follow_redirects
        self.verify_ssl = verify_ssl
        self.playwright_browser = playwright_browser
        self.save_html = save_html

        self._httpx_client: Optional[httpx.Client] = None
        self._last_request_time = 0.0

    def __enter__(self):
        self._httpx_client = httpx.Client(
            timeout=httpx.Timeout(self.timeout_httpx),
            follow_redirects=self.follow_redirects,
            verify=self.verify_ssl,
            headers={"User-Agent": self.user_agent},
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._httpx_client:
            self._httpx_client.close()
        self._httpx_client = None

    def _normalize_url(self, url: str) -> str:
        """Normaliza URL asegurando esquema."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def _rate_limit(self):
        """Rate limiting simple entre requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.delay_between_requests:
            time.sleep(self.delay_between_requests - elapsed)
        self._last_request_time = time.time()

    def scrape(self, url: str) -> LandingExtractionResult:
        """Scrapea una landing page con fallback automático."""
        url = self._normalize_url(url)
        self._rate_limit()

        result = LandingExtractionResult(url=url)

        # Intentar httpx primero
        try:
            result = self._scrape_httpx(url)
            if result.status == "completed":
                # Verificar si parece SPA y necesita Playwright
                if self.playwright_browser and detect_spa(result.raw_html or ""):
                    logger.info(
                        f"SPA detectada en {url}, intentando Playwright fallback"
                    )
                    pw_result = self._scrape_playwright(url)
                    if pw_result.status == "completed":
                        # Merge: mantener emails/phones de httpx si PW no los tiene
                        pw_result.emails = pw_result.emails or result.emails
                        pw_result.phones = pw_result.phones or result.phones
                        pw_result.method = "playwright_fallback"
                        return pw_result
                return result
        except Exception as e:
            logger.warning(f"httpx falló para {url}: {e}")

        # Fallback a Playwright si disponible
        if self.playwright_browser:
            try:
                result = self._scrape_playwright(url)
                result.method = "playwright"
                return result
            except Exception as e:
                logger.error(f"Playwright falló para {url}: {e}")
                result.status = "failed"
                result.error = f"playwright_error: {e}"
                return result

        result.status = "failed"
        result.error = "all_methods_failed"
        return result

    def _scrape_httpx(self, url: str) -> LandingExtractionResult:
        """Scrapea usando httpx (rápido, sin JS)."""
        result = LandingExtractionResult(url=url, method="httpx")
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = self._httpx_client.get(url)
                resp.raise_for_status()

                html = resp.text
                final_url = str(resp.url)

                # Guardar HTML si solicitado
                if self.save_html:
                    result.raw_html = html
                    result.raw_html_hash = hashlib.sha256(html.encode()).hexdigest()[
                        :16
                    ]

                # Extraer todo
                self._extract_all(html, final_url, result)
                result.status = "completed"
                return result

            except httpx.TimeoutException as e:
                last_error = f"timeout: {e}"
                logger.warning(
                    f"Timeout httpx {url} (intento {attempt + 1}/{self.max_retries + 1})"
                )
            except httpx.HTTPStatusError as e:
                last_error = f"http_{e.response.status_code}"
                if e.response.status_code >= 500:
                    logger.warning(f"Error 5xx {url}: {e}")
                else:
                    # 4xx no reintentar
                    result.status = "failed"
                    result.error = f"http_{e.response.status_code}"
                    return result
            except httpx.RequestError as e:
                last_error = f"request_error: {e}"
                logger.warning(f"Error de red httpx {url}: {e}")
            except Exception as e:
                last_error = f"unexpected: {e}"
                logger.error(f"Error inesperado httpx {url}: {e}")

            if attempt < self.max_retries:
                time.sleep(2**attempt)  # Backoff exponencial

        result.status = "failed"
        result.error = last_error or "unknown_httpx_error"
        return result

    def _scrape_playwright(self, url: str) -> LandingExtractionResult:
        """Scrapea usando Playwright (para SPAs y sitios con JS)."""
        result = LandingExtractionResult(url=url, method="playwright")

        html = self._playwright_fetch_sync(url)

        if html:
            if self.save_html:
                result.raw_html = html
                result.raw_html_hash = hashlib.sha256(html.encode()).hexdigest()[:16]

            self._extract_all(html, url, result)
            result.status = "completed"
        else:
            result.status = "failed"
            result.error = "playwright_no_content"

        return result

    def _playwright_fetch_sync(self, url: str) -> Optional[str]:
        """Fetch síncrono con Playwright (para thread pool)."""
        if not self.playwright_browser:
            return None

        try:
            page = self.playwright_browser.new_page()
            page.set_default_timeout(int(self.timeout_pw * 1000))
            page.goto(
                url, wait_until="networkidle", timeout=int(self.timeout_pw * 1000)
            )
            # Esperar un poco más para JS lazy-loaded
            page.wait_for_timeout(2000)
            html = page.content()
            page.close()
            return html
        except Exception as e:
            logger.warning(f"Playwright fetch failed {url}: {e}")
            return None

    def _extract_all(self, html: str, base_url: str, result: LandingExtractionResult):
        """Ejecuta todos los extractores sobre el HTML."""
        # Contacto
        result.emails = extract_emails(html, base_url)
        result.phones = extract_phones(html, base_url)
        result.whatsapp_urls = extract_whatsapp_urls(html, base_url)

        # Social links
        social = extract_social_urls(html, base_url)
        result.facebook_urls = social.get("facebook", [])
        result.instagram_urls = social.get("instagram", [])
        result.linkedin_urls = social.get("linkedin", [])
        result.twitter_urls = social.get("twitter", [])
        result.tiktok_urls = social.get("tiktok", [])
        result.youtube_urls = social.get("youtube", [])

        # Pricing
        result.pricing_urls = extract_pricing_urls(html, base_url)
        result.pricing_text_matches = extract_pricing_text(html)
        result.price_range = infer_price_range(result.pricing_text_matches)

        # Geo
        result.country_code, result.country_confidence = extract_country(
            html, result.phones
        )
        result.addresses = extract_addresses(html)

        # Tech & Forms
        result.tech_stack = extract_tech_stack(html)
        forms = extract_forms(html)
        result.has_contact_form = "contact" in forms
        result.has_newsletter_form = "newsletter" in forms
        result.has_checkout_form = "checkout" in forms


def scrape_single(url: str, **kwargs) -> LandingExtractionResult:
    """Función de conveniencia para scrapeo único."""
    with LandingScraper(**kwargs) as scraper:
        return scraper.scrape(url)


def scrape_batch(urls: list[str], **kwargs) -> list[LandingExtractionResult]:
    """Scrapea múltiples URLs en batch con rate limiting compartido."""
    with LandingScraper(**kwargs) as scraper:
        results = []
        for url in urls:
            results.append(scraper.scrape(url))
        return results
