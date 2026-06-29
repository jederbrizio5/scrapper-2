from sqlalchemy.orm import Session
from src.repositories.base import BaseRepository
from src.models.domains import Domain


class DomainRepository(BaseRepository[Domain]):
    def __init__(self, session: Session):
        super().__init__(Domain, session)
