"""
Workflow related Pydantic models
"""
from typing import Optional, List, Dict
from pydantic import BaseModel


class WorkflowCreate(BaseModel):
    """워크플로우 생성"""
    name: str
    description: Optional[str] = ""
    nodes: List[Dict] = []
    connections: List[Dict] = []


class WorkflowUpdate(BaseModel):
    """워크플로우 수정"""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict]] = None
    connections: Optional[List[Dict]] = None
