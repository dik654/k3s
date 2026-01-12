"""
Pod 관련 비즈니스 로직
Pod 목록 조회, 메트릭 수집, 로그 조회 등
"""

from typing import Optional, Dict, List
from kubernetes.client.rest import ApiException

from core.kubernetes import get_k8s_clients
from utils.resources import parse_cpu, parse_memory
from models.pod import (
    ContainerStatus,
    PodMetrics,
    PodInfo,
    PodListResponse,
    LogEntry,
    PodLogsResponse,
)


async def list_all_pods() -> PodListResponse:
    """모든 네임스페이스의 Pod 목록 조회

    Returns:
        PodListResponse: Pod 목록 및 메타데이터
    """
    try:
        core_v1, _, custom = get_k8s_clients()
        pods = core_v1.list_pod_for_all_namespaces()

        # Pod 메트릭 조회 시도
        pod_metrics = {}
        try:
            metrics = custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="pods",
            )
            for item in metrics.get("items", []):
                key = f"{item['metadata']['namespace']}/{item['metadata']['name']}"
                containers = item.get("containers", [])
                if containers:
                    cpu_usage = sum(
                        parse_cpu(c.get("usage", {}).get("cpu", "0"))
                        for c in containers
                    )
                    memory_usage = sum(
                        parse_memory(c.get("usage", {}).get("memory", "0"))
                        for c in containers
                    )
                    pod_metrics[key] = {"cpu": cpu_usage, "memory": memory_usage}
        except Exception:
            pass

        result = []
        for pod in pods.items:
            key = f"{pod.metadata.namespace}/{pod.metadata.name}"
            metrics = pod_metrics.get(key, {})

            # 컨테이너 상태
            container_statuses = []
            for cs in pod.status.container_statuses or []:
                state = (
                    "running"
                    if cs.state.running
                    else "waiting" if cs.state.waiting else "terminated"
                )
                container_statuses.append(
                    ContainerStatus(
                        name=cs.name,
                        ready=cs.ready,
                        restarts=cs.restart_count,
                        state=state,
                    )
                )

            pod_info = PodInfo(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                status=pod.status.phase,
                node_name=pod.spec.node_name,
                pod_ip=pod.status.pod_ip,
                containers=container_statuses,
                metrics=(
                    PodMetrics(
                        cpu_usage=metrics.get("cpu", 0),
                        memory_usage=metrics.get("memory", 0),
                    )
                    if metrics
                    else None
                ),
                created_at=(
                    pod.metadata.creation_timestamp.isoformat()
                    if pod.metadata.creation_timestamp
                    else ""
                ),
                labels=pod.metadata.labels or {},
            )
            result.append(pod_info)

        # 네임스페이스별 그룹핑
        pods_by_namespace = {}
        for pod_info in result:
            ns = pod_info.namespace
            if ns not in pods_by_namespace:
                pods_by_namespace[ns] = 0
            pods_by_namespace[ns] += 1

        return PodListResponse(
            count=len(result),
            pods=result,
            pods_by_namespace=pods_by_namespace,
        )
    except Exception as e:
        raise Exception(f"Failed to list all pods: {str(e)}")


async def list_namespace_pods(namespace: str) -> Dict:
    """특정 네임스페이스의 Pod 목록 조회

    Args:
        namespace: Kubernetes 네임스페이스

    Returns:
        dict: Pod 목록
    """
    try:
        core_v1, _, custom = get_k8s_clients()
        pods = core_v1.list_namespaced_pod(namespace)

        # Pod 메트릭 조회 시도
        pod_metrics = {}
        try:
            metrics = custom.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
            )
            for item in metrics.get("items", []):
                name = item["metadata"]["name"]
                containers = item.get("containers", [])
                if containers:
                    cpu_usage = sum(
                        parse_cpu(c.get("usage", {}).get("cpu", "0"))
                        for c in containers
                    )
                    memory_usage = sum(
                        parse_memory(c.get("usage", {}).get("memory", "0"))
                        for c in containers
                    )
                    pod_metrics[name] = {"cpu": cpu_usage, "memory": memory_usage}
        except Exception:
            pass

        result = []
        for pod in pods.items:
            metrics = pod_metrics.get(pod.metadata.name, {})

            # 컨테이너 상태
            container_statuses = []
            for cs in pod.status.container_statuses or []:
                state = (
                    "running"
                    if cs.state.running
                    else "waiting" if cs.state.waiting else "terminated"
                )
                container_statuses.append(
                    ContainerStatus(
                        name=cs.name,
                        ready=cs.ready,
                        restarts=cs.restart_count,
                        state=state,
                    )
                )

            pod_info = PodInfo(
                name=pod.metadata.name,
                namespace=namespace,
                status=pod.status.phase,
                node_name=pod.spec.node_name,
                pod_ip=pod.status.pod_ip,
                containers=container_statuses,
                metrics=(
                    PodMetrics(
                        cpu_usage=metrics.get("cpu", 0),
                        memory_usage=metrics.get("memory", 0),
                    )
                    if metrics
                    else None
                ),
                created_at=(
                    pod.metadata.creation_timestamp.isoformat()
                    if pod.metadata.creation_timestamp
                    else ""
                ),
                labels=pod.metadata.labels or {},
            )
            result.append(pod_info)

        return {"namespace": namespace, "pods": result}
    except Exception as e:
        raise Exception(f"Failed to list namespace pods: {str(e)}")


async def get_pod_logs(
    namespace: str, pod_name: str, container: Optional[str] = None, tail_lines: int = 100
) -> PodLogsResponse:
    """Pod 로그 조회

    Args:
        namespace: Kubernetes 네임스페이스
        pod_name: Pod 이름
        container: 컨테이너 이름 (선택사항)
        tail_lines: 조회할 로그 라인 수

    Returns:
        PodLogsResponse: Pod 로그

    Raises:
        ApiException: Kubernetes API 호출 실패
    """
    try:
        core_v1, _, _ = get_k8s_clients()

        kwargs = {"tail_lines": tail_lines}
        if container:
            kwargs["container"] = container

        logs = core_v1.read_namespaced_pod_log(pod_name, namespace, **kwargs)

        # 로그를 라인별로 파싱하고 에러/경고 탐지
        log_entries: List[LogEntry] = []
        error_count = 0
        warning_count = 0

        for line in logs.split("\n"):
            if not line.strip():
                continue

            line_lower = line.lower()
            level = "info"
            if (
                "error" in line_lower
                or "exception" in line_lower
                or "fail" in line_lower
            ):
                level = "error"
                error_count += 1
            elif "warn" in line_lower:
                level = "warning"
                warning_count += 1

            log_entries.append(LogEntry(level=level, message=line))

        return PodLogsResponse(
            pod_name=pod_name,
            namespace=namespace,
            container=container,
            logs=log_entries,
            error_count=error_count,
            warning_count=warning_count,
            total_lines=len(log_entries),
        )
    except ApiException as e:
        if e.status == 404:
            raise Exception(f"Pod {pod_name} not found in namespace {namespace}")
        raise Exception(f"Failed to get pod logs: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to get pod logs: {str(e)}")


__all__ = [
    "list_all_pods",
    "list_namespace_pods",
    "get_pod_logs",
]
