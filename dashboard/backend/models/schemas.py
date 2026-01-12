"""
Pydantic 스키마 모델 정의
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class WorkloadAction(BaseModel):
    """워크로드 액션 요청"""
    action: str  # start, stop, scale
    replicas: Optional[int] = 1
    storage_size_gb: Optional[int] = None
    config: Optional[dict] = None


class StorageConfig(BaseModel):
    """스토리지 설정"""
    size_gb: int


class NodeInfo(BaseModel):
    """노드 정보"""
    name: str
    status: str
    roles: List[str]
    cpu_capacity: str
    cpu_used: str
    memory_capacity: str
    memory_used: str
    gpu_count: int
    gpu_type: str


class BenchmarkConfig(BaseModel):
    """벤치마크 설정"""
    id: Optional[str] = None
    name: str
    model: str
    input_tokens: int = 128
    output_tokens: int = 128
    concurrent_requests: int = 1
    total_requests: int = 10
    temperature: float = 0.7
    prompt_template: Optional[str] = None


class BenchmarkResult(BaseModel):
    """벤치마크 결과"""
    id: str
    config_id: str
    timestamp: str
    metrics: Dict[str, Any]
    status: str


class EmbeddingRequest(BaseModel):
    """임베딩 생성 요청"""
    texts: List[str]
    model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class CypherQuery(BaseModel):
    """Cypher 쿼리 요청"""
    query: str
    parameters: Optional[Dict[str, Any]] = None


class QdrantSearchRequest(BaseModel):
    """Qdrant 검색 요청"""
    collection: str
    query_vector: List[float]
    limit: int = 10
    filter: Optional[Dict[str, Any]] = None


class LangGraphCodeRequest(BaseModel):
    """LangGraph 코드 생성 요청"""
    description: str
    agent_type: str = "react"
    tools: List[str] = []
