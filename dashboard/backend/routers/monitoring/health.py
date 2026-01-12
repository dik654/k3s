"""
Health check API
"""
from fastapi import APIRouter
from core.kubernetes import get_k8s_clients

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    """API 헬스체크"""
    return {"status": "healthy", "service": "k3s-dashboard"}


@router.get("/api/k8s/health")
async def k8s_health_check():
    """Kubernetes 연결 헬스체크"""
    try:
        core_v1, _, _ = get_k8s_clients()
        core_v1.list_namespace(limit=1)
        return {"status": "connected"}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}
