import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
from datetime import datetime, timezone

from services.minio_service import MinioService, MinioFileInfo
from minio.error import S3Error


def _make_s3_error(code="NoSuchKey", message="not found"):
    mock_response = MagicMock()
    return S3Error(
        mock_response, code, message, "resource", "req-id", "host-id"
    )


@pytest.fixture
def mock_minio_client():
    with patch("services.minio_service.Minio") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def minio_service(mock_minio_client):
    service = MinioService(
        endpoint="127.0.0.1/gzdwt-minio",
        access_key="test_access",
        secret_key="test_secret",
        bucket="rapfile",
        secure=False,
    )
    service._client = mock_minio_client
    return service


def test_minio_file_info_to_dict():
    now = datetime.now(timezone.utc)
    info = MinioFileInfo(
        name="test.txt",
        size=1024,
        content_type="text/plain",
        last_modified=now,
        is_dir=False,
    )
    d = info.to_dict()
    assert d["name"] == "test.txt"
    assert d["size"] == 1024
    assert d["content_type"] == "text/plain"
    assert d["last_modified"] == now.isoformat()
    assert d["is_dir"] is False


def test_minio_file_info_dir():
    info = MinioFileInfo(
        name="folder/",
        size=0,
        content_type="",
        last_modified=None,
        is_dir=True,
    )
    d = info.to_dict()
    assert d["is_dir"] is True
    assert d["last_modified"] is None


def test_ensure_bucket_exists(minio_service, mock_minio_client):
    mock_minio_client.bucket_exists.return_value = True
    minio_service.ensure_bucket()
    mock_minio_client.bucket_exists.assert_called_once_with("rapfile")
    mock_minio_client.make_bucket.assert_not_called()


def test_ensure_bucket_not_exists(minio_service, mock_minio_client):
    mock_minio_client.bucket_exists.return_value = False
    minio_service.ensure_bucket()
    mock_minio_client.bucket_exists.assert_called_once_with("rapfile")
    mock_minio_client.make_bucket.assert_called_once_with("rapfile")


def test_upload_file(minio_service, mock_minio_client):
    mock_minio_client.bucket_exists.return_value = True
    mock_result = MagicMock()
    mock_result.version_id = "v1"
    mock_minio_client.fput_object.return_value = mock_result

    result = minio_service.upload_file("test.txt", "/tmp/test.txt", "text/plain")
    assert result is True
    mock_minio_client.fput_object.assert_called_once_with(
        "rapfile", "test.txt", "/tmp/test.txt", content_type="text/plain"
    )


def test_upload_file_failure(minio_service, mock_minio_client):
    mock_minio_client.bucket_exists.return_value = True
    mock_minio_client.fput_object.side_effect = _make_s3_error("NoSuchBucket", "bucket not found")

    result = minio_service.upload_file("test.txt", "/tmp/test.txt")
    assert result is False


def test_upload_bytes(minio_service, mock_minio_client):
    mock_minio_client.bucket_exists.return_value = True
    data = b"hello world"

    result = minio_service.upload_bytes("test.txt", data, "text/plain")
    assert result is True
    mock_minio_client.put_object.assert_called_once()
    call_args = mock_minio_client.put_object.call_args
    assert call_args[0][0] == "rapfile"
    assert call_args[0][1] == "test.txt"
    assert call_args[1]["length"] == len(data)
    assert call_args[1]["content_type"] == "text/plain"


def test_upload_stream(minio_service, mock_minio_client):
    mock_minio_client.bucket_exists.return_value = True
    stream = BytesIO(b"stream data")

    result = minio_service.upload_stream("test.txt", stream, length=11, content_type="text/plain")
    assert result is True
    mock_minio_client.put_object.assert_called_once()


def test_download_file(minio_service, mock_minio_client):
    result = minio_service.download_file("test.txt", "/tmp/downloaded.txt")
    assert result is True
    mock_minio_client.fget_object.assert_called_once_with("rapfile", "test.txt", "/tmp/downloaded.txt")


def test_download_file_failure(minio_service, mock_minio_client):
    mock_minio_client.fget_object.side_effect = _make_s3_error("NoSuchKey", "key not found")

    result = minio_service.download_file("nonexistent.txt", "/tmp/out.txt")
    assert result is False


def test_download_bytes(minio_service, mock_minio_client):
    mock_response = MagicMock()
    mock_response.read.return_value = b"file content"
    mock_minio_client.get_object.return_value = mock_response

    data = minio_service.download_bytes("test.txt")
    assert data == b"file content"
    mock_response.close.assert_called_once()
    mock_response.release_conn.assert_called_once()


def test_download_bytes_failure(minio_service, mock_minio_client):
    mock_minio_client.get_object.side_effect = _make_s3_error("NoSuchKey", "key not found")

    data = minio_service.download_bytes("nonexistent.txt")
    assert data is None


def test_get_file_url(minio_service, mock_minio_client):
    mock_minio_client.presigned_get_object.return_value = "http://127.0.0.1/gzdwt-minio/rapfile/test.txt?token=abc"

    url = minio_service.get_file_url("test.txt", expires=7200)
    assert url is not None
    assert "test.txt" in url
    mock_minio_client.presigned_get_object.assert_called_once()


def test_get_file_url_failure(minio_service, mock_minio_client):
    mock_minio_client.presigned_get_object.side_effect = _make_s3_error("InvalidAccessKeyId", "invalid key")

    url = minio_service.get_file_url("test.txt")
    assert url is None


def test_delete_file(minio_service, mock_minio_client):
    result = minio_service.delete_file("test.txt")
    assert result is True
    mock_minio_client.remove_object.assert_called_once_with("rapfile", "test.txt")


def test_delete_file_failure(minio_service, mock_minio_client):
    mock_minio_client.remove_object.side_effect = _make_s3_error("NoSuchKey", "key not found")

    result = minio_service.delete_file("nonexistent.txt")
    assert result is False


def test_delete_files(minio_service, mock_minio_client):
    result = minio_service.delete_files(["a.txt", "b.txt", "c.txt"])
    assert result["a.txt"] is True
    assert result["b.txt"] is True
    assert result["c.txt"] is True
    assert mock_minio_client.remove_object.call_count == 3


def test_list_files(minio_service, mock_minio_client):
    mock_obj1 = MagicMock()
    mock_obj1.object_name = "file1.txt"
    mock_obj1.size = 100
    mock_obj1.content_type = "text/plain"
    mock_obj1.last_modified = datetime.now(timezone.utc)
    mock_obj1.is_dir = False

    mock_obj2 = MagicMock()
    mock_obj2.object_name = "folder/"
    mock_obj2.size = 0
    mock_obj2.content_type = None
    mock_obj2.last_modified = datetime.now(timezone.utc)
    mock_obj2.is_dir = True

    mock_minio_client.list_objects.return_value = [mock_obj1, mock_obj2]

    files = minio_service.list_files(prefix="", recursive=False)
    assert len(files) == 2
    assert files[0].name == "file1.txt"
    assert files[0].is_dir is False
    assert files[1].name == "folder/"
    assert files[1].is_dir is True


def test_list_files_empty(minio_service, mock_minio_client):
    mock_minio_client.list_objects.return_value = []

    files = minio_service.list_files()
    assert files == []


def test_list_files_failure(minio_service, mock_minio_client):
    mock_minio_client.list_objects.side_effect = _make_s3_error("NoSuchBucket", "bucket not found")

    files = minio_service.list_files()
    assert files == []


def test_get_file_info(minio_service, mock_minio_client):
    mock_stat = MagicMock()
    mock_stat.object_name = "test.txt"
    mock_stat.size = 2048
    mock_stat.content_type = "text/plain"
    mock_stat.last_modified = datetime.now(timezone.utc)
    mock_minio_client.stat_object.return_value = mock_stat

    info = minio_service.get_file_info("test.txt")
    assert info is not None
    assert info.name == "test.txt"
    assert info.size == 2048
    assert info.content_type == "text/plain"


def test_get_file_info_not_found(minio_service, mock_minio_client):
    mock_minio_client.stat_object.side_effect = _make_s3_error("NoSuchKey", "key not found")

    info = minio_service.get_file_info("nonexistent.txt")
    assert info is None


def test_file_exists(minio_service, mock_minio_client):
    mock_minio_client.stat_object.return_value = MagicMock()
    assert minio_service.file_exists("test.txt") is True


def test_file_not_exists(minio_service, mock_minio_client):
    mock_minio_client.stat_object.side_effect = _make_s3_error("NoSuchKey", "key not found")
    assert minio_service.file_exists("nonexistent.txt") is False


def test_copy_file(minio_service, mock_minio_client):
    result = minio_service.copy_file("source.txt", "dest.txt")
    assert result is True
    mock_minio_client.copy_object.assert_called_once()


def test_copy_file_failure(minio_service, mock_minio_client):
    mock_minio_client.copy_object.side_effect = _make_s3_error("NoSuchKey", "key not found")

    result = minio_service.copy_file("source.txt", "dest.txt")
    assert result is False


def test_move_file(minio_service, mock_minio_client):
    result = minio_service.move_file("old.txt", "new.txt")
    assert result is True
    mock_minio_client.copy_object.assert_called_once()
    mock_minio_client.remove_object.assert_called_once_with("rapfile", "old.txt")


def test_move_file_copy_failure(minio_service, mock_minio_client):
    mock_minio_client.copy_object.side_effect = _make_s3_error("NoSuchKey", "key not found")

    result = minio_service.move_file("old.txt", "new.txt")
    assert result is False
    mock_minio_client.remove_object.assert_not_called()


def test_rename_file(minio_service, mock_minio_client):
    result = minio_service.rename_file("old_name.txt", "new_name.txt")
    assert result is True
    mock_minio_client.copy_object.assert_called_once()
    mock_minio_client.remove_object.assert_called_once_with("rapfile", "old_name.txt")


def test_bucket_property():
    service = MinioService(bucket="custom-bucket")
    assert service.bucket == "custom-bucket"


def test_client_lazy_init():
    with patch("services.minio_service.Minio") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        service = MinioService(
            endpoint="127.0.0.1/gzdwt-minio",
            access_key="test",
            secret_key="test",
            secure=False,
        )

        mock_cls.assert_not_called()

        client = service.client
        mock_cls.assert_called_once_with(
            "127.0.0.1/gzdwt-minio",
            access_key="test",
            secret_key="test",
            secure=False,
        )

        client2 = service.client
        assert client is client2
        mock_cls.assert_called_once()
