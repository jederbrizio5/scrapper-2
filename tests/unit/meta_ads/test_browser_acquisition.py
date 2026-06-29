from unittest.mock import MagicMock, patch
from src.modules.meta_ads.browser.browser_manager import BrowserManager
from src.modules.meta_ads.acquisition.ads_extractor import AdsExtractor
from src.modules.meta_ads.dto import Ad


@patch("src.modules.meta_ads.browser.browser_manager.sync_playwright")
def test_browser_manager(mock_sync_playwright):
    # Mocking
    mock_playwright_instance = MagicMock()
    mock_browser = MagicMock()
    mock_sync_playwright.return_value.start.return_value = mock_playwright_instance
    mock_playwright_instance.chromium.launch.return_value = mock_browser

    manager = BrowserManager(headless=True)

    # Test start
    browser = manager.start()
    assert browser == mock_browser
    mock_playwright_instance.chromium.launch.assert_called_once_with(
        headless=True, args=["--disable-blink-features=AutomationControlled"]
    )

    # Test stop
    manager.stop()
    mock_browser.close.assert_called_once()
    mock_playwright_instance.stop.assert_called_once()


def test_ads_extractor():
    # Mock de Page
    mock_page = MagicMock()
    mock_element = MagicMock()

    # Configuramos el query_selector_all
    mock_page.query_selector_all.return_value = [mock_element]

    # Configuramos query_selector
    mock_element.inner_text.return_value = (
        "Texto del anuncio base con contenido suficiente para superar "
        "el filtro minimo del extractor."
    )

    mock_page_name = MagicMock()
    mock_page_name.inner_text.return_value = "Mocked Page"

    mock_body = MagicMock()
    mock_body.inner_text.return_value = "Mocked Body"

    mock_img = MagicMock()
    mock_img.get_attribute.return_value = "http://mock.img"

    def mock_query_selector(selector):
        if "span" in selector:
            return mock_page_name
        elif "dir" in selector:
            return mock_body
        elif "img" in selector:
            return mock_img
        return None

    mock_element.query_selector.side_effect = mock_query_selector

    extractor = AdsExtractor(mock_page)
    ad = extractor.extract_first_ad()

    assert ad is not None
    assert isinstance(ad, Ad)
    assert ad.page.name == "Mocked Page"
    assert ad.body == "Mocked Body"
    assert ad.media[0].url == "http://mock.img"
