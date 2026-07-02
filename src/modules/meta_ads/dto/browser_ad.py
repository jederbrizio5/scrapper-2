from dataclasses import dataclass


@dataclass
class BrowserAdDiscovery:
    """Datos base extraidos desde el listado de Meta Ads Library."""

    keyword: str
    library_id: str
    description: str | None
    circulation_start: str | None
    landing_url: str
    domain: str
    ad_library_url: str
    advertiser_name: str | None = None
    ad_snapshot_url: str | None = None
    extracted_at: str | None = None


@dataclass
class BrowserAdEnrichment:
    """Datos obtenidos al abrir el detalle de un anuncio."""

    library_id: str
    facebook_user: str | None = None
    instagram_user: str | None = None
    facebook_followers: str | None = None
    instagram_followers: str | None = None
    advertiser_info: str | None = None
    login_required: bool = False
    extracted_at: str | None = None


@dataclass
class BrowserAdResult:
    """Resultado final listo para persistencia posterior."""

    discovery: BrowserAdDiscovery
    enrichment: BrowserAdEnrichment | None = None
