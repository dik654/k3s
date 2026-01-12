"""
Embedding service
텍스트 임베딩 생성 및 관리
"""
from typing import Dict, Any
from core.config import settings

# 임베딩 모델 전역 변수 (지연 로딩)
_embedding_models: Dict[str, Any] = {}
_model_download_status: Dict[str, str] = {}


class EmbeddingService:
    """임베딩 서비스"""

    @staticmethod
    def get_model(model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """임베딩 모델을 지연 로딩으로 가져옴"""
        global _embedding_models, _model_download_status

        if model_name in _embedding_models:
            return _embedding_models[model_name]

        if model_name not in settings.SUPPORTED_EMBEDDING_MODELS:
            model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

        try:
            from sentence_transformers import SentenceTransformer

            _model_download_status[model_name] = "downloading"
            print(f"Loading embedding model: {model_name}")

            model = SentenceTransformer(model_name)
            _embedding_models[model_name] = model
            _model_download_status[model_name] = "ready"
            print(f"Embedding model {model_name} loaded successfully")

            return model
        except Exception as e:
            _model_download_status[model_name] = "error"
            print(f"Failed to load embedding model {model_name}: {e}")
            return None

    @staticmethod
    def get_model_status():
        """로드된 모델 상태 반환"""
        models_info = {}
        for model_id, info in settings.SUPPORTED_EMBEDDING_MODELS.items():
            models_info[model_id] = {
                **info,
                "loaded": model_id in _embedding_models,
                "status": _model_download_status.get(model_id, "not_loaded")
            }
        return models_info
