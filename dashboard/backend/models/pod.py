"""
Pod 관련 Pydantic 모델
Pod 정보, 메트릭, 로그 등의 데이터 구조 정의
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ContainerStatus(BaseModel):
    """컨테이너 상태 정보"""
    name: str
    ready: bool
    restarts: int
    state: str  # "running", "waiting", "terminated"
    state_reason: Optional[str] = None


class PodMetrics(BaseModel):
    """Pod 리소스 사용량"""
    cpu_usage: float  # millicores
    memory_usage: int  # MB


class PodInfo(BaseModel):
    """Pod 상세 정보"""
    name: str
    namespace: str
    status: str  # "Running", "Pending", "Failed", etc.
    node_name: Optional[str] = None
    pod_ip: Optional[str] = None
    containers: List[ContainerStatus]
    metrics: Optional[PodMetrics] = None
    created_at: str
    labels: Dict[str, str] = {}


class PodListResponse(BaseModel):
    """Pod 목록 응답"""
    count: int
    pods: List[PodInfo]
    pods_by_namespace: Optional[Dict[str, int]] = None


class LogEntry(BaseModel):
    """로그 엔트리"""
    timestamp: Optional[str] = None
    level: str  # "error", "warning", "info", "debug"
    message: str


class PodLogsResponse(BaseModel):
    """Pod 로그 응답"""
    pod_name: str
    namespace: str
    container: Optional[str] = None
    logs: List[LogEntry]
    error_count: int
    warning_count: int
    total_lines: int


__all__ = [
    "ContainerStatus",
    "PodMetrics",
    "PodInfo",
    "PodListResponse",
    "LogEntry",
    "PodLogsResponse",
]
