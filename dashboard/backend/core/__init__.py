# Core module - configuration, database, dependencies
from .config import settings
from .kubernetes import get_k8s_clients

__all__ = ['settings', 'get_k8s_clients']
