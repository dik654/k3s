"""
Storage management API (MinIO, Longhorn, RustFS)
버킷, 객체, 볼륨, 스냅샷, 사용자/쿼터 관리
"""
import os
import asyncio
import subprocess
import json
import base64
from datetime import timedelta, datetime
from typing import Optional, List
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from kubernetes.client.rest import ApiException
from pydantic import BaseModel
from minio import Minio
from minio.error import S3Error

from utils.k8s import get_k8s_clients

router = APIRouter(prefix="/api/storage", tags=["storage"])

# ============================================
# MinIO 클라이언트 설정
# ============================================

MINIO_INTERNAL_ENDPOINT = "rustfs.storage.svc.cluster.local:9000"
MINIO_EXTERNAL_ENDPOINT = "14.32.100.220:30900"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "admin1234"
MINIO_ADMIN_ENDPOINT = "http://rustfs.storage.svc.cluster.local:9000"

# 인메모리 저장소 (실제로는 DB 사용 권장)
bucket_quotas = {}
storage_users = {
    "admin": {
        "secret_key": "admin1234",
        "policy": "admin",
        "status": "enabled",
        "buckets": ["*"]
    }
}
bucket_user_permissions = {}


def get_minio_client():
    """MinIO 클라이언트 생성 (내부 통신용)"""
    return Minio(
        MINIO_INTERNAL_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )


def get_minio_client_external():
    """MinIO 클라이언트 생성 (외부 Presigned URL용)"""
    return Minio(
        MINIO_EXTERNAL_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )


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
# Pydantic 모델 정의
# ============================================

class StorageConfig(BaseModel):
    size_gb: int


class StorageResetRequest(BaseModel):
    new_size_gb: int
    confirm: bool = False


class BucketCreate(BaseModel):
    name: str


class ObjectUpload(BaseModel):
    object_name: str
    content: str  # base64 encoded
    content_type: str = "application/octet-stream"


class FolderCreate(BaseModel):
    folder_name: str


class BucketPolicy(BaseModel):
    policy: dict


class VersioningConfig(BaseModel):
    enabled: bool


class PresignedUrlRequest(BaseModel):
    object_name: str
    expires_hours: int = 1
    method: str = "GET"


class ObjectTags(BaseModel):
    tags: dict


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


class BucketQuota(BaseModel):
    quota_bytes: int
    quota_type: str = "hard"


class StorageUser(BaseModel):
    access_key: str
    secret_key: str
    policy: str = "readwrite"


class IAMUser(BaseModel):
    access_key: str
    secret_key: str
    policy: str = "readwrite"


class AbortMultipartUpload(BaseModel):
    object_name: str
    upload_id: str


class ObjectLockConfig(BaseModel):
    mode: str = "GOVERNANCE"
    duration: int = 30
    duration_unit: str = "DAYS"


class LegalHoldConfig(BaseModel):
    enabled: bool


class RetentionConfig(BaseModel):
    mode: str = "GOVERNANCE"
    retain_until_date: str


class BucketUserPermission(BaseModel):
    user: str
    access: str  # read, write, admin
    quota_gb: Optional[float] = None


# ============================================
# 헬퍼 함수
# ============================================

async def get_storage_disk_info():
    """스토리지 노드의 실제 디스크 정보 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        pods = core_v1.list_namespaced_pod(namespace="storage", label_selector="app=rustfs")

        if not pods.items:
            pvc_list = core_v1.list_namespaced_persistent_volume_claim(namespace="storage")
            for pvc in pvc_list.items:
                if "rustfs" in pvc.metadata.name or "data-rustfs" in pvc.metadata.name:
                    storage_req = pvc.spec.resources.requests.get("storage", "100Gi")
                    if storage_req.endswith("Gi"):
                        return {"total_capacity": int(storage_req[:-2]) * 1024 * 1024 * 1024}
                    elif storage_req.endswith("Ti"):
                        return {"total_capacity": int(storage_req[:-2]) * 1024 * 1024 * 1024 * 1024}
            return {"total_capacity": 100 * 1024 * 1024 * 1024}

        pod = pods.items[0]
        node_name = pod.spec.node_name

        node = core_v1.read_node(node_name)
        allocatable = node.status.allocatable or {}
        ephemeral = allocatable.get("ephemeral-storage", "0")

        if ephemeral.endswith("Ki"):
            total_bytes = int(ephemeral[:-2]) * 1024
        elif ephemeral.endswith("Mi"):
            total_bytes = int(ephemeral[:-2]) * 1024 * 1024
        elif ephemeral.endswith("Gi"):
            total_bytes = int(ephemeral[:-2]) * 1024 * 1024 * 1024
        else:
            total_bytes = int(ephemeral)

        pvc_list = core_v1.list_namespaced_persistent_volume_claim(namespace="storage")
        target_pvc = None

        for pvc in pvc_list.items:
            pvc_name = pvc.metadata.name
            if pvc_name.startswith("data-rustfs-") and pvc_name[-1].isdigit():
                target_pvc = pvc
                break
            elif pvc_name == "data-rustfs" and target_pvc is None:
                target_pvc = pvc

        if target_pvc:
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
                return {"total_capacity": min(total_bytes, pvc_bytes)}

        return {"total_capacity": total_bytes}

    except Exception as e:
        print(f"Storage disk info error: {e}")
        return {"total_capacity": 100 * 1024 * 1024 * 1024}


async def check_quota_before_upload(bucket_name: str, file_size: int) -> bool:
    """업로드 전 쿼터 체크"""
    if bucket_name not in bucket_quotas:
        return True

    quota = bucket_quotas[bucket_name]
    if quota["quota_bytes"] == 0:
        return True

    client = get_minio_client()
    objects = list(client.list_objects(bucket_name, recursive=True))
    current_usage = sum(obj.size for obj in objects if obj.size)

    return (current_usage + file_size) <= quota["quota_bytes"]


async def update_bucket_policy_for_user(client, bucket_name: str, user: str, access: str):
    """사용자별 버킷 정책 업데이트"""
    try:
        if access == "read":
            actions = ["s3:GetObject", "s3:ListBucket"]
        elif access == "write":
            actions = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        elif access == "admin":
            actions = ["s3:*"]
        else:
            actions = ["s3:GetObject", "s3:ListBucket"]

        try:
            current_policy = client.get_bucket_policy(bucket_name)
            policy = json.loads(current_policy)
        except:
            policy = {
                "Version": "2012-10-17",
                "Statement": []
            }

        policy["Statement"] = [
            stmt for stmt in policy.get("Statement", [])
            if not (stmt.get("Sid", "").startswith(f"User{user}"))
        ]

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


# ============================================
# RustFS 스토리지 관리 API
# ============================================

@router.get("/rustfs")
async def get_rustfs_status():
    """RustFS 상태 조회 (Deployment 또는 StatefulSet 지원)"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()
        namespace = "storage"

        # Deployment 먼저 확인 (Longhorn 사용 시)
        try:
            deploy = apps_v1.read_namespaced_deployment("rustfs", namespace)

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


@router.post("/rustfs/resize")
async def resize_rustfs(config: StorageConfig):
    """RustFS 스토리지 크기 변경"""
    return {
        "message": f"RustFS 스토리지를 {config.size_gb}GB로 조정 요청됨",
        "size_gb": config.size_gb
    }


@router.post("/rustfs/reset")
async def reset_rustfs_storage(request: StorageResetRequest):
    """RustFS 스토리지 초기화 (축소 포함)"""
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

        # StatefulSet 삭제
        try:
            apps_v1.delete_namespaced_stateful_set(
                name="rustfs",
                namespace=namespace,
                propagation_policy="Foreground"
            )
            await asyncio.sleep(5)
        except ApiException as e:
            if e.status != 404:
                raise

        # PVC 삭제
        pvcs = core_v1.list_namespaced_persistent_volume_claim(namespace)
        for pvc in pvcs.items:
            if pvc.metadata.name.startswith("data-rustfs"):
                core_v1.delete_namespaced_persistent_volume_claim(
                    name=pvc.metadata.name,
                    namespace=namespace
                )

        # 매니페스트 파일 업데이트
        import re
        manifest_path = "/app/manifests/14-rustfs.yaml"
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                content = f.read()

            content = re.sub(
                r'storage:\s*\d+Gi',
                f'storage: {request.new_size_gb}Gi',
                content
            )

            with open(manifest_path, "w") as f:
                f.write(content)

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
# 스토리지 상태/용량 API
# ============================================

@router.get("/status")
async def get_storage_status():
    """스토리지 서비스 상태 확인 (실제 디스크 용량 포함)"""
    try:
        client = get_minio_client()
        buckets = list(client.list_buckets())

        total_used = 0
        for bucket in buckets:
            objects = list(client.list_objects(bucket.name, recursive=True))
            total_used += sum(obj.size for obj in objects if obj.size)

        storage_info = await get_storage_disk_info()

        return {
            "status": "connected",
            "bucket_count": len(buckets),
            "endpoint": MINIO_INTERNAL_ENDPOINT,
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


@router.get("/available-capacity")
async def get_available_storage_capacity():
    """노드의 가용 스토리지 용량 조회"""
    try:
        core_v1, _, _ = get_k8s_clients()

        nodes = core_v1.list_node()
        node_storage = []
        total_available = 0

        for node in nodes.items:
            node_name = node.metadata.name
            allocatable = node.status.allocatable or {}
            capacity = node.status.capacity or {}

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

        current_pvc_size = 0
        current_storage_class = None
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
                current_storage_class = target_pvc.spec.storage_class_name
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

        max_single_node = max((n["allocatable"] for n in node_storage), default=0)

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
            "supports_expansion": current_storage_class == "longhorn",
            "recommended_sizes": recommended_sizes,
            "min_size": 10 * 1024 * 1024 * 1024,
            "min_size_human": "10 GB"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity")
async def get_storage_capacity():
    """스토리지 용량 정보 조회 (프론트엔드 호환)"""
    try:
        result = await get_available_storage_capacity()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_storage_info():
    """스토리지 정보 조회 (프론트엔드 호환)"""
    try:
        status = await get_storage_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage-breakdown")
async def get_storage_usage_breakdown():
    """스토리지 사용량 분류 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        current_node = os.environ.get('NODE_NAME', 'unknown')
        if current_node == 'unknown':
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

        # 디스크 사용량 조회
        try:
            df_result = subprocess.run(
                ["df", "-B1", "/"],
                capture_output=True, text=True
            )
            if df_result.returncode == 0:
                lines = df_result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        breakdown["total_capacity"] = int(parts[1])
                        breakdown["total_used"] = int(parts[2])
                        breakdown["total_available"] = int(parts[3])
        except:
            pass

        # RustFS PVC 사용량
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
        except:
            pass

        # RustFS 실제 데이터 크기
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

        # 시스템/부팅 데이터
        system_size = 0
        try:
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
            system_size = 10 * 1024 * 1024 * 1024

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

        # K3s 데이터
        try:
            du_result = subprocess.run(
                ["du", "-sb", "/var/lib/rancher"],
                capture_output=True, text=True
            )
            if du_result.returncode == 0:
                parts = du_result.stdout.strip().split()
                if parts:
                    k3s_size = int(parts[0])
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
        except:
            pass

        # Docker 데이터
        try:
            du_result = subprocess.run(
                ["du", "-sb", "/var/lib/docker"],
                capture_output=True, text=True
            )
            if du_result.returncode == 0:
                parts = du_result.stdout.strip().split()
                if parts:
                    docker_size = int(parts[0])
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
        except:
            pass

        # 기타 사용량
        categorized_total = sum(cat["allocated"] for cat in breakdown["categories"])
        other_used = max(0, breakdown["total_used"] - categorized_total)

        if other_used > 1024 * 1024 * 1024:
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

        # 여유 공간
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

        breakdown["total_capacity_human"] = format_size(breakdown["total_capacity"])
        breakdown["total_used_human"] = format_size(breakdown["total_used"])
        breakdown["total_available_human"] = format_size(breakdown["total_available"])
        breakdown["usage_percent"] = round(breakdown["total_used"] / breakdown["total_capacity"] * 100, 1) if breakdown["total_capacity"] > 0 else 0

        return breakdown
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage-by-node")
async def get_storage_usage_by_node():
    """노드별 스토리지 사용량 조회"""
    try:
        core_v1, apps_v1, _ = get_k8s_clients()

        nodes = core_v1.list_node()
        node_storage = []

        for node in nodes.items:
            node_name = node.metadata.name
            labels = node.metadata.labels or {}

            node_data = {
                "node_name": node_name,
                "role": "Master" if "node-role.kubernetes.io/master" in labels or "node-role.kubernetes.io/control-plane" in labels else "Worker",
                "categories": [],
                "total_capacity": 0,
                "total_used": 0,
                "total_available": 0
            }

            # 노드 용량 정보
            capacity = node.status.capacity or {}
            ephemeral_storage = capacity.get("ephemeral-storage", "0")

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

            node_data["total_available"] = node_data["total_capacity"]

            # 디스크 타입 추정
            try:
                node_labels = node.metadata.labels or {}
                if "storage-type" in node_labels:
                    node_data["root_disk_type"] = node_labels["storage-type"]
                else:
                    if node_data["total_capacity"] > 2 * 1024 * 1024 * 1024 * 1024:
                        node_data["root_disk_type"] = "HDD (추정)"
                    else:
                        node_data["root_disk_type"] = "SSD (추정)"
            except:
                node_data["root_disk_type"] = "Unknown"

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

            node_data["total_capacity_human"] = format_size(node_data["total_capacity"])
            node_data["total_used_human"] = format_size(node_data["total_used"])
            node_data["total_available_human"] = format_size(node_data["total_available"])
            node_data["usage_percent"] = round(node_data["total_used"] / node_data["total_capacity"] * 100, 1) if node_data["total_capacity"] > 0 else 0

            node_storage.append(node_data)

        return {"nodes": node_storage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 버킷 관리 API
# ============================================

@router.get("/buckets")
async def list_buckets():
    """버킷 목록 조회"""
    try:
        client = get_minio_client()
        buckets = client.list_buckets()

        result = []
        for bucket in buckets:
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


@router.post("/buckets")
async def create_bucket(bucket: BucketCreate):
    """버킷 생성"""
    try:
        client = get_minio_client()

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


@router.delete("/buckets/{bucket_name}")
async def delete_bucket(bucket_name: str, force: bool = False):
    """버킷 삭제"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

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


@router.get("/buckets/{bucket_name}/stats")
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

            ext = obj.object_name.rsplit('.', 1)[-1].lower() if '.' in obj.object_name else 'unknown'
            file_types[ext] = file_types.get(ext, 0) + 1

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


@router.get("/buckets/{bucket_name}/settings")
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
# 객체 관리 API
# ============================================

@router.get("/buckets/{bucket_name}/objects")
async def list_objects(bucket_name: str, prefix: str = "", delimiter: str = "/"):
    """버킷 내 객체 목록 조회"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        objects = client.list_objects(bucket_name, prefix=prefix, recursive=False)

        result = []
        for obj in objects:
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


@router.post("/buckets/{bucket_name}/objects")
async def upload_object(bucket_name: str, upload: ObjectUpload):
    """객체 업로드"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

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


@router.post("/buckets/{bucket_name}/objects/upload-with-quota")
async def upload_object_with_quota(bucket_name: str, upload: ObjectUpload):
    """객체 업로드 (쿼터 체크 포함)"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        content = base64.b64decode(upload.content)
        file_size = len(content)

        if not await check_quota_before_upload(bucket_name, file_size):
            quota_info = bucket_quotas.get(bucket_name, {})
            raise HTTPException(
                status_code=413,
                detail=f"쿼터 초과! 버킷 쿼터: {format_size(quota_info.get('quota_bytes', 0))}"
            )

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


@router.delete("/buckets/{bucket_name}/objects/{object_name:path}")
async def delete_object(bucket_name: str, object_name: str):
    """객체 삭제"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

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


@router.post("/buckets/{bucket_name}/objects/move")
async def move_object(bucket_name: str, request: Request):
    """객체 이동"""
    try:
        client = get_minio_client()
        data = await request.json()
        source_name = data.get("source")
        dest_name = data.get("destination")

        if not source_name or not dest_name:
            raise HTTPException(status_code=400, detail="source와 destination이 필요합니다")

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        from minio.commonconfig import CopySource

        if source_name.endswith('/'):
            objects = list(client.list_objects(bucket_name, prefix=source_name, recursive=True))
            moved_count = 0
            for obj in objects:
                relative_path = obj.object_name[len(source_name):]
                new_name = dest_name + relative_path

                client.copy_object(
                    bucket_name,
                    new_name,
                    CopySource(bucket_name, obj.object_name)
                )
                client.remove_object(bucket_name, obj.object_name)
                moved_count += 1

            return {"success": True, "message": f"{moved_count}개 객체가 이동되었습니다"}
        else:
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


@router.get("/buckets/{bucket_name}/objects/{object_name:path}/download")
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


@router.get("/buckets/{bucket_name}/objects/{object_name:path}/stream")
async def stream_object(bucket_name: str, object_name: str):
    """객체 스트리밍 (파일 직접 전송)"""
    try:
        minio_client = get_minio_client()

        if not minio_client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        stat = minio_client.stat_object(bucket_name, object_name)

        response = minio_client.get_object(bucket_name, object_name)
        content = response.read()
        response.close()
        response.release_conn()

        content_type = stat.content_type or "application/octet-stream"

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


@router.post("/buckets/{bucket_name}/folders")
async def create_folder(bucket_name: str, folder: FolderCreate):
    """폴더 생성"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        folder_name = folder.folder_name
        if not folder_name.endswith('/'):
            folder_name += '/'

        client.put_object(bucket_name, folder_name, BytesIO(b''), 0)

        return {"success": True, "message": f"폴더 '{folder_name}'이 생성되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 버킷 정책 관리 API
# ============================================

@router.get("/buckets/{bucket_name}/policy")
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


@router.put("/buckets/{bucket_name}/policy")
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


@router.delete("/buckets/{bucket_name}/policy")
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


@router.get("/policy-templates")
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


# ============================================
# 버전 관리 API
# ============================================

@router.get("/buckets/{bucket_name}/versioning")
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


@router.put("/buckets/{bucket_name}/versioning")
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


@router.get("/buckets/{bucket_name}/objects/{object_name:path}/versions")
async def list_object_versions(bucket_name: str, object_name: str):
    """객체의 모든 버전 조회"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        versions = []
        try:
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
        except Exception:
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


# ============================================
# 멀티파트 업로드 API
# ============================================

@router.get("/buckets/{bucket_name}/multipart-uploads")
async def list_multipart_uploads(bucket_name: str):
    """진행 중인 멀티파트 업로드 목록"""
    try:
        client = get_minio_client()

        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        uploads = []
        try:
            result = client._list_multipart_uploads(bucket_name)
            for upload in result:
                uploads.append({
                    "key": upload.object_name,
                    "upload_id": upload.upload_id,
                    "initiated": upload.initiated.isoformat() if upload.initiated else None,
                    "initiator": upload.initiator if hasattr(upload, 'initiator') else None
                })
        except Exception:
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


@router.post("/buckets/{bucket_name}/multipart-uploads/abort")
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


# ============================================
# Presigned URL API
# ============================================

@router.post("/buckets/{bucket_name}/presigned-url")
async def generate_presigned_url(bucket_name: str, request: PresignedUrlRequest):
    """Presigned URL 생성"""
    try:
        internal_client = get_minio_client()
        if not internal_client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

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


# ============================================
# 객체 태그 관리 API
# ============================================

@router.get("/buckets/{bucket_name}/objects/{object_name:path}/tags")
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


@router.put("/buckets/{bucket_name}/objects/{object_name:path}/tags")
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


@router.delete("/buckets/{bucket_name}/objects/{object_name:path}/tags")
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


# ============================================
# 생명주기 규칙 API
# ============================================

@router.get("/buckets/{bucket_name}/lifecycle")
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


@router.put("/buckets/{bucket_name}/lifecycle")
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


@router.delete("/buckets/{bucket_name}/lifecycle")
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


@router.get("/lifecycle-templates")
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


# ============================================
# 쿼터 관리 API
# ============================================

@router.get("/buckets/{bucket_name}/quota")
async def get_bucket_quota(bucket_name: str):
    """버킷 쿼터 조회"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        objects = list(client.list_objects(bucket_name, recursive=True))
        current_usage = sum(obj.size for obj in objects if obj.size)

        quota_info = bucket_quotas.get(bucket_name, {"quota_bytes": 0, "quota_type": "none"})

        return {
            "bucket": bucket_name,
            "quota_enabled": quota_info.get("quota_bytes", 0) > 0,
            "quota_bytes": quota_info.get("quota_bytes", 0),
            "quota_human": format_size(quota_info.get("quota_bytes", 0)) if quota_info.get("quota_bytes", 0) > 0 else "무제한",
            "quota_type": quota_info.get("quota_type", "none"),
            "current_usage": current_usage,
            "current_usage_human": format_size(current_usage),
            "usage_percent": round(current_usage / quota_info.get("quota_bytes", 1) * 100, 1) if quota_info.get("quota_bytes", 0) > 0 else 0,
            "remaining": max(0, quota_info.get("quota_bytes", 0) - current_usage) if quota_info.get("quota_bytes", 0) > 0 else None,
            "remaining_human": format_size(max(0, quota_info.get("quota_bytes", 0) - current_usage)) if quota_info.get("quota_bytes", 0) > 0 else "무제한"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/buckets/{bucket_name}/quota")
async def set_bucket_quota(bucket_name: str, quota: BucketQuota):
    """버킷 쿼터 설정"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        if quota.quota_bytes == 0:
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


@router.delete("/buckets/{bucket_name}/quota")
async def delete_bucket_quota(bucket_name: str):
    """버킷 쿼터 제거"""
    try:
        bucket_quotas.pop(bucket_name, None)
        return {"success": True, "message": f"버킷 '{bucket_name}'의 쿼터가 제거되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota-presets")
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


# ============================================
# 객체 잠금 API
# ============================================

@router.get("/buckets/{bucket_name}/object-lock")
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


@router.put("/buckets/{bucket_name}/object-lock")
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


@router.get("/buckets/{bucket_name}/objects/{object_name:path}/legal-hold")
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


@router.put("/buckets/{bucket_name}/objects/{object_name:path}/legal-hold")
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


@router.get("/buckets/{bucket_name}/objects/{object_name:path}/retention")
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


@router.put("/buckets/{bucket_name}/objects/{object_name:path}/retention")
async def set_object_retention(bucket_name: str, object_name: str, config: RetentionConfig, version_id: str = None):
    """객체 보존 정책 설정"""
    try:
        from minio.retention import Retention
        from minio.commonconfig import GOVERNANCE, COMPLIANCE

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


# ============================================
# 사용자 관리 API
# ============================================

@router.get("/users")
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


@router.post("/users")
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


@router.delete("/users/{access_key}")
async def delete_storage_user(access_key: str):
    """스토리지 사용자 삭제"""
    if access_key == "admin":
        raise HTTPException(status_code=400, detail="관리자 계정은 삭제할 수 없습니다")
    if access_key not in storage_users:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    del storage_users[access_key]
    return {"success": True, "message": f"사용자 '{access_key}'가 삭제되었습니다"}


@router.put("/users/{access_key}/buckets")
async def set_user_buckets(access_key: str, buckets: list[str]):
    """사용자가 접근 가능한 버킷 설정"""
    if access_key not in storage_users:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    storage_users[access_key]["buckets"] = buckets
    return {"success": True, "message": f"사용자 '{access_key}'의 버킷 접근 권한이 설정되었습니다"}


@router.put("/users/{access_key}/quota")
async def set_user_quota(access_key: str, quota_bytes: int):
    """사용자 총 쿼터 설정"""
    if access_key not in storage_users:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    storage_users[access_key]["quota_bytes"] = quota_bytes
    return {
        "success": True,
        "message": f"사용자 '{access_key}'의 쿼터가 {format_size(quota_bytes)}로 설정되었습니다"
    }


# ============================================
# IAM 관리 API
# ============================================

@router.get("/iam/users")
async def list_iam_users():
    """MinIO IAM 사용자 목록"""
    try:
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


@router.post("/iam/users")
async def create_iam_user(user: IAMUser):
    """MinIO IAM 사용자 생성"""
    try:
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


@router.delete("/iam/users/{access_key}")
async def delete_iam_user(access_key: str):
    """MinIO IAM 사용자 삭제"""
    try:
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


@router.get("/iam/policies")
async def list_iam_policies():
    """MinIO 정책 목록"""
    try:
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


@router.put("/iam/users/{access_key}/policy")
async def attach_iam_policy(access_key: str, policy: str):
    """사용자에게 정책 할당"""
    try:
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


@router.get("/iam/users/{access_key}/info")
async def get_iam_user_info(access_key: str):
    """IAM 사용자 상세 정보"""
    try:
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


@router.put("/iam/users/{access_key}/status")
async def set_iam_user_status(access_key: str, enabled: bool):
    """IAM 사용자 활성화/비활성화"""
    try:
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


# ============================================
# 버킷별 사용자 접근 권한 API
# ============================================

@router.get("/buckets/{bucket_name}/users")
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


@router.post("/buckets/{bucket_name}/users")
async def add_bucket_user(bucket_name: str, permission: BucketUserPermission):
    """버킷에 사용자 접근 권한 추가"""
    try:
        client = get_minio_client()
        if not client.bucket_exists(bucket_name):
            raise HTTPException(status_code=404, detail="버킷을 찾을 수 없습니다")

        if permission.user not in storage_users and permission.user != "admin":
            raise HTTPException(status_code=404, detail=f"사용자 '{permission.user}'를 찾을 수 없습니다")

        if bucket_name not in bucket_user_permissions:
            bucket_user_permissions[bucket_name] = {}

        quota_bytes = int(permission.quota_gb * 1024 * 1024 * 1024) if permission.quota_gb else None

        bucket_user_permissions[bucket_name][permission.user] = {
            "access": permission.access,
            "quota_bytes": quota_bytes
        }

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


@router.delete("/buckets/{bucket_name}/users/{user}")
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


@router.put("/buckets/{bucket_name}/users/{user}")
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
