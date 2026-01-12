"""
Ontology (Neo4j) API Router
그래프 데이터베이스 쿼리, 노드/관계 관리
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/ontology", tags=["ontology"])

# Neo4j 연결 설정
NEO4J_URL = "bolt://neo4j-service.ai-workloads.svc.cluster.local:7687"
_neo4j_demo_mode = True


class CypherQuery(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]] = None


@router.post("/query")
async def execute_cypher_query(request: CypherQuery):
    """Cypher 쿼리 실행"""
    query = request.query
    parameters = request.parameters or {}

    # Demo mode - 시뮬레이션 결과 반환
    if "MATCH" in query.upper():
        return {
            "results": [
                {"n": {"name": "김철수", "role": "Developer"}},
                {"n": {"name": "이영희", "role": "Manager"}},
                {"n": {"name": "AI Platform", "status": "active"}}
            ],
            "mode": "simulation",
            "note": "Neo4j 서버가 실행 중이지 않아 시뮬레이션 결과입니다."
        }
    elif "CREATE" in query.upper():
        return {
            "results": [{"created": 1}],
            "mode": "simulation",
            "note": "Neo4j 서버가 실행 중이지 않아 시뮬레이션 결과입니다."
        }
    else:
        return {
            "results": [],
            "mode": "simulation",
            "note": "Neo4j 서버가 실행 중이지 않아 시뮬레이션 결과입니다."
        }


@router.get("/schema")
async def get_ontology_schema():
    """온톨로지 스키마 정보 (RDBMS vs Graph 비교)"""
    return {
        "rdbms_schema": {
            "tables": [
                {"name": "employees", "columns": ["id (PK)", "name", "email", "department_id (FK)"]},
                {"name": "departments", "columns": ["id (PK)", "name", "budget"]},
                {"name": "projects", "columns": ["id (PK)", "name", "status"]},
                {"name": "employee_projects", "columns": ["employee_id (FK)", "project_id (FK)", "role"]}
            ],
            "sql_example": """
SELECT e.name, d.name as dept, p.name as project
FROM employees e
JOIN departments d ON e.department_id = d.id
JOIN employee_projects ep ON e.id = ep.employee_id
JOIN projects p ON ep.project_id = p.id
WHERE p.status = 'active';
""".strip()
        },
        "graph_schema": {
            "nodes": [
                {"label": "Person", "properties": ["name", "email", "role"], "color": "#4ecdc4"},
                {"label": "Department", "properties": ["name", "budget", "location"], "color": "#45b7d1"},
                {"label": "Project", "properties": ["name", "status", "deadline"], "color": "#96ceb4"},
                {"label": "Technology", "properties": ["name", "category", "version"], "color": "#ffeaa7"}
            ],
            "relationships": [
                {"from": "Person", "type": "WORKS_IN", "to": "Department"},
                {"from": "Person", "type": "MANAGES", "to": "Person"},
                {"from": "Person", "type": "CONTRIBUTES_TO", "to": "Project"},
                {"from": "Project", "type": "USES", "to": "Technology"},
                {"from": "Person", "type": "KNOWS", "to": "Technology"}
            ],
            "cypher_example": """
MATCH (p:Person)-[:CONTRIBUTES_TO]->(proj:Project)-[:USES]->(t:Technology)
WHERE proj.status = 'active'
RETURN p.name, proj.name, collect(t.name) as technologies
""".strip()
        },
        "comparison": {
            "data_model": {
                "rdbms": "테이블 + 외래키로 관계 표현",
                "graph": "노드 + 관계를 1급 시민으로 직접 표현"
            },
            "query_language": {
                "rdbms": "SQL (JOIN 기반)",
                "graph": "Cypher (패턴 매칭)"
            },
            "schema_flexibility": {
                "rdbms": "고정 스키마, 변경 어려움",
                "graph": "노드/관계 동적 추가 가능"
            },
            "query_complexity": {
                "rdbms": "n-depth 관계 → n개 JOIN",
                "graph": "n-depth 관계 → 단일 패턴 매칭"
            }
        }
    }


@router.get("/graph-data")
async def get_sample_graph_data():
    """시각화용 샘플 그래프 데이터"""
    return {
        "nodes": [
            {"id": "1", "label": "Person", "name": "김철수", "properties": {"role": "Developer"}, "x": 100, "y": 200},
            {"id": "2", "label": "Person", "name": "이영희", "properties": {"role": "Manager"}, "x": 300, "y": 100},
            {"id": "3", "label": "Department", "name": "Engineering", "properties": {"location": "서울"}, "x": 300, "y": 300},
            {"id": "4", "label": "Project", "name": "AI Platform", "properties": {"status": "active"}, "x": 500, "y": 200},
            {"id": "5", "label": "Technology", "name": "Kubernetes", "properties": {"category": "Infrastructure"}, "x": 700, "y": 150},
            {"id": "6", "label": "Technology", "name": "Python", "properties": {"category": "Language"}, "x": 700, "y": 250}
        ],
        "edges": [
            {"from": "1", "to": "3", "type": "WORKS_IN", "properties": {}},
            {"from": "2", "to": "1", "type": "MANAGES", "properties": {}},
            {"from": "1", "to": "4", "type": "CONTRIBUTES_TO", "properties": {"role": "Lead"}},
            {"from": "2", "to": "4", "type": "CONTRIBUTES_TO", "properties": {"role": "PM"}},
            {"from": "4", "to": "5", "type": "USES", "properties": {}},
            {"from": "4", "to": "6", "type": "USES", "properties": {}},
            {"from": "1", "to": "5", "type": "KNOWS", "properties": {"level": "expert"}},
            {"from": "1", "to": "6", "type": "KNOWS", "properties": {"level": "advanced"}}
        ]
    }


@router.get("/rag-integration")
async def get_ontology_rag_integration():
    """온톨로지가 RAG를 강화하는 방법 설명"""
    return {
        "traditional_rag": {
            "flow": ["Query", "Vector Search", "Top-K Documents", "LLM", "Response"],
            "limitations": [
                "의미적으로 유사하지만 관련 없는 문서 검색",
                "엔티티 간 관계 정보 손실",
                "컨텍스트 윈도우 제한으로 전체 맥락 파악 어려움"
            ]
        },
        "graph_enhanced_rag": {
            "flow": [
                {"step": "Query", "description": "사용자 질문"},
                {"step": "Entity Extraction", "description": "질문에서 엔티티 추출"},
                {"step": "Graph Traversal", "description": "관련 엔티티 및 관계 탐색"},
                {"step": "Vector Search", "description": "관련 문서 검색"},
                {"step": "Context Fusion", "description": "그래프 정보 + 문서 통합"},
                {"step": "LLM", "description": "강화된 컨텍스트로 응답 생성"},
                {"step": "Response", "description": "정확하고 연결된 응답"}
            ],
            "advantages": [
                "관계 기반 컨텍스트 확장",
                "Multi-hop reasoning 지원",
                "엔티티 disambiguation",
                "추론 경로 설명 가능"
            ]
        },
        "example": {
            "query": "김철수가 참여한 프로젝트에서 사용하는 기술은?",
            "graph_context": {
                "entities_found": ["김철수 (Person)"],
                "traversal": [
                    "김철수 -[CONTRIBUTES_TO]-> AI Platform",
                    "AI Platform -[USES]-> Kubernetes",
                    "AI Platform -[USES]-> Python"
                ],
                "related_info": [
                    "김철수는 AI Platform의 Lead Developer",
                    "프로젝트 상태: active"
                ]
            },
            "enhanced_answer": "김철수가 Lead로 참여 중인 AI Platform 프로젝트에서는 Kubernetes(인프라)와 Python(개발 언어)을 사용하고 있습니다."
        }
    }


@router.get("/index-types")
async def get_ontology_index_types():
    """Neo4j 인덱스 타입 설명"""
    return {
        "types": [
            {
                "name": "Node Label Index",
                "description": "노드 라벨별 빠른 조회",
                "syntax": "CREATE INDEX FOR (n:Person) ON (n.name)",
                "use_case": "특정 타입 노드 검색",
                "icon": "🏷️"
            },
            {
                "name": "Relationship Type Index",
                "description": "관계 타입별 인덱스",
                "syntax": "CREATE INDEX FOR ()-[r:WORKS_AT]-() ON (r.since)",
                "use_case": "특정 관계 속성으로 필터링",
                "icon": "🔗"
            },
            {
                "name": "Full-text Index",
                "description": "텍스트 전문 검색",
                "syntax": "CREATE FULLTEXT INDEX personNames FOR (n:Person) ON EACH [n.name, n.bio]",
                "use_case": "자연어 검색, 유사어 매칭",
                "icon": "📝"
            },
            {
                "name": "Vector Index",
                "description": "임베딩 벡터 유사도 검색",
                "syntax": "CREATE VECTOR INDEX embeddingIndex FOR (n:Document) ON (n.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1024}}",
                "use_case": "시맨틱 검색, RAG",
                "icon": "🎯"
            },
            {
                "name": "Composite Index",
                "description": "복합 속성 인덱스",
                "syntax": "CREATE INDEX FOR (n:Person) ON (n.department, n.role)",
                "use_case": "다중 조건 검색 최적화",
                "icon": "📊"
            }
        ],
        "hybrid_search_example": {
            "description": "Vector + Graph 하이브리드 검색",
            "cypher": """
// 1. 벡터 검색으로 유사 문서 찾기
CALL db.index.vector.queryNodes('embeddingIndex', 5, $queryVector)
YIELD node AS doc, score

// 2. 그래프 탐색으로 관련 엔티티 확장
MATCH (doc)-[:MENTIONS]->(entity:Entity)-[:RELATED_TO*1..2]-(related)

// 3. 결과 반환
RETURN doc.content, entity.name, collect(related.name) AS relatedEntities
ORDER BY score DESC
""".strip(),
            "explanation": [
                "벡터 유사도로 초기 후보 선정",
                "그래프 관계로 컨텍스트 확장",
                "관련 엔티티까지 포함한 풍부한 결과"
            ]
        }
    }
