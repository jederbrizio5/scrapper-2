from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LandingExtractionResult:
    """Resultado de extracción de una landing page."""

    status: str = "pending"  # pending, completed, partial, failed, skipped
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)  # Formato E.164
    whatsapp_urls: list[str] = field(default_factory=list)
    facebook_urls: list[str] = field(default_factory=list)
    instagram_urls: list[str] = field(default_factory=list)
    linkedin_urls: list[str] = field(default_factory=list)
    twitter_urls: list[str] = field(default_factory=list)
    pricing_urls: list[str] = field(default_factory=list)
    country_code: Optional[str] = None  # ISO 3166-1 alpha-2 (AR, US, MX, etc.)
    country_confidence: str = "low"  # high, medium, low
    addresses: list[str] = field(default_factory=list)
    social_links_in_bio: dict[str, list[str]] = field(
        default_factory=dict
    )  # platform -> urls
    tech_stack: list[str] = field(default_factory=list)
    forms_detected: list[str] = field(
        default_factory=list
    )  # contact, newsletter, checkout
    scraped_at: Optional[str] = None
    method: str = "httpx"  # httpx, playwright
    error: Optional[str] = None
    raw_html: Optional[str] = None  # Solo si se configura save_html

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "emails": self.emails,
            "phones": self.phones,
            "whatsapp_urls": self.whatsapp_urls,
            "facebook_urls": self.facebook_urls,
            "instagram_urls": self.instagram_urls,
            "linkedin_urls": self.linkedin_urls,
            "twitter_urls": self.twitter_urls,
            "pricing_urls": self.pricing_urls,
            "country_code": self.country_code,
            "country_confidence": self.country_confidence,
            "addresses": self.addresses,
            "social_links_in_bio": self.social_links_in_bio,
            "tech_stack": self.tech_stack,
            "forms_detected": self.forms_detected,
            "scraped_at": self.scraped_at,
            "method": self.method,
            "error": self.error,
            "raw_html": self.raw_html,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LandingExtractionResult":
        return cls(**data)
