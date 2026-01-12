"""
AI/ML 서비스 라우터
- vllm: vLLM 추론 서버
- embedding: 텍스트 임베딩 서비스
- comfyui: ComfyUI 이미지/영상 생성
"""
from .vllm import router as vllm_router
from .embedding import router as embedding_router
from .comfyui import router as comfyui_router

__all__ = [
    "vllm_router",
    "embedding_router",
    "comfyui_router"
]
