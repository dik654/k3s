"""
Cluster management API
클러스터 상태, 노드 관리, 워크로드 관리
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/cluster", tags=["cluster"])

# Note: 기존 main.py의 클러스터 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
