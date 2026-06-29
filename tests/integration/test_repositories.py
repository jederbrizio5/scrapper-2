from src.repositories.search_repository import SearchRepository
from src.repositories.domain_repository import DomainRepository
from src.repositories.company_repository import CompanyRepository
from src.repositories.lead_repository import LeadRepository


def test_search_crud(session):
    repo = SearchRepository(session)

    # Create
    search = repo.create(keyword="abogados", idioma="es", pais="es")
    assert search.id is not None
    assert search.keyword == "abogados"
    assert search.estado == "pending"

    # Get
    fetched = repo.get(search.id)
    assert fetched.id == search.id

    # Update
    repo.update(search.id, estado="completed")
    updated = repo.get(search.id)
    assert updated.estado == "completed"

    # List
    items = repo.list()
    assert len(items) == 1

    # Delete
    repo.delete(search.id)
    assert repo.get(search.id) is None


def test_domain_crud(session):
    repo = DomainRepository(session)

    domain = repo.create(dominio="example.com", fuente="test")
    assert domain.id is not None
    assert domain.activo is True


def test_company_and_lead_crud(session):
    domain_repo = DomainRepository(session)
    company_repo = CompanyRepository(session)
    lead_repo = LeadRepository(session)

    domain = domain_repo.create(dominio="company.com", fuente="test")
    company = company_repo.create(
        nombre="Test Corp", dominio_id=domain.id, industria="IT"
    )
    assert company.id is not None

    lead = lead_repo.create(company_id=company.id, score=10.5)
    assert lead.id is not None
    assert lead.score == 10.5
    assert lead.estado == "new"

    lead_repo.update(lead.id, estado="contacted", score=50.0)
    updated_lead = lead_repo.get(lead.id)
    assert updated_lead.score == 50.0
