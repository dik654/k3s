"""
Application configuration settings
"""
import os
from typing import List


class Settings:
    """Application settings"""

    # App
    APP_TITLE: str = "K3s Cluster Dashboard API"
    APP_VERSION: str = "1.0.0"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # Paths
    WORKFLOWS_DIR: str = "/data/workflows"
    FRONTEND_PATH: str = "/app/frontend"

    # Embedding Models
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


settings = Settings()
