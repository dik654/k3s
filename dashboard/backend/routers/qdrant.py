"""
Qdrant Vector Database API
컬렉션, 벡터 관리
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/qdrant", tags=["qdrant"])

# Note: 기존 main.py의 Qdrant 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
