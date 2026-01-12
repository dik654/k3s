"""
AI Pipeline Status API
파이프라인 컴포넌트 상태 및 연결 현황
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def get_k8s_clients():
    """Kubernetes 클라이언트 초기화"""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api(), client.AppsV1Api(), client.CustomObjectsApi()


# 워크로드 설정
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
}


@router.get("/status")
async def get_pipeline_status():
    """AI 파이프라인 상태 및 연결 상태 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        # 각 워크로드 상태 확인
        pipeline_components = {
            "vllm": {"name": "vLLM", "icon": "robot", "role": "LLM 추론", "status": "stopped", "connections": ["qdrant", "neo4j", "embedding"]},
            "embedding": {"name": "Embedding", "icon": "brain", "role": "텍스트 임베딩", "status": "stopped", "connections": ["qdrant", "vllm"]},
            "qdrant": {"name": "Qdrant", "icon": "search", "role": "벡터 검색", "status": "stopped", "connections": ["vllm", "embedding"]},
            "neo4j": {"name": "Neo4j", "icon": "share-2", "role": "그래프 DB", "status": "stopped", "connections": ["vllm"]},
            "comfyui": {"name": "ComfyUI", "icon": "image", "role": "이미지 생성", "status": "stopped", "connections": ["rustfs"]},
            "rustfs": {"name": "RustFS", "icon": "hard-drive", "role": "오브젝트 저장소", "status": "stopped", "connections": ["comfyui"]}
        }

        namespace = "ai-workloads"
        storage_namespace = "storage"

        # 워크로드별 상태 확인
        for name, component in pipeline_components.items():
            try:
                ns = storage_namespace if name == "rustfs" else namespace
                config = WORKLOADS.get(name, {})

                if "deployment" in config:
                    deploy = apps_v1.read_namespaced_deployment(config["deployment"], ns)
                    if deploy.status.ready_replicas and deploy.status.ready_replicas > 0:
                        component["status"] = "running"
                        component["replicas"] = deploy.status.ready_replicas
                elif "statefulset" in config:
                    sts = apps_v1.read_namespaced_stateful_set(config["statefulset"], ns)
                    if sts.status.ready_replicas and sts.status.ready_replicas > 0:
                        component["status"] = "running"
                        component["replicas"] = sts.status.ready_replicas
            except:
                pass

        # 활성 연결 계산
        active_connections = []
        for name, component in pipeline_components.items():
            if component["status"] == "running":
                for conn in component["connections"]:
                    if pipeline_components.get(conn, {}).get("status") == "running":
                        active_connections.append({
                            "from": name,
                            "to": conn,
                            "status": "active"
                        })

        # 최근 에러 이벤트 가져오기
        events = core_v1.list_event_for_all_namespaces()
        recent_errors = []
        for event in events.items:
            if event.type == "Warning" and event.last_timestamp:
                recent_errors.append({
                    "source": event.involved_object.name if event.involved_object else "",
                    "reason": event.reason,
                    "message": event.message[:100] if event.message else "",
                    "timestamp": event.last_timestamp.isoformat()
                })

        # 최신 5개만
        recent_errors = sorted(recent_errors, key=lambda x: x["timestamp"], reverse=True)[:5]

        return {
            "components": pipeline_components,
            "connections": active_connections,
            "recent_errors": recent_errors,
            "pipeline_health": "healthy" if all(c["status"] == "running" for c in pipeline_components.values()) else "partial"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
