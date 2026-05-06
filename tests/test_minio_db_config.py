import pytest
from unittest.mock import MagicMock, patch
from models.system_param import SystemParam
from services.minio_service import MinioService
from services.param_service import ParamService


@pytest.fixture
def param_service(db_session):
    return ParamService(db_session)


@pytest.fixture
def minio_params(param_service):
    param_service.create_param(
        param_name="MinIO Endpoint",
        param_code="minio_endpoint",
        param_value="minio.example.com:9000",
        status=1,
        description="MinIO服务端点"
    )
    param_service.create_param(
        param_name="MinIO Access Key",
        param_code="minio_access_key",
        param_value="test_access_key",
        status=1,
        description="MinIO访问密钥"
    )
    param_service.create_param(
        param_name="MinIO Secret Key",
        param_code="minio_secret_key",
        param_value="test_secret_key",
        status=1,
        description="MinIO秘密密钥"
    )
    param_service.create_param(
        param_name="MinIO Bucket",
        param_code="minio_bucket",
        param_value="test-bucket",
        status=1,
        description="MinIO存储桶"
    )
    param_service.create_param(
        param_name="MinIO Secure",
        param_code="minio_secure",
        param_value="false",
        status=1,
        description="是否使用HTTPS"
    )


def test_minio_service_with_db_params(db_session, minio_params):
    service = MinioService(db=db_session)
    
    assert service._endpoint == "minio.example.com:9000"
    assert service._access_key == "test_access_key"
    assert service._secret_key == "test_secret_key"
    assert service._bucket == "test-bucket"
    assert service._secure is False


def test_minio_service_with_db_params_secure_true(db_session, param_service):
    param_service.create_param(
        param_name="MinIO Endpoint",
        param_code="minio_endpoint",
        param_value="minio.example.com:9000",
        status=1
    )
    param_service.create_param(
        param_name="MinIO Access Key",
        param_code="minio_access_key",
        param_value="test_access_key",
        status=1
    )
    param_service.create_param(
        param_name="MinIO Secret Key",
        param_code="minio_secret_key",
        param_value="test_secret_key",
        status=1
    )
    param_service.create_param(
        param_name="MinIO Bucket",
        param_code="minio_bucket",
        param_value="test-bucket",
        status=1
    )
    param_service.create_param(
        param_name="MinIO Secure",
        param_code="minio_secure",
        param_value="true",
        status=1
    )
    
    service = MinioService(db=db_session)
    assert service._secure is True


def test_minio_service_with_override_params(db_session, minio_params):
    service = MinioService(
        db=db_session,
        endpoint="override.example.com:9000",
        bucket="override-bucket"
    )
    
    assert service._endpoint == "override.example.com:9000"
    assert service._access_key == "test_access_key"
    assert service._secret_key == "test_secret_key"
    assert service._bucket == "override-bucket"
    assert service._secure is False


def test_minio_service_without_db():
    service = MinioService(
        endpoint="manual.example.com:9000",
        access_key="manual_access",
        secret_key="manual_secret",
        bucket="manual-bucket",
        secure=True
    )
    
    assert service._endpoint == "manual.example.com:9000"
    assert service._access_key == "manual_access"
    assert service._secret_key == "manual_secret"
    assert service._bucket == "manual-bucket"
    assert service._secure is True


def test_minio_service_with_disabled_param(db_session, param_service):
    param_service.create_param(
        param_name="MinIO Endpoint",
        param_code="minio_endpoint",
        param_value="minio.example.com:9000",
        status=0
    )
    param_service.create_param(
        param_name="MinIO Access Key",
        param_code="minio_access_key",
        param_value="test_access_key",
        status=1
    )
    
    service = MinioService(db=db_session)
    
    assert service._endpoint is None
    assert service._access_key == "test_access_key"


def test_minio_service_with_missing_params(db_session):
    service = MinioService(db=db_session)
    
    assert service._endpoint is None
    assert service._access_key is None
    assert service._secret_key is None
    assert service._bucket is None
    assert service._secure is False


def test_minio_service_client_init_with_db_params(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance
        
        service = MinioService(db=db_session)
        client = service.client
        
        mock_minio_cls.assert_called_once_with(
            "minio.example.com:9000",
            access_key="test_access_key",
            secret_key="test_secret_key",
            secure=False
        )
        assert client is mock_instance


def test_minio_service_secure_variations(db_session, param_service):
    param_service.create_param(
        param_name="MinIO Endpoint",
        param_code="minio_endpoint",
        param_value="minio.example.com:9000",
        status=1
    )
    param_service.create_param(
        param_name="MinIO Access Key",
        param_code="minio_access_key",
        param_value="test_access_key",
        status=1
    )
    param_service.create_param(
        param_name="MinIO Secret Key",
        param_code="minio_secret_key",
        param_value="test_secret_key",
        status=1
    )
    param_service.create_param(
        param_name="MinIO Bucket",
        param_code="minio_bucket",
        param_value="test-bucket",
        status=1
    )
    
    test_cases = [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("YES", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("0", False),
        ("no", False),
        ("NO", False),
    ]
    
    for value, expected in test_cases:
        param = param_service.get_param_by_code("minio_secure")
        if param:
            param_service.update_param(param.id, param_value=value)
        else:
            param_service.create_param(
                param_name="MinIO Secure",
                param_code="minio_secure",
                param_value=value,
                status=1
            )
        
        service = MinioService(db=db_session)
        assert service._secure == expected, f"Failed for value: {value}"
