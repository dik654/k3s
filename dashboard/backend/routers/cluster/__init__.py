"""
클러스터 관리 라우터
- status: 클러스터 상태, 노드 정보
- workloads: 워크로드 관리 (배포, 스케일링)
- pods: Pod 관리
- events: 클러스터 이벤트
"""
from .status import router as cluster_router
from .workloads import router as workloads_router
from .pods import router as pods_router
from .events import router as events_router

__all__ = [
    "cluster_router",
    "workloads_router",
    "pods_router",
    "events_router"
]
