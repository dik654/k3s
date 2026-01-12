"""
스토리지 관리 라우터
- minio: MinIO 오브젝트 스토리지
- longhorn: Longhorn 분산 스토리지
"""
from .minio import router as storage_router
from .longhorn import router as longhorn_router

__all__ = [
    "storage_router",
    "longhorn_router"
]
