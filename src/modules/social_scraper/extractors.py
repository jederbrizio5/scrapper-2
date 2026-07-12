import logging
import re
from typing import Optional, Literal
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Selectores para Facebook
FB_SELECTORS = {
    "bio": [
        'div[data-testid="profile_intro_card_bio"]',
        'div[xstyle*="bio"]',
        'div[role="region"] [data-testid="profile_bio"]',
        'div[data-pagelet="ProfileTilesFeedUnit_0"] div[dir="auto"]',
    ],
    "followers": [
        'a[href*="/followers/"] span',
        'a[href*="/followers"] span',
        'span:has-text("followers")',
        'span:has-text("seguidores")',
        'div[data-testid="profile_followers_count"]',
    ],
    "following": [
        'a[href*="/following/"] span',
        'span:has-text("following")',
        'span:has-text("siguiendo")',
    ],
    "verified": [
        'svg[aria-label="Verified"]',
        'svg[aria-label="Verificado"]',
        'i[data-testid="verified-badge"]',
    ],
    "category": [
        'div[data-testid="profile_category"]',
        'span:has-text("Category")',
        'span:has-text("Categoría")',
    ],
    "profile_image": [
        'img[referrerpolicy="origin-when-cross-origin"]',
        'image[data-visualcompletion="media-vc-image"]',
        'svg[aria-label="Profile picture"] image',
    ],
    "external_links": [
        'a[href^="http"]',
        'a[rel="noopener nofollow"]',
    ],
}

# Selectores para Instagram
IG_SELECTORS = {
    "bio": [
        'section[aria-label="Profile"] header div',
        'div[data-testid="user-bio"]',
        "h1 + div",
        'div[role="region"] span',
    ],
    "followers": [
        'a[href*="/followers/"] span',
        'ul li a[href*="/followers/"] span',
        'span:has-text("followers")',
        'span:has-text("seguidores")',
    ],
    "following": [
        'a[href*="/following/"] span',
        'ul li a[href*="/following/"] span',
        'span:has-text("following")',
        'span:has-text("siguiendo")',
    ],
    "posts": [
        'a[href*="/p/"]:not([href*="/p/"]):first-of-type',
        "ul li:first-child span",
    ],
    "verified": [
        'svg[aria-label="Verified"]',
        'svg[aria-label="Verificado"]',
    ],
    "category": [
        'div[data-testid="profile_category"]',
        'span:has-text("Category")',
        'span:has-text("Categoría")',
    ],
    "profile_image": [
        'img[alt*="profile picture"]',
        'img[alt*="foto de perfil"]',
        "header img",
    ],
    "external_links": [
        'a[href^="http"]',
        'a[rel="noopener noreferrer"]',
    ],
    "website_link": [
        'a[href^="http"]:not([href*="instagram.com"]):not([href*="facebook.com"]):first-of-type',
    ],
}


def parse_number(text: str) -> Optional[int]:
    """Parsea números con formato: 1.2K, 1,234, 1.2M, 1,234,567, 2,1 mil, 275,7 mil, 1,4 mill, 1.473 mil."""
    if not text:
        return None
    text_lower = text.strip().lower()

    # Handle "millones" / "mill" / "M" / "m" -> millions
    if "millones" in text_lower or "mill" in text_lower or text_lower.endswith("m"):
        # Extract decimal number before mill/millones/m
        match = re.search(r"([\d.,]+)\s*(?:millones|mill|m\b)", text_lower)
        if match:
            num_str = match.group(1).replace(",", ".")
            try:
                return int(float(num_str) * 1000000)
            except Exception:
                pass

    # Handle "mil" / "k" / "K" -> thousands
    if "mil" in text_lower or "k" in text_lower:
        # Extract number before mil/k
        match = re.search(r"([\d.,]+)\s*(?:mil|k\b)", text_lower)
        if match:
            # In Spanish format: 1.473 = 1473 (dot is thousands separator)
            # 2,1 = 2.1 (comma is decimal separator)
            # We need to handle both
            num_str = match.group(1)
            # If there's a comma, it's decimal separator
            # If there's a dot and no comma, it could be thousands separator
            if "," in num_str and "." in num_str:
                # Both present: assume comma is decimal, dot is thousands
                num_str = num_str.replace(".", "")
            elif "." in num_str and "," not in num_str:
                # Only dots: could be thousands separator (e.g., 1.473)
                # Check if last part has 3 digits -> thousands separator
                parts = num_str.split(".")
                if len(parts[-1]) == 3:
                    num_str = num_str.replace(".", "")
            num_str = num_str.replace(",", ".")
            try:
                return int(float(num_str) * 1000)
            except Exception:
                pass

    # Handle regular numbers with thousands separators
    cleaned = text.strip().replace(",", "").replace(".", "")
    try:
        return int(cleaned)
    except Exception:
        return None


def extract_external_links(
    page, platform: Literal["facebook", "instagram"]
) -> list[str]:
    """Extrae links externos del perfil (bio, website, linktree, etc.)."""
    links = []
    try:
        if platform == "facebook":
            # Links en bio/about section
            link_elements = page.query_selector_all(
                'div[data-testid="profile_intro_card_bio"] a[href^="http"], a[rel="noopener nofollow"][href^="http"]'
            )
        else:
            # Instagram: links en bio + website link
            link_elements = page.query_selector_all(
                'a[href^="http"]:not([href*="instagram.com"]):not([href*="facebook.com"])'
            )

        for el in link_elements:
            href = el.get_attribute("href")
            if href and href.startswith("http"):
                # Filtrar dominios propios
                parsed = urlparse(href)
                domain = parsed.netloc.lower().replace("www.", "")
                if platform == "facebook" and (
                    "facebook.com" in domain or "fb.com" in domain
                ):
                    continue
                if platform == "instagram" and "instagram.com" in domain:
                    continue
                # Filtrar tracking/redirect
                if any(
                    track in domain
                    for track in ["l.facebook.com", "lm.facebook.com", "t.co", "bit.ly"]
                ):
                    continue
                links.append(href)
    except Exception as e:
        logger.debug(f"Error extrayendo links externos {platform}: {e}")
    return list(set(links))


def parse_facebook_profile(page) -> dict:
    """Parsea perfil de Facebook desde el DOM cargado."""
    result = {
        "username": None,
        "bio": None,
        "followers_count": None,
        "following_count": None,
        "is_verified": False,
        "category": None,
        "profile_image_url": None,
        "external_links": [],
    }

    try:
        # Username desde URL
        url = page.url
        match = re.search(r"facebook\.com/([^/?]+)", url)
        if match:
            result["username"] = match.group(1)

        # Bio
        for sel in FB_SELECTORS["bio"]:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    if text and len(text) > 5:
                        result["bio"] = text
                        break
            except Exception:
                continue

        # Followers
        for sel in FB_SELECTORS["followers"]:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    num = parse_number(text)
                    if num:
                        result["followers_count"] = num
                        break
            except Exception:
                continue

        # Following
        for sel in FB_SELECTORS["following"]:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    num = parse_number(text)
                    if num:
                        result["following_count"] = num
                        break
            except Exception:
                continue

        # Verified
        for sel in FB_SELECTORS["verified"]:
            try:
                if page.query_selector(sel):
                    result["is_verified"] = True
                    break
            except Exception:
                continue

        # Category
        for sel in FB_SELECTORS["category"]:
            try:
                el = page.query_selector(sel)
                if el:
                    result["category"] = el.inner_text().strip()
                    break
            except Exception:
                continue

        # Profile image
        for sel in FB_SELECTORS["profile_image"]:
            try:
                el = page.query_selector(sel)
                if el:
                    src = el.get_attribute("src") or el.get_attribute("xlink:href")
                    if src and src.startswith("http"):
                        result["profile_image_url"] = src
                        break
            except Exception:
                continue

        # External links
        result["external_links"] = extract_external_links(page, "facebook")

    except Exception as e:
        logger.warning(f"Error parseando perfil Facebook: {e}")

    return result


def parse_instagram_profile(page) -> dict:
    """Parsea perfil de Instagram desde el DOM cargado."""
    result = {
        "username": None,
        "bio": None,
        "followers_count": None,
        "following_count": None,
        "posts_count": None,
        "is_verified": False,
        "is_business_account": False,
        "category": None,
        "profile_image_url": None,
        "external_links": [],
    }

    try:
        # Username desde URL
        url = page.url
        match = re.search(r"instagram\.com/([^/?]+)", url)
        if match:
            result["username"] = match.group(1)

        # Bio - buscar en header
        for sel in IG_SELECTORS["bio"]:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    if text and len(text) > 5 and not text.startswith("@"):
                        result["bio"] = text
                        break
            except Exception:
                continue

        # Followers
        for sel in IG_SELECTORS["followers"]:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    num = parse_number(text)
                    if num:
                        result["followers_count"] = num
                        break
            except Exception:
                continue

        # Following
        for sel in IG_SELECTORS["following"]:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    num = parse_number(text)
                    if num:
                        result["following_count"] = num
                        break
            except Exception:
                continue

        # Posts
        for sel in IG_SELECTORS["posts"]:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    num = parse_number(text)
                    if num:
                        result["posts_count"] = num
                        break
            except Exception:
                continue

        # Verified
        for sel in IG_SELECTORS["verified"]:
            try:
                if page.query_selector(sel):
                    result["is_verified"] = True
                    break
            except Exception:
                continue

        # Category / Business account detection
        for sel in IG_SELECTORS["category"]:
            try:
                el = page.query_selector(sel)
                if el:
                    result["category"] = el.inner_text().strip()
                    result["is_business_account"] = True
                    break
            except Exception:
                continue

        # Detect business por texto "Business" o "Professional"
        try:
            body_text = page.inner_text("body").lower()
            if "business account" in body_text or "cuenta profesional" in body_text:
                result["is_business_account"] = True
        except Exception:
            pass

        # Profile image
        for sel in IG_SELECTORS["profile_image"]:
            try:
                el = page.query_selector(sel)
                if el:
                    src = el.get_attribute("src")
                    if src and src.startswith("http"):
                        result["profile_image_url"] = src
                        break
            except Exception:
                continue

        # External links (website + bio links)
        result["external_links"] = extract_external_links(page, "instagram")

    except Exception as e:
        logger.warning(f"Error parseando perfil Instagram: {e}")

    return result
