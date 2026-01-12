"""
K3s 클러스터 대시보드 백엔드 API

API 구조:
- /api/cluster/*     - 클러스터 상태, 노드 관리
- /api/storage/*     - MinIO/Longhorn 스토리지 관리
- /api/gpu/*         - GPU 모니터링
- /api/pods/*        - Pod 관리
- /api/benchmark/*   - LLM 벤치마크
- /api/embedding/*   - 임베딩 서비스
- /api/ontology/*    - Neo4j 온톨로지
- /api/langgraph/*   - LangGraph 에이전트
- /api/workflows/*   - 워크플로우 CRUD
- /api/qdrant/*      - Qdrant 벡터 DB
- /api/vllm/*        - vLLM 서비스
- /api/comfyui/*     - ComfyUI 이미지 생성
- /api/parser/*      - 문서 파싱
- /api/vectordb/*    - Vector DB RAG 가이드
- /api/ragflow/*     - RAGflow RAG 엔진
- /api/baremetal/*   - 베어메탈 프로비저닝 (Tinkerbell)
"""
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 환경 설정
ENV = os.getenv("ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================
# Routers - 기능별 모듈에서 가져오기
# ============================================
from routers import (
    # Cluster
    cluster_router,
    workloads_router,
    pods_router,
    events_router,
    # Storage
    storage_router,
    longhorn_router,
    # AI/ML
    vllm_router,
    embedding_router,
    comfyui_router,
    # RAG/Vector DB
    qdrant_router,
    vectordb_router,
    ragflow_router,
    parser_router,
    ontology_router,
    # Workflow
    workflow_router,
    langgraph_router,
    pipeline_router,
    # Monitoring
    gpu_router,
    benchmark_router,
    health_router,
    # Baremetal
    tinkerbell_router,
    rental_router,
)


# ============================================
# FastAPI 앱 설정
# ============================================
app = FastAPI(
    title="K3s Cluster Dashboard API",
    version="1.0.0",
    description="K3s 클러스터 관리 및 AI 워크로드 대시보드"
)

# CORS 설정 - 환경에 따라 다르게 설정
if ENV == "development":
    # 개발 환경: 로컬 Vite 개발 서버 허용
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    logger.info(f"Development mode: CORS origins = {cors_origins}")
else:
    # 프로덕션: Pod 내부 통신이므로 모든 오리진 허용 (클러스터 내부)
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# 라우터 등록
# ============================================
# 헬스체크 및 기본 상태
app.include_router(health_router)

# 클러스터 관리
app.include_router(cluster_router)
app.include_router(workloads_router)
app.include_router(pods_router)
app.include_router(events_router)

# GPU 모니터링
app.include_router(gpu_router)

# 스토리지
app.include_router(storage_router)
app.include_router(longhorn_router)

# AI/ML 서비스
app.include_router(vllm_router)
app.include_router(embedding_router)
app.include_router(comfyui_router)

# RAG/Vector DB
app.include_router(qdrant_router)
app.include_router(vectordb_router)
app.include_router(ragflow_router)

# 문서 처리
app.include_router(parser_router)
app.include_router(ontology_router)

# 워크플로우/파이프라인
app.include_router(workflow_router)
app.include_router(langgraph_router)
app.include_router(pipeline_router)

# 벤치마크
app.include_router(benchmark_router)

# 베어메탈 프로비저닝
app.include_router(tinkerbell_router)
app.include_router(rental_router)


# ============================================
# 루트 엔드포인트
# ============================================
@app.get("/")
async def root():
    """API 루트 - 사용 가능한 엔드포인트 목록"""
    return {
        "name": "K3s Cluster Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "cluster": "/api/cluster/*",
            "nodes": "/api/nodes/*",
            "workloads": "/api/workloads/*",
            "pods": "/api/pods/*",
            "events": "/api/events/*",
            "gpu": "/api/gpu/*",
            "storage": "/api/storage/*",
            "longhorn": "/api/longhorn/*",
            "vllm": "/api/vllm/*",
            "embedding": "/api/embedding/*",
            "comfyui": "/api/comfyui/*",
            "qdrant": "/api/qdrant/*",
            "vectordb": "/api/vectordb/*",
            "ragflow": "/api/ragflow/*",
            "parser": "/api/parser/*",
            "ontology": "/api/ontology/*",
            "workflows": "/api/workflows/*",
            "langgraph": "/api/langgraph/*",
            "pipeline": "/api/pipeline/*",
            "benchmark": "/api/benchmark/*",
            "baremetal": "/api/baremetal/*",
            "baremetal_rentals": "/api/baremetal/rentals/*"
        },
        "external_services": {
            "ragflow_web": "http://<NODE_IP>:30081",
            "ragflow_api": "http://<NODE_IP>:30380"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
