"""
vLLM API Router
LLM 모델 배포, 채팅, 완성 기능
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx

router = APIRouter(prefix="/api/vllm", tags=["vllm"])

# vLLM 서비스 URL
VLLM_URL = "http://vllm-service.ai-workloads.svc.cluster.local:8000"
_vllm_demo_mode = True


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 0.9
    stream: bool = False


async def check_vllm_connection():
    """Check if vLLM is available"""
    global _vllm_demo_mode
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{VLLM_URL}/v1/models")
            if resp.status_code == 200:
                _vllm_demo_mode = False
                return True
    except:
        pass
    _vllm_demo_mode = True
    return False


@router.get("/status")
async def get_vllm_status():
    """Get vLLM server status"""
    await check_vllm_connection()

    if not _vllm_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{VLLM_URL}/v1/models")
                if resp.status_code == 200:
                    return {
                        "status": "running",
                        "connected": True,
                        "url": VLLM_URL,
                        "mode": "connected"
                    }
        except:
            pass

    return {
        "status": "stopped",
        "connected": False,
        "mode": "demo"
    }


@router.get("/models")
async def get_vllm_models():
    """Get available models"""
    await check_vllm_connection()

    if not _vllm_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{VLLM_URL}/v1/models")
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass

    # Demo mode
    return {
        "models": [
            {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen2.5-7B-Instruct (demo)"},
            {"id": "Qwen/Qwen2.5-Coder-7B-Instruct", "name": "Qwen2.5-Coder-7B (demo)"}
        ],
        "mode": "demo"
    }


@router.post("/chat")
async def vllm_chat(request: dict):
    """Chat with vLLM model"""
    await check_vllm_connection()

    model = request.get("model", "Qwen/Qwen2.5-7B-Instruct")
    messages = request.get("messages", [])
    temperature = request.get("temperature", 0.7)
    max_tokens = request.get("max_tokens", 1024)

    if not _vllm_demo_mode:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{VLLM_URL}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    # Demo mode response
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "vLLM 서버가 실행 중이지 않습니다. AI 워크로드 페이지에서 vLLM을 시작해주세요."
            }
        }],
        "mode": "demo"
    }


@router.post("/chat/stream")
async def vllm_chat_stream(request: dict):
    """Chat with vLLM model (streaming)"""
    await check_vllm_connection()

    model = request.get("model", "Qwen/Qwen2.5-7B-Instruct")
    messages = request.get("messages", [])
    temperature = request.get("temperature", 0.7)
    max_tokens = request.get("max_tokens", 1024)
    top_p = request.get("top_p", 0.9)

    async def stream_response():
        if not _vllm_demo_mode:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST",
                        f"{VLLM_URL}/v1/chat/completions",
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "top_p": top_p,
                            "stream": True
                        }
                    ) as resp:
                        async for line in resp.aiter_lines():
                            if line:
                                yield f"{line}\n"
                        return
            except Exception as e:
                yield f'data: {{"error": "{str(e)}"}}\n'
                return

        # Demo mode - stream a simple response
        demo_response = "vLLM 서버가 실행 중이지 않습니다. AI 워크로드 페이지에서 vLLM을 시작해주세요."
        for char in demo_response:
            yield f'data: {{"choices": [{{"delta": {{"content": "{char}"}}}}]}}\n'
        yield "data: [DONE]\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@router.post("/start")
async def start_vllm(request: dict):
    """Start vLLM service"""
    model = request.get("model", "Qwen/Qwen2.5-7B-Instruct")
    return {
        "success": True,
        "message": f"vLLM 시작 요청됨 (모델: {model})",
        "note": "실제 시작은 AI 워크로드 페이지에서 진행해주세요."
    }


@router.post("/stop")
async def stop_vllm():
    """Stop vLLM service"""
    return {
        "success": True,
        "message": "vLLM 중지 요청됨",
        "note": "실제 중지는 AI 워크로드 페이지에서 진행해주세요."
    }
