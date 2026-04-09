import pytest
from services.param_service import ParamService

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
def param_service(db_session):
    return ParamService(db_session)

def test_create_param(param_service):
    param = param_service.create_param(
        param_name="Test Parameter",
        param_code="test_key",
        param_value="test_value",
        status=1,
        description="Test parameter"
    )
    assert param is not None
    assert param.param_name == "Test Parameter"
    assert param.param_code == "test_key"
    assert param.param_value == "test_value"
    assert param.status == 1
    assert param.description == "Test parameter"

def test_create_param_duplicate_key(param_service):
    param = param_service.create_param(
        param_name="Test Parameter",
        param_code="test_key",
        param_value="test_value"
    )
    assert param is not None

    with pytest.raises(ValueError) as exc_info:
        param_service.create_param(
            param_name="Another Parameter",
            param_code="test_key",
            param_value="another_value"
        )
    assert "参数代码 test_key 已存在" in str(exc_info.value)

def test_get_params(param_service):
    param_service.create_param("Parameter 1", "key1", "value1", 1, "Description 1")
    param_service.create_param("Parameter 2", "key2", "value2", 1, "Description 2")
    param_service.create_param("Parameter 3", "key3", "value3", 0, "Description 3")

    params = param_service.get_params()
    assert len(params) == 3

    params_with_limit = param_service.get_params(skip=1, limit=1)
    assert len(params_with_limit) == 1

def test_get_param(param_service):
    created_param = param_service.create_param(
        param_name="Test Parameter",
        param_code="test_key",
        param_value="test_value"
    )

    param = param_service.get_param(created_param.id)
    assert param is not None
    assert param.param_name == "Test Parameter"
    assert param.param_code == "test_key"
    assert param.param_value == "test_value"

    non_existent = param_service.get_param(999)
    assert non_existent is None

def test_get_param_by_code(param_service):
    param_service.create_param(
        param_name="Test Parameter",
        param_code="test_key",
        param_value="test_value"
    )

    param = param_service.get_param_by_code("test_key")
    assert param is not None
    assert param.param_name == "Test Parameter"
    assert param.param_code == "test_key"
    assert param.param_value == "test_value"

    non_existent = param_service.get_param_by_code("non_existent_key")
    assert non_existent is None

def test_update_param(param_service):
    param = param_service.create_param(
        param_name="Test Parameter",
        param_code="test_key",
        param_value="test_value",
        status=1,
        description="Original description"
    )

    updated = param_service.update_param(
        param.id,
        param_value="new_value",
        description="Updated description"
    )
    assert updated is not None
    assert updated.param_value == "new_value"
    assert updated.description == "Updated description"
    assert updated.param_code == "test_key"

def test_update_param_code(param_service):
    param = param_service.create_param(
        param_name="Test Parameter",
        param_code="test_key",
        param_value="test_value"
    )

    updated = param_service.update_param(
        param.id,
        param_code="new_key"
    )
    assert updated is not None
    assert updated.param_code == "new_key"

def test_update_param_duplicate_code(param_service):
    param1 = param_service.create_param("Parameter 1", "key1", "value1")
    param2 = param_service.create_param("Parameter 2", "key2", "value2")

    with pytest.raises(ValueError) as exc_info:
        param_service.update_param(param2.id, param_code="key1")
    assert "参数代码 key1 已存在" in str(exc_info.value)

def test_update_non_existent_param(param_service):
    result = param_service.update_param(999, param_value="new_value")
    assert result is None

def test_delete_param(param_service):
    param = param_service.create_param(
        param_name="Test Parameter",
        param_code="test_key",
        param_value="test_value"
    )

    deleted = param_service.delete_param(param.id)
    assert deleted is True

    param_after_delete = param_service.get_param(param.id)
    assert param_after_delete is None

def test_delete_non_existent_param(param_service):
    deleted = param_service.delete_param(999)
    assert deleted is False

def test_search_params(param_service):
    param_service.create_param("Server Host", "server_host", "192.168.1.1", 1, "Server host address")
    param_service.create_param("Server Port", "server_port", "8080", 1, "Server port number")
    param_service.create_param("Database URL", "database_url", "localhost", 1, "Database connection URL")

    results = param_service.search_params("server")
    assert len(results) == 2

    results = param_service.search_params("port")
    assert len(results) == 1
    assert results[0].param_code == "server_port"

    results = param_service.search_params("connection")
    assert len(results) == 1
    assert results[0].param_code == "database_url"

def test_create_param_with_defaults(param_service):
    param = param_service.create_param(
        param_name="Test Parameter",
        param_code="test_key",
        param_value="test_value"
    )
    assert param.status == 1
    assert param.description is None
