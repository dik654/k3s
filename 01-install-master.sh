#!/bin/bash
#===============================================================================
# K3s 마스터 노드 설치 스크립트
#
# 사용법: ./01-install-master.sh (일반 사용자로 실행, 내부에서 sudo 사용)
#
# 특징:
# - 단일 마스터로 시작 (나중에 HA로 확장 가능)
# - embedded etcd 사용 (HA 확장 대비)
# - NVIDIA GPU 지원 준비
# - Traefik Ingress 포함
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

# 현재 사용자 정보 저장 (sudo 전에)
CURRENT_USER=$(whoami)
CURRENT_HOME=$HOME
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Root로 실행하면 안됨
if [ "$EUID" -eq 0 ]; then
    log_error "일반 사용자로 실행하세요 (sudo 없이): ./01-install-master.sh"
    log_error "스크립트 내부에서 필요한 경우에만 sudo를 사용합니다."
    exit 1
fi

# sudo 권한 확인
if ! sudo -n true 2>/dev/null; then
    log_info "sudo 권한이 필요합니다. 비밀번호를 입력하세요."
    sudo -v
fi

# 설정 변수
MASTER_IP=$(hostname -I | awk '{print $1}')
CLUSTER_CIDR="10.42.0.0/16"
SERVICE_CIDR="10.43.0.0/16"
K3S_VERSION="v1.31.4+k3s1"  # 안정 버전

echo ""
echo "=============================================="
echo "       K3s 마스터 노드 설치"
echo "=============================================="
echo ""
echo "  실행 사용자: ${CURRENT_USER}"
echo "  서버 IP: ${MASTER_IP}"
echo "  K3s 버전: ${K3S_VERSION}"
echo "  Cluster CIDR: ${CLUSTER_CIDR}"
echo "  Service CIDR: ${SERVICE_CIDR}"
echo ""
echo "=============================================="
echo ""

read -p "설치를 진행하시겠습니까? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    log_warn "설치가 취소되었습니다."
    exit 0
fi

#-----------------------------------------------
# 1. 시스템 사전 준비 (sudo 필요)
#-----------------------------------------------
log_info "시스템 사전 준비 중..."

# 필수 패키지 설치
sudo apt-get update -qq
sudo apt-get install -y -qq curl wget apt-transport-https ca-certificates gnupg lsb-release

# 스왑 비활성화 (Kubernetes 권장)
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# 필요한 커널 모듈 로드
sudo tee /etc/modules-load.d/k3s.conf > /dev/null << EOF
br_netfilter
overlay
EOF

sudo modprobe br_netfilter
sudo modprobe overlay

# sysctl 설정
sudo tee /etc/sysctl.d/k3s.conf > /dev/null << EOF
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sudo sysctl --system > /dev/null 2>&1

log_success "시스템 준비 완료"

#-----------------------------------------------
# 2. K3s 마스터 설치 (embedded etcd)
#-----------------------------------------------
log_info "K3s 마스터 설치 중..."

# K3s 설치 (embedded etcd 모드 - HA 확장 대비)
curl -sfL https://get.k3s.io | sudo INSTALL_K3S_VERSION="${K3S_VERSION}" sh -s - server \
    --cluster-init \
    --tls-san "${MASTER_IP}" \
    --tls-san "$(hostname)" \
    --node-ip "${MASTER_IP}" \
    --advertise-address "${MASTER_IP}" \
    --cluster-cidr "${CLUSTER_CIDR}" \
    --service-cidr "${SERVICE_CIDR}" \
    --disable-cloud-controller \
    --write-kubeconfig-mode 644

# 서비스 시작 대기
log_info "K3s 서비스 시작 대기 중..."
sleep 10

# 서비스 상태 확인
if sudo systemctl is-active --quiet k3s; then
    log_success "K3s 서비스 시작됨"
else
    log_error "K3s 서비스 시작 실패"
    sudo journalctl -u k3s -n 50
    exit 1
fi

#-----------------------------------------------
# 3. kubectl 설정 (현재 사용자용)
#-----------------------------------------------
log_info "kubectl 설정 중..."

# 현재 사용자를 위한 kubeconfig 설정
mkdir -p ${CURRENT_HOME}/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ${CURRENT_HOME}/.kube/config
sudo chown ${CURRENT_USER}:${CURRENT_USER} ${CURRENT_HOME}/.kube/config
chmod 600 ${CURRENT_HOME}/.kube/config

# 환경 변수 설정
if ! grep -q "KUBECONFIG" ${CURRENT_HOME}/.bashrc; then
    echo 'export KUBECONFIG=~/.kube/config' >> ${CURRENT_HOME}/.bashrc
fi

# kubectl alias 설정
if ! grep -q "alias k=" ${CURRENT_HOME}/.bashrc; then
    echo 'alias k=kubectl' >> ${CURRENT_HOME}/.bashrc
    echo 'complete -F __start_kubectl k' >> ${CURRENT_HOME}/.bashrc
fi

log_success "kubectl 설정 완료"

#-----------------------------------------------
# 4. 노드 토큰 저장 (현재 사용자 소유)
#-----------------------------------------------
log_info "노드 토큰 저장 중..."

TOKEN_DIR="${SCRIPT_DIR}/tokens"
mkdir -p ${TOKEN_DIR}

# 노드 조인 토큰 저장
sudo cp /var/lib/rancher/k3s/server/node-token ${TOKEN_DIR}/node-token
sudo chown ${CURRENT_USER}:${CURRENT_USER} ${TOKEN_DIR}/node-token
chmod 600 ${TOKEN_DIR}/node-token

# 조인 정보 파일 생성
cat > ${TOKEN_DIR}/join-info.txt << EOF
============================================
K3s 클러스터 조인 정보
============================================

마스터 서버 IP: ${MASTER_IP}
K3s API 포트: 6443

노드 토큰 위치: ${TOKEN_DIR}/node-token

Worker 노드 조인 명령어:
curl -sfL https://get.k3s.io | K3S_URL=https://${MASTER_IP}:6443 K3S_TOKEN=<토큰> sh -

추가 마스터 조인 명령어 (HA):
curl -sfL https://get.k3s.io | K3S_URL=https://${MASTER_IP}:6443 K3S_TOKEN=<토큰> sh -s - server

============================================
EOF

log_success "토큰 저장 완료: ${TOKEN_DIR}"

#-----------------------------------------------
# 5. 마스터 노드 라벨 설정
#-----------------------------------------------
log_info "마스터 노드 라벨 설정 중..."

# 잠시 대기 후 라벨 설정
sleep 5
export KUBECONFIG=${CURRENT_HOME}/.kube/config

NODE_NAME=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')

# 노드 라벨 설정
kubectl label node ${NODE_NAME} node-role.kubernetes.io/master=true --overwrite
kubectl label node ${NODE_NAME} node-type=gpu --overwrite
kubectl label node ${NODE_NAME} gpu-type=rtx3090 --overwrite
kubectl label node ${NODE_NAME} gpu-count=4 --overwrite

log_success "노드 라벨 설정 완료"

#-----------------------------------------------
# 6. 설치 확인
#-----------------------------------------------
echo ""
echo "=============================================="
echo "       설치 완료!"
echo "=============================================="
echo ""

kubectl get nodes -o wide
echo ""
kubectl get pods -A
echo ""

log_success "K3s 마스터 설치가 완료되었습니다!"
echo ""
echo "다음 단계:"
echo "  1. 새 터미널을 열거나: source ~/.bashrc"
echo "  2. 클러스터 확인: kubectl get nodes"
echo "  3. Worker 추가: ./02-add-worker.sh (다른 서버에서 실행)"
echo ""
echo "토큰 확인: cat ${TOKEN_DIR}/node-token"
echo ""
