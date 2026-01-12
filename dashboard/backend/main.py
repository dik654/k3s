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
"""

import os
import asyncio
import subprocess
import json
import re
import random
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import StreamingResponse, Response
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# ============================================
# Routers (신규 분리된 라우터)
# ============================================
from routers.workflow import router as workflow_router
from routers.health import router as health_router

# 임베딩 모델 전역 변수 (지연 로딩)
_embedding_models = {}  # {model_name: model_instance}
_model_download_status = {}  # {model_name: "downloading" | "ready" | "error"}

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

app = FastAPI(title="K3s Cluster Dashboard API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# 라우터 등록
# ============================================
app.include_router(workflow_router)
app.include_router(health_router)

# Kubernetes 클라이언트 초기화
def get_k8s_clients():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    return client.CoreV1Api(), client.AppsV1Api(), client.CustomObjectsApi()


# ============================================
# 모델 정의
# ============================================

class WorkloadAction(BaseModel):
    action: str  # start, stop, scale
    replicas: Optional[int] = 1
    storage_size_gb: Optional[int] = None  # RustFS 스토리지 할당 크기 (GB)
    config: Optional[dict] = None  # 워크로드별 설정 (model, gpuCount, gpuIndices, nodeSelector 등)

class StorageConfig(BaseModel):
    size_gb: int

class NodeInfo(BaseModel):
    name: str
    status: str
    roles: list[str]
    cpu_capacity: str
    cpu_used: str
    memory_capacity: str
    memory_used: str
    gpu_count: int
    gpu_type: str


# ============================================
# 클러스터 상태 API
# ============================================

@app.get("/api/cluster/status")
async def get_cluster_status():
    """클러스터 전체 상태 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        # 노드 정보
        nodes = core_v1.list_node()
        node_count = len(nodes.items)
        ready_nodes = sum(1 for n in nodes.items
                        if any(c.type == "Ready" and c.status == "True"
                              for c in n.status.conditions))

        # 전체 Pod 수
        pods = core_v1.list_pod_for_all_namespaces()
        running_pods = sum(1 for p in pods.items if p.status.phase == "Running")

        # 네임스페이스 수
        namespaces = core_v1.list_namespace()

        return {
            "status": "healthy" if ready_nodes == node_count else "degraded",
            "nodes": {
                "total": node_count,
                "ready": ready_nodes
            },
            "pods": {
                "total": len(pods.items),
                "running": running_pods
            },
            "namespaces": len(namespaces.items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nodes")
async def get_nodes():
    """노드 목록 및 리소스 정보"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        result = []
        for node in nodes.items:
            # 노드 상태
            status = "Unknown"
            for condition in node.status.conditions:
                if condition.type == "Ready":
                    status = "Ready" if condition.status == "True" else "NotReady"
                    break

            # 역할 추출
            roles = []
            for label, value in (node.metadata.labels or {}).items():
                if label.startswith("node-role.kubernetes.io/"):
                    roles.append(label.split("/")[1])

            # GPU 정보
            gpu_count = int(node.metadata.labels.get("gpu-count", "0"))
            gpu_type = node.metadata.labels.get("gpu-type", "none")

            # 리소스 용량
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}

            result.append({
                "name": node.metadata.name,
                "status": status,
                "roles": roles if roles else ["worker"],
                "cpu_capacity": capacity.get("cpu", "0"),
                "memory_capacity": capacity.get("memory", "0"),
                "gpu_count": gpu_count,
                "gpu_type": gpu_type,
                "created": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else None
            })

        return {"nodes": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nodes/{node_name}/metrics")
async def get_node_metrics(node_name: str):
    """노드 리소스 사용량 (metrics-server 필요)"""
    try:
        core_v1, _, custom = get_k8s_clients()

        # metrics-server에서 노드 메트릭 조회
        try:
            metrics = custom.get_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes",
                name=node_name
            )

            return {
                "node": node_name,
                "cpu_usage": metrics.get("usage", {}).get("cpu", "0"),
                "memory_usage": metrics.get("usage", {}).get("memory", "0"),
                "timestamp": metrics.get("timestamp")
            }
        except ApiException as e:
            if e.status == 404:
                return {
                    "node": node_name,
                    "cpu_usage": "N/A",
                    "memory_usage": "N/A",
                    "message": "metrics-server not available"
                }
            raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 워크로드 관리 API
# ============================================

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
    }
}


@app.get("/api/workloads")
async def get_workloads():
    """모든 워크로드 상태 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        result = {}
        for name, config in WORKLOADS.items():
            namespace = config["namespace"]

            try:
                # 네임스페이스 존재 확인
                try:
                    core_v1.read_namespace(namespace)
                except ApiException:
                    result[name] = {
                        "status": "not_deployed",
                        "replicas": 0,
                        "ready_replicas": 0,
                        "description": config["description"]
                    }
                    continue

                # Deployment, StatefulSet, 또는 DaemonSet 조회
                if "deployment" in config:
                    deploy = apps_v1.read_namespaced_deployment(
                        config["deployment"], namespace
                    )
                    result[name] = {
                        "status": "running" if (deploy.status.ready_replicas or 0) > 0 else "stopped",
                        "replicas": deploy.spec.replicas or 0,
                        "ready_replicas": deploy.status.ready_replicas or 0,
                        "description": config["description"]
                    }
                elif "statefulset" in config:
                    sts = apps_v1.read_namespaced_stateful_set(
                        config["statefulset"], namespace
                    )
                    result[name] = {
                        "status": "running" if (sts.status.ready_replicas or 0) > 0 else "stopped",
                        "replicas": sts.spec.replicas or 0,
                        "ready_replicas": sts.status.ready_replicas or 0,
                        "description": config["description"]
                    }
                elif "daemonset" in config:
                    ds = apps_v1.read_namespaced_daemon_set(
                        config["daemonset"], namespace
                    )
                    result[name] = {
                        "status": "running" if (ds.status.number_ready or 0) > 0 else "stopped",
                        "replicas": ds.status.desired_number_scheduled or 0,
                        "ready_replicas": ds.status.number_ready or 0,
                        "description": config["description"],
                        "type": "daemonset"
                    }
            except ApiException as e:
                if e.status == 404:
                    result[name] = {
                        "status": "not_deployed",
                        "replicas": 0,
                        "ready_replicas": 0,
                        "description": config["description"]
                    }
                else:
                    raise

        return {"workloads": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workloads/{workload_name}")
async def control_workload(workload_name: str, action: WorkloadAction):
    """워크로드 제어 (시작/중지/스케일) - 없으면 자동 생성"""
    if workload_name not in WORKLOADS:
        raise HTTPException(status_code=404, detail=f"Unknown workload: {workload_name}")

    try:
        core_v1, apps_v1, _ = get_k8s_clients()
        config = WORKLOADS[workload_name]
        namespace = config["namespace"]

        # 네임스페이스 생성 (없으면)
        try:
            core_v1.read_namespace(namespace)
        except ApiException:
            core_v1.create_namespace(
                client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
            )

        if action.action == "start":
            replicas = action.replicas or 1
        elif action.action == "stop":
            replicas = 0
        elif action.action == "scale":
            replicas = action.replicas or 1
        elif action.action == "expand":
            # 실행 중 스토리지 확장 전용 액션
            if workload_name == "rustfs" and action.storage_size_gb:
                await update_rustfs_storage_size(core_v1, apps_v1, namespace, action.storage_size_gb)
                return {
                    "workload": workload_name,
                    "action": action.action,
                    "storage_size_gb": action.storage_size_gb,
                    "message": f"RustFS 스토리지가 {action.storage_size_gb}GB로 확장되었습니다. 변경 사항은 잠시 후 반영됩니다."
                }
            else:
                raise HTTPException(status_code=400, detail="expand 액션은 rustfs에서만 사용 가능합니다.")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action.action}")

        # RustFS 시작 시 스토리지 크기 설정
        if workload_name == "rustfs" and action.action == "start" and action.storage_size_gb:
            await update_rustfs_storage_size(core_v1, apps_v1, namespace, action.storage_size_gb)

        # 워크로드가 존재하는지 확인하고 없으면 생성
        workload_exists = False
        if "deployment" in config:
            try:
                existing_deployment = apps_v1.read_namespaced_deployment(config["deployment"], namespace)
                workload_exists = True

                # start 액션이고 config가 변경되었으면 deployment 재생성
                if action.action == "start" and action.config:
                    # GPU 인덱스, 노드 선택자 등이 변경되었는지 확인
                    needs_recreate = False
                    if action.config.get("gpuIndices") or action.config.get("nodeSelector"):
                        needs_recreate = True

                    if needs_recreate:
                        # 기존 deployment 삭제
                        apps_v1.delete_namespaced_deployment(
                            config["deployment"],
                            namespace,
                            body=client.V1DeleteOptions(propagation_policy='Foreground')
                        )
                        # 잠시 대기 (삭제 완료 확인)
                        import time
                        time.sleep(2)
                        # 새로운 deployment 생성
                        await create_workload_deployment(workload_name, namespace, action.config, core_v1, apps_v1)
            except ApiException as e:
                if e.status == 404 and action.action == "start":
                    # Deployment 생성
                    await create_workload_deployment(workload_name, namespace, action.config, core_v1, apps_v1)
                    workload_exists = True
                elif e.status != 404:
                    raise
        elif "statefulset" in config:
            try:
                apps_v1.read_namespaced_stateful_set(config["statefulset"], namespace)
                workload_exists = True
            except ApiException as e:
                if e.status == 404 and action.action == "start":
                    # StatefulSet 생성
                    await create_workload_statefulset(workload_name, namespace, action.config, core_v1, apps_v1)
                    workload_exists = True
                elif e.status != 404:
                    raise
        elif "daemonset" in config:
            try:
                apps_v1.read_namespaced_daemon_set(config["daemonset"], namespace)
                workload_exists = True
            except ApiException as e:
                if e.status == 404 and action.action == "start":
                    await create_workload_daemonset(workload_name, namespace, action.config, core_v1, apps_v1)
                    workload_exists = True
                elif e.status != 404:
                    raise

        if not workload_exists and action.action != "start":
            return {
                "workload": workload_name,
                "action": action.action,
                "message": f"{workload_name}이 배포되지 않은 상태입니다."
            }

        # 스케일 적용
        if "deployment" in config:
            apps_v1.patch_namespaced_deployment_scale(
                config["deployment"],
                namespace,
                {"spec": {"replicas": replicas}}
            )
        elif "statefulset" in config:
            apps_v1.patch_namespaced_stateful_set_scale(
                config["statefulset"],
                namespace,
                {"spec": {"replicas": replicas}}
            )
        elif "daemonset" in config:
            # DaemonSet은 스케일 개념이 없음 - nodeSelector로 제어
            if action.action == "stop":
                # 모든 노드에서 제외하여 중지
                apps_v1.patch_namespaced_daemon_set(
                    config["daemonset"],
                    namespace,
                    {"spec": {"template": {"spec": {"nodeSelector": {"non-existent-label": "true"}}}}}
                )
            elif action.action == "start":
                # nodeSelector 제거하여 다시 시작
                apps_v1.patch_namespaced_daemon_set(
                    config["daemonset"],
                    namespace,
                    {"spec": {"template": {"spec": {"nodeSelector": None}}}}
                )
            return {
                "workload": workload_name,
                "action": action.action,
                "type": "daemonset",
                "message": f"{workload_name} {action.action} 완료 (DaemonSet)"
            }

        return {
            "workload": workload_name,
            "action": action.action,
            "replicas": replicas,
            "storage_size_gb": action.storage_size_gb,
            "message": f"{workload_name} {action.action} 완료"
        }
    except ApiException as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def create_workload_deployment(workload_name: str, namespace: str, config: dict, core_v1, apps_v1):
    """워크로드별 Deployment 생성"""
    config = config or {}

    if workload_name == "comfyui":
        await create_comfyui_deployment(namespace, config, core_v1, apps_v1)
    elif workload_name == "vllm":
        await create_vllm_deployment(namespace, config, core_v1, apps_v1)
    elif workload_name == "embedding":
        await create_embedding_deployment(namespace, config, core_v1, apps_v1)
    elif workload_name == "rustfs":
        await create_rustfs_deployment(namespace, config, core_v1, apps_v1)
    elif workload_name == "loki":
        await create_loki_deployment(namespace, config, core_v1, apps_v1)
    else:
        raise HTTPException(status_code=400, detail=f"Deployment 템플릿이 없습니다: {workload_name}")


async def create_workload_statefulset(workload_name: str, namespace: str, config: dict, core_v1, apps_v1):
    """워크로드별 StatefulSet 생성"""
    config = config or {}

    if workload_name == "qdrant":
        await create_qdrant_statefulset(namespace, config, core_v1, apps_v1)
    elif workload_name == "neo4j":
        await create_neo4j_statefulset(namespace, config, core_v1, apps_v1)
    else:
        raise HTTPException(status_code=400, detail=f"StatefulSet 템플릿이 없습니다: {workload_name}")


async def create_workload_daemonset(workload_name: str, namespace: str, config: dict, core_v1, apps_v1):
    """워크로드별 DaemonSet 생성"""
    config = config or {}

    if workload_name == "promtail":
        await create_promtail_daemonset(namespace, config, core_v1, apps_v1)
    else:
        raise HTTPException(status_code=400, detail=f"DaemonSet 템플릿이 없습니다: {workload_name}")


async def create_comfyui_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """ComfyUI Deployment 생성"""
    gpu_count = config.get("gpuCount", 1)
    node_selector = config.get("nodeSelector", "")
    gpu_indices = config.get("gpuIndices", [])
    storage_size = config.get("storageSize", 100)

    # GPU 인덱스 환경변수 및 인증 비활성화
    env_vars = [
        client.V1EnvVar(name="NVIDIA_VISIBLE_DEVICES", value=",".join(map(str, gpu_indices)) if gpu_indices else "all"),
        client.V1EnvVar(name="WEB_ENABLE_AUTH", value="false"),
    ]

    # 노드 셀렉터
    node_selector_dict = {}
    if node_selector:
        node_selector_dict["kubernetes.io/hostname"] = node_selector

    # PVC 생성
    pvc_name = "comfyui-data"
    try:
        core_v1.read_namespaced_persistent_volume_claim(pvc_name, namespace)
    except ApiException:
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=pvc_name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                storage_class_name="longhorn",
                resources=client.V1ResourceRequirements(
                    requests={"storage": f"{storage_size}Gi"}
                )
            )
        )
        core_v1.create_namespaced_persistent_volume_claim(namespace, pvc)

    # Service 생성
    svc_name = "comfyui-service"
    try:
        core_v1.read_namespaced_service(svc_name, namespace)
    except ApiException:
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=svc_name),
            spec=client.V1ServiceSpec(
                selector={"app": "comfyui"},
                ports=[client.V1ServicePort(port=8188, target_port=8188)],
                type="ClusterIP"
            )
        )
        core_v1.create_namespaced_service(namespace, service)

    # Deployment 생성
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="comfyui"),
        spec=client.V1DeploymentSpec(
            replicas=0,  # 시작 시 스케일업됨
            selector=client.V1LabelSelector(match_labels={"app": "comfyui"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "comfyui"}),
                spec=client.V1PodSpec(
                    runtime_class_name="nvidia",
                    node_selector=node_selector_dict if node_selector_dict else None,
                    containers=[
                        client.V1Container(
                            name="comfyui",
                            image="ghcr.io/ai-dock/comfyui:latest",
                            ports=[client.V1ContainerPort(container_port=8188)],
                            env=env_vars,
                            resources=client.V1ResourceRequirements(
                                limits={"nvidia.com/gpu": str(gpu_count)},
                                requests={"nvidia.com/gpu": str(gpu_count)}
                            ),
                            volume_mounts=[
                                client.V1VolumeMount(name="data", mount_path="/workspace")
                            ],
                            lifecycle=client.V1Lifecycle(
                                post_start=client.V1LifecycleHandler(
                                    _exec=client.V1ExecAction(
                                        command=[
                                            "/bin/bash",
                                            "-c",
                                            "cd /opt/ComfyUI && git fetch origin && git checkout master && git pull origin master || true"
                                        ]
                                    )
                                )
                            )
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="data",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=pvc_name
                            )
                        )
                    ]
                )
            )
        )
    )
    apps_v1.create_namespaced_deployment(namespace, deployment)


async def create_neo4j_statefulset(namespace: str, config: dict, core_v1, apps_v1):
    """Neo4j StatefulSet 생성"""
    storage_size = config.get("storageSize", 50)

    # Service 생성
    svc_name = "neo4j"
    try:
        core_v1.read_namespaced_service(svc_name, namespace)
    except ApiException:
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=svc_name),
            spec=client.V1ServiceSpec(
                selector={"app": "neo4j"},
                ports=[
                    client.V1ServicePort(name="http", port=7474, target_port=7474),
                    client.V1ServicePort(name="bolt", port=7687, target_port=7687)
                ],
                type="ClusterIP"
            )
        )
        core_v1.create_namespaced_service(namespace, service)

    # StatefulSet 생성
    statefulset = client.V1StatefulSet(
        metadata=client.V1ObjectMeta(name="neo4j"),
        spec=client.V1StatefulSetSpec(
            replicas=0,
            service_name="neo4j",
            selector=client.V1LabelSelector(match_labels={"app": "neo4j"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "neo4j"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="neo4j",
                            image="neo4j:5.15.0-community",
                            ports=[
                                client.V1ContainerPort(container_port=7474),
                                client.V1ContainerPort(container_port=7687)
                            ],
                            env=[
                                client.V1EnvVar(name="NEO4J_AUTH", value="neo4j/password123"),
                                client.V1EnvVar(name="NEO4J_PLUGINS", value='["apoc"]'),
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(name="data", mount_path="/data")
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"memory": "1Gi", "cpu": "500m"},
                                limits={"memory": "4Gi", "cpu": "2"}
                            )
                        )
                    ]
                )
            ),
            volume_claim_templates=[
                client.V1PersistentVolumeClaim(
                    metadata=client.V1ObjectMeta(name="data"),
                    spec=client.V1PersistentVolumeClaimSpec(
                        access_modes=["ReadWriteOnce"],
                        storage_class_name="longhorn",
                        resources=client.V1ResourceRequirements(
                            requests={"storage": f"{storage_size}Gi"}
                        )
                    )
                )
            ]
        )
    )
    apps_v1.create_namespaced_stateful_set(namespace, statefulset)


async def create_vllm_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """vLLM Deployment 생성"""
    model = config.get("model", "Qwen/Qwen2.5-7B-Instruct")
    gpu_count = config.get("gpuCount", 1)
    node_selector = config.get("nodeSelector", "")
    gpu_indices = config.get("gpuIndices", [])
    memory = config.get("memory", "32Gi")

    env_vars = [
        client.V1EnvVar(name="NVIDIA_VISIBLE_DEVICES", value=",".join(map(str, gpu_indices)) if gpu_indices else "all"),
        client.V1EnvVar(name="HF_HOME", value="/models"),
    ]

    node_selector_dict = {}
    if node_selector:
        node_selector_dict["kubernetes.io/hostname"] = node_selector

    # PVC 생성
    pvc_name = "vllm-models"
    try:
        core_v1.read_namespaced_persistent_volume_claim(pvc_name, namespace)
    except ApiException:
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=pvc_name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                storage_class_name="longhorn",
                resources=client.V1ResourceRequirements(
                    requests={"storage": "200Gi"}
                )
            )
        )
        core_v1.create_namespaced_persistent_volume_claim(namespace, pvc)

    # Service 생성
    svc_name = "vllm-service"
    try:
        core_v1.read_namespaced_service(svc_name, namespace)
    except ApiException:
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=svc_name),
            spec=client.V1ServiceSpec(
                selector={"app": "vllm-server"},
                ports=[client.V1ServicePort(port=8000, target_port=8000)],
                type="ClusterIP"
            )
        )
        core_v1.create_namespaced_service(namespace, service)

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="vllm-server"),
        spec=client.V1DeploymentSpec(
            replicas=0,
            selector=client.V1LabelSelector(match_labels={"app": "vllm-server"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "vllm-server"}),
                spec=client.V1PodSpec(
                    runtime_class_name="nvidia",
                    node_selector=node_selector_dict if node_selector_dict else None,
                    containers=[
                        client.V1Container(
                            name="vllm",
                            image="vllm/vllm-openai:latest",
                            args=[
                                "--model", model,
                                "--tensor-parallel-size", str(gpu_count),
                                "--trust-remote-code"
                            ],
                            ports=[client.V1ContainerPort(container_port=8000)],
                            env=env_vars,
                            resources=client.V1ResourceRequirements(
                                limits={"nvidia.com/gpu": str(gpu_count), "memory": memory},
                                requests={"nvidia.com/gpu": str(gpu_count), "memory": memory}
                            ),
                            volume_mounts=[
                                client.V1VolumeMount(name="models", mount_path="/models")
                            ]
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="models",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=pvc_name
                            )
                        )
                    ]
                )
            )
        )
    )
    apps_v1.create_namespaced_deployment(namespace, deployment)


async def create_embedding_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """Embedding Service Deployment 생성"""
    # 간단한 embedding 서비스 deployment
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="embedding-service"),
        spec=client.V1DeploymentSpec(
            replicas=0,
            selector=client.V1LabelSelector(match_labels={"app": "embedding-service"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "embedding-service"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="embedding",
                            image="ghcr.io/huggingface/text-embeddings-inference:cpu-1.2",
                            args=["--model-id", "BAAI/bge-m3"],
                            ports=[client.V1ContainerPort(container_port=8080)],
                            resources=client.V1ResourceRequirements(
                                requests={"memory": "4Gi", "cpu": "2"},
                                limits={"memory": "8Gi", "cpu": "4"}
                            )
                        )
                    ]
                )
            )
        )
    )
    apps_v1.create_namespaced_deployment(namespace, deployment)


async def create_rustfs_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """RustFS Deployment 생성"""
    storage_size = config.get("storageSize", 100)

    pvc_name = "rustfs-longhorn"
    try:
        core_v1.read_namespaced_persistent_volume_claim(pvc_name, namespace)
    except ApiException:
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=pvc_name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                storage_class_name="longhorn",
                resources=client.V1ResourceRequirements(
                    requests={"storage": f"{storage_size}Gi"}
                )
            )
        )
        core_v1.create_namespaced_persistent_volume_claim(namespace, pvc)

    # Service 생성
    svc_name = "rustfs"
    try:
        core_v1.read_namespaced_service(svc_name, namespace)
    except ApiException:
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=svc_name),
            spec=client.V1ServiceSpec(
                selector={"app": "rustfs"},
                ports=[
                    client.V1ServicePort(name="api", port=9000, target_port=9000),
                    client.V1ServicePort(name="console", port=9001, target_port=9001)
                ],
                type="ClusterIP"
            )
        )
        core_v1.create_namespaced_service(namespace, service)

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="rustfs"),
        spec=client.V1DeploymentSpec(
            replicas=0,
            selector=client.V1LabelSelector(match_labels={"app": "rustfs"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "rustfs"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="rustfs",
                            image="minio/minio:latest",
                            args=["server", "/data", "--console-address", ":9001"],
                            ports=[
                                client.V1ContainerPort(container_port=9000),
                                client.V1ContainerPort(container_port=9001)
                            ],
                            env=[
                                client.V1EnvVar(name="MINIO_ROOT_USER", value="admin"),
                                client.V1EnvVar(name="MINIO_ROOT_PASSWORD", value="adminpassword"),
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(name="data", mount_path="/data")
                            ]
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="data",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=pvc_name
                            )
                        )
                    ]
                )
            )
        )
    )
    apps_v1.create_namespaced_deployment(namespace, deployment)


async def create_qdrant_statefulset(namespace: str, config: dict, core_v1, apps_v1):
    """Qdrant StatefulSet 생성"""
    storage_size = config.get("storageSize", 50)

    # Service 생성
    svc_name = "qdrant"
    try:
        core_v1.read_namespaced_service(svc_name, namespace)
    except ApiException:
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=svc_name),
            spec=client.V1ServiceSpec(
                selector={"app": "qdrant"},
                ports=[
                    client.V1ServicePort(name="http", port=6333, target_port=6333),
                    client.V1ServicePort(name="grpc", port=6334, target_port=6334)
                ],
                type="ClusterIP"
            )
        )
        core_v1.create_namespaced_service(namespace, service)

    statefulset = client.V1StatefulSet(
        metadata=client.V1ObjectMeta(name="qdrant"),
        spec=client.V1StatefulSetSpec(
            replicas=0,
            service_name="qdrant",
            selector=client.V1LabelSelector(match_labels={"app": "qdrant"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "qdrant"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="qdrant",
                            image="qdrant/qdrant:latest",
                            ports=[
                                client.V1ContainerPort(container_port=6333),
                                client.V1ContainerPort(container_port=6334)
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(name="data", mount_path="/qdrant/storage")
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"memory": "1Gi", "cpu": "500m"},
                                limits={"memory": "4Gi", "cpu": "2"}
                            )
                        )
                    ]
                )
            ),
            volume_claim_templates=[
                client.V1PersistentVolumeClaim(
                    metadata=client.V1ObjectMeta(name="data"),
                    spec=client.V1PersistentVolumeClaimSpec(
                        access_modes=["ReadWriteOnce"],
                        storage_class_name="longhorn",
                        resources=client.V1ResourceRequirements(
                            requests={"storage": f"{storage_size}Gi"}
                        )
                    )
                )
            ]
        )
    )
    apps_v1.create_namespaced_stateful_set(namespace, statefulset)


async def create_loki_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """Loki Deployment 생성"""
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="loki"),
        spec=client.V1DeploymentSpec(
            replicas=0,
            selector=client.V1LabelSelector(match_labels={"app": "loki"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "loki"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="loki",
                            image="grafana/loki:2.9.0",
                            args=["-config.file=/etc/loki/local-config.yaml"],
                            ports=[client.V1ContainerPort(container_port=3100)],
                            resources=client.V1ResourceRequirements(
                                requests={"memory": "256Mi", "cpu": "100m"},
                                limits={"memory": "1Gi", "cpu": "500m"}
                            )
                        )
                    ]
                )
            )
        )
    )
    apps_v1.create_namespaced_deployment(namespace, deployment)


async def create_promtail_daemonset(namespace: str, config: dict, core_v1, apps_v1):
    """Promtail DaemonSet 생성"""
    daemonset = client.V1DaemonSet(
        metadata=client.V1ObjectMeta(name="promtail"),
        spec=client.V1DaemonSetSpec(
            selector=client.V1LabelSelector(match_labels={"app": "promtail"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "promtail"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="promtail",
                            image="grafana/promtail:2.9.0",
                            args=["-config.file=/etc/promtail/promtail.yaml"],
                            volume_mounts=[
                                client.V1VolumeMount(name="logs", mount_path="/var/log", read_only=True)
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"memory": "64Mi", "cpu": "50m"},
                                limits={"memory": "256Mi", "cpu": "200m"}
                            )
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="logs",
                            host_path=client.V1HostPathVolumeSource(path="/var/log")
                        )
                    ]
                )
            )
        )
    )
    apps_v1.create_namespaced_daemon_set(namespace, daemonset)


async def update_rustfs_storage_size(core_v1, apps_v1, namespace: str, size_gb: int):
    """RustFS PVC 크기 업데이트 - 확장만 가능, 축소 불가"""
    try:
        # 기존 PVC 확인
        pvcs = core_v1.list_namespaced_persistent_volume_claim(namespace)
        rustfs_pvc = None
        for pvc in pvcs.items:
            if "rustfs" in pvc.metadata.name or "data-rustfs" in pvc.metadata.name:
                rustfs_pvc = pvc
                break

        if rustfs_pvc:
            # 기존 PVC가 있으면 크기 확장 시도 (축소는 불가)
            current_size = rustfs_pvc.spec.resources.requests.get("storage", "0Gi")
            current_gb = 0
            if current_size.endswith("Gi"):
                current_gb = int(current_size[:-2])
            elif current_size.endswith("Ti"):
                current_gb = int(current_size[:-2]) * 1024

            if size_gb < current_gb:
                # 축소 시도 - 예외 발생
                raise HTTPException(
                    status_code=400,
                    detail=f"스토리지 축소는 불가능합니다. 현재 할당량: {current_gb}GB, 요청: {size_gb}GB. 데이터 손실 방지를 위해 Kubernetes PVC는 확장만 지원합니다."
                )
            elif size_gb > current_gb:
                # PVC 크기 확장
                core_v1.patch_namespaced_persistent_volume_claim(
                    rustfs_pvc.metadata.name,
                    namespace,
                    {"spec": {"resources": {"requests": {"storage": f"{size_gb}Gi"}}}}
                )
                print(f"RustFS storage expanded: {current_gb}GB -> {size_gb}GB")
            # size_gb == current_gb: 변경 없음
        else:
            # PVC가 없으면 새로 생성될 때 적용됨
            print(f"RustFS storage size will be set to {size_gb}GB on deployment")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating RustFS storage size: {e}")


# ============================================
# RustFS 스토리지 관리
# ============================================

@app.get("/api/storage/rustfs")
async def get_rustfs_status():
    """RustFS 상태 조회 (Deployment 또는 StatefulSet 지원)"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        namespace = "storage"

        # Deployment 먼저 확인 (Longhorn 사용 시)
        try:
            deploy = apps_v1.read_namespaced_deployment("rustfs", namespace)

            # rustfs-longhorn PVC 확인
            total_storage = 0
            try:
                pvc = core_v1.read_namespaced_persistent_volume_claim("rustfs-longhorn", namespace)
                storage = pvc.spec.resources.requests.get("storage", "0Gi")
                if storage.endswith("Gi"):
                    total_storage = int(storage[:-2])
                elif storage.endswith("Ti"):
                    total_storage = int(storage[:-2]) * 1024
            except ApiException:
                pass

            return {
                "status": "running" if (deploy.status.ready_replicas or 0) > 0 else "stopped",
                "replicas": deploy.spec.replicas or 0,
                "ready_replicas": deploy.status.ready_replicas or 0,
                "total_storage_gb": total_storage,
                "storage_per_node_gb": total_storage,
                "deployment_type": "deployment"
            }
        except ApiException:
            pass

        # StatefulSet 확인 (레거시)
        try:
            sts = apps_v1.read_namespaced_stateful_set("rustfs", namespace)
            pvcs = core_v1.list_namespaced_persistent_volume_claim(namespace)

            total_storage = 0
            for pvc in pvcs.items:
                if pvc.metadata.name.startswith("data-rustfs"):
                    storage = pvc.spec.resources.requests.get("storage", "0Gi")
                    if storage.endswith("Gi"):
                        total_storage += int(storage[:-2])

            return {
                "status": "running" if (sts.status.ready_replicas or 0) > 0 else "stopped",
                "replicas": sts.spec.replicas or 0,
                "ready_replicas": sts.status.ready_replicas or 0,
                "total_storage_gb": total_storage,
                "storage_per_node_gb": total_storage // max(sts.spec.replicas or 1, 1),
                "deployment_type": "statefulset"
            }
        except ApiException:
            return {
                "status": "not_deployed",
                "replicas": 0,
                "ready_replicas": 0,
                "total_storage_gb": 0,
                "storage_per_node_gb": 0,
                "deployment_type": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/storage/rustfs/resize")
async def resize_rustfs(config: StorageConfig):
    """RustFS 스토리지 크기 변경"""
    # 실제 구현에서는 PVC 크기 조정이나 노드 추가 등을 수행
    return {
        "message": f"RustFS 스토리지를 {config.size_gb}GB로 조정 요청됨",
        "size_gb": config.size_gb
    }


class StorageResetRequest(BaseModel):
    new_size_gb: int
    confirm: bool = False  # 데이터 삭제 확인


@app.post("/api/storage/rustfs/reset")
async def reset_rustfs_storage(request: StorageResetRequest):
    """
    RustFS 스토리지 초기화 (축소 포함)
    - StatefulSet 삭제
    - PVC 삭제 (데이터 삭제!)
    - 새 크기로 매니페스트 업데이트
    주의: 모든 데이터가 삭제됩니다!
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="데이터 삭제 확인이 필요합니다. confirm=true로 설정하세요."
        )

    if request.new_size_gb < 10:
        raise HTTPException(
            status_code=400,
            detail="최소 스토리지 크기는 10GB입니다."
        )

    try:
        core_v1, apps_v1, _ = get_k8s_clients()
        namespace = "storage"

        # 1. StatefulSet 삭제 (cascade로 Pod도 삭제됨)
        try:
            apps_v1.delete_namespaced_stateful_set(
                name="rustfs",
                namespace=namespace,
                propagation_policy="Foreground"
            )
            print("RustFS StatefulSet 삭제됨")
            # StatefulSet 삭제 완료 대기
            await asyncio.sleep(5)
        except ApiException as e:
            if e.status != 404:
                raise

        # 2. PVC 삭제 (데이터 삭제!)
        pvcs = core_v1.list_namespaced_persistent_volume_claim(namespace)
        for pvc in pvcs.items:
            if pvc.metadata.name.startswith("data-rustfs"):
                core_v1.delete_namespaced_persistent_volume_claim(
                    name=pvc.metadata.name,
                    namespace=namespace
                )
                print(f"PVC {pvc.metadata.name} 삭제됨")

        # 3. 매니페스트 파일 업데이트
        manifest_path = "/app/manifests/14-rustfs.yaml"
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                content = f.read()

            # storage 크기 업데이트
            import re
            content = re.sub(
                r'storage:\s*\d+Gi',
                f'storage: {request.new_size_gb}Gi',
                content
            )

            with open(manifest_path, "w") as f:
                f.write(content)
            print(f"매니페스트 업데이트됨: {request.new_size_gb}Gi")

        return {
            "message": f"RustFS 스토리지가 초기화되었습니다. 새 크기: {request.new_size_gb}GB",
            "new_size_gb": request.new_size_gb,
            "status": "reset_complete",
            "note": "워크로드를 다시 시작하면 새 크기로 PVC가 생성됩니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스토리지 초기화 실패: {str(e)}")


# ============================================
# GPU 상태 API (상세 정보 포함)
# ============================================

import httpx

async def get_gpu_metrics_from_collectors():
    """GPU 메트릭 collector Pod들에서 실시간 메트릭 수집"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # gpu-metrics Pod 목록 조회
        pods = core_v1.list_namespaced_pod(
            namespace="dashboard",
            label_selector="app=gpu-metrics"
        )

        all_gpus = []
        gpu_index = 0

        async with httpx.AsyncClient(timeout=5.0) as client:
            for pod in pods.items:
                if pod.status.phase != "Running":
                    continue

                pod_ip = pod.status.pod_ip
                if not pod_ip:
                    continue

                try:
                    response = await client.get(f"http://{pod_ip}:9400/metrics")
                    if response.status_code == 200:
                        data = response.json()
                        node_name = data.get("node", pod.spec.node_name)

                        for gpu in data.get("gpus", []):
                            gpu["index"] = gpu_index
                            gpu["node"] = node_name
                            gpu["status"] = "available"
                            all_gpus.append(gpu)
                            gpu_index += 1
                except Exception as e:
                    print(f"Failed to get metrics from {pod_ip}: {e}")
                    continue

        return all_gpus if all_gpus else None
    except Exception as e:
        print(f"Error getting GPU metrics: {e}")
        return None


def get_gpu_info_from_k8s():
    """Kubernetes 노드에서 GPU 정보 조회 (fallback)"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        gpus = []
        gpu_index = 0

        for node in nodes.items:
            capacity = node.status.capacity or {}
            labels = node.metadata.labels or {}

            # nvidia.com/gpu 리소스 확인
            gpu_capacity = capacity.get("nvidia.com/gpu", "0")

            try:
                gpu_count = int(gpu_capacity)
            except:
                gpu_count = 0

            if gpu_count > 0:
                # GPU 타입 추출 (라벨에서 또는 기본값)
                gpu_type = labels.get("nvidia.com/gpu.product",
                           labels.get("gpu-type", "NVIDIA GPU"))

                # 메모리 정보 (라벨에서)
                gpu_memory = labels.get("nvidia.com/gpu.memory", "0")
                try:
                    memory_total = int(gpu_memory)
                except:
                    memory_total = 24576  # 기본값 24GB

                # 각 GPU에 대해 항목 생성
                for i in range(gpu_count):
                    gpus.append({
                        "index": gpu_index,
                        "name": gpu_type,
                        "node": node.metadata.name,
                        "temperature": 0,
                        "memory_used": 0,
                        "memory_total": memory_total,
                        "utilization": 0,
                        "power_draw": 0,
                        "power_limit": 350,
                        "status": "available"
                    })
                    gpu_index += 1

        return gpus
    except Exception as e:
        print(f"Error getting GPU info: {e}")
        return None


@app.get("/api/gpu/status")
async def get_gpu_status():
    """GPU 상태 조회 (기본 정보)"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        gpu_nodes = []
        total_gpus = 0

        for node in nodes.items:
            capacity = node.status.capacity or {}
            labels = node.metadata.labels or {}

            # nvidia.com/gpu 리소스 확인
            gpu_capacity = capacity.get("nvidia.com/gpu", "0")
            try:
                gpu_count = int(gpu_capacity)
            except:
                gpu_count = 0

            if gpu_count > 0:
                gpu_type = labels.get("nvidia.com/gpu.product",
                           labels.get("gpu-type", "NVIDIA GPU"))

                gpu_nodes.append({
                    "node": node.metadata.name,
                    "gpu_type": gpu_type,
                    "gpu_count": gpu_count,
                    "status": "available"
                })
                total_gpus += gpu_count

        return {
            "total_gpus": total_gpus,
            "gpu_nodes": gpu_nodes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gpu/detailed")
async def get_gpu_detailed():
    """GPU 상세 정보 조회"""
    try:
        # 먼저 collector에서 실시간 메트릭 시도
        gpus = await get_gpu_metrics_from_collectors()

        # collector가 없으면 K8s 정보로 fallback
        if gpus is None or len(gpus) == 0:
            gpus = get_gpu_info_from_k8s()

        if gpus is None or len(gpus) == 0:
            return {
                "available": False,
                "message": "클러스터에 GPU 노드가 없습니다",
                "gpus": []
            }

        return {
            "available": True,
            "gpu_count": len(gpus),
            "gpus": gpus
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Pod 목록 API
# ============================================

@app.get("/api/pods")
async def get_all_pods():
    """모든 네임스페이스의 Pod 목록"""
    try:
        core_v1, _, custom = get_k8s_clients()
        pods = core_v1.list_pod_for_all_namespaces()

        # Pod 메트릭 조회 시도
        pod_metrics = {}
        try:
            metrics = custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="pods"
            )
            for item in metrics.get("items", []):
                key = f"{item['metadata']['namespace']}/{item['metadata']['name']}"
                containers = item.get("containers", [])
                if containers:
                    cpu_usage = sum(parse_cpu(c.get("usage", {}).get("cpu", "0")) for c in containers)
                    memory_usage = sum(parse_memory(c.get("usage", {}).get("memory", "0")) for c in containers)
                    pod_metrics[key] = {"cpu": cpu_usage, "memory": memory_usage}
        except:
            pass

        result = []
        for pod in pods.items:
            key = f"{pod.metadata.namespace}/{pod.metadata.name}"
            metrics = pod_metrics.get(key, {})

            # 컨테이너 상태
            container_statuses = []
            for cs in (pod.status.container_statuses or []):
                container_statuses.append({
                    "name": cs.name,
                    "ready": cs.ready,
                    "restarts": cs.restart_count,
                    "state": "running" if cs.state.running else "waiting" if cs.state.waiting else "terminated"
                })

            result.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "ip": pod.status.pod_ip,
                "cpu_usage": metrics.get("cpu", 0),
                "memory_usage": metrics.get("memory", 0),
                "containers": container_statuses,
                "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
            })

        # 네임스페이스별 그룹핑
        by_namespace = {}
        for pod in result:
            ns = pod["namespace"]
            if ns not in by_namespace:
                by_namespace[ns] = []
            by_namespace[ns].append(pod)

        return {
            "total": len(result),
            "pods": result,
            "by_namespace": by_namespace
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pods/{namespace}")
async def get_namespace_pods(namespace: str):
    """특정 네임스페이스의 Pod 목록"""
    try:
        core_v1, _, custom = get_k8s_clients()
        pods = core_v1.list_namespaced_pod(namespace)

        # Pod 메트릭 조회 시도
        pod_metrics = {}
        try:
            metrics = custom.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods"
            )
            for item in metrics.get("items", []):
                name = item['metadata']['name']
                containers = item.get("containers", [])
                if containers:
                    cpu_usage = sum(parse_cpu(c.get("usage", {}).get("cpu", "0")) for c in containers)
                    memory_usage = sum(parse_memory(c.get("usage", {}).get("memory", "0")) for c in containers)
                    pod_metrics[name] = {"cpu": cpu_usage, "memory": memory_usage}
        except:
            pass

        result = []
        for pod in pods.items:
            metrics = pod_metrics.get(pod.metadata.name, {})

            result.append({
                "name": pod.metadata.name,
                "namespace": namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "ip": pod.status.pod_ip,
                "cpu_usage": metrics.get("cpu", 0),
                "memory_usage": metrics.get("memory", 0),
                "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
            })

        return {"namespace": namespace, "pods": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 노드 리소스 사용률 API
# ============================================

def parse_cpu(cpu_str: str) -> float:
    """CPU 문자열을 밀리코어로 변환"""
    if not cpu_str:
        return 0
    if cpu_str.endswith('n'):
        return float(cpu_str[:-1]) / 1000000
    if cpu_str.endswith('u'):
        return float(cpu_str[:-1]) / 1000
    if cpu_str.endswith('m'):
        return float(cpu_str[:-1])
    return float(cpu_str) * 1000


def parse_memory(mem_str: str) -> int:
    """메모리 문자열을 MB로 변환"""
    if not mem_str:
        return 0
    if mem_str.endswith('Ki'):
        return int(float(mem_str[:-2]) / 1024)
    if mem_str.endswith('Mi'):
        return int(float(mem_str[:-2]))
    if mem_str.endswith('Gi'):
        return int(float(mem_str[:-2]) * 1024)
    if mem_str.endswith('Ti'):
        return int(float(mem_str[:-2]) * 1024 * 1024)
    if mem_str.endswith('K'):
        return int(float(mem_str[:-1]) / 1024)
    if mem_str.endswith('M'):
        return int(float(mem_str[:-1]))
    if mem_str.endswith('G'):
        return int(float(mem_str[:-1]) * 1024)
    return int(float(mem_str) / (1024 * 1024))


def get_actual_gpu_usage() -> dict:
    """nvidia-smi를 통해 실제 GPU 사용 상태 확인 (500MB 이상 사용 시 사용 중으로 간주)"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,memory.used', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )

        gpu_status = {}
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                idx = parts[0].strip()
                mem_mb = int(parts[1].strip())
                gpu_status[int(idx)] = mem_mb > 500  # 500MB 이상 사용 중으로 간주

        return gpu_status
    except Exception:
        return {}


def get_gpu_detailed_metrics() -> list:
    """nvidia-smi를 통해 각 GPU의 상세 메트릭 수집"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu,utilization.memory',
             '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )

        gpu_metrics = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 6:
                gpu_metrics.append({
                    'index': int(parts[0]),
                    'name': parts[1],
                    'memory_used_mb': int(parts[2]),
                    'memory_total_mb': int(parts[3]),
                    'utilization_percent': int(parts[4]),
                    'memory_utilization_percent': int(parts[5])
                })

        return gpu_metrics
    except Exception:
        return []


def get_pod_gpu_mapping():
    """Pod이 요청한 GPU 정보를 포드별로 매핑"""
    try:
        core_v1 = get_k8s_clients()[0]
        pods = core_v1.list_pod_for_all_namespaces()
        pod_gpu_map = {}  # pod_name -> {"namespace": ns, "gpu_count": n, "container": c}

        for pod in pods.items:
            if pod.status.phase not in ["Running", "Pending"]:
                continue
            pod_name = pod.metadata.name
            namespace = pod.metadata.namespace

            for container in (pod.spec.containers or []):
                resources = container.resources or {}
                requests = resources.requests or {}
                gpu_req = requests.get("nvidia.com/gpu", "0")
                try:
                    gpu_count = int(gpu_req) if gpu_req else 0
                    if gpu_count > 0:
                        pod_gpu_map[f"{namespace}/{pod_name}/{container.name}"] = {
                            "namespace": namespace,
                            "pod": pod_name,
                            "container": container.name,
                            "gpu_count": gpu_count,
                            "node": pod.spec.node_name or ""
                        }
                except:
                    pass

        return pod_gpu_map
    except Exception:
        return {}


@app.get("/api/nodes/metrics")
async def get_all_nodes_metrics():
    """모든 노드의 리소스 사용률 (requests/limits 포함)"""
    try:
        core_v1, _, custom = get_k8s_clients()

        # 노드 정보 조회
        nodes = core_v1.list_node()
        node_info = {}
        for node in nodes.items:
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}
            labels = node.metadata.labels or {}

            # CPU 용량 (코어 수)
            cpu_capacity = capacity.get("cpu", "0")
            if cpu_capacity.endswith('m'):
                cpu_capacity_cores = float(cpu_capacity[:-1]) / 1000
            else:
                cpu_capacity_cores = float(cpu_capacity)

            # 메모리 용량 (MB)
            mem_capacity = parse_memory(capacity.get("memory", "0"))

            # GPU 정보
            gpu_capacity = int(capacity.get("nvidia.com/gpu", "0"))
            gpu_type = labels.get("nvidia.com/gpu.product", labels.get("gpu-type", ""))

            node_info[node.metadata.name] = {
                "cpu_capacity": cpu_capacity_cores * 1000,  # 밀리코어
                "memory_capacity": mem_capacity,
                "gpu_capacity": gpu_capacity,
                "gpu_type": gpu_type
            }

        # Pod의 GPU 매핑 정보 수집
        pod_gpu_map = get_pod_gpu_mapping()

        # 노드별 리소스 예약(requests/limits) 계산
        pods = core_v1.list_pod_for_all_namespaces()
        node_requests = {}
        node_limits = {}
        node_gpu_usage = {}
        node_pod_gpu_list = {}  # 노드별 GPU 사용 Pod 목록

        for pod in pods.items:
            if pod.status.phase not in ["Running", "Pending"]:
                continue
            node_name = pod.spec.node_name or ""
            if node_name not in node_requests:
                node_requests[node_name] = {"cpu": 0, "memory": 0, "gpu": 0}
                node_limits[node_name] = {"cpu": 0, "memory": 0, "gpu": 0}
                node_gpu_usage[node_name] = 0
                node_pod_gpu_list[node_name] = []

            for container in (pod.spec.containers or []):
                resources = container.resources or {}
                requests = resources.requests or {}
                limits = resources.limits or {}

                # CPU requests/limits
                cpu_req = requests.get("cpu", "0")
                cpu_lim = limits.get("cpu", "0")
                node_requests[node_name]["cpu"] += parse_cpu(cpu_req)
                node_limits[node_name]["cpu"] += parse_cpu(cpu_lim)

                # Memory requests/limits
                mem_req = requests.get("memory", "0")
                mem_lim = requests.get("memory", "0")
                node_requests[node_name]["memory"] += parse_memory(mem_req)
                node_limits[node_name]["memory"] += parse_memory(mem_lim)

                # GPU requests
                gpu_req = requests.get("nvidia.com/gpu", "0")
                gpu_lim = limits.get("nvidia.com/gpu", "0")
                try:
                    gpu_count = int(gpu_req) if gpu_req else 0
                    node_requests[node_name]["gpu"] += gpu_count
                    # GPU 사용량은 나중에 실제 nvidia-smi 기반으로 계산

                    # GPU 사용 Pod 목록에 추가
                    if gpu_count > 0:
                        node_pod_gpu_list[node_name].append({
                            "namespace": pod.metadata.namespace,
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "gpu_count": gpu_count
                        })
                except:
                    pass

        # 실제 GPU 사용 상태 확인 (nvidia-smi)
        actual_gpu_usage = get_actual_gpu_usage()

        # 실제 사용 중인 GPU 개수 계산 (500MB 이상)
        for node_name in node_requests:
            node_gpu_usage[node_name] = sum(1 for v in actual_gpu_usage.values() if v)

        # GPU 상세 메트릭 수집 (collector에서)
        gpu_metrics_list = await get_gpu_metrics_from_collectors()

        # 노드별로 GPU 메트릭 그룹핑
        gpu_metrics_by_node = {}
        if gpu_metrics_list:
            for gpu in gpu_metrics_list:
                node = gpu.get('node', '')
                if node not in gpu_metrics_by_node:
                    gpu_metrics_by_node[node] = []
                gpu_metrics_by_node[node].append(gpu)

        # 메트릭 조회
        result = []
        try:
            metrics = custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )

            for item in metrics.get("items", []):
                name = item["metadata"]["name"]
                usage = item.get("usage", {})

                cpu_usage = parse_cpu(usage.get("cpu", "0"))
                memory_usage = parse_memory(usage.get("memory", "0"))

                info = node_info.get(name, {})
                cpu_capacity = info.get("cpu_capacity", 1)
                memory_capacity = info.get("memory_capacity", 1)
                gpu_capacity = info.get("gpu_capacity", 0)
                gpu_type = info.get("gpu_type", "")

                req = node_requests.get(name, {"cpu": 0, "memory": 0, "gpu": 0})
                lim = node_limits.get(name, {"cpu": 0, "memory": 0, "gpu": 0})
                gpu_used = node_gpu_usage.get(name, 0)

                # 실제 GPU 사용 상태 배열 생성
                gpu_status_array = [actual_gpu_usage.get(i, False) for i in range(gpu_capacity)]

                # GPU 상세 메트릭 추가 (해당 노드에 GPU가 있는 경우)
                gpu_details = []
                if gpu_capacity > 0:
                    node_gpus = gpu_metrics_by_node.get(name, [])
                    if node_gpus:
                        for gpu_metric in node_gpus:
                            gpu_index = gpu_metric.get('index', 0)
                            gpu_details.append({
                                'index': gpu_index,
                                'name': gpu_metric.get('name', gpu_type),
                                'memory_used': gpu_metric.get('memory_used', 0),
                                'memory_total': gpu_metric.get('memory_total', 0),
                                'memory_percent': round(gpu_metric.get('memory_used', 0) / gpu_metric.get('memory_total', 1) * 100, 1) if gpu_metric.get('memory_total', 0) > 0 else 0,
                                'utilization_percent': gpu_metric.get('utilization', 0),
                                'in_use': actual_gpu_usage.get(gpu_index, False)
                            })

                result.append({
                    "name": name,
                    "cpu_usage": round(cpu_usage, 1),
                    "cpu_capacity": round(cpu_capacity, 1),
                    "cpu_percent": round(cpu_usage / cpu_capacity * 100, 1) if cpu_capacity > 0 else 0,
                    "cpu_requests": round(req["cpu"], 1),
                    "cpu_limits": round(lim["cpu"], 1),
                    "cpu_requests_percent": round(req["cpu"] / cpu_capacity * 100, 1) if cpu_capacity > 0 else 0,
                    "memory_usage": memory_usage,
                    "memory_capacity": memory_capacity,
                    "memory_percent": round(memory_usage / memory_capacity * 100, 1) if memory_capacity > 0 else 0,
                    "memory_requests": req["memory"],
                    "memory_limits": lim["memory"],
                    "memory_requests_percent": round(req["memory"] / memory_capacity * 100, 1) if memory_capacity > 0 else 0,
                    "gpu_capacity": gpu_capacity,
                    "gpu_used": gpu_used,
                    "gpu_status_array": gpu_status_array,
                    "gpu_details": gpu_details,
                    "gpu_type": gpu_type,
                    "gpu_pod_list": node_pod_gpu_list.get(name, []),
                    "timestamp": item.get("timestamp")
                })
        except ApiException as e:
            # metrics-server가 없는 경우
            for name, info in node_info.items():
                req = node_requests.get(name, {"cpu": 0, "memory": 0, "gpu": 0})
                lim = node_limits.get(name, {"cpu": 0, "memory": 0, "gpu": 0})
                gpu_used = node_gpu_usage.get(name, 0)
                cpu_capacity = info.get("cpu_capacity", 0)
                memory_capacity = info.get("memory_capacity", 0)
                gpu_capacity = info.get("gpu_capacity", 0)

                # 실제 GPU 사용 상태 배열 생성
                gpu_status_array = [actual_gpu_usage.get(i, False) for i in range(gpu_capacity)]

                # GPU 상세 메트릭 추가 (해당 노드에 GPU가 있는 경우)
                gpu_details = []
                if gpu_capacity > 0:
                    node_gpus = gpu_metrics_by_node.get(name, [])
                    if node_gpus:
                        for gpu_metric in node_gpus:
                            gpu_index = gpu_metric.get('index', 0)
                            gpu_details.append({
                                'index': gpu_index,
                                'name': gpu_metric.get('name', info.get("gpu_type", "")),
                                'memory_used': gpu_metric.get('memory_used', 0),
                                'memory_total': gpu_metric.get('memory_total', 0),
                                'memory_percent': round(gpu_metric.get('memory_used', 0) / gpu_metric.get('memory_total', 1) * 100, 1) if gpu_metric.get('memory_total', 0) > 0 else 0,
                                'utilization_percent': gpu_metric.get('utilization', 0),
                                'in_use': actual_gpu_usage.get(gpu_index, False)
                            })

                result.append({
                    "name": name,
                    "cpu_usage": 0,
                    "cpu_capacity": cpu_capacity,
                    "cpu_percent": 0,
                    "cpu_requests": round(req["cpu"], 1),
                    "cpu_limits": round(lim["cpu"], 1),
                    "cpu_requests_percent": round(req["cpu"] / cpu_capacity * 100, 1) if cpu_capacity > 0 else 0,
                    "memory_usage": 0,
                    "memory_capacity": memory_capacity,
                    "memory_percent": 0,
                    "memory_requests": req["memory"],
                    "memory_limits": lim["memory"],
                    "memory_requests_percent": round(req["memory"] / memory_capacity * 100, 1) if memory_capacity > 0 else 0,
                    "gpu_capacity": gpu_capacity,
                    "gpu_used": gpu_used,
                    "gpu_status_array": gpu_status_array,
                    "gpu_details": gpu_details,
                    "gpu_type": info.get("gpu_type", ""),
                    "gpu_pod_list": node_pod_gpu_list.get(name, []),
                    "message": "metrics-server not available"
                })

        return {"nodes": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 클러스터 요약 API (확장)
# ============================================

@app.get("/api/cluster/summary")
async def get_cluster_summary():
    """클러스터 전체 요약 (리소스 사용률 포함)"""
    try:
        core_v1, apps_v1, custom = get_k8s_clients()

        # 노드 정보
        nodes = core_v1.list_node()
        node_count = len(nodes.items)
        ready_nodes = sum(1 for n in nodes.items
                        if any(c.type == "Ready" and c.status == "True"
                              for c in n.status.conditions))

        # 전체 용량 계산
        total_cpu_capacity = 0
        total_memory_capacity = 0
        total_gpu_count = 0
        gpu_by_type = {}  # GPU 타입별 개수

        for node in nodes.items:
            capacity = node.status.capacity or {}
            labels = node.metadata.labels or {}

            cpu = capacity.get("cpu", "0")
            if cpu.endswith('m'):
                total_cpu_capacity += float(cpu[:-1]) / 1000
            else:
                total_cpu_capacity += float(cpu)

            total_memory_capacity += parse_memory(capacity.get("memory", "0"))

            # GPU 정보 - nvidia.com/gpu 리소스에서 가져옴
            gpu_capacity = capacity.get("nvidia.com/gpu", "0")
            try:
                gpu_count = int(gpu_capacity)
            except:
                gpu_count = 0

            if gpu_count > 0:
                total_gpu_count += gpu_count
                # GPU 타입 가져오기
                gpu_type = labels.get("nvidia.com/gpu.product",
                           labels.get("gpu-type", "NVIDIA GPU"))
                # 타입별로 그룹화
                if gpu_type in gpu_by_type:
                    gpu_by_type[gpu_type] += gpu_count
                else:
                    gpu_by_type[gpu_type] = gpu_count

        # Pod 정보
        pods = core_v1.list_pod_for_all_namespaces()
        running_pods = sum(1 for p in pods.items if p.status.phase == "Running")
        pending_pods = sum(1 for p in pods.items if p.status.phase == "Pending")
        failed_pods = sum(1 for p in pods.items if p.status.phase == "Failed")

        # 네임스페이스 수
        namespaces = core_v1.list_namespace()

        # 리소스 사용률 조회
        total_cpu_usage = 0
        total_memory_usage = 0
        try:
            metrics = custom.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="nodes"
            )
            for item in metrics.get("items", []):
                usage = item.get("usage", {})
                total_cpu_usage += parse_cpu(usage.get("cpu", "0"))
                total_memory_usage += parse_memory(usage.get("memory", "0"))
        except:
            pass

        return {
            "status": "healthy" if ready_nodes == node_count else "degraded",
            "nodes": {
                "total": node_count,
                "ready": ready_nodes
            },
            "pods": {
                "total": len(pods.items),
                "running": running_pods,
                "pending": pending_pods,
                "failed": failed_pods
            },
            "namespaces": len(namespaces.items),
            "resources": {
                "cpu": {
                    "usage": round(total_cpu_usage, 1),
                    "capacity": round(total_cpu_capacity * 1000, 1),
                    "percent": round(total_cpu_usage / (total_cpu_capacity * 1000) * 100, 1) if total_cpu_capacity > 0 else 0
                },
                "memory": {
                    "usage": total_memory_usage,
                    "capacity": total_memory_capacity,
                    "percent": round(total_memory_usage / total_memory_capacity * 100, 1) if total_memory_capacity > 0 else 0
                },
                "gpu": {
                    "total": total_gpu_count,
                    "by_type": gpu_by_type
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 헬스체크 (routers/health.py로 이전됨)
# ============================================
# /api/health, /api/k8s/health는 health_router에서 처리


# ============================================
# LLM 벤치마크 API
# ============================================

import time
import uuid
from datetime import datetime
from typing import Dict, Any

# 벤치마크 결과 저장 (메모리 내, 실제로는 DB 사용 권장)
benchmark_results: Dict[str, Any] = {}
benchmark_configs: Dict[str, Any] = {}


class BenchmarkConfig(BaseModel):
    name: str
    model: str = "facebook/opt-125m"
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    num_requests: int = 10
    concurrent_requests: int = 1
    test_prompts: List[str] = [
        "Explain quantum computing in simple terms.",
        "Write a short poem about artificial intelligence.",
        "What are the benefits of renewable energy?",
        "Describe the process of photosynthesis.",
        "How does machine learning work?"
    ]
    # vLLM 런타임 파라미터
    gpu_memory_utilization: Optional[float] = None  # 0.1 ~ 0.95
    quantization: Optional[str] = None  # awq, gptq, squeezellm, None
    tensor_parallel_size: Optional[int] = None  # 1, 2, 4, 8
    max_model_len: Optional[int] = None  # 컨텍스트 길이
    dtype: Optional[str] = None  # auto, float16, bfloat16, float32
    enforce_eager: Optional[bool] = None  # Eager 모드 강제


class BenchmarkRun(BaseModel):
    config_id: str
    custom_prompts: Optional[List[str]] = None


class AutoRangeBenchmark(BaseModel):
    """자동 범위 벤치마크 설정"""
    name: str
    model: str = "facebook/opt-125m"
    # 범위 설정 (min, max, step)
    max_tokens_range: Optional[List[int]] = None  # [min, max, step] e.g. [32, 512, 64]
    concurrent_range: Optional[List[int]] = None  # [min, max, step] e.g. [1, 8, 1]
    temperature_range: Optional[List[float]] = None  # [min, max, step] e.g. [0.1, 1.0, 0.3]
    batch_size_range: Optional[List[int]] = None  # [min, max, step] e.g. [1, 32, 4]
    # 고정 파라미터
    num_requests: int = 10
    test_prompts: List[str] = [
        "Explain quantum computing in simple terms.",
        "Write a short poem about artificial intelligence.",
        "What are the benefits of renewable energy?"
    ]
    # vLLM 파라미터
    gpu_memory_utilization: Optional[float] = None
    quantization: Optional[str] = None


# 자동 범위 벤치마크 결과 저장
auto_benchmark_sessions: Dict[str, Any] = {}


# 일반적인 파라미터 범위 기본값
DEFAULT_RANGES = {
    "max_tokens": {"min": 32, "max": 512, "step": 64, "default": [32, 128, 256, 512]},
    "concurrent_requests": {"min": 1, "max": 16, "step": 2, "default": [1, 2, 4, 8, 16]},
    "temperature": {"min": 0.1, "max": 1.0, "step": 0.3, "default": [0.1, 0.4, 0.7, 1.0]},
    "batch_size": {"min": 1, "max": 32, "step": 4, "default": [1, 4, 8, 16, 32]},
    "gpu_memory_utilization": {"min": 0.5, "max": 0.95, "step": 0.15, "default": [0.5, 0.7, 0.85, 0.95]},
}


@app.get("/api/benchmark/configs")
async def list_benchmark_configs():
    """저장된 벤치마크 설정 목록"""
    configs = []
    for config_id, config in benchmark_configs.items():
        configs.append({
            "id": config_id,
            **config,
            "created_at": config.get("created_at")
        })
    return {"configs": configs, "total": len(configs)}


@app.post("/api/benchmark/configs")
async def create_benchmark_config(config: BenchmarkConfig):
    """벤치마크 설정 생성"""
    config_id = str(uuid.uuid4())[:8]
    benchmark_configs[config_id] = {
        "name": config.name,
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "num_requests": config.num_requests,
        "concurrent_requests": config.concurrent_requests,
        "test_prompts": config.test_prompts,
        # vLLM 런타임 파라미터
        "gpu_memory_utilization": config.gpu_memory_utilization,
        "quantization": config.quantization,
        "tensor_parallel_size": config.tensor_parallel_size,
        "max_model_len": config.max_model_len,
        "dtype": config.dtype,
        "enforce_eager": config.enforce_eager,
        "created_at": datetime.now().isoformat()
    }
    return {"id": config_id, "message": f"벤치마크 설정 '{config.name}'이 생성되었습니다"}


@app.delete("/api/benchmark/configs/{config_id}")
async def delete_benchmark_config(config_id: str):
    """벤치마크 설정 삭제"""
    if config_id not in benchmark_configs:
        raise HTTPException(status_code=404, detail="설정을 찾을 수 없습니다")
    del benchmark_configs[config_id]
    return {"success": True, "message": "설정이 삭제되었습니다"}


@app.get("/api/benchmark/results")
async def list_benchmark_results():
    """벤치마크 결과 목록"""
    results = []
    for result_id, result in benchmark_results.items():
        results.append({
            "id": result_id,
            "config_name": result.get("config_name"),
            "model": result.get("model"),
            "status": result.get("status"),
            "started_at": result.get("started_at"),
            "completed_at": result.get("completed_at"),
            "summary": result.get("summary")
        })
    # 최신 순으로 정렬
    results.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return {"results": results, "total": len(results)}


@app.get("/api/benchmark/results/{result_id}")
async def get_benchmark_result(result_id: str):
    """벤치마크 결과 상세 조회"""
    if result_id not in benchmark_results:
        raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
    return benchmark_results[result_id]


@app.delete("/api/benchmark/results/{result_id}")
async def delete_benchmark_result(result_id: str):
    """벤치마크 결과 삭제"""
    if result_id not in benchmark_results:
        raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
    del benchmark_results[result_id]
    return {"success": True, "message": "결과가 삭제되었습니다"}


async def run_single_request(client: httpx.AsyncClient, endpoint: str, prompt: str,
                             model: str, max_tokens: int, temperature: float, top_p: float):
    """단일 추론 요청 실행"""
    start_time = time.time()
    error = None
    output_tokens = 0
    response_text = ""

    try:
        # vLLM OpenAI-compatible API 호출
        response = await client.post(
            f"{endpoint}/v1/completions",
            json={
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            },
            timeout=120.0
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0].get("text", "")
                output_tokens = data.get("usage", {}).get("completion_tokens", len(response_text.split()))
        else:
            error = f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        error = str(e)

    end_time = time.time()
    latency = end_time - start_time

    return {
        "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
        "response": response_text[:200] + "..." if len(response_text) > 200 else response_text,
        "latency": round(latency, 3),
        "output_tokens": output_tokens,
        "tokens_per_second": round(output_tokens / latency, 2) if latency > 0 and output_tokens > 0 else 0,
        "success": error is None,
        "error": error
    }


@app.post("/api/benchmark/run")
async def run_benchmark(run_config: BenchmarkRun):
    """벤치마크 실행"""
    if run_config.config_id not in benchmark_configs:
        raise HTTPException(status_code=404, detail="설정을 찾을 수 없습니다")

    config = benchmark_configs[run_config.config_id]
    result_id = str(uuid.uuid4())[:8]

    # 결과 초기화
    benchmark_results[result_id] = {
        "id": result_id,
        "config_id": run_config.config_id,
        "config_name": config["name"],
        "model": config["model"],
        "settings": {
            "max_tokens": config["max_tokens"],
            "temperature": config["temperature"],
            "top_p": config["top_p"],
            "num_requests": config["num_requests"],
            "concurrent_requests": config["concurrent_requests"]
        },
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "requests": [],
        "summary": None
    }

    # vLLM 서비스 엔드포인트
    vllm_endpoint = "http://vllm-server.ai-workloads.svc.cluster.local:8000"

    # 테스트 프롬프트
    prompts = run_config.custom_prompts or config["test_prompts"]

    # 벤치마크 실행
    all_results = []
    try:
        async with httpx.AsyncClient() as client:
            # 먼저 vLLM 서비스 상태 확인
            try:
                health_check = await client.get(f"{vllm_endpoint}/health", timeout=10.0)
                if health_check.status_code != 200:
                    raise Exception("vLLM service not healthy")
            except Exception as e:
                benchmark_results[result_id]["status"] = "failed"
                benchmark_results[result_id]["error"] = f"vLLM 서비스에 연결할 수 없습니다: {str(e)}"
                benchmark_results[result_id]["completed_at"] = datetime.now().isoformat()
                return {"result_id": result_id, "status": "failed", "error": str(e)}

            # 요청 실행
            for i in range(config["num_requests"]):
                prompt = prompts[i % len(prompts)]

                if config["concurrent_requests"] > 1:
                    # 동시 요청
                    tasks = [
                        run_single_request(
                            client, vllm_endpoint, prompt,
                            config["model"], config["max_tokens"],
                            config["temperature"], config["top_p"]
                        )
                        for _ in range(min(config["concurrent_requests"], config["num_requests"] - i))
                    ]
                    results = await asyncio.gather(*tasks)
                    all_results.extend(results)
                    i += len(tasks) - 1
                else:
                    # 순차 요청
                    result = await run_single_request(
                        client, vllm_endpoint, prompt,
                        config["model"], config["max_tokens"],
                        config["temperature"], config["top_p"]
                    )
                    all_results.append(result)

        # 결과 요약
        successful = [r for r in all_results if r["success"]]
        failed = [r for r in all_results if not r["success"]]

        if successful:
            latencies = [r["latency"] for r in successful]
            tokens_per_sec = [r["tokens_per_second"] for r in successful if r["tokens_per_second"] > 0]

            summary = {
                "total_requests": len(all_results),
                "successful_requests": len(successful),
                "failed_requests": len(failed),
                "success_rate": round(len(successful) / len(all_results) * 100, 1),
                "avg_latency": round(sum(latencies) / len(latencies), 3),
                "min_latency": round(min(latencies), 3),
                "max_latency": round(max(latencies), 3),
                "p50_latency": round(sorted(latencies)[len(latencies)//2], 3),
                "p95_latency": round(sorted(latencies)[int(len(latencies)*0.95)], 3) if len(latencies) >= 20 else None,
                "avg_tokens_per_second": round(sum(tokens_per_sec) / len(tokens_per_sec), 2) if tokens_per_sec else 0,
                "total_output_tokens": sum(r["output_tokens"] for r in successful)
            }
        else:
            summary = {
                "total_requests": len(all_results),
                "successful_requests": 0,
                "failed_requests": len(failed),
                "success_rate": 0,
                "error": "모든 요청이 실패했습니다"
            }

        benchmark_results[result_id]["requests"] = all_results
        benchmark_results[result_id]["summary"] = summary
        benchmark_results[result_id]["status"] = "completed"
        benchmark_results[result_id]["completed_at"] = datetime.now().isoformat()

        return {
            "result_id": result_id,
            "status": "completed",
            "summary": summary
        }

    except Exception as e:
        benchmark_results[result_id]["status"] = "failed"
        benchmark_results[result_id]["error"] = str(e)
        benchmark_results[result_id]["completed_at"] = datetime.now().isoformat()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/benchmark/compare")
async def compare_benchmark_results(result_ids: str):
    """여러 벤치마크 결과 비교"""
    ids = result_ids.split(",")
    comparison = []

    for result_id in ids:
        result_id = result_id.strip()
        if result_id in benchmark_results:
            result = benchmark_results[result_id]
            comparison.append({
                "id": result_id,
                "config_name": result.get("config_name"),
                "model": result.get("model"),
                "settings": result.get("settings"),
                "summary": result.get("summary"),
                "completed_at": result.get("completed_at")
            })

    return {"comparison": comparison, "total": len(comparison)}


@app.get("/api/benchmark/default-ranges")
async def get_default_ranges():
    """자동 범위 벤치마크를 위한 기본 범위값 조회"""
    return {"ranges": DEFAULT_RANGES}


@app.post("/api/benchmark/auto-range")
async def run_auto_range_benchmark(config: AutoRangeBenchmark, background_tasks: BackgroundTasks):
    """자동 범위 벤치마크 실행 - 파라미터 범위를 자동으로 순회하며 테스트"""
    session_id = str(uuid.uuid4())[:8]

    # 범위 값 생성
    def generate_range(range_config, default_key):
        if range_config and len(range_config) >= 3:
            min_val, max_val, step = range_config[0], range_config[1], range_config[2]
            values = []
            current = min_val
            while current <= max_val:
                values.append(current)
                current += step
            return values
        return DEFAULT_RANGES[default_key]["default"]

    # 테스트할 파라미터 조합 생성
    max_tokens_values = generate_range(config.max_tokens_range, "max_tokens") if config.max_tokens_range else [128]
    concurrent_values = generate_range(config.concurrent_range, "concurrent_requests") if config.concurrent_range else [1]
    temperature_values = generate_range(config.temperature_range, "temperature") if config.temperature_range else [0.7]

    # 테스트 조합 생성 (모든 조합 또는 주요 조합만)
    test_combinations = []

    # 각 파라미터별 변화 테스트 (다른 파라미터는 기본값 유지)
    base_max_tokens = max_tokens_values[len(max_tokens_values)//2] if max_tokens_values else 128
    base_concurrent = concurrent_values[0] if concurrent_values else 1
    base_temperature = temperature_values[len(temperature_values)//2] if temperature_values else 0.7

    # max_tokens 변화 테스트
    for mt in max_tokens_values:
        test_combinations.append({
            "max_tokens": mt,
            "concurrent_requests": base_concurrent,
            "temperature": base_temperature,
            "test_type": "max_tokens"
        })

    # concurrent_requests 변화 테스트
    for cr in concurrent_values:
        if cr == base_concurrent:
            continue
        test_combinations.append({
            "max_tokens": base_max_tokens,
            "concurrent_requests": cr,
            "temperature": base_temperature,
            "test_type": "concurrent"
        })

    # temperature 변화 테스트
    for temp in temperature_values:
        if abs(temp - base_temperature) < 0.01:
            continue
        test_combinations.append({
            "max_tokens": base_max_tokens,
            "concurrent_requests": base_concurrent,
            "temperature": temp,
            "test_type": "temperature"
        })

    # 세션 초기화
    auto_benchmark_sessions[session_id] = {
        "id": session_id,
        "name": config.name,
        "model": config.model,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "total_tests": len(test_combinations),
        "completed_tests": 0,
        "current_test": None,
        "test_combinations": test_combinations,
        "results": [],
        "vllm_params": {
            "gpu_memory_utilization": config.gpu_memory_utilization,
            "quantization": config.quantization
        }
    }

    # 백그라운드에서 실행
    background_tasks.add_task(execute_auto_range_benchmark, session_id, config)

    return {
        "session_id": session_id,
        "status": "started",
        "total_tests": len(test_combinations),
        "message": f"자동 범위 벤치마크가 시작되었습니다. {len(test_combinations)}개의 테스트를 실행합니다."
    }


async def execute_auto_range_benchmark(session_id: str, config: AutoRangeBenchmark):
    """자동 범위 벤치마크 실행 (백그라운드)"""
    session = auto_benchmark_sessions.get(session_id)
    if not session:
        return

    vllm_endpoint = "http://vllm-server.ai-workloads.svc.cluster.local:8000"

    async with httpx.AsyncClient() as client:
        # vLLM 상태 확인
        try:
            health_check = await client.get(f"{vllm_endpoint}/health", timeout=10.0)
            if health_check.status_code != 200:
                session["status"] = "failed"
                session["error"] = "vLLM 서비스가 응답하지 않습니다"
                session["completed_at"] = datetime.now().isoformat()
                return
        except Exception as e:
            session["status"] = "failed"
            session["error"] = f"vLLM 연결 실패: {str(e)}"
            session["completed_at"] = datetime.now().isoformat()
            return

        # 각 테스트 조합 실행
        for i, combo in enumerate(session["test_combinations"]):
            session["current_test"] = combo
            session["completed_tests"] = i

            test_result = {
                "params": combo,
                "started_at": datetime.now().isoformat(),
                "requests": [],
                "summary": None
            }

            all_results = []
            try:
                for j in range(config.num_requests):
                    prompt = config.test_prompts[j % len(config.test_prompts)]

                    start_time = time.time()
                    try:
                        response = await client.post(
                            f"{vllm_endpoint}/v1/completions",
                            json={
                                "model": config.model,
                                "prompt": prompt,
                                "max_tokens": combo["max_tokens"],
                                "temperature": combo["temperature"],
                                "top_p": 0.9
                            },
                            timeout=120.0
                        )

                        end_time = time.time()
                        latency = end_time - start_time

                        if response.status_code == 200:
                            data = response.json()
                            output_tokens = data.get("usage", {}).get("completion_tokens", 0)
                            all_results.append({
                                "latency": latency,
                                "output_tokens": output_tokens,
                                "tokens_per_second": output_tokens / latency if latency > 0 else 0,
                                "success": True
                            })
                        else:
                            all_results.append({
                                "latency": latency,
                                "success": False,
                                "error": f"HTTP {response.status_code}"
                            })
                    except Exception as e:
                        all_results.append({
                            "latency": time.time() - start_time,
                            "success": False,
                            "error": str(e)
                        })

                # 결과 요약
                successful = [r for r in all_results if r.get("success")]
                if successful:
                    latencies = [r["latency"] for r in successful]
                    tokens_per_sec = [r["tokens_per_second"] for r in successful if r.get("tokens_per_second", 0) > 0]

                    test_result["summary"] = {
                        "total_requests": len(all_results),
                        "successful_requests": len(successful),
                        "success_rate": round(len(successful) / len(all_results) * 100, 1),
                        "avg_latency": round(sum(latencies) / len(latencies), 3),
                        "min_latency": round(min(latencies), 3),
                        "max_latency": round(max(latencies), 3),
                        "avg_tokens_per_second": round(sum(tokens_per_sec) / len(tokens_per_sec), 2) if tokens_per_sec else 0
                    }
                else:
                    test_result["summary"] = {
                        "total_requests": len(all_results),
                        "successful_requests": 0,
                        "success_rate": 0,
                        "error": "모든 요청 실패"
                    }

                test_result["completed_at"] = datetime.now().isoformat()
                session["results"].append(test_result)

            except Exception as e:
                test_result["error"] = str(e)
                test_result["completed_at"] = datetime.now().isoformat()
                session["results"].append(test_result)

        # 완료
        session["status"] = "completed"
        session["completed_tests"] = len(session["test_combinations"])
        session["current_test"] = None
        session["completed_at"] = datetime.now().isoformat()

        # 최적의 파라미터 찾기
        best_result = None
        best_tps = 0
        for result in session["results"]:
            if result.get("summary") and result["summary"].get("avg_tokens_per_second", 0) > best_tps:
                best_tps = result["summary"]["avg_tokens_per_second"]
                best_result = result

        session["best_params"] = best_result["params"] if best_result else None
        session["best_performance"] = best_result["summary"] if best_result else None


@app.get("/api/benchmark/auto-range/{session_id}")
async def get_auto_range_status(session_id: str):
    """자동 범위 벤치마크 상태 조회"""
    if session_id not in auto_benchmark_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return auto_benchmark_sessions[session_id]


@app.get("/api/benchmark/auto-range")
async def list_auto_range_sessions():
    """자동 범위 벤치마크 세션 목록"""
    sessions = []
    for session_id, session in auto_benchmark_sessions.items():
        sessions.append({
            "id": session_id,
            "name": session.get("name"),
            "model": session.get("model"),
            "status": session.get("status"),
            "total_tests": session.get("total_tests"),
            "completed_tests": session.get("completed_tests"),
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at"),
            "best_params": session.get("best_params"),
            "best_performance": session.get("best_performance")
        })
    sessions.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return {"sessions": sessions, "total": len(sessions)}


@app.delete("/api/benchmark/auto-range/{session_id}")
async def delete_auto_range_session(session_id: str):
    """자동 범위 벤치마크 세션 삭제"""
    if session_id not in auto_benchmark_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    del auto_benchmark_sessions[session_id]
    return {"success": True, "message": "세션이 삭제되었습니다"}


# ============================================
# 전체 벤치마크 사이클 API (모델 배포 -> 벤치마크 -> 분석)
# ============================================

class FullBenchmarkCycle(BaseModel):
    """전체 벤치마크 사이클 설정"""
    name: str
    model: str  # HuggingFace 모델 ID (예: facebook/opt-125m, meta-llama/Llama-2-7b-hf)
    # vLLM 배포 파라미터
    gpu_memory_utilization: float = 0.9
    max_model_len: Optional[int] = None
    quantization: Optional[str] = None  # awq, gptq, squeezellm
    tensor_parallel_size: int = 1
    dtype: str = "auto"  # auto, float16, bfloat16
    enforce_eager: bool = False
    # 벤치마크 파라미터 범위
    max_tokens_range: List[int] = [64, 256, 512]  # 테스트할 max_tokens 값들
    concurrent_range: List[int] = [1, 2, 4]  # 테스트할 동시성 값들
    num_requests_per_test: int = 10
    # 품질 평가용 프롬프트
    quality_prompts: List[str] = [
        "Explain the theory of relativity in simple terms.",
        "Write a short story about a robot learning to paint.",
        "What are the main causes of climate change?",
        "Describe the process of photosynthesis step by step.",
        "Compare and contrast machine learning and deep learning."
    ]


# 전체 사이클 세션 저장
full_cycle_sessions: Dict[str, Any] = {}


@app.post("/api/benchmark/full-cycle")
async def start_full_benchmark_cycle(config: FullBenchmarkCycle, background_tasks: BackgroundTasks):
    """전체 벤치마크 사이클 시작: 모델 배포 -> 부팅 시간 측정 -> 벤치마크 -> 품질 평가 -> 분석"""
    session_id = str(uuid.uuid4())[:8]

    # 테스트 조합 생성
    test_matrix = []
    for max_tokens in config.max_tokens_range:
        for concurrent in config.concurrent_range:
            test_matrix.append({
                "max_tokens": max_tokens,
                "concurrent_requests": concurrent
            })

    # 세션 초기화
    full_cycle_sessions[session_id] = {
        "id": session_id,
        "name": config.name,
        "model": config.model,
        "status": "initializing",
        "phase": "pending",  # pending, deploying, booting, benchmarking, evaluating, analyzing, completed, failed
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "vllm_config": {
            "gpu_memory_utilization": config.gpu_memory_utilization,
            "max_model_len": config.max_model_len,
            "quantization": config.quantization,
            "tensor_parallel_size": config.tensor_parallel_size,
            "dtype": config.dtype,
            "enforce_eager": config.enforce_eager
        },
        "test_matrix": test_matrix,
        "current_test_index": 0,
        "total_tests": len(test_matrix),
        # 측정값들
        "metrics": {
            "boot_time": None,  # 모델 부팅 시간 (초)
            "model_load_time": None,  # 모델 로딩 시간
            "first_inference_time": None,  # 첫 추론 시간
            "warmup_time": None  # 워밍업 완료 시간
        },
        "benchmark_results": [],  # 각 테스트 조합의 결과
        "quality_results": [],  # 품질 평가 결과
        "analysis": None,  # 최종 분석 결과
        "optimal_config": None,  # 최적 설정
        "logs": []
    }

    # 백그라운드에서 실행
    background_tasks.add_task(execute_full_benchmark_cycle, session_id, config)

    return {
        "session_id": session_id,
        "status": "started",
        "total_tests": len(test_matrix),
        "message": f"전체 벤치마크 사이클이 시작되었습니다. 모델: {config.model}"
    }


def add_log(session: dict, message: str, level: str = "info"):
    """세션에 로그 추가"""
    session["logs"].append({
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message
    })


async def deploy_vllm_model(session: dict, config: FullBenchmarkCycle) -> bool:
    """vLLM 모델 배포"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        # 기존 vLLM deployment 업데이트
        deployment_name = "vllm-server"
        namespace = "ai-workloads"

        # vLLM 컨테이너 인수 생성
        vllm_args = [
            "--model", config.model,
            "--host", "0.0.0.0",
            "--port", "8000",
            "--gpu-memory-utilization", str(config.gpu_memory_utilization),
            "--dtype", config.dtype,
            "--tensor-parallel-size", str(config.tensor_parallel_size),
        ]

        if config.max_model_len:
            vllm_args.extend(["--max-model-len", str(config.max_model_len)])

        if config.quantization:
            vllm_args.extend(["--quantization", config.quantization])

        if config.enforce_eager:
            vllm_args.append("--enforce-eager")

        # Deployment 패치
        patch_body = {
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "vllm",
                            "args": vllm_args
                        }]
                    }
                }
            }
        }

        try:
            apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=patch_body
            )
            add_log(session, f"vLLM Deployment 업데이트: {config.model}")
        except ApiException as e:
            if e.status == 404:
                add_log(session, "vLLM Deployment가 존재하지 않습니다. 새로 생성합니다.", "warning")
                # 여기서 새 deployment 생성 로직 추가 가능
                return False
            raise

        return True

    except Exception as e:
        add_log(session, f"모델 배포 실패: {str(e)}", "error")
        return False


async def wait_for_vllm_ready(session: dict, timeout: int = 600) -> dict:
    """vLLM 서비스가 준비될 때까지 대기하고 부팅 시간 측정"""
    vllm_endpoint = "http://vllm-server.ai-workloads.svc.cluster.local:8000"
    start_time = time.time()
    boot_phases = {
        "deployment_ready": None,
        "container_ready": None,
        "health_endpoint_ready": None,
        "model_loaded": None,
        "first_inference": None
    }

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time

            # K8s 상태 확인
            try:
                _, apps_v1, _ = get_k8s_clients()
                deployment = apps_v1.read_namespaced_deployment("vllm-server", "ai-workloads")

                if deployment.status.ready_replicas and deployment.status.ready_replicas > 0:
                    if not boot_phases["deployment_ready"]:
                        boot_phases["deployment_ready"] = elapsed
                        add_log(session, f"Deployment 준비 완료: {elapsed:.1f}초")
            except:
                pass

            # Health 엔드포인트 확인
            try:
                health = await client.get(f"{vllm_endpoint}/health", timeout=5.0)
                if health.status_code == 200:
                    if not boot_phases["health_endpoint_ready"]:
                        boot_phases["health_endpoint_ready"] = elapsed
                        add_log(session, f"Health 엔드포인트 응답: {elapsed:.1f}초")

                    # 모델 로딩 확인
                    try:
                        models = await client.get(f"{vllm_endpoint}/v1/models", timeout=10.0)
                        if models.status_code == 200:
                            model_data = models.json()
                            if model_data.get("data"):
                                if not boot_phases["model_loaded"]:
                                    boot_phases["model_loaded"] = elapsed
                                    add_log(session, f"모델 로딩 완료: {elapsed:.1f}초")

                                # 첫 추론 테스트
                                if not boot_phases["first_inference"]:
                                    try:
                                        inference_start = time.time()
                                        resp = await client.post(
                                            f"{vllm_endpoint}/v1/completions",
                                            json={
                                                "model": session["model"],
                                                "prompt": "Hello",
                                                "max_tokens": 5
                                            },
                                            timeout=60.0
                                        )
                                        if resp.status_code == 200:
                                            boot_phases["first_inference"] = elapsed
                                            first_inference_time = time.time() - inference_start
                                            add_log(session, f"첫 추론 완료: {elapsed:.1f}초 (추론 시간: {first_inference_time:.2f}초)")

                                            return {
                                                "success": True,
                                                "total_boot_time": elapsed,
                                                "phases": boot_phases,
                                                "first_inference_latency": first_inference_time
                                            }
                                    except:
                                        pass
                    except:
                        pass
            except:
                pass

            session["phase"] = "booting"
            session["metrics"]["boot_time"] = elapsed
            await asyncio.sleep(5)

    return {
        "success": False,
        "total_boot_time": time.time() - start_time,
        "phases": boot_phases,
        "error": "타임아웃"
    }


async def run_benchmark_test(session: dict, config: FullBenchmarkCycle, test_params: dict) -> dict:
    """단일 벤치마크 테스트 실행"""
    vllm_endpoint = "http://vllm-server.ai-workloads.svc.cluster.local:8000"
    results = []

    async with httpx.AsyncClient() as client:
        for i in range(config.num_requests_per_test):
            prompt = config.quality_prompts[i % len(config.quality_prompts)]

            start_time = time.time()
            try:
                response = await client.post(
                    f"{vllm_endpoint}/v1/completions",
                    json={
                        "model": config.model,
                        "prompt": prompt,
                        "max_tokens": test_params["max_tokens"],
                        "temperature": 0.7,
                        "top_p": 0.9
                    },
                    timeout=120.0
                )

                latency = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()
                    output_tokens = data.get("usage", {}).get("completion_tokens", 0)
                    response_text = data.get("choices", [{}])[0].get("text", "")

                    results.append({
                        "success": True,
                        "latency": latency,
                        "output_tokens": output_tokens,
                        "tokens_per_second": output_tokens / latency if latency > 0 else 0,
                        "response_length": len(response_text),
                        "prompt": prompt[:50] + "..."
                    })
                else:
                    results.append({
                        "success": False,
                        "latency": latency,
                        "error": f"HTTP {response.status_code}"
                    })
            except Exception as e:
                results.append({
                    "success": False,
                    "latency": time.time() - start_time,
                    "error": str(e)
                })

    # 결과 요약
    successful = [r for r in results if r.get("success")]
    if successful:
        latencies = [r["latency"] for r in successful]
        tps = [r["tokens_per_second"] for r in successful if r.get("tokens_per_second", 0) > 0]

        return {
            "params": test_params,
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "success_rate": round(len(successful) / len(results) * 100, 1),
            "latency": {
                "avg": round(sum(latencies) / len(latencies), 3),
                "min": round(min(latencies), 3),
                "max": round(max(latencies), 3),
                "p50": round(sorted(latencies)[len(latencies)//2], 3),
                "p95": round(sorted(latencies)[int(len(latencies)*0.95)], 3) if len(latencies) >= 20 else None
            },
            "throughput": {
                "avg_tokens_per_second": round(sum(tps) / len(tps), 2) if tps else 0,
                "max_tokens_per_second": round(max(tps), 2) if tps else 0,
                "total_tokens": sum(r.get("output_tokens", 0) for r in successful)
            },
            "raw_results": results
        }
    else:
        return {
            "params": test_params,
            "total_requests": len(results),
            "successful": 0,
            "failed": len(results),
            "success_rate": 0,
            "error": "모든 요청 실패"
        }


async def evaluate_quality(session: dict, config: FullBenchmarkCycle) -> dict:
    """출력 품질 평가"""
    vllm_endpoint = "http://vllm-server.ai-workloads.svc.cluster.local:8000"
    quality_results = []

    # 품질 평가 기준
    quality_prompts = [
        {
            "prompt": "What is 2 + 2?",
            "expected_contains": ["4", "four"],
            "type": "math"
        },
        {
            "prompt": "The capital of France is",
            "expected_contains": ["Paris"],
            "type": "factual"
        },
        {
            "prompt": "Write a haiku about nature.",
            "min_words": 5,
            "type": "creative"
        },
        {
            "prompt": "Explain why the sky is blue in one sentence.",
            "min_words": 10,
            "type": "explanation"
        },
        {
            "prompt": "List three primary colors: ",
            "expected_contains": ["red", "blue", "yellow"],
            "type": "list"
        }
    ]

    async with httpx.AsyncClient() as client:
        for qp in quality_prompts:
            try:
                response = await client.post(
                    f"{vllm_endpoint}/v1/completions",
                    json={
                        "model": config.model,
                        "prompt": qp["prompt"],
                        "max_tokens": 100,
                        "temperature": 0.3  # 낮은 temperature로 일관된 결과
                    },
                    timeout=60.0
                )

                if response.status_code == 200:
                    data = response.json()
                    text = data.get("choices", [{}])[0].get("text", "").strip().lower()

                    # 품질 점수 계산
                    score = 0
                    if "expected_contains" in qp:
                        for expected in qp["expected_contains"]:
                            if expected.lower() in text:
                                score += 1
                        score = score / len(qp["expected_contains"]) * 100
                    elif "min_words" in qp:
                        word_count = len(text.split())
                        score = min(100, (word_count / qp["min_words"]) * 100)

                    quality_results.append({
                        "type": qp["type"],
                        "prompt": qp["prompt"],
                        "response": text[:200],
                        "score": round(score, 1),
                        "passed": score >= 50
                    })
            except Exception as e:
                quality_results.append({
                    "type": qp["type"],
                    "prompt": qp["prompt"],
                    "error": str(e),
                    "score": 0,
                    "passed": False
                })

    # 품질 요약
    passed = sum(1 for q in quality_results if q.get("passed"))
    avg_score = sum(q.get("score", 0) for q in quality_results) / len(quality_results) if quality_results else 0

    return {
        "tests": quality_results,
        "summary": {
            "total_tests": len(quality_results),
            "passed": passed,
            "failed": len(quality_results) - passed,
            "pass_rate": round(passed / len(quality_results) * 100, 1) if quality_results else 0,
            "avg_score": round(avg_score, 1)
        }
    }


def analyze_results(session: dict) -> dict:
    """결과 분석 및 최적 설정 도출"""
    benchmark_results = session.get("benchmark_results", [])
    quality_results = session.get("quality_results", {})

    if not benchmark_results:
        return {"error": "벤치마크 결과 없음"}

    # 최적 설정 찾기 (처리량 기준)
    best_throughput = None
    best_latency = None
    best_balanced = None

    for result in benchmark_results:
        if result.get("success_rate", 0) < 80:
            continue  # 성공률 80% 미만은 제외

        tps = result.get("throughput", {}).get("avg_tokens_per_second", 0)
        latency = result.get("latency", {}).get("avg", float('inf'))

        # 처리량 최적
        if best_throughput is None or tps > best_throughput.get("throughput", {}).get("avg_tokens_per_second", 0):
            best_throughput = result

        # 지연시간 최적
        if best_latency is None or latency < best_latency.get("latency", {}).get("avg", float('inf')):
            best_latency = result

        # 균형 점수 (정규화된 처리량 + 정규화된 역지연시간)
        # 단순화: tps / latency
        balance_score = tps / latency if latency > 0 else 0
        if best_balanced is None or balance_score > (best_balanced.get("throughput", {}).get("avg_tokens_per_second", 0) /
                                                      best_balanced.get("latency", {}).get("avg", 1)):
            best_balanced = result

    # 차트 데이터 생성
    chart_data = {
        "latency_by_tokens": [],
        "throughput_by_tokens": [],
        "latency_by_concurrent": [],
        "throughput_by_concurrent": []
    }

    for result in benchmark_results:
        params = result.get("params", {})
        chart_data["latency_by_tokens"].append({
            "x": params.get("max_tokens"),
            "y": result.get("latency", {}).get("avg", 0),
            "concurrent": params.get("concurrent_requests")
        })
        chart_data["throughput_by_tokens"].append({
            "x": params.get("max_tokens"),
            "y": result.get("throughput", {}).get("avg_tokens_per_second", 0),
            "concurrent": params.get("concurrent_requests")
        })

    return {
        "optimal_configs": {
            "best_throughput": {
                "params": best_throughput.get("params") if best_throughput else None,
                "value": best_throughput.get("throughput", {}).get("avg_tokens_per_second") if best_throughput else None
            },
            "best_latency": {
                "params": best_latency.get("params") if best_latency else None,
                "value": best_latency.get("latency", {}).get("avg") if best_latency else None
            },
            "best_balanced": {
                "params": best_balanced.get("params") if best_balanced else None,
                "throughput": best_balanced.get("throughput", {}).get("avg_tokens_per_second") if best_balanced else None,
                "latency": best_balanced.get("latency", {}).get("avg") if best_balanced else None
            }
        },
        "quality_score": quality_results.get("summary", {}).get("avg_score", 0),
        "chart_data": chart_data,
        "summary": {
            "total_tests": len(benchmark_results),
            "boot_time": session.get("metrics", {}).get("boot_time"),
            "model": session.get("model"),
            "vllm_config": session.get("vllm_config")
        }
    }


async def execute_full_benchmark_cycle(session_id: str, config: FullBenchmarkCycle):
    """전체 벤치마크 사이클 실행 (백그라운드)"""
    session = full_cycle_sessions.get(session_id)
    if not session:
        return

    try:
        # 1. 모델 배포
        session["status"] = "running"
        session["phase"] = "deploying"
        add_log(session, f"모델 배포 시작: {config.model}")

        deploy_success = await deploy_vllm_model(session, config)
        if not deploy_success:
            session["status"] = "failed"
            session["phase"] = "failed"
            add_log(session, "모델 배포 실패", "error")
            session["completed_at"] = datetime.now().isoformat()
            return

        # 2. 부팅 대기 및 시간 측정
        session["phase"] = "booting"
        add_log(session, "vLLM 서비스 부팅 대기 중...")

        boot_result = await wait_for_vllm_ready(session)
        session["metrics"]["boot_time"] = boot_result.get("total_boot_time")
        session["metrics"]["model_load_time"] = boot_result.get("phases", {}).get("model_loaded")
        session["metrics"]["first_inference_time"] = boot_result.get("first_inference_latency")

        if not boot_result.get("success"):
            session["status"] = "failed"
            session["phase"] = "failed"
            add_log(session, f"부팅 실패: {boot_result.get('error')}", "error")
            session["completed_at"] = datetime.now().isoformat()
            return

        add_log(session, f"부팅 완료: {boot_result.get('total_boot_time'):.1f}초")

        # 3. 벤치마크 실행
        session["phase"] = "benchmarking"
        add_log(session, f"벤치마크 시작: {len(session['test_matrix'])}개 테스트")

        for i, test_params in enumerate(session["test_matrix"]):
            session["current_test_index"] = i
            add_log(session, f"테스트 {i+1}/{len(session['test_matrix'])}: max_tokens={test_params['max_tokens']}, concurrent={test_params['concurrent_requests']}")

            result = await run_benchmark_test(session, config, test_params)
            session["benchmark_results"].append(result)

        add_log(session, "벤치마크 완료")

        # 4. 품질 평가
        session["phase"] = "evaluating"
        add_log(session, "품질 평가 시작...")

        quality_result = await evaluate_quality(session, config)
        session["quality_results"] = quality_result
        add_log(session, f"품질 평가 완료: 점수 {quality_result['summary']['avg_score']}")

        # 5. 분석
        session["phase"] = "analyzing"
        add_log(session, "결과 분석 중...")

        analysis = analyze_results(session)
        session["analysis"] = analysis
        session["optimal_config"] = analysis.get("optimal_configs", {}).get("best_balanced", {}).get("params")

        add_log(session, "분석 완료")

        # 완료
        session["status"] = "completed"
        session["phase"] = "completed"
        session["completed_at"] = datetime.now().isoformat()
        add_log(session, "전체 벤치마크 사이클 완료!")

    except Exception as e:
        session["status"] = "failed"
        session["phase"] = "failed"
        add_log(session, f"오류 발생: {str(e)}", "error")
        session["completed_at"] = datetime.now().isoformat()


@app.get("/api/benchmark/full-cycle")
async def list_full_cycle_sessions():
    """전체 사이클 세션 목록"""
    sessions = []
    for session_id, session in full_cycle_sessions.items():
        sessions.append({
            "id": session_id,
            "name": session.get("name"),
            "model": session.get("model"),
            "status": session.get("status"),
            "phase": session.get("phase"),
            "total_tests": session.get("total_tests"),
            "current_test_index": session.get("current_test_index"),
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at"),
            "boot_time": session.get("metrics", {}).get("boot_time"),
            "optimal_config": session.get("optimal_config"),
            "quality_score": session.get("quality_results", {}).get("summary", {}).get("avg_score")
        })
    sessions.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return {"sessions": sessions, "total": len(sessions)}


@app.get("/api/benchmark/full-cycle/{session_id}")
async def get_full_cycle_session(session_id: str):
    """전체 사이클 세션 상세 조회"""
    if session_id not in full_cycle_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return full_cycle_sessions[session_id]


@app.delete("/api/benchmark/full-cycle/{session_id}")
async def delete_full_cycle_session(session_id: str):
    """전체 사이클 세션 삭제"""
    if session_id not in full_cycle_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    del full_cycle_sessions[session_id]
    return {"success": True, "message": "세션이 삭제되었습니다"}


@app.post("/api/benchmark/full-cycle/{session_id}/stop")
async def stop_full_cycle_session(session_id: str):
    """실행 중인 세션 중지"""
    if session_id not in full_cycle_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    session = full_cycle_sessions[session_id]
    if session["status"] == "running":
        session["status"] = "stopped"
        session["phase"] = "stopped"
        session["completed_at"] = datetime.now().isoformat()
        add_log(session, "사용자에 의해 중지됨", "warning")

    return {"success": True, "message": "세션이 중지되었습니다"}


# 기본 벤치마크 설정 추가
default_configs = [
    {
        "name": "Quick Test",
        "model": "facebook/opt-125m",
        "max_tokens": 50,
        "temperature": 0.7,
        "top_p": 0.9,
        "num_requests": 5,
        "concurrent_requests": 1,
        "test_prompts": [
            "What is machine learning?",
            "Explain AI briefly.",
            "What is deep learning?",
            "How do neural networks work?",
            "What is NLP?"
        ]
    },
    {
        "name": "Standard Benchmark",
        "model": "facebook/opt-125m",
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 0.9,
        "num_requests": 20,
        "concurrent_requests": 1,
        "test_prompts": [
            "Explain the concept of artificial intelligence and its applications.",
            "Write a detailed explanation of how neural networks learn.",
            "Describe the differences between supervised and unsupervised learning.",
            "What are transformers in machine learning and why are they important?",
            "Explain the concept of attention mechanism in deep learning."
        ]
    },
    {
        "name": "Stress Test",
        "model": "facebook/opt-125m",
        "max_tokens": 200,
        "temperature": 0.8,
        "top_p": 0.95,
        "num_requests": 50,
        "concurrent_requests": 5,
        "test_prompts": [
            "Write a comprehensive essay about the future of artificial intelligence.",
            "Explain quantum computing and its potential impact on machine learning.",
            "Describe the ethical considerations in developing AI systems.",
            "What are the key challenges in natural language processing today?",
            "How will AI transform healthcare in the next decade?"
        ]
    }
]

# 기본 설정 등록
for i, cfg in enumerate(default_configs):
    config_id = f"default-{i+1}"
    benchmark_configs[config_id] = {
        **cfg,
        "created_at": datetime.now().isoformat()
    }


@app.get("/api/benchmark/vllm-status")
async def get_vllm_status():
    """vLLM 서비스 상태 확인"""
    vllm_endpoint = "http://vllm-server.ai-workloads.svc.cluster.local:8000"

    # 먼저 K8s에서 vLLM pod 상태 확인
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        # vLLM deployment 상태 확인
        try:
            deployment = apps_v1.read_namespaced_deployment("vllm-server", "ai-workloads")
            replicas = deployment.spec.replicas or 0
            ready_replicas = deployment.status.ready_replicas or 0

            if replicas == 0:
                return {
                    "status": "stopped",
                    "message": "vLLM 서비스가 중지되어 있습니다",
                    "replicas": 0,
                    "ready_replicas": 0,
                    "healthy": False
                }

            if ready_replicas < replicas:
                # Pod 상태 확인
                pods = core_v1.list_namespaced_pod(
                    "ai-workloads",
                    label_selector="app=vllm-server"
                )

                pod_status = "준비 중"
                for pod in pods.items:
                    if pod.status.phase == "Pending":
                        pod_status = "대기 중 (리소스 할당 중)"
                    elif pod.status.phase == "Running":
                        # 컨테이너 상태 확인
                        for cs in pod.status.container_statuses or []:
                            if cs.state.waiting:
                                reason = cs.state.waiting.reason
                                if reason == "ContainerCreating":
                                    pod_status = "컨테이너 생성 중"
                                elif reason == "CrashLoopBackOff":
                                    pod_status = "시작 실패 (반복 충돌)"
                                elif reason == "ImagePullBackOff":
                                    pod_status = "이미지 다운로드 실패"
                                else:
                                    pod_status = f"대기 중: {reason}"
                            elif cs.state.terminated:
                                pod_status = f"종료됨: {cs.state.terminated.reason}"
                    elif pod.status.phase == "Failed":
                        pod_status = "실패"

                return {
                    "status": "starting",
                    "message": f"vLLM 서비스 {pod_status} ({ready_replicas}/{replicas})",
                    "replicas": replicas,
                    "ready_replicas": ready_replicas,
                    "healthy": False
                }
        except Exception as k8s_err:
            # Deployment를 찾을 수 없음
            return {
                "status": "not_found",
                "message": "vLLM 서비스가 배포되지 않았습니다",
                "healthy": False,
                "error": str(k8s_err)
            }

        # vLLM health 엔드포인트 확인
        async with httpx.AsyncClient() as client:
            try:
                health_check = await client.get(f"{vllm_endpoint}/health", timeout=5.0)
                if health_check.status_code == 200:
                    # 모델 정보도 가져오기
                    try:
                        models_res = await client.get(f"{vllm_endpoint}/v1/models", timeout=5.0)
                        models_data = models_res.json() if models_res.status_code == 200 else {}
                        model_list = [m.get("id") for m in models_data.get("data", [])]
                    except:
                        model_list = []

                    return {
                        "status": "online",
                        "message": "vLLM 서비스가 정상 작동 중입니다",
                        "replicas": replicas,
                        "ready_replicas": ready_replicas,
                        "healthy": True,
                        "models": model_list
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": f"vLLM 서비스가 응답하지 않습니다 (HTTP {health_check.status_code})",
                        "replicas": replicas,
                        "ready_replicas": ready_replicas,
                        "healthy": False
                    }
            except httpx.TimeoutException:
                return {
                    "status": "timeout",
                    "message": "vLLM 서비스 응답 시간 초과 (모델 로딩 중일 수 있음)",
                    "replicas": replicas,
                    "ready_replicas": ready_replicas,
                    "healthy": False
                }
            except Exception as conn_err:
                return {
                    "status": "connection_error",
                    "message": f"vLLM 서비스에 연결할 수 없습니다: {str(conn_err)}",
                    "replicas": replicas,
                    "ready_replicas": ready_replicas,
                    "healthy": False
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"상태 확인 실패: {str(e)}",
            "healthy": False
        }


# ============================================
# RustFS (MinIO) 스토리지 관리 API
# ============================================

from minio import Minio
from minio.error import S3Error
from io import BytesIO
import base64

def get_minio_client():
    """MinIO 클라이언트 생성 (내부 통신용)"""
    # RustFS(MinIO) 서비스 엔드포인트
    return Minio(
        "rustfs.storage.svc.cluster.local:9000",
        access_key="admin",
        secret_key="admin1234",
        secure=False
    )

def get_minio_client_external():
    """MinIO 클라이언트 생성 (외부 Presigned URL용)"""
    # 외부에서 접근 가능한 엔드포인트
    return Minio(
        "14.32.100.220:30900",
        access_key="admin",
        secret_key="admin1234",
        secure=False
    )


@app.get("/api/storage/status")
async def get_storage_status():
    """스토리지 서비스 상태 확인 (실제 디스크 용량 포함)"""
    try:
        client = get_minio_client()
        # 버킷 목록 조회로 연결 확인
        buckets = list(client.list_buckets())

        # 전체 사용량 계산
        total_used = 0
        for bucket in buckets:
            objects = list(client.list_objects(bucket.name, recursive=True))
            total_used += sum(obj.size for obj in objects if obj.size)

        # MinIO 서버 정보 조회 (mc admin info)
        # MinIO는 S3 API로는 디스크 정보를 제공하지 않음
        # PVC 크기에서 가져오거나, 노드의 디스크 정보 사용
        storage_info = await get_storage_disk_info()

        return {
            "status": "connected",
            "bucket_count": len(buckets),
            "endpoint": "rustfs.storage.svc.cluster.local:9000",
            "total_capacity": storage_info.get("total_capacity", 0),
            "total_capacity_human": format_size(storage_info.get("total_capacity", 0)),
            "used_capacity": total_used,
            "used_capacity_human": format_size(total_used),
            "available_capacity": storage_info.get("total_capacity", 0) - total_used,
            "available_capacity_human": format_size(max(0, storage_info.get("total_capacity", 0) - total_used)),
            "usage_percent": round(total_used / storage_info.get("total_capacity", 1) * 100, 1) if storage_info.get("total_capacity", 0) > 0 else 0
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
            "message": "RustFS 서비스가 실행 중인지 확인하세요"
        }


async def get_storage_disk_info():
    """스토리지 노드의 실제 디스크 정보 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # RustFS Pod가 실행 중인 노드 찾기
        pods = core_v1.list_namespaced_pod(namespace="storage", label_selector="app=rustfs")

        if not pods.items:
            # PVC에서 요청된 크기 확인
            pvc_list = core_v1.list_namespaced_persistent_volume_claim(namespace="storage")
            for pvc in pvc_list.items:
                if "rustfs" in pvc.metadata.name or "data-rustfs" in pvc.metadata.name:
                    storage_req = pvc.spec.resources.requests.get("storage", "100Gi")
                    # 크기 파싱 (예: 100Gi -> bytes)
                    if storage_req.endswith("Gi"):
                        return {"total_capacity": int(storage_req[:-2]) * 1024 * 1024 * 1024}
                    elif storage_req.endswith("Ti"):
                        return {"total_capacity": int(storage_req[:-2]) * 1024 * 1024 * 1024 * 1024}
            return {"total_capacity": 100 * 1024 * 1024 * 1024}  # 기본값 100GB

        pod = pods.items[0]
        node_name = pod.spec.node_name

        # 노드의 디스크 정보 (ephemeral-storage)
        node = core_v1.read_node(node_name)
        allocatable = node.status.allocatable or {}

        # ephemeral-storage는 노드의 로컬 스토리지 용량
        ephemeral = allocatable.get("ephemeral-storage", "0")

        # 파싱
        if ephemeral.endswith("Ki"):
            total_bytes = int(ephemeral[:-2]) * 1024
        elif ephemeral.endswith("Mi"):
            total_bytes = int(ephemeral[:-2]) * 1024 * 1024
        elif ephemeral.endswith("Gi"):
            total_bytes = int(ephemeral[:-2]) * 1024 * 1024 * 1024
        else:
            total_bytes = int(ephemeral)

        # PVC 크기도 확인 (실제 할당된 크기)
        # StatefulSet PVC (data-rustfs-0)를 우선 찾고, 없으면 일반 PVC (data-rustfs)
        pvc_list = core_v1.list_namespaced_persistent_volume_claim(namespace="storage")
        target_pvc = None

        for pvc in pvc_list.items:
            pvc_name = pvc.metadata.name
            # StatefulSet PVC 형식 (data-rustfs-0, data-rustfs-1, ...)
            if pvc_name.startswith("data-rustfs-") and pvc_name[-1].isdigit():
                target_pvc = pvc
                break
            # 일반 PVC (data-rustfs)
            elif pvc_name == "data-rustfs" and target_pvc is None:
                target_pvc = pvc

        if target_pvc:
            # status.capacity (실제 할당됨) 우선, 없으면 spec.requests (요청값) 사용
            storage_actual = None
            if target_pvc.status and target_pvc.status.capacity:
                storage_actual = target_pvc.status.capacity.get("storage")

            storage_val = storage_actual or target_pvc.spec.resources.requests.get("storage", "0")
            pvc_bytes = 0
            if storage_val.endswith("Gi"):
                pvc_bytes = int(storage_val[:-2]) * 1024 * 1024 * 1024
            elif storage_val.endswith("Ti"):
                pvc_bytes = int(storage_val[:-2]) * 1024 * 1024 * 1024 * 1024
            if pvc_bytes > 0:
                # PVC 크기와 노드 용량 중 작은 값 사용
                return {"total_capacity": min(total_bytes, pvc_bytes)}

        return {"total_capacity": total_bytes}

    except Exception as e:
        print(f"Storage disk info error: {e}")
        return {"total_capacity": 100 * 1024 * 1024 * 1024}  # 기본값 100GB


@app.get("/api/storage/available-capacity")
async def get_available_storage_capacity():
    """노드의 가용 스토리지 용량 조회 (RustFS 할당 전)"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # 모든 노드의 스토리지 정보 조회
        nodes = core_v1.list_node()
        node_storage = []
        total_available = 0

        for node in nodes.items:
            node_name = node.metadata.name
            allocatable = node.status.allocatable or {}
            capacity = node.status.capacity or {}

            # ephemeral-storage 파싱
            def parse_storage(value):
                if not value:
                    return 0
                if value.endswith("Ki"):
                    return int(value[:-2]) * 1024
                elif value.endswith("Mi"):
                    return int(value[:-2]) * 1024 * 1024
                elif value.endswith("Gi"):
                    return int(value[:-2]) * 1024 * 1024 * 1024
                elif value.endswith("Ti"):
                    return int(value[:-2]) * 1024 * 1024 * 1024 * 1024
                else:
                    try:
                        return int(value)
                    except:
                        return 0

            allocatable_bytes = parse_storage(allocatable.get("ephemeral-storage", "0"))
            capacity_bytes = parse_storage(capacity.get("ephemeral-storage", "0"))

            node_storage.append({
                "node": node_name,
                "capacity": capacity_bytes,
                "capacity_human": format_size(capacity_bytes),
                "allocatable": allocatable_bytes,
                "allocatable_human": format_size(allocatable_bytes)
            })
            total_available += allocatable_bytes

        # 현재 RustFS PVC가 있으면 그 크기도 확인 (rustfs-longhorn 또는 StatefulSet PVC)
        current_pvc_size = 0
        current_storage_class = None
        try:
            pvc_list = core_v1.list_namespaced_persistent_volume_claim(namespace="storage")
            target_pvc = None

            for pvc in pvc_list.items:
                pvc_name = pvc.metadata.name
                # rustfs-longhorn PVC 우선 (Deployment 사용)
                if pvc_name == "rustfs-longhorn":
                    target_pvc = pvc
                    break
                # StatefulSet PVC 형식 (data-rustfs-0)
                elif pvc_name.startswith("data-rustfs-") and pvc_name[-1].isdigit():
                    target_pvc = pvc
                elif pvc_name == "data-rustfs" and target_pvc is None:
                    target_pvc = pvc

            if target_pvc:
                # StorageClass 정보 가져오기
                current_storage_class = target_pvc.spec.storage_class_name

                # status.capacity (실제 할당됨) 우선, 없으면 spec.requests (요청값) 사용
                storage_actual = None
                if target_pvc.status and target_pvc.status.capacity:
                    storage_actual = target_pvc.status.capacity.get("storage")

                storage_val = storage_actual or target_pvc.spec.resources.requests.get("storage", "0")
                if storage_val.endswith("Gi"):
                    current_pvc_size = int(storage_val[:-2]) * 1024 * 1024 * 1024
                elif storage_val.endswith("Ti"):
                    current_pvc_size = int(storage_val[:-2]) * 1024 * 1024 * 1024 * 1024
        except:
            pass

        # 단일 노드에서 할당 가능한 최대값 (가장 큰 노드 기준)
        max_single_node = max((n["allocatable"] for n in node_storage), default=0)

        # 추천 크기들 (10GB ~ 최대값)
        recommended_sizes = []
        for size_gb in [10, 50, 100, 200, 500, 1000, 2000]:
            size_bytes = size_gb * 1024 * 1024 * 1024
            if size_bytes <= max_single_node:
                recommended_sizes.append({
                    "label": f"{size_gb} GB" if size_gb < 1000 else f"{size_gb // 1000} TB",
                    "bytes": size_bytes
                })

        return {
            "nodes": node_storage,
            "total_available": total_available,
            "total_available_human": format_size(total_available),
            "max_allocatable": max_single_node,
            "max_allocatable_human": format_size(max_single_node),
            "current_pvc_size": current_pvc_size,
            "current_pvc_size_human": format_size(current_pvc_size) if current_pvc_size > 0 else None,
            "current_storage_class": current_storage_class,
            "supports_expansion": current_storage_class == "longhorn",  # Longhorn은 동적 확장 지원
            "recommended_sizes": recommended_sizes,
            "min_size": 10 * 1024 * 1024 * 1024,  # 최소 10GB
            "min_size_human": "10 GB"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/capacity")
async def get_storage_capacity():
    """스토리지 용량 정보 조회 (프론트엔드 호환)"""
    try:
        result = await get_available_storage_capacity()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/info")
async def get_storage_info():
    """스토리지 정보 조회 (프론트엔드 호환)"""
    try:
        status = await get_storage_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/usage-breakdown")
async def get_storage_usage_breakdown():
    """스토리지 사용량 분류 조회 (파일 스토리지, RustFS, 시스템 등) - 노드별"""
    try:
        import subprocess
        import os

        core_v1, apps_v1, _ = get_k8s_clients()

        # 현재 Pod가 실행 중인 노드 이름 확인
        current_node = os.environ.get('NODE_NAME', 'unknown')
        if current_node == 'unknown':
            # Pod의 nodeName 조회 시도
            try:
                hostname = os.environ.get('HOSTNAME', '')
                if hostname:
                    pod = core_v1.read_namespaced_pod(name=hostname, namespace='default')
                    current_node = pod.spec.node_name or 'unknown'
            except:
                pass

        breakdown = {
            "node_name": current_node,
            "categories": [],
            "total_capacity": 0,
            "total_used": 0,
            "total_available": 0
        }

        # 1. 실제 디스크 사용량 조회 (df 명령어 사용)
        try:
            df_result = subprocess.run(
                ["df", "-B1", "/"],  # 루트 파티션
                capture_output=True, text=True
            )
            if df_result.returncode == 0:
                lines = df_result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        total_bytes = int(parts[1])
                        used_bytes = int(parts[2])
                        available_bytes = int(parts[3])
                        breakdown["total_capacity"] = total_bytes
                        breakdown["total_used"] = used_bytes
                        breakdown["total_available"] = available_bytes
        except:
            pass

        # 2. RustFS PVC 사용량 (rustfs-longhorn 우선, 그 다음 StatefulSet PVC)
        rustfs_pvc_size = 0
        rustfs_pvc_used = 0
        try:
            pvc_list = core_v1.list_namespaced_persistent_volume_claim(namespace="storage")
            target_pvc = None

            for pvc in pvc_list.items:
                pvc_name = pvc.metadata.name
                # Longhorn PVC 우선 (Deployment 사용)
                if pvc_name == "rustfs-longhorn":
                    target_pvc = pvc
                    break
                # StatefulSet PVC 형식 (data-rustfs-0)
                elif pvc_name.startswith("data-rustfs-") and pvc_name[-1].isdigit():
                    target_pvc = pvc
                elif pvc_name == "data-rustfs" and target_pvc is None:
                    target_pvc = pvc

            if target_pvc:
                # status.capacity (실제 할당됨) 우선, 없으면 spec.requests (요청값) 사용
                storage_actual = None
                if target_pvc.status and target_pvc.status.capacity:
                    storage_actual = target_pvc.status.capacity.get("storage")

                storage_val = storage_actual or target_pvc.spec.resources.requests.get("storage", "0")
                if storage_val.endswith("Gi"):
                    rustfs_pvc_size = int(storage_val[:-2]) * 1024 * 1024 * 1024
                elif storage_val.endswith("Ti"):
                    rustfs_pvc_size = int(storage_val[:-2]) * 1024 * 1024 * 1024 * 1024
                elif storage_val.endswith("Mi"):
                    rustfs_pvc_size = int(storage_val[:-2]) * 1024 * 1024
        except:
            pass

        # RustFS에 저장된 실제 데이터 크기
        try:
            client = get_minio_client()
            buckets = client.list_buckets()
            for bucket in buckets:
                objects = list(client.list_objects(bucket.name, recursive=True))
                rustfs_pvc_used += sum(obj.size for obj in objects if obj.size)
        except:
            pass

        if rustfs_pvc_size > 0:
            breakdown["categories"].append({
                "name": "RustFS 스토리지",
                "description": "분산 오브젝트 스토리지",
                "allocated": rustfs_pvc_size,
                "allocated_human": format_size(rustfs_pvc_size),
                "used": rustfs_pvc_used,
                "used_human": format_size(rustfs_pvc_used),
                "type": "rustfs",
                "color": "#3b82f6"
            })

        # 3. 시스템/부팅 데이터 추정 (os 관련)
        system_size = 0
        try:
            # /boot, /usr, /var/lib 등의 시스템 디렉토리 크기 추정
            for path in ["/boot", "/usr"]:
                du_result = subprocess.run(
                    ["du", "-sb", path],
                    capture_output=True, text=True
                )
                if du_result.returncode == 0:
                    parts = du_result.stdout.strip().split()
                    if parts:
                        system_size += int(parts[0])
        except:
            system_size = 10 * 1024 * 1024 * 1024  # 추정치 10GB

        breakdown["categories"].append({
            "name": "시스템/부팅",
            "description": "OS 및 부팅 관련 데이터",
            "allocated": system_size,
            "allocated_human": format_size(system_size),
            "used": system_size,
            "used_human": format_size(system_size),
            "type": "system",
            "color": "#6b7280"
        })

        # 4. K3s 데이터 (/var/lib/rancher)
        k3s_size = 0
        try:
            du_result = subprocess.run(
                ["du", "-sb", "/var/lib/rancher"],
                capture_output=True, text=True
            )
            if du_result.returncode == 0:
                parts = du_result.stdout.strip().split()
                if parts:
                    k3s_size = int(parts[0])
        except:
            pass

        if k3s_size > 0:
            breakdown["categories"].append({
                "name": "K3s 클러스터",
                "description": "컨테이너 이미지 및 클러스터 데이터",
                "allocated": k3s_size,
                "allocated_human": format_size(k3s_size),
                "used": k3s_size,
                "used_human": format_size(k3s_size),
                "type": "k3s",
                "color": "#10b981"
            })

        # 5. Docker 이미지/데이터 (/var/lib/docker)
        docker_size = 0
        try:
            du_result = subprocess.run(
                ["du", "-sb", "/var/lib/docker"],
                capture_output=True, text=True
            )
            if du_result.returncode == 0:
                parts = du_result.stdout.strip().split()
                if parts:
                    docker_size = int(parts[0])
        except:
            pass

        if docker_size > 0:
            breakdown["categories"].append({
                "name": "Docker 데이터",
                "description": "Docker 이미지 및 컨테이너",
                "allocated": docker_size,
                "allocated_human": format_size(docker_size),
                "used": docker_size,
                "used_human": format_size(docker_size),
                "type": "docker",
                "color": "#8b5cf6"
            })

        # 6. 기타 사용량 (전체 - 위의 합계)
        categorized_total = sum(cat["allocated"] for cat in breakdown["categories"])
        other_used = max(0, breakdown["total_used"] - categorized_total)

        if other_used > 1024 * 1024 * 1024:  # 1GB 이상만 표시
            breakdown["categories"].append({
                "name": "기타",
                "description": "사용자 데이터 및 기타 파일",
                "allocated": other_used,
                "allocated_human": format_size(other_used),
                "used": other_used,
                "used_human": format_size(other_used),
                "type": "other",
                "color": "#f59e0b"
            })

        # 7. 여유 공간
        breakdown["categories"].append({
            "name": "여유 공간",
            "description": "할당 가능한 빈 공간",
            "allocated": breakdown["total_available"],
            "allocated_human": format_size(breakdown["total_available"]),
            "used": 0,
            "used_human": "0 B",
            "type": "free",
            "color": "#e5e7eb"
        })

        # 인간이 읽을 수 있는 총계
        breakdown["total_capacity_human"] = format_size(breakdown["total_capacity"])
        breakdown["total_used_human"] = format_size(breakdown["total_used"])
        breakdown["total_available_human"] = format_size(breakdown["total_available"])
        breakdown["usage_percent"] = round(breakdown["total_used"] / breakdown["total_capacity"] * 100, 1) if breakdown["total_capacity"] > 0 else 0

        return breakdown
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/usage-by-node")
async def get_storage_usage_by_node():
    """노드별 스토리지 사용량 조회"""
    try:
        import subprocess
        core_v1, apps_v1, _ = get_k8s_clients()

        # 모든 노드 조회
        nodes = core_v1.list_node()
        node_storage = []

        for node in nodes.items:
            node_name = node.metadata.name
            labels = node.metadata.labels or {}

            # 노드별 스토리지 정보 수집
            node_data = {
                "node_name": node_name,
                "role": "Master" if "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels else "Worker",
                "categories": [],
                "total_capacity": 0,
                "total_used": 0,
                "total_available": 0
            }

            # 현재 실행 중인 노드인지 확인 (로컬 명령어 실행 가능)
            import os
            current_hostname = os.environ.get('HOSTNAME', '')
            is_current_node = False

            try:
                if current_hostname:
                    # 대시보드 네임스페이스에서 현재 Pod 찾기
                    pod = core_v1.read_namespaced_pod(name=current_hostname, namespace='dashboard')
                    is_current_node = (pod.spec.node_name == node_name)
            except:
                try:
                    # default 네임스페이스에서도 확인
                    if current_hostname:
                        pod = core_v1.read_namespaced_pod(name=current_hostname, namespace='default')
                        is_current_node = (pod.spec.node_name == node_name)
                except:
                    pass

            # 로컬 노드인 경우 실제 디스크 사용량 조회
            if is_current_node:
                # 모든 마운트 포인트 조회 (SSD/HDD 구분)
                try:
                    # df로 모든 파일시스템 조회
                    df_result = subprocess.run(
                        ["df", "-B1", "-x", "tmpfs", "-x", "devtmpfs"],
                        capture_output=True, text=True, timeout=5
                    )

                    # lsblk로 디스크 타입 정보 조회 (ROTA: 0=SSD, 1=HDD)
                    lsblk_result = subprocess.run(
                        ["lsblk", "-o", "NAME,ROTA,MOUNTPOINT", "-n"],
                        capture_output=True, text=True, timeout=5
                    )

                    # 디스크별 ROTA 값 매핑
                    disk_rotation = {}
                    if lsblk_result.returncode == 0:
                        for line in lsblk_result.stdout.strip().split('\n'):
                            parts = line.split()
                            if len(parts) >= 2:
                                disk_name = parts[0].strip('├─└│ ')
                                rota = parts[1]
                                disk_rotation[disk_name] = rota

                    # df 결과 파싱
                    if df_result.returncode == 0:
                        lines = df_result.stdout.strip().split('\n')[1:]  # 헤더 제외

                        for line in lines:
                            parts = line.split()
                            if len(parts) >= 6:
                                filesystem = parts[0]
                                total_bytes = int(parts[1])
                                used_bytes = int(parts[2])
                                available_bytes = int(parts[3])
                                mountpoint = parts[5]

                                # 루트 파티션은 전체 용량으로 계산
                                if mountpoint == '/':
                                    node_data["total_capacity"] = total_bytes
                                    node_data["total_used"] = used_bytes
                                    node_data["total_available"] = available_bytes

                                    # 디스크 타입 확인 (/sys/block을 통해)
                                    # 컨테이너에서는 overlay FS이므로 /sys/block의 nvme/sd 디스크 확인
                                    disk_type = "Unknown"
                                    try:
                                        import os
                                        # /sys/block에서 메인 디스크 찾기 (nvme 또는 sd로 시작)
                                        if os.path.exists('/sys/block'):
                                            for disk in os.listdir('/sys/block'):
                                                if disk.startswith('nvme') or (disk.startswith('sd') and len(disk) == 3):
                                                    # 첫 번째 메인 디스크의 타입 확인
                                                    rota_path = f"/sys/block/{disk}/queue/rotational"
                                                    if os.path.exists(rota_path):
                                                        with open(rota_path, 'r') as f:
                                                            rota_value = f.read().strip()
                                                            disk_type = "SSD" if rota_value == '0' else "HDD"
                                                            break  # 첫 번째 메인 디스크만 사용
                                    except:
                                        pass

                                    node_data["root_disk_type"] = disk_type
                except:
                    pass

                # RustFS PVC 사용량 (이 노드에 있는 경우)
                rustfs_pvc_size = 0
                rustfs_pvc_used = 0
                try:
                    pvc_list = core_v1.list_namespaced_persistent_volume_claim(namespace="storage")
                    target_pvc = None

                    for pvc in pvc_list.items:
                        pvc_name = pvc.metadata.name
                        if pvc_name == "rustfs-longhorn":
                            target_pvc = pvc
                            break
                        elif pvc_name.startswith("data-rustfs-") and pvc_name[-1].isdigit():
                            target_pvc = pvc
                        elif pvc_name == "data-rustfs" and target_pvc is None:
                            target_pvc = pvc

                    if target_pvc:
                        storage_actual = None
                        if target_pvc.status and target_pvc.status.capacity:
                            storage_actual = target_pvc.status.capacity.get("storage")

                        storage_val = storage_actual or target_pvc.spec.resources.requests.get("storage", "0")
                        if storage_val.endswith("Gi"):
                            rustfs_pvc_size = int(storage_val[:-2]) * 1024 * 1024 * 1024
                        elif storage_val.endswith("Ti"):
                            rustfs_pvc_size = int(storage_val[:-2]) * 1024 * 1024 * 1024 * 1024
                        elif storage_val.endswith("Mi"):
                            rustfs_pvc_size = int(storage_val[:-2]) * 1024 * 1024

                    # RustFS에 저장된 실제 데이터 크기
                    if rustfs_pvc_size > 0:
                        try:
                            client = get_minio_client()
                            buckets = client.list_buckets()
                            for bucket in buckets:
                                objects = list(client.list_objects(bucket.name, recursive=True))
                                rustfs_pvc_used += sum(obj.size for obj in objects if obj.size)
                        except:
                            pass

                        node_data["categories"].append({
                            "name": "RustFS 스토리지",
                            "description": "분산 오브젝트 스토리지",
                            "allocated": rustfs_pvc_size,
                            "allocated_human": format_size(rustfs_pvc_size),
                            "used": rustfs_pvc_used,
                            "used_human": format_size(rustfs_pvc_used),
                            "type": "rustfs",
                            "color": "#3b82f6"
                        })
                except:
                    pass

                # 시스템/부팅 데이터
                system_size = 0
                try:
                    for path in ["/boot", "/usr"]:
                        du_result = subprocess.run(
                            ["du", "-sb", path],
                            capture_output=True, text=True, timeout=5
                        )
                        if du_result.returncode == 0:
                            parts = du_result.stdout.strip().split()
                            if parts:
                                system_size += int(parts[0])
                except:
                    system_size = 10 * 1024 * 1024 * 1024  # 추정치 10GB

                if system_size > 0:
                    node_data["categories"].append({
                        "name": "시스템/부팅",
                        "description": "OS 및 부팅 관련 데이터",
                        "allocated": system_size,
                        "allocated_human": format_size(system_size),
                        "type": "system",
                        "color": "#6b7280"
                    })

                # K3s 데이터
                try:
                    du_result = subprocess.run(
                        ["du", "-sb", "/var/lib/rancher"],
                        capture_output=True, text=True, timeout=10
                    )
                    if du_result.returncode == 0:
                        parts = du_result.stdout.strip().split()
                        if parts:
                            k3s_size = int(parts[0])
                            node_data["categories"].append({
                                "name": "K3s 클러스터",
                                "description": "컨테이너 이미지 및 클러스터 데이터",
                                "allocated": k3s_size,
                                "allocated_human": format_size(k3s_size),
                                "type": "k3s",
                                "color": "#10b981"
                            })
                except:
                    pass

                # Docker 데이터
                try:
                    du_result = subprocess.run(
                        ["du", "-sb", "/var/lib/docker"],
                        capture_output=True, text=True, timeout=10
                    )
                    if du_result.returncode == 0:
                        parts = du_result.stdout.strip().split()
                        if parts:
                            docker_size = int(parts[0])
                            if docker_size > 0:
                                node_data["categories"].append({
                                    "name": "Docker 데이터",
                                    "description": "Docker 이미지 및 컨테이너",
                                    "allocated": docker_size,
                                    "allocated_human": format_size(docker_size),
                                    "type": "docker",
                                    "color": "#8b5cf6"
                                })
                except:
                    pass

                # 기타 사용량 (전체 - 카테고리 합계)
                categorized_total = sum(cat["allocated"] for cat in node_data["categories"])
                other_used = max(0, node_data["total_used"] - categorized_total)

                if other_used > 1024 * 1024 * 1024:  # 1GB 이상만 표시
                    node_data["categories"].append({
                        "name": "기타",
                        "description": "사용자 데이터 및 기타 파일",
                        "allocated": other_used,
                        "allocated_human": format_size(other_used),
                        "type": "other",
                        "color": "#f59e0b"
                    })
            else:
                # 원격 노드는 추정치 사용 (Node의 ephemeral-storage capacity 기반)
                capacity = node.status.capacity or {}
                ephemeral_storage = capacity.get("ephemeral-storage", "0")

                # 단위 파싱 (1919238496Ki 형식)
                if ephemeral_storage.endswith("Ki"):
                    node_data["total_capacity"] = int(ephemeral_storage[:-2]) * 1024
                elif ephemeral_storage.endswith("Mi"):
                    node_data["total_capacity"] = int(ephemeral_storage[:-2]) * 1024 * 1024
                elif ephemeral_storage.endswith("Gi"):
                    node_data["total_capacity"] = int(ephemeral_storage[:-2]) * 1024 * 1024 * 1024
                elif ephemeral_storage.endswith("Ti"):
                    node_data["total_capacity"] = int(ephemeral_storage[:-2]) * 1024 * 1024 * 1024 * 1024
                elif ephemeral_storage.isdigit():
                    node_data["total_capacity"] = int(ephemeral_storage)

                # 사용량은 Pod의 실제 사용량으로 추정
                node_data["total_used"] = 0
                node_data["total_available"] = node_data["total_capacity"]

                # Worker 노드도 루트 디스크 타입 추정 (기본값)
                try:
                    # 노드 라벨에서 디스크 타입 확인 시도
                    node_labels = node.metadata.labels or {}
                    if "storage-type" in node_labels:
                        node_data["root_disk_type"] = node_labels["storage-type"]
                    else:
                        # 기본값: 용량이 큰 경우 HDD로 추정
                        if node_data["total_capacity"] > 2 * 1024 * 1024 * 1024 * 1024:  # 2TB 이상
                            node_data["root_disk_type"] = "HDD (추정)"
                        else:
                            node_data["root_disk_type"] = "SSD (추정)"
                except:
                    node_data["root_disk_type"] = "Unknown"

            # 로컬 노드인 경우 추가 디스크 정보 수집 (HDD)
            if is_current_node:
                try:
                    # 모든 블록 디바이스 조회
                    lsblk_full = subprocess.run(
                        ["lsblk", "-b", "-o", "NAME,SIZE,ROTA,TYPE,MOUNTPOINT", "-n"],
                        capture_output=True, text=True, timeout=5
                    )

                    if lsblk_full.returncode == 0:
                        for line in lsblk_full.stdout.strip().split('\n'):
                            parts = line.split(maxsplit=4)
                            if len(parts) >= 4:
                                disk_name = parts[0].strip('├─└│ ')
                                size_bytes = int(parts[1]) if parts[1].isdigit() else 0
                                rota = parts[2]
                                dtype = parts[3]
                                mountpoint = parts[4] if len(parts) >= 5 else ""

                                # HDD만 선택 (disk 타입이고 ROTA=1)
                                if dtype == "disk" and rota == "1" and size_bytes > 0:
                                    disk_type_str = "HDD"

                                    # 실제 사용량 확인 (마운트된 경우)
                                    used_bytes = 0
                                    avail_bytes = size_bytes
                                    usage_info = "미할당"

                                    if mountpoint and mountpoint != "":
                                        try:
                                            df_disk = subprocess.run(
                                                ["df", "-B1", mountpoint],
                                                capture_output=True, text=True, timeout=2
                                            )
                                            if df_disk.returncode == 0:
                                                df_lines = df_disk.stdout.strip().split('\n')
                                                if len(df_lines) >= 2:
                                                    df_parts = df_lines[1].split()
                                                    if len(df_parts) >= 4:
                                                        used_bytes = int(df_parts[2])
                                                        avail_bytes = int(df_parts[3])
                                        except:
                                            pass

                                        # 마운트 포인트에서 용도 추출
                                        if "/var/lib/kubelet/pods/" in mountpoint:
                                            # Pod UUID 추출 시도
                                            parts = mountpoint.split("/")
                                            if "pvc-" in mountpoint:
                                                # PVC 이름 추출
                                                pvc_idx = next((i for i, p in enumerate(parts) if 'pvc-' in p), -1)
                                                if pvc_idx > 0:
                                                    usage_info = f"PVC 마운트"
                                            else:
                                                usage_info = "Kubernetes Pod 사용"
                                        else:
                                            usage_info = f"마운트: {mountpoint}"

                                    node_data["categories"].append({
                                        "name": f"HDD: /dev/{disk_name}",
                                        "description": f"추가 하드 디스크 ({format_size(size_bytes)}) - {usage_info}",
                                        "allocated": size_bytes,
                                        "allocated_human": format_size(size_bytes),
                                        "used": used_bytes,
                                        "used_human": format_size(used_bytes),
                                        "type": "hdd",
                                        "color": "#fb923c",
                                        "usage_info": usage_info
                                    })
                except:
                    pass

            # PVC 정보 추가 (이 노드에 할당된 PVC)
            try:
                pvs = core_v1.list_persistent_volume()
                for pv in pvs.items:
                    if pv.spec.node_affinity:
                        # Node affinity로 노드 확인
                        node_selector = pv.spec.node_affinity.required
                        if node_selector and node_selector.node_selector_terms:
                            for term in node_selector.node_selector_terms:
                                for expr in term.match_expressions or []:
                                    if expr.key == "kubernetes.io/hostname" and node_name in expr.values:
                                        # 이 PV는 현재 노드에 할당됨
                                        capacity_str = pv.spec.capacity.get("storage", "0")
                                        pv_size = 0
                                        if capacity_str.endswith("Gi"):
                                            pv_size = int(capacity_str[:-2]) * 1024 * 1024 * 1024
                                        elif capacity_str.endswith("Ti"):
                                            pv_size = int(capacity_str[:-2]) * 1024 * 1024 * 1024 * 1024

                                        if pv_size > 0:
                                            pv_name = pv.metadata.name
                                            claim_ref = pv.spec.claim_ref
                                            claim_name = claim_ref.name if claim_ref else pv_name
                                            storage_class = pv.spec.storage_class_name or "default"

                                            # local-path는 루트 디스크 사용, 그 외는 별도 PVC로 분류
                                            if storage_class == "local-path":
                                                pv_type = "pvc-local"
                                                pv_description = f"PVC: {claim_name} (루트 디스크)"
                                                pv_color = "#3b82f6"
                                            else:
                                                pv_type = "pvc-remote"
                                                pv_description = f"별도 스토리지 ({storage_class})"
                                                pv_color = "#8b5cf6"

                                            node_data["categories"].append({
                                                "name": f"PVC: {claim_name}",
                                                "description": pv_description,
                                                "allocated": pv_size,
                                                "allocated_human": format_size(pv_size),
                                                "type": pv_type,
                                                "color": pv_color
                                            })
            except:
                pass

            # 여유 공간
            if node_data["total_capacity"] > 0:
                node_data["categories"].append({
                    "name": "여유 공간",
                    "description": "할당 가능한 빈 공간",
                    "allocated": node_data["total_available"],
                    "allocated_human": format_size(node_data["total_available"]),
                    "type": "free",
                    "color": "#e5e7eb"
                })

            # 인간이 읽을 수 있는 형식 추가
            node_data["total_capacity_human"] = format_size(node_data["total_capacity"])
            node_data["total_used_human"] = format_size(node_data["total_used"])
            node_data["total_available_human"] = format_size(node_data["total_available"])
            node_data["usage_percent"] = round(node_data["total_used"] / node_data["total_capacity"] * 100, 1) if node_data["total_capacity"] > 0 else 0

            node_storage.append(node_data)

        return {"nodes": node_storage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/buckets")
async def list_buckets():
    """버킷 목록 조회"""
    try:
        client = get_minio_client()
        buckets = client.list_buckets()

        result = []
        for bucket in buckets:
            # 버킷 내 객체 수 계산
            objects = list(client.list_objects(bucket.name, recursive=True))
            total_size = sum(obj.size for obj in objects if obj.size)

            result.append({
                "name": bucket.name,
                "creation_date": bucket.creation_date.isoformat() if bucket.creation_date else None,
                "object_count": len(objects),
                "total_size": total_size,
                "total_size_human": format_size(total_size)
            })

        return {"buckets": result, "total": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def format_size(size_bytes):
    """바이트를 읽기 쉬운 형식으로 변환"""
    if size_bytes == 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


class BucketCreate(BaseModel):
    name: str


@app.post("/api/storage/buckets")
async def create_bucket(bucket: BucketCreate):
    """버킷 생성"""
    try:
        client = get_minio_client()

        # 버킷 이름 유효성 검사
        if not bucket.name or len(bucket.name) < 3:
            raise HTTPException(status_code=400, detail="버킷 이름은 3자 이상이어야 합니다")

        if client.bucket_exists(bucket.name):
            raise HTTPException(status_code=400, detail="이미 존재하는 버킷입니다")

        client.make_bucket(bucket.name)
        return {"success": True, "message": f"버킷 '{bucket.name}'이 생성되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/storage/buckets/{bucket_name}")
async def delete_bucket(bucket_name: str, force: bool = False):
    """버킷 삭제"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # force=True면 버킷 내 모든 객체 삭제 후 버킷 삭제
        if force:
            objects = client.list_objects(bucket_name, recursive=True)
            for obj in objects:
                client.remove_object(bucket_name, obj.object_name)

        client.remove_bucket(bucket_name)
        return {"success": True, "message": f"버킷 '{bucket_name}'이 삭제되었습니다"}
    except HTTPException:
        raise
    except S3Error as e:
        if "not empty" in str(e).lower():
            raise HTTPException(status_code=400, detail="버킷이 비어있지 않습니다. force=true로 강제 삭제하세요")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/buckets/{bucket_name}/objects")
async def list_objects(bucket_name: str, prefix: str = "", delimiter: str = "/"):
    """버킷 내 객체 목록 조회 (폴더 구조 지원)"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        objects = client.list_objects(bucket_name, prefix=prefix, recursive=False)

        result = []
        for obj in objects:
            # 현재 prefix와 같은 폴더는 스킵 (자기 자신 제외)
            if obj.object_name == prefix:
                continue

            is_folder = obj.object_name.endswith('/') or obj.is_dir
            result.append({
                "name": obj.object_name,
                "display_name": obj.object_name.split('/')[-1] or obj.object_name.split('/')[-2] + '/',
                "size": obj.size if not is_folder else 0,
                "size_human": format_size(obj.size) if obj.size and not is_folder else "-",
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                "is_folder": is_folder,
                "etag": obj.etag if not is_folder else None
            })

        # 폴더 먼저, 그 다음 파일 (이름순)
        result.sort(key=lambda x: (not x['is_folder'], x['name'].lower()))

        return {
            "bucket": bucket_name,
            "prefix": prefix,
            "objects": result,
            "total": len(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ObjectUpload(BaseModel):
    object_name: str
    content: str  # base64 encoded
    content_type: str = "application/octet-stream"


@app.post("/api/storage/buckets/{bucket_name}/objects")
async def upload_object(bucket_name: str, upload: ObjectUpload):
    """객체 업로드 (base64 인코딩된 내용)"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # base64 디코딩
        content = base64.b64decode(upload.content)
        content_stream = BytesIO(content)

        client.put_object(
            bucket_name,
            upload.object_name,
            content_stream,
            length=len(content),
            content_type=upload.content_type
        )

        return {
            "success": True,
            "message": f"'{upload.object_name}'이 업로드되었습니다",
            "size": len(content),
            "size_human": format_size(len(content))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/storage/buckets/{bucket_name}/objects/{object_name:path}")
async def delete_object(bucket_name: str, object_name: str):
    """객체 삭제"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # 폴더인 경우 하위 모든 객체 삭제
        if object_name.endswith('/'):
            objects = client.list_objects(bucket_name, prefix=object_name, recursive=True)
            deleted_count = 0
            for obj in objects:
                client.remove_object(bucket_name, obj.object_name)
                deleted_count += 1
            return {"success": True, "message": f"폴더와 {deleted_count}개의 객체가 삭제되었습니다"}
        else:
            client.remove_object(bucket_name, object_name)
            return {"success": True, "message": f"'{object_name}'이 삭제되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/storage/buckets/{bucket_name}/objects/move")
async def move_object(bucket_name: str, request: Request):
    """객체 이동 (복사 후 삭제)"""
    try:
        client = get_minio_client()
        data = await request.json()
        source_name = data.get("source")
        dest_name = data.get("destination")

        if not source_name or not dest_name:
            raise HTTPException(status_code=400, detail="source와 destination이 필요합니다")

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # 소스가 폴더인 경우 (끝이 /로 끝나는 경우)
        if source_name.endswith('/'):
            # 폴더 내 모든 객체 이동
            objects = list(client.list_objects(bucket_name, prefix=source_name, recursive=True))
            moved_count = 0
            for obj in objects:
                # 새 경로 계산
                relative_path = obj.object_name[len(source_name):]
                new_name = dest_name + relative_path

                # 복사
                from minio.commonconfig import CopySource
                client.copy_object(
                    bucket_name,
                    new_name,
                    CopySource(bucket_name, obj.object_name)
                )
                # 삭제
                client.remove_object(bucket_name, obj.object_name)
                moved_count += 1

            return {"success": True, "message": f"{moved_count}개 객체가 이동되었습니다"}
        else:
            # 단일 파일 이동
            from minio.commonconfig import CopySource
            client.copy_object(
                bucket_name,
                dest_name,
                CopySource(bucket_name, source_name)
            )
            client.remove_object(bucket_name, source_name)
            return {"success": True, "message": f"'{source_name}'이 '{dest_name}'으로 이동되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/download")
async def download_object(bucket_name: str, object_name: str):
    """객체 다운로드 (base64로 반환)"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        response = client.get_object(bucket_name, object_name)
        content = response.read()
        response.close()
        response.release_conn()

        # 파일 정보
        stat = client.stat_object(bucket_name, object_name)

        return {
            "object_name": object_name,
            "content": base64.b64encode(content).decode('utf-8'),
            "content_type": stat.content_type,
            "size": stat.size,
            "size_human": format_size(stat.size),
            "last_modified": stat.last_modified.isoformat() if stat.last_modified else None
        }
    except HTTPException:
        raise
    except S3Error as e:
        if "NoSuchKey" in str(e):
            raise HTTPException(status_code=404, detail="객체를 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/stream")
async def stream_object(bucket_name: str, object_name: str):
    """객체 스트리밍 (파일 직접 전송 - PDF, 이미지 등 미리보기용)"""
    try:
        minio_client = get_minio_client()

        if not minio_client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # 파일 정보
        stat = minio_client.stat_object(bucket_name, object_name)

        # 파일 가져오기
        response = minio_client.get_object(bucket_name, object_name)
        content = response.read()
        response.close()
        response.release_conn()

        # Content-Type 결정
        content_type = stat.content_type or "application/octet-stream"

        # 확장자 기반 Content-Type 보정
        ext = object_name.lower().split('.')[-1] if '.' in object_name else ''
        content_type_map = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'svg': 'image/svg+xml',
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'html': 'text/html',
            'txt': 'text/plain',
            'json': 'application/json',
            'xml': 'application/xml',
        }
        if ext in content_type_map:
            content_type = content_type_map[ext]

        # 파일명 (Content-Disposition용)
        filename = object_name.split('/')[-1]

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Content-Length": str(stat.size),
                "Cache-Control": "max-age=3600",
            }
        )
    except HTTPException:
        raise
    except S3Error as e:
        if "NoSuchKey" in str(e):
            raise HTTPException(status_code=404, detail="객체를 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FolderCreate(BaseModel):
    folder_name: str


@app.post("/api/storage/buckets/{bucket_name}/folders")
async def create_folder(bucket_name: str, folder: FolderCreate):
    """폴더 생성 (빈 객체로 표현)"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        folder_name = folder.folder_name
        if not folder_name.endswith('/'):
            folder_name += '/'

        # 빈 객체로 폴더 생성
        client.put_object(bucket_name, folder_name, BytesIO(b''), 0)

        return {"success": True, "message": f"폴더 '{folder_name}'이 생성되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# S3 고급 기능 API
# ============================================

from datetime import timedelta
import json
import xml.etree.ElementTree as ET

# --- 버킷 정책 관리 ---

class BucketPolicy(BaseModel):
    policy: dict

@app.get("/api/storage/buckets/{bucket_name}/policy")
async def get_bucket_policy(bucket_name: str):
    """버킷 정책 조회"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        try:
            policy = client.get_bucket_policy(bucket_name)
            return {"bucket": bucket_name, "policy": json.loads(policy) if policy else None}
        except S3Error as e:
            if "NoSuchBucketPolicy" in str(e):
                return {"bucket": bucket_name, "policy": None}
            raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/buckets/{bucket_name}/policy")
async def set_bucket_policy(bucket_name: str, policy_data: BucketPolicy):
    """버킷 정책 설정"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        policy_json = json.dumps(policy_data.policy)
        client.set_bucket_policy(bucket_name, policy_json)

        return {"success": True, "message": f"버킷 '{bucket_name}'의 정책이 설정되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/storage/buckets/{bucket_name}/policy")
async def delete_bucket_policy(bucket_name: str):
    """버킷 정책 삭제"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        client.delete_bucket_policy(bucket_name)
        return {"success": True, "message": f"버킷 '{bucket_name}'의 정책이 삭제되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 정책 템플릿
@app.get("/api/storage/policy-templates")
async def get_policy_templates():
    """사전 정의된 정책 템플릿"""
    return {
        "templates": [
            {
                "name": "public-read",
                "description": "모든 사용자가 읽기 가능",
                "policy": {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::BUCKET_NAME/*"]
                    }]
                }
            },
            {
                "name": "public-read-write",
                "description": "모든 사용자가 읽기/쓰기 가능",
                "policy": {
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                        "Resource": ["arn:aws:s3:::BUCKET_NAME/*"]
                    }]
                }
            },
            {
                "name": "private",
                "description": "인증된 사용자만 접근 가능 (기본값)",
                "policy": None
            }
        ]
    }


# --- 객체 버전 관리 ---

class VersioningConfig(BaseModel):
    enabled: bool

@app.get("/api/storage/buckets/{bucket_name}/versioning")
async def get_bucket_versioning(bucket_name: str):
    """버킷 버전 관리 상태 조회"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        config = client.get_bucket_versioning(bucket_name)
        return {
            "bucket": bucket_name,
            "versioning": {
                "status": config.status if config else "Disabled",
                "mfa_delete": config.mfa_delete if config else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/buckets/{bucket_name}/versioning")
async def set_bucket_versioning(bucket_name: str, config: VersioningConfig):
    """버킷 버전 관리 설정"""
    try:
        from minio.versioningconfig import VersioningConfig as MinioVersioningConfig, ENABLED, SUSPENDED

        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        versioning_config = MinioVersioningConfig(ENABLED if config.enabled else SUSPENDED)
        client.set_bucket_versioning(bucket_name, versioning_config)

        status = "활성화" if config.enabled else "비활성화"
        return {"success": True, "message": f"버킷 '{bucket_name}'의 버전 관리가 {status}되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/versions")
async def list_object_versions(bucket_name: str, object_name: str):
    """객체의 모든 버전 조회"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # 버전 관리가 활성화된 경우에만 버전 목록 조회 가능
        versions = []
        try:
            # MinIO의 list_objects에서 include_version=True 사용
            objects = client.list_objects(bucket_name, prefix=object_name, include_version=True)
            for obj in objects:
                if obj.object_name == object_name:
                    versions.append({
                        "version_id": obj.version_id,
                        "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                        "size": obj.size,
                        "size_human": format_size(obj.size) if obj.size else "0 B",
                        "is_latest": obj.is_latest,
                        "is_delete_marker": obj.is_delete_marker if hasattr(obj, 'is_delete_marker') else False
                    })
        except Exception as e:
            # 버전 관리가 비활성화된 경우
            stat = client.stat_object(bucket_name, object_name)
            versions.append({
                "version_id": None,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "size": stat.size,
                "size_human": format_size(stat.size),
                "is_latest": True,
                "is_delete_marker": False
            })

        return {
            "bucket": bucket_name,
            "object_name": object_name,
            "versions": versions,
            "total": len(versions)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 멀티파트 업로드 ---

@app.get("/api/storage/buckets/{bucket_name}/multipart-uploads")
async def list_multipart_uploads(bucket_name: str):
    """진행 중인 멀티파트 업로드 목록"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        uploads = []
        try:
            # MinIO Python SDK에서는 직접 지원하지 않아 HTTP 요청 사용
            from minio.api import _DEFAULT_USER_AGENT
            import urllib3

            # 멀티파트 업로드 목록 조회
            result = client._list_multipart_uploads(bucket_name)
            for upload in result:
                uploads.append({
                    "key": upload.object_name,
                    "upload_id": upload.upload_id,
                    "initiated": upload.initiated.isoformat() if upload.initiated else None,
                    "initiator": upload.initiator if hasattr(upload, 'initiator') else None
                })
        except Exception:
            # SDK가 지원하지 않으면 빈 목록 반환
            pass

        return {
            "bucket": bucket_name,
            "uploads": uploads,
            "total": len(uploads)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AbortMultipartUpload(BaseModel):
    object_name: str
    upload_id: str

@app.post("/api/storage/buckets/{bucket_name}/multipart-uploads/abort")
async def abort_multipart_upload(bucket_name: str, abort_data: AbortMultipartUpload):
    """멀티파트 업로드 중단"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        client._abort_multipart_upload(bucket_name, abort_data.object_name, abort_data.upload_id)
        return {"success": True, "message": "멀티파트 업로드가 중단되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Presigned URL ---

class PresignedUrlRequest(BaseModel):
    object_name: str
    expires_hours: int = 1  # 기본 1시간
    method: str = "GET"  # GET 또는 PUT

@app.post("/api/storage/buckets/{bucket_name}/presigned-url")
async def generate_presigned_url(bucket_name: str, request: PresignedUrlRequest):
    """Presigned URL 생성"""
    try:
        # 내부 클라이언트로 버킷 존재 확인
        internal_client = get_minio_client()
        if not internal_client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # 외부 클라이언트로 Presigned URL 생성 (서명이 외부 endpoint와 일치하도록)
        external_client = get_minio_client_external()
        expires = timedelta(hours=request.expires_hours)

        if request.method.upper() == "PUT":
            url = external_client.presigned_put_object(bucket_name, request.object_name, expires=expires)
            action = "업로드"
        else:
            url = external_client.presigned_get_object(bucket_name, request.object_name, expires=expires)
            action = "다운로드"

        return {
            "url": url,
            "method": request.method.upper(),
            "expires_in": f"{request.expires_hours}시간",
            "object_name": request.object_name,
            "message": f"이 URL로 {request.expires_hours}시간 동안 {action} 가능합니다"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 객체 태그 관리 ---

class ObjectTags(BaseModel):
    tags: dict  # {"key": "value", ...}

@app.get("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/tags")
async def get_object_tags(bucket_name: str, object_name: str):
    """객체 태그 조회"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        try:
            tags = client.get_object_tags(bucket_name, object_name)
            tag_dict = {}
            if tags:
                for tag in tags:
                    tag_dict[tag.key] = tag.value
            return {
                "bucket": bucket_name,
                "object_name": object_name,
                "tags": tag_dict
            }
        except S3Error as e:
            if "NoSuchKey" in str(e):
                raise HTTPException(status_code=404, detail="객체를 찾을 수 없습니다")
            raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/tags")
async def set_object_tags(bucket_name: str, object_name: str, tag_data: ObjectTags):
    """객체 태그 설정"""
    try:
        from minio.commonconfig import Tags

        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        tags = Tags.new_object_tags()
        for key, value in tag_data.tags.items():
            tags[key] = value

        client.set_object_tags(bucket_name, object_name, tags)
        return {
            "success": True,
            "message": f"객체 '{object_name}'에 태그가 설정되었습니다",
            "tags": tag_data.tags
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/tags")
async def delete_object_tags(bucket_name: str, object_name: str):
    """객체 태그 삭제"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        client.delete_object_tags(bucket_name, object_name)
        return {"success": True, "message": f"객체 '{object_name}'의 태그가 삭제되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 생명주기 규칙 ---

class LifecycleRule(BaseModel):
    rule_id: str
    prefix: str = ""
    enabled: bool = True
    expiration_days: Optional[int] = None
    noncurrent_expiration_days: Optional[int] = None
    transition_days: Optional[int] = None
    transition_storage_class: Optional[str] = None

class LifecycleConfig(BaseModel):
    rules: List[LifecycleRule]

@app.get("/api/storage/buckets/{bucket_name}/lifecycle")
async def get_bucket_lifecycle(bucket_name: str):
    """버킷 생명주기 규칙 조회"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        try:
            config = client.get_bucket_lifecycle(bucket_name)
            rules = []
            if config and config.rules:
                for rule in config.rules:
                    rule_data = {
                        "rule_id": rule.rule_id,
                        "prefix": rule.rule_filter.prefix if rule.rule_filter else "",
                        "enabled": rule.status == "Enabled",
                    }
                    if rule.expiration:
                        rule_data["expiration_days"] = rule.expiration.days
                        rule_data["expiration_date"] = rule.expiration.date.isoformat() if rule.expiration.date else None
                    if rule.noncurrent_version_expiration:
                        rule_data["noncurrent_expiration_days"] = rule.noncurrent_version_expiration.noncurrent_days
                    if rule.transition:
                        rule_data["transition_days"] = rule.transition.days
                        rule_data["transition_storage_class"] = rule.transition.storage_class
                    rules.append(rule_data)

            return {"bucket": bucket_name, "rules": rules, "total": len(rules)}
        except S3Error as e:
            if "NoSuchLifecycleConfiguration" in str(e):
                return {"bucket": bucket_name, "rules": [], "total": 0}
            raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/buckets/{bucket_name}/lifecycle")
async def set_bucket_lifecycle(bucket_name: str, config: LifecycleConfig):
    """버킷 생명주기 규칙 설정"""
    try:
        from minio.lifecycleconfig import LifecycleConfig as MinioLifecycleConfig, Rule, Expiration, Filter, NoncurrentVersionExpiration, Transition

        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        rules = []
        for rule_data in config.rules:
            expiration = None
            noncurrent_expiration = None
            transition = None

            if rule_data.expiration_days:
                expiration = Expiration(days=rule_data.expiration_days)

            if rule_data.noncurrent_expiration_days:
                noncurrent_expiration = NoncurrentVersionExpiration(noncurrent_days=rule_data.noncurrent_expiration_days)

            if rule_data.transition_days and rule_data.transition_storage_class:
                transition = Transition(days=rule_data.transition_days, storage_class=rule_data.transition_storage_class)

            rule = Rule(
                rule_id=rule_data.rule_id,
                status="Enabled" if rule_data.enabled else "Disabled",
                rule_filter=Filter(prefix=rule_data.prefix) if rule_data.prefix else None,
                expiration=expiration,
                noncurrent_version_expiration=noncurrent_expiration,
                transition=transition
            )
            rules.append(rule)

        lifecycle_config = MinioLifecycleConfig(rules)
        client.set_bucket_lifecycle(bucket_name, lifecycle_config)

        return {"success": True, "message": f"버킷 '{bucket_name}'의 생명주기 규칙이 설정되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/storage/buckets/{bucket_name}/lifecycle")
async def delete_bucket_lifecycle(bucket_name: str):
    """버킷 생명주기 규칙 삭제"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        client.delete_bucket_lifecycle(bucket_name)
        return {"success": True, "message": f"버킷 '{bucket_name}'의 생명주기 규칙이 삭제되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 생명주기 규칙 템플릿
@app.get("/api/storage/lifecycle-templates")
async def get_lifecycle_templates():
    """사전 정의된 생명주기 규칙 템플릿"""
    return {
        "templates": [
            {
                "name": "delete-after-30-days",
                "description": "30일 후 자동 삭제",
                "rule": {
                    "rule_id": "delete-30d",
                    "prefix": "",
                    "enabled": True,
                    "expiration_days": 30
                }
            },
            {
                "name": "delete-after-90-days",
                "description": "90일 후 자동 삭제",
                "rule": {
                    "rule_id": "delete-90d",
                    "prefix": "",
                    "enabled": True,
                    "expiration_days": 90
                }
            },
            {
                "name": "delete-after-1-year",
                "description": "1년 후 자동 삭제",
                "rule": {
                    "rule_id": "delete-365d",
                    "prefix": "",
                    "enabled": True,
                    "expiration_days": 365
                }
            },
            {
                "name": "cleanup-old-versions",
                "description": "이전 버전 30일 후 삭제",
                "rule": {
                    "rule_id": "cleanup-versions",
                    "prefix": "",
                    "enabled": True,
                    "noncurrent_expiration_days": 30
                }
            },
            {
                "name": "temp-files-cleanup",
                "description": "temp/ 폴더 7일 후 삭제",
                "rule": {
                    "rule_id": "temp-cleanup",
                    "prefix": "temp/",
                    "enabled": True,
                    "expiration_days": 7
                }
            },
            {
                "name": "logs-cleanup",
                "description": "logs/ 폴더 14일 후 삭제",
                "rule": {
                    "rule_id": "logs-cleanup",
                    "prefix": "logs/",
                    "enabled": True,
                    "expiration_days": 14
                }
            }
        ]
    }


# --- 버킷 통계 ---

@app.get("/api/storage/buckets/{bucket_name}/stats")
async def get_bucket_stats(bucket_name: str):
    """버킷 상세 통계"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        objects = list(client.list_objects(bucket_name, recursive=True))

        total_size = 0
        object_count = 0
        folder_count = 0
        file_types = {}
        size_distribution = {"<1KB": 0, "1KB-1MB": 0, "1MB-100MB": 0, "100MB-1GB": 0, ">1GB": 0}

        for obj in objects:
            if obj.object_name.endswith('/'):
                folder_count += 1
                continue

            object_count += 1
            size = obj.size or 0
            total_size += size

            # 파일 확장자 분류
            ext = obj.object_name.rsplit('.', 1)[-1].lower() if '.' in obj.object_name else 'unknown'
            file_types[ext] = file_types.get(ext, 0) + 1

            # 크기 분포
            if size < 1024:
                size_distribution["<1KB"] += 1
            elif size < 1024 * 1024:
                size_distribution["1KB-1MB"] += 1
            elif size < 100 * 1024 * 1024:
                size_distribution["1MB-100MB"] += 1
            elif size < 1024 * 1024 * 1024:
                size_distribution["100MB-1GB"] += 1
            else:
                size_distribution[">1GB"] += 1

        # 버전 관리 상태
        versioning = client.get_bucket_versioning(bucket_name)

        return {
            "bucket": bucket_name,
            "stats": {
                "total_objects": object_count,
                "total_folders": folder_count,
                "total_size": total_size,
                "total_size_human": format_size(total_size),
                "versioning_enabled": versioning.status == "Enabled" if versioning else False,
                "file_types": dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]),
                "size_distribution": size_distribution
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 버킷 쿼터 및 사용자 관리 API (MinIO Admin)
# ============================================

import httpx
import hashlib
import hmac
from datetime import datetime
from urllib.parse import urlencode

MINIO_ADMIN_ENDPOINT = "http://rustfs.storage.svc.cluster.local:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "admin1234"


def minio_admin_request(method: str, path: str, body: dict = None) -> dict:
    """MinIO Admin API 요청 (서명된 요청)"""
    try:
        url = f"{MINIO_ADMIN_ENDPOINT}{path}"

        # 간단한 Basic Auth 또는 Bearer Token 사용
        # MinIO Console API는 로그인 후 토큰 사용
        headers = {
            "Content-Type": "application/json"
        }

        with httpx.Client(timeout=30) as client:
            if method == "GET":
                response = client.get(url, headers=headers, auth=(MINIO_ACCESS_KEY, MINIO_SECRET_KEY))
            elif method == "POST":
                response = client.post(url, headers=headers, json=body, auth=(MINIO_ACCESS_KEY, MINIO_SECRET_KEY))
            elif method == "PUT":
                response = client.put(url, headers=headers, json=body, auth=(MINIO_ACCESS_KEY, MINIO_SECRET_KEY))
            elif method == "DELETE":
                response = client.delete(url, headers=headers, auth=(MINIO_ACCESS_KEY, MINIO_SECRET_KEY))
            else:
                return {"success": False, "error": f"지원하지 않는 메서드: {method}"}

            if response.status_code < 300:
                try:
                    return {"success": True, "data": response.json()}
                except:
                    return {"success": True, "data": response.text}
            else:
                return {"success": False, "error": response.text, "status_code": response.status_code}

    except Exception as e:
        return {"success": False, "error": str(e)}


class BucketQuota(BaseModel):
    quota_bytes: int  # 바이트 단위 (0 = 무제한)
    quota_type: str = "hard"  # hard 또는 fifo


class StorageUser(BaseModel):
    access_key: str
    secret_key: str  # 최소 8자
    policy: str = "readwrite"  # 기본 정책


class UserPolicy(BaseModel):
    policy_name: str


# --- 소프트 쿼터 (애플리케이션 레벨) ---
# MinIO Admin API가 복잡하므로, 먼저 소프트 쿼터 구현

# 인메모리 쿼터 저장소 (실제로는 DB 사용 권장)
bucket_quotas = {}


@app.get("/api/storage/buckets/{bucket_name}/quota")
async def get_bucket_quota(bucket_name: str):
    """버킷 쿼터 조회"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # 현재 사용량 계산
        objects = list(client.list_objects(bucket_name, recursive=True))
        current_usage = sum(obj.size for obj in objects if obj.size)

        quota_info = bucket_quotas.get(bucket_name, {"quota_bytes": 0, "quota_type": "none"})

        return {
            "bucket": bucket_name,
            "quota_enabled": quota_info["quota_bytes"] > 0,
            "quota_bytes": quota_info["quota_bytes"],
            "quota_human": format_size(quota_info["quota_bytes"]) if quota_info["quota_bytes"] > 0 else "무제한",
            "quota_type": quota_info["quota_type"],
            "current_usage": current_usage,
            "current_usage_human": format_size(current_usage),
            "usage_percent": round(current_usage / quota_info["quota_bytes"] * 100, 1) if quota_info["quota_bytes"] > 0 else 0,
            "remaining": max(0, quota_info["quota_bytes"] - current_usage) if quota_info["quota_bytes"] > 0 else None,
            "remaining_human": format_size(max(0, quota_info["quota_bytes"] - current_usage)) if quota_info["quota_bytes"] > 0 else "무제한"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/buckets/{bucket_name}/quota")
async def set_bucket_quota(bucket_name: str, quota: BucketQuota):
    """버킷 쿼터 설정"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        if quota.quota_bytes == 0:
            # 쿼터 제거
            bucket_quotas.pop(bucket_name, None)
            return {"success": True, "message": f"버킷 '{bucket_name}'의 쿼터가 제거되었습니다"}
        else:
            bucket_quotas[bucket_name] = {
                "quota_bytes": quota.quota_bytes,
                "quota_type": quota.quota_type
            }
            return {
                "success": True,
                "message": f"버킷 '{bucket_name}'의 쿼터가 {format_size(quota.quota_bytes)}로 설정되었습니다"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/storage/buckets/{bucket_name}/quota")
async def delete_bucket_quota(bucket_name: str):
    """버킷 쿼터 제거"""
    try:
        bucket_quotas.pop(bucket_name, None)
        return {"success": True, "message": f"버킷 '{bucket_name}'의 쿼터가 제거되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 쿼터 체크 미들웨어 (업로드 시 체크) ---

async def check_quota_before_upload(bucket_name: str, file_size: int) -> bool:
    """업로드 전 쿼터 체크"""
    if bucket_name not in bucket_quotas:
        return True  # 쿼터 없음

    quota = bucket_quotas[bucket_name]
    if quota["quota_bytes"] == 0:
        return True

    client = get_minio_client()
    objects = list(client.list_objects(bucket_name, recursive=True))
    current_usage = sum(obj.size for obj in objects if obj.size)

    return (current_usage + file_size) <= quota["quota_bytes"]


# 기존 업로드 API에 쿼터 체크 추가
@app.post("/api/storage/buckets/{bucket_name}/objects/upload-with-quota")
async def upload_object_with_quota(bucket_name: str, upload: ObjectUpload):
    """객체 업로드 (쿼터 체크 포함)"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        content = base64.b64decode(upload.content)
        file_size = len(content)

        # 쿼터 체크
        if not await check_quota_before_upload(bucket_name, file_size):
            quota_info = bucket_quotas.get(bucket_name, {})
            raise HTTPException(
                status_code=413,
                detail=f"쿼터 초과! 버킷 쿼터: {format_size(quota_info.get('quota_bytes', 0))}"
            )

        # 업로드 진행
        from io import BytesIO
        content_type = upload.content_type or "application/octet-stream"
        client.put_object(
            bucket_name,
            upload.object_name,
            BytesIO(content),
            len(content),
            content_type=content_type
        )

        return {
            "success": True,
            "message": f"'{upload.object_name}'이 업로드되었습니다",
            "object_name": upload.object_name,
            "size": file_size,
            "size_human": format_size(file_size)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 사용자 관리 (소프트 구현) ---
# 실제 MinIO IAM 대신 애플리케이션 레벨 사용자 관리

storage_users = {
    "admin": {
        "secret_key": "admin1234",
        "policy": "admin",
        "status": "enabled",
        "buckets": ["*"]  # 모든 버킷 접근
    }
}


@app.get("/api/storage/users")
async def list_storage_users():
    """스토리지 사용자 목록"""
    users = []
    for access_key, info in storage_users.items():
        users.append({
            "access_key": access_key,
            "policy": info.get("policy", "readwrite"),
            "status": info.get("status", "enabled"),
            "buckets": info.get("buckets", [])
        })
    return {"users": users, "total": len(users)}


@app.post("/api/storage/users")
async def create_storage_user(user: StorageUser):
    """스토리지 사용자 생성"""
    if user.access_key in storage_users:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자입니다")
    if len(user.secret_key) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")

    storage_users[user.access_key] = {
        "secret_key": user.secret_key,
        "policy": user.policy,
        "status": "enabled",
        "buckets": []
    }
    return {"success": True, "message": f"사용자 '{user.access_key}'가 생성되었습니다"}


@app.delete("/api/storage/users/{access_key}")
async def delete_storage_user(access_key: str):
    """스토리지 사용자 삭제"""
    if access_key == "admin":
        raise HTTPException(status_code=400, detail="관리자 계정은 삭제할 수 없습니다")
    if access_key not in storage_users:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    del storage_users[access_key]
    return {"success": True, "message": f"사용자 '{access_key}'가 삭제되었습니다"}


@app.put("/api/storage/users/{access_key}/buckets")
async def set_user_buckets(access_key: str, buckets: list[str]):
    """사용자가 접근 가능한 버킷 설정"""
    if access_key not in storage_users:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    storage_users[access_key]["buckets"] = buckets
    return {"success": True, "message": f"사용자 '{access_key}'의 버킷 접근 권한이 설정되었습니다"}


@app.put("/api/storage/users/{access_key}/quota")
async def set_user_quota(access_key: str, quota_bytes: int):
    """사용자 총 쿼터 설정"""
    if access_key not in storage_users:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    storage_users[access_key]["quota_bytes"] = quota_bytes
    return {
        "success": True,
        "message": f"사용자 '{access_key}'의 쿼터가 {format_size(quota_bytes)}로 설정되었습니다"
    }


# --- 쿼터 프리셋 ---

@app.get("/api/storage/quota-presets")
async def get_quota_presets():
    """쿼터 프리셋 목록"""
    return {
        "presets": [
            {"name": "1GB", "bytes": 1 * 1024**3, "label": "1 GB"},
            {"name": "5GB", "bytes": 5 * 1024**3, "label": "5 GB"},
            {"name": "10GB", "bytes": 10 * 1024**3, "label": "10 GB"},
            {"name": "50GB", "bytes": 50 * 1024**3, "label": "50 GB"},
            {"name": "100GB", "bytes": 100 * 1024**3, "label": "100 GB"},
            {"name": "500GB", "bytes": 500 * 1024**3, "label": "500 GB"},
            {"name": "1TB", "bytes": 1 * 1024**4, "label": "1 TB"},
            {"name": "unlimited", "bytes": 0, "label": "무제한"}
        ]
    }


# --- 객체 잠금 (Object Lock / Legal Hold / Retention) ---

@app.get("/api/storage/buckets/{bucket_name}/object-lock")
async def get_bucket_object_lock_config(bucket_name: str):
    """버킷 객체 잠금 설정 조회"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        try:
            config = client.get_object_lock_config(bucket_name)
            return {
                "bucket": bucket_name,
                "enabled": True,
                "mode": config.mode if config else None,
                "duration": config.duration[1] if config and config.duration else None,
                "duration_unit": config.duration[0] if config and config.duration else None
            }
        except Exception as e:
            if "ObjectLockConfigurationNotFoundError" in str(e) or "does not have object lock" in str(e).lower():
                return {
                    "bucket": bucket_name,
                    "enabled": False,
                    "mode": None,
                    "duration": None,
                    "duration_unit": None,
                    "message": "객체 잠금이 활성화되지 않았습니다 (버킷 생성 시 설정 필요)"
                }
            raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ObjectLockConfig(BaseModel):
    mode: str = "GOVERNANCE"
    duration: int = 30
    duration_unit: str = "DAYS"


@app.put("/api/storage/buckets/{bucket_name}/object-lock")
async def set_bucket_object_lock_config(bucket_name: str, config: ObjectLockConfig):
    """버킷 객체 잠금 기본 보존 설정"""
    try:
        from minio.commonconfig import GOVERNANCE, COMPLIANCE

        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        mode = GOVERNANCE if config.mode == "GOVERNANCE" else COMPLIANCE
        duration = (config.duration_unit, config.duration)

        client.set_object_lock_config(bucket_name, mode, duration)

        return {
            "success": True,
            "message": f"버킷 '{bucket_name}'의 기본 보존 정책이 설정되었습니다",
            "mode": config.mode,
            "duration": f"{config.duration} {config.duration_unit}"
        }
    except HTTPException:
        raise
    except Exception as e:
        if "object lock" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail="이 버킷은 객체 잠금을 지원하지 않습니다. 버킷 생성 시 객체 잠금을 활성화해야 합니다."
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/legal-hold")
async def get_object_legal_hold(bucket_name: str, object_name: str, version_id: str = None):
    """객체 법적 보관 상태 조회"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        try:
            is_enabled = client.is_object_legal_hold_enabled(bucket_name, object_name, version_id=version_id)
            return {
                "bucket": bucket_name,
                "object_name": object_name,
                "version_id": version_id,
                "legal_hold_enabled": is_enabled
            }
        except Exception as e:
            if "object lock" in str(e).lower():
                return {
                    "bucket": bucket_name,
                    "object_name": object_name,
                    "legal_hold_enabled": False,
                    "message": "객체 잠금이 활성화되지 않았습니다"
                }
            raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class LegalHoldConfig(BaseModel):
    enabled: bool


@app.put("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/legal-hold")
async def set_object_legal_hold(bucket_name: str, object_name: str, config: LegalHoldConfig, version_id: str = None):
    """객체 법적 보관 설정"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        if config.enabled:
            client.enable_object_legal_hold(bucket_name, object_name, version_id=version_id)
            action = "활성화"
        else:
            client.disable_object_legal_hold(bucket_name, object_name, version_id=version_id)
            action = "비활성화"

        return {
            "success": True,
            "message": f"'{object_name}'의 법적 보관이 {action}되었습니다",
            "object_name": object_name,
            "legal_hold_enabled": config.enabled
        }
    except HTTPException:
        raise
    except Exception as e:
        if "object lock" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail="이 버킷은 객체 잠금을 지원하지 않습니다."
            )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/retention")
async def get_object_retention(bucket_name: str, object_name: str, version_id: str = None):
    """객체 보존 정책 조회"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        try:
            retention = client.get_object_retention(bucket_name, object_name, version_id=version_id)
            return {
                "bucket": bucket_name,
                "object_name": object_name,
                "version_id": version_id,
                "mode": retention.mode if retention else None,
                "retain_until_date": retention.retain_until_date.isoformat() if retention and retention.retain_until_date else None
            }
        except Exception as e:
            if "NoSuchObjectLockConfiguration" in str(e) or "object lock" in str(e).lower():
                return {
                    "bucket": bucket_name,
                    "object_name": object_name,
                    "mode": None,
                    "retain_until_date": None,
                    "message": "보존 정책이 설정되지 않았습니다"
                }
            raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RetentionConfig(BaseModel):
    mode: str = "GOVERNANCE"
    retain_until_date: str


@app.put("/api/storage/buckets/{bucket_name}/objects/{object_name:path}/retention")
async def set_object_retention(bucket_name: str, object_name: str, config: RetentionConfig, version_id: str = None):
    """객체 보존 정책 설정"""
    try:
        from minio.retention import Retention
        from minio.commonconfig import GOVERNANCE, COMPLIANCE
        from datetime import datetime

        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        mode = GOVERNANCE if config.mode == "GOVERNANCE" else COMPLIANCE
        retain_until = datetime.fromisoformat(config.retain_until_date.replace('Z', '+00:00'))

        retention = Retention(mode, retain_until)
        client.set_object_retention(bucket_name, object_name, retention, version_id=version_id)

        return {
            "success": True,
            "message": f"'{object_name}'의 보존 정책이 설정되었습니다",
            "object_name": object_name,
            "mode": config.mode,
            "retain_until_date": config.retain_until_date
        }
    except HTTPException:
        raise
    except Exception as e:
        if "object lock" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail="이 버킷은 객체 잠금을 지원하지 않습니다."
            )
        raise HTTPException(status_code=500, detail=str(e))


# --- MinIO IAM 관리 ---

@app.get("/api/storage/iam/users")
async def list_iam_users():
    """MinIO IAM 사용자 목록"""
    try:
        import subprocess
        result = subprocess.run(
            ["mc", "admin", "user", "list", "local", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        users = []
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("status") == "success":
                            users.append({
                                "accessKey": data.get("accessKey"),
                                "policyName": data.get("policyName"),
                                "userStatus": data.get("userStatus")
                            })
                    except:
                        pass

        return {"users": users, "total": len(users)}
    except FileNotFoundError:
        return await list_storage_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class IAMUser(BaseModel):
    access_key: str
    secret_key: str
    policy: str = "readwrite"


@app.post("/api/storage/iam/users")
async def create_iam_user(user: IAMUser):
    """MinIO IAM 사용자 생성"""
    try:
        import subprocess

        result = subprocess.run(
            ["mc", "admin", "user", "add", "local", user.access_key, user.secret_key],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=result.stderr or "사용자 생성 실패")

        if user.policy:
            subprocess.run(
                ["mc", "admin", "policy", "attach", "local", user.policy, "--user", user.access_key],
                capture_output=True,
                text=True,
                timeout=10
            )

        return {"success": True, "message": f"IAM 사용자 '{user.access_key}'가 생성되었습니다"}
    except FileNotFoundError:
        return await create_storage_user(StorageUser(
            access_key=user.access_key,
            secret_key=user.secret_key,
            policy=user.policy
        ))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/storage/iam/users/{access_key}")
async def delete_iam_user(access_key: str):
    """MinIO IAM 사용자 삭제"""
    try:
        import subprocess

        if access_key == "admin":
            raise HTTPException(status_code=400, detail="관리자 계정은 삭제할 수 없습니다")

        result = subprocess.run(
            ["mc", "admin", "user", "remove", "local", access_key],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=result.stderr or "사용자 삭제 실패")

        return {"success": True, "message": f"IAM 사용자 '{access_key}'가 삭제되었습니다"}
    except FileNotFoundError:
        return await delete_storage_user(access_key)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/iam/policies")
async def list_iam_policies():
    """MinIO 정책 목록"""
    try:
        import subprocess

        result = subprocess.run(
            ["mc", "admin", "policy", "list", "local", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        policies = []
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("status") == "success":
                            policies.append(data.get("policy"))
                    except:
                        pass

        if not policies:
            policies = ["readonly", "readwrite", "writeonly", "diagnostics", "consoleAdmin"]

        return {"policies": policies}
    except FileNotFoundError:
        return {"policies": ["readonly", "readwrite", "writeonly", "consoleAdmin"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/iam/users/{access_key}/policy")
async def attach_iam_policy(access_key: str, policy: str):
    """사용자에게 정책 할당"""
    try:
        import subprocess

        result = subprocess.run(
            ["mc", "admin", "policy", "attach", "local", policy, "--user", access_key],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=result.stderr or "정책 할당 실패")

        return {"success": True, "message": f"'{access_key}'에게 '{policy}' 정책이 할당되었습니다"}
    except FileNotFoundError:
        if access_key in storage_users:
            storage_users[access_key]["policy"] = policy
            return {"success": True, "message": f"'{access_key}'에게 '{policy}' 정책이 할당되었습니다"}
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/iam/users/{access_key}/info")
async def get_iam_user_info(access_key: str):
    """IAM 사용자 상세 정보"""
    try:
        import subprocess

        result = subprocess.run(
            ["mc", "admin", "user", "info", "local", access_key, "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "accessKey": data.get("accessKey"),
                "policyName": data.get("policyName"),
                "userStatus": data.get("userStatus"),
                "memberOf": data.get("memberOf", [])
            }
        else:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    except FileNotFoundError:
        if access_key in storage_users:
            info = storage_users[access_key]
            return {
                "accessKey": access_key,
                "policyName": info.get("policy"),
                "userStatus": info.get("status"),
                "memberOf": []
            }
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/iam/users/{access_key}/status")
async def set_iam_user_status(access_key: str, enabled: bool):
    """IAM 사용자 활성화/비활성화"""
    try:
        import subprocess

        action = "enable" if enabled else "disable"
        result = subprocess.run(
            ["mc", "admin", "user", action, "local", access_key],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=result.stderr or "상태 변경 실패")

        status = "활성화" if enabled else "비활성화"
        return {"success": True, "message": f"'{access_key}'가 {status}되었습니다"}
    except FileNotFoundError:
        if access_key in storage_users:
            storage_users[access_key]["status"] = "enabled" if enabled else "disabled"
            status = "활성화" if enabled else "비활성화"
            return {"success": True, "message": f"'{access_key}'가 {status}되었습니다"}
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 버킷 설정 통합 조회 ---

@app.get("/api/storage/buckets/{bucket_name}/settings")
async def get_bucket_settings(bucket_name: str):
    """버킷의 모든 설정 조회"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        settings = {
            "bucket": bucket_name,
            "versioning": {"enabled": False},
            "object_lock": {"enabled": False},
            "lifecycle": {"rules": []},
            "quota": bucket_quotas.get(bucket_name, {})
        }

        try:
            versioning = client.get_bucket_versioning(bucket_name)
            settings["versioning"]["enabled"] = versioning.status == "Enabled" if versioning else False
        except:
            pass

        try:
            lock_config = client.get_object_lock_config(bucket_name)
            settings["object_lock"]["enabled"] = True
            settings["object_lock"]["mode"] = lock_config.mode if lock_config else None
        except:
            pass

        try:
            lifecycle = client.get_bucket_lifecycle(bucket_name)
            if lifecycle:
                rules = []
                for rule in lifecycle.rules:
                    rules.append({
                        "id": rule.rule_id,
                        "enabled": rule.status == "Enabled",
                        "prefix": rule.rule_filter.prefix if rule.rule_filter else ""
                    })
                settings["lifecycle"]["rules"] = rules
        except:
            pass

        return settings
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 버킷별 사용자 접근 권한 및 할당량 관리
# ============================================

# 버킷별 사용자 접근 권한 저장소 (메모리)
bucket_user_permissions = {}  # {bucket_name: {user: {access: "read"|"write"|"admin", quota_bytes: int}}}


class BucketUserPermission(BaseModel):
    user: str
    access: str  # read, write, admin
    quota_gb: Optional[float] = None


@app.get("/api/storage/buckets/{bucket_name}/users")
async def get_bucket_users(bucket_name: str):
    """버킷의 사용자 접근 권한 목록"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        permissions = bucket_user_permissions.get(bucket_name, {})
        users_list = []

        for user, perm in permissions.items():
            users_list.append({
                "user": user,
                "access": perm.get("access", "read"),
                "quota_bytes": perm.get("quota_bytes"),
                "quota_human": format_size(perm.get("quota_bytes", 0)) if perm.get("quota_bytes") else None
            })

        return {
            "bucket": bucket_name,
            "users": users_list,
            "total": len(users_list)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/storage/buckets/{bucket_name}/users")
async def add_bucket_user(bucket_name: str, permission: BucketUserPermission):
    """버킷에 사용자 접근 권한 추가"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        # 사용자 존재 확인
        if permission.user not in storage_users and permission.user != "admin":
            raise HTTPException(status_code=404, detail=f"사용자 '{permission.user}'를 찾을 수 없습니다")

        if bucket_name not in bucket_user_permissions:
            bucket_user_permissions[bucket_name] = {}

        quota_bytes = int(permission.quota_gb * 1024 * 1024 * 1024) if permission.quota_gb else None

        bucket_user_permissions[bucket_name][permission.user] = {
            "access": permission.access,
            "quota_bytes": quota_bytes
        }

        # MinIO 버킷 정책 업데이트 (사용자별 정책 생성)
        try:
            await update_bucket_policy_for_user(client, bucket_name, permission.user, permission.access)
        except Exception as e:
            print(f"Failed to update bucket policy: {e}")

        return {
            "success": True,
            "message": f"'{permission.user}'에게 '{bucket_name}' 버킷 접근 권한이 부여되었습니다",
            "access": permission.access,
            "quota_gb": permission.quota_gb
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/storage/buckets/{bucket_name}/users/{user}")
async def remove_bucket_user(bucket_name: str, user: str):
    """버킷에서 사용자 접근 권한 제거"""
    try:
        if bucket_name not in bucket_user_permissions:
            raise HTTPException(status_code=404, detail="버킷 권한 정보를 찾을 수 없습니다")

        if user not in bucket_user_permissions[bucket_name]:
            raise HTTPException(status_code=404, detail=f"'{user}'의 권한을 찾을 수 없습니다")

        del bucket_user_permissions[bucket_name][user]

        return {
            "success": True,
            "message": f"'{user}'의 '{bucket_name}' 버킷 접근 권한이 제거되었습니다"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/buckets/{bucket_name}/users/{user}")
async def update_bucket_user(bucket_name: str, user: str, permission: BucketUserPermission):
    """버킷 사용자 권한 수정"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        if bucket_name not in bucket_user_permissions:
            bucket_user_permissions[bucket_name] = {}

        quota_bytes = int(permission.quota_gb * 1024 * 1024 * 1024) if permission.quota_gb else None

        bucket_user_permissions[bucket_name][user] = {
            "access": permission.access,
            "quota_bytes": quota_bytes
        }

        return {
            "success": True,
            "message": f"'{user}'의 권한이 업데이트되었습니다"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def update_bucket_policy_for_user(client, bucket_name: str, user: str, access: str):
    """사용자별 버킷 정책 업데이트"""
    try:
        # 기본 정책 템플릿
        if access == "read":
            actions = ["s3:GetObject", "s3:ListBucket"]
        elif access == "write":
            actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        elif access == "admin":
            actions = ["s3:*"]
        else:
            actions = ["s3:GetObject", "s3:ListBucket"]

        # 현재 정책 가져오기
        try:
            current_policy = client.get_bucket_policy(bucket_name)
            policy = json.loads(current_policy)
        except:
            policy = {
                "Version": "2012-10-17",
                "Statement": []
            }

        # 기존 사용자 정책 제거
        policy["Statement"] = [
            stmt for stmt in policy.get("Statement", [])
            if not (stmt.get("Sid", "").startswith(f"User{user}"))
        ]

        # 새 정책 추가
        new_statement = {
            "Sid": f"User{user}Access",
            "Effect": "Allow",
            "Principal": {"AWS": [f"arn:aws:iam:::user/{user}"]},
            "Action": actions,
            "Resource": [
                f"arn:aws:s3:::{bucket_name}",
                f"arn:aws:s3:::{bucket_name}/*"
            ]
        }
        policy["Statement"].append(new_statement)

        client.set_bucket_policy(bucket_name, json.dumps(policy))
    except Exception as e:
        print(f"Error updating bucket policy: {e}")


@app.get("/api/storage/buckets/{bucket_name}/quota")
async def get_bucket_quota(bucket_name: str):
    """버킷 할당량 조회"""
    try:
        quota = bucket_quotas.get(bucket_name, {})
        return {
            "bucket": bucket_name,
            "quota_bytes": quota.get("quota_bytes"),
            "quota_human": format_size(quota.get("quota_bytes", 0)) if quota.get("quota_bytes") else None,
            "used_bytes": quota.get("used_bytes", 0),
            "used_human": format_size(quota.get("used_bytes", 0))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/storage/buckets/{bucket_name}/quota")
async def set_bucket_quota(bucket_name: str, quota_gb: float = Query(..., gt=0)):
    """버킷 할당량 설정"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        quota_bytes = int(quota_gb * 1024 * 1024 * 1024)

        # 현재 사용량 계산
        objects = list(client.list_objects(bucket_name, recursive=True))
        used_bytes = sum(obj.size for obj in objects if obj.size)

        bucket_quotas[bucket_name] = {
            "quota_bytes": quota_bytes,
            "used_bytes": used_bytes
        }

        return {
            "success": True,
            "message": f"버킷 할당량이 {quota_gb}GB로 설정되었습니다",
            "quota_bytes": quota_bytes,
            "used_bytes": used_bytes
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Longhorn 스냅샷/볼륨 관리 API
# ============================================

class SnapshotCreate(BaseModel):
    name: str
    labels: Optional[dict] = None

class SnapshotRestore(BaseModel):
    snapshot_name: str

@app.get("/api/longhorn/volumes")
async def get_longhorn_volumes():
    """Longhorn 볼륨 목록 조회"""
    try:
        _, _, custom_api = get_k8s_clients()

        volumes = custom_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes"
        )

        result = []
        for vol in volumes.get("items", []):
            spec = vol.get("spec", {})
            status = vol.get("status", {})

            result.append({
                "name": vol["metadata"]["name"],
                "size": spec.get("size", "0"),
                "size_human": format_size(int(spec.get("size", 0))),
                "numberOfReplicas": spec.get("numberOfReplicas", 1),
                "state": status.get("state", "unknown"),
                "robustness": status.get("robustness", "unknown"),
                "frontend": spec.get("frontend", ""),
                "created": vol["metadata"].get("creationTimestamp", ""),
                "pvc": spec.get("Kubernetes", {}).get("pvName", ""),
                "pvc_name": spec.get("Kubernetes", {}).get("pvcName", ""),
                "pvc_namespace": spec.get("Kubernetes", {}).get("namespace", ""),
            })

        return {"volumes": result}
    except ApiException as e:
        if e.status == 404:
            return {"volumes": [], "message": "Longhorn not installed"}
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/longhorn/volumes/{volume_name}")
async def get_longhorn_volume(volume_name: str):
    """특정 Longhorn 볼륨 상세 정보"""
    try:
        _, _, custom_api = get_k8s_clients()

        vol = custom_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name
        )

        spec = vol.get("spec", {})
        status = vol.get("status", {})

        return {
            "name": vol["metadata"]["name"],
            "size": spec.get("size", "0"),
            "size_human": format_size(int(spec.get("size", 0))),
            "numberOfReplicas": spec.get("numberOfReplicas", 1),
            "state": status.get("state", "unknown"),
            "robustness": status.get("robustness", "unknown"),
            "frontend": spec.get("frontend", ""),
            "created": vol["metadata"].get("creationTimestamp", ""),
            "conditions": status.get("conditions", []),
            "currentSize": status.get("currentSize", 0),
            "actualSize": status.get("actualSize", 0),
        }
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/longhorn/volumes/{volume_name}/snapshots")
async def get_volume_snapshots(volume_name: str):
    """볼륨의 스냅샷 목록 조회"""
    try:
        _, _, custom_api = get_k8s_clients()

        snapshots = custom_api.list_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="snapshots"
        )

        result = []
        for snap in snapshots.get("items", []):
            spec = snap.get("spec", {})
            status = snap.get("status", {})

            # 해당 볼륨의 스냅샷만 필터링
            if spec.get("volume") != volume_name:
                continue

            result.append({
                "name": snap["metadata"]["name"],
                "volume": spec.get("volume", ""),
                "created": snap["metadata"].get("creationTimestamp", ""),
                "size": status.get("size", 0),
                "size_human": format_size(int(status.get("size", 0))),
                "state": status.get("state", "unknown"),
                "ready": status.get("readyToUse", False),
                "labels": spec.get("labels", {}),
            })

        # 생성 시간 기준 정렬 (최신순)
        result.sort(key=lambda x: x["created"], reverse=True)

        return {"snapshots": result, "volume": volume_name}
    except ApiException as e:
        if e.status == 404:
            return {"snapshots": [], "volume": volume_name}
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/longhorn/volumes/{volume_name}/snapshots")
async def create_volume_snapshot(volume_name: str, data: SnapshotCreate):
    """볼륨 스냅샷 생성"""
    try:
        _, _, custom_api = get_k8s_clients()

        # 볼륨 존재 확인
        try:
            custom_api.get_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumes",
                name=volume_name
            )
        except ApiException:
            raise HTTPException(status_code=404, detail=f"볼륨 '{volume_name}'을 찾을 수 없습니다")

        # 스냅샷 이름 생성
        import time
        snapshot_name = f"{data.name}-{int(time.time())}"

        snapshot_manifest = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Snapshot",
            "metadata": {
                "name": snapshot_name,
                "namespace": "longhorn-system"
            },
            "spec": {
                "volume": volume_name,
                "labels": data.labels or {"created-by": "k3s-dashboard"}
            }
        }

        result = custom_api.create_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="snapshots",
            body=snapshot_manifest
        )

        return {
            "success": True,
            "message": f"스냅샷 '{snapshot_name}'이 생성되었습니다",
            "snapshot": {
                "name": snapshot_name,
                "volume": volume_name
            }
        }
    except HTTPException:
        raise
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/longhorn/snapshots/{snapshot_name}")
async def delete_snapshot(snapshot_name: str):
    """스냅샷 삭제"""
    try:
        _, _, custom_api = get_k8s_clients()

        custom_api.delete_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="snapshots",
            name=snapshot_name
        )

        return {
            "success": True,
            "message": f"스냅샷 '{snapshot_name}'이 삭제되었습니다"
        }
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/longhorn/volumes/{volume_name}/restore")
async def restore_volume_snapshot(volume_name: str, data: SnapshotRestore):
    """스냅샷에서 볼륨 복원 (새 볼륨 생성)"""
    try:
        _, _, custom_api = get_k8s_clients()

        # 원본 볼륨 정보 가져오기
        orig_vol = custom_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name
        )

        # 스냅샷 확인
        snapshot = custom_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="snapshots",
            name=data.snapshot_name
        )

        if snapshot.get("spec", {}).get("volume") != volume_name:
            raise HTTPException(status_code=400, detail="스냅샷이 해당 볼륨에 속하지 않습니다")

        import time
        new_volume_name = f"{volume_name}-restored-{int(time.time())}"

        # 새 볼륨 생성 (스냅샷에서 복원)
        new_volume_manifest = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Volume",
            "metadata": {
                "name": new_volume_name,
                "namespace": "longhorn-system"
            },
            "spec": {
                "size": orig_vol["spec"].get("size", "10737418240"),
                "numberOfReplicas": orig_vol["spec"].get("numberOfReplicas", 1),
                "fromBackup": "",
                "dataSource": data.snapshot_name,
                "frontend": "blockdev"
            }
        }

        result = custom_api.create_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            body=new_volume_manifest
        )

        return {
            "success": True,
            "message": f"스냅샷에서 새 볼륨 '{new_volume_name}'이 생성되었습니다",
            "new_volume": new_volume_name,
            "source_snapshot": data.snapshot_name
        }
    except HTTPException:
        raise
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/longhorn/volumes/{volume_name}/expand")
async def expand_volume(volume_name: str, size_gb: int):
    """볼륨 확장 (동적)"""
    try:
        core_v1, _, custom_api = get_k8s_clients()

        # Longhorn 볼륨 정보 가져오기
        vol = custom_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace="longhorn-system",
            plural="volumes",
            name=volume_name
        )

        current_size = int(vol["spec"].get("size", 0))
        new_size = size_gb * 1024 * 1024 * 1024

        if new_size <= current_size:
            raise HTTPException(status_code=400, detail="새 크기는 현재 크기보다 커야 합니다")

        # PVC 이름 가져오기
        pvc_name = vol["spec"].get("Kubernetes", {}).get("pvcName", "")
        pvc_namespace = vol["spec"].get("Kubernetes", {}).get("namespace", "")

        if pvc_name and pvc_namespace:
            # PVC 크기 확장
            pvc = core_v1.read_namespaced_persistent_volume_claim(pvc_name, pvc_namespace)
            pvc.spec.resources.requests["storage"] = f"{size_gb}Gi"
            core_v1.patch_namespaced_persistent_volume_claim(pvc_name, pvc_namespace, pvc)

            return {
                "success": True,
                "message": f"PVC '{pvc_name}'이 {size_gb}GB로 확장 요청되었습니다",
                "previous_size": format_size(current_size),
                "new_size": f"{size_gb}GB"
            }
        else:
            raise HTTPException(status_code=400, detail="연결된 PVC를 찾을 수 없습니다")
    except HTTPException:
        raise
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/longhorn/status")
async def get_longhorn_status():
    """Longhorn 전체 상태"""
    try:
        core_v1, _, custom_api = get_k8s_clients()

        # Longhorn 노드 상태
        try:
            nodes = custom_api.list_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="nodes"
            )

            node_info = []
            total_storage = 0
            used_storage = 0

            for node in nodes.get("items", []):
                status = node.get("status", {})
                disks = status.get("diskStatus", {})

                for disk_id, disk_status in disks.items():
                    conditions = disk_status.get("conditions", [])
                    # conditions가 리스트일 경우 딕셔너리로 변환
                    if isinstance(conditions, list):
                        conditions_dict = {c.get("type"): c for c in conditions}
                    else:
                        conditions_dict = conditions
                    schedulable = conditions_dict.get("Schedulable", {}).get("status") == "True"
                    ready = conditions_dict.get("Ready", {}).get("status") == "True"

                    storage_max = int(disk_status.get("storageMaximum", 0))
                    storage_avail = int(disk_status.get("storageAvailable", 0))

                    total_storage += storage_max
                    used_storage += (storage_max - storage_avail)

                    node_info.append({
                        "node": node["metadata"]["name"],
                        "disk_id": disk_id,
                        "schedulable": schedulable,
                        "ready": ready,
                        "storage_max": format_size(storage_max),
                        "storage_available": format_size(storage_avail),
                        "storage_used": format_size(storage_max - storage_avail),
                    })

            # 볼륨 수
            volumes = custom_api.list_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace="longhorn-system",
                plural="volumes"
            )

            return {
                "installed": True,
                "nodes": node_info,
                "total_storage": format_size(total_storage),
                "used_storage": format_size(used_storage),
                "available_storage": format_size(total_storage - used_storage),
                "usage_percent": round((used_storage / total_storage * 100), 1) if total_storage > 0 else 0,
                "volume_count": len(volumes.get("items", []))
            }
        except ApiException as e:
            if e.status == 404:
                return {"installed": False, "message": "Longhorn이 설치되어 있지 않습니다"}
            raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 클러스터 노드 관리 API
# ============================================

class NodeJoinInfo(BaseModel):
    """노드 조인 정보"""
    node_ip: str
    node_name: Optional[str] = None
    role: str = "worker"  # worker, master


@app.get("/api/cluster/nodes")
async def get_cluster_nodes():
    """클러스터 노드 목록 및 상세 정보 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        result = []
        for node in nodes.items:
            node_name = node.metadata.name
            labels = node.metadata.labels or {}

            # 노드 역할 판별
            is_master = "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels
            role = "master" if is_master else "worker"

            # 상태 확인
            conditions = {c.type: c.status for c in node.status.conditions} if node.status.conditions else {}
            is_ready = conditions.get("Ready") == "True"

            # 리소스 정보
            allocatable = node.status.allocatable or {}
            capacity = node.status.capacity or {}

            # 주소 정보
            addresses = {addr.type: addr.address for addr in node.status.addresses} if node.status.addresses else {}

            # 노드 정보
            node_info = node.status.node_info

            # 이 노드의 Pod 수
            pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
            pod_count = len(pods.items)

            # GPU 정보
            gpu_count = int(capacity.get("nvidia.com/gpu", 0))

            result.append({
                "name": node_name,
                "role": role,
                "status": "Ready" if is_ready else "NotReady",
                "internal_ip": addresses.get("InternalIP", ""),
                "external_ip": addresses.get("ExternalIP", ""),
                "hostname": addresses.get("Hostname", node_name),
                "os": node_info.os_image if node_info else "",
                "kernel": node_info.kernel_version if node_info else "",
                "container_runtime": node_info.container_runtime_version if node_info else "",
                "kubelet_version": node_info.kubelet_version if node_info else "",
                "cpu_capacity": capacity.get("cpu", "0"),
                "cpu_allocatable": allocatable.get("cpu", "0"),
                "memory_capacity": capacity.get("memory", "0"),
                "memory_allocatable": allocatable.get("memory", "0"),
                "storage_capacity": capacity.get("ephemeral-storage", "0"),
                "gpu_count": gpu_count,
                "pod_count": pod_count,
                "pod_capacity": int(allocatable.get("pods", 110)),
                "labels": labels,
                "taints": [{"key": t.key, "value": t.value, "effect": t.effect} for t in (node.spec.taints or [])],
                "created": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else None
            })

        return {
            "nodes": result,
            "total": len(result),
            "master_count": sum(1 for n in result if n["role"] == "master"),
            "worker_count": sum(1 for n in result if n["role"] == "worker"),
            "ready_count": sum(1 for n in result if n["status"] == "Ready")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cluster/nodes/{node_name}")
async def get_node_detail(node_name: str):
    """특정 노드 상세 정보 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        try:
            node = core_v1.read_node(node_name)
        except ApiException as e:
            if e.status == 404:
                raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
            raise

        # 노드의 Pod 목록
        pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
        pod_list = []
        for pod in pods.items:
            pod_list.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip
            })

        # 노드 이벤트
        events = core_v1.list_event_for_all_namespaces(
            field_selector=f"involvedObject.name={node_name},involvedObject.kind=Node"
        )
        event_list = []
        for event in events.items[:20]:  # 최근 20개만
            event_list.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "time": event.last_timestamp.isoformat() if event.last_timestamp else None
            })

        labels = node.metadata.labels or {}
        allocatable = node.status.allocatable or {}
        capacity = node.status.capacity or {}
        addresses = {addr.type: addr.address for addr in node.status.addresses} if node.status.addresses else {}
        node_info = node.status.node_info
        is_master = "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels

        return {
            "name": node_name,
            "role": "master" if is_master else "worker",
            "internal_ip": addresses.get("InternalIP", ""),
            "os": node_info.os_image if node_info else "",
            "kernel": node_info.kernel_version if node_info else "",
            "architecture": node_info.architecture if node_info else "",
            "container_runtime": node_info.container_runtime_version if node_info else "",
            "kubelet_version": node_info.kubelet_version if node_info else "",
            "cpu_capacity": capacity.get("cpu", "0"),
            "memory_capacity": capacity.get("memory", "0"),
            "gpu_count": int(capacity.get("nvidia.com/gpu", 0)),
            "pods": pod_list,
            "pod_count": len(pod_list),
            "events": event_list,
            "labels": labels,
            "taints": [{"key": t.key, "value": t.value, "effect": t.effect} for t in (node.spec.taints or [])]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cluster/join-command")
async def get_join_command():
    """새 노드 조인을 위한 명령어 생성"""
    try:
        # K3s 토큰 읽기 (마스터 노드에서만 가능)
        token_path = "/var/lib/rancher/k3s/server/node-token"

        # 클러스터 내에서 실행 중이면 ConfigMap이나 Secret에서 가져오기
        core_v1, _, _ = get_k8s_clients()

        # 마스터 노드 IP 가져오기
        nodes = core_v1.list_node()
        master_ip = None
        for node in nodes.items:
            labels = node.metadata.labels or {}
            if "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels:
                for addr in node.status.addresses:
                    if addr.type == "InternalIP":
                        master_ip = addr.address
                        break
                break

        if not master_ip:
            # 첫 번째 노드 IP 사용
            if nodes.items:
                for addr in nodes.items[0].status.addresses:
                    if addr.type == "InternalIP":
                        master_ip = addr.address
                        break

        return {
            "master_ip": master_ip,
            "instructions": {
                "worker": f"""# 워커 노드에서 실행:
# 1. K3s 설치 스크립트 다운로드
curl -sfL https://get.k3s.io | K3S_URL=https://{master_ip}:6443 K3S_TOKEN=<NODE_TOKEN> sh -

# NODE_TOKEN은 마스터 노드에서 확인:
# sudo cat /var/lib/rancher/k3s/server/node-token""",
                "master": f"""# 추가 마스터 노드 (HA 구성):
curl -sfL https://get.k3s.io | K3S_TOKEN=<NODE_TOKEN> sh -s - server --server https://{master_ip}:6443"""
            },
            "note": "NODE_TOKEN은 마스터 노드의 /var/lib/rancher/k3s/server/node-token 파일에서 확인하세요."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cluster/nodes/{node_name}/cordon")
async def cordon_node(node_name: str):
    """노드 스케줄링 비활성화 (cordon)"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # 노드에 unschedulable 설정
        body = {"spec": {"unschedulable": True}}
        core_v1.patch_node(node_name, body)

        return {"message": f"노드 '{node_name}'의 스케줄링이 비활성화되었습니다", "status": "cordoned"}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cluster/nodes/{node_name}/uncordon")
async def uncordon_node(node_name: str):
    """노드 스케줄링 활성화 (uncordon)"""
    try:
        core_v1, _, _ = get_k8s_clients()

        body = {"spec": {"unschedulable": False}}
        core_v1.patch_node(node_name, body)

        return {"message": f"노드 '{node_name}'의 스케줄링이 활성화되었습니다", "status": "uncordoned"}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cluster/nodes/{node_name}/drain")
async def drain_node(node_name: str, force: bool = False):
    """노드 드레인 (Pod 퇴거)"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # 먼저 cordon
        body = {"spec": {"unschedulable": True}}
        core_v1.patch_node(node_name, body)

        # 노드의 Pod 목록 (DaemonSet 제외)
        pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")

        evicted = []
        skipped = []

        for pod in pods.items:
            # DaemonSet Pod는 건너뛰기
            if pod.metadata.owner_references:
                is_daemonset = any(ref.kind == "DaemonSet" for ref in pod.metadata.owner_references)
                if is_daemonset:
                    skipped.append(f"{pod.metadata.namespace}/{pod.metadata.name} (DaemonSet)")
                    continue

            # 시스템 네임스페이스의 중요 Pod 건너뛰기
            if pod.metadata.namespace in ["kube-system"] and not force:
                skipped.append(f"{pod.metadata.namespace}/{pod.metadata.name} (system)")
                continue

            try:
                # Pod 삭제 (eviction)
                core_v1.delete_namespaced_pod(
                    pod.metadata.name,
                    pod.metadata.namespace,
                    grace_period_seconds=30
                )
                evicted.append(f"{pod.metadata.namespace}/{pod.metadata.name}")
            except ApiException:
                skipped.append(f"{pod.metadata.namespace}/{pod.metadata.name} (삭제 실패)")

        return {
            "message": f"노드 '{node_name}' 드레인 완료",
            "evicted": evicted,
            "skipped": skipped,
            "evicted_count": len(evicted),
            "skipped_count": len(skipped)
        }
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cluster/nodes/{node_name}")
async def delete_node(node_name: str):
    """클러스터에서 노드 제거"""
    try:
        core_v1, _, _ = get_k8s_clients()

        # 노드 삭제
        core_v1.delete_node(node_name)

        return {"message": f"노드 '{node_name}'이 클러스터에서 제거되었습니다"}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/cluster/nodes/{node_name}/labels")
async def update_node_labels(node_name: str, labels: dict):
    """노드 레이블 업데이트"""
    try:
        core_v1, _, _ = get_k8s_clients()

        body = {"metadata": {"labels": labels}}
        core_v1.patch_node(node_name, body)

        return {"message": f"노드 '{node_name}'의 레이블이 업데이트되었습니다", "labels": labels}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"노드 '{node_name}'을 찾을 수 없습니다")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cluster/resources")
async def get_cluster_resources():
    """클러스터 전체 리소스 현황"""
    try:
        core_v1, _, _ = get_k8s_clients()
        nodes = core_v1.list_node()

        total_cpu = 0
        total_memory = 0
        total_gpu = 0
        total_pods_capacity = 0
        total_pods_used = 0

        for node in nodes.items:
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}

            # CPU (코어 단위로 변환)
            cpu_str = capacity.get("cpu", "0")
            if cpu_str.endswith("m"):
                total_cpu += int(cpu_str[:-1]) / 1000
            else:
                total_cpu += int(cpu_str)

            # 메모리 (bytes로 변환)
            mem_str = capacity.get("memory", "0")
            if mem_str.endswith("Ki"):
                total_memory += int(mem_str[:-2]) * 1024
            elif mem_str.endswith("Mi"):
                total_memory += int(mem_str[:-2]) * 1024 * 1024
            elif mem_str.endswith("Gi"):
                total_memory += int(mem_str[:-2]) * 1024 * 1024 * 1024

            # GPU
            total_gpu += int(capacity.get("nvidia.com/gpu", 0))

            # Pods
            total_pods_capacity += int(allocatable.get("pods", 110))

            # 이 노드의 Pod 수
            pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node.metadata.name}")
            total_pods_used += len(pods.items)

        def format_memory(bytes_val):
            if bytes_val >= 1024**4:
                return f"{bytes_val / (1024**4):.1f} TB"
            elif bytes_val >= 1024**3:
                return f"{bytes_val / (1024**3):.1f} GB"
            elif bytes_val >= 1024**2:
                return f"{bytes_val / (1024**2):.1f} MB"
            return f"{bytes_val} B"

        return {
            "cpu": {
                "total": total_cpu,
                "unit": "cores"
            },
            "memory": {
                "total": total_memory,
                "total_human": format_memory(total_memory)
            },
            "gpu": {
                "total": total_gpu
            },
            "pods": {
                "used": total_pods_used,
                "capacity": total_pods_capacity,
                "usage_percent": round(total_pods_used / total_pods_capacity * 100, 1) if total_pods_capacity > 0 else 0
            },
            "nodes": {
                "total": len(nodes.items)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 로그 및 이벤트 API
# ============================================

@app.get("/api/events")
async def get_cluster_events(namespace: str = None, limit: int = 100):
    """클러스터 이벤트 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        if namespace:
            events = core_v1.list_namespaced_event(namespace)
        else:
            events = core_v1.list_event_for_all_namespaces()

        # 최신순 정렬
        sorted_events = sorted(
            events.items,
            key=lambda e: e.last_timestamp or e.metadata.creation_timestamp or datetime.min.replace(tzinfo=None),
            reverse=True
        )[:limit]

        result = []
        for event in sorted_events:
            result.append({
                "name": event.metadata.name,
                "namespace": event.metadata.namespace,
                "type": event.type,  # Normal, Warning
                "reason": event.reason,
                "message": event.message,
                "source": event.source.component if event.source else "",
                "object": {
                    "kind": event.involved_object.kind if event.involved_object else "",
                    "name": event.involved_object.name if event.involved_object else ""
                },
                "count": event.count or 1,
                "first_timestamp": event.first_timestamp.isoformat() if event.first_timestamp else None,
                "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None
            })

        # 통계
        warning_count = sum(1 for e in result if e["type"] == "Warning")
        normal_count = sum(1 for e in result if e["type"] == "Normal")

        return {
            "events": result,
            "total": len(result),
            "warning_count": warning_count,
            "normal_count": normal_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/{namespace}/{pod_name}")
async def get_pod_logs(namespace: str, pod_name: str, container: str = None, tail_lines: int = 100):
    """Pod 로그 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        kwargs = {"tail_lines": tail_lines}
        if container:
            kwargs["container"] = container

        logs = core_v1.read_namespaced_pod_log(pod_name, namespace, **kwargs)

        # 로그를 라인별로 파싱하고 에러/경고 탐지
        lines = []
        error_count = 0
        warning_count = 0

        for line in logs.split("\n"):
            line_lower = line.lower()
            level = "info"
            if "error" in line_lower or "exception" in line_lower or "fail" in line_lower:
                level = "error"
                error_count += 1
            elif "warn" in line_lower:
                level = "warning"
                warning_count += 1

            lines.append({
                "content": line,
                "level": level
            })

        return {
            "pod": pod_name,
            "namespace": namespace,
            "container": container,
            "lines": lines,
            "total_lines": len(lines),
            "error_count": error_count,
            "warning_count": warning_count
        }
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Pod {pod_name} not found")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 임베딩 API
# ============================================

from typing import List

class EmbeddingRequest(BaseModel):
    text: str
    model: str = "BAAI/bge-m3"
    return_sparse: bool = True
    return_dense: bool = True

class EmbeddingCompareRequest(BaseModel):
    text1: str
    text2: str
    model: str = "BAAI/bge-m3"

# 클러스터 내 임베딩 서비스 URL
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service.ai-workloads.svc.cluster.local:8080")

@app.get("/api/embedding/models")
async def get_available_models():
    """사용 가능한 임베딩 모델 목록 반환"""
    return {
        "models": get_model_status(),
        "loaded_count": len(_embedding_models),
        "total_count": len(SUPPORTED_EMBEDDING_MODELS)
    }

@app.post("/api/embedding/models/{model_id:path}/load")
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

@app.get("/api/embedding/models/{model_id:path}/status")
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

@app.post("/api/embedding/generate")
async def generate_embedding(request: EmbeddingRequest):
    """텍스트를 임베딩 벡터로 변환 (실제 모델 사용)"""
    import time
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
                import hashlib
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


@app.post("/api/embedding/compare")
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


@app.get("/api/embedding/storage-format")
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


@app.get("/api/pipeline/status")
async def get_pipeline_status():
    """AI 파이프라인 상태 및 연결 상태 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        # 각 워크로드 상태 확인
        pipeline_components = {
            "vllm": {"name": "vLLM", "icon": "🤖", "role": "LLM 추론", "status": "stopped", "connections": ["qdrant", "neo4j", "embedding"]},
            "embedding": {"name": "Embedding", "icon": "🧠", "role": "텍스트 임베딩", "status": "stopped", "connections": ["qdrant", "vllm"]},
            "qdrant": {"name": "Qdrant", "icon": "🔍", "role": "벡터 검색", "status": "stopped", "connections": ["vllm", "embedding"]},
            "neo4j": {"name": "Neo4j", "icon": "🕸️", "role": "그래프 DB", "status": "stopped", "connections": ["vllm"]},
            "comfyui": {"name": "ComfyUI", "icon": "🎨", "role": "이미지 생성", "status": "stopped", "connections": ["rustfs"]},
            "rustfs": {"name": "RustFS", "icon": "💾", "role": "오브젝트 저장소", "status": "stopped", "connections": ["comfyui"]}
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


# ============================================
# Ontology (Neo4j) 라이브 데모 API
# ============================================

class CypherQueryRequest(BaseModel):
    query: str
    params: dict = {}

class OntologyNodeRequest(BaseModel):
    label: str
    properties: dict

class OntologyRelationRequest(BaseModel):
    from_node: dict  # {"label": "Person", "property": "name", "value": "John"}
    to_node: dict
    relation_type: str
    properties: dict = {}


@app.post("/api/ontology/query")
async def execute_cypher_query(request: CypherQueryRequest):
    """Cypher 쿼리 실행 (라이브 또는 시뮬레이션)"""
    try:
        # 실제 Neo4j 연결 시도
        neo4j_host = "neo4j.ai-workloads.svc.cluster.local"
        neo4j_port = 7687

        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((neo4j_host, neo4j_port))
            sock.close()

            if result == 0:
                # 실제 Neo4j 쿼리 실행
                from neo4j import GraphDatabase
                driver = GraphDatabase.driver(f"bolt://{neo4j_host}:{neo4j_port}", auth=("neo4j", "password"))
                with driver.session() as session:
                    result = session.run(request.query, request.params)
                    records = [dict(record) for record in result]
                driver.close()

                return {
                    "success": True,
                    "mode": "live",
                    "results": records,
                    "query": request.query
                }
        except:
            pass

        # 시뮬레이션 모드 - 예제 쿼리에 대한 샘플 응답
        simulated_results = get_simulated_cypher_results(request.query)

        return {
            "success": True,
            "mode": "simulation",
            "results": simulated_results,
            "query": request.query,
            "note": "Neo4j 미연결 - 시뮬레이션 데이터"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_simulated_cypher_results(query: str):
    """시뮬레이션 Cypher 결과"""
    query_lower = query.lower()

    # 노드 조회 쿼리
    if "match (n)" in query_lower or "match (p:person)" in query_lower:
        return [
            {"n": {"id": 1, "label": "Person", "name": "김철수", "role": "Developer"}},
            {"n": {"id": 2, "label": "Person", "name": "이영희", "role": "Manager"}},
            {"n": {"id": 3, "label": "Company", "name": "TechCorp", "industry": "IT"}},
            {"n": {"id": 4, "label": "Project", "name": "AI Platform", "status": "active"}},
            {"n": {"id": 5, "label": "Technology", "name": "Kubernetes", "category": "Infrastructure"}}
        ]

    # 관계 조회 쿼리
    if "match (a)-[r]->(b)" in query_lower or "->" in query_lower:
        return [
            {"a": {"label": "Person", "name": "김철수"}, "r": {"type": "WORKS_AT"}, "b": {"label": "Company", "name": "TechCorp"}},
            {"a": {"label": "Person", "name": "이영희"}, "r": {"type": "MANAGES"}, "b": {"label": "Project", "name": "AI Platform"}},
            {"a": {"label": "Project", "name": "AI Platform"}, "r": {"type": "USES"}, "b": {"label": "Technology", "name": "Kubernetes"}},
            {"a": {"label": "Person", "name": "김철수"}, "r": {"type": "CONTRIBUTES_TO"}, "b": {"label": "Project", "name": "AI Platform"}}
        ]

    # 경로 쿼리
    if "shortestpath" in query_lower or "path" in query_lower:
        return [
            {
                "path": {
                    "nodes": [
                        {"label": "Person", "name": "김철수"},
                        {"label": "Project", "name": "AI Platform"},
                        {"label": "Technology", "name": "Kubernetes"}
                    ],
                    "relationships": [
                        {"type": "CONTRIBUTES_TO"},
                        {"type": "USES"}
                    ]
                }
            }
        ]

    # 집계 쿼리
    if "count" in query_lower:
        return [{"count": 42}]

    # 기본 응답
    return [
        {"message": "쿼리 실행됨", "affected_rows": 0}
    ]


@app.get("/api/ontology/schema")
async def get_ontology_schema():
    """온톨로지 스키마 정보 - RDBMS vs Graph 비교"""
    return {
        "rdbms_schema": {
            "tables": [
                {
                    "name": "employees",
                    "columns": ["id INT PK", "name VARCHAR", "department_id FK", "manager_id FK"],
                    "description": "직원 테이블"
                },
                {
                    "name": "departments",
                    "columns": ["id INT PK", "name VARCHAR", "location VARCHAR"],
                    "description": "부서 테이블"
                },
                {
                    "name": "projects",
                    "columns": ["id INT PK", "name VARCHAR", "start_date DATE"],
                    "description": "프로젝트 테이블"
                },
                {
                    "name": "employee_projects",
                    "columns": ["employee_id FK", "project_id FK", "role VARCHAR"],
                    "description": "직원-프로젝트 관계 테이블"
                }
            ],
            "sql_example": """
SELECT e.name, d.name as dept, p.name as project
FROM employees e
JOIN departments d ON e.department_id = d.id
JOIN employee_projects ep ON e.id = ep.employee_id
JOIN projects p ON ep.project_id = p.id
WHERE e.manager_id = (SELECT id FROM employees WHERE name = '김철수')
""".strip()
        },
        "graph_schema": {
            "nodes": [
                {"label": "Person", "properties": ["name", "role", "email"], "color": "#4ecdc4"},
                {"label": "Department", "properties": ["name", "location"], "color": "#45b7d1"},
                {"label": "Project", "properties": ["name", "status", "startDate"], "color": "#96ceb4"},
                {"label": "Technology", "properties": ["name", "category", "version"], "color": "#ffeaa7"}
            ],
            "relationships": [
                {"type": "WORKS_IN", "from": "Person", "to": "Department", "properties": ["since"]},
                {"type": "MANAGES", "from": "Person", "to": "Person", "properties": []},
                {"type": "CONTRIBUTES_TO", "from": "Person", "to": "Project", "properties": ["role", "hours"]},
                {"type": "USES", "from": "Project", "to": "Technology", "properties": []},
                {"type": "KNOWS", "from": "Person", "to": "Technology", "properties": ["level"]}
            ],
            "cypher_example": """
MATCH (p:Person)-[:MANAGES]->(team:Person)-[:CONTRIBUTES_TO]->(proj:Project)
WHERE p.name = '김철수'
RETURN team.name, proj.name
""".strip()
        },
        "comparison": {
            "joins_vs_traversal": {
                "rdbms": "여러 JOIN 필요 (복잡한 관계에서 성능 저하)",
                "graph": "관계 직접 탐색 (깊은 관계도 O(1))"
            },
            "schema_flexibility": {
                "rdbms": "스키마 변경 시 마이그레이션 필요",
                "graph": "노드/관계 동적 추가 가능"
            },
            "query_complexity": {
                "rdbms": "n-depth 관계 → n개 JOIN",
                "graph": "n-depth 관계 → 단일 패턴 매칭"
            }
        }
    }


@app.get("/api/ontology/graph-data")
async def get_sample_graph_data():
    """시각화용 샘플 그래프 데이터"""
    return {
        "nodes": [
            {"id": "1", "label": "Person", "name": "김철수", "properties": {"role": "Developer"}, "x": 100, "y": 200},
            {"id": "2", "label": "Person", "name": "이영희", "properties": {"role": "Manager"}, "x": 300, "y": 100},
            {"id": "3", "label": "Department", "name": "Engineering", "properties": {"location": "서울"}, "x": 300, "y": 300},
            {"id": "4", "label": "Project", "name": "AI Platform", "properties": {"status": "active"}, "x": 500, "y": 200},
            {"id": "5", "label": "Technology", "name": "Kubernetes", "properties": {"category": "Infrastructure"}, "x": 700, "y": 150},
            {"id": "6", "label": "Technology", "name": "Python", "properties": {"category": "Language"}, "x": 700, "y": 250}
        ],
        "edges": [
            {"from": "1", "to": "3", "type": "WORKS_IN", "properties": {}},
            {"from": "2", "to": "1", "type": "MANAGES", "properties": {}},
            {"from": "1", "to": "4", "type": "CONTRIBUTES_TO", "properties": {"role": "Lead"}},
            {"from": "2", "to": "4", "type": "CONTRIBUTES_TO", "properties": {"role": "PM"}},
            {"from": "4", "to": "5", "type": "USES", "properties": {}},
            {"from": "4", "to": "6", "type": "USES", "properties": {}},
            {"from": "1", "to": "5", "type": "KNOWS", "properties": {"level": "expert"}},
            {"from": "1", "to": "6", "type": "KNOWS", "properties": {"level": "advanced"}}
        ]
    }


@app.get("/api/ontology/rag-integration")
async def get_ontology_rag_integration():
    """온톨로지가 RAG를 강화하는 방법 설명"""
    return {
        "traditional_rag": {
            "flow": ["Query", "Vector Search", "Top-K Documents", "LLM", "Response"],
            "limitations": [
                "의미적으로 유사하지만 관련 없는 문서 검색",
                "엔티티 간 관계 정보 손실",
                "컨텍스트 윈도우 제한으로 전체 맥락 파악 어려움"
            ]
        },
        "graph_enhanced_rag": {
            "flow": [
                {"step": "Query", "description": "사용자 질문"},
                {"step": "Entity Extraction", "description": "질문에서 엔티티 추출"},
                {"step": "Graph Traversal", "description": "관련 엔티티 및 관계 탐색"},
                {"step": "Vector Search", "description": "관련 문서 검색"},
                {"step": "Context Fusion", "description": "그래프 정보 + 문서 통합"},
                {"step": "LLM", "description": "강화된 컨텍스트로 응답 생성"},
                {"step": "Response", "description": "정확하고 연결된 응답"}
            ],
            "advantages": [
                "관계 기반 컨텍스트 확장",
                "Multi-hop reasoning 지원",
                "엔티티 disambiguation",
                "추론 경로 설명 가능"
            ]
        },
        "example": {
            "query": "김철수가 참여한 프로젝트에서 사용하는 기술은?",
            "graph_context": {
                "entities_found": ["김철수 (Person)"],
                "traversal": [
                    "김철수 -[CONTRIBUTES_TO]-> AI Platform",
                    "AI Platform -[USES]-> Kubernetes",
                    "AI Platform -[USES]-> Python"
                ],
                "related_info": [
                    "김철수는 AI Platform의 Lead Developer",
                    "프로젝트 상태: active"
                ]
            },
            "enhanced_response": "김철수가 Lead로 참여 중인 AI Platform 프로젝트에서는 Kubernetes(인프라)와 Python(개발 언어)을 사용하고 있습니다."
        }
    }


@app.get("/api/ontology/index-types")
async def get_ontology_index_types():
    """Neo4j 인덱스 타입 설명"""
    return {
        "index_types": [
            {
                "type": "Node Label Index",
                "description": "노드 라벨별 빠른 조회",
                "cypher": "CREATE INDEX FOR (n:Person) ON (n.name)",
                "use_case": "특정 타입 노드 검색",
                "icon": "🏷️"
            },
            {
                "type": "Relationship Type Index",
                "description": "관계 타입별 인덱스",
                "cypher": "CREATE INDEX FOR ()-[r:WORKS_AT]-() ON (r.since)",
                "use_case": "특정 관계 속성으로 필터링",
                "icon": "🔗"
            },
            {
                "type": "Full-text Index",
                "description": "텍스트 전문 검색",
                "cypher": "CREATE FULLTEXT INDEX personNames FOR (n:Person) ON EACH [n.name, n.bio]",
                "use_case": "자연어 검색, 유사어 매칭",
                "icon": "📝"
            },
            {
                "type": "Vector Index",
                "description": "임베딩 벡터 유사도 검색",
                "cypher": "CREATE VECTOR INDEX embeddingIndex FOR (n:Document) ON (n.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1024}}",
                "use_case": "시맨틱 검색, RAG",
                "icon": "🎯"
            },
            {
                "type": "Composite Index",
                "description": "복합 속성 인덱스",
                "cypher": "CREATE INDEX FOR (n:Person) ON (n.department, n.role)",
                "use_case": "다중 조건 검색 최적화",
                "icon": "📊"
            }
        ],
        "hybrid_search_example": {
            "description": "Vector + Graph 하이브리드 검색",
            "cypher": """
// 1. 벡터 검색으로 유사 문서 찾기
CALL db.index.vector.queryNodes('embeddingIndex', 5, $queryVector)
YIELD node AS doc, score

// 2. 그래프 탐색으로 관련 엔티티 확장
MATCH (doc)-[:MENTIONS]->(entity:Entity)-[:RELATED_TO*1..2]-(related)

// 3. 결과 반환
RETURN doc.content, entity.name, collect(related.name) AS relatedEntities
ORDER BY score DESC
""".strip(),
            "explanation": [
                "벡터 유사도로 초기 후보 선정",
                "그래프 관계로 컨텍스트 확장",
                "관련 엔티티까지 포함한 풍부한 결과"
            ]
        }
    }


# ============================================
# ComfyUI API 프록시 및 데모
# ============================================

COMFYUI_URL = "http://comfyui-service.ai-workloads.svc.cluster.local:8188"

@app.get("/api/comfyui/status")
async def get_comfyui_status():
    """ComfyUI 서비스 상태 확인"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("comfyui-service.ai-workloads.svc.cluster.local", 8188))
        sock.close()

        if result == 0:
            return {"status": "running", "connected": True, "url": COMFYUI_URL}
        return {"status": "stopped", "connected": False}
    except:
        return {"status": "unknown", "connected": False}


@app.post("/api/comfyui/prompt")
async def queue_comfyui_prompt(request: dict):
    """ComfyUI에 프롬프트 전송 (시뮬레이션)"""
    # 실제 연결 시 httpx로 프록시
    import uuid
    prompt_id = str(uuid.uuid4())

    return {
        "prompt_id": prompt_id,
        "mode": "simulation",
        "message": "ComfyUI 미연결 - 시뮬레이션 모드"
    }


@app.get("/api/comfyui/queue")
async def get_comfyui_queue():
    """큐 상태 조회 (시뮬레이션)"""
    return {
        "queue_pending": [],
        "queue_running": [],
        "mode": "simulation"
    }


@app.get("/api/comfyui/pipeline-diagram")
async def get_comfyui_pipeline_diagram():
    """ComfyUI 파이프라인 구조 다이어그램 데이터"""
    return {
        "architecture": {
            "title": "ComfyUI 연동 아키텍처",
            "layers": [
                {
                    "name": "Frontend",
                    "components": [
                        {"id": "react", "name": "React App", "icon": "⚛️", "type": "client"}
                    ]
                },
                {
                    "name": "Backend API",
                    "components": [
                        {"id": "fastapi", "name": "FastAPI", "icon": "⚡", "type": "proxy"},
                        {"id": "ws_proxy", "name": "WebSocket Proxy", "icon": "🔌", "type": "proxy"}
                    ]
                },
                {
                    "name": "AI Engine",
                    "components": [
                        {"id": "comfyui", "name": "ComfyUI", "icon": "🎨", "type": "engine", "port": 8188}
                    ]
                },
                {
                    "name": "Storage",
                    "components": [
                        {"id": "rustfs", "name": "RustFS (S3)", "icon": "💾", "type": "storage"}
                    ]
                }
            ],
            "connections": [
                {"from": "react", "to": "fastapi", "label": "REST API"},
                {"from": "react", "to": "ws_proxy", "label": "WebSocket"},
                {"from": "fastapi", "to": "comfyui", "label": "/prompt, /queue"},
                {"from": "ws_proxy", "to": "comfyui", "label": "진행률 스트림"},
                {"from": "comfyui", "to": "rustfs", "label": "결과 저장"}
            ]
        },
        "image_pipeline": {
            "title": "이미지 생성 파이프라인",
            "steps": [
                {"id": 1, "name": "Checkpoint Loader", "icon": "📦", "description": "SD 모델 로드", "node": "CheckpointLoaderSimple"},
                {"id": 2, "name": "CLIP Encode", "icon": "📝", "description": "텍스트 → 임베딩", "node": "CLIPTextEncode"},
                {"id": 3, "name": "Empty Latent", "icon": "🔲", "description": "빈 잠재 이미지", "node": "EmptyLatentImage"},
                {"id": 4, "name": "KSampler", "icon": "🎲", "description": "디노이징", "node": "KSampler"},
                {"id": 5, "name": "VAE Decode", "icon": "🔓", "description": "잠재 → 이미지", "node": "VAEDecode"},
                {"id": 6, "name": "Save Image", "icon": "💾", "description": "결과 저장", "node": "SaveImage"}
            ],
            "flow": "linear"
        },
        "video_pipeline": {
            "title": "영상 생성 파이프라인 (AnimateDiff)",
            "steps": [
                {"id": 1, "name": "Checkpoint Loader", "icon": "📦", "description": "베이스 모델", "node": "CheckpointLoaderSimple"},
                {"id": 2, "name": "Motion Module", "icon": "🎞️", "description": "AnimateDiff 모델", "node": "ADE_LoadAnimateDiffModel"},
                {"id": 3, "name": "Apply Motion", "icon": "🔄", "description": "모션 적용", "node": "ADE_ApplyAnimateDiffModel"},
                {"id": 4, "name": "CLIP Encode", "icon": "📝", "description": "프롬프트 인코딩", "node": "CLIPTextEncode"},
                {"id": 5, "name": "Empty Latent (Batch)", "icon": "🔲", "description": "다중 프레임 잠재", "node": "EmptyLatentImage"},
                {"id": 6, "name": "KSampler", "icon": "🎲", "description": "배치 디노이징", "node": "KSampler"},
                {"id": 7, "name": "VAE Decode", "icon": "🔓", "description": "프레임 디코딩", "node": "VAEDecode"},
                {"id": 8, "name": "Video Combine", "icon": "🎬", "description": "MP4 변환", "node": "VHS_VideoCombine"}
            ],
            "flow": "linear"
        },
        "api_endpoints": [
            {"method": "POST", "path": "/prompt", "description": "워크플로우 실행"},
            {"method": "GET", "path": "/queue", "description": "큐 상태 조회"},
            {"method": "GET", "path": "/history/{id}", "description": "결과 조회"},
            {"method": "GET", "path": "/view", "description": "이미지/영상 조회"},
            {"method": "WebSocket", "path": "/ws", "description": "실시간 진행률"}
        ]
    }


# ============================================
# Vector DB RAG 관리 가이드 API
# ============================================

@app.get("/api/vectordb/rag-guide")
async def get_vectordb_rag_guide():
    """Vector DB RAG 관리 가이드 - 컬렉션 전략, 태깅, RBAC 등"""
    return {
        "collection_strategies": {
            "title": "컬렉션 분리 전략",
            "description": "RAG 시스템에서 효과적인 컬렉션 구성 방법",
            "strategies": [
                {
                    "name": "문서 타입별 분리",
                    "icon": "📁",
                    "collections": [
                        {"name": "documents_pdf", "description": "PDF 문서", "example": "매뉴얼, 보고서, 논문"},
                        {"name": "documents_web", "description": "웹 페이지 크롤링", "example": "기술 블로그, 문서"},
                        {"name": "documents_code", "description": "코드 및 README", "example": "GitHub repos"},
                        {"name": "documents_chat", "description": "대화 히스토리", "example": "Slack, Discord"}
                    ],
                    "pros": ["타입별 최적화된 청킹 가능", "특정 소스만 검색 가능"],
                    "cons": ["컬렉션 수 증가", "크로스 타입 검색 복잡"]
                },
                {
                    "name": "도메인/부서별 분리",
                    "icon": "🏢",
                    "collections": [
                        {"name": "hr_documents", "description": "인사 관련", "example": "취업규칙, 복리후생"},
                        {"name": "engineering_docs", "description": "기술 문서", "example": "API 스펙, 아키텍처"},
                        {"name": "sales_materials", "description": "영업 자료", "example": "제안서, 사례"},
                        {"name": "legal_contracts", "description": "법무 문서", "example": "계약서, 약관"}
                    ],
                    "pros": ["RBAC 적용 용이", "부서별 독립 관리"],
                    "cons": ["중복 데이터 가능성", "전사 검색 시 병합 필요"]
                },
                {
                    "name": "권한 레벨별 분리",
                    "icon": "🔐",
                    "collections": [
                        {"name": "public_knowledge", "description": "공개 정보", "example": "FAQ, 가이드"},
                        {"name": "internal_docs", "description": "사내 전용", "example": "프로세스, 정책"},
                        {"name": "confidential_data", "description": "기밀 정보", "example": "재무, 전략"},
                        {"name": "restricted_pii", "description": "개인정보", "example": "고객 데이터"}
                    ],
                    "pros": ["보안 정책 명확", "감사 추적 용이"],
                    "cons": ["권한 변경 시 마이그레이션 필요"]
                }
            ]
        },
        "metadata_tagging": {
            "title": "메타데이터 태깅 전략",
            "description": "검색 정확도 향상을 위한 메타데이터 설계",
            "required_fields": [
                {"field": "source_file", "type": "string", "description": "원본 파일명", "example": "manual_v2.pdf"},
                {"field": "source_type", "type": "string", "description": "문서 타입", "example": "pdf|web|code|chat"},
                {"field": "created_at", "type": "datetime", "description": "생성 시간", "example": "2024-01-15T10:30:00Z"},
                {"field": "updated_at", "type": "datetime", "description": "수정 시간", "example": "2024-03-20T14:00:00Z"}
            ],
            "recommended_fields": [
                {"field": "department", "type": "string", "description": "소속 부서", "filter": True},
                {"field": "access_level", "type": "string", "description": "접근 레벨", "filter": True},
                {"field": "language", "type": "string", "description": "문서 언어", "filter": True},
                {"field": "version", "type": "string", "description": "문서 버전", "filter": False},
                {"field": "author", "type": "string", "description": "작성자", "filter": True},
                {"field": "tags", "type": "array", "description": "키워드 태그", "filter": True},
                {"field": "chunk_index", "type": "integer", "description": "청크 순서", "filter": False},
                {"field": "total_chunks", "type": "integer", "description": "전체 청크 수", "filter": False}
            ],
            "filter_example": {
                "description": "메타데이터 필터 활용 예시",
                "code": """
# Qdrant 필터 예시
filter = Filter(
    must=[
        FieldCondition(key="department", match=MatchValue(value="engineering")),
        FieldCondition(key="access_level", match=MatchAny(any=["public", "internal"])),
        FieldCondition(key="updated_at", range=Range(gte="2024-01-01"))
    ]
)

# 검색 실행
results = client.search(
    collection_name="documents",
    query_vector=query_embedding,
    query_filter=filter,
    limit=10
)
""".strip()
            }
        },
        "rbac_implementation": {
            "title": "RBAC (역할 기반 접근 제어)",
            "description": "Vector DB에서 권한 관리 구현 방법",
            "approaches": [
                {
                    "name": "컬렉션 레벨 RBAC",
                    "description": "컬렉션 단위로 접근 권한 설정",
                    "implementation": "각 부서/권한별 별도 컬렉션 생성",
                    "code": """
# 사용자 권한에 따른 컬렉션 선택
def get_accessible_collections(user_role):
    role_collections = {
        "public": ["public_knowledge"],
        "employee": ["public_knowledge", "internal_docs"],
        "manager": ["public_knowledge", "internal_docs", "confidential_data"],
        "admin": ["public_knowledge", "internal_docs", "confidential_data", "restricted_pii"]
    }
    return role_collections.get(user_role, ["public_knowledge"])

# 검색 시 허용된 컬렉션만 쿼리
accessible = get_accessible_collections(current_user.role)
results = []
for collection in accessible:
    results.extend(client.search(collection, query_vector, limit=5))
""".strip()
                },
                {
                    "name": "메타데이터 필터 RBAC",
                    "description": "단일 컬렉션에서 메타데이터 필터로 권한 제어",
                    "implementation": "access_level 필드로 필터링",
                    "code": """
# 사용자 접근 가능 레벨 정의
def get_access_levels(user_role):
    role_levels = {
        "public": ["public"],
        "employee": ["public", "internal"],
        "manager": ["public", "internal", "confidential"],
        "admin": ["public", "internal", "confidential", "restricted"]
    }
    return role_levels.get(user_role, ["public"])

# 검색 시 접근 레벨 필터 적용
levels = get_access_levels(current_user.role)
filter = Filter(
    must=[
        FieldCondition(key="access_level", match=MatchAny(any=levels))
    ]
)
results = client.search("all_documents", query_vector, query_filter=filter)
""".strip()
                }
            ],
            "best_practices": [
                "중요 문서는 업로드 시점에 access_level 필수 지정",
                "기본 access_level을 'internal'로 설정 (안전 기본값)",
                "정기적인 권한 감사 및 로깅",
                "삭제된 사용자의 문서 접근 차단"
            ]
        },
        "chunking_strategies": {
            "title": "청킹 전략",
            "description": "문서 타입별 최적 청킹 방법",
            "strategies": [
                {
                    "type": "텍스트 문서 (PDF, Word)",
                    "chunk_size": "500-1000 토큰",
                    "overlap": "50-100 토큰 (10-20%)",
                    "method": "문단/섹션 기준 분리",
                    "tip": "제목, 부제목을 청크 시작에 포함"
                },
                {
                    "type": "코드",
                    "chunk_size": "함수/클래스 단위",
                    "overlap": "imports, 클래스 정의 포함",
                    "method": "AST 기반 분리",
                    "tip": "독스트링/주석을 청크에 포함"
                },
                {
                    "type": "채팅/대화",
                    "chunk_size": "대화 턴 단위",
                    "overlap": "이전 2-3턴 컨텍스트",
                    "method": "시간/화자 기준 분리",
                    "tip": "질문-답변 쌍을 하나의 청크로"
                },
                {
                    "type": "테이블 데이터",
                    "chunk_size": "행 단위 또는 섹션",
                    "overlap": "헤더 항상 포함",
                    "method": "구조 보존 분리",
                    "tip": "테이블 컨텍스트(제목, 출처) 추가"
                }
            ]
        },
        "search_optimization": {
            "title": "검색 최적화 팁",
            "tips": [
                {
                    "category": "쿼리 전처리",
                    "items": [
                        "쿼리 확장: 동의어, 관련 용어 추가",
                        "쿼리 분해: 복잡한 질문을 하위 질문으로",
                        "HyDE: 가상 답변 생성 후 검색"
                    ]
                },
                {
                    "category": "검색 전략",
                    "items": [
                        "Hybrid Search: Dense + Sparse 결합",
                        "Re-ranking: Cross-encoder로 결과 재정렬",
                        "MMR: 다양성 고려한 결과 선택"
                    ]
                },
                {
                    "category": "컨텍스트 구성",
                    "items": [
                        "인접 청크 포함: 검색된 청크의 앞뒤 청크",
                        "메타데이터 활용: 파일명, 섹션 제목 포함",
                        "원본 링크: 출처 확인을 위한 링크 제공"
                    ]
                }
            ]
        },
        "maintenance": {
            "title": "유지보수 가이드",
            "tasks": [
                {
                    "task": "정기 재인덱싱",
                    "frequency": "월 1회 또는 모델 업데이트 시",
                    "description": "임베딩 모델 변경 시 전체 재인덱싱 필요"
                },
                {
                    "task": "중복 제거",
                    "frequency": "주 1회",
                    "description": "유사도 0.95 이상 청크 병합/제거"
                },
                {
                    "task": "오래된 문서 정리",
                    "frequency": "분기 1회",
                    "description": "updated_at 기준 오래된 버전 아카이빙"
                },
                {
                    "task": "성능 모니터링",
                    "frequency": "상시",
                    "description": "검색 지연시간, 정확도 메트릭 추적"
                }
            ],
            "backup_strategy": {
                "description": "백업 및 복구 전략",
                "recommendations": [
                    "일일 스냅샷 백업 (Qdrant snapshots)",
                    "주간 전체 백업 (컬렉션 + 메타데이터)",
                    "지역 간 복제 (DR 구성)",
                    "복구 테스트 분기별 실시"
                ]
            }
        }
    }


# ============================================
# LangGraph Agent API - 코드 생성 및 Docker 이미지 빌드
# ============================================

class LangGraphWorkflow(BaseModel):
    id: str
    name: str
    description: str = ""
    nodes: list = []
    connections: list = []

class LangGraphBuildRequest(BaseModel):
    workflow: dict
    image_name: str = ""
    image_tag: str = "latest"

# LangGraph 빌드 상태 저장
langgraph_builds = {}


def generate_langgraph_code(workflow_data: dict) -> str:
    """워크플로우를 LangGraph Python 코드로 변환"""
    nodes = workflow_data.get('nodes', [])
    connections = workflow_data.get('connections', [])
    workflow_name = workflow_data.get('name', 'Untitled Agent')
    workflow_desc = workflow_data.get('description', '')

    # 노드 타입별 분류
    agent_nodes = [n for n in nodes if 'agent' in n.get('type', '').lower()]
    tool_nodes = [n for n in nodes if 'tool' in n.get('type', '').lower()]
    retriever_nodes = [n for n in nodes if 'retriever' in n.get('type', '').lower()]

    # Tools 결정
    tools_list = []
    for tn in tool_nodes:
        params = tn.get('data', {}).get('parameters', {})
        tool_type = params.get('tools', 'web_search')
        if tool_type == 'web_search':
            tools_list.append('web_search')
        elif tool_type == 'calculator':
            tools_list.append('calculator')
        elif tool_type == 'rag_retriever':
            tools_list.append('rag_retriever')

    if retriever_nodes:
        tools_list.append('rag_retriever')

    tools_list = list(set(tools_list))

    # Agent 설정
    agent_config = {
        'model': 'gpt-4',
        'temperature': 0.7,
        'system_prompt': 'You are a helpful assistant.'
    }
    if agent_nodes:
        params = agent_nodes[0].get('data', {}).get('parameters', {})
        agent_config['model'] = params.get('model', 'gpt-4')
        agent_config['temperature'] = params.get('temperature', 0.7)
        agent_config['system_prompt'] = params.get('systemPrompt', 'You are a helpful assistant.')

    code = f'''"""
LangGraph Agent - Auto-generated
Workflow: {workflow_name}
Description: {workflow_desc}
"""

import os
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool

# State Definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "Conversation messages"]
    context: str

'''

    # Tools 정의
    if 'web_search' in tools_list:
        code += '''
@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    from langchain_community.tools import DuckDuckGoSearchRun
    search = DuckDuckGoSearchRun()
    return search.run(query)
'''

    if 'calculator' in tools_list:
        code += '''
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {{e}}"
'''

    if 'rag_retriever' in tools_list:
        code += '''
@tool
def rag_retriever(query: str) -> str:
    """Retrieve relevant documents from vector store."""
    # Implement your RAG logic here
    return f"Retrieved context for: {{query}}"
'''

    tools_str = ', '.join(tools_list) if tools_list else ''
    code += f'''
tools = [{tools_str}]

# LLM Configuration
llm = ChatOpenAI(model="{agent_config['model']}", temperature={agent_config['temperature']})
llm_with_tools = llm.bind_tools(tools) if tools else llm

SYSTEM_PROMPT = """{agent_config['system_prompt']}"""

def agent_node(state: AgentState) -> AgentState:
    """Main agent node."""
    messages = list(state["messages"])
    if not any(getattr(m, 'type', '') == 'system' for m in messages):
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    response = llm_with_tools.invoke(messages)
    return {{"messages": state["messages"] + [response], "context": state.get("context", "")}}

def tools_node(state: AgentState) -> AgentState:
    """Execute tool calls."""
    tool_node = ToolNode(tools=tools)
    result = tool_node.invoke(state)
    return {{"messages": state["messages"] + result.get("messages", []), "context": state.get("context", "")}}

def create_graph():
    """Build the LangGraph workflow."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
'''

    if tools_list:
        code += '''    workflow.add_node("tools", tools_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", tools_condition, {"continue": "tools", "end": END})
    workflow.add_edge("tools", "agent")
'''
    else:
        code += '''    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
'''

    code += '''
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

graph = create_graph()

def run_agent(user_input: str, thread_id: str = "default") -> str:
    """Run the agent."""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [HumanMessage(content=user_input)], "context": ""}, config)
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            return msg.content
    return "No response."

# FastAPI Server
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="LangGraph Agent API")

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        response = run_agent(request.message, request.thread_id)
        return {"response": response, "thread_id": request.thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
'''
    return code


def generate_dockerfile() -> str:
    """LangGraph 에이전트용 Dockerfile"""
    return '''FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py .
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "agent.py"]
'''


def generate_requirements() -> str:
    """requirements.txt"""
    return '''langchain>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.20
langgraph>=0.0.40
duckduckgo-search>=4.0.0
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
'''


def generate_k8s_yaml(workflow_data: dict, image_name: str, image_tag: str) -> str:
    """K8s Deployment YAML"""
    safe_name = workflow_data.get('name', 'agent').lower().replace(' ', '-').replace('_', '-')[:40]
    return f'''apiVersion: apps/v1
kind: Deployment
metadata:
  name: langgraph-{safe_name}
  namespace: ai-workloads
spec:
  replicas: 1
  selector:
    matchLabels:
      app: langgraph-{safe_name}
  template:
    metadata:
      labels:
        app: langgraph-{safe_name}
    spec:
      containers:
      - name: agent
        image: {image_name}:{image_tag}
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8080
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-api-keys
              key: openai-api-key
              optional: true
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: langgraph-{safe_name}
  namespace: ai-workloads
spec:
  selector:
    app: langgraph-{safe_name}
  ports:
  - port: 8080
    targetPort: 8080
'''


@app.post("/api/langgraph/generate-code")
async def generate_langgraph_code_api(workflow: dict):
    """워크플로우를 LangGraph Python 코드로 변환"""
    try:
        code = generate_langgraph_code(workflow)
        dockerfile = generate_dockerfile()
        requirements = generate_requirements()
        k8s_yaml = generate_k8s_yaml(workflow, f"langgraph-{workflow.get('id', 'agent')}", "latest")

        return {
            "success": True,
            "files": {
                "agent.py": code,
                "Dockerfile": dockerfile,
                "requirements.txt": requirements,
                "k8s-deployment.yaml": k8s_yaml
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/langgraph/build")
async def build_langgraph_image(request: LangGraphBuildRequest, background_tasks: BackgroundTasks):
    """워크플로우를 Docker 이미지로 빌드"""
    import tempfile
    import subprocess

    workflow = request.workflow
    image_name = request.image_name or f"langgraph-{workflow.get('id', 'agent')}"
    image_tag = request.image_tag
    build_id = str(uuid.uuid4())[:8]

    langgraph_builds[build_id] = {
        "status": "pending",
        "workflow_id": workflow.get('id'),
        "workflow_name": workflow.get('name'),
        "image_name": image_name,
        "image_tag": image_tag,
        "logs": [],
        "started_at": datetime.now().isoformat()
    }

    async def do_build():
        try:
            langgraph_builds[build_id]["status"] = "building"
            langgraph_builds[build_id]["logs"].append("Starting build...")

            with tempfile.TemporaryDirectory() as tmpdir:
                # Generate files
                code = generate_langgraph_code(workflow)
                with open(os.path.join(tmpdir, "agent.py"), "w") as f:
                    f.write(code)
                langgraph_builds[build_id]["logs"].append("Generated agent.py")

                with open(os.path.join(tmpdir, "Dockerfile"), "w") as f:
                    f.write(generate_dockerfile())

                with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                    f.write(generate_requirements())

                # Docker build
                full_image = f"{image_name}:{image_tag}"
                langgraph_builds[build_id]["logs"].append(f"Building {full_image}...")

                result = subprocess.run(
                    ["docker", "build", "-t", full_image, "."],
                    cwd=tmpdir, capture_output=True, text=True, timeout=600
                )

                if result.returncode != 0:
                    langgraph_builds[build_id]["status"] = "failed"
                    langgraph_builds[build_id]["error"] = result.stderr
                    return

                langgraph_builds[build_id]["logs"].append("Docker build completed")

                # Import to k3s
                tar_path = os.path.join(tmpdir, "image.tar")
                subprocess.run(["docker", "save", "-o", tar_path, full_image], capture_output=True)
                subprocess.run(["sudo", "-n", "k3s", "ctr", "images", "import", tar_path], capture_output=True)

                langgraph_builds[build_id]["status"] = "completed"
                langgraph_builds[build_id]["completed_at"] = datetime.now().isoformat()
                langgraph_builds[build_id]["logs"].append("Build completed!")

        except Exception as e:
            langgraph_builds[build_id]["status"] = "failed"
            langgraph_builds[build_id]["error"] = str(e)

    background_tasks.add_task(do_build)
    return {"success": True, "build_id": build_id}


@app.get("/api/langgraph/build/{build_id}/status")
async def get_build_status(build_id: str):
    """빌드 상태 조회"""
    if build_id not in langgraph_builds:
        raise HTTPException(status_code=404, detail="Build not found")
    return langgraph_builds[build_id]


@app.get("/api/langgraph/builds")
async def list_builds():
    """빌드 목록"""
    return {"builds": list(langgraph_builds.values())}


@app.post("/api/langgraph/deploy/{build_id}")
async def deploy_agent(build_id: str):
    """빌드된 에이전트 배포"""
    import subprocess
    import tempfile

    if build_id not in langgraph_builds:
        raise HTTPException(status_code=404, detail="Build not found")

    build = langgraph_builds[build_id]
    if build["status"] != "completed":
        raise HTTPException(status_code=400, detail="Build not completed")

    k8s_yaml = generate_k8s_yaml(
        {"name": build["workflow_name"], "id": build["workflow_id"]},
        build["image_name"],
        build["image_tag"]
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(k8s_yaml)
        yaml_path = f.name

    result = subprocess.run(["kubectl", "apply", "-f", yaml_path], capture_output=True, text=True)
    os.unlink(yaml_path)

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)

    return {"success": True, "message": "Deployed successfully"}


# ============================================
# Qdrant Vector Database API
# ============================================

QDRANT_URL = "http://qdrant.ai-workloads.svc.cluster.local:6333"

# In-memory storage for demo mode
_qdrant_collections = {}
_qdrant_demo_mode = True

async def check_qdrant_connection():
    """Check if Qdrant is available"""
    global _qdrant_demo_mode
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{QDRANT_URL}/collections")
            if resp.status_code == 200:
                _qdrant_demo_mode = False
                return True
    except:
        pass
    _qdrant_demo_mode = True
    return False


@app.get("/api/qdrant/info")
async def get_qdrant_info():
    """Get Qdrant server info"""
    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{QDRANT_URL}/collections")
                data = resp.json()
                collections = data.get("result", {}).get("collections", [])
                total_vectors = 0
                for col in collections:
                    col_resp = await client.get(f"{QDRANT_URL}/collections/{col['name']}")
                    col_data = col_resp.json()
                    total_vectors += col_data.get("result", {}).get("vectors_count", 0)

                return {
                    "version": "1.7.0",
                    "collections_count": len(collections),
                    "total_vectors": total_vectors,
                    "mode": "connected"
                }
        except Exception as e:
            pass

    # Demo mode
    return {
        "version": "1.7.0 (demo)",
        "collections_count": len(_qdrant_collections),
        "total_vectors": sum(c.get("vectors_count", 0) for c in _qdrant_collections.values()),
        "mode": "demo"
    }


@app.get("/api/qdrant/collections")
async def get_qdrant_collections():
    """Get all collections"""
    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{QDRANT_URL}/collections")
                data = resp.json()
                collections = []
                for col in data.get("result", {}).get("collections", []):
                    col_resp = await client.get(f"{QDRANT_URL}/collections/{col['name']}")
                    col_data = col_resp.json().get("result", {})
                    collections.append({
                        "name": col["name"],
                        "vectors_count": col_data.get("vectors_count", 0),
                        "points_count": col_data.get("points_count", 0),
                        "status": col_data.get("status", "green"),
                        "config": col_data.get("config", {})
                    })
                return {"collections": collections}
        except:
            pass

    # Demo mode
    return {
        "collections": [
            {
                "name": name,
                "vectors_count": data.get("vectors_count", 0),
                "points_count": data.get("points_count", 0),
                "status": "green",
                "config": data.get("config", {})
            }
            for name, data in _qdrant_collections.items()
        ]
    }


@app.post("/api/qdrant/collections")
async def create_qdrant_collection(request: dict):
    """Create a new collection"""
    name = request.get("name")
    vector_size = request.get("vector_size", 1536)
    distance = request.get("distance", "Cosine")

    if not name:
        raise HTTPException(status_code=400, detail="Collection name is required")

    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.put(
                    f"{QDRANT_URL}/collections/{name}",
                    json={
                        "vectors": {
                            "size": vector_size,
                            "distance": distance
                        }
                    }
                )
                if resp.status_code in [200, 201]:
                    return {"success": True, "message": f"Collection '{name}' created"}
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    # Demo mode
    if name in _qdrant_collections:
        raise HTTPException(status_code=400, detail=f"Collection '{name}' already exists")

    _qdrant_collections[name] = {
        "vectors_count": 0,
        "points_count": 0,
        "config": {
            "params": {
                "vectors": {
                    "size": vector_size,
                    "distance": distance
                }
            }
        }
    }
    return {"success": True, "message": f"Collection '{name}' created (demo mode)"}


@app.delete("/api/qdrant/collections/{name}")
async def delete_qdrant_collection(name: str):
    """Delete a collection"""
    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(f"{QDRANT_URL}/collections/{name}")
                if resp.status_code == 200:
                    return {"success": True, "message": f"Collection '{name}' deleted"}
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    # Demo mode
    if name not in _qdrant_collections:
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")

    del _qdrant_collections[name]
    return {"success": True, "message": f"Collection '{name}' deleted (demo mode)"}


@app.post("/api/qdrant/search")
async def search_qdrant(request: dict):
    """Search vectors in a collection"""
    collection = request.get("collection")
    query_vector = request.get("vector")
    limit = request.get("limit", 10)

    if not collection:
        raise HTTPException(status_code=400, detail="Collection name is required")

    await check_qdrant_connection()

    if not _qdrant_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{QDRANT_URL}/collections/{collection}/points/search",
                    json={
                        "vector": query_vector,
                        "limit": limit,
                        "with_payload": True
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    # Demo mode - return empty results
    return {
        "result": [],
        "status": "ok",
        "time": 0.001,
        "mode": "demo"
    }


# ============================================
# vLLM API
# ============================================

VLLM_URL = "http://vllm-service.ai-workloads.svc.cluster.local:8000"
_vllm_demo_mode = True

async def check_vllm_connection():
    """Check if vLLM is available"""
    global _vllm_demo_mode
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{VLLM_URL}/v1/models")
            if resp.status_code == 200:
                _vllm_demo_mode = False
                return True
    except:
        pass
    _vllm_demo_mode = True
    return False


@app.get("/api/vllm/status")
async def get_vllm_status():
    """Get vLLM server status"""
    await check_vllm_connection()

    if not _vllm_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{VLLM_URL}/v1/models")
                if resp.status_code == 200:
                    return {
                        "status": "running",
                        "connected": True,
                        "url": VLLM_URL,
                        "mode": "connected"
                    }
        except:
            pass

    return {
        "status": "stopped",
        "connected": False,
        "mode": "demo"
    }


@app.get("/api/vllm/models")
async def get_vllm_models():
    """Get available models"""
    await check_vllm_connection()

    if not _vllm_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{VLLM_URL}/v1/models")
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass

    # Demo mode
    return {
        "models": [
            {"id": "Qwen/Qwen2.5-7B-Instruct", "name": "Qwen2.5-7B-Instruct (demo)"},
            {"id": "Qwen/Qwen2.5-Coder-7B-Instruct", "name": "Qwen2.5-Coder-7B (demo)"}
        ],
        "mode": "demo"
    }


@app.post("/api/vllm/chat")
async def vllm_chat(request: dict):
    """Chat with vLLM model"""
    await check_vllm_connection()

    model = request.get("model", "Qwen/Qwen2.5-7B-Instruct")
    messages = request.get("messages", [])
    temperature = request.get("temperature", 0.7)
    max_tokens = request.get("max_tokens", 1024)

    if not _vllm_demo_mode:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{VLLM_URL}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                if resp.status_code == 200:
                    return resp.json()
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
        except HTTPException:
            raise
        except:
            pass

    # Demo mode response
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "vLLM 서버가 실행 중이지 않습니다. AI 워크로드 페이지에서 vLLM을 시작해주세요."
            }
        }],
        "mode": "demo"
    }


@app.post("/api/vllm/chat/stream")
async def vllm_chat_stream(request: dict):
    """Chat with vLLM model (streaming)"""
    from fastapi.responses import StreamingResponse
    import httpx

    await check_vllm_connection()

    model = request.get("model", "Qwen/Qwen2.5-7B-Instruct")
    messages = request.get("messages", [])
    temperature = request.get("temperature", 0.7)
    max_tokens = request.get("max_tokens", 1024)
    top_p = request.get("top_p", 0.95)

    if _vllm_demo_mode:
        # Demo mode: 간단한 스트리밍 시뮬레이션
        async def demo_stream():
            demo_message = "vLLM 서버가 실행 중이지 않습니다. AI 워크로드 페이지에서 vLLM을 시작해주세요."
            for char in demo_message:
                yield f"data: {char}\n\n"
                await asyncio.sleep(0.02)
            yield "data: [DONE]\n\n"

        return StreamingResponse(demo_stream(), media_type="text/event-stream")

    # 실제 vLLM 서버로 스트리밍 요청
    async def stream_response():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{VLLM_URL}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p,
                        "stream": True
                    }
                ) as resp:
                    if resp.status_code != 200:
                        yield f"data: Error: {resp.status_code}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    async for line in resp.aiter_lines():
                        if line.strip():
                            # vLLM의 SSE 형식 그대로 전달
                            if line.startswith("data:"):
                                content = line[5:].strip()
                                if content == "[DONE]":
                                    yield "data: [DONE]\n\n"
                                else:
                                    try:
                                        import json
                                        data = json.loads(content)
                                        if "choices" in data and len(data["choices"]) > 0:
                                            delta = data["choices"][0].get("delta", {})
                                            if "content" in delta:
                                                yield f"data: {delta['content']}\n\n"
                                    except:
                                        yield f"{line}\n\n"
                    yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@app.post("/api/vllm/start")
async def start_vllm(request: dict):
    """Start vLLM service"""
    model = request.get("model", "Qwen/Qwen2.5-7B-Instruct")
    # This would typically trigger Kubernetes deployment
    return {
        "success": True,
        "message": f"vLLM 시작 요청됨 (모델: {model})",
        "note": "실제 시작은 AI 워크로드 페이지에서 진행해주세요."
    }


@app.post("/api/vllm/stop")
async def stop_vllm():
    """Stop vLLM service"""
    return {
        "success": True,
        "message": "vLLM 중지 요청됨",
        "note": "실제 중지는 AI 워크로드 페이지에서 진행해주세요."
    }


# ============================================
# Workloads Status API (for Pipeline page)
# ============================================

@app.get("/api/workloads/status")
async def get_workloads_status():
    """Get workloads status summary"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        status = {}
        for name, config in WORKLOADS.items():
            namespace = config["namespace"]
            try:
                if "deployment" in config:
                    deploy = apps_v1.read_namespaced_deployment(
                        config["deployment"], namespace
                    )
                    status[name] = {
                        "running": (deploy.status.ready_replicas or 0) > 0,
                        "ready": deploy.status.ready_replicas or 0,
                        "desired": deploy.spec.replicas or 0
                    }
                elif "statefulset" in config:
                    sts = apps_v1.read_namespaced_stateful_set(
                        config["statefulset"], namespace
                    )
                    status[name] = {
                        "running": (sts.status.ready_replicas or 0) > 0,
                        "ready": sts.status.ready_replicas or 0,
                        "desired": sts.spec.replicas or 0
                    }
                elif "daemonset" in config:
                    ds = apps_v1.read_namespaced_daemon_set(
                        config["daemonset"], namespace
                    )
                    status[name] = {
                        "running": (ds.status.number_ready or 0) > 0,
                        "ready": ds.status.number_ready or 0,
                        "desired": ds.status.desired_number_scheduled or 0
                    }
            except ApiException:
                status[name] = {"running": False, "ready": 0, "desired": 0}

        return status
    except Exception as e:
        return {}


# ============================================
# ComfyUI Extended API
# ============================================

COMFYUI_SERVICE_URL = "http://comfyui-service.ai-workloads.svc.cluster.local:8188"

# In-memory storage for ComfyUI demo
_comfyui_workflows = [
    {
        "id": "txt2img_basic",
        "name": "Text to Image (Basic)",
        "description": "기본 텍스트-이미지 생성 워크플로우",
        "category": "text2img",
        "nodes": ["CheckpointLoader", "CLIPTextEncode", "KSampler", "VAEDecode", "SaveImage"]
    },
    {
        "id": "img2img",
        "name": "Image to Image",
        "description": "이미지 기반 변형 워크플로우",
        "category": "img2img",
        "nodes": ["LoadImage", "VAEEncode", "KSampler", "VAEDecode", "SaveImage"]
    },
    {
        "id": "inpainting",
        "name": "Inpainting",
        "description": "이미지 부분 수정 워크플로우",
        "category": "inpainting",
        "nodes": ["LoadImage", "LoadMask", "InpaintModel", "KSampler", "VAEDecode"]
    }
]

_comfyui_generations = []


@app.get("/api/comfyui/workflows")
async def get_comfyui_workflows():
    """Get available ComfyUI workflows"""
    return {"workflows": _comfyui_workflows}


@app.get("/api/comfyui/generations")
async def get_comfyui_generations():
    """Get generation history"""
    return {"generations": _comfyui_generations[-50:]}  # Last 50


@app.get("/api/comfyui/history")
async def get_comfyui_history():
    """Get ComfyUI generation history from the actual service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{COMFYUI_SERVICE_URL}/history")
            if response.status_code == 200:
                history_data = response.json()
                # Transform history to a more usable format
                results = []
                for prompt_id, data in history_data.items():
                    outputs = data.get("outputs", {})
                    images = []
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for img in node_output["images"]:
                                images.append({
                                    "filename": img.get("filename"),
                                    "subfolder": img.get("subfolder", ""),
                                    "type": img.get("type", "output")
                                })
                    results.append({
                        "id": prompt_id,
                        "status": data.get("status", {}).get("status_str", "completed"),
                        "images": images,
                        "completed": data.get("status", {}).get("completed", True)
                    })
                return {"history": results[-50:]}  # Last 50
            return {"history": [], "error": "Could not fetch history"}
    except Exception as e:
        return {"history": [], "error": str(e)}


@app.get("/api/comfyui/outputs")
async def get_comfyui_outputs():
    """Get list of output images from ComfyUI output folder"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get all output images using ComfyUI's view endpoint
            response = await client.get(f"{COMFYUI_SERVICE_URL}/history")
            if response.status_code == 200:
                history = response.json()
                outputs = []
                for prompt_id, data in history.items():
                    for node_id, node_output in data.get("outputs", {}).items():
                        if "images" in node_output:
                            for img in node_output["images"]:
                                filename = img.get("filename", "")
                                subfolder = img.get("subfolder", "")
                                img_type = img.get("type", "output")
                                outputs.append({
                                    "filename": filename,
                                    "subfolder": subfolder,
                                    "type": img_type,
                                    "prompt_id": prompt_id,
                                    "url": f"/api/comfyui/view?filename={filename}&subfolder={subfolder}&type={img_type}"
                                })
                # Sort by filename (usually contains timestamp)
                outputs.sort(key=lambda x: x["filename"], reverse=True)
                return {"outputs": outputs[:100]}  # Last 100 images
            return {"outputs": [], "error": "Could not fetch outputs"}
    except Exception as e:
        return {"outputs": [], "error": str(e)}


@app.get("/api/comfyui/view")
async def view_comfyui_image(filename: str, subfolder: str = "", type: str = "output"):
    """Proxy ComfyUI image view"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"filename": filename, "subfolder": subfolder, "type": type}
            response = await client.get(f"{COMFYUI_SERVICE_URL}/view", params=params)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "image/png")
                from fastapi.responses import Response
                return Response(content=response.content, media_type=content_type)
            raise HTTPException(status_code=404, detail="Image not found")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


class ComfyUITxt2ImgRequest(BaseModel):
    """ComfyUI Text to Image 생성 요청"""
    prompt: str
    negative_prompt: str = ""
    steps: int = 20
    cfg_scale: float = 7.0
    width: int = 512
    height: int = 512
    seed: int = -1


class ComfyUIImg2ImgRequest(BaseModel):
    """ComfyUI Image to Image 생성 요청"""
    prompt: str
    negative_prompt: str = ""
    image: str  # 입력 이미지 파일명
    strength: float = 0.7  # 변화 강도 (0.0~1.0, 낮을수록 원본 유지)
    steps: int = 20
    cfg_scale: float = 7.0
    seed: int = -1


class ComfyUIInpaintingRequest(BaseModel):
    """ComfyUI Inpainting 생성 요청"""
    prompt: str
    negative_prompt: str = ""
    image: str  # 입력 이미지 파일명
    mask: str   # 마스크 이미지 파일명 (흰색=변경할 영역, 검정색=유지할 영역)
    steps: int = 20
    cfg_scale: float = 7.0
    seed: int = -1


class ComfyUIGenerateRequest(BaseModel):
    """ComfyUI 이미지 생성 요청 (호환성용, txt2img로 처리)"""
    workflow_id: str = "txt2img_basic"
    prompt: str
    negative_prompt: str = ""
    steps: int = 20
    cfg_scale: float = 7.0
    width: int = 512
    height: int = 512
    seed: int = -1


@app.post("/api/comfyui/generate")
async def generate_comfyui_image(request: ComfyUIGenerateRequest):
    """Queue an image generation to ComfyUI"""
    import uuid
    from datetime import datetime

    workflow_id = request.workflow_id
    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    steps = request.steps
    cfg_scale = request.cfg_scale
    width = request.width
    height = request.height
    seed = request.seed

    # Build a basic ComfyUI workflow prompt
    # This is a minimal txt2img workflow
    comfyui_prompt = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": cfg_scale,
                "denoise": 1,
                "latent_image": ["5", 0],
                "model": ["4", 0],
                "negative": ["7", 0],
                "positive": ["6", 0],
                "sampler_name": "euler",
                "scheduler": "normal",
                "seed": seed if seed >= 0 else random.randint(0, 2**32),
                "steps": steps
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "v1-5-pruned-emaonly.safetensors"
            }
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": 1,
                "height": height,
                "width": width
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 1],
                "text": prompt_text
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 1],
                "text": negative_prompt or "ugly, blurry, low quality"
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            }
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["8", 0]
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{COMFYUI_SERVICE_URL}/prompt",
                json={"prompt": comfyui_prompt}
            )
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id", "unknown")

                # Store in local history
                generation = {
                    "id": prompt_id,
                    "workflow_id": workflow_id,
                    "prompt": prompt_text,
                    "negative_prompt": negative_prompt,
                    "status": "queued",
                    "created_at": datetime.now().isoformat(),
                    "progress": 0,
                    "settings": {
                        "steps": steps,
                        "cfg_scale": cfg_scale,
                        "width": width,
                        "height": height,
                        "seed": seed
                    }
                }
                _comfyui_generations.append(generation)

                return {
                    "generation_id": prompt_id,
                    "status": "queued",
                    "message": "Generation queued successfully"
                }
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to queue prompt")
    except httpx.RequestError as e:
        # Fallback to demo mode if ComfyUI not available
        generation_id = str(uuid.uuid4())[:8]
        generation = {
            "id": generation_id,
            "workflow_id": workflow_id,
            "prompt": prompt_text,
            "negative_prompt": negative_prompt,
            "status": "error",
            "error": f"ComfyUI service unavailable: {str(e)}",
            "created_at": datetime.now().isoformat(),
            "progress": 0
        }
        _comfyui_generations.append(generation)
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


class ComfyUIVideoGenerateRequest(BaseModel):
    """WAN2.2 5b를 사용한 영상 생성 요청"""
    prompt: str
    negative_prompt: str = ""
    start_image: str  # 시작 이미지 파일명 또는 URL
    end_image: str    # 종료 이미지 파일명 또는 URL
    num_frames: int = 24  # 생성할 프레임 수 (기본값: 1초 @ 24fps)
    steps: int = 25
    cfg_scale: float = 7.5
    motion_scale: float = 1.0  # 모션 스케일 (1.0 = normal, 0.5 = subtle, 2.0 = strong)
    seed: int = -1


@app.post("/api/comfyui/txt2img")
async def generate_txt2img(request: ComfyUITxt2ImgRequest):
    """Text to Image 생성"""
    import uuid
    from datetime import datetime

    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    steps = request.steps
    cfg_scale = request.cfg_scale
    width = request.width
    height = request.height
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    # Text to Image 워크플로우
    comfyui_prompt = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": prompt_text}
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": negative_prompt or "ugly, blurry, low quality"}
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"batch_size": 1, "height": height, "width": width}
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": cfg_scale, "denoise": 1.0, "latent_image": ["4", 0],
                "model": ["1", 0], "negative": ["3", 0], "positive": ["2", 0],
                "sampler_name": "euler", "scheduler": "normal", "seed": seed, "steps": steps
            }
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "txt2img", "images": ["6", 0]}
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{COMFYUI_SERVICE_URL}/prompt",
                json={"prompt": comfyui_prompt}
            )
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id", "unknown")
                generation = {
                    "id": prompt_id, "workflow_id": "txt2img", "type": "image",
                    "prompt": prompt_text, "negative_prompt": negative_prompt,
                    "status": "queued", "created_at": datetime.now().isoformat(),
                    "progress": 0,
                    "settings": {"steps": steps, "cfg_scale": cfg_scale, "width": width, "height": height, "seed": seed}
                }
                _comfyui_generations.append(generation)
                return {"generation_id": prompt_id, "status": "queued", "message": "Text to Image generation queued"}
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to queue txt2img")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@app.post("/api/comfyui/img2img")
async def generate_img2img(request: ComfyUIImg2ImgRequest):
    """Image to Image 생성"""
    import uuid
    from datetime import datetime

    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    image_file = request.image
    strength = request.strength
    steps = request.steps
    cfg_scale = request.cfg_scale
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    # Image to Image 워크플로우
    comfyui_prompt = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": image_file}
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": prompt_text}
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": negative_prompt or "ugly, blurry, low quality"}
        },
        "5": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": cfg_scale, "denoise": strength, "latent_image": ["5", 0],
                "model": ["1", 0], "negative": ["4", 0], "positive": ["3", 0],
                "sampler_name": "euler", "scheduler": "normal", "seed": seed, "steps": steps
            }
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]}
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "img2img", "images": ["7", 0]}
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{COMFYUI_SERVICE_URL}/prompt",
                json={"prompt": comfyui_prompt}
            )
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id", "unknown")
                generation = {
                    "id": prompt_id, "workflow_id": "img2img", "type": "image",
                    "prompt": prompt_text, "negative_prompt": negative_prompt,
                    "input_image": image_file, "status": "queued",
                    "created_at": datetime.now().isoformat(), "progress": 0,
                    "settings": {"steps": steps, "cfg_scale": cfg_scale, "strength": strength, "seed": seed}
                }
                _comfyui_generations.append(generation)
                return {"generation_id": prompt_id, "status": "queued", "message": "Image to Image generation queued"}
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to queue img2img")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@app.post("/api/comfyui/inpainting")
async def generate_inpainting(request: ComfyUIInpaintingRequest):
    """Inpainting 생성"""
    import uuid
    from datetime import datetime

    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    image_file = request.image
    mask_file = request.mask
    steps = request.steps
    cfg_scale = request.cfg_scale
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    # Inpainting 워크플로우
    comfyui_prompt = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": image_file}
        },
        "3": {
            "class_type": "LoadImage",
            "inputs": {"image": mask_file}
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": prompt_text}
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": negative_prompt or "ugly, blurry, low quality"}
        },
        "6": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["2", 0], "vae": ["1", 2]}
        },
        "7": {
            "class_type": "SetLatentMask",
            "inputs": {"samples": ["6", 0], "mask": ["3", 0]}
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": cfg_scale, "denoise": 1.0, "latent_image": ["7", 0],
                "model": ["1", 0], "negative": ["5", 0], "positive": ["4", 0],
                "sampler_name": "euler", "scheduler": "normal", "seed": seed, "steps": steps
            }
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["8", 0], "vae": ["1", 2]}
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "inpainting", "images": ["9", 0]}
        }
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{COMFYUI_SERVICE_URL}/prompt",
                json={"prompt": comfyui_prompt}
            )
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id", "unknown")
                generation = {
                    "id": prompt_id, "workflow_id": "inpainting", "type": "image",
                    "prompt": prompt_text, "negative_prompt": negative_prompt,
                    "input_image": image_file, "mask_image": mask_file, "status": "queued",
                    "created_at": datetime.now().isoformat(), "progress": 0,
                    "settings": {"steps": steps, "cfg_scale": cfg_scale, "seed": seed}
                }
                _comfyui_generations.append(generation)
                return {"generation_id": prompt_id, "status": "queued", "message": "Inpainting generation queued"}
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to queue inpainting")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@app.post("/api/comfyui/generate-video")
async def generate_comfyui_video(request: ComfyUIVideoGenerateRequest):
    """WAN2.2 5b 모델로 시작/종료 이미지 기반 영상 생성"""
    import uuid
    from datetime import datetime

    prompt_text = request.prompt
    negative_prompt = request.negative_prompt
    start_image = request.start_image
    end_image = request.end_image
    num_frames = request.num_frames
    steps = request.steps
    cfg_scale = request.cfg_scale
    motion_scale = request.motion_scale
    seed = request.seed if request.seed >= 0 else random.randint(0, 2**32)

    # WAN2.2 5b를 사용한 비디오 생성 워크플로우
    # WAN (Waveform Animation Network) 모델로 이미지 간 인터폴레이션을 통한 영상 생성
    comfyui_prompt = {
        # 1단계: 시작 이미지 로드
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": start_image
            }
        },
        # 2단계: 종료 이미지 로드
        "2": {
            "class_type": "LoadImage",
            "inputs": {
                "image": end_image
            }
        },
        # 3단계: WAN2.2 5b 모델 로드
        "3": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "wan_v2_2_5b.safetensors"
            }
        },
        # 4단계: 프롬프트 인코딩 (텍스트 → CLIP 임베딩)
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["3", 1],
                "text": prompt_text
            }
        },
        # 5단계: 네거티브 프롬프트 인코딩
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["3", 1],
                "text": negative_prompt or "low quality, blurry, distorted"
            }
        },
        # 6단계: 이미지를 VAE 잠재 공간으로 인코딩 (시작 이미지)
        "6": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["1", 0],
                "vae": ["3", 2]
            }
        },
        # 7단계: 이미지를 VAE 잠재 공간으로 인코딩 (종료 이미지)
        "7": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["2", 0],
                "vae": ["3", 2]
            }
        },
        # 8단계: WAN2.2 인터폴레이션 샘플러
        "8": {
            "class_type": "WANInterpolateSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_start": ["6", 0],
                "latent_end": ["7", 0],
                "num_frames": num_frames,
                "steps": steps,
                "cfg": cfg_scale,
                "motion_scale": motion_scale,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "seed": seed
            }
        },
        # 9단계: 잠재 프레임을 이미지로 디코딩
        "9": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["8", 0],
                "vae": ["3", 2]
            }
        },
        # 10단계: 이미지 프레임을 비디오로 변환
        "10": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["9", 0],
                "frame_rate": 24,
                "loop_count": 0,
                "filename_prefix": "WAN_VideoOutput",
                "format": "video/mp4",
                "codec": "h264",
                "crf": 20
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{COMFYUI_SERVICE_URL}/prompt",
                json={"prompt": comfyui_prompt}
            )
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id", "unknown")

                # 생성 이력 저장
                generation = {
                    "id": prompt_id,
                    "workflow_id": "wan_2_2_video",
                    "type": "video",
                    "prompt": prompt_text,
                    "negative_prompt": negative_prompt,
                    "start_image": start_image,
                    "end_image": end_image,
                    "status": "queued",
                    "created_at": datetime.now().isoformat(),
                    "progress": 0,
                    "settings": {
                        "num_frames": num_frames,
                        "steps": steps,
                        "cfg_scale": cfg_scale,
                        "motion_scale": motion_scale,
                        "seed": seed
                    }
                }
                _comfyui_generations.append(generation)

                return {
                    "generation_id": prompt_id,
                    "status": "queued",
                    "message": "Video generation queued successfully",
                    "type": "video",
                    "num_frames": num_frames
                }
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to queue video generation")
    except httpx.RequestError as e:
        # ComfyUI 미연결 시 에러 반환 (데모 모드 제거)
        raise HTTPException(status_code=503, detail=f"ComfyUI service unavailable: {str(e)}")


@app.delete("/api/comfyui/generations/{generation_id}")
async def delete_comfyui_generation(generation_id: str):
    """Delete a generation from history"""
    global _comfyui_generations

    _comfyui_generations = [g for g in _comfyui_generations if g["id"] != generation_id]
    return {"success": True, "message": f"Generation {generation_id} deleted"}


@app.get("/api/comfyui/object_info")
async def get_comfyui_object_info():
    """Get ComfyUI available nodes and models info"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{COMFYUI_SERVICE_URL}/object_info")
            if response.status_code == 200:
                return response.json()
            return {"error": "Could not fetch object info"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/comfyui/models")
async def get_comfyui_models():
    """Get list of available models (checkpoints)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{COMFYUI_SERVICE_URL}/object_info/CheckpointLoaderSimple")
            if response.status_code == 200:
                data = response.json()
                checkpoints = data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
                return {"models": checkpoints}
            return {"models": [], "error": "Could not fetch models"}
    except Exception as e:
        return {"models": [], "error": str(e)}


# ============================================
# 정적 파일 서빙 (프론트엔드) - SPA 지원
# ============================================

frontend_path = "/app/frontend"
if os.path.exists(frontend_path):
    from fastapi.responses import FileResponse

    # SPA fallback: 알려지지 않은 경로에 대해 index.html 반환
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API 경로는 제외 (이미 위에서 처리됨)
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        # 정적 파일 확인 (assets, index 등)
        file_path = os.path.join(frontend_path, full_path)
        if os.path.isfile(file_path):
            # 파일 확장자에 따라 올바른 MIME 타입으로 반환
            if full_path.endswith('.js'):
                return FileResponse(file_path, media_type="application/javascript")
            elif full_path.endswith('.css'):
                return FileResponse(file_path, media_type="text/css")
            elif full_path.endswith('.json'):
                return FileResponse(file_path, media_type="application/json")
            elif full_path.endswith('.wasm'):
                return FileResponse(file_path, media_type="application/wasm")
            else:
                return FileResponse(file_path)

        # SPA: index.html 반환 (HTML 경로에만)
        if not full_path or '.' not in full_path.split('/')[-1]:
            index_path = os.path.join(frontend_path, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)

        raise HTTPException(status_code=404, detail="Not Found")

    # 정적 파일 (CSS, JS, 이미지 등)
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
