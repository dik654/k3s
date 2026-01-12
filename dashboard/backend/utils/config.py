"""
전역 설정 및 상수
"""

# 워크로드 정의
WORKLOADS = {
    "vllm": {
        "namespace": "ai-workloads",
        "deployment": "vllm-server",
        "description": "vLLM 추론 서버"
    },
    "embedding": {
        "namespace": "ai-workloads",
        "deployment": "embedding-service",
        "description": "텍스트 임베딩 서비스 (BGE-M3, KURE)"
    },
    "rustfs": {
        "namespace": "storage",
        "deployment": "rustfs",
        "description": "RustFS 분산 스토리지 (Longhorn)"
    },
    "qdrant": {
        "namespace": "ai-workloads",
        "statefulset": "qdrant",
        "description": "Qdrant 벡터 데이터베이스"
    },
    "comfyui": {
        "namespace": "ai-workloads",
        "deployment": "comfyui",
        "description": "ComfyUI 이미지/동영상 생성"
    },
    "neo4j": {
        "namespace": "ai-workloads",
        "statefulset": "neo4j",
        "description": "Neo4j 그래프 데이터베이스 (Ontology)"
    },
    "loki": {
        "namespace": "logging",
        "deployment": "loki",
        "description": "Loki 로그 저장소 (중앙 집중식)"
    },
    "promtail": {
        "namespace": "logging",
        "daemonset": "promtail",
        "description": "Promtail 로그 수집기 (각 노드)"
    },
    "ragflow": {
        "namespace": "ai-workloads",
        "deployment": "ragflow",
        "description": "RAGflow RAG 엔진 (지식 베이스, 대화형 AI)"
    },
    "ragflow-mysql": {
        "namespace": "ai-workloads",
        "deployment": "ragflow-mysql",
        "description": "RAGflow MySQL (메타데이터)"
    },
    "ragflow-redis": {
        "namespace": "ai-workloads",
        "deployment": "ragflow-redis",
        "description": "RAGflow Redis (캐시)"
    },
    "ragflow-elasticsearch": {
        "namespace": "ai-workloads",
        "deployment": "ragflow-elasticsearch",
        "description": "RAGflow Elasticsearch (검색 인덱스)"
    },
    "kubeflow": {
        "namespace": "kubeflow",
        "deployment": "ml-pipeline-ui",
        "description": "Kubeflow ML 플랫폼 (파이프라인, 노트북, 모델 서빙)"
    },
    "kubeflow-pipelines": {
        "namespace": "kubeflow",
        "deployment": "ml-pipeline",
        "description": "Kubeflow Pipelines API 서버"
    },
    "kubeflow-notebook": {
        "namespace": "kubeflow",
        "statefulset": "jupyter-notebook",
        "description": "Kubeflow Jupyter 노트북 서버"
    }
}

# 지원하는 임베딩 모델 목록
SUPPORTED_EMBEDDING_MODELS = {
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": {
        "name": "MiniLM-L12 (다국어)",
        "dimension": 384,
        "description": "경량 다국어 임베딩 모델, 빠른 속도",
        "size_mb": 480,
        "languages": ["다국어 (50개 이상)"],
    },
    "BAAI/bge-m3": {
        "name": "BGE-M3",
        "dimension": 1024,
        "description": "다국어 멀티태스크 임베딩, Dense/Sparse/ColBERT 지원",
        "size_mb": 2200,
        "languages": ["다국어 (100개 이상)"],
    },
    "intfloat/multilingual-e5-large": {
        "name": "E5-Large (다국어)",
        "dimension": 1024,
        "description": "대규모 다국어 임베딩, 높은 정확도",
        "size_mb": 2100,
        "languages": ["다국어 (100개 이상)"],
    },
    "jhgan/ko-sroberta-multitask": {
        "name": "Ko-SROBERTA",
        "dimension": 768,
        "description": "한국어 특화 SROBERTA 기반 모델",
        "size_mb": 1100,
        "languages": ["한국어"],
    },
    "nlpai-lab/KURE-v1": {
        "name": "KURE v1",
        "dimension": 1024,
        "description": "고려대 NLP & AI 연구실 + HIAI 연구소 개발 한국어 특화 모델",
        "size_mb": 1500,
        "languages": ["한국어"],
    },
    "BAAI/bge-small-en-v1.5": {
        "name": "BGE-Small (영어)",
        "dimension": 384,
        "description": "경량 영어 임베딩, 빠른 추론 속도",
        "size_mb": 130,
        "languages": ["영어"],
    },
}

# MinIO 설정
MINIO_ENDPOINT = "minio-service.storage.svc.cluster.local:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"

# vLLM 설정
VLLM_URL = "http://vllm-service.ai-workloads.svc.cluster.local:8000"

# ComfyUI 설정
COMFYUI_URL = "http://comfyui-service.ai-workloads.svc.cluster.local:8188"

# Qdrant 설정
QDRANT_URL = "http://qdrant-service.ai-workloads.svc.cluster.local:6333"

# Neo4j 설정
NEO4J_URL = "bolt://neo4j-service.ai-workloads.svc.cluster.local:7687"

# RAGflow 설정
RAGFLOW_API_URL = "http://ragflow.ai-workloads.svc.cluster.local:9380"
RAGFLOW_WEB_URL = "http://ragflow.ai-workloads.svc.cluster.local:80"
