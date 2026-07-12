import pytest
from src.modules.landing_scraper.extractors import (
    extract_emails,
    extract_phones,
    extract_whatsapp_urls,
    extract_social_urls,
    extract_pricing_urls,
    extract_pricing_text,
    infer_price_range,
    extract_country,
    extract_addresses,
    extract_tech_stack,
    extract_forms,
    detect_spa,
    normalize_phone_e164,
    get_country_from_phone,
    is_profile_url,
)


class TestExtractEmails:
    def test_basic_emails(self):
        html = "Contact us at info@empresa.com or sales@test.org"
        emails = extract_emails(html, "https://example.com")
        assert "info@empresa.com" in emails
        assert "sales@test.org" in emails

    def test_mailto_links(self):
        html = '<a href="mailto:contact@site.com">Contact</a>'
        emails = extract_emails(html, "https://example.com")
        assert "contact@site.com" in emails

    def test_filters_fake_emails(self):
        html = "test@example.com real@domain.com user@yoursite.com"
        emails = extract_emails(html, "https://example.com")
        assert "real@domain.com" in emails
        assert "test@example.com" not in emails
        assert "user@yoursite.com" not in emails

    def test_deduplication(self):
        html = "info@site.com and info@site.com again"
        emails = extract_emails(html, "https://example.com")
        assert emails == ["info@site.com"]


class TestExtractPhones:
    def test_basic_phones(self):
        html = "Call us at +54 11 2233-4455 or +1-555-123-4567"
        phones = extract_phones(html, "https://example.com")
        assert any("541122334455" in p for p in phones)
        assert any("15551234567" in p for p in phones)

    def test_tel_links(self):
        html = '<a href="tel:+5491122334455">Call</a>'
        phones = extract_phones(html, "https://example.com")
        assert any("5491122334455" in p for p in phones)

    def test_normalizes_to_e164(self):
        html = "Phone: 011 4555-6677"
        phones = extract_phones(html, "https://example.com")
        # Should be normalized
        assert any(p.startswith("+54") for p in phones)

    def test_short_numbers_ignored(self):
        html = "Pin: 1234"
        phones = extract_phones(html, "https://example.com")
        assert len(phones) == 0


class TestExtractWhatsAppUrls:
    def test_wa_me_links(self):
        html = "https://wa.me/5491122334455"
        urls = extract_whatsapp_urls(html, "https://example.com")
        assert "https://wa.me/5491122334455" in urls

    def test_whatsapp_com_links(self):
        html = 'href="https://whatsapp.com/send?phone=5491122334455"'
        urls = extract_whatsapp_urls(html, "https://example.com")
        assert "https://whatsapp.com/send?phone=5491122334455" in urls

    def test_api_whatsapp(self):
        html = 'href="https://api.whatsapp.com/send?phone=5491122334455"'
        urls = extract_whatsapp_urls(html, "https://example.com")
        assert "https://api.whatsapp.com/send?phone=5491122334455" in urls

    def test_relative_links(self):
        html = 'href="wa.me/5491122334455"'
        urls = extract_whatsapp_urls(html, "https://example.com")
        assert "https://wa.me/5491122334455" in urls


class TestExtractSocialUrls:
    def test_facebook_profile(self):
        html = 'href="https://facebook.com/miempresa"'
        urls = extract_social_urls(html, "https://example.com")
        assert "https://facebook.com/miempresa" in urls.get("facebook", [])

    def test_instagram_profile(self):
        html = 'href="https://instagram.com/miempresa"'
        urls = extract_social_urls(html, "https://example.com")
        assert "https://instagram.com/miempresa" in urls.get("instagram", [])

    def test_linkedin_profile(self):
        html = 'href="https://linkedin.com/company/miempresa"'
        urls = extract_social_urls(html, "https://example.com")
        assert "https://linkedin.com/company/miempresa" in urls.get("linkedin", [])

    def test_filters_non_profile_facebook(self):
        html = 'href="https://facebook.com/ads/library/?id=123"'
        urls = extract_social_urls(html, "https://example.com")
        assert "facebook" not in urls or len(urls.get("facebook", [])) == 0

    def test_filters_ig_me(self):
        html = 'href="https://ig.me/miempresa"'
        urls = extract_social_urls(html, "https://example.com")
        assert "instagram" not in urls or len(urls.get("instagram", [])) == 0

    def test_relative_urls(self):
        html = 'href="/miempresa"'
        urls = extract_social_urls(html, "https://facebook.com")
        assert "https://facebook.com/miempresa" in urls.get("facebook", [])


class TestExtractPricingUrls:
    def test_pricing_keywords_in_href(self):
        html = '<a href="/precios">Ver planes</a>'
        urls = extract_pricing_urls(html, "https://example.com")
        assert "https://example.com/precios" in urls

    def test_pricing_keywords_in_text(self):
        html = '<a href="/planes">Nuestros planes</a>'
        urls = extract_pricing_urls(html, "https://example.com")
        assert "https://example.com/planes" in urls

    def test_checkout_links(self):
        html = '<a href="https://pay.example.com/checkout">Comprar</a>'
        urls = extract_pricing_urls(html, "https://example.com")
        assert "https://pay.example.com/checkout" in urls

    def test_form_action_checkout(self):
        html = '<form action="/comprar">'
        urls = extract_pricing_urls(html, "https://example.com")
        assert "https://example.com/comprar" in urls


class TestExtractPricingText:
    def test_usd_prices(self):
        html = "Price: $99.99/month"
        matches = extract_pricing_text(html)
        assert "$99.99/month" in matches

    def test_ars_prices(self):
        html = "Desde ARS 10.000"
        matches = extract_pricing_text(html)
        assert "ARS 10.000" in matches

    def test_euro_prices(self):
        html = "€49/mes"
        matches = extract_pricing_text(html)
        assert "€49/mes" in matches

    def test_from_price(self):
        html = "desde $100"
        matches = extract_pricing_text(html)
        assert "desde $100" in matches


class TestInferPriceRange:
    def test_single_price(self):
        matches = ["$99"]
        result = infer_price_range(matches)
        assert result == "~99"

    def test_price_range(self):
        matches = ["$29 - $99"]
        result = infer_price_range(matches)
        assert "29 - 99" in result

    def test_empty(self):
        result = infer_price_range([])
        assert result is None


class TestExtractCountry:
    def test_from_phone(self):
        html = "Some content"
        phones = ["+5491122334455"]
        country, conf = extract_country(html, phones)
        assert country == "AR"
        assert conf in ("high", "medium", "low")

    def test_from_hreflang(self):
        html = '<link rel="alternate" hreflang="es-AR" href="..."/>'
        phones = []
        country, conf = extract_country(html, phones)
        assert country == "AR"

    def test_from_currency(self):
        html = "Price: ARS 1000"
        phones = []
        country, conf = extract_country(html, phones)
        assert country == "AR"

    def test_from_geo_meta(self):
        html = '<meta name="geo.country" content="MX"/>'
        phones = []
        country, conf = extract_country(html, phones)
        assert country == "MX"

    def test_no_signals(self):
        html = "Just text"
        phones = []
        country, conf = extract_country(html, phones)
        assert country is None
        assert conf == "low"


class TestExtractAddresses:
    def test_schema_org_address(self):
        html = """
        <script type="application/ld+json">
        {"@type": "LocalBusiness", "address": {"@type": "PostalAddress", "streetAddress": "Av. Corrientes 1234", "addressLocality": "CABA", "addressRegion": "Buenos Aires", "postalCode": "1043", "addressCountry": "AR"}}
        </script>
        """
        addresses = extract_addresses(html)
        assert any("Av. Corrientes 1234" in a for a in addresses)

    def test_keyword_heuristic(self):
        html = "Dirección: Calle Falsa 123, Ciudad"
        addresses = extract_addresses(html)
        assert any("Calle Falsa 123" in a for a in addresses)


class TestExtractTechStack:
    def test_wordpress(self):
        html = '<link rel="stylesheet" href="/wp-content/themes/theme.css"/>'
        stack = extract_tech_stack(html)
        assert "WordPress" in stack

    def test_shopify(self):
        html = '<script src="https://cdn.shopify.com/s/assets/storefront.js"></script>'
        stack = extract_tech_stack(html)
        assert "Shopify" in stack

    def test_react_nextjs(self):
        html = (
            '<script id="__NEXT_DATA__" type="application/json">{"props":{}}</script>'
        )
        stack = extract_tech_stack(html)
        assert "React" in stack

    def test_google_analytics(self):
        html = 'gtag("config", "GA_MEASUREMENT_ID");'
        stack = extract_tech_stack(html)
        assert "Google Analytics" in stack

    def test_meta_pixel(self):
        html = 'fbq("track", "PageView");'
        stack = extract_tech_stack(html)
        assert "Meta Pixel" in stack


class TestExtractForms:
    def test_contact_form(self):
        html = '<form action="/contact" id="contact-form"></form>'
        forms = extract_forms(html)
        assert "contact" in forms

    def test_newsletter_form(self):
        html = '<form class="newsletter-signup"></form>'
        forms = extract_forms(html)
        assert "contact" in forms

    def test_checkout_form(self):
        html = '<form action="/checkout">'
        forms = extract_forms(html)
        assert "checkout" in forms


class TestDetectSpa:
    def test_react_root(self):
        html = '<div id="root"></div>'
        assert detect_spa(html) is True

    def test_nextjs(self):
        html = '<div id="__next"></div>'
        assert detect_spa(html) is True

    def test_vue(self):
        html = '<div id="app"></div>'
        assert detect_spa(html) is True

    def test_static_html(self):
        html = "<html><body><h1>Hello</h1></body></html>"
        assert detect_spa(html) is False


class TestPhoneNormalization:
    def test_argentinian_mobile(self):
        result = normalize_phone_e164("+5491122334455")
        assert result == "+5491122334455"

    def test_us_number(self):
        result = normalize_phone_e164("+15551234567")
        assert result == "+15551234567"

    def test_invalid_short(self):
        result = normalize_phone_e164("1234")
        assert result is None

    def test_get_country_from_phone(self):
        country = get_country_from_phone("+5491122334455")
        assert country == "AR"

    def test_get_country_from_phone_us(self):
        country = get_country_from_phone("+14155552671")
        assert country == "US"


class TestIsProfileUrl:
    def test_facebook_profile_ok(self):
        assert is_profile_url("https://facebook.com/miempresa", "facebook") is True

    def test_facebook_ads_blocked(self):
        assert (
            is_profile_url("https://facebook.com/ads/library/?id=123", "facebook")
            is False
        )

    def test_facebook_sharer_blocked(self):
        assert (
            is_profile_url("https://facebook.com/sharer.php?u=...", "facebook") is False
        )

    def test_instagram_profile_ok(self):
        assert is_profile_url("https://instagram.com/miempresa", "instagram") is True

    def test_instagram_ig_me_blocked(self):
        assert is_profile_url("https://ig.me/miempresa", "instagram") is False

    def test_instagram_stories_blocked(self):
        assert (
            is_profile_url("https://instagram.com/stories/miempresa", "instagram")
            is False
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
