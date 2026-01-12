"""
Cluster management API
클러스터 상태, 노드 관리, 리소스 모니터링
"""
import subprocess
import httpx
from fastapi import APIRouter, HTTPException
from kubernetes.client.rest import ApiException
from utils.k8s import get_k8s_clients, parse_cpu, parse_memory

router = APIRouter(prefix="/api", tags=["cluster"])


# ============================================
# 헬퍼 함수
# ============================================

def get_pod_gpu_mapping():
    """Pod이 요청한 GPU 정보를 포드별로 매핑"""
    try:
        core_v1 = get_k8s_clients()[0]
        pods = core_v1.list_pod_for_all_namespaces()
        pod_gpu_map = {}

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


def get_actual_gpu_usage() -> dict:
    """nvidia-smi를 통해 실제 GPU 사용 상태 확인 (500MB 이상 사용 시 사용 중으로 간주)"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,memory.used', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )

        gpu_status = {}
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                idx = parts[0].strip()
                mem_mb = int(parts[1].strip())
                gpu_status[int(idx)] = mem_mb > 500

        return gpu_status
    except Exception:
        return {}


async def get_gpu_metrics_from_collectors():
    """GPU 메트릭 collector Pod들에서 실시간 메트릭 수집"""
    try:
        core_v1, _, _ = get_k8s_clients()

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


# ============================================
# 클러스터 상태 API
# ============================================

@router.get("/cluster/status")
async def get_cluster_status():
    """클러스터 전체 상태 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        # 노드 정보
        nodes = core_v1.list_node()
        node_count = len(nodes.items)
        ready_nodes = sum(1 for n in nodes.items
                        if any(c.type == "Ready" and c.status == "True"
                              for c in n.status.conditions))

        # 전체 Pod 수
        pods = core_v1.list_pod_for_all_namespaces()
        running_pods = sum(1 for p in pods.items if p.status.phase == "Running")

        # 네임스페이스 수
        namespaces = core_v1.list_namespace()

        return {
            "status": "healthy" if ready_nodes == node_count else "degraded",
            "nodes": {
                "total": node_count,
                "ready": ready_nodes
            },
            "pods": {
                "total": len(pods.items),
                "running": running_pods
            },
            "namespaces": len(namespaces.items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/summary")
async def get_cluster_summary():
    """클러스터 전체 요약 (리소스 사용률 포함)"""
    try:
        core_v1, apps_v1, custom = get_k8s_clients()

        # 노드 정보
        nodes = core_v1.list_node()
        node_count = len(nodes.items)
        ready_nodes = sum(1 for n in nodes.items
                        if any(c.type == "Ready" and c.status == "True"
                              for c in n.status.conditions))

        # 전체 용량 계산
        total_cpu_capacity = 0
        total_memory_capacity = 0
        total_gpu_count = 0
        gpu_by_type = {}

        for node in nodes.items:
            capacity = node.status.capacity or {}
            labels = node.metadata.labels or {}

            cpu = capacity.get("cpu", "0")
            if cpu.endswith('m'):
                total_cpu_capacity += float(cpu[:-1]) / 1000
            else:
                total_cpu_capacity += float(cpu)

            total_memory_capacity += parse_memory(capacity.get("memory", "0"))

            gpu_capacity = capacity.get("nvidia.com/gpu", "0")
            try:
                gpu_count = int(gpu_capacity)
            except:
                gpu_count = 0

            if gpu_count > 0:
                total_gpu_count += gpu_count
                gpu_type = labels.get("nvidia.com/gpu.product",
                           labels.get("gpu-type", "NVIDIA GPU"))
                if gpu_type in gpu_by_type:
                    gpu_by_type[gpu_type] += gpu_count
                else:
                    gpu_by_type[gpu_type] = gpu_count

        # Pod 정보
        pods = core_v1.list_pod_for_all_namespaces()
        running_pods = sum(1 for p in pods.items if p.status.phase == "Running")
        pending_pods = sum(1 for p in pods.items if p.status.phase == "Pending")
        failed_pods = sum(1 for p in pods.items if p.status.phase == "Failed")

        # 네임스페이스 수
        namespaces = core_v1.list_namespace()

        # 리소스 사용률 조회
        total_cpu_usage = 0
        total_memory_usage = 0
        try:
            metrics = custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
            for item in metrics.get("items", []):
                usage = item.get("usage", {})
                total_cpu_usage += parse_cpu(usage.get("cpu", "0"))
                total_memory_usage += parse_memory(usage.get("memory", "0"))
        except:
            pass

        return {
            "status": "healthy" if ready_nodes == node_count else "degraded",
            "nodes": {
                "total": node_count,
                "ready": ready_nodes
            },
            "pods": {
                "total": len(pods.items),
                "running": running_pods,
                "pending": pending_pods,
                "failed": failed_pods
            },
            "namespaces": len(namespaces.items),
            "resources": {
                "cpu": {
                    "usage": round(total_cpu_usage, 1),
                    "capacity": round(total_cpu_capacity * 1000, 1),
                    "percent": round(total_cpu_usage / (total_cpu_capacity * 1000) * 100, 1) if total_cpu_capacity > 0 else 0
                },
                "memory": {
                    "usage": total_memory_usage,
                    "capacity": total_memory_capacity,
                    "percent": round(total_memory_usage / total_memory_capacity * 100, 1) if total_memory_capacity > 0 else 0
                },
                "gpu": {
                    "total": total_gpu_count,
                    "by_type": gpu_by_type
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/resources")
async def get_cluster_resources():
    """클러스터 전체 리소스 현황"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        total_cpu = 0
        total_memory = 0
        total_gpu = 0
        total_pods_capacity = 0
        total_pods_used = 0

        for node in nodes.items:
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}

            # CPU (코어 단위로 변환)
            cpu_str = capacity.get("cpu", "0")
            if cpu_str.endswith("m"):
                total_cpu += int(cpu_str[:-1]) / 1000
            else:
                total_cpu += int(cpu_str)

            # 메모리 (bytes로 변환)
            mem_str = capacity.get("memory", "0")
            if mem_str.endswith("Ki"):
                total_memory += int(mem_str[:-2]) * 1024
            elif mem_str.endswith("Mi"):
                total_memory += int(mem_str[:-2]) * 1024 * 1024
            elif mem_str.endswith("Gi"):
                total_memory += int(mem_str[:-2]) * 1024 * 1024 * 1024

            # GPU
            total_gpu += int(capacity.get("nvidia.com/gpu", 0))

            # Pods
            total_pods_capacity += int(allocatable.get("pods", 110))

            # 이 노드의 Pod 수
            pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node.metadata.name}")
            total_pods_used += len(pods.items)

        def format_memory(bytes_val):
            if bytes_val >= 1024**4:
                return f"{bytes_val / (1024**4):.1f} TB"
            elif bytes_val >= 1024**3:
                return f"{bytes_val / (1024**3):.1f} GB"
            elif bytes_val >= 1024**2:
                return f"{bytes_val / (1024**2):.1f} MB"
            return f"{bytes_val} B"

        return {
            "cpu": {
                "total": total_cpu,
                "unit": "cores"
            },
            "memory": {
                "total": total_memory,
                "total_human": format_memory(total_memory)
            },
            "gpu": {
                "total": total_gpu
            },
            "pods": {
                "used": total_pods_used,
                "capacity": total_pods_capacity,
                "usage_percent": round(total_pods_used / total_pods_capacity * 100, 1) if total_pods_capacity > 0 else 0
            },
            "nodes": {
                "total": len(nodes.items)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 노드 관리 API
# ============================================

@router.get("/nodes")
async def get_nodes():
    """노드 목록 및 리소스 정보"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        result = []
        for node in nodes.items:
            # 노드 상태
            status = "Unknown"
            for condition in node.status.conditions:
                if condition.type == "Ready":
                    status = "Ready" if condition.status == "True" else "NotReady"
                    break

            # 역할 추출
            roles = []
            for label, value in (node.metadata.labels or {}).items():
                if label.startswith("node-role.kubernetes.io/"):
                    roles.append(label.split("/")[1])

            # GPU 정보
            gpu_count = int(node.metadata.labels.get("gpu-count", "0"))
            gpu_type = node.metadata.labels.get("gpu-type", "none")

            # 리소스 용량
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}

            result.append({
                "name": node.metadata.name,
                "status": status,
                "roles": roles if roles else ["worker"],
                "cpu_capacity": capacity.get("cpu", "0"),
                "memory_capacity": capacity.get("memory", "0"),
                "gpu_count": gpu_count,
                "gpu_type": gpu_type,
                "created": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else None
            })

        return {"nodes": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/nodes")
async def get_cluster_nodes():
    """클러스터 노드 목록 및 상세 정보 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        result = []
        for node in nodes.items:
            node_name = node.metadata.name
            labels = node.metadata.labels or {}

            # 노드 역할 판별
            is_master = "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels
            role = "master" if is_master else "worker"

            # 상태 확인
            conditions = {c.type: c.status for c in node.status.conditions} if node.status.conditions else {}
            is_ready = conditions.get("Ready") == "True"

            # 리소스 정보
            allocatable = node.status.allocatable or {}
            capacity = node.status.capacity or {}

            # 주소 정보
            addresses = {addr.type: addr.address for addr in node.status.addresses} if node.status.addresses else {}

            # 노드 정보
            node_info = node.status.node_info

            # 이 노드의 Pod 수
            pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
            pod_count = len(pods.items)

            # GPU 정보
            gpu_count = int(capacity.get("nvidia.com/gpu", 0))

            result.append({
                "name": node_name,
                "role": role,
                "status": "Ready" if is_ready else "NotReady",
                "internal_ip": addresses.get("InternalIP", ""),
                "external_ip": addresses.get("ExternalIP", ""),
                "hostname": addresses.get("Hostname", node_name),
                "os": node_info.os_image if node_info else "",
                "kernel": node_info.kernel_version if node_info else "",
                "container_runtime": node_info.container_runtime_version if node_info else "",
                "kubelet_version": node_info.kubelet_version if node_info else "",
                "cpu_capacity": capacity.get("cpu", "0"),
                "cpu_allocatable": allocatable.get("cpu", "0"),
                "memory_capacity": capacity.get("memory", "0"),
                "memory_allocatable": allocatable.get("memory", "0"),
                "storage_capacity": capacity.get("ephemeral-storage", "0"),
                "gpu_count": gpu_count,
                "pod_count": pod_count,
                "pod_capacity": int(allocatable.get("pods", 110)),
                "labels": labels,
                "taints": [{"key": t.key, "value": t.value, "effect": t.effect} for t in (node.spec.taints or [])],
                "created": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else None
            })

        return {
            "nodes": result,
            "total": len(result),
            "master_count": sum(1 for n in result if n["role"] == "master"),
            "worker_count": sum(1 for n in result if n["role"] == "worker"),
            "ready_count": sum(1 for n in result if n["status"] == "Ready")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/nodes/{node_name}")
async def get_node_detail(node_name: str):
    """특정 노드 상세 정보 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        try:
            node = core_v1.read_node(node_name)
        except ApiException as e:
            if e.status == 404:
                raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
            raise

        # 노드의 Pod 목록
        pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
        pod_list = []
        for pod in pods.items:
            pod_list.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip
            })

        # 노드 이벤트
        events = core_v1.list_event_for_all_namespaces(
            field_selector=f"involvedObject.name={node_name},involvedObject.kind=Node"
        )
        event_list = []
        for event in events.items[:20]:
            event_list.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "time": event.last_timestamp.isoformat() if event.last_timestamp else None
            })

        labels = node.metadata.labels or {}
        allocatable = node.status.allocatable or {}
        capacity = node.status.capacity or {}
        addresses = {addr.type: addr.address for addr in node.status.addresses} if node.status.addresses else {}
        node_info = node.status.node_info
        is_master = "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels

        return {
            "name": node_name,
            "role": "master" if is_master else "worker",
            "internal_ip": addresses.get("InternalIP", ""),
            "os": node_info.os_image if node_info else "",
            "kernel": node_info.kernel_version if node_info else "",
            "architecture": node_info.architecture if node_info else "",
            "container_runtime": node_info.container_runtime_version if node_info else "",
            "kubelet_version": node_info.kubelet_version if node_info else "",
            "cpu_capacity": capacity.get("cpu", "0"),
            "memory_capacity": capacity.get("memory", "0"),
            "gpu_count": int(capacity.get("nvidia.com/gpu", 0)),
            "pods": pod_list,
            "pod_count": len(pod_list),
            "events": event_list,
            "labels": labels,
            "taints": [{"key": t.key, "value": t.value, "effect": t.effect} for t in (node.spec.taints or [])]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_name}/metrics")
async def get_node_metrics(node_name: str):
    """노드 리소스 사용량 (metrics-server 필요)"""
    try:
        core_v1, _, custom = get_k8s_clients()

        try:
            metrics = custom.get_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes",
                name=node_name
            )

            return {
                "node": node_name,
                "cpu_usage": metrics.get("usage", {}).get("cpu", "0"),
                "memory_usage": metrics.get("usage", {}).get("memory", "0"),
                "timestamp": metrics.get("timestamp")
            }
        except ApiException as e:
            if e.status == 404:
                return {
                    "node": node_name,
                    "cpu_usage": "N/A",
                    "memory_usage": "N/A",
                    "message": "metrics-server not available"
                }
            raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/metrics")
async def get_all_nodes_metrics():
    """모든 노드의 리소스 사용률 (requests/limits 포함)"""
    try:
        core_v1, _, custom = get_k8s_clients()

        # 노드 정보 조회
        nodes = core_v1.list_node()
        node_info = {}
        for node in nodes.items:
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}
            labels = node.metadata.labels or {}

            # CPU 용량 (코어 수)
            cpu_capacity = capacity.get("cpu", "0")
            if cpu_capacity.endswith('m'):
                cpu_capacity_cores = float(cpu_capacity[:-1]) / 1000
            else:
                cpu_capacity_cores = float(cpu_capacity)

            # 메모리 용량 (MB)
            mem_capacity = parse_memory(capacity.get("memory", "0"))

            # GPU 정보
            gpu_capacity = int(capacity.get("nvidia.com/gpu", "0"))
            gpu_type = labels.get("nvidia.com/gpu.product", labels.get("gpu-type", ""))

            node_info[node.metadata.name] = {
                "cpu_capacity": cpu_capacity_cores * 1000,
                "memory_capacity": mem_capacity,
                "gpu_capacity": gpu_capacity,
                "gpu_type": gpu_type
            }

        # Pod의 GPU 매핑 정보 수집
        pod_gpu_map = get_pod_gpu_mapping()

        # 노드별 리소스 예약(requests/limits) 계산
        pods = core_v1.list_pod_for_all_namespaces()
        node_requests = {}
        node_limits = {}
        node_gpu_usage = {}
        node_pod_gpu_list = {}

        for pod in pods.items:
            if pod.status.phase not in ["Running", "Pending"]:
                continue
            node_name = pod.spec.node_name or ""
            if node_name not in node_requests:
                node_requests[node_name] = {"cpu": 0, "memory": 0, "gpu": 0}
                node_limits[node_name] = {"cpu": 0, "memory": 0, "gpu": 0}
                node_gpu_usage[node_name] = 0
                node_pod_gpu_list[node_name] = []

            for container in (pod.spec.containers or []):
                resources = container.resources or {}
                requests = resources.requests or {}
                limits = resources.limits or {}

                # CPU requests/limits
                cpu_req = requests.get("cpu", "0")
                cpu_lim = limits.get("cpu", "0")
                node_requests[node_name]["cpu"] += parse_cpu(cpu_req)
                node_limits[node_name]["cpu"] += parse_cpu(cpu_lim)

                # Memory requests/limits
                mem_req = requests.get("memory", "0")
                mem_lim = requests.get("memory", "0")
                node_requests[node_name]["memory"] += parse_memory(mem_req)
                node_limits[node_name]["memory"] += parse_memory(mem_lim)

                # GPU requests
                gpu_req = requests.get("nvidia.com/gpu", "0")
                gpu_lim = limits.get("nvidia.com/gpu", "0")
                try:
                    gpu_count = int(gpu_req) if gpu_req else 0
                    node_requests[node_name]["gpu"] += gpu_count

                    if gpu_count > 0:
                        node_pod_gpu_list[node_name].append({
                            "namespace": pod.metadata.namespace,
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "gpu_count": gpu_count
                        })
                except:
                    pass

        # 실제 GPU 사용 상태 확인 (nvidia-smi)
        actual_gpu_usage = get_actual_gpu_usage()

        # 실제 사용 중인 GPU 개수 계산 (500MB 이상)
        for node_name in node_requests:
            node_gpu_usage[node_name] = sum(1 for v in actual_gpu_usage.values() if v)

        # GPU 상세 메트릭 수집 (collector에서)
        gpu_metrics_list = await get_gpu_metrics_from_collectors()

        # 노드별로 GPU 메트릭 그룹핑
        gpu_metrics_by_node = {}
        if gpu_metrics_list:
            for gpu in gpu_metrics_list:
                node = gpu.get('node', '')
                if node not in gpu_metrics_by_node:
                    gpu_metrics_by_node[node] = []
                gpu_metrics_by_node[node].append(gpu)

        # 메트릭 조회
        result = []
        try:
            metrics = custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )

            for item in metrics.get("items", []):
                name = item["metadata"]["name"]
                usage = item.get("usage", {})

                cpu_usage = parse_cpu(usage.get("cpu", "0"))
                memory_usage = parse_memory(usage.get("memory", "0"))

                info = node_info.get(name, {})
                cpu_capacity = info.get("cpu_capacity", 1)
                memory_capacity = info.get("memory_capacity", 1)
                gpu_capacity = info.get("gpu_capacity", 0)
                gpu_type = info.get("gpu_type", "")

                req = node_requests.get(name, {"cpu": 0, "memory": 0, "gpu": 0})
                lim = node_limits.get(name, {"cpu": 0, "memory": 0, "gpu": 0})
                gpu_used = node_gpu_usage.get(name, 0)

                # 실제 GPU 사용 상태 배열 생성
                gpu_status_array = [actual_gpu_usage.get(i, False) for i in range(gpu_capacity)]

                # GPU 상세 메트릭 추가
                gpu_details = []
                if gpu_capacity > 0:
                    node_gpus = gpu_metrics_by_node.get(name, [])
                    if node_gpus:
                        for gpu_metric in node_gpus:
                            gpu_index = gpu_metric.get('index', 0)
                            gpu_details.append({
                                'index': gpu_index,
                                'name': gpu_metric.get('name', gpu_type),
                                'memory_used': gpu_metric.get('memory_used', 0),
                                'memory_total': gpu_metric.get('memory_total', 0),
                                'memory_percent': round(gpu_metric.get('memory_used', 0) / gpu_metric.get('memory_total', 1) * 100, 1) if gpu_metric.get('memory_total', 0) > 0 else 0,
                                'utilization_percent': gpu_metric.get('utilization', 0),
                                'in_use': actual_gpu_usage.get(gpu_index, False)
                            })

                result.append({
                    "name": name,
                    "cpu_usage": round(cpu_usage, 1),
                    "cpu_capacity": round(cpu_capacity, 1),
                    "cpu_percent": round(cpu_usage / cpu_capacity * 100, 1) if cpu_capacity > 0 else 0,
                    "cpu_requests": round(req["cpu"], 1),
                    "cpu_limits": round(lim["cpu"], 1),
                    "cpu_requests_percent": round(req["cpu"] / cpu_capacity * 100, 1) if cpu_capacity > 0 else 0,
                    "memory_usage": memory_usage,
                    "memory_capacity": memory_capacity,
                    "memory_percent": round(memory_usage / memory_capacity * 100, 1) if memory_capacity > 0 else 0,
                    "memory_requests": req["memory"],
                    "memory_limits": lim["memory"],
                    "memory_requests_percent": round(req["memory"] / memory_capacity * 100, 1) if memory_capacity > 0 else 0,
                    "gpu_capacity": gpu_capacity,
                    "gpu_used": gpu_used,
                    "gpu_status_array": gpu_status_array,
                    "gpu_details": gpu_details,
                    "gpu_type": gpu_type,
                    "gpu_pod_list": node_pod_gpu_list.get(name, []),
                    "timestamp": item.get("timestamp")
                })
        except ApiException as e:
            # metrics-server가 없는 경우
            for name, info in node_info.items():
                req = node_requests.get(name, {"cpu": 0, "memory": 0, "gpu": 0})
                lim = node_limits.get(name, {"cpu": 0, "memory": 0, "gpu": 0})
                gpu_used = node_gpu_usage.get(name, 0)
                cpu_capacity = info.get("cpu_capacity", 0)
                memory_capacity = info.get("memory_capacity", 0)
                gpu_capacity = info.get("gpu_capacity", 0)

                # 실제 GPU 사용 상태 배열 생성
                gpu_status_array = [actual_gpu_usage.get(i, False) for i in range(gpu_capacity)]

                # GPU 상세 메트릭 추가
                gpu_details = []
                if gpu_capacity > 0:
                    node_gpus = gpu_metrics_by_node.get(name, [])
                    if node_gpus:
                        for gpu_metric in node_gpus:
                            gpu_index = gpu_metric.get('index', 0)
                            gpu_details.append({
                                'index': gpu_index,
                                'name': gpu_metric.get('name', info.get("gpu_type", "")),
                                'memory_used': gpu_metric.get('memory_used', 0),
                                'memory_total': gpu_metric.get('memory_total', 0),
                                'memory_percent': round(gpu_metric.get('memory_used', 0) / gpu_metric.get('memory_total', 1) * 100, 1) if gpu_metric.get('memory_total', 0) > 0 else 0,
                                'utilization_percent': gpu_metric.get('utilization', 0),
                                'in_use': actual_gpu_usage.get(gpu_index, False)
                            })

                result.append({
                    "name": name,
                    "cpu_usage": 0,
                    "cpu_capacity": cpu_capacity,
                    "cpu_percent": 0,
                    "cpu_requests": round(req["cpu"], 1),
                    "cpu_limits": round(lim["cpu"], 1),
                    "cpu_requests_percent": round(req["cpu"] / cpu_capacity * 100, 1) if cpu_capacity > 0 else 0,
                    "memory_usage": 0,
                    "memory_capacity": memory_capacity,
                    "memory_percent": 0,
                    "memory_requests": req["memory"],
                    "memory_limits": lim["memory"],
                    "memory_requests_percent": round(req["memory"] / memory_capacity * 100, 1) if memory_capacity > 0 else 0,
                    "gpu_capacity": gpu_capacity,
                    "gpu_used": gpu_used,
                    "gpu_status_array": gpu_status_array,
                    "gpu_details": gpu_details,
                    "gpu_type": info.get("gpu_type", ""),
                    "gpu_pod_list": node_pod_gpu_list.get(name, []),
                    "message": "metrics-server not available"
                })

        return {"nodes": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 노드 조인 및 관리
# ============================================

@router.get("/cluster/join-command")
async def get_join_command():
    """새 노드 조인을 위한 명령어 생성"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # 마스터 노드 IP 가져오기
        nodes = core_v1.list_node()
        master_ip = None
        for node in nodes.items:
            labels = node.metadata.labels or {}
            if "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels:
                for addr in node.status.addresses:
                    if addr.type == "InternalIP":
                        master_ip = addr.address
                        break
                break

        if not master_ip:
            if nodes.items:
                for addr in nodes.items[0].status.addresses:
                    if addr.type == "InternalIP":
                        master_ip = addr.address
                        break

        return {
            "master_ip": master_ip,
            "instructions": {
                "worker": f"""# 워커 노드에서 실행:
# 1. K3s 설치 스크립트 다운로드
curl -sfL https://get.k3s.io | K3S_URL=https://{master_ip}:6443 K3S_TOKEN=<NODE_TOKEN> sh -

# NODE_TOKEN은 마스터 노드에서 확인:
# sudo cat /var/lib/rancher/k3s/server/node-token""",
                "master": f"""# 추가 마스터 노드 (HA 구성):
curl -sfL https://get.k3s.io | K3S_TOKEN=<NODE_TOKEN> sh -s - server --server https://{master_ip}:6443"""
            },
            "note": "NODE_TOKEN은 마스터 노드의 /var/lib/rancher/k3s/server/node-token 파일에서 확인하세요."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster/nodes/{node_name}/cordon")
async def cordon_node(node_name: str):
    """노드 스케줄링 비활성화 (cordon)"""
    try:
        core_v1, _, _ = get_k8s_clients()

        body = {"spec": {"unschedulable": True}}
        core_v1.patch_node(node_name, body)

        return {"message": f"노드 '{node_name}'의 스케줄링이 비활성화되었습니다", "status": "cordoned"}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster/nodes/{node_name}/uncordon")
async def uncordon_node(node_name: str):
    """노드 스케줄링 활성화 (uncordon)"""
    try:
        core_v1, _, _ = get_k8s_clients()

        body = {"spec": {"unschedulable": False}}
        core_v1.patch_node(node_name, body)

        return {"message": f"노드 '{node_name}'의 스케줄링이 활성화되었습니다", "status": "uncordoned"}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster/nodes/{node_name}/drain")
async def drain_node(node_name: str, force: bool = False):
    """노드 드레인 (Pod 퇴거)"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # 먼저 cordon
        body = {"spec": {"unschedulable": True}}
        core_v1.patch_node(node_name, body)

        # 노드의 Pod 목록 (DaemonSet 제외)
        pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")

        evicted = []
        skipped = []

        for pod in pods.items:
            # DaemonSet Pod는 건너뛰기
            if pod.metadata.owner_references:
                is_daemonset = any(ref.kind == "DaemonSet" for ref in pod.metadata.owner_references)
                if is_daemonset:
                    skipped.append(f"{pod.metadata.namespace}/{pod.metadata.name} (DaemonSet)")
                    continue

            # 시스템 네임스페이스의 중요 Pod 건너뛰기
            if pod.metadata.namespace in ["kube-system"] and not force:
                skipped.append(f"{pod.metadata.namespace}/{pod.metadata.name} (system)")
                continue

            try:
                core_v1.delete_namespaced_pod(
                    pod.metadata.name,
                    pod.metadata.namespace,
                    grace_period_seconds=30
                )
                evicted.append(f"{pod.metadata.namespace}/{pod.metadata.name}")
            except ApiException:
                skipped.append(f"{pod.metadata.namespace}/{pod.metadata.name} (삭제 실패)")

        return {
            "message": f"노드 '{node_name}' 드레인 완료",
            "evicted": evicted,
            "skipped": skipped,
            "evicted_count": len(evicted),
            "skipped_count": len(skipped)
        }
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cluster/nodes/{node_name}")
async def delete_node(node_name: str):
    """클러스터에서 노드 제거"""
    try:
        core_v1, _, _ = get_k8s_clients()

        core_v1.delete_node(node_name)

        return {"message": f"노드 '{node_name}'이 클러스터에서 제거되었습니다"}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cluster/nodes/{node_name}/labels")
async def update_node_labels(node_name: str, labels: dict):
    """노드 레이블 업데이트"""
    try:
        core_v1, _, _ = get_k8s_clients()

        body = {"metadata": {"labels": labels}}
        core_v1.patch_node(node_name, body)

        return {"message": f"노드 '{node_name}'의 레이블이 업데이트되었습니다", "labels": labels}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))
