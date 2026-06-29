from dataclasses import dataclass
from typing import Optional


@dataclass
class Media:
    type: str  # 'image' o 'video'
    url: str
    thumbnail_url: Optional[str] = None
