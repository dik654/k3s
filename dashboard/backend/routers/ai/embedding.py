"""
Embedding service API
텍스트 임베딩 생성, 비교, 모델 관리
"""

import os
import time
import hashlib
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx

from utils.config import SUPPORTED_EMBEDDING_MODELS

router = APIRouter(prefix="/api/embedding", tags=["embedding"])

# ============================================
# 전역 변수 (임베딩 모델 상태)
# ============================================
_embedding_models = {}  # {model_name: model_instance}
_model_download_status = {}  # {model_name: "downloading" | "ready" | "error"}

# 클러스터 내 임베딩 서비스 URL
EMBEDDING_SERVICE_URL = os.getenv(
    "EMBEDDING_SERVICE_URL",
    "http://embedding-service.ai-workloads.svc.cluster.local:8080"
)


# ============================================
# Pydantic 모델
# ============================================
class EmbeddingRequest(BaseModel):
    text: str
    model: str = "BAAI/bge-m3"
    return_sparse: bool = True
    return_dense: bool = True


class EmbeddingCompareRequest(BaseModel):
    text1: str
    text2: str
    model: str = "BAAI/bge-m3"


# ============================================
# 헬퍼 함수
# ============================================
def get_embedding_model(model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    """임베딩 모델을 지연 로딩으로 가져옴 (메모리 효율화)"""
    global _embedding_models, _model_download_status

    # 모델이 이미 로드되어 있으면 재사용
    if model_name in _embedding_models:
        return _embedding_models[model_name]

    # 지원하지 않는 모델이면 기본 모델로 폴백
    if model_name not in SUPPORTED_EMBEDDING_MODELS:
        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    try:
        from sentence_transformers import SentenceTransformer

        _model_download_status[model_name] = "downloading"
        print(f"Loading embedding model: {model_name}")

        # 실제 모델 로드
        model = SentenceTransformer(model_name)
        _embedding_models[model_name] = model
        _model_download_status[model_name] = "ready"
        print(f"Embedding model {model_name} loaded successfully")

        return model
    except Exception as e:
        _model_download_status[model_name] = "error"
        print(f"Failed to load embedding model {model_name}: {e}")
        return None


def get_model_status():
    """모든 모델의 상태 반환"""
    result = {}
    for model_id, info in SUPPORTED_EMBEDDING_MODELS.items():
        status = _model_download_status.get(model_id, "not_loaded")
        result[model_id] = {
            **info,
            "id": model_id,
            "status": status,
            "loaded": model_id in _embedding_models
        }
    return result


# ============================================
# API 엔드포인트
# ============================================
@router.get("/models")
async def get_available_models():
    """사용 가능한 임베딩 모델 목록 반환"""
    return {
        "models": get_model_status(),
        "loaded_count": len(_embedding_models),
        "total_count": len(SUPPORTED_EMBEDDING_MODELS)
    }


@router.post("/models/{model_id:path}/load")
async def load_model(model_id: str, background_tasks: BackgroundTasks):
    """특정 임베딩 모델을 다운로드/로드"""
    if model_id not in SUPPORTED_EMBEDDING_MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not supported")

    if model_id in _embedding_models:
        return {
            "success": True,
            "message": f"Model {model_id} already loaded",
            "status": "ready"
        }

    # 백그라운드에서 모델 로드
    def load_in_background():
        get_embedding_model(model_id)

    background_tasks.add_task(load_in_background)

    return {
        "success": True,
        "message": f"Model {model_id} loading started",
        "status": "downloading"
    }


@router.get("/models/{model_id:path}/status")
async def get_model_load_status(model_id: str):
    """특정 모델의 로드 상태 확인"""
    if model_id not in SUPPORTED_EMBEDDING_MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not supported")

    status = _model_download_status.get(model_id, "not_loaded")
    loaded = model_id in _embedding_models

    return {
        "model_id": model_id,
        "status": status,
        "loaded": loaded,
        **SUPPORTED_EMBEDDING_MODELS[model_id]
    }


@router.post("/generate")
async def generate_embedding(request: EmbeddingRequest):
    """텍스트를 임베딩 벡터로 변환 (실제 모델 사용)"""
    start_time = time.time()

    try:
        # 1. 먼저 클러스터 내 임베딩 서비스 시도 (GPU 가속)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{EMBEDDING_SERVICE_URL}/embed",
                    json={
                        "inputs": request.text,
                        "model": request.model,
                        "return_sparse": request.return_sparse,
                        "return_dense": request.return_dense
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "source": "cluster-gpu",
                        "text": request.text,
                        "model": request.model,
                        "dense_embedding": result.get("dense", result.get("embedding", [])),
                        "sparse_embedding": result.get("sparse", {}),
                        "dimension": len(result.get("dense", result.get("embedding", []))),
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
        except Exception as e:
            print(f"Cluster embedding service unavailable: {e}")

        # 2. 로컬 sentence-transformers 모델 사용
        model = get_embedding_model(request.model)
        if model is not None:
            # 실제 임베딩 생성
            embedding = model.encode(request.text, normalize_embeddings=True)
            dense_vector = embedding.tolist()

            # Sparse 임베딩 (간단한 토큰 기반 - 실제 BM25 스타일)
            sparse_embedding = {}
            if request.return_sparse:
                words = request.text.lower().split()
                word_counts = {}
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1
                for word, count in word_counts.items():
                    token_id = int(hashlib.md5(word.encode()).hexdigest()[:6], 16) % 30000
                    # TF-IDF 스타일 가중치
                    tf = count / len(words)
                    weight = round(tf * (1 + len(word) / 10), 4)  # 긴 단어에 약간의 가중치
                    sparse_embedding[str(token_id)] = weight

            processing_time = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "source": "local-cpu",
                "text": request.text,
                "model": request.model,
                "model_loaded": SUPPORTED_EMBEDDING_MODELS.get(request.model, {}).get("name", request.model),
                "dense_embedding": dense_vector if request.return_dense else [],
                "sparse_embedding": sparse_embedding if request.return_sparse else {},
                "dimension": len(dense_vector),
                "processing_time_ms": processing_time
            }

        # 3. 모델 로드 실패 시 에러 (시뮬레이션 제거)
        raise HTTPException(
            status_code=503,
            detail=f"Embedding model {request.model} not available. Please load it first via /api/embedding/models/{request.model}/load"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_embeddings(request: EmbeddingCompareRequest):
    """두 텍스트의 임베딩 유사도 비교"""
    try:
        emb1_req = EmbeddingRequest(text=request.text1, model=request.model)
        emb2_req = EmbeddingRequest(text=request.text2, model=request.model)

        emb1_result = await generate_embedding(emb1_req)
        emb2_result = await generate_embedding(emb2_req)

        vec1 = emb1_result["dense_embedding"]
        vec2 = emb2_result["dense_embedding"]

        if len(vec1) != len(vec2):
            raise HTTPException(status_code=400, detail="벡터 차원이 일치하지 않습니다")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a ** 2 for a in vec1) ** 0.5
        magnitude2 = sum(b ** 2 for b in vec2) ** 0.5

        cosine_similarity = dot_product / (magnitude1 * magnitude2) if magnitude1 and magnitude2 else 0

        if cosine_similarity >= 0.9:
            interpretation = "매우 유사함 (거의 동일한 의미)"
        elif cosine_similarity >= 0.7:
            interpretation = "유사함 (관련된 내용)"
        elif cosine_similarity >= 0.5:
            interpretation = "약간 관련됨"
        elif cosine_similarity >= 0.3:
            interpretation = "약간 다름"
        else:
            interpretation = "매우 다름 (관련 없음)"

        return {
            "success": True,
            "text1": request.text1,
            "text2": request.text2,
            "model": request.model,
            "cosine_similarity": round(cosine_similarity, 6),
            "similarity_percent": round(cosine_similarity * 100, 2),
            "interpretation": interpretation,
            "embedding1_preview": vec1[:10],
            "embedding2_preview": vec2[:10],
            "dimension": len(vec1),
            "source": emb1_result.get("source", "unknown")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage-format")
async def get_storage_format_example():
    """Qdrant에 저장되는 형식 예시"""
    return {
        "description": "Qdrant 벡터 DB에 저장되는 데이터 형식",
        "dense_only_example": {
            "id": "doc_001",
            "vector": "[0.023, -0.156, 0.872, 0.034, ... (총 1024차원)]",
            "payload": {
                "text": "원본 텍스트 내용",
                "source": "문서 출처",
                "created_at": "2026-01-08T12:00:00Z"
            }
        },
        "hybrid_example": {
            "id": "doc_002",
            "vector": {
                "dense": "[0.023, -0.156, 0.872, ... (1024차원)]",
                "sparse": {"indices": [1542, 3891, 7234], "values": [0.45, 0.32, 0.78]}
            },
            "payload": {
                "text": "하이브리드 검색용 텍스트",
                "chunk_index": 3
            }
        },
        "search_types": {
            "dense_search": "의미 기반 검색 (유사한 개념 찾기)",
            "sparse_search": "키워드 기반 검색 (정확한 단어 매칭)",
            "hybrid_search": "Dense + Sparse 결합 (RRF Fusion)"
        }
    }
