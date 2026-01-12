#!/bin/bash

##############################################################################
# K3s Dashboard - 향상된 배포 스크립트 (sudo 포함)
# 이 스크립트는 K3s containerd 이미지 캐시 문제를 해결하기 위해
# Docker 이미지를 K3s에 직접 로드합니다.
##############################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 설정
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_DIR="${ROOT_DIR}/dashboard"
IMAGE_NAME="${IMAGE_NAME:-localhost:5000/k3s-dashboard}"
TAG=$(date +%s)  # 타임스탐프 태그로 강제 갱신
FULL_IMAGE="${IMAGE_NAME}:${TAG}"
NAMESPACE="${NAMESPACE:-default}"
DEPLOYMENT_NAME="k3s-dashboard"

log_info ""
log_info "╔════════════════════════════════════════════════════════════╗"
log_info "║  K3s Dashboard 배포 (K3s containerd 최적화)                 ║"
log_info "╚════════════════════════════════════════════════════════════╝"
log_info ""

##############################################################################
# 1. 프론트엔드 재빌드
##############################################################################

log_info "Step 1/5: 프론트엔드 재빌드"

cd "$DASHBOARD_DIR/frontend"
log_info "  → npm run build 실행..."
rm -rf build
npm run build > /dev/null 2>&1
log_success "  ✓ 프론트엔드 빌드 완료"

##############################################################################
# 2. Docker 이미지 빌드
##############################################################################

log_info ""
log_info "Step 2/5: Docker 이미지 빌드"

cd "$DASHBOARD_DIR"
log_info "  → ${FULL_IMAGE} 빌드 중..."
docker image rm -f "${IMAGE_NAME}:latest" 2>/dev/null || true
docker build --no-cache -f Dockerfile -t "$FULL_IMAGE" . > /dev/null 2>&1
docker tag "$FULL_IMAGE" "${IMAGE_NAME}:latest"
log_success "  ✓ Docker 이미지 빌드 완료"

##############################################################################
# 3. K3s containerd에 이미지 로드
##############################################################################

log_info ""
log_info "Step 3/5: K3s containerd에 이미지 로드"

TAR_FILE="/tmp/k3s-dashboard-${TAG}.tar"
log_info "  → 이미지를 tar로 저장: $TAR_FILE"
docker save "$FULL_IMAGE" -o "$TAR_FILE"

log_info "  → K3s containerd에 로드 (sudo 필요)..."
sudo k3s ctr images import "$TAR_FILE" 2>&1 | grep -E "imported|error|ERROR" || true
rm -f "$TAR_FILE"
log_success "  ✓ K3s containerd 로드 완료"

##############################################################################
# 4. K8s 배포 업데이트
##############################################################################

log_info ""
log_info "Step 4/5: K8s 배포 업데이트"

cd "$ROOT_DIR"

# 네임스페이스 확인
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    log_info "  → 네임스페이스 생성: $NAMESPACE"
    kubectl create namespace "$NAMESPACE"
fi

# Deployment가 있는지 확인
if kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
    log_info "  → 기존 Deployment 이미지 업데이트"
    kubectl set image deployment/$DEPLOYMENT_NAME \
        dashboard="$FULL_IMAGE" \
        -n "$NAMESPACE" \
        --record 2>/dev/null || true

    log_info "  → Pod 재시작 중..."
    kubectl rollout restart deployment/$DEPLOYMENT_NAME -n "$NAMESPACE"

    log_info "  → 롤아웃 완료 대기..."
    kubectl rollout status deployment/$DEPLOYMENT_NAME -n "$NAMESPACE" --timeout=5m || true
else
    log_warn "  → Deployment를 찾을 수 없습니다"
    if [ -f "${ROOT_DIR}/dashboard-deployment.yaml" ]; then
        log_info "  → deployment.yaml 적용 중..."
        kubectl apply -f "${ROOT_DIR}/dashboard-deployment.yaml"
    fi
fi

log_success "  ✓ K8s 배포 완료"

##############################################################################
# 5. 배포 검증
##############################################################################

log_info ""
log_info "Step 5/5: 배포 검증"

sleep 3

# Pod 상태 확인
READY=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
    -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
DESIRED=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
    -o jsonpath='{.status.desiredReplicas}' 2>/dev/null || echo "0")

if [ "$READY" = "$DESIRED" ] && [ "$READY" -gt 0 ]; then
    log_success "  ✓ Pod 준비 완료 ($READY/$DESIRED)"
else
    log_warn "  ⚠ Pod 준비 중... ($READY/$DESIRED)"
fi

# Ingress 확인
INGRESS_HOST=$(kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
    -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)

log_info ""
log_info "╔════════════════════════════════════════════════════════════╗"
log_info "║  배포 완료!                                                 ║"
log_info "╚════════════════════════════════════════════════════════════╝"
log_info ""

echo -e "${GREEN}✅ 배포 정보:${NC}"
echo "  • 이미지: $FULL_IMAGE"
echo "  • 태그: $TAG (타임스탐프)"
echo "  • Namespace: $NAMESPACE"
echo "  • Deployment: $DEPLOYMENT_NAME"
echo ""

if [ -n "$INGRESS_HOST" ]; then
    echo -e "${GREEN}🌐 대시보드 접근:${NC}"
    echo "  http://$INGRESS_HOST"
fi

echo ""
echo -e "${GREEN}📝 유용한 명령어:${NC}"
echo "  # 로그 확인"
echo "  kubectl logs -n $NAMESPACE -l app=$DEPLOYMENT_NAME -f"
echo ""
echo "  # Pod 상태 확인"
echo "  kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME -o wide"
echo ""
echo "  # 배포 상태 확인"
echo "  kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE"
echo ""

echo -e "${YELLOW}⚠️  브라우저 캐시 초기화 필수:${NC}"
echo "  Windows/Linux: Ctrl + Shift + R"
echo "  Mac: Cmd + Shift + R"
echo ""

log_success "스크립트 완료!"
