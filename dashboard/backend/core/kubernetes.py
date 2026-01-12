"""
Kubernetes client initialization and utilities

환경 자동 감지:
- KUBERNETES_SERVICE_HOST 환경변수가 있으면 → incluster_config (Pod 내부)
- 없으면 → kubeconfig 파일 사용 (로컬 개발)
"""
# 새 환경 감지 유틸리티에서 re-export
from utils.k8s_client import (
    get_k8s_clients,
    get_core_v1_api,
    get_apps_v1_api,
    get_custom_objects_api,
    is_running_in_cluster,
    get_environment_info,
    ApiException,
)


__all__ = [
    'get_k8s_clients',
    'get_core_v1_api',
    'get_apps_v1_api',
    'get_custom_objects_api',
    'is_running_in_cluster',
    'get_environment_info',
    'ApiException',
]
