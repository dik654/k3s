"""
ComfyUI API
이미지 생성 워크플로우, 생성 히스토리
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/comfyui", tags=["comfyui"])

# Note: 기존 main.py의 ComfyUI 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
