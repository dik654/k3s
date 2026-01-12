"""
Kubernetes 클라이언트 환경 자동 감지 유틸리티

환경에 따라 인증 방식을 자동으로 선택:
- Pod 내부 (KUBERNETES_SERVICE_HOST 존재): ServiceAccount 토큰 사용 (incluster_config)
- 로컬 개발 환경: ~/.kube/config 파일 사용 (kube_config)
"""
import os
import logging
from typing import Tuple, Optional
from functools import lru_cache

from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

# 환경 감지 결과 캐싱
_config_loaded = False
_is_in_cluster: Optional[bool] = None


def is_running_in_cluster() -> bool:
    """현재 코드가 K8s 클러스터 내부(Pod)에서 실행 중인지 확인

    Returns:
        bool: 클러스터 내부면 True, 로컬이면 False
    """
    return os.environ.get('KUBERNETES_SERVICE_HOST') is not None


def _load_k8s_config() -> bool:
    """K8s 설정 로드 (환경 자동 감지)

    Returns:
        bool: 클러스터 내부 config 사용 시 True, kube_config 사용 시 False
    """
    global _config_loaded, _is_in_cluster

    if _config_loaded:
        return _is_in_cluster

    if is_running_in_cluster():
        try:
            config.load_incluster_config()
            _is_in_cluster = True
            _config_loaded = True
            logger.info("K8s config loaded: in-cluster (ServiceAccount)")
            return True
        except config.ConfigException as e:
            logger.warning(f"In-cluster config failed: {e}, falling back to kubeconfig")

    # 로컬 환경 또는 in-cluster 실패 시
    try:
        config.load_kube_config()
        _is_in_cluster = False
        _config_loaded = True
        logger.info("K8s config loaded: kubeconfig (~/.kube/config)")
        return False
    except config.ConfigException as e:
        logger.error(f"Failed to load any K8s config: {e}")
        raise RuntimeError(
            "K8s 설정을 로드할 수 없습니다. "
            "클러스터 내부가 아니라면 ~/.kube/config 파일이 있는지 확인하세요."
        ) from e


def get_k8s_clients() -> Tuple[client.CoreV1Api, client.AppsV1Api, client.CustomObjectsApi]:
    """Kubernetes API 클라이언트 초기화 및 반환

    환경 자동 감지:
    - KUBERNETES_SERVICE_HOST 환경변수가 있으면 → incluster_config (Pod 내부)
    - 없으면 → kubeconfig 파일 사용 (로컬 개발)

    Returns:
        tuple: (CoreV1Api, AppsV1Api, CustomObjectsApi)
        - CoreV1Api: Pod, Service, Node, ConfigMap 등 핵심 리소스
        - AppsV1Api: Deployment, StatefulSet, DaemonSet 등 워크로드
        - CustomObjectsApi: Fleet CRD, Longhorn 등 커스텀 리소스

    Raises:
        RuntimeError: K8s 설정 로드 실패 시

    Example:
        >>> core_v1, apps_v1, custom = get_k8s_clients()
        >>> pods = core_v1.list_namespaced_pod("default")
        >>> deployments = apps_v1.list_namespaced_deployment("default")
    """
    _load_k8s_config()

    return (
        client.CoreV1Api(),
        client.AppsV1Api(),
        client.CustomObjectsApi()
    )


def get_core_v1_api() -> client.CoreV1Api:
    """CoreV1Api만 필요할 때 사용"""
    _load_k8s_config()
    return client.CoreV1Api()


def get_apps_v1_api() -> client.AppsV1Api:
    """AppsV1Api만 필요할 때 사용"""
    _load_k8s_config()
    return client.AppsV1Api()


def get_custom_objects_api() -> client.CustomObjectsApi:
    """CustomObjectsApi만 필요할 때 사용 (Fleet CRD 등)"""
    _load_k8s_config()
    return client.CustomObjectsApi()


def get_environment_info() -> dict:
    """현재 K8s 연결 환경 정보 반환

    Returns:
        dict: 환경 정보
            - environment: "in-cluster" 또는 "local"
            - config_source: 사용된 설정 소스
            - kubernetes_host: API 서버 주소 (in-cluster인 경우)
    """
    env_info = {
        "environment": "in-cluster" if is_running_in_cluster() else "local",
        "config_source": "ServiceAccount token" if is_running_in_cluster() else "~/.kube/config",
    }

    if is_running_in_cluster():
        env_info["kubernetes_host"] = os.environ.get('KUBERNETES_SERVICE_HOST')
        env_info["kubernetes_port"] = os.environ.get('KUBERNETES_SERVICE_PORT')

    return env_info


# 편의를 위한 re-export
__all__ = [
    'get_k8s_clients',
    'get_core_v1_api',
    'get_apps_v1_api',
    'get_custom_objects_api',
    'is_running_in_cluster',
    'get_environment_info',
    'ApiException'
]
