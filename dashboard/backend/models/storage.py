"""
Storage related Pydantic models (MinIO, Longhorn)
"""
from typing import Optional, List, Dict
from pydantic import BaseModel


class StorageResetRequest(BaseModel):
    """스토리지 리셋 요청"""
    new_size_gb: int
    confirm: bool = False  # 데이터 삭제 확인


class BucketCreate(BaseModel):
    """버킷 생성"""
    name: str


class ObjectUpload(BaseModel):
    """객체 업로드 (base64 인코딩)"""
    object_name: str
    content: str  # base64 encoded
    content_type: str = "application/octet-stream"


class FolderCreate(BaseModel):
    """폴더 생성"""
    folder_name: str


class BucketPolicy(BaseModel):
    """버킷 정책"""
    policy: dict


class VersioningConfig(BaseModel):
    """버전 관리 설정"""
    enabled: bool


class AbortMultipartUpload(BaseModel):
    """멀티파트 업로드 중단"""
    object_name: str
    upload_id: str


class PresignedUrlRequest(BaseModel):
    """Presigned URL 요청"""
    object_name: str
    expires_hours: int = 1  # 기본 1시간
    method: str = "GET"  # GET 또는 PUT


class ObjectTags(BaseModel):
    """객체 태그"""
    tags: Dict[str, str]  # {"key": "value", ...}


class LifecycleRule(BaseModel):
    """생명주기 규칙"""
    rule_id: str
    prefix: str = ""
    enabled: bool = True
    expiration_days: Optional[int] = None
    noncurrent_expiration_days: Optional[int] = None
    transition_days: Optional[int] = None
    transition_storage_class: Optional[str] = None


class LifecycleConfig(BaseModel):
    """생명주기 설정"""
    rules: List[LifecycleRule]


class BucketQuota(BaseModel):
    """버킷 쿼터"""
    quota_bytes: int  # 바이트 단위 (0 = 무제한)
    quota_type: str = "hard"  # hard 또는 fifo


class StorageUser(BaseModel):
    """스토리지 사용자"""
    access_key: str
    secret_key: str  # 최소 8자
    policy: str = "readwrite"  # 기본 정책


class UserPolicy(BaseModel):
    """사용자 정책"""
    policy_name: str


class ObjectLockConfig(BaseModel):
    """객체 잠금 설정"""
    mode: str = "GOVERNANCE"  # GOVERNANCE 또는 COMPLIANCE
    duration: int = 30
    duration_unit: str = "DAYS"


class LegalHoldConfig(BaseModel):
    """법적 보관 설정"""
    enabled: bool


class RetentionConfig(BaseModel):
    """보존 정책"""
    mode: str = "GOVERNANCE"
    retain_until_date: str


class IAMUser(BaseModel):
    """IAM 사용자"""
    access_key: str
    secret_key: str
    policy: str = "readwrite"


class BucketUserPermission(BaseModel):
    """버킷 사용자 권한"""
    user: str
    access: str  # read, write, admin
    quota_gb: Optional[float] = None


class SnapshotCreate(BaseModel):
    """스냅샷 생성"""
    name: str
    labels: Optional[Dict[str, str]] = None


class SnapshotRestore(BaseModel):
    """스냅샷 복원"""
    snapshot_name: str
