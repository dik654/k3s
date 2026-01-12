"""
모니터링 라우터
- gpu: GPU 모니터링
- benchmark: LLM 벤치마크
- health: 헬스체크
"""
from .gpu import router as gpu_router
from .benchmark import router as benchmark_router
from .health import router as health_router

__all__ = [
    "gpu_router",
    "benchmark_router",
    "health_router"
]
