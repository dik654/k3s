"""
LLM Benchmark related Pydantic models
"""
from typing import Optional, List
from pydantic import BaseModel


class BenchmarkConfig(BaseModel):
    """벤치마크 설정"""
    name: str
    model: str = "facebook/opt-125m"
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    num_requests: int = 10
    concurrent_requests: int = 1
    test_prompts: List[str] = [
        "Explain quantum computing in simple terms.",
        "Write a short poem about artificial intelligence.",
        "What are the benefits of renewable energy?",
        "Describe the process of photosynthesis.",
        "How does machine learning work?"
    ]
    # vLLM 런타임 파라미터
    gpu_memory_utilization: Optional[float] = None  # 0.1 ~ 0.95
    quantization: Optional[str] = None  # awq, gptq, squeezellm, None
    tensor_parallel_size: Optional[int] = None  # 1, 2, 4, 8
    max_model_len: Optional[int] = None  # 컨텍스트 길이
    dtype: Optional[str] = None  # auto, float16, bfloat16, float32
    enforce_eager: Optional[bool] = None  # Eager 모드 강제


class BenchmarkRun(BaseModel):
    """벤치마크 실행"""
    config_id: str
    custom_prompts: Optional[List[str]] = None


class AutoRangeBenchmark(BaseModel):
    """자동 범위 벤치마크 설정"""
    name: str
    model: str = "facebook/opt-125m"
    # 범위 설정 (min, max, step)
    max_tokens_range: Optional[List[int]] = None  # [min, max, step] e.g. [32, 512, 64]
    concurrent_range: Optional[List[int]] = None  # [min, max, step] e.g. [1, 8, 1]
    temperature_range: Optional[List[float]] = None  # [min, max, step] e.g. [0.1, 1.0, 0.3]
    batch_size_range: Optional[List[int]] = None  # [min, max, step] e.g. [1, 32, 4]
    # 고정 파라미터
    num_requests: int = 10
    test_prompts: List[str] = [
        "Explain quantum computing in simple terms.",
        "Write a short poem about artificial intelligence.",
        "What are the benefits of renewable energy?"
    ]


class FullBenchmarkCycle(BaseModel):
    """전체 벤치마크 사이클 설정 (모델 배포 -> 벤치마크 -> 분석)"""
    name: str
    model: str  # HuggingFace 모델 ID
    # vLLM 배포 파라미터
    gpu_memory_utilization: float = 0.9
    max_model_len: Optional[int] = None
    quantization: Optional[str] = None  # awq, gptq, squeezellm
    tensor_parallel_size: int = 1
    dtype: str = "auto"  # auto, float16, bfloat16
    enforce_eager: bool = False
    # 벤치마크 파라미터 범위
    max_tokens_range: List[int] = [64, 256, 512]
    concurrent_range: List[int] = [1, 2, 4]
    num_requests_per_test: int = 10
    # 품질 평가용 프롬프트
    quality_prompts: List[str] = [
        "Explain the theory of relativity in simple terms.",
        "Write a short story about a robot learning to paint.",
        "What are the main causes of climate change?",
        "Describe the process of photosynthesis step by step.",
        "Compare and contrast machine learning and deep learning."
    ]
