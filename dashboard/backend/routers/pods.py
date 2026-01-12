"""
Pod management API
Pod 목록, 상태, 로그 조회
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/pods", tags=["pods"])

# Note: 기존 main.py의 Pod 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
