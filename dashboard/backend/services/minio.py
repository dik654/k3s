"""
MinIO service
S3 호환 스토리지 관리
"""
import os
from typing import Optional
from minio import Minio


class MinioService:
    """MinIO 서비스"""

    _client: Optional[Minio] = None

    @classmethod
    def get_client(cls) -> Minio:
        """MinIO 클라이언트 싱글톤"""
        if cls._client is None:
            cls._client = Minio(
                os.getenv("MINIO_ENDPOINT", "minio.storage.svc.cluster.local:9000"),
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                secure=os.getenv("MINIO_SECURE", "false").lower() == "true"
            )
        return cls._client

    @classmethod
    def format_size(cls, size_bytes: int) -> str:
        """바이트를 읽기 쉬운 형태로 변환"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
