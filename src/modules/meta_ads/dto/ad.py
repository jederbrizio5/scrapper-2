from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from src.modules.meta_ads.dto.page import Page
from src.modules.meta_ads.dto.advertiser import Advertiser
from src.modules.meta_ads.dto.media import Media


@dataclass
class Ad:
    id: str
    creation_time: Optional[datetime] = None
    status: str = "active"
    body: Optional[str] = None
    page: Optional[Page] = None
    advertiser: Optional[Advertiser] = None
    media: List[Media] = field(default_factory=list)
