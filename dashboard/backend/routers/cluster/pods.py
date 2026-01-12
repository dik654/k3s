"""
Pod management API
Pod 목록, 상태, 로그 조회
"""
from fastapi import APIRouter, HTTPException
from kubernetes.client.rest import ApiException
from utils.k8s import get_k8s_clients, parse_cpu, parse_memory

router = APIRouter(prefix="/api/pods", tags=["pods"])


@router.get("")
async def get_all_pods():
    """모든 네임스페이스의 Pod 목록"""
    try:
        core_v1, _, custom = get_k8s_clients()
        pods = core_v1.list_pod_for_all_namespaces()

        # Pod 메트릭 조회 시도
        pod_metrics = {}
        try:
            metrics = custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="pods"
            )
            for item in metrics.get("items", []):
                key = f"{item['metadata']['namespace']}/{item['metadata']['name']}"
                containers = item.get("containers", [])
                if containers:
                    cpu_usage = sum(parse_cpu(c.get("usage", {}).get("cpu", "0")) for c in containers)
                    memory_usage = sum(parse_memory(c.get("usage", {}).get("memory", "0")) for c in containers)
                    pod_metrics[key] = {"cpu": cpu_usage, "memory": memory_usage}
        except:
            pass

        result = []
        for pod in pods.items:
            key = f"{pod.metadata.namespace}/{pod.metadata.name}"
            metrics = pod_metrics.get(key, {})

            # 컨테이너 상태
            container_statuses = []
            for cs in (pod.status.container_statuses or []):
                container_statuses.append({
                    "name": cs.name,
                    "ready": cs.ready,
                    "restarts": cs.restart_count,
                    "state": "running" if cs.state.running else "waiting" if cs.state.waiting else "terminated"
                })

            result.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "ip": pod.status.pod_ip,
                "cpu_usage": metrics.get("cpu", 0),
                "memory_usage": metrics.get("memory", 0),
                "containers": container_statuses,
                "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
            })

        # 네임스페이스별 그룹핑
        by_namespace = {}
        for pod in result:
            ns = pod["namespace"]
            if ns not in by_namespace:
                by_namespace[ns] = []
            by_namespace[ns].append(pod)

        return {
            "total": len(result),
            "pods": result,
            "by_namespace": by_namespace
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{namespace}")
async def get_namespace_pods(namespace: str):
    """특정 네임스페이스의 Pod 목록"""
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
                plural="pods"
            )
            for item in metrics.get("items", []):
                name = item['metadata']['name']
                containers = item.get("containers", [])
                if containers:
                    cpu_usage = sum(parse_cpu(c.get("usage", {}).get("cpu", "0")) for c in containers)
                    memory_usage = sum(parse_memory(c.get("usage", {}).get("memory", "0")) for c in containers)
                    pod_metrics[name] = {"cpu": cpu_usage, "memory": memory_usage}
        except:
            pass

        result = []
        for pod in pods.items:
            metrics = pod_metrics.get(pod.metadata.name, {})

            result.append({
                "name": pod.metadata.name,
                "namespace": namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "ip": pod.status.pod_ip,
                "cpu_usage": metrics.get("cpu", 0),
                "memory_usage": metrics.get("memory", 0),
                "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
            })

        return {"namespace": namespace, "pods": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
