"""
Workloads API Router
- 워크로드 상태 조회 및 제어 (시작/중지/스케일)
"""

from fastapi import APIRouter, HTTPException
from kubernetes import client
from kubernetes.client.rest import ApiException
from pydantic import BaseModel
from typing import Optional
from utils.k8s import get_k8s_clients
from utils.config import WORKLOADS

router = APIRouter(prefix="/api/workloads", tags=["workloads"])


class WorkloadAction(BaseModel):
    """워크로드 액션 요청"""
    action: str  # start, stop, scale, expand
    replicas: Optional[int] = 1
    storage_size_gb: Optional[int] = None  # RustFS 스토리지 할당 크기 (GB)
    config: Optional[dict] = None  # 워크로드별 설정 (model, gpuCount, gpuIndices, nodeSelector 등)


@router.get("")
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


@router.get("/status")
async def get_workloads_status():
    """Get workloads status summary (for Pipeline page)"""
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


@router.post("/{workload_name}")
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


@router.post("/{workload_name}/stop")
async def stop_workload(workload_name: str):
    """워크로드 중지 API (프론트엔드 호환용)"""
    if workload_name not in WORKLOADS:
        raise HTTPException(status_code=404, detail=f"Unknown workload: {workload_name}")

    try:
        core_v1, apps_v1, _ = get_k8s_clients()
        workload_config = WORKLOADS[workload_name]
        namespace = workload_config["namespace"]

        # 워크로드 replicas를 0으로 설정하여 중지
        if "deployment" in workload_config:
            apps_v1.patch_namespaced_deployment(
                workload_config["deployment"],
                namespace,
                {"spec": {"replicas": 0}}
            )
        elif "statefulset" in workload_config:
            apps_v1.patch_namespaced_stateful_set(
                workload_config["statefulset"],
                namespace,
                {"spec": {"replicas": 0}}
            )

        return {
            "success": True,
            "workload": workload_name,
            "action": "stop",
            "message": f"{workload_name} 중지 요청이 전송되었습니다."
        }
    except ApiException as e:
        if e.status == 404:
            return {
                "success": True,
                "workload": workload_name,
                "action": "stop",
                "message": f"{workload_name}이(가) 이미 배포되지 않은 상태입니다."
            }
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Helper Functions (워크로드 생성용)
# ============================================

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


# ============================================
# Placeholder functions (main.py에서 구현 필요)
# TODO: 각 워크로드별 생성 함수는 별도 모듈로 분리 권장
# ============================================

async def update_rustfs_storage_size(core_v1, apps_v1, namespace: str, storage_size_gb: int):
    """RustFS 스토리지 크기 업데이트"""
    # TODO: main.py의 update_rustfs_storage_size 함수 구현 참조
    raise NotImplementedError("update_rustfs_storage_size 함수는 main.py에서 구현 필요")


async def create_comfyui_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """ComfyUI Deployment 생성"""
    # TODO: main.py의 create_comfyui_deployment 함수 구현 참조
    raise NotImplementedError("create_comfyui_deployment 함수는 main.py에서 구현 필요")


async def create_vllm_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """vLLM Deployment 생성"""
    # TODO: main.py의 create_vllm_deployment 함수 구현 참조
    raise NotImplementedError("create_vllm_deployment 함수는 main.py에서 구현 필요")


async def create_embedding_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """Embedding Service Deployment 생성"""
    # TODO: main.py의 create_embedding_deployment 함수 구현 참조
    raise NotImplementedError("create_embedding_deployment 함수는 main.py에서 구현 필요")


async def create_rustfs_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """RustFS Deployment 생성"""
    # TODO: main.py의 create_rustfs_deployment 함수 구현 참조
    raise NotImplementedError("create_rustfs_deployment 함수는 main.py에서 구현 필요")


async def create_loki_deployment(namespace: str, config: dict, core_v1, apps_v1):
    """Loki Deployment 생성"""
    # TODO: main.py의 create_loki_deployment 함수 구현 참조
    raise NotImplementedError("create_loki_deployment 함수는 main.py에서 구현 필요")


async def create_qdrant_statefulset(namespace: str, config: dict, core_v1, apps_v1):
    """Qdrant StatefulSet 생성"""
    # TODO: main.py의 create_qdrant_statefulset 함수 구현 참조
    raise NotImplementedError("create_qdrant_statefulset 함수는 main.py에서 구현 필요")


async def create_neo4j_statefulset(namespace: str, config: dict, core_v1, apps_v1):
    """Neo4j StatefulSet 생성"""
    # TODO: main.py의 create_neo4j_statefulset 함수 구현 참조
    raise NotImplementedError("create_neo4j_statefulset 함수는 main.py에서 구현 필요")


async def create_promtail_daemonset(namespace: str, config: dict, core_v1, apps_v1):
    """Promtail DaemonSet 생성"""
    # TODO: main.py의 create_promtail_daemonset 함수 구현 참조
    raise NotImplementedError("create_promtail_daemonset 함수는 main.py에서 구현 필요")
