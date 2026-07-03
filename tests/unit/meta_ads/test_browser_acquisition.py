import json
from unittest.mock import MagicMock, patch

from src.modules.meta_ads.acquisition.ads_extractor import AdsExtractor
from src.modules.meta_ads.acquisition.ads_searcher import AdsSearcher
from src.modules.meta_ads.browser.browser_manager import (
    ANTI_DETECTION_ARGS,
    BrowserManager,
)
from src.modules.meta_ads.dto import Ad, BrowserAdDiscovery, BrowserAdResult


@patch("src.modules.meta_ads.browser.browser_manager.sync_playwright")
def test_browser_manager(mock_sync_playwright):
    mock_playwright_instance = MagicMock()
    mock_browser = MagicMock()
    mock_sync_playwright.return_value.start.return_value = mock_playwright_instance
    mock_playwright_instance.chromium.launch.return_value = mock_browser

    manager = BrowserManager(headless=True)

    browser = manager.start()
    assert browser == mock_browser
    mock_playwright_instance.chromium.launch.assert_called_once_with(
        headless=True, slow_mo=0, args=ANTI_DETECTION_ARGS
    )

    manager.stop()
    mock_browser.close.assert_called_once()
    mock_playwright_instance.stop.assert_called_once()


@patch("src.modules.meta_ads.browser.browser_manager.sync_playwright")
def test_browser_manager_debug_mode(mock_sync_playwright):
    mock_playwright_instance = MagicMock()
    mock_browser = MagicMock()
    mock_sync_playwright.return_value.start.return_value = mock_playwright_instance
    mock_playwright_instance.chromium.launch.return_value = mock_browser

    manager = BrowserManager(headless=True, debug_mode=True, slow_mo_ms=100)

    browser = manager.start()
    assert browser == mock_browser
    call_kwargs = mock_playwright_instance.chromium.launch.call_args[1]
    assert call_kwargs["headless"] is False
    assert call_kwargs["slow_mo"] == 200
    assert "--start-maximized" in call_kwargs["args"]


def test_ads_extractor():
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"
    mock_page.query_selector_all.return_value = [
        _mock_card(hrefs=["https://landing.example.com/curso"], library_id="123")
    ]

    extractor = AdsExtractor(mock_page)
    ad = extractor.extract_first_ad()

    assert ad is not None
    assert isinstance(ad, Ad)
    assert ad.page.name == "landing.example.com"
    assert "Descripcion comercial del anuncio" in ad.body
    assert ad.media[0].url == "https://landing.example.com/curso"


def test_ads_searcher_builds_required_filters():
    mock_page = MagicMock()
    searcher = AdsSearcher(mock_page, wait_after_search_ms=10)

    searcher.search("curso marketing")

    search_url = mock_page.goto.call_args.args[0]

    assert "country=ALL" in search_url
    assert "ad_type=all" in search_url
    assert "content_languages%5B0%5D=es" in search_url
    assert "sort_data%5Bmode%5D=total_impressions" in search_url
    assert "publisher_platforms%5B0%5D=facebook" in search_url
    assert "publisher_platforms%5B1%5D=instagram" in search_url
    assert "active_status=active" in search_url
    assert "q=curso+marketing" in search_url
    mock_page.wait_for_timeout.assert_called_once_with(10)


def test_ads_searcher_build_search_url_static():
    url = AdsSearcher.build_search_url_static("test")
    assert "q=test" in url
    assert "country=ALL" in url


def test_ads_extractor_discovery_filters_only_external_landings():
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"

    whatsapp_card = _mock_card(hrefs=["https://wa.me/5491111111111"], library_id="111")
    landing_card = _mock_card(
        hrefs=[
            "https://l.facebook.com/l.php?u="
            "https%3A%2F%2Flanding.example.com%2Fcurso"
        ],
        library_id="222",
    )
    mock_page.query_selector_all.return_value = [whatsapp_card, landing_card]

    extractor = AdsExtractor(mock_page)
    ads = extractor.extract_discovery_ads(keyword="curso", limit=3)

    assert len(ads) == 1
    assert ads[0].library_id == "222"
    assert ads[0].domain == "landing.example.com"
    assert ads[0].landing_url == "https://landing.example.com/curso"


def test_ads_extractor_discovery_blocks_metastatus_domain():
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"

    blocked_card = _mock_card(
        hrefs=["https://metastatus.com/ads-transparency"], library_id="999"
    )
    landing_card = _mock_card(
        hrefs=["https://cursoreal.com/inscribete"], library_id="888"
    )
    mock_page.query_selector_all.return_value = [blocked_card, landing_card]

    extractor = AdsExtractor(mock_page)
    ads = extractor.extract_discovery_ads(keyword="curso", limit=3)

    assert len(ads) == 1
    assert ads[0].library_id == "888"
    assert ads[0].domain == "cursoreal.com"


def test_ads_extractor_description_excludes_ui_noise():
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"
    card = _mock_card_with_noise(
        hrefs=["https://ciftt.edu.bo/excel"],
        library_id="555",
        ad_text="Increíble curso de Excel, aprende desde cero hasta avanzado con IA",
    )
    mock_page.query_selector_all.return_value = [card]

    extractor = AdsExtractor(mock_page)
    ads = extractor.extract_discovery_ads(keyword="curso", limit=1)

    assert len(ads) == 1
    desc = ads[0].description
    assert desc is not None
    assert "Increíble curso de Excel" in desc
    assert "Informe de la biblioteca" not in desc
    assert "Buscar por palabra clave" not in desc
    assert "Iniciar sesión" not in desc


def test_ads_extractor_enrichment_reads_social_users():
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"
    card = _mock_card(hrefs=["https://landing.example.com"], library_id="333")
    detail_button = MagicMock()
    card.query_selector.return_value = detail_button

    dialog = MagicMock()
    dialog.inner_text.return_value = (
        "Detalles del anuncio\n"
        "Publicidad\n"
        "Información sobre el anunciante\n"
        "Mock Page Name\n"
        "@mockuser\n"
        "1260 seguidores •\n"
        "Sector tecnologia\n"
    )
    heading = MagicMock()
    heading.inner_text.return_value = "Información sobre el anunciante"
    close_button = MagicMock()

    # New enrich_ads: page.goto -> wait -> _candidate_cards -> _find_detail_button
    # -> button.click -> wait -> _find_detail_dialog -> _click_advertiser_heading
    # -> wait -> _close_details
    mock_page.query_selector_all.side_effect = [
        [card],  # _candidate_cards
        [dialog],  # _find_detail_dialog
    ]
    mock_page.query_selector.return_value = close_button  # _close_details
    dialog.query_selector_all.return_value = [heading]  # _click_advertiser_heading

    discovery = extractor_discovery("333")
    extractor = AdsExtractor(mock_page, action_delay_ms=1)

    results = extractor.enrich_ads([discovery])

    assert results[0].enrichment is not None
    assert results[0].enrichment.facebook_user == "mockuser"
    assert results[0].enrichment.instagram_user is None
    assert results[0].enrichment.facebook_followers == "1260"
    assert results[0].enrichment.instagram_followers is None


def test_browser_ad_result_serialization():
    discovery = BrowserAdDiscovery(
        keyword="curso",
        library_id="123456",
        description="Test description",
        circulation_start="En circulación desde 1 ene 2026",
        landing_url="https://example.com",
        domain="example.com",
        ad_library_url="https://www.facebook.com/ads/library/?id=123456",
        advertiser_name="Test Advertiser",
    )

    result = BrowserAdResult(discovery=discovery)

    assert result.discovery.keyword == "curso"
    assert result.discovery.library_id == "123456"
    assert result.discovery.advertiser_name == "Test Advertiser"
    assert result.enrichment is None


def test_ads_extractor_extracts_advertiser_name():
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"
    card = MagicMock()
    card.inner_text.return_value = (
        "Mi Empresa SRL\n"
        "Identificador de la biblioteca: 777\n"
        "En circulación desde el 25 jun 2026\n"
        "Aprende marketing digital con nosotros."
    )
    card.query_selector_all.return_value = [
        _mock_anchor("https://miempresa.com/cursos")
    ]
    mock_page.query_selector_all.return_value = [card]

    extractor = AdsExtractor(mock_page)
    ads = extractor.extract_discovery_ads(keyword="curso", limit=1)

    assert len(ads) == 1
    assert ads[0].advertiser_name == "Mi Empresa SRL"


def _mock_card(hrefs: list[str], library_id: str) -> MagicMock:
    card = MagicMock()
    card.inner_text.return_value = (
        f"Mi Empresa\n"
        f"Identificador de la biblioteca: {library_id}\n"
        "En circulacion desde 1 ene 2026\n"
        "Descripcion comercial del anuncio en espanol."
        " Este es un texto de ejemplo para el anuncio que debe superar "
        "los 200 caracteres de longitud para pasar el filtro de candidatos. "
        "Meta Ads Library es una plataforma de transparencia publicitaria."
    )
    card.query_selector_all.return_value = [_mock_anchor(href) for href in hrefs]
    return card


def _mock_card_with_noise(hrefs: list[str], library_id: str, ad_text: str) -> MagicMock:
    card = MagicMock()
    card.inner_text.return_value = (
        f"Informe de la biblioteca de anuncios\n"
        f"API de la biblioteca de anuncios\n"
        f"Todos\nTodos los anuncios\n"
        f"Buscar por palabra clave o anunciante\n"
        f"Iniciar sesión\n"
        f"Identificador de la biblioteca: {library_id}\n"
        f"En circulación desde el 29 jun 2026\n"
        f"{ad_text}\n"
        f"Ver detalles del anuncio\n"
        f"Publicidad\n"
        f"Plataformas\n"
        f"Contenido de marca\n"
    )
    card.query_selector_all.return_value = [_mock_anchor(href) for href in hrefs]
    return card


def _mock_anchor(href: str) -> MagicMock:
    anchor = MagicMock()
    anchor.get_attribute.return_value = href
    return anchor


def extractor_discovery(library_id: str) -> BrowserAdDiscovery:
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"
    card = _mock_card(hrefs=["https://landing.example.com"], library_id=library_id)
    mock_page.query_selector_all.return_value = [card]
    return AdsExtractor(mock_page).extract_discovery_ads(keyword="curso", limit=1)[0]


# ── nuevos tests Fase 3.2 ─────────────────────────────────────────────


def test_parse_keyword_with_limit():
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    result = MetaAdsBrowserRunner._parse_keywords(["curso:30", "curso marketing"], 30)
    assert result == [("curso", 30), ("curso marketing", 30)]


def test_parse_keyword_without_limit():
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    result = MetaAdsBrowserRunner._parse_keywords(["curso marketing", "ingles"], 20)
    assert result == [("curso marketing", 20), ("ingles", 20)]


def test_parse_keyword_global_none():
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    result = MetaAdsBrowserRunner._parse_keywords(["curso:50"], 30)
    assert result == [("curso", 50)]


def test_razon_corte_objetivo():
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    assert "objetivo" in MetaAdsBrowserRunner._razon_corte([1] * 30, 0, 5, 30)


def test_razon_corte_vacios():
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    assert "vacios" in MetaAdsBrowserRunner._razon_corte([1] * 5, 3, 5, 30)


def test_razon_corte_scrolls():
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    assert "limite" in MetaAdsBrowserRunner._razon_corte([1] * 5, 1, 50, 30)


def test_load_domains_from_file(tmp_path):
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    f = tmp_path / "test.json"
    f.write_text(
        json.dumps(
            [
                {"discovery": {"domain": "example.com", "library_id": "111"}},
                {"discovery": {"domain": "test.org", "library_id": "222"}},
            ]
        )
    )
    domains, ids = MetaAdsBrowserRunner._load_domains_from_file(str(f))
    assert domains == {"example.com", "test.org"}
    assert ids == {"111", "222"}


def test_load_domains_from_file_missing(tmp_path, caplog):
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    caplog.set_level("WARNING")
    domains, ids = MetaAdsBrowserRunner._load_domains_from_file(
        str(tmp_path / "no_existe.json")
    )
    assert domains == set()
    assert ids == set()
    assert "No se pudo cargar resume" in caplog.text


def test_extracted_at_in_discovery():
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"
    card = _mock_card(hrefs=["https://landing.example.com"], library_id="123456")
    mock_page.query_selector_all.return_value = [card]

    extractor = AdsExtractor(mock_page)
    ads = extractor.extract_discovery_ads(keyword="curso", limit=1)

    assert len(ads) == 1
    assert ads[0].extracted_at is not None
    assert "hs" in ads[0].extracted_at


def test_extra_blocked_domains():
    mock_page = MagicMock()
    mock_page.url = "https://www.facebook.com/ads/library/?q=curso"
    blocked_card = _mock_card(
        hrefs=["https://customblocked.com/ad"], library_id="666661"
    )
    landing_card = _mock_card(hrefs=["https://good.com/landing"], library_id="666662")
    mock_page.query_selector_all.return_value = [blocked_card, landing_card]

    extractor = AdsExtractor(mock_page, extra_blocked_domains={"customblocked.com"})
    ads = extractor.extract_discovery_ads(keyword="curso", limit=3)

    assert len(ads) == 1
    assert ads[0].library_id == "666662"
    assert ads[0].domain == "good.com"


def test_enrich_only_creates_enrichment(tmp_path):
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    disc_json = [
        {
            "discovery": {
                "keyword": "curso",
                "library_id": "777777",
                "description": "Curso test",
                "circulation_start": None,
                "landing_url": "https://test.com",
                "domain": "test.com",
                "ad_library_url": "https://www.facebook.com/ads/library/?id=777777",
                "advertiser_name": "Test",
                "extracted_at": "2026-07-02T00:00:00",
            }
        }
    ]
    input_f = tmp_path / "input.json"
    input_f.write_text(json.dumps(disc_json))
    output_f = tmp_path / "output.json"

    runner = MetaAdsBrowserRunner(
        headless=True,
        per_keyword_limit=10,
        enrich=True,
    )

    with patch.object(runner, "_register_signal_handler"):
        with patch.object(runner, "_save_checkpoint") as mock_save:
            with patch.object(runner, "_process_keyword") as mock_pk:
                mock_pk.return_value = ([], MagicMock())
                runner.run(
                    ["curso"], output_path=str(output_f), mode="overwrite", force=True
                )
                mock_save.assert_called()


def test_checkpoint_saves_file(tmp_path):
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    results = [
        BrowserAdResult(
            discovery=BrowserAdDiscovery(
                keyword="test",
                library_id="c1",
                description="d",
                circulation_start=None,
                landing_url="https://x.com",
                domain="x.com",
                ad_library_url="https://fb.com/ads/?id=c1",
                extracted_at="2026-07-02T00:00:00",
            )
        )
    ]
    out = tmp_path / "checkpoint.json"
    runner = MetaAdsBrowserRunner(per_keyword_limit=10)
    runner._save_checkpoint(results, str(out))
    assert out.exists()
    data = json.loads(out.read_text())
    assert len(data) == 1
    assert data[0]["discovery"]["library_id"] == "c1"


def test_append_mode_loads_existing(tmp_path):
    from src.modules.meta_ads.acquisition.browser_runner import MetaAdsBrowserRunner

    existing = tmp_path / "existing.json"
    existing.write_text(
        json.dumps(
            [
                {
                    "discovery": {
                        "domain": "old.com",
                        "library_id": "888881",
                        "keyword": "prev",
                        "description": None,
                        "circulation_start": None,
                        "landing_url": "",
                        "ad_library_url": "",
                        "advertiser_name": None,
                    }
                }
            ]
        )
    )

    runner = MetaAdsBrowserRunner(per_keyword_limit=10)
    domains, ids = runner._load_existing(str(existing), "append", None)
    assert "old.com" in domains
    assert "888881" in ids
