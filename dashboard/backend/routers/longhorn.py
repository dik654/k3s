"""
Longhorn Storage API
볼륨, 스냅샷, 백업 관리
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time

router = APIRouter(prefix="/api/longhorn", tags=["longhorn"])


def get_k8s_clients():
    """Kubernetes 클라이언트 초기화"""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api(), client.AppsV1Api(), client.CustomObjectsApi()


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


# ============================================
# 모델 정의
# ============================================

class SnapshotCreate(BaseModel):
    name: str
    labels: Optional[dict] = None


class SnapshotRestore(BaseModel):
    snapshot_name: str


# ============================================
# Longhorn Volume API
# ============================================

@router.get("/volumes")
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


@router.get("/volumes/{volume_name}")
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


@router.get("/volumes/{volume_name}/snapshots")
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


@router.post("/volumes/{volume_name}/snapshots")
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


@router.delete("/snapshots/{snapshot_name}")
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


@router.post("/volumes/{volume_name}/restore")
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


@router.put("/volumes/{volume_name}/expand")
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


@router.get("/status")
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
