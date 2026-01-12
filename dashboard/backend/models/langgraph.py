"""
LangGraph Agent related Pydantic models
"""
from typing import List, Dict, Optional
from pydantic import BaseModel


class LangGraphWorkflow(BaseModel):
    """LangGraph 워크플로우"""
    id: str
    name: str
    description: str = ""
    nodes: List[Dict] = []
    connections: List[Dict] = []


class LangGraphBuildRequest(BaseModel):
    """LangGraph 빌드 요청"""
    workflow: Dict
    image_name: str = ""
    image_tag: str = "latest"


class ChatRequest(BaseModel):
    """채팅 요청"""
    message: str
    thread_id: str = "default"
