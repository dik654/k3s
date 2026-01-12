"""
Ontology (Neo4j) related Pydantic models
"""
from typing import Dict
from pydantic import BaseModel


class CypherQueryRequest(BaseModel):
    """Cypher 쿼리 요청"""
    query: str
    params: Dict = {}


class OntologyNodeRequest(BaseModel):
    """온톨로지 노드 생성 요청"""
    label: str
    properties: Dict


class OntologyRelationRequest(BaseModel):
    """온톨로지 관계 생성 요청"""
    from_node: Dict  # {"label": "Person", "property": "name", "value": "John"}
    to_node: Dict
    relation_type: str
    properties: Dict = {}
