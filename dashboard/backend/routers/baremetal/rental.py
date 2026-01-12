"""
베어메탈 렌탈 API Router

대여 세션 관리:
- 대여 요청/승인
- 대여 연장
- 대여 종료 및 정리
- 디스크 자동 스왑
"""
import logging
import secrets
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from kubernetes.client.rest import ApiException

from utils.k8s_client import get_k8s_clients, get_custom_objects_api
from utils.config import BAREMETAL_DEFAULT_RENTAL_HOURS, BAREMETAL_MAX_RENTAL_HOURS
from models.baremetal import (
    RentalSession, RentalStatus, RentalRequest, RentalExtendRequest,
    HardwareStatus, DiskType
)
from .tinkerbell import DEMO_HARDWARE, _check_tinkerbell_available, _demo_mode

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/baremetal/rentals", tags=["baremetal-rentals"])

# 데모 렌탈 데이터
DEMO_RENTALS: List[RentalSession] = [
    RentalSession(
        id="rental-001",
        hardware_id="hw-002",
        hardware_name="gpu-server-02",
        renter_id="renter-001",
        renter_name="이영희",
        renter_email="lee@example.com",
        template_id="tpl-ubuntu-2404-cuda",
        os_name="Ubuntu 24.04 + CUDA 12.4",
        ssh_ip="10.0.0.102",
        ssh_port=22,
        ssh_user="rental",
        ssh_password="temp-pass-abc123",
        rental_hours=48,
        started_at=datetime.now() - timedelta(hours=12),
        expires_at=datetime.now() + timedelta(hours=36),
        status=RentalStatus.ACTIVE,
        workflow_id="wf-001",
        created_at=datetime.now() - timedelta(hours=12),
        notes="ML 모델 학습용"
    )
]


# ============================================
# 렌탈 세션 API
# ============================================

@router.get("", response_model=List[RentalSession])
async def list_rentals(
    status: Optional[RentalStatus] = Query(None, description="상태 필터"),
    hardware_id: Optional[str] = Query(None, description="하드웨어 ID 필터"),
    renter_id: Optional[str] = Query(None, description="대여자 ID 필터"),
    include_completed: bool = Query(False, description="완료된 대여 포함")
):
    """대여 세션 목록 조회"""
    result = DEMO_RENTALS.copy()

    if status:
        result = [r for r in result if r.status == status]
    if hardware_id:
        result = [r for r in result if r.hardware_id == hardware_id]
    if renter_id:
        result = [r for r in result if r.renter_id == renter_id]
    if not include_completed:
        result = [r for r in result if r.status != RentalStatus.COMPLETED]

    return result


@router.get("/{rental_id}", response_model=RentalSession)
async def get_rental(rental_id: str):
    """특정 대여 세션 상세 정보 조회"""
    for rental in DEMO_RENTALS:
        if rental.id == rental_id:
            return rental
    raise HTTPException(status_code=404, detail=f"Rental not found: {rental_id}")


@router.post("", response_model=RentalSession)
async def create_rental(request: RentalRequest, background_tasks: BackgroundTasks):
    """
    새 대여 요청 생성

    프로세스:
    1. 하드웨어 가용성 확인
    2. 대여용 디스크로 스왑 (필요시)
    3. OS 프로비저닝 워크플로우 시작
    4. SSH 접속 정보 생성
    """
    _check_tinkerbell_available()

    # 하드웨어 확인
    hw = None
    for h in DEMO_HARDWARE:
        if h.id == request.hardware_id:
            hw = h
            break

    if not hw:
        raise HTTPException(status_code=404, detail=f"Hardware not found: {request.hardware_id}")

    if hw.status not in [HardwareStatus.AVAILABLE, HardwareStatus.OWNER_USE]:
        raise HTTPException(
            status_code=400,
            detail=f"하드웨어가 대여 가능한 상태가 아닙니다. 현재 상태: {hw.status.value}"
        )

    # 대여 시간 검증
    rental_hours = min(request.rental_hours, BAREMETAL_MAX_RENTAL_HOURS)

    # 임시 SSH 비밀번호 생성
    temp_password = secrets.token_urlsafe(12)

    # SSH IP 가져오기
    ssh_ip = ""
    for iface in hw.interfaces:
        if iface.ip:
            ssh_ip = iface.ip
            break

    # 새 대여 세션 생성
    now = datetime.now()
    rental = RentalSession(
        id=f"rental-{secrets.token_hex(4)}",
        hardware_id=hw.id,
        hardware_name=hw.name,
        renter_id=f"renter-{secrets.token_hex(4)}",
        renter_name=request.renter_name,
        renter_email=request.renter_email,
        template_id=request.template_id,
        os_name="",  # 프로비저닝 후 업데이트
        ssh_ip=ssh_ip,
        ssh_port=22,
        ssh_user="rental",
        ssh_password=temp_password,
        rental_hours=rental_hours,
        started_at=now,
        expires_at=now + timedelta(hours=rental_hours),
        status=RentalStatus.PROVISIONING,
        workflow_id=f"wf-{secrets.token_hex(4)}",
        created_at=now,
        notes=request.notes
    )

    # 하드웨어 상태 업데이트
    hw.status = HardwareStatus.PROVISIONING
    hw.current_rental_id = rental.id

    # 데모 데이터에 추가
    DEMO_RENTALS.append(rental)

    # 백그라운드에서 프로비저닝 시뮬레이션
    background_tasks.add_task(_simulate_provisioning, rental.id)

    return rental


@router.post("/{rental_id}/extend", response_model=RentalSession)
async def extend_rental(rental_id: str, request: RentalExtendRequest):
    """대여 기간 연장"""
    for rental in DEMO_RENTALS:
        if rental.id == rental_id:
            if rental.status != RentalStatus.ACTIVE:
                raise HTTPException(status_code=400, detail="활성 대여만 연장할 수 있습니다.")

            # 최대 대여 시간 확인
            total_hours = rental.rental_hours + request.additional_hours
            if total_hours > BAREMETAL_MAX_RENTAL_HOURS:
                raise HTTPException(
                    status_code=400,
                    detail=f"최대 대여 시간({BAREMETAL_MAX_RENTAL_HOURS}시간)을 초과합니다."
                )

            # 연장
            rental.rental_hours = total_hours
            rental.expires_at = rental.started_at + timedelta(hours=total_hours)

            return rental

    raise HTTPException(status_code=404, detail=f"Rental not found: {rental_id}")


@router.post("/{rental_id}/terminate", response_model=RentalSession)
async def terminate_rental(rental_id: str, background_tasks: BackgroundTasks):
    """
    대여 종료 및 정리

    프로세스:
    1. 서버 전원 OFF
    2. 대여용 디스크 완전 삭제 (wipefs)
    3. 소유자 디스크로 스왑 (선택적)
    """
    for rental in DEMO_RENTALS:
        if rental.id == rental_id:
            if rental.status in [RentalStatus.COMPLETED, RentalStatus.CLEANING]:
                raise HTTPException(status_code=400, detail="이미 종료되었거나 정리 중입니다.")

            # 정리 시작
            rental.status = RentalStatus.CLEANING
            rental.cleanup_workflow_id = f"cleanup-{secrets.token_hex(4)}"

            # 백그라운드에서 정리 시뮬레이션
            background_tasks.add_task(_simulate_cleanup, rental_id)

            return rental

    raise HTTPException(status_code=404, detail=f"Rental not found: {rental_id}")


@router.get("/expiring-soon", response_model=List[RentalSession])
async def get_expiring_rentals(hours: int = Query(1, ge=1, le=24, description="만료까지 남은 시간")):
    """곧 만료되는 대여 목록 조회"""
    now = datetime.now()
    threshold = now + timedelta(hours=hours)

    result = []
    for rental in DEMO_RENTALS:
        if rental.status == RentalStatus.ACTIVE and rental.expires_at:
            if rental.expires_at <= threshold:
                result.append(rental)

    return result


# ============================================
# 통계 API
# ============================================

@router.get("/stats/summary")
async def get_rental_stats():
    """대여 통계 요약"""
    total = len(DEMO_RENTALS)
    active = len([r for r in DEMO_RENTALS if r.status == RentalStatus.ACTIVE])
    provisioning = len([r for r in DEMO_RENTALS if r.status == RentalStatus.PROVISIONING])
    completed = len([r for r in DEMO_RENTALS if r.status == RentalStatus.COMPLETED])

    # 대여 가능한 하드웨어 수
    available_hw = len([h for h in DEMO_HARDWARE if h.status == HardwareStatus.AVAILABLE])
    total_hw = len(DEMO_HARDWARE)

    return {
        "rentals": {
            "total": total,
            "active": active,
            "provisioning": provisioning,
            "completed": completed,
        },
        "hardware": {
            "total": total_hw,
            "available": available_hw,
            "rented": len([h for h in DEMO_HARDWARE if h.status == HardwareStatus.RENTED]),
            "owner_use": len([h for h in DEMO_HARDWARE if h.status == HardwareStatus.OWNER_USE]),
        }
    }


# ============================================
# Helper Functions
# ============================================

async def _simulate_provisioning(rental_id: str):
    """프로비저닝 시뮬레이션 (데모용)"""
    import asyncio

    # 잠시 대기 후 상태 변경
    await asyncio.sleep(3)

    for rental in DEMO_RENTALS:
        if rental.id == rental_id:
            rental.status = RentalStatus.ACTIVE
            rental.os_name = "Ubuntu 24.04 + CUDA 12.4"

            # 하드웨어 상태 업데이트
            for hw in DEMO_HARDWARE:
                if hw.id == rental.hardware_id:
                    hw.status = HardwareStatus.RENTED
                    # 대여용 디스크 활성화
                    for disk in hw.disks:
                        disk.is_active = (disk.disk_type == DiskType.RENTAL)
                        if disk.is_active:
                            hw.active_disk = disk.device
                    break
            break


async def _simulate_cleanup(rental_id: str):
    """정리 시뮬레이션 (데모용)"""
    import asyncio

    # 잠시 대기 후 상태 변경
    await asyncio.sleep(5)

    for rental in DEMO_RENTALS:
        if rental.id == rental_id:
            rental.status = RentalStatus.COMPLETED

            # 하드웨어 상태 업데이트
            for hw in DEMO_HARDWARE:
                if hw.id == rental.hardware_id:
                    hw.status = HardwareStatus.AVAILABLE
                    hw.current_rental_id = None
                    # 대여용 디스크 비활성화 (초기화 완료)
                    for disk in hw.disks:
                        if disk.disk_type == DiskType.RENTAL:
                            disk.is_active = True
                            hw.active_disk = disk.device
                    break
            break


async def check_expired_rentals():
    """만료된 대여 확인 및 자동 정리 (스케줄러에서 호출)"""
    now = datetime.now()

    for rental in DEMO_RENTALS:
        if rental.status == RentalStatus.ACTIVE and rental.expires_at:
            if rental.expires_at <= now:
                rental.status = RentalStatus.EXPIRED
                logger.warning(f"Rental {rental.id} has expired")

                # TODO: 자동 정리 워크플로우 시작
