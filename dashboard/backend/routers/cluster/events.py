"""
Events and Logs API
클러스터 이벤트 및 Pod 로그 조회
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from kubernetes import client, config
from kubernetes.client.rest import ApiException

router = APIRouter(tags=["events"])


def get_k8s_clients():
    """Kubernetes 클라이언트 초기화"""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api(), client.AppsV1Api(), client.CustomObjectsApi()


# ============================================
# 클러스터 이벤트 API
# ============================================

@router.get("/api/events")
async def get_cluster_events(namespace: str = None, limit: int = 100):
    """클러스터 이벤트 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        if namespace:
            events = core_v1.list_namespaced_event(namespace)
        else:
            events = core_v1.list_event_for_all_namespaces()

        # 최신순 정렬
        sorted_events = sorted(
            events.items,
            key=lambda e: e.last_timestamp or e.metadata.creation_timestamp or datetime.min.replace(tzinfo=None),
            reverse=True
        )[:limit]

        result = []
        for event in sorted_events:
            result.append({
                "name": event.metadata.name,
                "namespace": event.metadata.namespace,
                "type": event.type,  # Normal, Warning
                "reason": event.reason,
                "message": event.message,
                "source": event.source.component if event.source else "",
                "object": {
                    "kind": event.involved_object.kind if event.involved_object else "",
                    "name": event.involved_object.name if event.involved_object else ""
                },
                "count": event.count or 1,
                "first_timestamp": event.first_timestamp.isoformat() if event.first_timestamp else None,
                "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None
            })

        # 통계
        warning_count = sum(1 for e in result if e["type"] == "Warning")
        normal_count = sum(1 for e in result if e["type"] == "Normal")

        return {
            "events": result,
            "total": len(result),
            "warning_count": warning_count,
            "normal_count": normal_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Pod 로그 API
# ============================================

@router.get("/api/logs/{namespace}/{pod_name}")
async def get_pod_logs(namespace: str, pod_name: str, container: str = None, tail_lines: int = 100):
    """Pod 로그 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        kwargs = {"tail_lines": tail_lines}
        if container:
            kwargs["container"] = container

        logs = core_v1.read_namespaced_pod_log(pod_name, namespace, **kwargs)

        # 로그를 라인별로 파싱하고 에러/경고 탐지
        lines = []
        error_count = 0
        warning_count = 0

        for line in logs.split("\n"):
            line_lower = line.lower()
            level = "info"
            if "error" in line_lower or "exception" in line_lower or "fail" in line_lower:
                level = "error"
                error_count += 1
            elif "warn" in line_lower:
                level = "warning"
                warning_count += 1

            lines.append({
                "content": line,
                "level": level
            })

        return {
            "pod": pod_name,
            "namespace": namespace,
            "container": container,
            "lines": lines,
            "total_lines": len(lines),
            "error_count": error_count,
            "warning_count": warning_count
        }
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Pod {pod_name} not found")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
