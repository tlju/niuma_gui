from minio import Minio
from minio.error import S3Error
from io import BytesIO
from typing import List, Optional, BinaryIO
from core.config import settings
from core.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


class MinioFileInfo:
    def __init__(self, name: str, size: int, content_type: str,
                 last_modified: datetime, is_dir: bool = False):
        self.name = name
        self.size = size
        self.content_type = content_type
        self.last_modified = last_modified
        self.is_dir = is_dir

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "size": self.size,
            "content_type": self.content_type,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "is_dir": self.is_dir,
        }


class MinioService:
    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket: str = None,
        secure: bool = None,
    ):
        self._endpoint = endpoint or settings.MINIO_ENDPOINT
        self._access_key = access_key or settings.MINIO_ACCESS_KEY
        self._secret_key = secret_key or settings.MINIO_SECRET_KEY
        self._bucket = bucket or settings.MINIO_BUCKET
        self._secure = secure if secure is not None else settings.MINIO_SECURE
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )
        return self._client

    @property
    def bucket(self) -> str:
        return self._bucket

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self._bucket):
            self.client.make_bucket(self._bucket)
            logger.info(f"创建存储桶: {self._bucket}")

    def upload_file(
        self,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
    ) -> bool:
        try:
            self.ensure_bucket()
            result = self.client.fput_object(
                self._bucket, object_name, file_path, content_type=content_type
            )
            logger.info(f"上传文件: {object_name} -> {result.version_id}")
            return True
        except S3Error as e:
            logger.error(f"上传文件失败: {object_name}, 错误: {e}")
            return False

    def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> bool:
        try:
            self.ensure_bucket()
            data_stream = BytesIO(data)
            self.client.put_object(
                self._bucket,
                object_name,
                data_stream,
                length=len(data),
                content_type=content_type,
            )
            logger.info(f"上传字节数据: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"上传字节数据失败: {object_name}, 错误: {e}")
            return False

    def upload_stream(
        self,
        object_name: str,
        stream: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> bool:
        try:
            self.ensure_bucket()
            self.client.put_object(
                self._bucket,
                object_name,
                stream,
                length=length,
                content_type=content_type,
            )
            logger.info(f"上传流数据: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"上传流数据失败: {object_name}, 错误: {e}")
            return False

    def download_file(self, object_name: str, file_path: str) -> bool:
        try:
            self.client.fget_object(self._bucket, object_name, file_path)
            logger.info(f"下载文件: {object_name} -> {file_path}")
            return True
        except S3Error as e:
            logger.error(f"下载文件失败: {object_name}, 错误: {e}")
            return False

    def download_bytes(self, object_name: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(self._bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"下载字节数据: {object_name}, 大小: {len(data)}")
            return data
        except S3Error as e:
            logger.error(f"下载字节数据失败: {object_name}, 错误: {e}")
            return None

    def get_file_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self._bucket, object_name, expires=timedelta(seconds=expires)
            )
            logger.info(f"获取文件预签名URL: {object_name}")
            return url
        except S3Error as e:
            logger.error(f"获取文件URL失败: {object_name}, 错误: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        try:
            self.client.remove_object(self._bucket, object_name)
            logger.info(f"删除文件: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"删除文件失败: {object_name}, 错误: {e}")
            return False

    def delete_files(self, object_names: List[str]) -> dict:
        results = {}
        for name in object_names:
            results[name] = self.delete_file(name)
        return results

    def list_files(self, prefix: str = "", recursive: bool = False) -> List[MinioFileInfo]:
        try:
            objects = self.client.list_objects(
                self._bucket, prefix=prefix, recursive=recursive
            )
            files = []
            for obj in objects:
                files.append(
                    MinioFileInfo(
                        name=obj.object_name,
                        size=obj.size if obj.size else 0,
                        content_type=obj.content_type or "",
                        last_modified=obj.last_modified,
                        is_dir=obj.is_dir,
                    )
                )
            logger.info(f"列出文件: prefix={prefix}, 数量={len(files)}")
            return files
        except S3Error as e:
            logger.error(f"列出文件失败: prefix={prefix}, 错误: {e}")
            return []

    def get_file_info(self, object_name: str) -> Optional[MinioFileInfo]:
        try:
            stat = self.client.stat_object(self._bucket, object_name)
            return MinioFileInfo(
                name=stat.object_name,
                size=stat.size,
                content_type=stat.content_type,
                last_modified=stat.last_modified,
            )
        except S3Error as e:
            logger.error(f"获取文件信息失败: {object_name}, 错误: {e}")
            return None

    def file_exists(self, object_name: str) -> bool:
        try:
            self.client.stat_object(self._bucket, object_name)
            return True
        except S3Error:
            return False

    def copy_file(self, source_name: str, dest_name: str) -> bool:
        from minio.commonconfig import CopySource
        try:
            self.client.copy_object(
                self._bucket,
                dest_name,
                CopySource(self._bucket, source_name),
            )
            logger.info(f"复制文件: {source_name} -> {dest_name}")
            return True
        except S3Error as e:
            logger.error(f"复制文件失败: {source_name} -> {dest_name}, 错误: {e}")
            return False

    def move_file(self, source_name: str, dest_name: str) -> bool:
        if self.copy_file(source_name, dest_name):
            return self.delete_file(source_name)
        return False

    def rename_file(self, old_name: str, new_name: str) -> bool:
        return self.move_file(old_name, new_name)
