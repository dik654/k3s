"""
LLM Benchmark API
벤치마크 설정, 실행, 결과 조회, 자동 범위 테스트, 전체 사이클 관리
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import asyncio
import time
import httpx

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

# ============================================
# In-memory Storage (실제로는 DB 사용 권장)
# ============================================
benchmark_results: Dict[str, Any] = {}
benchmark_configs: Dict[str, Any] = {}
auto_benchmark_sessions: Dict[str, Any] = {}
full_cycle_sessions: Dict[str, Any] = {}


# ============================================
# Pydantic Models
# ============================================
class BenchmarkConfig(BaseModel):
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
    # vLLM 파라미터
    gpu_memory_utilization: Optional[float] = None
    quantization: Optional[str] = None


class FullBenchmarkCycle(BaseModel):
    """전체 벤치마크 사이클 설정"""
    name: str
    model: str  # HuggingFace 모델 ID (예: facebook/opt-125m, meta-llama/Llama-2-7b-hf)
    # vLLM 배포 파라미터
    gpu_memory_utilization: float = 0.9
    max_model_len: Optional[int] = None
    quantization: Optional[str] = None  # awq, gptq, squeezellm
    tensor_parallel_size: int = 1
    dtype: str = "auto"  # auto, float16, bfloat16
    enforce_eager: bool = False
    # 벤치마크 파라미터 범위
    max_tokens_range: List[int] = [64, 256, 512]  # 테스트할 max_tokens 값들
    concurrent_range: List[int] = [1, 2, 4]  # 테스트할 동시성 값들
    num_requests_per_test: int = 10
    # 품질 평가용 프롬프트
    quality_prompts: List[str] = [
        "Explain the theory of relativity in simple terms.",
        "Write a short story about a robot learning to paint.",
        "What are the main causes of climate change?",
        "Describe the process of photosynthesis step by step.",
        "Compare and contrast machine learning and deep learning."
    ]


# 일반적인 파라미터 범위 기본값
DEFAULT_RANGES = {
    "max_tokens": {"min": 32, "max": 512, "step": 64, "default": [32, 128, 256, 512]},
    "concurrent_requests": {"min": 1, "max": 16, "step": 2, "default": [1, 2, 4, 8, 16]},
    "temperature": {"min": 0.1, "max": 1.0, "step": 0.3, "default": [0.1, 0.4, 0.7, 1.0]},
    "batch_size": {"min": 1, "max": 32, "step": 4, "default": [1, 4, 8, 16, 32]},
    "gpu_memory_utilization": {"min": 0.5, "max": 0.95, "step": 0.15, "default": [0.5, 0.7, 0.85, 0.95]},
}

# vLLM 서비스 엔드포인트
VLLM_ENDPOINT = "http://vllm-server.ai-workloads.svc.cluster.local:8000"


# ============================================
# Helper Functions
# ============================================
def get_k8s_clients():
    """Kubernetes 클라이언트 초기화"""
    from kubernetes import client, config
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api(), client.AppsV1Api(), client.CustomObjectsApi()


def add_log(session: dict, message: str, level: str = "info"):
    """세션에 로그 추가"""
    session["logs"].append({
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message
    })


async def run_single_request(client: httpx.AsyncClient, endpoint: str, prompt: str,
                             model: str, max_tokens: int, temperature: float, top_p: float):
    """단일 추론 요청 실행"""
    start_time = time.time()
    error = None
    output_tokens = 0
    response_text = ""

    try:
        # vLLM OpenAI-compatible API 호출
        response = await client.post(
            f"{endpoint}/v1/completions",
            json={
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            },
            timeout=120.0
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0].get("text", "")
                output_tokens = data.get("usage", {}).get("completion_tokens", len(response_text.split()))
        else:
            error = f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        error = str(e)

    end_time = time.time()
    latency = end_time - start_time

    return {
        "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
        "response": response_text[:200] + "..." if len(response_text) > 200 else response_text,
        "latency": round(latency, 3),
        "output_tokens": output_tokens,
        "tokens_per_second": round(output_tokens / latency, 2) if latency > 0 and output_tokens > 0 else 0,
        "success": error is None,
        "error": error
    }


# ============================================
# Benchmark Config Endpoints
# ============================================
@router.get("/configs")
async def list_benchmark_configs():
    """저장된 벤치마크 설정 목록"""
    configs = []
    for config_id, config in benchmark_configs.items():
        configs.append({
            "id": config_id,
            **config,
            "created_at": config.get("created_at")
        })
    return {"configs": configs, "total": len(configs)}


@router.post("/configs")
async def create_benchmark_config(config: BenchmarkConfig):
    """벤치마크 설정 생성"""
    config_id = str(uuid.uuid4())[:8]
    benchmark_configs[config_id] = {
        "name": config.name,
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "num_requests": config.num_requests,
        "concurrent_requests": config.concurrent_requests,
        "test_prompts": config.test_prompts,
        # vLLM 런타임 파라미터
        "gpu_memory_utilization": config.gpu_memory_utilization,
        "quantization": config.quantization,
        "tensor_parallel_size": config.tensor_parallel_size,
        "max_model_len": config.max_model_len,
        "dtype": config.dtype,
        "enforce_eager": config.enforce_eager,
        "created_at": datetime.now().isoformat()
    }
    return {"id": config_id, "message": f"벤치마크 설정 '{config.name}'이 생성되었습니다"}


@router.delete("/configs/{config_id}")
async def delete_benchmark_config(config_id: str):
    """벤치마크 설정 삭제"""
    if config_id not in benchmark_configs:
        raise HTTPException(status_code=404, detail="설정을 찾을 수 없습니다")
    del benchmark_configs[config_id]
    return {"success": True, "message": "설정이 삭제되었습니다"}


# ============================================
# Benchmark Results Endpoints
# ============================================
@router.get("/results")
async def list_benchmark_results():
    """벤치마크 결과 목록"""
    results = []
    for result_id, result in benchmark_results.items():
        results.append({
            "id": result_id,
            "config_name": result.get("config_name"),
            "model": result.get("model"),
            "status": result.get("status"),
            "started_at": result.get("started_at"),
            "completed_at": result.get("completed_at"),
            "summary": result.get("summary")
        })
    # 최신 순으로 정렬
    results.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return {"results": results, "total": len(results)}


@router.get("/results/{result_id}")
async def get_benchmark_result(result_id: str):
    """벤치마크 결과 상세 조회"""
    if result_id not in benchmark_results:
        raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
    return benchmark_results[result_id]


@router.delete("/results/{result_id}")
async def delete_benchmark_result(result_id: str):
    """벤치마크 결과 삭제"""
    if result_id not in benchmark_results:
        raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
    del benchmark_results[result_id]
    return {"success": True, "message": "결과가 삭제되었습니다"}


# ============================================
# Benchmark Run Endpoint
# ============================================
@router.post("/run")
async def run_benchmark(run_config: BenchmarkRun):
    """벤치마크 실행"""
    if run_config.config_id not in benchmark_configs:
        raise HTTPException(status_code=404, detail="설정을 찾을 수 없습니다")

    config = benchmark_configs[run_config.config_id]
    result_id = str(uuid.uuid4())[:8]

    # 결과 초기화
    benchmark_results[result_id] = {
        "id": result_id,
        "config_id": run_config.config_id,
        "config_name": config["name"],
        "model": config["model"],
        "settings": {
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"],
            "top_p": config["top_p"],
            "num_requests": config["num_requests"],
            "concurrent_requests": config["concurrent_requests"]
        },
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "requests": [],
        "summary": None
    }

    # 테스트 프롬프트
    prompts = run_config.custom_prompts or config["test_prompts"]

    # 벤치마크 실행
    all_results = []
    try:
        async with httpx.AsyncClient() as client:
            # 먼저 vLLM 서비스 상태 확인
            try:
                health_check = await client.get(f"{VLLM_ENDPOINT}/health", timeout=10.0)
                if health_check.status_code != 200:
                    raise Exception("vLLM service not healthy")
            except Exception as e:
                benchmark_results[result_id]["status"] = "failed"
                benchmark_results[result_id]["error"] = f"vLLM 서비스에 연결할 수 없습니다: {str(e)}"
                benchmark_results[result_id]["completed_at"] = datetime.now().isoformat()
                return {"result_id": result_id, "status": "failed", "error": str(e)}

            # 요청 실행
            for i in range(config["num_requests"]):
                prompt = prompts[i % len(prompts)]

                if config["concurrent_requests"] > 1:
                    # 동시 요청
                    tasks = [
                        run_single_request(
                            client, VLLM_ENDPOINT, prompt,
                            config["model"], config["max_tokens"],
                            config["temperature"], config["top_p"]
                        )
                        for _ in range(min(config["concurrent_requests"], config["num_requests"] - i))
                    ]
                    results = await asyncio.gather(*tasks)
                    all_results.extend(results)
                    i += len(tasks) - 1
                else:
                    # 순차 요청
                    result = await run_single_request(
                        client, VLLM_ENDPOINT, prompt,
                        config["model"], config["max_tokens"],
                        config["temperature"], config["top_p"]
                    )
                    all_results.append(result)

        # 결과 요약
        successful = [r for r in all_results if r["success"]]
        failed = [r for r in all_results if not r["success"]]

        if successful:
            latencies = [r["latency"] for r in successful]
            tokens_per_sec = [r["tokens_per_second"] for r in successful if r["tokens_per_second"] > 0]

            summary = {
                "total_requests": len(all_results),
                "successful_requests": len(successful),
                "failed_requests": len(failed),
                "success_rate": round(len(successful) / len(all_results) * 100, 1),
                "avg_latency": round(sum(latencies) / len(latencies), 3),
                "min_latency": round(min(latencies), 3),
                "max_latency": round(max(latencies), 3),
                "p50_latency": round(sorted(latencies)[len(latencies)//2], 3),
                "p95_latency": round(sorted(latencies)[int(len(latencies)*0.95)], 3) if len(latencies) >= 20 else None,
                "avg_tokens_per_second": round(sum(tokens_per_sec) / len(tokens_per_sec), 2) if tokens_per_sec else 0,
                "total_output_tokens": sum(r["output_tokens"] for r in successful)
            }
        else:
            summary = {
                "total_requests": len(all_results),
                "successful_requests": 0,
                "failed_requests": len(failed),
                "success_rate": 0,
                "error": "모든 요청이 실패했습니다"
            }

        benchmark_results[result_id]["requests"] = all_results
        benchmark_results[result_id]["summary"] = summary
        benchmark_results[result_id]["status"] = "completed"
        benchmark_results[result_id]["completed_at"] = datetime.now().isoformat()

        return {
            "result_id": result_id,
            "status": "completed",
            "summary": summary
        }

    except Exception as e:
        benchmark_results[result_id]["status"] = "failed"
        benchmark_results[result_id]["error"] = str(e)
        benchmark_results[result_id]["completed_at"] = datetime.now().isoformat()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Compare Benchmark Results
# ============================================
@router.get("/compare")
async def compare_benchmark_results(result_ids: str):
    """여러 벤치마크 결과 비교"""
    ids = result_ids.split(",")
    comparison = []

    for result_id in ids:
        result_id = result_id.strip()
        if result_id in benchmark_results:
            result = benchmark_results[result_id]
            comparison.append({
                "id": result_id,
                "config_name": result.get("config_name"),
                "model": result.get("model"),
                "settings": result.get("settings"),
                "summary": result.get("summary"),
                "completed_at": result.get("completed_at")
            })

    return {"comparison": comparison, "total": len(comparison)}


# ============================================
# Default Ranges
# ============================================
@router.get("/default-ranges")
async def get_default_ranges():
    """자동 범위 벤치마크를 위한 기본 범위값 조회"""
    return {"ranges": DEFAULT_RANGES}


# ============================================
# Auto-Range Benchmark Endpoints
# ============================================
@router.post("/auto-range")
async def run_auto_range_benchmark(config: AutoRangeBenchmark, background_tasks: BackgroundTasks):
    """자동 범위 벤치마크 실행 - 파라미터 범위를 자동으로 순회하며 테스트"""
    session_id = str(uuid.uuid4())[:8]

    # 범위 값 생성
    def generate_range(range_config, default_key):
        if range_config and len(range_config) >= 3:
            min_val, max_val, step = range_config[0], range_config[1], range_config[2]
            values = []
            current = min_val
            while current <= max_val:
                values.append(current)
                current += step
            return values
        return DEFAULT_RANGES[default_key]["default"]

    # 테스트할 파라미터 조합 생성
    max_tokens_values = generate_range(config.max_tokens_range, "max_tokens") if config.max_tokens_range else [128]
    concurrent_values = generate_range(config.concurrent_range, "concurrent_requests") if config.concurrent_range else [1]
    temperature_values = generate_range(config.temperature_range, "temperature") if config.temperature_range else [0.7]

    # 테스트 조합 생성 (모든 조합 또는 주요 조합만)
    test_combinations = []

    # 각 파라미터별 변화 테스트 (다른 파라미터는 기본값 유지)
    base_max_tokens = max_tokens_values[len(max_tokens_values)//2] if max_tokens_values else 128
    base_concurrent = concurrent_values[0] if concurrent_values else 1
    base_temperature = temperature_values[len(temperature_values)//2] if temperature_values else 0.7

    # max_tokens 변화 테스트
    for mt in max_tokens_values:
        test_combinations.append({
            "max_tokens": mt,
            "concurrent_requests": base_concurrent,
            "temperature": base_temperature,
            "test_type": "max_tokens"
        })

    # concurrent_requests 변화 테스트
    for cr in concurrent_values:
        if cr == base_concurrent:
            continue
        test_combinations.append({
            "max_tokens": base_max_tokens,
            "concurrent_requests": cr,
            "temperature": base_temperature,
            "test_type": "concurrent"
        })

    # temperature 변화 테스트
    for temp in temperature_values:
        if abs(temp - base_temperature) < 0.01:
            continue
        test_combinations.append({
            "max_tokens": base_max_tokens,
            "concurrent_requests": base_concurrent,
            "temperature": temp,
            "test_type": "temperature"
        })

    # 세션 초기화
    auto_benchmark_sessions[session_id] = {
        "id": session_id,
        "name": config.name,
        "model": config.model,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "total_tests": len(test_combinations),
        "completed_tests": 0,
        "current_test": None,
        "test_combinations": test_combinations,
        "results": [],
        "vllm_params": {
            "gpu_memory_utilization": config.gpu_memory_utilization,
            "quantization": config.quantization
        }
    }

    # 백그라운드에서 실행
    background_tasks.add_task(execute_auto_range_benchmark, session_id, config)

    return {
        "session_id": session_id,
        "status": "started",
        "total_tests": len(test_combinations),
        "message": f"자동 범위 벤치마크가 시작되었습니다. {len(test_combinations)}개의 테스트를 실행합니다."
    }


async def execute_auto_range_benchmark(session_id: str, config: AutoRangeBenchmark):
    """자동 범위 벤치마크 실행 (백그라운드)"""
    session = auto_benchmark_sessions.get(session_id)
    if not session:
        return

    async with httpx.AsyncClient() as client:
        # vLLM 상태 확인
        try:
            health_check = await client.get(f"{VLLM_ENDPOINT}/health", timeout=10.0)
            if health_check.status_code != 200:
                session["status"] = "failed"
                session["error"] = "vLLM 서비스가 응답하지 않습니다"
                session["completed_at"] = datetime.now().isoformat()
                return
        except Exception as e:
            session["status"] = "failed"
            session["error"] = f"vLLM 연결 실패: {str(e)}"
            session["completed_at"] = datetime.now().isoformat()
            return

        # 각 테스트 조합 실행
        for i, combo in enumerate(session["test_combinations"]):
            session["current_test"] = combo
            session["completed_tests"] = i

            test_result = {
                "params": combo,
                "started_at": datetime.now().isoformat(),
                "requests": [],
                "summary": None
            }

            all_results = []
            try:
                for j in range(config.num_requests):
                    prompt = config.test_prompts[j % len(config.test_prompts)]

                    start_time = time.time()
                    try:
                        response = await client.post(
                            f"{VLLM_ENDPOINT}/v1/completions",
                            json={
                                "model": config.model,
                                "prompt": prompt,
                                "max_tokens": combo["max_tokens"],
                                "temperature": combo["temperature"],
                                "top_p": 0.9
                            },
                            timeout=120.0
                        )

                        end_time = time.time()
                        latency = end_time - start_time

                        if response.status_code == 200:
                            data = response.json()
                            output_tokens = data.get("usage", {}).get("completion_tokens", 0)
                            all_results.append({
                                "latency": latency,
                                "output_tokens": output_tokens,
                                "tokens_per_second": output_tokens / latency if latency > 0 else 0,
                                "success": True
                            })
                        else:
                            all_results.append({
                                "latency": latency,
                                "success": False,
                                "error": f"HTTP {response.status_code}"
                            })
                    except Exception as e:
                        all_results.append({
                            "latency": time.time() - start_time,
                            "success": False,
                            "error": str(e)
                        })

                # 결과 요약
                successful = [r for r in all_results if r.get("success")]
                if successful:
                    latencies = [r["latency"] for r in successful]
                    tokens_per_sec = [r["tokens_per_second"] for r in successful if r.get("tokens_per_second", 0) > 0]

                    test_result["summary"] = {
                        "total_requests": len(all_results),
                        "successful_requests": len(successful),
                        "success_rate": round(len(successful) / len(all_results) * 100, 1),
                        "avg_latency": round(sum(latencies) / len(latencies), 3),
                        "min_latency": round(min(latencies), 3),
                        "max_latency": round(max(latencies), 3),
                        "avg_tokens_per_second": round(sum(tokens_per_sec) / len(tokens_per_sec), 2) if tokens_per_sec else 0
                    }
                else:
                    test_result["summary"] = {
                        "total_requests": len(all_results),
                        "successful_requests": 0,
                        "success_rate": 0,
                        "error": "모든 요청 실패"
                    }

                test_result["completed_at"] = datetime.now().isoformat()
                session["results"].append(test_result)

            except Exception as e:
                test_result["error"] = str(e)
                test_result["completed_at"] = datetime.now().isoformat()
                session["results"].append(test_result)

        # 완료
        session["status"] = "completed"
        session["completed_tests"] = len(session["test_combinations"])
        session["current_test"] = None
        session["completed_at"] = datetime.now().isoformat()

        # 최적의 파라미터 찾기
        best_result = None
        best_tps = 0
        for result in session["results"]:
            if result.get("summary") and result["summary"].get("avg_tokens_per_second", 0) > best_tps:
                best_tps = result["summary"]["avg_tokens_per_second"]
                best_result = result

        session["best_params"] = best_result["params"] if best_result else None
        session["best_performance"] = best_result["summary"] if best_result else None


@router.get("/auto-range/{session_id}")
async def get_auto_range_status(session_id: str):
    """자동 범위 벤치마크 상태 조회"""
    if session_id not in auto_benchmark_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return auto_benchmark_sessions[session_id]


@router.get("/auto-range")
async def list_auto_range_sessions():
    """자동 범위 벤치마크 세션 목록"""
    sessions = []
    for session_id, session in auto_benchmark_sessions.items():
        sessions.append({
            "id": session_id,
            "name": session.get("name"),
            "model": session.get("model"),
            "status": session.get("status"),
            "total_tests": session.get("total_tests"),
            "completed_tests": session.get("completed_tests"),
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at"),
            "best_params": session.get("best_params"),
            "best_performance": session.get("best_performance")
        })
    sessions.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/auto-range/{session_id}")
async def delete_auto_range_session(session_id: str):
    """자동 범위 벤치마크 세션 삭제"""
    if session_id not in auto_benchmark_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    del auto_benchmark_sessions[session_id]
    return {"success": True, "message": "세션이 삭제되었습니다"}


# ============================================
# Full Benchmark Cycle Endpoints
# ============================================
@router.post("/full-cycle")
async def start_full_benchmark_cycle(config: FullBenchmarkCycle, background_tasks: BackgroundTasks):
    """전체 벤치마크 사이클 시작: 모델 배포 -> 부팅 시간 측정 -> 벤치마크 -> 품질 평가 -> 분석"""
    session_id = str(uuid.uuid4())[:8]

    # 테스트 조합 생성
    test_matrix = []
    for max_tokens in config.max_tokens_range:
        for concurrent in config.concurrent_range:
            test_matrix.append({
                "max_tokens": max_tokens,
                "concurrent_requests": concurrent
            })

    # 세션 초기화
    full_cycle_sessions[session_id] = {
        "id": session_id,
        "name": config.name,
        "model": config.model,
        "status": "initializing",
        "phase": "pending",  # pending, deploying, booting, benchmarking, evaluating, analyzing, completed, failed
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "vllm_config": {
            "gpu_memory_utilization": config.gpu_memory_utilization,
            "max_model_len": config.max_model_len,
            "quantization": config.quantization,
            "tensor_parallel_size": config.tensor_parallel_size,
            "dtype": config.dtype,
            "enforce_eager": config.enforce_eager
        },
        "test_matrix": test_matrix,
        "current_test_index": 0,
        "total_tests": len(test_matrix),
        # 측정값들
        "metrics": {
            "boot_time": None,  # 모델 부팅 시간 (초)
            "model_load_time": None,  # 모델 로딩 시간
            "first_inference_time": None,  # 첫 추론 시간
            "warmup_time": None  # 워밍업 완료 시간
        },
        "benchmark_results": [],  # 각 테스트 조합의 결과
        "quality_results": [],  # 품질 평가 결과
        "analysis": None,  # 최종 분석 결과
        "optimal_config": None,  # 최적 설정
        "logs": []
    }

    # 백그라운드에서 실행
    background_tasks.add_task(execute_full_benchmark_cycle, session_id, config)

    return {
        "session_id": session_id,
        "status": "started",
        "total_tests": len(test_matrix),
        "message": f"전체 벤치마크 사이클이 시작되었습니다. 모델: {config.model}"
    }


async def deploy_vllm_model(session: dict, config: FullBenchmarkCycle) -> bool:
    """vLLM 모델 배포"""
    try:
        from kubernetes.client.rest import ApiException
        core_v1, apps_v1, _ = get_k8s_clients()

        # 기존 vLLM deployment 업데이트
        deployment_name = "vllm-server"
        namespace = "ai-workloads"

        # vLLM 컨테이너 인수 생성
        vllm_args = [
            "--model", config.model,
            "--host", "0.0.0.0",
            "--port", "8000",
            "--gpu-memory-utilization", str(config.gpu_memory_utilization),
            "--dtype", config.dtype,
            "--tensor-parallel-size", str(config.tensor_parallel_size),
        ]

        if config.max_model_len:
            vllm_args.extend(["--max-model-len", str(config.max_model_len)])

        if config.quantization:
            vllm_args.extend(["--quantization", config.quantization])

        if config.enforce_eager:
            vllm_args.append("--enforce-eager")

        # Deployment 패치
        patch_body = {
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "vllm",
                            "args": vllm_args
                        }]
                    }
                }
            }
        }

        try:
            apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=patch_body
            )
            add_log(session, f"vLLM Deployment 업데이트: {config.model}")
        except ApiException as e:
            if e.status == 404:
                add_log(session, "vLLM Deployment가 존재하지 않습니다. 새로 생성합니다.", "warning")
                # 여기서 새 deployment 생성 로직 추가 가능
                return False
            raise

        return True

    except Exception as e:
        add_log(session, f"모델 배포 실패: {str(e)}", "error")
        return False


async def wait_for_vllm_ready(session: dict, timeout: int = 600) -> dict:
    """vLLM 서비스가 준비될 때까지 대기하고 부팅 시간 측정"""
    start_time = time.time()
    boot_phases = {
        "deployment_ready": None,
        "container_ready": None,
        "health_endpoint_ready": None,
        "model_loaded": None,
        "first_inference": None
    }

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time

            # K8s 상태 확인
            try:
                _, apps_v1, _ = get_k8s_clients()
                deployment = apps_v1.read_namespaced_deployment("vllm-server", "ai-workloads")

                if deployment.status.ready_replicas and deployment.status.ready_replicas > 0:
                    if not boot_phases["deployment_ready"]:
                        boot_phases["deployment_ready"] = elapsed
                        add_log(session, f"Deployment 준비 완료: {elapsed:.1f}초")
            except:
                pass

            # Health 엔드포인트 확인
            try:
                health = await client.get(f"{VLLM_ENDPOINT}/health", timeout=5.0)
                if health.status_code == 200:
                    if not boot_phases["health_endpoint_ready"]:
                        boot_phases["health_endpoint_ready"] = elapsed
                        add_log(session, f"Health 엔드포인트 응답: {elapsed:.1f}초")

                    # 모델 로딩 확인
                    try:
                        models = await client.get(f"{VLLM_ENDPOINT}/v1/models", timeout=10.0)
                        if models.status_code == 200:
                            model_data = models.json()
                            if model_data.get("data"):
                                if not boot_phases["model_loaded"]:
                                    boot_phases["model_loaded"] = elapsed
                                    add_log(session, f"모델 로딩 완료: {elapsed:.1f}초")

                                # 첫 추론 테스트
                                if not boot_phases["first_inference"]:
                                    try:
                                        inference_start = time.time()
                                        resp = await client.post(
                                            f"{VLLM_ENDPOINT}/v1/completions",
                                            json={
                                                "model": session["model"],
                                                "prompt": "Hello",
                                                "max_tokens": 5
                                            },
                                            timeout=60.0
                                        )
                                        if resp.status_code == 200:
                                            boot_phases["first_inference"] = elapsed
                                            first_inference_time = time.time() - inference_start
                                            add_log(session, f"첫 추론 완료: {elapsed:.1f}초 (추론 시간: {first_inference_time:.2f}초)")

                                            return {
                                                "success": True,
                                                "total_boot_time": elapsed,
                                                "phases": boot_phases,
                                                "first_inference_latency": first_inference_time
                                            }
                                    except:
                                        pass
                    except:
                        pass
            except:
                pass

            session["phase"] = "booting"
            session["metrics"]["boot_time"] = elapsed
            await asyncio.sleep(5)

    return {
        "success": False,
        "total_boot_time": time.time() - start_time,
        "phases": boot_phases,
        "error": "타임아웃"
    }


async def run_benchmark_test(session: dict, config: FullBenchmarkCycle, test_params: dict) -> dict:
    """단일 벤치마크 테스트 실행"""
    results = []

    async with httpx.AsyncClient() as client:
        for i in range(config.num_requests_per_test):
            prompt = config.quality_prompts[i % len(config.quality_prompts)]

            start_time = time.time()
            try:
                response = await client.post(
                    f"{VLLM_ENDPOINT}/v1/completions",
                    json={
                        "model": config.model,
                        "prompt": prompt,
                        "max_tokens": test_params["max_tokens"],
                        "temperature": 0.7,
                        "top_p": 0.9
                    },
                    timeout=120.0
                )

                latency = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()
                    output_tokens = data.get("usage", {}).get("completion_tokens", 0)
                    response_text = data.get("choices", [{}])[0].get("text", "")

                    results.append({
                        "success": True,
                        "latency": latency,
                        "output_tokens": output_tokens,
                        "tokens_per_second": output_tokens / latency if latency > 0 else 0,
                        "response_length": len(response_text),
                        "prompt": prompt[:50] + "..."
                    })
                else:
                    results.append({
                        "success": False,
                        "latency": latency,
                        "error": f"HTTP {response.status_code}"
                    })
            except Exception as e:
                results.append({
                    "success": False,
                    "latency": time.time() - start_time,
                    "error": str(e)
                })

    # 결과 요약
    successful = [r for r in results if r.get("success")]
    if successful:
        latencies = [r["latency"] for r in successful]
        tps = [r["tokens_per_second"] for r in successful if r.get("tokens_per_second", 0) > 0]

        return {
            "params": test_params,
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "success_rate": round(len(successful) / len(results) * 100, 1),
            "latency": {
                "avg": round(sum(latencies) / len(latencies), 3),
                "min": round(min(latencies), 3),
                "max": round(max(latencies), 3),
                "p50": round(sorted(latencies)[len(latencies)//2], 3),
                "p95": round(sorted(latencies)[int(len(latencies)*0.95)], 3) if len(latencies) >= 20 else None
            },
            "throughput": {
                "avg_tokens_per_second": round(sum(tps) / len(tps), 2) if tps else 0,
                "max_tokens_per_second": round(max(tps), 2) if tps else 0,
                "total_tokens": sum(r.get("output_tokens", 0) for r in successful)
            },
            "raw_results": results
        }
    else:
        return {
            "params": test_params,
            "total_requests": len(results),
            "successful": 0,
            "failed": len(results),
            "success_rate": 0,
            "error": "모든 요청 실패"
        }


async def evaluate_quality(session: dict, config: FullBenchmarkCycle) -> dict:
    """출력 품질 평가"""
    quality_results = []

    # 품질 평가 기준
    quality_prompts = [
        {
            "prompt": "What is 2 + 2?",
            "expected_contains": ["4", "four"],
            "type": "math"
        },
        {
            "prompt": "The capital of France is",
            "expected_contains": ["Paris"],
            "type": "factual"
        },
        {
            "prompt": "Write a haiku about nature.",
            "min_words": 5,
            "type": "creative"
        },
        {
            "prompt": "Explain why the sky is blue in one sentence.",
            "min_words": 10,
            "type": "explanation"
        },
        {
            "prompt": "List three primary colors: ",
            "expected_contains": ["red", "blue", "yellow"],
            "type": "list"
        }
    ]

    async with httpx.AsyncClient() as client:
        for qp in quality_prompts:
            try:
                response = await client.post(
                    f"{VLLM_ENDPOINT}/v1/completions",
                    json={
                        "model": config.model,
                        "prompt": qp["prompt"],
                        "max_tokens": 100,
                        "temperature": 0.3  # 낮은 temperature로 일관된 결과
                    },
                    timeout=60.0
                )

                if response.status_code == 200:
                    data = response.json()
                    text = data.get("choices", [{}])[0].get("text", "").strip().lower()

                    # 품질 점수 계산
                    score = 0
                    if "expected_contains" in qp:
                        for expected in qp["expected_contains"]:
                            if expected.lower() in text:
                                score += 1
                        score = score / len(qp["expected_contains"]) * 100
                    elif "min_words" in qp:
                        word_count = len(text.split())
                        score = min(100, (word_count / qp["min_words"]) * 100)

                    quality_results.append({
                        "type": qp["type"],
                        "prompt": qp["prompt"],
                        "response": text[:200],
                        "score": round(score, 1),
                        "passed": score >= 50
                    })
            except Exception as e:
                quality_results.append({
                    "type": qp["type"],
                    "prompt": qp["prompt"],
                    "error": str(e),
                    "score": 0,
                    "passed": False
                })

    # 품질 요약
    passed = sum(1 for q in quality_results if q.get("passed"))
    avg_score = sum(q.get("score", 0) for q in quality_results) / len(quality_results) if quality_results else 0

    return {
        "tests": quality_results,
        "summary": {
            "total_tests": len(quality_results),
            "passed": passed,
            "failed": len(quality_results) - passed,
            "pass_rate": round(passed / len(quality_results) * 100, 1) if quality_results else 0,
            "avg_score": round(avg_score, 1)
        }
    }


def analyze_results(session: dict) -> dict:
    """결과 분석 및 최적 설정 도출"""
    benchmark_results_data = session.get("benchmark_results", [])
    quality_results = session.get("quality_results", {})

    if not benchmark_results_data:
        return {"error": "벤치마크 결과 없음"}

    # 최적 설정 찾기 (처리량 기준)
    best_throughput = None
    best_latency = None
    best_balanced = None

    for result in benchmark_results_data:
        if result.get("success_rate", 0) < 80:
            continue  # 성공률 80% 미만은 제외

        tps = result.get("throughput", {}).get("avg_tokens_per_second", 0)
        latency = result.get("latency", {}).get("avg", float('inf'))

        # 처리량 최적
        if best_throughput is None or tps > best_throughput.get("throughput", {}).get("avg_tokens_per_second", 0):
            best_throughput = result

        # 지연시간 최적
        if best_latency is None or latency < best_latency.get("latency", {}).get("avg", float('inf')):
            best_latency = result

        # 균형 점수 (정규화된 처리량 + 정규화된 역지연시간)
        # 단순화: tps / latency
        balance_score = tps / latency if latency > 0 else 0
        if best_balanced is None or balance_score > (best_balanced.get("throughput", {}).get("avg_tokens_per_second", 0) /
                                                      best_balanced.get("latency", {}).get("avg", 1)):
            best_balanced = result

    # 차트 데이터 생성
    chart_data = {
        "latency_by_tokens": [],
        "throughput_by_tokens": [],
        "latency_by_concurrent": [],
        "throughput_by_concurrent": []
    }

    for result in benchmark_results_data:
        params = result.get("params", {})
        chart_data["latency_by_tokens"].append({
            "x": params.get("max_tokens"),
            "y": result.get("latency", {}).get("avg", 0),
            "concurrent": params.get("concurrent_requests")
        })
        chart_data["throughput_by_tokens"].append({
            "x": params.get("max_tokens"),
            "y": result.get("throughput", {}).get("avg_tokens_per_second", 0),
            "concurrent": params.get("concurrent_requests")
        })

    return {
        "optimal_configs": {
            "best_throughput": {
                "params": best_throughput.get("params") if best_throughput else None,
                "value": best_throughput.get("throughput", {}).get("avg_tokens_per_second") if best_throughput else None
            },
            "best_latency": {
                "params": best_latency.get("params") if best_latency else None,
                "value": best_latency.get("latency", {}).get("avg") if best_latency else None
            },
            "best_balanced": {
                "params": best_balanced.get("params") if best_balanced else None,
                "throughput": best_balanced.get("throughput", {}).get("avg_tokens_per_second") if best_balanced else None,
                "latency": best_balanced.get("latency", {}).get("avg") if best_balanced else None
            }
        },
        "quality_score": quality_results.get("summary", {}).get("avg_score", 0),
        "chart_data": chart_data,
        "summary": {
            "total_tests": len(benchmark_results_data),
            "boot_time": session.get("metrics", {}).get("boot_time"),
            "model": session.get("model"),
            "vllm_config": session.get("vllm_config")
        }
    }


async def execute_full_benchmark_cycle(session_id: str, config: FullBenchmarkCycle):
    """전체 벤치마크 사이클 실행 (백그라운드)"""
    session = full_cycle_sessions.get(session_id)
    if not session:
        return

    try:
        # 1. 모델 배포
        session["status"] = "running"
        session["phase"] = "deploying"
        add_log(session, f"모델 배포 시작: {config.model}")

        deploy_success = await deploy_vllm_model(session, config)
        if not deploy_success:
            session["status"] = "failed"
            session["phase"] = "failed"
            add_log(session, "모델 배포 실패", "error")
            session["completed_at"] = datetime.now().isoformat()
            return

        # 2. 부팅 대기 및 시간 측정
        session["phase"] = "booting"
        add_log(session, "vLLM 서비스 부팅 대기 중...")

        boot_result = await wait_for_vllm_ready(session)
        session["metrics"]["boot_time"] = boot_result.get("total_boot_time")
        session["metrics"]["model_load_time"] = boot_result.get("phases", {}).get("model_loaded")
        session["metrics"]["first_inference_time"] = boot_result.get("first_inference_latency")

        if not boot_result.get("success"):
            session["status"] = "failed"
            session["phase"] = "failed"
            add_log(session, f"부팅 실패: {boot_result.get('error')}", "error")
            session["completed_at"] = datetime.now().isoformat()
            return

        add_log(session, f"부팅 완료: {boot_result.get('total_boot_time'):.1f}초")

        # 3. 벤치마크 실행
        session["phase"] = "benchmarking"
        add_log(session, f"벤치마크 시작: {len(session['test_matrix'])}개 테스트")

        for i, test_params in enumerate(session["test_matrix"]):
            session["current_test_index"] = i
            add_log(session, f"테스트 {i+1}/{len(session['test_matrix'])}: max_tokens={test_params['max_tokens']}, concurrent={test_params['concurrent_requests']}")

            result = await run_benchmark_test(session, config, test_params)
            session["benchmark_results"].append(result)

        add_log(session, "벤치마크 완료")

        # 4. 품질 평가
        session["phase"] = "evaluating"
        add_log(session, "품질 평가 시작...")

        quality_result = await evaluate_quality(session, config)
        session["quality_results"] = quality_result
        add_log(session, f"품질 평가 완료: 점수 {quality_result['summary']['avg_score']}")

        # 5. 분석
        session["phase"] = "analyzing"
        add_log(session, "결과 분석 중...")

        analysis = analyze_results(session)
        session["analysis"] = analysis
        session["optimal_config"] = analysis.get("optimal_configs", {}).get("best_balanced", {}).get("params")

        add_log(session, "분석 완료")

        # 완료
        session["status"] = "completed"
        session["phase"] = "completed"
        session["completed_at"] = datetime.now().isoformat()
        add_log(session, "전체 벤치마크 사이클 완료!")

    except Exception as e:
        session["status"] = "failed"
        session["phase"] = "failed"
        add_log(session, f"오류 발생: {str(e)}", "error")
        session["completed_at"] = datetime.now().isoformat()


@router.get("/full-cycle")
async def list_full_cycle_sessions():
    """전체 사이클 세션 목록"""
    sessions = []
    for session_id, session in full_cycle_sessions.items():
        sessions.append({
            "id": session_id,
            "name": session.get("name"),
            "model": session.get("model"),
            "status": session.get("status"),
            "phase": session.get("phase"),
            "total_tests": session.get("total_tests"),
            "current_test_index": session.get("current_test_index"),
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at"),
            "boot_time": session.get("metrics", {}).get("boot_time"),
            "optimal_config": session.get("optimal_config"),
            "quality_score": session.get("quality_results", {}).get("summary", {}).get("avg_score")
        })
    sessions.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/full-cycle/{session_id}")
async def get_full_cycle_session(session_id: str):
    """전체 사이클 세션 상세 조회"""
    if session_id not in full_cycle_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return full_cycle_sessions[session_id]


@router.delete("/full-cycle/{session_id}")
async def delete_full_cycle_session(session_id: str):
    """전체 사이클 세션 삭제"""
    if session_id not in full_cycle_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    del full_cycle_sessions[session_id]
    return {"success": True, "message": "세션이 삭제되었습니다"}


@router.post("/full-cycle/{session_id}/stop")
async def stop_full_cycle_session(session_id: str):
    """실행 중인 세션 중지"""
    if session_id not in full_cycle_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    session = full_cycle_sessions[session_id]
    if session["status"] == "running":
        session["status"] = "stopped"
        session["phase"] = "stopped"
        session["completed_at"] = datetime.now().isoformat()
        add_log(session, "사용자에 의해 중지됨", "warning")

    return {"success": True, "message": "세션이 중지되었습니다"}


# ============================================
# vLLM Status Endpoint
# ============================================
@router.get("/vllm-status")
async def get_vllm_status():
    """vLLM 서비스 상태 확인"""
    # 먼저 K8s에서 vLLM pod 상태 확인
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        # vLLM deployment 상태 확인
        try:
            deployment = apps_v1.read_namespaced_deployment("vllm-server", "ai-workloads")
            replicas = deployment.spec.replicas or 0
            ready_replicas = deployment.status.ready_replicas or 0

            if replicas == 0:
                return {
                    "status": "stopped",
                    "message": "vLLM 서비스가 중지되어 있습니다",
                    "replicas": 0,
                    "ready_replicas": 0,
                    "healthy": False
                }

            if ready_replicas < replicas:
                # Pod 상태 확인
                pods = core_v1.list_namespaced_pod(
                    "ai-workloads",
                    label_selector="app=vllm-server"
                )

                pod_status = "준비 중"
                for pod in pods.items:
                    if pod.status.phase == "Pending":
                        pod_status = "대기 중 (리소스 할당 중)"
                    elif pod.status.phase == "Running":
                        # 컨테이너 상태 확인
                        for cs in pod.status.container_statuses or []:
                            if cs.state.waiting:
                                reason = cs.state.waiting.reason
                                if reason == "ContainerCreating":
                                    pod_status = "컨테이너 생성 중"
                                elif reason == "CrashLoopBackOff":
                                    pod_status = "시작 실패 (반복 충돌)"
                                elif reason == "ImagePullBackOff":
                                    pod_status = "이미지 다운로드 실패"
                                else:
                                    pod_status = f"대기 중: {reason}"
                            elif cs.state.terminated:
                                pod_status = f"종료됨: {cs.state.terminated.reason}"
                    elif pod.status.phase == "Failed":
                        pod_status = "실패"

                return {
                    "status": "starting",
                    "message": f"vLLM 서비스 {pod_status} ({ready_replicas}/{replicas})",
                    "replicas": replicas,
                    "ready_replicas": ready_replicas,
                    "healthy": False
                }
        except Exception as k8s_err:
            # Deployment를 찾을 수 없음
            return {
                "status": "not_found",
                "message": "vLLM 서비스가 배포되지 않았습니다",
                "healthy": False,
                "error": str(k8s_err)
            }

        # vLLM health 엔드포인트 확인
        async with httpx.AsyncClient() as client:
            try:
                health_check = await client.get(f"{VLLM_ENDPOINT}/health", timeout=5.0)
                if health_check.status_code == 200:
                    # 모델 정보도 가져오기
                    try:
                        models_res = await client.get(f"{VLLM_ENDPOINT}/v1/models", timeout=5.0)
                        models_data = models_res.json() if models_res.status_code == 200 else {}
                        model_list = [m.get("id") for m in models_data.get("data", [])]
                    except:
                        model_list = []

                    return {
                        "status": "online",
                        "message": "vLLM 서비스가 정상 작동 중입니다",
                        "replicas": replicas,
                        "ready_replicas": ready_replicas,
                        "healthy": True,
                        "models": model_list
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": f"vLLM 서비스가 응답하지 않습니다 (HTTP {health_check.status_code})",
                        "replicas": replicas,
                        "ready_replicas": ready_replicas,
                        "healthy": False
                    }
            except httpx.TimeoutException:
                return {
                    "status": "timeout",
                    "message": "vLLM 서비스 응답 시간 초과 (모델 로딩 중일 수 있음)",
                    "replicas": replicas,
                    "ready_replicas": ready_replicas,
                    "healthy": False
                }
            except Exception as conn_err:
                return {
                    "status": "connection_error",
                    "message": f"vLLM 서비스에 연결할 수 없습니다: {str(conn_err)}",
                    "replicas": replicas,
                    "ready_replicas": ready_replicas,
                    "healthy": False
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"상태 확인 실패: {str(e)}",
            "healthy": False
        }


# ============================================
# Initialize Default Benchmark Configs
# ============================================
def init_default_configs():
    """기본 벤치마크 설정 등록"""
    default_configs = [
        {
            "name": "Quick Test",
            "model": "facebook/opt-125m",
            "max_tokens": 50,
            "temperature": 0.7,
            "top_p": 0.9,
            "num_requests": 5,
            "concurrent_requests": 1,
            "test_prompts": [
                "What is machine learning?",
                "Explain AI briefly.",
                "What is deep learning?",
                "How do neural networks work?",
                "What is NLP?"
            ]
        },
        {
            "name": "Standard Benchmark",
            "model": "facebook/opt-125m",
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 0.9,
            "num_requests": 20,
            "concurrent_requests": 1,
            "test_prompts": [
                "Explain the concept of artificial intelligence and its applications.",
                "Write a detailed explanation of how neural networks learn.",
                "Describe the differences between supervised and unsupervised learning.",
                "What are transformers in machine learning and why are they important?",
                "Explain the concept of attention mechanism in deep learning."
            ]
        },
        {
            "name": "Stress Test",
            "model": "facebook/opt-125m",
            "max_tokens": 200,
            "temperature": 0.8,
            "top_p": 0.95,
            "num_requests": 50,
            "concurrent_requests": 5,
            "test_prompts": [
                "Write a comprehensive essay about the future of artificial intelligence.",
                "Explain quantum computing and its potential impact on machine learning.",
                "Describe the ethical considerations in developing AI systems.",
                "What are the key challenges in natural language processing today?",
                "How will AI transform healthcare in the next decade?"
            ]
        }
    ]

    for i, cfg in enumerate(default_configs):
        config_id = f"default-{i+1}"
        benchmark_configs[config_id] = {
            **cfg,
            "created_at": datetime.now().isoformat()
        }


# 모듈 로드 시 기본 설정 초기화
init_default_configs()
