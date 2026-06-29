from sqlalchemy.orm import Session
from src.repositories.base import BaseRepository
from src.models.leads import Lead


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, session: Session):
        super().__init__(Lead, session)
