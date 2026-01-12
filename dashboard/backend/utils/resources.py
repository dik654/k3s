"""
Kubernetes 리소스 단위 변환 유틸리티
CPU와 메모리 문자열을 표준 단위로 변환
"""


def parse_cpu(cpu_str: str) -> float:
    """CPU 문자열을 밀리코어(millicores)로 변환

    지원되는 형식:
    - '100m' -> 100 (millicores)
    - '2' -> 2000 (millicores)
    - '500u' -> 0.5 (microcores)
    - '1000n' -> 0.001 (nanocores)

    Args:
        cpu_str: CPU 리소스 문자열 (e.g., '100m', '2', '500u')

    Returns:
        float: 밀리코어 단위의 CPU 값
    """
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
    """메모리 문자열을 MB로 변환

    지원되는 형식:
    - '512Mi' -> 512 (MB)
    - '1Gi' -> 1024 (MB)
    - '256K' -> 0 (KB)
    - '1G' -> 1024 (MB)

    Args:
        mem_str: 메모리 리소스 문자열 (e.g., '512Mi', '1Gi')

    Returns:
        int: MB 단위의 메모리 값
    """
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


__all__ = ["parse_cpu", "parse_memory"]
