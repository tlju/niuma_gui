import pytest
from unittest.mock import MagicMock, patch
from models.system_param import SystemParam
from services.param_service import ParamService
from core.node_types import MinioNode, NodeStatus


@pytest.fixture
def param_service(db_session):
    return ParamService()


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


def test_minio_node_upload(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance
        mock_instance.bucket_exists.return_value = True

        node = MinioNode(1, "测试上传", {
            "operation": "upload",
            "object_name": "test/file.txt",
            "file_path": "/tmp/test.txt",
            "content_type": "text/plain"
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "上传成功" in result.output
        assert result.data["object_name"] == "test/file.txt"
        assert result.data["file_path"] == "/tmp/test.txt"


def test_minio_node_download(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance

        node = MinioNode(2, "测试下载", {
            "operation": "download",
            "object_name": "test/file.txt",
            "file_path": "/tmp/downloaded.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "下载成功" in result.output
        assert result.data["object_name"] == "test/file.txt"


def test_minio_node_delete(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance

        node = MinioNode(3, "测试删除", {
            "operation": "delete",
            "object_name": "test/file.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "删除成功" in result.output
        assert result.data["object_name"] == "test/file.txt"


def test_minio_node_list(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance

        from datetime import datetime, timezone
        mock_obj = MagicMock()
        mock_obj.object_name = "test/file.txt"
        mock_obj.size = 1024
        mock_obj.content_type = "text/plain"
        mock_obj.last_modified = datetime.now(timezone.utc)
        mock_obj.is_dir = False
        mock_instance.list_objects.return_value = [mock_obj]

        node = MinioNode(4, "测试列表", {
            "operation": "list",
            "prefix": "test/",
            "recursive": True
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "列出文件成功" in result.output
        assert result.data["count"] == 1
        assert len(result.data["files"]) == 1


def test_minio_node_copy(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance

        node = MinioNode(5, "测试复制", {
            "operation": "copy",
            "source_name": "test/source.txt",
            "dest_name": "test/dest.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "复制成功" in result.output
        assert result.data["source_name"] == "test/source.txt"
        assert result.data["dest_name"] == "test/dest.txt"


def test_minio_node_move(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance

        node = MinioNode(6, "测试移动", {
            "operation": "move",
            "source_name": "test/old.txt",
            "dest_name": "test/new.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "移动成功" in result.output
        assert result.data["source_name"] == "test/old.txt"
        assert result.data["dest_name"] == "test/new.txt"


def test_minio_node_exists_true(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance
        mock_instance.stat_object.return_value = MagicMock()

        node = MinioNode(7, "测试存在", {
            "operation": "exists",
            "object_name": "test/file.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "存在" in result.output
        assert result.data["exists"] is True


def test_minio_node_exists_false(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance
        from minio.error import S3Error
        mock_instance.stat_object.side_effect = S3Error(
            MagicMock(), "NoSuchKey", "not found", "resource", "req-id", "host-id"
        )

        node = MinioNode(8, "测试不存在", {
            "operation": "exists",
            "object_name": "test/nonexistent.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "不存在" in result.output
        assert result.data["exists"] is False


def test_minio_node_info(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance

        from datetime import datetime, timezone
        mock_stat = MagicMock()
        mock_stat.object_name = "test/file.txt"
        mock_stat.size = 2048
        mock_stat.content_type = "text/plain"
        mock_stat.last_modified = datetime.now(timezone.utc)
        mock_instance.stat_object.return_value = mock_stat

        node = MinioNode(9, "测试信息", {
            "operation": "info",
            "object_name": "test/file.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.SUCCESS
        assert "获取文件信息成功" in result.output
        assert "file_info" in result.data


def test_minio_node_no_db():
    node = MinioNode(10, "测试无数据库", {
        "operation": "upload",
        "object_name": "test/file.txt",
        "file_path": "/tmp/test.txt"
    })

    result = node.execute()

    assert result.status == NodeStatus.FAILED


def test_minio_node_no_operation(db_session, minio_params):
    node = MinioNode(11, "测试无操作", {})

    result = node.execute()

    assert result.status == NodeStatus.FAILED
    assert "未指定操作类型" in result.error


def test_minio_node_missing_params(db_session, minio_params):
    node = MinioNode(12, "测试缺少参数", {
        "operation": "upload"
    })

    result = node.execute()

    assert result.status == NodeStatus.FAILED
    assert "配置错误" in result.error


def test_minio_node_invalid_operation(db_session, minio_params):
    node = MinioNode(13, "测试无效操作", {
        "operation": "invalid_op"
    })

    result = node.execute()

    assert result.status == NodeStatus.FAILED
    assert "不支持的操作类型" in result.error


def test_minio_node_config_schema():
    node = MinioNode(0, "")
    schema = node.get_config_schema()

    assert schema["type"] == "object"
    assert "operation" in schema["properties"]
    assert "object_name" in schema["properties"]
    assert "file_path" in schema["properties"]
    assert "operation" in schema["required"]

    operation_prop = schema["properties"]["operation"]
    assert "enum" in operation_prop
    assert "upload" in operation_prop["enum"]
    assert "download" in operation_prop["enum"]
    assert "delete" in operation_prop["enum"]
    assert "list" in operation_prop["enum"]


def test_minio_node_variable_replacement(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance
        mock_instance.bucket_exists.return_value = True

        node = MinioNode(14, "测试变量替换", {
            "operation": "upload",
            "object_name": "test/@input.output",
            "file_path": "/tmp/@input.output"
        })

        inputs = {"output": "replaced.txt"}
        result = node.execute(inputs)

        assert result.status == NodeStatus.SUCCESS
        assert result.data["object_name"] == "test/replaced.txt"
        assert result.data["file_path"] == "/tmp/replaced.txt"


def test_minio_node_upload_failure(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance
        from minio.error import S3Error
        mock_instance.fput_object.side_effect = S3Error(
            MagicMock(), "NoSuchBucket", "bucket not found", "resource", "req-id", "host-id"
        )

        node = MinioNode(15, "测试上传失败", {
            "operation": "upload",
            "object_name": "test/file.txt",
            "file_path": "/tmp/test.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.FAILED
        assert "MinIO操作失败" in result.error


def test_minio_node_download_failure(db_session, minio_params):
    with patch("services.minio_service.Minio") as mock_minio_cls:
        mock_instance = MagicMock()
        mock_minio_cls.return_value = mock_instance
        from minio.error import S3Error
        mock_instance.fget_object.side_effect = S3Error(
            MagicMock(), "NoSuchKey", "key not found", "resource", "req-id", "host-id"
        )

        node = MinioNode(16, "测试下载失败", {
            "operation": "download",
            "object_name": "test/nonexistent.txt",
            "file_path": "/tmp/out.txt"
        })

        result = node.execute()

        assert result.status == NodeStatus.FAILED
        assert "MinIO操作失败" in result.error
