from sqlalchemy.orm import Session

from src.models.companies import Company
from src.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: Session):
        super().__init__(Company, session)
