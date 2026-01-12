"""
Kubernetes client initialization and utilities
"""
from kubernetes import client, config
from kubernetes.client.rest import ApiException


def get_k8s_clients():
    """Kubernetes API 클라이언트 초기화 및 반환

    클러스터 내부에서 실행 중이면 in-cluster config 사용,
    아니면 kubeconfig 파일 사용

    Returns:
        tuple: (CoreV1Api, AppsV1Api, CustomObjectsApi)
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    return client.CoreV1Api(), client.AppsV1Api(), client.CustomObjectsApi()


__all__ = ['get_k8s_clients', 'ApiException']
