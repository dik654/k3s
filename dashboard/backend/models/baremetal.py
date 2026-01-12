"""
베어메탈 프로비저닝 및 렌탈 모델

Tinkerbell CRD 기반:
- Hardware: 베어메탈 서버 정보
- Template: OS 설치 템플릿
- Workflow: 프로비저닝 워크플로우

렌탈 관리:
- RentalSession: 대여 세션 정보
- DiskSwapPolicy: 디스크 스왑 정책
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class DiskType(str, Enum):
    """디스크 타입"""
    RENTAL = "rental"  # 대여용 (OS만 설치된 빈 디스크)
    OWNER = "owner"  # 소유자용 (데이터 포함)


class HardwareStatus(str, Enum):
    """하드웨어 상태"""
    AVAILABLE = "available"  # 대여 가능
    RENTED = "rented"  # 대여 중
    PROVISIONING = "provisioning"  # OS 설치 중
    MAINTENANCE = "maintenance"  # 유지보수 중
    OWNER_USE = "owner_use"  # 소유자 사용 중


class BMCInfo(BaseModel):
    """BMC (Baseboard Management Controller) 정보"""
    ip: str = Field(..., description="BMC IP 주소")
    username: str = Field(default="admin", description="BMC 사용자명")
    password: str = Field(default="", description="BMC 비밀번호 (암호화)")
    vendor: str = Field(default="unknown", description="BMC 벤더 (ipmi, redfish, dell-idrac, hp-ilo)")


class DiskInfo(BaseModel):
    """디스크 정보"""
    device: str = Field(..., description="디스크 디바이스 경로 (e.g., /dev/sda)")
    size_gb: int = Field(..., description="디스크 크기 (GB)")
    disk_type: DiskType = Field(..., description="디스크 타입 (rental/owner)")
    label: str = Field(default="", description="디스크 라벨")
    is_active: bool = Field(default=False, description="현재 활성화된 디스크 여부")


class NetworkInterface(BaseModel):
    """네트워크 인터페이스 정보"""
    mac: str = Field(..., description="MAC 주소")
    ip: Optional[str] = Field(None, description="할당된 IP 주소")
    gateway: Optional[str] = Field(None, description="게이트웨이")
    netmask: Optional[str] = Field(default="255.255.255.0", description="넷마스크")
    is_management: bool = Field(default=False, description="관리 인터페이스 여부")


class HardwareSpec(BaseModel):
    """하드웨어 스펙"""
    cpu_cores: int = Field(default=0, description="CPU 코어 수")
    cpu_model: str = Field(default="", description="CPU 모델")
    memory_gb: int = Field(default=0, description="메모리 크기 (GB)")
    gpu_count: int = Field(default=0, description="GPU 개수")
    gpu_model: str = Field(default="", description="GPU 모델")


class Hardware(BaseModel):
    """베어메탈 하드웨어 정보 (Tinkerbell Hardware CRD 기반)"""
    id: str = Field(..., description="하드웨어 ID")
    name: str = Field(..., description="하드웨어 이름")
    status: HardwareStatus = Field(default=HardwareStatus.AVAILABLE, description="현재 상태")

    # BMC 정보
    bmc: BMCInfo = Field(..., description="BMC 정보")

    # 하드웨어 스펙
    spec: HardwareSpec = Field(default_factory=HardwareSpec, description="하드웨어 스펙")

    # 디스크 정보
    disks: List[DiskInfo] = Field(default_factory=list, description="디스크 목록")
    active_disk: Optional[str] = Field(None, description="현재 활성 디스크 디바이스")

    # 네트워크 정보
    interfaces: List[NetworkInterface] = Field(default_factory=list, description="네트워크 인터페이스 목록")

    # 소유자 정보
    owner_id: Optional[str] = Field(None, description="소유자 ID")
    owner_name: Optional[str] = Field(None, description="소유자 이름")

    # 현재 렌탈 정보
    current_rental_id: Optional[str] = Field(None, description="현재 대여 세션 ID")

    # 메타데이터
    labels: Dict[str, str] = Field(default_factory=dict, description="레이블")
    annotations: Dict[str, str] = Field(default_factory=dict, description="어노테이션")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OSTemplate(BaseModel):
    """OS 설치 템플릿 (Tinkerbell Template CRD 기반)"""
    id: str = Field(..., description="템플릿 ID")
    name: str = Field(..., description="템플릿 이름")
    os_name: str = Field(..., description="OS 이름 (e.g., Ubuntu, Rocky Linux)")
    os_version: str = Field(..., description="OS 버전 (e.g., 22.04, 9.3)")
    description: str = Field(default="", description="설명")

    # 이미지 정보
    image_url: str = Field(..., description="OS 이미지 URL")
    image_checksum: str = Field(default="", description="이미지 체크섬")

    # 설치 옵션
    disk_device: str = Field(default="/dev/sda", description="설치할 디스크 디바이스")
    partition_scheme: str = Field(default="gpt", description="파티션 스키마")
    filesystem: str = Field(default="ext4", description="파일시스템")

    # 포스트 설치 스크립트
    post_install_script: str = Field(default="", description="설치 후 실행 스크립트")

    # Tinkerbell 워크플로우 액션
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Tinkerbell 워크플로우 액션")

    # 메타데이터
    for_rental: bool = Field(default=True, description="대여용 템플릿 여부")
    created_at: Optional[datetime] = None


class WorkflowStatus(str, Enum):
    """워크플로우 상태"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ProvisioningWorkflow(BaseModel):
    """프로비저닝 워크플로우 (Tinkerbell Workflow CRD 기반)"""
    id: str = Field(..., description="워크플로우 ID")
    hardware_id: str = Field(..., description="대상 하드웨어 ID")
    template_id: str = Field(..., description="사용 템플릿 ID")

    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="워크플로우 상태")
    current_action: str = Field(default="", description="현재 실행 중인 액션")
    progress_percent: int = Field(default=0, description="진행률 (%)")

    # 시간 정보
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 로그
    logs: List[str] = Field(default_factory=list, description="워크플로우 로그")
    error_message: str = Field(default="", description="에러 메시지")


class RentalStatus(str, Enum):
    """렌탈 세션 상태"""
    REQUESTED = "requested"  # 대여 요청됨
    PROVISIONING = "provisioning"  # OS 설치 중
    ACTIVE = "active"  # 대여 활성화
    EXPIRING_SOON = "expiring_soon"  # 곧 만료 (1시간 전)
    EXPIRED = "expired"  # 만료됨
    CLEANING = "cleaning"  # 정리 중 (디스크 스왑)
    COMPLETED = "completed"  # 완료


class RentalSession(BaseModel):
    """베어메탈 대여 세션"""
    id: str = Field(..., description="대여 세션 ID")
    hardware_id: str = Field(..., description="대상 하드웨어 ID")
    hardware_name: str = Field(default="", description="하드웨어 이름")

    # 대여자 정보
    renter_id: str = Field(..., description="대여자 ID")
    renter_name: str = Field(default="", description="대여자 이름")
    renter_email: str = Field(default="", description="대여자 이메일")

    # OS 정보
    template_id: str = Field(..., description="사용 OS 템플릿 ID")
    os_name: str = Field(default="", description="설치된 OS")

    # 접속 정보
    ssh_ip: str = Field(default="", description="SSH 접속 IP")
    ssh_port: int = Field(default=22, description="SSH 포트")
    ssh_user: str = Field(default="rental", description="SSH 사용자")
    ssh_password: str = Field(default="", description="임시 SSH 비밀번호")

    # 대여 시간
    rental_hours: int = Field(..., description="대여 시간 (시간)")
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # 상태
    status: RentalStatus = Field(default=RentalStatus.REQUESTED, description="대여 상태")
    workflow_id: Optional[str] = Field(None, description="프로비저닝 워크플로우 ID")
    cleanup_workflow_id: Optional[str] = Field(None, description="정리 워크플로우 ID")

    # 메타데이터
    created_at: Optional[datetime] = None
    notes: str = Field(default="", description="메모")


class DiskSwapRequest(BaseModel):
    """디스크 스왑 요청"""
    hardware_id: str = Field(..., description="하드웨어 ID")
    target_disk: DiskType = Field(..., description="전환할 디스크 타입")
    force: bool = Field(default=False, description="강제 스왑 여부")


class RentalRequest(BaseModel):
    """대여 요청"""
    hardware_id: str = Field(..., description="대여할 하드웨어 ID")
    template_id: str = Field(..., description="설치할 OS 템플릿 ID")
    rental_hours: int = Field(default=24, ge=1, le=168, description="대여 시간 (1-168시간)")
    renter_name: str = Field(..., description="대여자 이름")
    renter_email: str = Field(default="", description="대여자 이메일")
    notes: str = Field(default="", description="메모")


class RentalExtendRequest(BaseModel):
    """대여 연장 요청"""
    additional_hours: int = Field(..., ge=1, le=168, description="추가 대여 시간")


class HardwareRegistration(BaseModel):
    """하드웨어 등록 요청"""
    name: str = Field(..., description="하드웨어 이름")

    # BMC 정보
    bmc_ip: str = Field(..., description="BMC IP 주소")
    bmc_username: str = Field(default="admin", description="BMC 사용자명")
    bmc_password: str = Field(..., description="BMC 비밀번호")
    bmc_vendor: str = Field(default="ipmi", description="BMC 벤더")

    # 네트워크 인터페이스
    mac_address: str = Field(..., description="메인 MAC 주소")
    ip_address: Optional[str] = Field(None, description="할당할 IP 주소")
    gateway: Optional[str] = Field(None, description="게이트웨이")

    # 디스크 정보
    rental_disk: str = Field(default="/dev/sda", description="대여용 디스크 디바이스")
    rental_disk_size_gb: int = Field(default=500, description="대여용 디스크 크기")
    owner_disk: str = Field(default="/dev/sdb", description="소유자 디스크 디바이스")
    owner_disk_size_gb: int = Field(default=1000, description="소유자 디스크 크기")

    # 소유자 정보
    owner_name: str = Field(default="", description="소유자 이름")
    owner_id: Optional[str] = Field(None, description="소유자 ID")

    # 옵션
    labels: Dict[str, str] = Field(default_factory=dict, description="레이블")
