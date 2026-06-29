from sqlalchemy.orm import Session
from src.repositories.base import BaseRepository
from src.models.searches import Search


class SearchRepository(BaseRepository[Search]):
    def __init__(self, session: Session):
        super().__init__(Search, session)
