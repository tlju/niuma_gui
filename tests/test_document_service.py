import pytest
from services.document_service import DocumentService

@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def document_service(db_session):
    return DocumentService(db_session)

def test_create_document(document_service):
    document = document_service.create_document(
        title="Test Document",
        content="This is test content",
        category="test",
        tags="tag1,tag2",
        created_by=1
    )
    assert document is not None
    assert document.title == "Test Document"
    assert document.content == "This is test content"
    assert document.category == "test"
    assert document.tags == "tag1,tag2"
    assert document.created_by == 1

def test_get_documents(document_service):
    document_service.create_document("Doc1", "Content 1", "category1")
    document_service.create_document("Doc2", "Content 2", "category2")
    document_service.create_document("Doc3", "Content 3", "category1")

    all_docs = document_service.get_documents()
    assert len(all_docs) == 3

    category_docs = document_service.get_documents(category="category1")
    assert len(category_docs) == 2

def test_get_document(document_service):
    created = document_service.create_document("Test Document", "Content")

    document = document_service.get_document(created.id)
    assert document is not None
    assert document.title == "Test Document"

    non_existent = document_service.get_document(999)
    assert non_existent is None

def test_get_documents_by_user(document_service):
    document_service.create_document("Doc1", "Content 1", created_by=1)
    document_service.create_document("Doc2", "Content 2", created_by=1)
    document_service.create_document("Doc3", "Content 3", created_by=2)

    user_docs = document_service.get_documents_by_user(1)
    assert len(user_docs) == 2

    user_docs_with_category = document_service.get_documents_by_user(2, category="test")
    assert len(user_docs_with_category) == 0

def test_update_document(document_service):
    document = document_service.create_document("Original Title", "Original content")

    updated = document_service.update_document(
        document.id,
        title="Updated Title",
        content="Updated content"
    )
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.content == "Updated content"

def test_update_non_existent_document(document_service):
    result = document_service.update_document(999, title="New Title")
    assert result is None

def test_delete_document(document_service):
    document = document_service.create_document("Test Document", "Content")

    deleted = document_service.delete_document(document.id)
    assert deleted is True

    document_after_delete = document_service.get_document(document.id)
    assert document_after_delete is None

def test_delete_non_existent_document(document_service):
    deleted = document_service.delete_document(999)
    assert deleted is False

def test_search_documents(document_service):
    document_service.create_document("Server Configuration", "This document describes server settings")
    document_service.create_document("Database Setup", "Database configuration guide")
    document_service.create_document("API Documentation", "API reference and usage")

    results = document_service.search_documents("server")
    assert len(results) == 1
    assert results[0].title == "Server Configuration"

    results = document_service.search_documents("configuration")
    assert len(results) == 2

def test_get_categories(document_service):
    document_service.create_document("Doc1", "Content", "category1")
    document_service.create_document("Doc2", "Content", "category2")
    document_service.create_document("Doc3", "Content", "category1")
    document_service.create_document("Doc4", "Content", None)

    categories = document_service.get_categories()
    assert len(categories) == 2
    assert "category1" in categories
    assert "category2" in categories
