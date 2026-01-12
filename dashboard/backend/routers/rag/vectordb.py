"""
Vector DB RAG Guide API
컬렉션 전략, 태깅, RBAC 가이드
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/vectordb", tags=["vectordb"])


@router.get("/rag-guide")
async def get_vectordb_rag_guide():
    """Vector DB RAG 관리 가이드 - 컬렉션 전략, 태깅, RBAC 등"""
    return {
        "collection_strategies": {
            "title": "컬렉션 분리 전략",
            "description": "RAG 시스템에서 효과적인 컬렉션 구성 방법",
            "strategies": [
                {
                    "name": "문서 타입별 분리",
                    "icon": "folder",
                    "collections": [
                        {"name": "documents_pdf", "description": "PDF 문서", "example": "매뉴얼, 보고서, 논문"},
                        {"name": "documents_web", "description": "웹 페이지 크롤링", "example": "기술 블로그, 문서"},
                        {"name": "documents_code", "description": "코드 및 README", "example": "GitHub repos"},
                        {"name": "documents_chat", "description": "대화 히스토리", "example": "Slack, Discord"}
                    ],
                    "pros": ["타입별 최적화된 청킹 가능", "특정 소스만 검색 가능"],
                    "cons": ["컬렉션 수 증가", "크로스 타입 검색 복잡"]
                },
                {
                    "name": "도메인/부서별 분리",
                    "icon": "building",
                    "collections": [
                        {"name": "hr_documents", "description": "인사 관련", "example": "취업규칙, 복리후생"},
                        {"name": "engineering_docs", "description": "기술 문서", "example": "API 스펙, 아키텍처"},
                        {"name": "sales_materials", "description": "영업 자료", "example": "제안서, 사례"},
                        {"name": "legal_contracts", "description": "법무 문서", "example": "계약서, 약관"}
                    ],
                    "pros": ["RBAC 적용 용이", "부서별 독립 관리"],
                    "cons": ["중복 데이터 가능성", "전사 검색 시 병합 필요"]
                },
                {
                    "name": "권한 레벨별 분리",
                    "icon": "lock",
                    "collections": [
                        {"name": "public_knowledge", "description": "공개 정보", "example": "FAQ, 가이드"},
                        {"name": "internal_docs", "description": "사내 전용", "example": "프로세스, 정책"},
                        {"name": "confidential_data", "description": "기밀 정보", "example": "재무, 전략"},
                        {"name": "restricted_pii", "description": "개인정보", "example": "고객 데이터"}
                    ],
                    "pros": ["보안 정책 명확", "감사 추적 용이"],
                    "cons": ["권한 변경 시 마이그레이션 필요"]
                }
            ]
        },
        "metadata_tagging": {
            "title": "메타데이터 태깅 전략",
            "description": "검색 정확도 향상을 위한 메타데이터 설계",
            "required_fields": [
                {"field": "source_file", "type": "string", "description": "원본 파일명", "example": "manual_v2.pdf"},
                {"field": "source_type", "type": "string", "description": "문서 타입", "example": "pdf|web|code|chat"},
                {"field": "created_at", "type": "datetime", "description": "생성 시간", "example": "2024-01-15T10:30:00Z"},
                {"field": "updated_at", "type": "datetime", "description": "수정 시간", "example": "2024-03-20T14:00:00Z"}
            ],
            "recommended_fields": [
                {"field": "department", "type": "string", "description": "소속 부서", "filter": True},
                {"field": "access_level", "type": "string", "description": "접근 레벨", "filter": True},
                {"field": "language", "type": "string", "description": "문서 언어", "filter": True},
                {"field": "version", "type": "string", "description": "문서 버전", "filter": False},
                {"field": "author", "type": "string", "description": "작성자", "filter": True},
                {"field": "tags", "type": "array", "description": "키워드 태그", "filter": True},
                {"field": "chunk_index", "type": "integer", "description": "청크 순서", "filter": False},
                {"field": "total_chunks", "type": "integer", "description": "전체 청크 수", "filter": False}
            ],
            "filter_example": {
                "description": "메타데이터 필터 활용 예시",
                "code": """
# Qdrant 필터 예시
filter = Filter(
    must=[
        FieldCondition(key="department", match=MatchValue(value="engineering")),
        FieldCondition(key="access_level", match=MatchAny(any=["public", "internal"])),
        FieldCondition(key="updated_at", range=Range(gte="2024-01-01"))
    ]
)

# 검색 실행
results = client.search(
    collection_name="documents",
    query_vector=query_embedding,
    query_filter=filter,
    limit=10
)
""".strip()
            }
        },
        "rbac_implementation": {
            "title": "RBAC (역할 기반 접근 제어)",
            "description": "Vector DB에서 권한 관리 구현 방법",
            "approaches": [
                {
                    "name": "컬렉션 레벨 RBAC",
                    "description": "컬렉션 단위로 접근 권한 설정",
                    "implementation": "각 부서/권한별 별도 컬렉션 생성",
                    "code": """
# 사용자 권한에 따른 컬렉션 선택
def get_accessible_collections(user_role):
    role_collections = {
        "public": ["public_knowledge"],
        "employee": ["public_knowledge", "internal_docs"],
        "manager": ["public_knowledge", "internal_docs", "confidential_data"],
        "admin": ["public_knowledge", "internal_docs", "confidential_data", "restricted_pii"]
    }
    return role_collections.get(user_role, ["public_knowledge"])

# 검색 시 허용된 컬렉션만 쿼리
accessible = get_accessible_collections(current_user.role)
results = []
for collection in accessible:
    results.extend(client.search(collection, query_vector, limit=5))
""".strip()
                },
                {
                    "name": "메타데이터 필터 RBAC",
                    "description": "단일 컬렉션에서 메타데이터 필터로 권한 제어",
                    "implementation": "access_level 필드로 필터링",
                    "code": """
# 사용자 접근 가능 레벨 정의
def get_access_levels(user_role):
    role_levels = {
        "public": ["public"],
        "employee": ["public", "internal"],
        "manager": ["public", "internal", "confidential"],
        "admin": ["public", "internal", "confidential", "restricted"]
    }
    return role_levels.get(user_role, ["public"])

# 검색 시 접근 레벨 필터 적용
levels = get_access_levels(current_user.role)
filter = Filter(
    must=[
        FieldCondition(key="access_level", match=MatchAny(any=levels))
    ]
)
results = client.search("all_documents", query_vector, query_filter=filter)
""".strip()
                }
            ],
            "best_practices": [
                "중요 문서는 업로드 시점에 access_level 필수 지정",
                "기본 access_level을 'internal'로 설정 (안전 기본값)",
                "정기적인 권한 감사 및 로깅",
                "삭제된 사용자의 문서 접근 차단"
            ]
        },
        "chunking_strategies": {
            "title": "청킹 전략",
            "description": "문서 타입별 최적 청킹 방법",
            "strategies": [
                {
                    "type": "텍스트 문서 (PDF, Word)",
                    "chunk_size": "500-1000 토큰",
                    "overlap": "50-100 토큰 (10-20%)",
                    "method": "문단/섹션 기준 분리",
                    "tip": "제목, 부제목을 청크 시작에 포함"
                },
                {
                    "type": "코드",
                    "chunk_size": "함수/클래스 단위",
                    "overlap": "imports, 클래스 정의 포함",
                    "method": "AST 기반 분리",
                    "tip": "독스트링/주석을 청크에 포함"
                },
                {
                    "type": "채팅/대화",
                    "chunk_size": "대화 턴 단위",
                    "overlap": "이전 2-3턴 컨텍스트",
                    "method": "시간/화자 기준 분리",
                    "tip": "질문-답변 쌍을 하나의 청크로"
                },
                {
                    "type": "테이블 데이터",
                    "chunk_size": "행 단위 또는 섹션",
                    "overlap": "헤더 항상 포함",
                    "method": "구조 보존 분리",
                    "tip": "테이블 컨텍스트(제목, 출처) 추가"
                }
            ]
        },
        "search_optimization": {
            "title": "검색 최적화 팁",
            "tips": [
                {
                    "category": "쿼리 전처리",
                    "items": [
                        "쿼리 확장: 동의어, 관련 용어 추가",
                        "쿼리 분해: 복잡한 질문을 하위 질문으로",
                        "HyDE: 가상 답변 생성 후 검색"
                    ]
                },
                {
                    "category": "검색 전략",
                    "items": [
                        "Hybrid Search: Dense + Sparse 결합",
                        "Re-ranking: Cross-encoder로 결과 재정렬",
                        "MMR: 다양성 고려한 결과 선택"
                    ]
                },
                {
                    "category": "컨텍스트 구성",
                    "items": [
                        "인접 청크 포함: 검색된 청크의 앞뒤 청크",
                        "메타데이터 활용: 파일명, 섹션 제목 포함",
                        "원본 링크: 출처 확인을 위한 링크 제공"
                    ]
                }
            ]
        },
        "maintenance": {
            "title": "유지보수 가이드",
            "tasks": [
                {
                    "task": "정기 재인덱싱",
                    "frequency": "월 1회 또는 모델 업데이트 시",
                    "description": "임베딩 모델 변경 시 전체 재인덱싱 필요"
                },
                {
                    "task": "중복 제거",
                    "frequency": "주 1회",
                    "description": "유사도 0.95 이상 청크 병합/제거"
                },
                {
                    "task": "오래된 문서 정리",
                    "frequency": "분기 1회",
                    "description": "updated_at 기준 오래된 버전 아카이빙"
                },
                {
                    "task": "성능 모니터링",
                    "frequency": "상시",
                    "description": "검색 지연시간, 정확도 메트릭 추적"
                }
            ],
            "backup_strategy": {
                "description": "백업 및 복구 전략",
                "recommendations": [
                    "일일 스냅샷 백업 (Qdrant snapshots)",
                    "주간 전체 백업 (컬렉션 + 메타데이터)",
                    "지역 간 복제 (DR 구성)",
                    "복구 테스트 분기별 실시"
                ]
            }
        }
    }
