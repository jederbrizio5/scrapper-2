from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy.orm import Session
from src.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: Session):
        self.model = model
        self.session = session

    def create(self, **kwargs) -> ModelType:
        """Crea una nueva entidad."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def get(self, id: int) -> Optional[ModelType]:
        """Obtiene una entidad por su ID."""
        return self.session.get(self.model, id)

    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Actualiza una entidad existente."""
        instance = self.get(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            self.session.commit()
            self.session.refresh(instance)
        return instance

    def delete(self, id: int) -> bool:
        """Elimina una entidad por su ID."""
        instance = self.get(id)
        if instance:
            self.session.delete(instance)
            self.session.commit()
            return True
        return False

    def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Lista todas las entidades con paginación."""
        return self.session.query(self.model).offset(skip).limit(limit).all()
