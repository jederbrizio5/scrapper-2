import pytest
from src.modules.meta_ads.parser.parser import MetaParser
from src.modules.meta_ads.client.exceptions import ParsingException


def test_parse_search_response_valid():
    raw_data = {
        "data": [
            {
                "id": "111",
                "page_id": "222",
                "page_name": "Test Page",
                "ad_creative_bodies": ["Buy our product"],
                "snapshot_media_url": "http://example.com/img.jpg",
            }
        ],
        "paging": {"cursors": {"after": "abc"}},
    }

    response = MetaParser.parse_search_response(raw_data)
    assert len(response.ads) == 1

    ad = response.ads[0]
    assert ad.id == "111"
    assert ad.body == "Buy our product"
    assert ad.page.id == "222"
    assert ad.page.name == "Test Page"

    assert len(ad.media) == 1
    assert ad.media[0].url == "http://example.com/img.jpg"
    assert ad.media[0].type == "image"

    assert response.next_cursor == "abc"


def test_parse_search_response_invalid():
    # Simulamos un fallo en el parseo, por ejemplo, data no es una lista
    raw_data = {"data": "esto debería ser una lista pero es un string"}

    with pytest.raises(ParsingException):
        MetaParser.parse_search_response(raw_data)
