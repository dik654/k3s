"""
Kubernetes 클라이언트 및 헬퍼 함수
"""
from kubernetes import client, config
from kubernetes.client.rest import ApiException

def get_k8s_clients():
    """Kubernetes API 클라이언트 초기화"""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    return client.CoreV1Api(), client.AppsV1Api(), client.CustomObjectsApi()


def parse_cpu(cpu_str: str) -> float:
    """CPU 문자열을 밀리코어로 변환"""
    if not cpu_str:
        return 0
    if cpu_str.endswith('n'):
        return float(cpu_str[:-1]) / 1000000
    if cpu_str.endswith('u'):
        return float(cpu_str[:-1]) / 1000
    if cpu_str.endswith('m'):
        return float(cpu_str[:-1])
    return float(cpu_str) * 1000


def parse_memory(mem_str: str) -> int:
    """메모리 문자열을 MB로 변환"""
    if not mem_str:
        return 0
    if mem_str.endswith('Ki'):
        return int(float(mem_str[:-2]) / 1024)
    if mem_str.endswith('Mi'):
        return int(float(mem_str[:-2]))
    if mem_str.endswith('Gi'):
        return int(float(mem_str[:-2]) * 1024)
    if mem_str.endswith('Ti'):
        return int(float(mem_str[:-2]) * 1024 * 1024)
    if mem_str.endswith('K'):
        return int(float(mem_str[:-1]) / 1024)
    if mem_str.endswith('M'):
        return int(float(mem_str[:-1]))
    if mem_str.endswith('G'):
        return int(float(mem_str[:-1]) * 1024)
    return int(float(mem_str) / (1024 * 1024))


def get_node_gpu_info(core_v1) -> dict:
    """노드별 GPU 정보 조회"""
    nodes = core_v1.list_node()
    gpu_info = {}

    for node in nodes.items:
        node_name = node.metadata.name
        capacity = node.status.capacity or {}
        labels = node.metadata.labels or {}

        gpu_count = int(capacity.get("nvidia.com/gpu", "0"))
        if gpu_count > 0:
            gpu_type = labels.get("nvidia.com/gpu.product",
                       labels.get("gpu-type", "NVIDIA GPU"))
            gpu_info[node_name] = {
                "gpu_count": gpu_count,
                "gpu_type": gpu_type
            }

    return gpu_info
