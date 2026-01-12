"""
Storage management API (MinIO, Longhorn)
버킷, 객체, 볼륨, 스냅샷 관리
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/storage", tags=["storage"])

# Note: 기존 main.py의 스토리지 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
