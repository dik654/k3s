"""
Embedding related Pydantic models
"""
from pydantic import BaseModel


class EmbeddingRequest(BaseModel):
    """임베딩 요청"""
    text: str
    model: str = "BAAI/bge-m3"
    return_sparse: bool = True
    return_dense: bool = True


class EmbeddingCompareRequest(BaseModel):
    """임베딩 비교 요청"""
    text1: str
    text2: str
    model: str = "BAAI/bge-m3"
