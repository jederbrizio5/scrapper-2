from dataclasses import dataclass
from typing import Optional


@dataclass
class Page:
    id: str
    name: str
    url: Optional[str] = None
    profile_picture_url: Optional[str] = None
