"""
Embedding service API
텍스트 임베딩 생성, 비교
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/embedding", tags=["embedding"])

# Note: 기존 main.py의 임베딩 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
