#!/bin/bash
#===============================================================================
# 커스텀 K3s 대시보드 설치 스크립트
#
# 사용법: ./07-install-dashboard.sh (일반 사용자로 실행)
#
# 설치 항목:
# - Docker (이미지 빌드용)
# - K3s Dashboard (React + FastAPI)
# - 워크로드 매니페스트 (vLLM, RustFS, Qdrant)
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

# 현재 사용자 정보
CURRENT_USER=$(whoami)
CURRENT_HOME=$HOME
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DASHBOARD_DIR="${SCRIPT_DIR}/dashboard"

# Root로 실행하면 안됨
if [ "$EUID" -eq 0 ]; then
    log_error "일반 사용자로 실행하세요 (sudo 없이): ./07-install-dashboard.sh"
    exit 1
fi

# sudo 권한 확인
if ! sudo -n true 2>/dev/null; then
    log_info "sudo 권한이 필요합니다. 비밀번호를 입력하세요."
    sudo -v
fi

# kubectl 확인
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl이 설치되어 있지 않습니다. 먼저 01-install-master.sh를 실행하세요."
    exit 1
fi

# 클러스터 연결 확인
export KUBECONFIG=${CURRENT_HOME}/.kube/config
if ! kubectl cluster-info &> /dev/null; then
    log_error "Kubernetes 클러스터에 연결할 수 없습니다."
    exit 1
fi

# 설정 변수
MASTER_IP=$(hostname -I | awk '{print $1}')
DASHBOARD_HOSTNAME="dashboard.${MASTER_IP}.nip.io"
IMAGE_NAME="k3s-dashboard"
IMAGE_TAG="latest"

echo ""
echo "=============================================="
echo "       K3s 커스텀 대시보드 설치"
echo "=============================================="
echo ""
echo "  대시보드 URL: http://${DASHBOARD_HOSTNAME}"
echo "  이미지: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "=============================================="
echo ""

read -p "설치를 진행하시겠습니까? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    log_warn "설치가 취소되었습니다."
    exit 0
fi

#-----------------------------------------------
# 1. Docker 설치 확인
#-----------------------------------------------
log_info "Docker 설치 확인 중..."

if ! command -v docker &> /dev/null; then
    log_info "Docker 설치 중..."

    # Docker 공식 설치 스크립트
    curl -fsSL https://get.docker.com | sudo sh

    # 현재 사용자를 docker 그룹에 추가
    sudo usermod -aG docker ${CURRENT_USER}

    log_success "Docker 설치 완료"
    log_warn "Docker 그룹 적용을 위해 로그아웃 후 다시 로그인하거나, 'newgrp docker' 실행이 필요할 수 있습니다."
else
    log_info "Docker가 이미 설치됨: $(docker --version)"
fi

#-----------------------------------------------
# 2. Node.js 설치 확인 (프론트엔드 빌드용)
#-----------------------------------------------
log_info "Node.js 설치 확인 중..."

if ! command -v node &> /dev/null; then
    log_info "Node.js 설치 중..."

    # NodeSource에서 Node.js 20.x 설치
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs

    log_success "Node.js 설치 완료: $(node --version)"
else
    log_info "Node.js가 이미 설치됨: $(node --version)"
fi

#-----------------------------------------------
# 3. 대시보드 이미지 빌드
#-----------------------------------------------
log_info "대시보드 Docker 이미지 빌드 중..."

cd ${DASHBOARD_DIR}

# Docker 빌드 (K3s의 containerd에서 사용할 수 있도록)
sudo docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# K3s containerd에 이미지 저장
log_info "K3s에 이미지 등록 중..."
sudo docker save ${IMAGE_NAME}:${IMAGE_TAG} | sudo k3s ctr images import -

log_success "대시보드 이미지 빌드 완료"

#-----------------------------------------------
# 4. 워크로드 매니페스트 배포
#-----------------------------------------------
log_info "워크로드 매니페스트 배포 중..."

kubectl apply -f ${DASHBOARD_DIR}/k8s/workloads.yaml

log_success "워크로드 매니페스트 배포 완료"

#-----------------------------------------------
# 5. 대시보드 배포
#-----------------------------------------------
log_info "대시보드 배포 중..."

# Ingress 호스트네임 업데이트
sed -i "s/dashboard.local/${DASHBOARD_HOSTNAME}/g" ${DASHBOARD_DIR}/k8s/deployment.yaml

kubectl apply -f ${DASHBOARD_DIR}/k8s/deployment.yaml

# 배포 대기
log_info "대시보드 Pod 준비 대기 중..."
kubectl -n dashboard rollout status deployment/k3s-dashboard --timeout=120s

log_success "대시보드 배포 완료"

#-----------------------------------------------
# 6. 접속 정보
#-----------------------------------------------
echo ""
echo "=============================================="
echo "       대시보드 설치 완료!"
echo "=============================================="
echo ""

# Pod 상태 확인
log_info "대시보드 Pod 상태:"
kubectl get pods -n dashboard
echo ""

log_info "워크로드 네임스페이스:"
kubectl get namespaces | grep -E "dashboard|ai-workloads|storage"
echo ""

# 접속 정보 저장
cat > ${SCRIPT_DIR}/dashboard-access.txt << EOF
============================================
K3s Dashboard 접속 정보
============================================

대시보드 URL: http://${DASHBOARD_HOSTNAME}

기능:
- 클러스터 상태 모니터링
- 노드 리소스 확인
- vLLM 실행/중지
- RustFS 스토리지 관리
- Qdrant 실행/중지

※ 브라우저에서 위 URL로 접속하세요.
※ nip.io DNS를 사용하므로 인터넷 연결이 필요합니다.

============================================
EOF

log_success "접속 정보가 ${SCRIPT_DIR}/dashboard-access.txt에 저장되었습니다."
echo ""
echo "  대시보드 URL: http://${DASHBOARD_HOSTNAME}"
echo ""
echo "  브라우저에서 위 URL로 접속하세요!"
echo ""
