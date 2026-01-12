"""
LangGraph Agent API
워크플로우 코드 생성, 빌드, 배포
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/langgraph", tags=["langgraph"])

# Note: 기존 main.py의 LangGraph 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
