import pytest
from services.todo_service import TodoService
from models.todo import TodoStatus, RecurrenceType
from datetime import datetime, timedelta

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
def todo_service(db_session):
    return TodoService(db_session)

def test_create_todo(todo_service):
    todo = todo_service.create_todo(
        title="Test Todo",
        description="Test description",
        priority=5,
        assigned_to=1,
        due_date=datetime.now() + timedelta(days=1)
    )
    assert todo is not None
    assert todo.title == "Test Todo"
    assert todo.description == "Test description"
    assert todo.priority == 5
    assert todo.assigned_to == 1
    assert todo.status == TodoStatus.PENDING

def test_get_todos(todo_service):
    todo_service.create_todo("Todo 1", "Description 1")
    todo_service.create_todo("Todo 2", "Description 2")
    todo_service.create_todo("Todo 3", "Description 3")

    all_todos = todo_service.get_todos()
    assert len(all_todos) == 3

def test_get_todos_with_status(todo_service):
    todo1 = todo_service.create_todo("Todo 1", "Description 1")
    todo2 = todo_service.create_todo("Todo 2", "Description 2")
    todo_service.complete_todo(todo1.id)

    pending_todos = todo_service.get_todos(status=TodoStatus.PENDING)
    assert len(pending_todos) == 1

    completed_todos = todo_service.get_todos(status=TodoStatus.COMPLETED)
    assert len(completed_todos) == 1

def test_get_todo(todo_service):
    created = todo_service.create_todo("Test Todo", "Test description")

    todo = todo_service.get_todo(created.id)
    assert todo is not None
    assert todo.title == "Test Todo"

    non_existent = todo_service.get_todo(999)
    assert non_existent is None

def test_get_todos_by_user(todo_service):
    todo_service.create_todo("Todo 1", "Description 1", assigned_to=1)
    todo_service.create_todo("Todo 2", "Description 2", assigned_to=1)
    todo_service.create_todo("Todo 3", "Description 3", assigned_to=2)

    user_todos = todo_service.get_todos_by_user(1)
    assert len(user_todos) == 2

def test_update_todo(todo_service):
    todo = todo_service.create_todo("Original Title", "Original description")

    updated = todo_service.update_todo(
        todo.id,
        title="Updated Title",
        description="Updated description",
        priority=8
    )
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.description == "Updated description"
    assert updated.priority == 8

def test_update_todo_status_to_completed(todo_service):
    todo = todo_service.create_todo("Test Todo", "Description")
    assert todo.completed_at is None

    updated = todo_service.update_todo(todo.id, status=TodoStatus.COMPLETED)
    assert updated.status == TodoStatus.COMPLETED
    assert updated.completed_at is not None

def test_update_non_existent_todo(todo_service):
    result = todo_service.update_todo(999, title="New Title")
    assert result is None

def test_delete_todo(todo_service):
    todo = todo_service.create_todo("Test Todo", "Description")

    deleted = todo_service.delete_todo(todo.id)
    assert deleted is True

    todo_after_delete = todo_service.get_todo(todo.id)
    assert todo_after_delete is None

def test_delete_non_existent_todo(todo_service):
    deleted = todo_service.delete_todo(999)
    assert deleted is False

def test_complete_todo(todo_service):
    todo = todo_service.create_todo("Test Todo", "Description")
    assert todo.status == TodoStatus.PENDING

    completed = todo_service.complete_todo(todo.id)
    assert completed.status == TodoStatus.COMPLETED
    assert completed.completed_at is not None

def test_search_todos(todo_service):
    todo_service.create_todo("Server Setup", "Configure the server settings")
    todo_service.create_todo("Database Migration", "Migrate database to new schema")
    todo_service.create_todo("API Testing", "Test API endpoints")

    results = todo_service.search_todos("server")
    assert len(results) == 1
    assert results[0].title == "Server Setup"

    results = todo_service.search_todos("database")
    assert len(results) == 1

    results = todo_service.search_todos("Test")
    assert len(results) == 1


def test_create_recurring_todo(todo_service):
    todo = todo_service.create_todo(
        title="Weekly Meeting",
        description="Team sync",
        recurrence_type=RecurrenceType.WEEKLY,
        recurrence_interval=1
    )
    assert todo is not None
    assert todo.recurrence_type == RecurrenceType.WEEKLY
    assert todo.recurrence_interval == 1


def test_complete_recurring_todo_creates_next(todo_service):
    todo = todo_service.create_todo(
        title="Weekly Meeting",
        description="Team sync",
        recurrence_type=RecurrenceType.WEEKLY,
        recurrence_interval=1,
        due_date=datetime.now()
    )
    
    initial_count = len(todo_service.get_todos())
    
    completed = todo_service.complete_todo(todo.id)
    assert completed.status == TodoStatus.COMPLETED
    
    all_todos = todo_service.get_todos()
    assert len(all_todos) == initial_count + 1
    
    new_todo = [t for t in all_todos if t.status == TodoStatus.PENDING and t.title == "Weekly Meeting"][0]
    assert new_todo.recurrence_type == RecurrenceType.WEEKLY
    assert new_todo.recurrence_interval == 1


def test_complete_non_recurring_todo_no_new(todo_service):
    todo = todo_service.create_todo(
        title="One-time Task",
        description="Do once"
    )
    
    initial_count = len(todo_service.get_todos())
    
    completed = todo_service.complete_todo(todo.id)
    assert completed.status == TodoStatus.COMPLETED
    
    all_todos = todo_service.get_todos()
    assert len(all_todos) == initial_count
