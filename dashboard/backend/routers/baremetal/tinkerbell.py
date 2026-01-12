"""
Tinkerbell API Router

Tinkerbell CRD를 통한 베어메탈 프로비저닝:
- Hardware: 서버 등록 및 관리
- Template: OS 설치 템플릿
- Workflow: 프로비저닝 워크플로우
"""
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from kubernetes.client.rest import ApiException

from utils.k8s_client import get_k8s_clients, get_custom_objects_api
from models.baremetal import (
    Hardware, HardwareStatus, HardwareRegistration, HardwareSpec,
    BMCInfo, DiskInfo, DiskType, NetworkInterface,
    OSTemplate, ProvisioningWorkflow, WorkflowStatus,
    DiskSwapRequest
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/baremetal", tags=["baremetal"])

# Tinkerbell CRD 정보
TINKERBELL_GROUP = "tinkerbell.org"
TINKERBELL_VERSION = "v1alpha1"
TINKERBELL_NAMESPACE = "tinkerbell"

# 데모 모드 (Tinkerbell 미설치 시)
_demo_mode = False


def _check_tinkerbell_available() -> bool:
    """Tinkerbell CRD 사용 가능 여부 확인"""
    global _demo_mode
    try:
        custom = get_custom_objects_api()
        custom.list_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="hardware"
        )
        _demo_mode = False
        return True
    except ApiException as e:
        if e.status == 404:
            _demo_mode = True
            logger.warning("Tinkerbell CRD not found, running in demo mode")
        return False
    except Exception:
        _demo_mode = True
        return False


# 데모 데이터
DEMO_HARDWARE: List[Hardware] = [
    Hardware(
        id="hw-001",
        name="gpu-server-01",
        status=HardwareStatus.AVAILABLE,
        bmc=BMCInfo(ip="192.168.1.101", username="admin", password="***", vendor="ipmi"),
        spec=HardwareSpec(cpu_cores=64, cpu_model="AMD EPYC 7763", memory_gb=256, gpu_count=4, gpu_model="NVIDIA A100 80GB"),
        disks=[
            DiskInfo(device="/dev/nvme0n1", size_gb=500, disk_type=DiskType.RENTAL, label="Rental Disk", is_active=True),
            DiskInfo(device="/dev/nvme1n1", size_gb=2000, disk_type=DiskType.OWNER, label="Owner Disk", is_active=False),
        ],
        active_disk="/dev/nvme0n1",
        interfaces=[NetworkInterface(mac="00:1A:2B:3C:4D:01", ip="10.0.0.101", gateway="10.0.0.1", is_management=True)],
        owner_id="owner-001",
        owner_name="홍길동",
        labels={"gpu": "a100", "location": "rack-1"},
        created_at=datetime.now()
    ),
    Hardware(
        id="hw-002",
        name="gpu-server-02",
        status=HardwareStatus.RENTED,
        bmc=BMCInfo(ip="192.168.1.102", username="admin", password="***", vendor="redfish"),
        spec=HardwareSpec(cpu_cores=32, cpu_model="Intel Xeon Gold 6348", memory_gb=128, gpu_count=2, gpu_model="NVIDIA RTX 4090"),
        disks=[
            DiskInfo(device="/dev/sda", size_gb=1000, disk_type=DiskType.RENTAL, label="Rental Disk", is_active=True),
            DiskInfo(device="/dev/sdb", size_gb=4000, disk_type=DiskType.OWNER, label="Owner Disk", is_active=False),
        ],
        active_disk="/dev/sda",
        interfaces=[NetworkInterface(mac="00:1A:2B:3C:4D:02", ip="10.0.0.102", gateway="10.0.0.1", is_management=True)],
        owner_id="owner-002",
        owner_name="김철수",
        current_rental_id="rental-001",
        labels={"gpu": "rtx4090", "location": "rack-2"},
        created_at=datetime.now()
    ),
    Hardware(
        id="hw-003",
        name="compute-server-01",
        status=HardwareStatus.OWNER_USE,
        bmc=BMCInfo(ip="192.168.1.103", username="admin", password="***", vendor="dell-idrac"),
        spec=HardwareSpec(cpu_cores=128, cpu_model="AMD EPYC 9654", memory_gb=512, gpu_count=0, gpu_model=""),
        disks=[
            DiskInfo(device="/dev/nvme0n1", size_gb=500, disk_type=DiskType.RENTAL, label="Rental Disk", is_active=False),
            DiskInfo(device="/dev/nvme1n1", size_gb=8000, disk_type=DiskType.OWNER, label="Owner Disk", is_active=True),
        ],
        active_disk="/dev/nvme1n1",
        interfaces=[NetworkInterface(mac="00:1A:2B:3C:4D:03", ip="10.0.0.103", gateway="10.0.0.1", is_management=True)],
        owner_id="owner-001",
        owner_name="홍길동",
        labels={"type": "compute", "location": "rack-1"},
        created_at=datetime.now()
    ),
]

DEMO_TEMPLATES: List[OSTemplate] = [
    OSTemplate(
        id="tpl-ubuntu-2204",
        name="Ubuntu 22.04 LTS (Rental)",
        os_name="Ubuntu",
        os_version="22.04",
        description="대여용 Ubuntu 22.04 LTS 서버 이미지 - 기본 개발 도구 포함",
        image_url="http://10.0.0.1:8080/images/ubuntu-22.04-server.raw",
        disk_device="/dev/sda",
        for_rental=True,
        actions=[
            {"name": "disk-wipe", "image": "quay.io/tinkerbell-actions/disk-wipe:v1.0.0"},
            {"name": "image2disk", "image": "quay.io/tinkerbell-actions/image2disk:v1.0.0"},
            {"name": "kexec", "image": "quay.io/tinkerbell-actions/kexec:v1.0.0"},
        ],
        created_at=datetime.now()
    ),
    OSTemplate(
        id="tpl-rocky-93",
        name="Rocky Linux 9.3 (Rental)",
        os_name="Rocky Linux",
        os_version="9.3",
        description="대여용 Rocky Linux 9.3 서버 이미지 - RHEL 호환",
        image_url="http://10.0.0.1:8080/images/rocky-9.3-server.raw",
        disk_device="/dev/sda",
        for_rental=True,
        created_at=datetime.now()
    ),
    OSTemplate(
        id="tpl-ubuntu-2404-cuda",
        name="Ubuntu 24.04 + CUDA 12.4 (Rental)",
        os_name="Ubuntu",
        os_version="24.04",
        description="대여용 Ubuntu 24.04 + NVIDIA CUDA 12.4 - ML 워크로드용",
        image_url="http://10.0.0.1:8080/images/ubuntu-24.04-cuda-12.4.raw",
        disk_device="/dev/sda",
        for_rental=True,
        post_install_script="#!/bin/bash\nnvidia-smi\n",
        created_at=datetime.now()
    ),
]


# ============================================
# 하드웨어 관리 API
# ============================================

@router.get("/hardware", response_model=List[Hardware])
async def list_hardware(
    status: Optional[HardwareStatus] = Query(None, description="상태 필터"),
    owner_id: Optional[str] = Query(None, description="소유자 ID 필터"),
    has_gpu: Optional[bool] = Query(None, description="GPU 보유 여부 필터")
):
    """등록된 베어메탈 하드웨어 목록 조회"""
    _check_tinkerbell_available()

    if _demo_mode:
        result = DEMO_HARDWARE.copy()
        if status:
            result = [h for h in result if h.status == status]
        if owner_id:
            result = [h for h in result if h.owner_id == owner_id]
        if has_gpu is not None:
            result = [h for h in result if (h.spec.gpu_count > 0) == has_gpu]
        return result

    try:
        custom = get_custom_objects_api()
        hardware_list = custom.list_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="hardware"
        )

        result = []
        for item in hardware_list.get("items", []):
            hw = _parse_tinkerbell_hardware(item)
            if status and hw.status != status:
                continue
            if owner_id and hw.owner_id != owner_id:
                continue
            if has_gpu is not None and (hw.spec.gpu_count > 0) != has_gpu:
                continue
            result.append(hw)

        return result
    except ApiException as e:
        raise HTTPException(status_code=500, detail=f"Failed to list hardware: {e.reason}")


@router.get("/hardware/{hardware_id}", response_model=Hardware)
async def get_hardware(hardware_id: str):
    """특정 하드웨어 상세 정보 조회"""
    _check_tinkerbell_available()

    if _demo_mode:
        for hw in DEMO_HARDWARE:
            if hw.id == hardware_id:
                return hw
        raise HTTPException(status_code=404, detail=f"Hardware not found: {hardware_id}")

    try:
        custom = get_custom_objects_api()
        item = custom.get_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="hardware",
            name=hardware_id
        )
        return _parse_tinkerbell_hardware(item)
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Hardware not found: {hardware_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get hardware: {e.reason}")


@router.post("/hardware", response_model=Hardware)
async def register_hardware(reg: HardwareRegistration):
    """새 베어메탈 하드웨어 등록"""
    _check_tinkerbell_available()

    if _demo_mode:
        # 데모 모드에서는 메모리에 추가
        new_hw = Hardware(
            id=f"hw-{len(DEMO_HARDWARE)+1:03d}",
            name=reg.name,
            status=HardwareStatus.AVAILABLE,
            bmc=BMCInfo(
                ip=reg.bmc_ip,
                username=reg.bmc_username,
                password="***",
                vendor=reg.bmc_vendor
            ),
            spec=HardwareSpec(),
            disks=[
                DiskInfo(device=reg.rental_disk, size_gb=reg.rental_disk_size_gb, disk_type=DiskType.RENTAL, label="Rental"),
                DiskInfo(device=reg.owner_disk, size_gb=reg.owner_disk_size_gb, disk_type=DiskType.OWNER, label="Owner"),
            ],
            active_disk=reg.rental_disk,
            interfaces=[NetworkInterface(mac=reg.mac_address, ip=reg.ip_address, gateway=reg.gateway, is_management=True)],
            owner_id=reg.owner_id,
            owner_name=reg.owner_name,
            labels=reg.labels,
            created_at=datetime.now()
        )
        DEMO_HARDWARE.append(new_hw)
        return new_hw

    # 실제 Tinkerbell Hardware CRD 생성
    try:
        custom = get_custom_objects_api()

        hardware_manifest = {
            "apiVersion": f"{TINKERBELL_GROUP}/{TINKERBELL_VERSION}",
            "kind": "Hardware",
            "metadata": {
                "name": reg.name.lower().replace(" ", "-"),
                "namespace": TINKERBELL_NAMESPACE,
                "labels": {
                    **reg.labels,
                    "baremetal.k3s.io/owner-id": reg.owner_id or "",
                    "baremetal.k3s.io/owner-name": reg.owner_name or "",
                },
                "annotations": {
                    "baremetal.k3s.io/rental-disk": reg.rental_disk,
                    "baremetal.k3s.io/owner-disk": reg.owner_disk,
                }
            },
            "spec": {
                "bmcRef": {
                    "host": reg.bmc_ip,
                    "username": reg.bmc_username,
                    "password": reg.bmc_password,
                },
                "interfaces": [
                    {
                        "netboot": {"allowPXE": True, "allowWorkflow": True},
                        "dhcp": {
                            "mac": reg.mac_address,
                            "ip": {"address": reg.ip_address or "", "gateway": reg.gateway or ""},
                            "hostname": reg.name,
                        }
                    }
                ],
                "disks": [
                    {"device": reg.rental_disk},
                    {"device": reg.owner_disk}
                ],
                "metadata": {
                    "state": "available"
                }
            }
        }

        result = custom.create_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="hardware",
            body=hardware_manifest
        )

        return _parse_tinkerbell_hardware(result)
    except ApiException as e:
        raise HTTPException(status_code=500, detail=f"Failed to register hardware: {e.reason}")


@router.delete("/hardware/{hardware_id}")
async def delete_hardware(hardware_id: str, force: bool = False):
    """하드웨어 등록 해제"""
    _check_tinkerbell_available()

    if _demo_mode:
        global DEMO_HARDWARE
        for i, hw in enumerate(DEMO_HARDWARE):
            if hw.id == hardware_id:
                if hw.status == HardwareStatus.RENTED and not force:
                    raise HTTPException(status_code=400, detail="대여 중인 하드웨어는 삭제할 수 없습니다. force=true로 강제 삭제하세요.")
                DEMO_HARDWARE.pop(i)
                return {"message": f"Hardware {hardware_id} deleted"}
        raise HTTPException(status_code=404, detail=f"Hardware not found: {hardware_id}")

    try:
        custom = get_custom_objects_api()
        custom.delete_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="hardware",
            name=hardware_id
        )
        return {"message": f"Hardware {hardware_id} deleted"}
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Hardware not found: {hardware_id}")
        raise HTTPException(status_code=500, detail=f"Failed to delete hardware: {e.reason}")


# ============================================
# 디스크 스왑 API
# ============================================

@router.post("/hardware/{hardware_id}/swap-disk")
async def swap_disk(hardware_id: str, request: DiskSwapRequest):
    """
    디스크 스왑 - 대여용/소유자용 디스크 전환

    동작 순서:
    1. BMC를 통해 서버 전원 OFF
    2. 부트 순서 변경 (대상 디스크로)
    3. 서버 전원 ON
    """
    _check_tinkerbell_available()

    if _demo_mode:
        for hw in DEMO_HARDWARE:
            if hw.id == hardware_id:
                if hw.status == HardwareStatus.RENTED and not request.force:
                    raise HTTPException(status_code=400, detail="대여 중에는 디스크 스왑이 불가합니다.")

                # 디스크 스왑 시뮬레이션
                for disk in hw.disks:
                    if disk.disk_type == request.target_disk:
                        disk.is_active = True
                        hw.active_disk = disk.device
                    else:
                        disk.is_active = False

                # 상태 변경
                if request.target_disk == DiskType.OWNER:
                    hw.status = HardwareStatus.OWNER_USE
                else:
                    hw.status = HardwareStatus.AVAILABLE

                return {
                    "message": f"디스크 스왑 완료: {request.target_disk.value}",
                    "hardware_id": hardware_id,
                    "active_disk": hw.active_disk,
                    "status": hw.status.value
                }
        raise HTTPException(status_code=404, detail=f"Hardware not found: {hardware_id}")

    # 실제 구현: BMC를 통한 디스크 스왑 워크플로우 실행
    # TODO: Rufio BMC 컨트롤러를 통한 실제 디스크 스왑 구현
    raise HTTPException(status_code=501, detail="실제 디스크 스왑은 Rufio BMC 컨트롤러 필요")


# ============================================
# OS 템플릿 API
# ============================================

@router.get("/templates", response_model=List[OSTemplate])
async def list_templates(for_rental: Optional[bool] = Query(None, description="대여용 필터")):
    """OS 설치 템플릿 목록 조회"""
    _check_tinkerbell_available()

    if _demo_mode:
        result = DEMO_TEMPLATES.copy()
        if for_rental is not None:
            result = [t for t in result if t.for_rental == for_rental]
        return result

    try:
        custom = get_custom_objects_api()
        template_list = custom.list_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="templates"
        )

        result = []
        for item in template_list.get("items", []):
            tpl = _parse_tinkerbell_template(item)
            if for_rental is not None and tpl.for_rental != for_rental:
                continue
            result.append(tpl)

        return result
    except ApiException as e:
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {e.reason}")


@router.get("/templates/{template_id}", response_model=OSTemplate)
async def get_template(template_id: str):
    """특정 템플릿 상세 정보 조회"""
    if _demo_mode:
        for tpl in DEMO_TEMPLATES:
            if tpl.id == template_id:
                return tpl
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

    try:
        custom = get_custom_objects_api()
        item = custom.get_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="templates",
            name=template_id
        )
        return _parse_tinkerbell_template(item)
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get template: {e.reason}")


# ============================================
# 워크플로우 API
# ============================================

@router.get("/workflows", response_model=List[ProvisioningWorkflow])
async def list_workflows(
    hardware_id: Optional[str] = Query(None, description="하드웨어 ID 필터"),
    status: Optional[WorkflowStatus] = Query(None, description="상태 필터")
):
    """프로비저닝 워크플로우 목록 조회"""
    _check_tinkerbell_available()

    if _demo_mode:
        # 데모 워크플로우 데이터
        return []

    try:
        custom = get_custom_objects_api()
        workflow_list = custom.list_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="workflows"
        )

        result = []
        for item in workflow_list.get("items", []):
            wf = _parse_tinkerbell_workflow(item)
            if hardware_id and wf.hardware_id != hardware_id:
                continue
            if status and wf.status != status:
                continue
            result.append(wf)

        return result
    except ApiException as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {e.reason}")


@router.get("/workflows/{workflow_id}", response_model=ProvisioningWorkflow)
async def get_workflow(workflow_id: str):
    """특정 워크플로우 상세 정보 조회"""
    if _demo_mode:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")

    try:
        custom = get_custom_objects_api()
        item = custom.get_namespaced_custom_object(
            group=TINKERBELL_GROUP,
            version=TINKERBELL_VERSION,
            namespace=TINKERBELL_NAMESPACE,
            plural="workflows",
            name=workflow_id
        )
        return _parse_tinkerbell_workflow(item)
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {e.reason}")


# ============================================
# 상태 API
# ============================================

@router.get("/status")
async def get_tinkerbell_status():
    """Tinkerbell 서비스 상태 조회"""
    _check_tinkerbell_available()

    return {
        "demo_mode": _demo_mode,
        "tinkerbell_available": not _demo_mode,
        "hardware_count": len(DEMO_HARDWARE) if _demo_mode else 0,
        "template_count": len(DEMO_TEMPLATES) if _demo_mode else 0,
        "message": "Tinkerbell CRD 미설치 - 데모 모드" if _demo_mode else "Tinkerbell 정상 작동 중"
    }


# ============================================
# Helper Functions
# ============================================

def _parse_tinkerbell_hardware(item: dict) -> Hardware:
    """Tinkerbell Hardware CRD를 Hardware 모델로 변환"""
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    labels = metadata.get("labels", {})
    annotations = metadata.get("annotations", {})

    # BMC 정보
    bmc_ref = spec.get("bmcRef", {})
    bmc = BMCInfo(
        ip=bmc_ref.get("host", ""),
        username=bmc_ref.get("username", "admin"),
        password="***",
        vendor=labels.get("baremetal.k3s.io/bmc-vendor", "unknown")
    )

    # 디스크 정보
    disks = []
    rental_disk = annotations.get("baremetal.k3s.io/rental-disk", "/dev/sda")
    owner_disk = annotations.get("baremetal.k3s.io/owner-disk", "/dev/sdb")
    for disk_spec in spec.get("disks", []):
        device = disk_spec.get("device", "")
        disk_type = DiskType.RENTAL if device == rental_disk else DiskType.OWNER
        disks.append(DiskInfo(
            device=device,
            size_gb=disk_spec.get("sizeGb", 0),
            disk_type=disk_type,
            is_active=False
        ))

    # 네트워크 인터페이스
    interfaces = []
    for iface in spec.get("interfaces", []):
        dhcp = iface.get("dhcp", {})
        ip_info = dhcp.get("ip", {})
        interfaces.append(NetworkInterface(
            mac=dhcp.get("mac", ""),
            ip=ip_info.get("address"),
            gateway=ip_info.get("gateway"),
            is_management=iface.get("netboot", {}).get("allowWorkflow", False)
        ))

    # 상태
    state = spec.get("metadata", {}).get("state", "available")
    status_map = {
        "available": HardwareStatus.AVAILABLE,
        "rented": HardwareStatus.RENTED,
        "provisioning": HardwareStatus.PROVISIONING,
        "maintenance": HardwareStatus.MAINTENANCE,
        "owner_use": HardwareStatus.OWNER_USE,
    }
    status = status_map.get(state, HardwareStatus.AVAILABLE)

    return Hardware(
        id=metadata.get("name", ""),
        name=metadata.get("name", ""),
        status=status,
        bmc=bmc,
        spec=HardwareSpec(
            cpu_cores=int(labels.get("baremetal.k3s.io/cpu-cores", 0)),
            cpu_model=labels.get("baremetal.k3s.io/cpu-model", ""),
            memory_gb=int(labels.get("baremetal.k3s.io/memory-gb", 0)),
            gpu_count=int(labels.get("baremetal.k3s.io/gpu-count", 0)),
            gpu_model=labels.get("baremetal.k3s.io/gpu-model", ""),
        ),
        disks=disks,
        interfaces=interfaces,
        owner_id=labels.get("baremetal.k3s.io/owner-id"),
        owner_name=labels.get("baremetal.k3s.io/owner-name"),
        current_rental_id=annotations.get("baremetal.k3s.io/current-rental-id"),
        labels={k: v for k, v in labels.items() if not k.startswith("baremetal.k3s.io/")},
        created_at=metadata.get("creationTimestamp")
    )


def _parse_tinkerbell_template(item: dict) -> OSTemplate:
    """Tinkerbell Template CRD를 OSTemplate 모델로 변환"""
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    labels = metadata.get("labels", {})
    annotations = metadata.get("annotations", {})

    return OSTemplate(
        id=metadata.get("name", ""),
        name=annotations.get("baremetal.k3s.io/display-name", metadata.get("name", "")),
        os_name=labels.get("baremetal.k3s.io/os-name", ""),
        os_version=labels.get("baremetal.k3s.io/os-version", ""),
        description=annotations.get("description", ""),
        image_url=annotations.get("baremetal.k3s.io/image-url", ""),
        for_rental=labels.get("baremetal.k3s.io/for-rental", "true") == "true",
        actions=spec.get("actions", []),
        created_at=metadata.get("creationTimestamp")
    )


def _parse_tinkerbell_workflow(item: dict) -> ProvisioningWorkflow:
    """Tinkerbell Workflow CRD를 ProvisioningWorkflow 모델로 변환"""
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    status = item.get("status", {})

    state = status.get("state", "pending")
    status_map = {
        "pending": WorkflowStatus.PENDING,
        "running": WorkflowStatus.RUNNING,
        "success": WorkflowStatus.SUCCESS,
        "failed": WorkflowStatus.FAILED,
        "timeout": WorkflowStatus.TIMEOUT,
    }

    return ProvisioningWorkflow(
        id=metadata.get("name", ""),
        hardware_id=spec.get("hardwareRef", {}).get("name", ""),
        template_id=spec.get("templateRef", {}).get("name", ""),
        status=status_map.get(state, WorkflowStatus.PENDING),
        current_action=status.get("currentAction", ""),
        progress_percent=int(status.get("progress", 0)),
        started_at=status.get("startedAt"),
        completed_at=status.get("completedAt"),
        logs=status.get("logs", []),
        error_message=status.get("errorMessage", "")
    )
