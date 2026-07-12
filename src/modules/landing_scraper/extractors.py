import re
from urllib.parse import urlparse, urljoin
from typing import Optional

try:
    import phonenumbers

    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False


EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

PHONE_REGEX = re.compile(
    r"""
    (?:
        (?:\+?\d{1,3}[-.\s]?)?     # Country code opcional
        (?:\(?\d{2,4}\)?[-.\s]?)?  # Area code opcional
        \d{3,4}[-.\s]?\d{3,4}      # Número principal
    )
    """,
    re.VERBOSE,
)

WHATSAPP_PATTERNS = [
    r"wa\.me/\d+",
    r"whatsapp\.com/(?:send|message)/",
    r"api\.whatsapp\.com/send",
    r"web\.whatsapp\.com/send",
]

SOCIAL_DOMAINS = {
    "facebook": ["facebook.com", "fb.com", "fb.me"],
    "instagram": ["instagram.com", "ig.me"],
    "linkedin": ["linkedin.com", "lnkd.in"],
    "twitter": ["twitter.com", "x.com", "t.co"],
    "youtube": ["youtube.com", "youtu.be"],
    "tiktok": ["tiktok.com"],
}

PRICING_KEYWORDS = [
    "precio",
    "precios",
    "planes",
    "plan",
    "pricing",
    "price",
    "comprar",
    "compra",
    "buy",
    "checkout",
    "pagar",
    "pago",
    "suscripcion",
    "suscribir",
    "subscribe",
    "subscription",
    "contratar",
    "contratacion",
    "signup",
    "sign-up",
    "registro",
    "tarifa",
    "tarifas",
    "costo",
    "costos",
    "fee",
    "fees",
    "cuota",
    "cuotas",
    "mensualidad",
    "anualidad",
]

ADDRESS_KEYWORDS = [
    "direccion",
    "dirección",
    "address",
    "calle",
    "avenida",
    "av.",
    "ciudad",
    "city",
    "provincia",
    "province",
    "estado",
    "state",
    "codigo postal",
    "código postal",
    "cp ",
    "postal code",
    "zip code",
    "piso",
    "depto",
    "oficina",
    "local",
    "suite",
]

TECH_STACK_PATTERNS = {
    "WordPress": [r"wp-content", r"wp-includes", r"wordpress", r"/wp-json/"],
    "Shopify": [r"shopify", r"myshopify\.com", r"Shopify\.theme"],
    "React": [r"react", r"__NEXT_DATA__", r"next\.js", r"_next/static"],
    "Vue.js": [r"vue\.js", r"vuejs", r"__VUE__"],
    "Angular": [r"ng-version", r"angular"],
    "Google Analytics": [r"google-analytics\.com/analytics\.js", r"gtag\(", r"ga\("],
    "Google Tag Manager": [r"googletagmanager\.com/gtm\.js", r"GTM-"],
    "Meta Pixel": [r"connect\.facebook\.net/en_US/fbevents\.js", r"fbq\("],
    "Hotjar": [r"static\.hotjar\.com", r"hj\("],
    "Intercom": [r"intercom\.io", r"Intercom\("],
    "HubSpot": [r"hubspot\.com", r"hs-forms\.com"],
    "Mailchimp": [r"mailchimp", r"mc4wp"],
    "Wix": [r"wix\.com", r"wixstatic\.com"],
    "Squarespace": [r"squarespace\.com", r"static\.squarespace\.com"],
    "Webflow": [r"webflow\.js", r"webflow\.com"],
    "Framer": [r"framer\.com", r"framer\.js"],
    "Carrd": [r"carrd\.co"],
    "Notion": [r"notion\.site", r"notion\.so"],
    "Ghost": [r"ghost\.org", r"/ghost/"],
    "WooCommerce": [r"woocommerce", r"wc-ajax"],
    "Magento": [r"magento", r"mage/"],
    "PrestaShop": [r"prestashop"],
    "Cloudflare": [r"cloudflare", r"__cfduid"],
    "Vercel": [r"vercel\.app", r"vercel\.com"],
    "Netlify": [r"netlify\.app", r"netlify\.com"],
}


def extract_emails(html: str, base_url: str) -> list[str]:
    """Extrae emails únicos del HTML."""
    emails = set()
    for match in EMAIL_REGEX.finditer(html):
        email = match.group(0).lower()
        # Filtrar emails falsos comunes (match exacto de dominio)
        email_domain = email.split("@")[-1] if "@" in email else ""
        if not any(
            email_domain == fake or email_domain.endswith("." + fake)
            for fake in ["example.com", "test.com", "yoursite.com"]
        ):
            emails.add(email)
    # También buscar en mailto: links
    mailto_matches = re.findall(r'mailto:([^"\'>\s]+)', html, re.IGNORECASE)
    for m in mailto_matches:
        email = m.split("?")[0].lower()
        if "@" in email:
            email_domain = email.split("@")[-1]
            if not any(
                email_domain == fake or email_domain.endswith("." + fake)
                for fake in ["example.com", "test.com", "yoursite.com"]
            ):
                emails.add(email)
    return sorted(emails)


def extract_phones(html: str, base_url: str) -> list[str]:
    """Extrae y normaliza teléfonos a formato E.164."""
    phones = set()
    for match in PHONE_REGEX.finditer(html):
        raw = match.group(0).strip()
        # Limpiar
        cleaned = re.sub(r"[^\d+]", "", raw)
        if len(cleaned) >= 8:  # Mínimo razonable
            phones.add(cleaned)
    # También tel: links
    tel_matches = re.findall(r'tel:([^"\'>\s]+)', html, re.IGNORECASE)
    for m in tel_matches:
        cleaned = re.sub(r"[^\d+]", "", m)
        if len(cleaned) >= 8:
            phones.add(cleaned)

    # Normalizar a E.164 si phonenumbers disponible
    normalized = []
    for phone in phones:
        e164 = normalize_phone_e164(phone)
        if e164:
            normalized.append(e164)
        else:
            normalized.append(phone)  # fallback raw
    return sorted(set(normalized))


def normalize_phone_e164(phone: str) -> Optional[str]:
    """Normaliza teléfono a formato E.164 (+5491122334455)."""
    if not HAS_PHONENUMBERS:
        # Fallback simple: si empieza con + y tiene 10-15 dígitos, asumir E.164
        if phone.startswith("+") and 10 <= len(phone) <= 16:
            return phone
        return None

    # Intentar parsear con diferentes países probables
    for region in [
        "AR",
        "US",
        "MX",
        "CL",
        "CO",
        "PE",
        "ES",
        "BR",
        "UY",
        "PY",
        "BO",
        "EC",
        "VE",
        "CR",
        "PA",
        "DO",
        "GT",
        "SV",
        "HN",
        "NI",
    ]:
        try:
            parsed = phonenumbers.parse(phone, region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
        except Exception:
            continue
    # Fallback: si ya parece E.164
    if phone.startswith("+") and 10 <= len(phone) <= 16:
        return phone
    return None


def get_country_from_phone(phone: str) -> Optional[str]:
    """Extrae código de país ISO del teléfono E.164."""
    if not HAS_PHONENUMBERS:
        # Mapping básico por prefijo
        prefix_map = {
            "+54": "AR",
            "+1": "US",
            "+52": "MX",
            "+56": "CL",
            "+57": "CO",
            "+51": "PE",
            "+34": "ES",
            "+55": "BR",
            "+598": "UY",
            "+595": "PY",
            "+591": "BO",
            "+593": "EC",
            "+58": "VE",
            "+506": "CR",
            "+507": "PA",
            "+599": "CW",
            "+53": "CU",
            "+502": "GT",
            "+503": "SV",
            "+504": "HN",
            "+505": "NI",
        }
        for prefix, code in prefix_map.items():
            if phone.startswith(prefix):
                return code
        return None

    try:
        parsed = phonenumbers.parse(phone, None)
        if phonenumbers.is_valid_number(parsed):
            region = phonenumbers.region_code_for_number(parsed)
            return region
    except Exception:
        pass
    return None


def extract_whatsapp_urls(html: str, base_url: str) -> list[str]:
    """Extrae URLs de WhatsApp."""
    urls = set()
    for pattern in WHATSAPP_PATTERNS:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for m in matches:
            if m.startswith("http"):
                urls.add(m)
            else:
                urls.add(f"https://{m}")
    # También buscar en anchors
    anchor_matches = re.findall(
        r'href=["\']([^"\']*wa\.me[^"\']*)["\']', html, re.IGNORECASE
    )
    for m in anchor_matches:
        urls.add(m if m.startswith("http") else f"https://{m}")
    anchor_matches2 = re.findall(
        r'href=["\']([^"\']*whatsapp\.com[^"\']*)["\']', html, re.IGNORECASE
    )
    for m in anchor_matches2:
        urls.add(m if m.startswith("http") else f"https://{m}")
    return sorted(urls)


def extract_social_urls(html: str, base_url: str) -> dict[str, list[str]]:
    """Extrae URLs de redes sociales categorizadas."""
    result = {platform: [] for platform in SOCIAL_DOMAINS}
    result["other"] = []

    # Buscar todos los hrefs
    href_matches = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)

    for href in href_matches:
        href_lower = href.lower()
        # Normalizar URL relativa
        if href.startswith("/"):
            href = urljoin(base_url, href)
        elif not href.startswith("http"):
            continue

        parsed = urlparse(href)
        domain = parsed.netloc.lower().replace("www.", "")

        categorized = False
        for platform, domains in SOCIAL_DOMAINS.items():
            for d in domains:
                if d in domain:
                    # Filtrar URLs que NO son perfiles (ads library, ig.me, etc.)
                    if not is_profile_url(href, platform):
                        continue
                    result[platform].append(href)
                    categorized = True
                    break
            if categorized:
                break
        if not categorized and ("http" in href_lower):
            result["other"].append(href)

    # Deduplicar
    for platform in result:
        result[platform] = sorted(set(result[platform]))

    # Quitar "other" si vacío
    if not result["other"]:
        del result["other"]
    return result


def is_profile_url(url: str, platform: str) -> bool:
    """Determina si una URL de red social es un perfil/página (no ads, no shortlinks)."""
    url_lower = url.lower()
    # Filtrar conocidos no-perfil
    blocked_patterns = [
        "ads/library",
        "ads/manager",
        "business.facebook.com",
        "ig.me",
        "wa.me",
        "m.me",
        "l.facebook.com",
        "lm.facebook.com",
        "facebook.com/sharer",
        "facebook.com/dialog",
        "facebook.com/plugins",
        "twitter.com/intent",
        "twitter.com/share",
        "t.co/",
        "linkedin.com/feed",
        "linkedin.com/in/feed",
        "instagram.com/stories",
        "instagram.com/reel",
        "instagram.com/p/",
        "youtube.com/watch",
        "youtube.com/shorts",
    ]
    for blocked in blocked_patterns:
        if blocked in url_lower:
            return False
    return True


def extract_pricing_urls(html: str, base_url: str) -> list[str]:
    """Extrae URLs que parecen páginas de precios/compra."""
    urls = set()
    # Buscar en anchors con texto o href sugestivo
    anchor_pattern = re.compile(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in anchor_pattern.finditer(html):
        href, text = match.groups()
        href_lower = href.lower()
        text_lower = text.lower().strip()

        # Normalizar href
        if href.startswith("/"):
            href = urljoin(base_url, href)
        elif not href.startswith("http"):
            continue

        # Score por keywords en href o texto
        score = 0
        for kw in PRICING_KEYWORDS:
            if kw in href_lower or kw in text_lower:
                score += 1
        if score > 0:
            urls.add(href)

    # También buscar botones/formularios de checkout
    checkout_patterns = [
        r'href=["\']([^"\']*(?:checkout|comprar|pagar|pago|buy|pay)[^"\']*)["\']',
        r'action=["\']([^"\']*(?:checkout|comprar|pagar|pago|buy|pay)[^"\']*)["\']',
    ]
    for pattern in checkout_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for m in matches:
            if m.startswith("/"):
                m = urljoin(base_url, m)
            elif not m.startswith("http"):
                continue
            urls.add(m)

    return sorted(urls)


def extract_addresses(html: str) -> list[str]:
    """Extrae direcciones postales del HTML (schema.org + heurísticas)."""
    addresses = set()

    # 1. Schema.org PostalAddress (JSON-LD)
    json_ld_matches = re.findall(
        r'<script\s+type=["\']application/ld\+json["\'][^>]*>([^<]+)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    for json_text in json_ld_matches:
        try:
            import json

            data = json.loads(json_text.strip())
            # Puede ser lista o dict
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    # Buscar PostalAddress
                    if item.get("@type") == "PostalAddress":
                        addr = format_schema_address(item)
                        if addr:
                            addresses.add(addr)
                    # Buscar en Organization/LocalBusiness
                    elif item.get("@type") in (
                        "Organization",
                        "LocalBusiness",
                        "Store",
                    ):
                        address = item.get("address")
                        if address:
                            if isinstance(address, dict):
                                addr = format_schema_address(address)
                                if addr:
                                    addresses.add(addr)
                            elif isinstance(address, list):
                                for a in address:
                                    addr = format_schema_address(a)
                                    if addr:
                                        addresses.add(addr)
        except Exception:
            continue

    # 2. Microdata (itemprop)
    # address, streetAddress, addressLocality, addressRegion, postalCode, addressCountry
    microdata_pattern = re.compile(
        r'itemprop=["\']address["\'][^>]*>([^<]+)', re.IGNORECASE
    )
    for match in microdata_pattern.finditer(html):
        addr = match.group(1).strip()
        if len(addr) > 10:
            addresses.add(addr)

    # 3. Heurísticas por keywords en texto visible
    # Buscar líneas que contengan keywords de dirección
    lines = [line.strip() for line in html.split("\n") if line.strip()]
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in ADDRESS_KEYWORDS):
            # Filtrar líneas muy largas (probablemente no son direcciones)
            if 15 <= len(line) <= 200:
                # Debe tener números (altura) y letras
                if re.search(r"\d", line) and re.search(r"[a-zA-Z]", line):
                    addresses.add(line)

    return sorted(addresses)


def format_schema_address(addr: dict) -> Optional[str]:
    """Formatea dirección de schema.org PostalAddress."""
    parts = []
    for field in [
        "streetAddress",
        "addressLocality",
        "addressRegion",
        "postalCode",
        "addressCountry",
    ]:
        val = addr.get(field)
        if val:
            parts.append(str(val))
    if parts:
        return ", ".join(parts)
    return None


def extract_country(html: str, phones: list[str]) -> tuple[Optional[str], str]:
    """Determina país por múltiples señales: teléfono, TLD, hreflang, currency, meta tags."""
    signals = {}

    # 1. Teléfonos (peso alto)
    for phone in phones:
        country = get_country_from_phone(phone)
        if country:
            signals[country] = signals.get(country, 0) + 3

    # 2. hreflang / lang attribute
    hreflang_matches = re.findall(
        r'hreflang=["\']([a-z]{2})(?:-([A-Z]{2}))?["\']', html, re.IGNORECASE
    )
    for hl in hreflang_matches:
        lang = hl[0] if isinstance(hl, tuple) else hl
        country = hl[1] if isinstance(hl, tuple) and hl[1] else None
        if country:
            signals[country.upper()] = signals.get(country.upper(), 0) + 3
        else:
            signals[lang.upper()] = signals.get(lang.upper(), 0) + 1

    html_lang = re.search(r'<html[^>]*lang=["\']([a-z]{2})', html, re.IGNORECASE)
    if html_lang:
        signals[html_lang.group(1).upper()] = (
            signals.get(html_lang.group(1).upper(), 0) + 1
        )

    # 3. Currency symbols / meta
    currency_map = {
        "ARS": "AR",
        "$": "AR",
        "USD": "US",
        "MXN": "MX",
        "CLP": "CL",
        "COP": "CO",
        "PEN": "PE",
        "UYU": "UY",
        "PYG": "PY",
        "BOB": "BO",
        "EUR": "ES",
        "BRL": "BR",
        "CRC": "CR",
        "PAB": "PA",
        "DOP": "DO",
        "GTQ": "GT",
        "SVC": "SV",
        "HNL": "HN",
        "NIO": "NI",
    }
    for curr, country in currency_map.items():
        if curr in html:
            signals[country] = signals.get(country, 0) + 1

    # 4. Geo meta tags
    geo_country = re.search(
        r'<meta\s+(?:name|property)=["\'](?:geo\.country|og:country)["\']\s+content=["\']([A-Z]{2})["\']',
        html,
        re.IGNORECASE,
    )
    if geo_country:
        signals[geo_country.group(1).upper()] = (
            signals.get(geo_country.group(1).upper(), 0) + 2
        )

    # 5. TLD del dominio base (si disponible en base_url, pero no lo tenemos aquí)
    # Se puede pasar por parámetro si se necesita

    if not signals:
        return None, "low"

    # Ordenar por score
    sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
    top_country, top_score = sorted_signals[0]

    # Confidence
    if top_score >= 5:
        confidence = "high"
    elif top_score >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    return top_country, confidence


def extract_tech_stack(html: str) -> list[str]:
    """Detecta stack tecnológico por patrones en HTML."""
    detected = []
    for tech, patterns in TECH_STACK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, html, re.IGNORECASE):
                detected.append(tech)
                break
    return detected


def extract_pricing_text(html: str) -> list[str]:
    """Extrae texto relacionado con precios del HTML."""
    matches = []
    # Buscar patrones de precios en texto visible
    # Order matters: more specific patterns first
    price_patterns = [
        # Currency symbol + number + optional period (most specific)
        r"[\$\€\£]\s?\d[\d.,]*(?:\s*(?:/mes|/month|mensual|anual|per\s+month|per\s+year))?",
        # Currency code + number
        r"(?:ARS|USD|EUR|MXN|CLP|COP)\s*\d[\d.,]*",
        # desde/from + optional currency + number
        r"(?:desde|from)\s*[\$\€\£]?\s*\d[\d.,]*",
        # Number + currency code
        r"\d[\d.,]*\s*(?:ARS|USD|EUR|MXN|CLP|COP)",
        # Number + period suffix (only if not already captured by currency symbol)
        r"(?<![\$\€\£])\d[\d.,]*\s*(?:/mes|/month|mensual|anual)",
    ]
    for pattern in price_patterns:
        matches.extend(re.findall(pattern, html, re.IGNORECASE))
    return list(set(matches))


def infer_price_range(price_matches: list[str]) -> Optional[str]:
    """Infiere rango de precios desde matches de texto."""
    if not price_matches:
        return None

    # Buscar patrones como "desde $10.000", "$29 - $99", "ARS 10000/50000"
    prices = []
    for match in price_matches:
        # Extraer números con posibles separadores de miles y decimales
        nums = re.findall(r"[\d.,]+", match.replace(".", "").replace(",", "."))
        for n in nums:
            try:
                prices.append(float(n))
            except ValueError:
                pass

    if prices:
        min_p = min(prices)
        max_p = max(prices)
        if min_p == max_p:
            return f"~{min_p:,.0f}"
        return f"{min_p:,.0f} - {max_p:,.0f}"
    return None


def extract_forms(html: str) -> list[str]:
    """Detecta tipos de formularios."""
    forms = []
    # Buscar forms con action o id sugestivo
    form_matches = re.findall(
        r'<form[^>]*(?:action=["\']([^"\']*)["\']|id=["\']([^"\']*)["\']|class=["\']([^"\']*)["\'])[^>]*>',
        html,
        re.IGNORECASE,
    )
    for match in form_matches:
        action, fid, fclass = match
        text = f"{action} {fid} {fclass}".lower()
        if any(
            kw in text
            for kw in ["contact", "contacto", "newsletter", "suscripcion", "subscribe"]
        ):
            forms.append("contact")
        elif any(
            kw in text for kw in ["checkout", "comprar", "pagar", "pago", "buy", "pay"]
        ):
            forms.append("checkout")
        elif any(
            kw in text for kw in ["login", "register", "registro", "signup", "signin"]
        ):
            forms.append("auth")
    # Deduplicar
    return list(set(forms))


def detect_spa(html: str) -> bool:
    """Detecta si la página es una SPA (requiere JS/Playwright)."""
    spa_indicators = [
        r'<div\s+id=["\']root["\']',
        r'<div\s+id=["\']__next["\']',
        r'<div\s+id=["\']app["\']',
        r"data-reactroot",
        r"__NEXT_DATA__",
        r"__NUXT__",
        r"__VUE__",
        r"ng-version",
        r"ng-app",
        r"gatsby-",
        r"vercel\.analytics",
        r"next\.js",
        r"webpack",
    ]
    for pattern in spa_indicators:
        if re.search(pattern, html, re.IGNORECASE):
            return True
    # Meta tags de frameworks
    meta_frameworks = re.findall(
        r'<meta[^>]*(?:generator|framework)=["\']([^"\']+)["\']', html, re.IGNORECASE
    )
    for m in meta_frameworks:
        if any(
            fw in m.lower()
            for fw in ["next", "nuxt", "gatsby", "react", "vue", "angular", "svelte"]
        ):
            return True
    return False
