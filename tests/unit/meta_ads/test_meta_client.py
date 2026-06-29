import pytest
import responses
from src.modules.meta_ads.client import (
    MetaClient,
    AuthenticationException,
    RateLimitException,
)
from src.modules.meta_ads.dto import SearchRequest


@responses.activate
def test_search_ads_success():
    client = MetaClient()
    request = SearchRequest(keyword="test")

    mock_response = {
        "data": [
            {
                "id": "123",
                "page_id": "456",
                "page_name": "Test Page",
                "ad_creative_bodies": ["Test body"],
            }
        ],
        "paging": {"cursors": {"after": "cursor123"}},
    }

    responses.add(responses.GET, client.base_url, json=mock_response, status=200)

    response = client.search_ads(request)
    assert len(response.ads) == 1
    assert response.ads[0].id == "123"
    assert response.next_cursor == "cursor123"


@responses.activate
def test_search_ads_authentication_error():
    client = MetaClient()
    request = SearchRequest(keyword="test")

    responses.add(
        responses.GET,
        client.base_url,
        json={"error": {"message": "Invalid token"}},
        status=401,
    )

    with pytest.raises(AuthenticationException):
        client.search_ads(request)


@responses.activate
def test_search_ads_rate_limit_error():
    client = MetaClient()
    request = SearchRequest(keyword="test")

    responses.add(
        responses.GET,
        client.base_url,
        json={"error": {"message": "Rate limit"}},
        status=429,
    )

    with pytest.raises(RateLimitException):
        client.search_ads(request)
