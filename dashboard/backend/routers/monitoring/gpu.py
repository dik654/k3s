"""
GPU monitoring API
GPU 상태, 온도, VRAM, 사용률 모니터링
GPU를 사용하는 Pod 정보 포함
"""
from fastapi import APIRouter, HTTPException
from kubernetes.client.rest import ApiException
import httpx
from typing import Dict, List, Optional, Any
from utils.k8s import get_k8s_clients

router = APIRouter(prefix="/api/gpu", tags=["gpu"])


# ============================================
# GPU 메트릭 수집 함수
# ============================================

async def get_gpu_metrics_from_collectors() -> Optional[List[Dict[str, Any]]]:
    """GPU 메트릭 collector Pod들에서 실시간 메트릭 수집"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # gpu-metrics Pod 목록 조회
        pods = core_v1.list_namespaced_pod(
            namespace="dashboard",
            label_selector="app=gpu-metrics"
        )

        all_gpus = []
        gpu_index = 0

        async with httpx.AsyncClient(timeout=5.0) as client:
            for pod in pods.items:
                if pod.status.phase != "Running":
                    continue

                pod_ip = pod.status.pod_ip
                if not pod_ip:
                    continue

                try:
                    response = await client.get(f"http://{pod_ip}:9400/metrics")
                    if response.status_code == 200:
                        data = response.json()
                        node_name = data.get("node", pod.spec.node_name)

                        for gpu in data.get("gpus", []):
                            gpu["index"] = gpu_index
                            gpu["node"] = node_name
                            gpu["status"] = "available"
                            all_gpus.append(gpu)
                            gpu_index += 1
                except Exception as e:
                    print(f"Failed to get metrics from {pod_ip}: {e}")
                    continue

        return all_gpus if all_gpus else None
    except Exception as e:
        print(f"Error getting GPU metrics: {e}")
        return None


def get_gpu_info_from_k8s() -> Optional[List[Dict[str, Any]]]:
    """Kubernetes 노드에서 GPU 정보 조회 (fallback)"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        gpus = []
        gpu_index = 0

        for node in nodes.items:
            capacity = node.status.capacity or {}
            labels = node.metadata.labels or {}

            # nvidia.com/gpu 리소스 확인
            gpu_capacity = capacity.get("nvidia.com/gpu", "0")

            try:
                gpu_count = int(gpu_capacity)
            except:
                gpu_count = 0

            if gpu_count > 0:
                # GPU 타입 추출 (라벨에서 또는 기본값)
                gpu_type = labels.get("nvidia.com/gpu.product",
                           labels.get("gpu-type", "NVIDIA GPU"))

                # 메모리 정보 (라벨에서)
                gpu_memory = labels.get("nvidia.com/gpu.memory", "0")
                try:
                    memory_total = int(gpu_memory)
                except:
                    memory_total = 24576  # 기본값 24GB

                # 각 GPU에 대해 항목 생성
                for i in range(gpu_count):
                    gpus.append({
                        "index": gpu_index,
                        "local_index": i,  # 노드 내 로컬 인덱스
                        "name": gpu_type,
                        "node": node.metadata.name,
                        "temperature": 0,
                        "memory_used": 0,
                        "memory_total": memory_total,
                        "utilization": 0,
                        "power_draw": 0,
                        "power_limit": 350,
                        "status": "available"
                    })
                    gpu_index += 1

        return gpus
    except Exception as e:
        print(f"Error getting GPU info: {e}")
        return None


def get_pods_using_gpu() -> List[Dict[str, Any]]:
    """GPU를 사용하는 Pod 목록 조회 (노드 및 GPU 인덱스 정보 포함)"""
    try:
        core_v1, _, _ = get_k8s_clients()
        pods = core_v1.list_pod_for_all_namespaces()

        # 노드별 GPU 정보 수집
        nodes = core_v1.list_node()
        node_gpu_info = {}  # node_name -> {"gpu_count": n, "gpu_type": str}

        for node in nodes.items:
            capacity = node.status.capacity or {}
            labels = node.metadata.labels or {}
            gpu_count = int(capacity.get("nvidia.com/gpu", "0"))

            if gpu_count > 0:
                gpu_type = labels.get("nvidia.com/gpu.product",
                           labels.get("gpu-type", "NVIDIA GPU"))
                node_gpu_info[node.metadata.name] = {
                    "gpu_count": gpu_count,
                    "gpu_type": gpu_type,
                    "allocated_indices": []  # 할당된 GPU 인덱스 추적
                }

        gpu_pods = []

        for pod in pods.items:
            if pod.status.phase not in ["Running", "Pending"]:
                continue

            pod_name = pod.metadata.name
            namespace = pod.metadata.namespace
            node_name = pod.spec.node_name or ""

            for container in (pod.spec.containers or []):
                resources = container.resources or {}
                requests = resources.requests or {}
                limits = resources.limits or {}

                gpu_req = requests.get("nvidia.com/gpu", "0")
                gpu_lim = limits.get("nvidia.com/gpu", "0")

                try:
                    gpu_count = int(gpu_req) if gpu_req else 0
                    if gpu_count <= 0:
                        gpu_count = int(gpu_lim) if gpu_lim else 0

                    if gpu_count > 0:
                        # GPU 인덱스 할당 (노드의 사용 가능한 GPU 순서대로)
                        gpu_indices = []
                        if node_name in node_gpu_info:
                            node_info = node_gpu_info[node_name]
                            for i in range(gpu_count):
                                # 다음 사용 가능한 인덱스 할당
                                next_index = len(node_info["allocated_indices"])
                                if next_index < node_info["gpu_count"]:
                                    gpu_indices.append(next_index)
                                    node_info["allocated_indices"].append(next_index)

                        gpu_pods.append({
                            "namespace": namespace,
                            "pod": pod_name,
                            "container": container.name,
                            "node": node_name,
                            "gpu_count": gpu_count,
                            "gpu_indices": gpu_indices,
                            "gpu_type": node_gpu_info.get(node_name, {}).get("gpu_type", "Unknown"),
                            "status": pod.status.phase
                        })
                except:
                    pass

        return gpu_pods
    except Exception as e:
        print(f"Error getting GPU pods: {e}")
        return []


def get_pod_gpu_mapping() -> Dict[str, Dict[str, Any]]:
    """Pod이 요청한 GPU 정보를 포드별로 매핑"""
    try:
        core_v1 = get_k8s_clients()[0]
        pods = core_v1.list_pod_for_all_namespaces()
        pod_gpu_map = {}  # pod_name -> {"namespace": ns, "gpu_count": n, "container": c}

        for pod in pods.items:
            if pod.status.phase not in ["Running", "Pending"]:
                continue
            pod_name = pod.metadata.name
            namespace = pod.metadata.namespace

            for container in (pod.spec.containers or []):
                resources = container.resources or {}
                requests = resources.requests or {}
                gpu_req = requests.get("nvidia.com/gpu", "0")
                try:
                    gpu_count = int(gpu_req) if gpu_req else 0
                    if gpu_count > 0:
                        pod_gpu_map[f"{namespace}/{pod_name}/{container.name}"] = {
                            "namespace": namespace,
                            "pod": pod_name,
                            "container": container.name,
                            "gpu_count": gpu_count,
                            "node": pod.spec.node_name or ""
                        }
                except:
                    pass

        return pod_gpu_map
    except Exception:
        return {}


# ============================================
# GPU API 엔드포인트
# ============================================

@router.get("/status")
async def get_gpu_status():
    """GPU 상태 조회 (기본 정보)"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        gpu_nodes = []
        total_gpus = 0

        for node in nodes.items:
            capacity = node.status.capacity or {}
            labels = node.metadata.labels or {}

            # nvidia.com/gpu 리소스 확인
            gpu_capacity = capacity.get("nvidia.com/gpu", "0")
            try:
                gpu_count = int(gpu_capacity)
            except:
                gpu_count = 0

            if gpu_count > 0:
                gpu_type = labels.get("nvidia.com/gpu.product",
                           labels.get("gpu-type", "NVIDIA GPU"))

                gpu_nodes.append({
                    "node": node.metadata.name,
                    "gpu_type": gpu_type,
                    "gpu_count": gpu_count,
                    "status": "available"
                })
                total_gpus += gpu_count

        # GPU 사용 중인 Pod 수 계산
        gpu_pods = get_pods_using_gpu()
        pods_using_gpu = len(gpu_pods)
        gpus_in_use = sum(p.get("gpu_count", 0) for p in gpu_pods)

        return {
            "total_gpus": total_gpus,
            "gpus_in_use": gpus_in_use,
            "gpus_available": total_gpus - gpus_in_use,
            "pods_using_gpu": pods_using_gpu,
            "gpu_nodes": gpu_nodes
        }
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detailed")
async def get_gpu_detailed():
    """GPU 상세 정보 조회 (메트릭, Pod 할당 정보 포함)"""
    try:
        # 먼저 collector에서 실시간 메트릭 시도
        gpus = await get_gpu_metrics_from_collectors()

        # collector가 없으면 K8s 정보로 fallback
        if gpus is None or len(gpus) == 0:
            gpus = get_gpu_info_from_k8s()

        if gpus is None or len(gpus) == 0:
            return {
                "available": False,
                "message": "클러스터에 GPU 노드가 없습니다",
                "gpus": [],
                "gpu_pods": []
            }

        # GPU를 사용하는 Pod 정보 조회
        gpu_pods = get_pods_using_gpu()

        # GPU별로 사용 중인 Pod 매핑
        for gpu in gpus:
            gpu["assigned_pods"] = []
            node_name = gpu.get("node", "")
            local_index = gpu.get("local_index", gpu.get("index", 0))

            for pod in gpu_pods:
                if pod.get("node") == node_name:
                    # 이 Pod가 이 GPU 인덱스를 사용하는지 확인
                    pod_gpu_indices = pod.get("gpu_indices", [])
                    if local_index in pod_gpu_indices or not pod_gpu_indices:
                        gpu["assigned_pods"].append({
                            "namespace": pod["namespace"],
                            "pod": pod["pod"],
                            "container": pod["container"]
                        })
                        gpu["status"] = "in_use"

        return {
            "available": True,
            "gpu_count": len(gpus),
            "gpus": gpus,
            "gpu_pods": gpu_pods
        }
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pods")
async def get_gpu_pods():
    """GPU를 사용하는 모든 Pod 목록 조회"""
    try:
        gpu_pods = get_pods_using_gpu()

        # 노드별로 그룹핑
        pods_by_node = {}
        for pod in gpu_pods:
            node = pod.get("node", "unknown")
            if node not in pods_by_node:
                pods_by_node[node] = []
            pods_by_node[node].append(pod)

        return {
            "total_pods": len(gpu_pods),
            "total_gpus_allocated": sum(p.get("gpu_count", 0) for p in gpu_pods),
            "pods": gpu_pods,
            "pods_by_node": pods_by_node
        }
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes")
async def get_gpu_nodes():
    """GPU가 있는 노드 목록 및 상세 정보"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        gpu_pods = get_pods_using_gpu()

        # 노드별 GPU 사용 Pod 매핑
        pods_by_node = {}
        for pod in gpu_pods:
            node = pod.get("node", "")
            if node not in pods_by_node:
                pods_by_node[node] = []
            pods_by_node[node].append(pod)

        gpu_nodes = []

        for node in nodes.items:
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}
            labels = node.metadata.labels or {}

            gpu_capacity = capacity.get("nvidia.com/gpu", "0")
            try:
                gpu_count = int(gpu_capacity)
            except:
                gpu_count = 0

            if gpu_count > 0:
                gpu_type = labels.get("nvidia.com/gpu.product",
                           labels.get("gpu-type", "NVIDIA GPU"))
                gpu_memory = labels.get("nvidia.com/gpu.memory", "0")

                node_name = node.metadata.name
                node_pods = pods_by_node.get(node_name, [])
                gpus_in_use = sum(p.get("gpu_count", 0) for p in node_pods)

                gpu_nodes.append({
                    "node": node_name,
                    "gpu_type": gpu_type,
                    "gpu_count": gpu_count,
                    "gpus_in_use": gpus_in_use,
                    "gpus_available": gpu_count - gpus_in_use,
                    "gpu_memory_mb": int(gpu_memory) if gpu_memory.isdigit() else 0,
                    "status": "available" if gpus_in_use < gpu_count else "fully_allocated",
                    "pods": node_pods
                })

        return {
            "total_gpu_nodes": len(gpu_nodes),
            "total_gpus": sum(n["gpu_count"] for n in gpu_nodes),
            "total_gpus_in_use": sum(n["gpus_in_use"] for n in gpu_nodes),
            "nodes": gpu_nodes
        }
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
