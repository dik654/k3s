"""
Ontology (Neo4j) API
그래프 데이터베이스 쿼리, 노드/관계 관리
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/ontology", tags=["ontology"])

# Note: 기존 main.py의 온톨로지 관련 API를 점진적으로 이전
# 현재는 main.py에서 직접 처리
