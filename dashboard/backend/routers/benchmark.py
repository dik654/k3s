"""
LLM Benchmark API
벤치마크 설정, 실행, 결과 조회
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

# Note: 기존 main.py의 벤치마크 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
