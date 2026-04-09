import pytest
from services.workflow_service import WorkflowService

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
def workflow_service(db_session):
    return WorkflowService(db_session)

def test_create_template(workflow_service):
    template = workflow_service.create_template(
        name="test_workflow",
        description="Test workflow template",
        definition={"steps": ["step1", "step2"]},
        created_by=1
    )
    assert template is not None
    assert template.name == "test_workflow"
    assert template.description == "Test workflow template"
    assert template.created_by == 1

def test_get_templates(workflow_service):
    workflow_service.create_template("workflow1", "Description 1")
    workflow_service.create_template("workflow2", "Description 2")

    templates = workflow_service.get_templates()
    assert len(templates) == 2

def test_get_template(workflow_service):
    created = workflow_service.create_template("test_workflow", "Test description")

    template = workflow_service.get_template(created.id)
    assert template is not None
    assert template.name == "test_workflow"

    non_existent = workflow_service.get_template(999)
    assert non_existent is None

def test_update_template(workflow_service):
    template = workflow_service.create_template("test_workflow", "Original description")

    updated = workflow_service.update_template(
        template.id,
        description="Updated description",
        definition={"steps": ["new_step"]}
    )
    assert updated is not None
    assert updated.description == "Updated description"

def test_update_non_existent_template(workflow_service):
    result = workflow_service.update_template(999, description="New description")
    assert result is None

def test_delete_template(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")

    deleted = workflow_service.delete_template(template.id)
    assert deleted is True

    template_after_delete = workflow_service.get_template(template.id)
    assert template_after_delete is None

def test_delete_non_existent_template(workflow_service):
    deleted = workflow_service.delete_template(999)
    assert deleted is False

def test_create_instance(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")

    instance = workflow_service.create_instance(
        template.id,
        name="test_instance",
        variables={"var1": "value1"}
    )
    assert instance is not None
    assert instance.name == "test_instance"
    assert instance.template_id == template.id

def test_create_instance_non_existent_template(workflow_service):
    with pytest.raises(ValueError) as exc_info:
        workflow_service.create_instance(999, "test_instance")
    assert "模板 999 不存在" in str(exc_info.value)

def test_get_instances(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")
    workflow_service.create_instance(template.id, "instance1")
    workflow_service.create_instance(template.id, "instance2")

    instances = workflow_service.get_instances(template_id=template.id)
    assert len(instances) == 2

def test_get_instance(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")
    created = workflow_service.create_instance(template.id, "test_instance")

    instance = workflow_service.get_instance(created.id)
    assert instance is not None
    assert instance.name == "test_instance"

def test_start_instance(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")
    instance = workflow_service.create_instance(template.id, "test_instance")

    started = workflow_service.start_instance(instance.id)
    assert started.status == "running"
    assert started.started_at is not None

def test_start_instance_already_started(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")
    instance = workflow_service.create_instance(template.id, "test_instance")
    workflow_service.start_instance(instance.id)

    with pytest.raises(ValueError) as exc_info:
        workflow_service.start_instance(instance.id)
    assert "实例已启动" in str(exc_info.value)

def test_complete_instance(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")
    instance = workflow_service.create_instance(template.id, "test_instance")
    workflow_service.start_instance(instance.id)

    completed = workflow_service.complete_instance(instance.id)
    assert completed.status == "completed"
    assert completed.completed_at is not None

def test_fail_instance(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")
    instance = workflow_service.create_instance(template.id, "test_instance")
    workflow_service.start_instance(instance.id)

    failed = workflow_service.fail_instance(instance.id)
    assert failed.status == "failed"
    assert failed.completed_at is not None

def test_create_execution_execution(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")
    instance = workflow_service.create_instance(template.id, "test_instance")

    execution = workflow_service.create_execution(
        instance.id,
        step_name="step1",
        status="completed",
        output="Success"
    )
    assert execution is not None
    assert execution.instance_id == instance.id
    assert execution.step_name == "step1"

def test_get_executions(workflow_service):
    template = workflow_service.create_template("test_workflow", "Test description")
    instance = workflow_service.create_instance(template.id, "test_instance")
    workflow_service.create_execution(instance.id, "step1", "completed")
    workflow_service.create_execution(instance.id, "step2", "completed")

    executions = workflow_service.get_executions(instance.id)
    assert len(executions) == 2

def test_get_template_definition(workflow_service):
    definition = {"steps": ["step1", "step2"]}
    template = workflow_service.create_template(
        "test_workflow",
        "Test description",
        definition=definition
    )

    retrieved = workflow_service.get_template_definition(template.id)
    assert retrieved == definition

def test_get_instance_variables(workflow_service):
    variables = {"var1": "value1", "var2": "value2"}
    template = workflow_service.create_template("test_workflow", "Test description")
    instance = workflow_service.create_instance(template.id, variables=variables)

    retrieved = workflow_service.get_instance_variables(instance.id)
    assert retrieved == variables
