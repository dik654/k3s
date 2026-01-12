"""
Cluster related Pydantic models
"""
from typing import Optional, List
from pydantic import BaseModel


class WorkloadAction(BaseModel):
    """워크로드 작업 요청"""
    action: str  # start, stop, scale
    replicas: Optional[int] = 1
    storage_size_gb: Optional[int] = None  # RustFS 스토리지 할당 크기 (GB)


class StorageConfig(BaseModel):
    """스토리지 설정"""
    size_gb: int


class NodeInfo(BaseModel):
    """노드 정보"""
    name: str
    status: str
    roles: List[str]
    cpu_capacity: str
    cpu_used: str
    memory_capacity: str
    memory_used: str
    gpu_count: int
    gpu_type: str


class NodeJoinInfo(BaseModel):
    """노드 조인 정보"""
    node_ip: str
    node_name: Optional[str] = None
    role: str = "worker"  # worker, master
