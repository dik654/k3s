#!/bin/bash
#===============================================================================
# K3s HA 마스터 노드 추가 스크립트
#
# 사용법: sudo ./03-add-master-ha.sh --master-ip <기존마스터IP> --token <TOKEN>
#
# 주의:
# - HA 구성을 위해 최소 3대의 마스터 노드 권장
# - 기존 마스터가 --cluster-init으로 설치되어 있어야 함
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
NODE_NAME=""
K3S_VERSION="v1.31.4+k3s1"

# 도움말
show_help() {
    echo "K3s HA 마스터 노드 추가 스크립트"
    echo ""
    echo "사용법: sudo $0 [옵션]"
    echo ""
    echo "필수 옵션:"
    echo "  --master-ip <IP>     기존 마스터 노드 IP 주소"
    echo "  --token <TOKEN>      노드 조인 토큰"
    echo ""
    echo "선택 옵션:"
    echo "  --name <NAME>        노드 이름 [기본: 호스트명]"
    echo "  -h, --help           도움말"
    echo ""
    echo "예시:"
    echo "  sudo $0 --master-ip 14.32.100.220 --token K10xxx..."
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
        --name)
            NODE_NAME="$2"
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

# 노드 이름/IP 설정
if [ -z "$NODE_NAME" ]; then
    NODE_NAME=$(hostname)
fi

NODE_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=============================================="
echo "       K3s HA 마스터 노드 추가"
echo "=============================================="
echo ""
echo "  기존 마스터 IP: ${MASTER_IP}"
echo "  새 마스터 IP: ${NODE_IP}"
echo "  노드 이름: ${NODE_NAME}"
echo "  K3s 버전: ${K3S_VERSION}"
echo ""
echo "=============================================="
echo ""
log_warn "HA 구성을 위해 최소 3대의 마스터 노드가 권장됩니다."
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
# 2. K3s Server (마스터) 설치
#-----------------------------------------------
log_info "K3s 마스터 노드 설치 중..."

curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="${K3S_VERSION}" \
    K3S_URL="https://${MASTER_IP}:6443" \
    K3S_TOKEN="${TOKEN}" \
    sh -s - server \
    --node-name "${NODE_NAME}" \
    --node-ip "${NODE_IP}" \
    --tls-san "${NODE_IP}" \
    --tls-san "${NODE_NAME}" \
    --disable-cloud-controller

# 서비스 시작 대기
log_info "K3s 서비스 시작 대기 중..."
sleep 15

# 서비스 상태 확인
if systemctl is-active --quiet k3s; then
    log_success "K3s 서비스 시작됨"
else
    log_error "K3s 서비스 시작 실패"
    journalctl -u k3s -n 50
    exit 1
fi

#-----------------------------------------------
# 3. kubectl 설정
#-----------------------------------------------
log_info "kubectl 설정 중..."

REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo ~${REAL_USER})

mkdir -p ${REAL_HOME}/.kube
cp /etc/rancher/k3s/k3s.yaml ${REAL_HOME}/.kube/config
chown -R ${REAL_USER}:${REAL_USER} ${REAL_HOME}/.kube
chmod 600 ${REAL_HOME}/.kube/config

# 환경 변수 설정
if ! grep -q "KUBECONFIG" ${REAL_HOME}/.bashrc; then
    echo 'export KUBECONFIG=~/.kube/config' >> ${REAL_HOME}/.bashrc
fi

log_success "kubectl 설정 완료"

#-----------------------------------------------
# 4. 노드 라벨 설정
#-----------------------------------------------
log_info "노드 라벨 설정 중..."

sleep 5
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

kubectl label node ${NODE_NAME} node-role.kubernetes.io/master=true --overwrite
kubectl label node ${NODE_NAME} node-type=master --overwrite

log_success "노드 라벨 설정 완료"

#-----------------------------------------------
# 5. 설치 확인
#-----------------------------------------------
echo ""
echo "=============================================="
echo "       HA 마스터 노드 추가 완료!"
echo "=============================================="
echo ""

kubectl get nodes -o wide
echo ""

log_success "K3s HA 마스터 노드가 클러스터에 추가되었습니다!"
echo ""
echo "etcd 상태 확인: kubectl get endpoints -n kube-system"
echo ""
