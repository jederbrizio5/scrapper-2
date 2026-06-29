from dataclasses import dataclass


@dataclass
class SearchRequest:
    keyword: str
    country: str = "ALL"
    language: str = "ALL"
    limit: int = 10
    cursor: str | None = None
