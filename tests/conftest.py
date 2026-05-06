from __future__ import annotations

import pytest
import sys
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("CRYPTO_KEY", "test-crypto-key-for-unit-tests-only-32b")

from models.base import Base

_GET_DB_MODULES = [
    "core.database",
    "services.workflow_service",
    "services.script_service",
    "services.asset_service",
    "services.todo_service",
    "services.document_service",
    "services.auth_service",
    "services.audit_service",
    "services.param_service",
    "services.dict_service",
    "services.audit_mixin",
    "services.minio_service",
    "core.node_types",
]


@pytest.fixture(scope="session")
def qapp():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture(scope="session")
def engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _patch_get_db(db_session, monkeypatch):
    @contextmanager
    def _mock_get_db():
        yield db_session

    import importlib
    for module_name in _GET_DB_MODULES:
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            continue
        if hasattr(mod, "get_db"):
            monkeypatch.setattr(f"{module_name}.get_db", _mock_get_db)
        if hasattr(mod, "get_thread_db"):
            monkeypatch.setattr(f"{module_name}.get_thread_db", _mock_get_db)
