"""
API Routers - 기능별 모듈화

디렉터리 구조:
- cluster/   : 클러스터 관리 (status, workloads, pods, events)
- storage/   : 스토리지 관리 (minio, longhorn)
- ai/        : AI/ML 서비스 (vllm, embedding, comfyui)
- rag/       : RAG/Vector DB (qdrant, vectordb, ragflow, parser, ontology)
- workflow/  : 워크플로우 (workflow, langgraph, pipeline)
- monitoring/: 모니터링 (gpu, benchmark, health)
"""

# Cluster 라우터
from .cluster import (
    cluster_router,
    workloads_router,
    pods_router,
    events_router
)

# Storage 라우터
from .storage import (
    storage_router,
    longhorn_router
)

# AI/ML 라우터
from .ai import (
    vllm_router,
    embedding_router,
    comfyui_router
)

# RAG/Vector DB 라우터
from .rag import (
    qdrant_router,
    vectordb_router,
    ragflow_router,
    parser_router,
    ontology_router
)

# Workflow 라우터
from .workflow import (
    workflow_router,
    langgraph_router,
    pipeline_router
)

# Monitoring 라우터
from .monitoring import (
    gpu_router,
    benchmark_router,
    health_router
)

__all__ = [
    # Cluster
    'cluster_router',
    'workloads_router',
    'pods_router',
    'events_router',
    # Storage
    'storage_router',
    'longhorn_router',
    # AI/ML
    'vllm_router',
    'embedding_router',
    'comfyui_router',
    # RAG/Vector DB
    'qdrant_router',
    'vectordb_router',
    'ragflow_router',
    'parser_router',
    'ontology_router',
    # Workflow
    'workflow_router',
    'langgraph_router',
    'pipeline_router',
    # Monitoring
    'gpu_router',
    'benchmark_router',
    'health_router',
]
