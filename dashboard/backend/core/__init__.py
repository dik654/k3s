# Core module - configuration, database, dependencies
from .config import settings
from .kubernetes import get_k8s_clients

# 환경 자동 감지 K8s 클라이언트 (로컬 개발 지원)
from utils.k8s_client import (
    is_running_in_cluster,
    get_environment_info,
)

__all__ = [
    'settings',
    'get_k8s_clients',
    'is_running_in_cluster',
    'get_environment_info',
]
