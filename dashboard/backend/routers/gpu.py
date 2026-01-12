"""
GPU monitoring API
GPU 상태, 온도, VRAM, 사용률 모니터링
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/gpu", tags=["gpu"])

# Note: 기존 main.py의 GPU 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
