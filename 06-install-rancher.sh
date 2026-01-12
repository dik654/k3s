#!/bin/bash
#===============================================================================
# Rancher 설치 스크립트
#
# 사용법: ./06-install-rancher.sh (일반 사용자로 실행)
#
# 설치 항목:
# - Helm 패키지 매니저
# - cert-manager (인증서 관리)
# - Rancher (클러스터 관리 UI)
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

# Root로 실행하면 안됨
if [ "$EUID" -eq 0 ]; then
    log_error "일반 사용자로 실행하세요 (sudo 없이): ./06-install-rancher.sh"
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
RANCHER_HOSTNAME="rancher.${MASTER_IP}.nip.io"
RANCHER_PASSWORD="admin1234"  # 초기 비밀번호 (나중에 변경)
HELM_VERSION="v3.17.3"
CERT_MANAGER_VERSION="v1.17.2"
RANCHER_VERSION="2.11.3"

echo ""
echo "=============================================="
echo "       Rancher 설치"
echo "=============================================="
echo ""
echo "  Helm 버전: ${HELM_VERSION}"
echo "  cert-manager 버전: ${CERT_MANAGER_VERSION}"
echo "  Rancher 버전: ${RANCHER_VERSION}"
echo "  Rancher URL: https://${RANCHER_HOSTNAME}"
echo "  초기 비밀번호: ${RANCHER_PASSWORD}"
echo ""
echo "=============================================="
echo ""

read -p "설치를 진행하시겠습니까? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    log_warn "설치가 취소되었습니다."
    exit 0
fi

#-----------------------------------------------
# 1. Helm 설치
#-----------------------------------------------
log_info "Helm 설치 확인 중..."

if command -v helm &> /dev/null; then
    CURRENT_HELM=$(helm version --short 2>/dev/null | cut -d'+' -f1)
    log_info "Helm이 이미 설치됨: ${CURRENT_HELM}"
else
    log_info "Helm 설치 중..."

    # Helm 다운로드 및 설치
    curl -fsSL https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz -o /tmp/helm.tar.gz
    tar -xzf /tmp/helm.tar.gz -C /tmp
    sudo mv /tmp/linux-amd64/helm /usr/local/bin/helm
    sudo chmod +x /usr/local/bin/helm
    rm -rf /tmp/helm.tar.gz /tmp/linux-amd64

    log_success "Helm 설치 완료: $(helm version --short)"
fi

#-----------------------------------------------
# 2. Helm 리포지토리 추가
#-----------------------------------------------
log_info "Helm 리포지토리 추가 중..."

helm repo add jetstack https://charts.jetstack.io 2>/dev/null || true
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable 2>/dev/null || true
helm repo update

log_success "Helm 리포지토리 추가 완료"

#-----------------------------------------------
# 3. cert-manager 설치
#-----------------------------------------------
log_info "cert-manager 설치 중..."

# cert-manager namespace 생성
kubectl create namespace cert-manager 2>/dev/null || true

# cert-manager CRDs 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.crds.yaml

# cert-manager 설치
helm upgrade --install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --version ${CERT_MANAGER_VERSION} \
    --wait

# cert-manager Pod 준비 대기
log_info "cert-manager Pod 준비 대기 중..."
kubectl -n cert-manager rollout status deployment/cert-manager --timeout=120s
kubectl -n cert-manager rollout status deployment/cert-manager-webhook --timeout=120s
kubectl -n cert-manager rollout status deployment/cert-manager-cainjector --timeout=120s

log_success "cert-manager 설치 완료"

#-----------------------------------------------
# 4. Rancher 설치
#-----------------------------------------------
log_info "Rancher 설치 중..."

# cattle-system namespace 생성
kubectl create namespace cattle-system 2>/dev/null || true

# Rancher 설치
helm upgrade --install rancher rancher-stable/rancher \
    --namespace cattle-system \
    --version ${RANCHER_VERSION} \
    --set hostname=${RANCHER_HOSTNAME} \
    --set bootstrapPassword=${RANCHER_PASSWORD} \
    --set ingress.tls.source=rancher \
    --set replicas=1 \
    --wait --timeout=10m

# Rancher 준비 대기
log_info "Rancher 준비 대기 중... (최대 5분)"
kubectl -n cattle-system rollout status deployment/rancher --timeout=300s

log_success "Rancher 설치 완료"

#-----------------------------------------------
# 5. 설치 확인
#-----------------------------------------------
echo ""
echo "=============================================="
echo "       Rancher 설치 완료!"
echo "=============================================="
echo ""

# Pod 상태 확인
log_info "cert-manager Pods:"
kubectl get pods -n cert-manager
echo ""

log_info "Rancher Pods:"
kubectl get pods -n cattle-system
echo ""

# 접속 정보 저장
cat > ${SCRIPT_DIR}/rancher-access.txt << EOF
============================================
Rancher 접속 정보
============================================

URL: https://${RANCHER_HOSTNAME}
초기 비밀번호: ${RANCHER_PASSWORD}

※ 자체 서명 인증서를 사용하므로 브라우저에서 보안 경고가 표시됩니다.
   "고급" → "계속 진행" 클릭하여 접속하세요.

※ 첫 로그인 후 비밀번호를 변경하세요.

============================================
EOF

log_success "접속 정보가 ${SCRIPT_DIR}/rancher-access.txt에 저장되었습니다."
echo ""
echo "  Rancher URL: https://${RANCHER_HOSTNAME}"
echo "  초기 비밀번호: ${RANCHER_PASSWORD}"
echo ""
echo "  브라우저에서 위 URL로 접속하세요!"
echo ""
