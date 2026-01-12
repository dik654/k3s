"""
Utility helper functions
"""
import re


def format_size(size_bytes: int) -> str:
    """바이트를 읽기 쉬운 형태로 변환"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def parse_resource(resource_str: str) -> float:
    """Kubernetes 리소스 문자열을 숫자로 변환"""
    if not resource_str:
        return 0.0

    resource_str = str(resource_str).strip()

    # CPU: millicores (예: "500m" -> 0.5)
    if resource_str.endswith('m'):
        return float(resource_str[:-1]) / 1000

    # Memory: Ki, Mi, Gi, Ti
    units = {
        'Ki': 1024,
        'Mi': 1024 ** 2,
        'Gi': 1024 ** 3,
        'Ti': 1024 ** 4,
        'K': 1000,
        'M': 1000 ** 2,
        'G': 1000 ** 3,
        'T': 1000 ** 4,
    }

    for unit, multiplier in units.items():
        if resource_str.endswith(unit):
            return float(resource_str[:-len(unit)]) * multiplier

    # 단위 없으면 그대로 반환
    try:
        return float(resource_str)
    except ValueError:
        return 0.0
