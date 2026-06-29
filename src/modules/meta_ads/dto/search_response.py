from dataclasses import dataclass, field
from typing import List, Optional
from src.modules.meta_ads.dto.ad import Ad


@dataclass
class SearchResponse:
    ads: List[Ad] = field(default_factory=list)
    next_cursor: Optional[str] = None
    total_results: Optional[int] = None
