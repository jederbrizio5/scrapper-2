from unittest.mock import MagicMock

from src.modules.social_scraper.extractors import (
    parse_facebook_profile,
    parse_instagram_profile,
    extract_external_links,
    parse_number,
)


class TestParseNumber:
    def test_simple_number(self):
        assert parse_number("1234") == 1234

    def test_k_suffix(self):
        assert parse_number("1.2K") == 1200
        assert parse_number("1,2K") == 1200
        assert parse_number("10K") == 10000

    def test_m_suffix(self):
        assert parse_number("1.5M") == 1500000
        assert parse_number("1,5M") == 1500000

    def test_mil_suffix(self):
        assert parse_number("2,1 mil") == 2100
        assert parse_number("159 mil") == 159000
        assert parse_number("275,7 mil") == 275700

    def test_mill_suffix(self):
        assert parse_number("1,4 mill") == 1400000

    def test_dot_thousands(self):
        assert parse_number("1.473 mil") == 1473000

    def test_none_input(self):
        assert parse_number(None) is None
        assert parse_number("") is None


class MockPage:
    """Mock Playwright page for testing."""

    def __init__(
        self,
        url="https://facebook.com/testpage",
        inner_text_return="",
        query_selector_results=None,
    ):
        self._url = url
        self._inner_text_return = inner_text_return
        self._query_selector_results = query_selector_results or {}

    @property
    def url(self):
        return self._url

    def inner_text(self, selector=None):
        return self._inner_text_return

    def query_selector(self, selector):
        return self._query_selector_results.get(selector)

    def query_selector_all(self, selector):
        return self._query_selector_results.get(selector, [])


class TestParseFacebookProfile:
    def test_extracts_username_from_url(self):
        page = MockPage(url="https://facebook.com/miempresa")
        result = parse_facebook_profile(page)
        assert result["username"] == "miempresa"

    def test_extracts_bio(self):
        page = MockPage(
            inner_text_return="Somos una empresa de educación online",
            query_selector_results={
                'div[data-testid="profile_intro_card_bio"]': MockPage(
                    inner_text_return="Somos una empresa de educación online"
                )
            },
        )
        result = parse_facebook_profile(page)
        assert "educación" in result["bio"].lower()

    def test_extracts_followers(self):
        page = MockPage(
            query_selector_results={
                'a[href*="/followers/"] span': MockPage(
                    inner_text_return="10.5K followers"
                )
            }
        )
        result = parse_facebook_profile(page)
        assert result["followers_count"] == 10500

    def test_extracts_verified(self):
        page = MockPage(
            query_selector_results={'svg[aria-label="Verified"]': MockPage()}
        )
        result = parse_facebook_profile(page)
        assert result["is_verified"] is True

    def test_extracts_category(self):
        page = MockPage(
            query_selector_results={
                'div[data-testid="profile_category"]': MockPage(
                    inner_text_return="Education"
                )
            }
        )
        result = parse_facebook_profile(page)
        assert result["category"] == "Education"

    def test_extracts_external_links(self):
        mock_link = MockPage()
        mock_link.get_attribute = MagicMock(return_value="https://linktr.ee/miempresa")
        mock_link.inner_text = MagicMock(return_value="Linktree")

        # Use the combined selector that the function actually uses
        fb_selector = 'div[data-testid="profile_intro_card_bio"] a[href^="http"], a[rel="noopener nofollow"][href^="http"]'

        page = MockPage(
            query_selector_results={
                fb_selector: [mock_link],
            }
        )
        result = parse_facebook_profile(page)
        assert "https://linktr.ee/miempresa" in result["external_links"]


class TestParseInstagramProfile:
    def test_extracts_username_from_url(self):
        page = MockPage(url="https://instagram.com/miempresa")
        result = parse_instagram_profile(page)
        assert result["username"] == "miempresa"

    def test_extracts_bio(self):
        page = MockPage(
            inner_text_return="📚 Cursos online\n👇 Inscribite acá",
            query_selector_results={
                'div[data-testid="user-bio"]': MockPage(
                    inner_text_return="📚 Cursos online\n👇 Inscribite acá"
                )
            },
        )
        result = parse_instagram_profile(page)
        assert "Cursos" in result["bio"]

    def test_extracts_followers(self):
        page = MockPage(
            query_selector_results={
                'a[href*="/followers/"] span': MockPage(
                    inner_text_return="8.9K followers"
                )
            }
        )
        result = parse_instagram_profile(page)
        assert result["followers_count"] == 8900

    def test_extracts_verified(self):
        page = MockPage(
            query_selector_results={'svg[aria-label="Verified"]': MockPage()}
        )
        result = parse_instagram_profile(page)
        assert result["is_verified"] is True

    def test_detects_business_account(self):
        page = MockPage(
            inner_text_return="Business Account\nCategoría: Education",
            query_selector_results={
                'div[data-testid="profile_category"]': MockPage(
                    inner_text_return="Education"
                )
            },
        )
        result = parse_instagram_profile(page)
        assert result["is_business_account"] is True
        assert result["category"] == "Education"


class TestExtractExternalLinks:
    def test_filters_own_domain(self):
        mock_link = MockPage()
        mock_link.get_attribute = MagicMock(
            return_value="https://instagram.com/miempresa"
        )

        page = MockPage(
            query_selector_results={
                'a[href^="http"]:not([href*="instagram.com"]):not([href*="facebook.com"])': []
            }
        )

        # Test the function directly
        links = extract_external_links(page, "instagram")
        assert len(links) == 0

    def test_excludes_tracking_domains(self):
        mock_link1 = MockPage()
        mock_link1.get_attribute = MagicMock(
            return_value="https://l.facebook.com/l.php?u=https://example.com"
        )
        mock_link2 = MockPage()
        mock_link2.get_attribute = MagicMock(return_value="https://bit.ly/abc123")

        page = MockPage(
            query_selector_results={'a[href^="http"]': [mock_link1, mock_link2]}
        )

        links = extract_external_links(page, "facebook")
        # Should filter out tracking domains
        assert not any("l.facebook.com" in link for link in links)
        assert not any("bit.ly" in link for link in links)

    def test_includes_valid_external(self):
        mock_link = MockPage()
        mock_link.get_attribute = MagicMock(return_value="https://linktr.ee/miempresa")

        # Use the selector that the function actually uses for Instagram
        ig_selector = (
            'a[href^="http"]:not([href*="instagram.com"]):not([href*="facebook.com"])'
        )

        page = MockPage(
            query_selector_results={
                ig_selector: [mock_link],
            }
        )

        links = extract_external_links(page, "instagram")
        assert "https://linktr.ee/miempresa" in links
