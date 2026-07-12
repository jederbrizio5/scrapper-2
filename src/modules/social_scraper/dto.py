from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal


@dataclass
class SocialProfileResult:
    """Resultado de scraping de un perfil social (Facebook/Instagram)."""

    platform: Literal["facebook", "instagram"]
    profile_url: str
    username: Optional[str] = None
    status: str = (
        "pending"  # pending, completed, failed, login_required, not_found, blocked
    )
    error: Optional[str] = None
    scraped_at: Optional[str] = None

    # Profile info
    bio: Optional[str] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    posts_count: Optional[int] = None

    # Business info
    is_verified: bool = False
    is_business_account: bool = False
    category: Optional[str] = None  # "Education", "Software Company", etc.

    # Links en bio
    external_links: list[str] = field(
        default_factory=list
    )  # linktree, web, wa.me, etc.

    # Media
    profile_image_url: Optional[str] = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S hs")

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "profile_url": self.profile_url,
            "username": self.username,
            "status": self.status,
            "error": self.error,
            "scraped_at": self.scraped_at,
            "bio": self.bio,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "posts_count": self.posts_count,
            "is_verified": self.is_verified,
            "is_business_account": self.is_business_account,
            "category": self.category,
            "external_links": self.external_links,
            "profile_image_url": self.profile_image_url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SocialProfileResult":
        return cls(**data)


@dataclass
class SocialEnrichmentResult:
    """Resultado consolidado de enriquecimiento social para un dominio."""

    domain: str
    facebook: Optional[SocialProfileResult] = None
    instagram: Optional[SocialProfileResult] = None
    status: str = "pending"  # pending, partial, completed, failed
    completed_at: Optional[str] = None

    def __post_init__(self):
        if self.completed_at is None and self.status in ("completed", "partial"):
            self.completed_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S hs")

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "facebook": self.facebook.to_dict() if self.facebook else None,
            "instagram": self.instagram.to_dict() if self.instagram else None,
            "status": self.status,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SocialEnrichmentResult":
        fb = data.get("facebook")
        ig = data.get("instagram")
        return cls(
            domain=data["domain"],
            facebook=SocialProfileResult.from_dict(fb) if fb else None,
            instagram=SocialProfileResult.from_dict(ig) if ig else None,
            status=data.get("status", "pending"),
            completed_at=data.get("completed_at"),
        )
