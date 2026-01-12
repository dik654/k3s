"""
vLLM API
LLM 모델 배포, 채팅, 완성
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/vllm", tags=["vllm"])

# Note: 기존 main.py의 vLLM 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
