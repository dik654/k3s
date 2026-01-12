#!/bin/bash
#===============================================================================
# K3s Worker 노드 추가 스크립트
#
# 사용법:
#   새 서버에서 실행:
#   curl -sfL http://<마스터IP>:8080/02-add-worker.sh | sudo bash -s -- <옵션>
#
#   또는 직접 실행:
#   sudo ./02-add-worker.sh --master-ip <IP> --token <TOKEN> --type <TYPE>
#
# 노드 타입:
#   cpu      - CPU 연산용 노드
#   gpu      - GPU 연산용 노드 (NVIDIA)
#   storage  - 스토리지 전용 노드
#   general  - 범용 노드
#===============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 기본값
MASTER_IP=""
TOKEN=""
NODE_TYPE="general"
NODE_NAME=""
K3S_VERSION="v1.31.4+k3s1"

# 도움말
show_help() {
    echo "K3s Worker 노드 추가 스크립트"
    echo ""
    echo "사용법: sudo $0 [옵션]"
    echo ""
    echo "필수 옵션:"
    echo "  --master-ip <IP>     마스터 노드 IP 주소"
    echo "  --token <TOKEN>      노드 조인 토큰"
    echo ""
    echo "선택 옵션:"
    echo "  --type <TYPE>        노드 타입 (cpu|gpu|storage|general) [기본: general]"
    echo "  --name <NAME>        노드 이름 [기본: 호스트명]"
    echo "  --gpu-type <TYPE>    GPU 타입 (예: rtx3090, rtx4090, a100)"
    echo "  --gpu-count <N>      GPU 개수"
    echo "  -h, --help           도움말"
    echo ""
    echo "예시:"
    echo "  sudo $0 --master-ip 14.32.100.220 --token K10xxx... --type gpu --gpu-type rtx4090 --gpu-count 2"
    echo "  sudo $0 --master-ip 14.32.100.220 --token K10xxx... --type storage"
    echo ""
}

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --master-ip)
            MASTER_IP="$2"
            shift 2
            ;;
        --token)
            TOKEN="$2"
            shift 2
            ;;
        --type)
            NODE_TYPE="$2"
            shift 2
            ;;
        --name)
            NODE_NAME="$2"
            shift 2
            ;;
        --gpu-type)
            GPU_TYPE="$2"
            shift 2
            ;;
        --gpu-count)
            GPU_COUNT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "알 수 없는 옵션: $1"
            show_help
            exit 1
            ;;
    esac
done

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한이 필요합니다: sudo $0"
    exit 1
fi

# 필수 인자 확인
if [ -z "$MASTER_IP" ] || [ -z "$TOKEN" ]; then
    log_error "마스터 IP와 토큰은 필수입니다!"
    echo ""
    show_help
    exit 1
fi

# 노드 이름 설정
if [ -z "$NODE_NAME" ]; then
    NODE_NAME=$(hostname)
fi

NODE_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=============================================="
echo "       K3s Worker 노드 추가"
echo "=============================================="
echo ""
echo "  마스터 IP: ${MASTER_IP}"
echo "  노드 IP: ${NODE_IP}"
echo "  노드 이름: ${NODE_NAME}"
echo "  노드 타입: ${NODE_TYPE}"
echo "  K3s 버전: ${K3S_VERSION}"
echo ""
echo "=============================================="
echo ""

read -p "설치를 진행하시겠습니까? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    log_warn "설치가 취소되었습니다."
    exit 0
fi

#-----------------------------------------------
# 1. 시스템 사전 준비
#-----------------------------------------------
log_info "시스템 사전 준비 중..."

# 필수 패키지 설치
apt-get update -qq
apt-get install -y -qq curl wget apt-transport-https ca-certificates

# 스왑 비활성화
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

# 커널 모듈
cat > /etc/modules-load.d/k3s.conf << EOF
br_netfilter
overlay
EOF

modprobe br_netfilter
modprobe overlay

# sysctl 설정
cat > /etc/sysctl.d/k3s.conf << EOF
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sysctl --system > /dev/null 2>&1

log_success "시스템 준비 완료"

#-----------------------------------------------
# 2. GPU 노드인 경우 NVIDIA 드라이버 확인
#-----------------------------------------------
if [ "$NODE_TYPE" = "gpu" ]; then
    log_info "GPU 환경 확인 중..."

    if ! command -v nvidia-smi &> /dev/null; then
        log_warn "NVIDIA 드라이버가 설치되어 있지 않습니다."
        log_warn "K3s 설치 후 NVIDIA Container Toolkit을 설정해야 합니다."
    else
        log_success "NVIDIA 드라이버 감지됨"
        nvidia-smi --query-gpu=name --format=csv,noheader

        # GPU 정보 자동 감지
        if [ -z "$GPU_TYPE" ]; then
            GPU_TYPE=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g')
        fi
        if [ -z "$GPU_COUNT" ]; then
            GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
        fi
        log_info "GPU 타입: ${GPU_TYPE}, 개수: ${GPU_COUNT}"
    fi
fi

#-----------------------------------------------
# 3. K3s Agent 설치
#-----------------------------------------------
log_info "K3s Agent 설치 중..."

# 노드 라벨 준비
NODE_LABELS="node-type=${NODE_TYPE}"

case $NODE_TYPE in
    gpu)
        NODE_LABELS="${NODE_LABELS},gpu=true"
        [ -n "$GPU_TYPE" ] && NODE_LABELS="${NODE_LABELS},gpu-type=${GPU_TYPE}"
        [ -n "$GPU_COUNT" ] && NODE_LABELS="${NODE_LABELS},gpu-count=${GPU_COUNT}"
        ;;
    storage)
        NODE_LABELS="${NODE_LABELS},storage=true"
        ;;
    cpu)
        NODE_LABELS="${NODE_LABELS},cpu-optimized=true"
        ;;
esac

# K3s Agent 설치
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="${K3S_VERSION}" \
    K3S_URL="https://${MASTER_IP}:6443" \
    K3S_TOKEN="${TOKEN}" \
    sh -s - agent \
    --node-name "${NODE_NAME}" \
    --node-ip "${NODE_IP}" \
    --node-label "${NODE_LABELS}"

log_success "K3s Agent 설치 완료"

#-----------------------------------------------
# 4. GPU 노드: NVIDIA Container Toolkit 설정
#-----------------------------------------------
if [ "$NODE_TYPE" = "gpu" ] && command -v nvidia-smi &> /dev/null; then
    log_info "NVIDIA Container Toolkit 설정 중..."

    # NVIDIA Container Toolkit 설치 (이미 설치되어 있지 않은 경우)
    if ! command -v nvidia-ctk &> /dev/null; then
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
        apt-get update -qq
        apt-get install -y -qq nvidia-container-toolkit
    fi

    # containerd 기본 설정
    nvidia-ctk runtime configure --runtime=containerd --set-as-default

    # K3s Agent용 containerd 설정 (필수!)
    log_info "K3s containerd GPU 런타임 설정 중..."
    mkdir -p /var/lib/rancher/k3s/agent/etc/containerd

    cat > /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl << 'CONTAINERD_EOF'
version = 2

[plugins."io.containerd.grpc.v1.cri".containerd]
  default_runtime_name = "nvidia"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  privileged_without_host_devices = false
  runtime_engine = ""
  runtime_root = ""
  runtime_type = "io.containerd.runc.v2"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
  BinaryName = "/usr/bin/nvidia-container-runtime"
  SystemdCgroup = true
CONTAINERD_EOF

    # K3s Agent 재시작
    log_info "K3s Agent 재시작 중..."
    systemctl restart k3s-agent
    sleep 10

    if systemctl is-active --quiet k3s-agent; then
        log_success "K3s Agent 재시작 완료"
    else
        log_error "K3s Agent 시작 실패"
        journalctl -u k3s-agent -n 20
    fi

    log_success "NVIDIA Container Toolkit 및 K3s GPU 런타임 설정 완료"
fi

#-----------------------------------------------
# 5. 설치 확인
#-----------------------------------------------
echo ""
echo "=============================================="
echo "       Worker 노드 추가 완료!"
echo "=============================================="
echo ""
echo "노드 이름: ${NODE_NAME}"
echo "노드 타입: ${NODE_TYPE}"
echo "노드 라벨: ${NODE_LABELS}"
echo ""
echo "마스터에서 확인: kubectl get nodes"
echo ""
log_success "K3s Worker 노드가 클러스터에 추가되었습니다!"
