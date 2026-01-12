#!/bin/bash
# K3s Dashboard 배포 스크립트 (이미지 캐싱 문제 해결 버전)
# 실행: sudo ./deploy-dashboard.sh
#
# 이 스크립트는 다음 문제를 해결합니다:
# 1. K3s containerd의 기존 이미지 캐시로 인한 재배포 실패
# 2. latest 태그 사용 시 이미지 변경 감지 실패
# 3. Pod가 기존 이미지를 재사용하는 문제

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

# 설정
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="k3s-dashboard"
DEPLOYMENT_NAME="k3s-dashboard"
IMAGE_NAME="k3s-dashboard"
TAR_FILE="${TAR_FILE:-/tmp/k3s-dashboard.tar}"
MANIFEST_FILE="${MANIFEST_FILE:-${ROOT_DIR}/manifests/20-dashboard.yaml}"

# 타임스탬프 태그 생성 (재배포 강제용)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="v${TIMESTAMP}"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

echo "=== K3s Dashboard 배포 (이미지 갱신 보장) ==="
echo ""

##############################################################################
# 1. Docker 이미지 확인 및 태그 생성
##############################################################################

log_info "Step 1: Docker 이미지 준비"

# Docker 이미지가 로컬에 있는지 확인
if docker image inspect "${IMAGE_NAME}:latest" &> /dev/null; then
    log_info "Docker에서 ${IMAGE_NAME}:latest 이미지 발견"

    # 타임스탬프 태그 추가
    log_info "새 태그 생성: ${FULL_IMAGE}"
    docker tag "${IMAGE_NAME}:latest" "${FULL_IMAGE}"

    # tar 파일로 저장
    log_info "이미지를 tar 파일로 저장 중..."
    docker save "${FULL_IMAGE}" -o "${TAR_FILE}"
    log_success "이미지 저장 완료: ${TAR_FILE}"
else
    log_warn "Docker에 ${IMAGE_NAME}:latest 이미지가 없습니다"

    # 기존 tar 파일 확인
    if [ ! -f "${TAR_FILE}" ]; then
        log_error "${TAR_FILE} 파일도 없습니다."
        log_error "먼저 Docker 이미지를 빌드하세요:"
        log_error "  cd dashboard && docker build -t ${IMAGE_NAME}:latest ."
        exit 1
    fi
    log_warn "기존 ${TAR_FILE} 파일 사용"
    # 기존 tar에서 latest 태그를 사용
    FULL_IMAGE="${IMAGE_NAME}:latest"
fi

##############################################################################
# 2. K3s containerd에서 기존 이미지 삭제 (캐시 문제 해결)
##############################################################################

log_info "Step 2: K3s containerd 기존 이미지 정리"

# 모든 k3s-dashboard 이미지 삭제
log_info "기존 ${IMAGE_NAME} 이미지 삭제 중..."
k3s ctr images list | grep "${IMAGE_NAME}" | awk '{print $1}' | while read img; do
    if [ -n "$img" ]; then
        log_info "  삭제: $img"
        k3s ctr images rm "$img" 2>/dev/null || true
    fi
done

log_success "기존 이미지 정리 완료"

##############################################################################
# 3. 새 이미지 Import
##############################################################################

log_info "Step 3: 새 이미지 Import"

log_info "K3s containerd에 이미지 import 중: ${TAR_FILE}"
if k3s ctr images import "${TAR_FILE}"; then
    log_success "이미지 import 완료"
else
    log_error "이미지 import 실패"
    exit 1
fi

# Import된 이미지 확인
log_info "Import된 이미지 목록:"
k3s ctr images list | grep "${IMAGE_NAME}" || log_warn "이미지를 찾을 수 없음"

##############################################################################
# 4. Kubernetes 리소스 적용 (이미지 태그 업데이트)
##############################################################################

log_info "Step 4: Kubernetes 배포 업데이트"

# 매니페스트 파일 확인
if [ ! -f "${MANIFEST_FILE}" ]; then
    log_error "매니페스트 파일을 찾을 수 없습니다: ${MANIFEST_FILE}"
    exit 1
fi

# 네임스페이스 생성 (없으면)
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# 매니페스트 적용
log_info "매니페스트 적용 중: ${MANIFEST_FILE}"
kubectl apply -f "${MANIFEST_FILE}"

# Deployment 이미지 업데이트 (타임스탬프 태그로)
log_info "Deployment 이미지 업데이트: ${FULL_IMAGE}"
kubectl set image deployment/${DEPLOYMENT_NAME} \
    dashboard="${FULL_IMAGE}" \
    -n "${NAMESPACE}" 2>/dev/null || true

##############################################################################
# 5. Pod 강제 재시작 (이미지 갱신 보장)
##############################################################################

log_info "Step 5: Pod 강제 재시작"

# 기존 Pod 삭제로 강제 재시작
log_info "기존 Pod 삭제 중..."
kubectl delete pod -n "${NAMESPACE}" -l "app=${DEPLOYMENT_NAME}" --ignore-not-found --wait=false

# Rollout 재시작 (백업 방법)
log_info "Deployment rollout restart..."
kubectl rollout restart deployment/${DEPLOYMENT_NAME} -n "${NAMESPACE}" 2>/dev/null || true

##############################################################################
# 6. 배포 상태 확인
##############################################################################

log_info "Step 6: 배포 상태 확인"

log_info "새 Pod 생성 대기 중 (최대 60초)..."
for i in {1..12}; do
    READY=$(kubectl get deployment "${DEPLOYMENT_NAME}" -n "${NAMESPACE}" \
        -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    DESIRED=$(kubectl get deployment "${DEPLOYMENT_NAME}" -n "${NAMESPACE}" \
        -o jsonpath='{.status.replicas}' 2>/dev/null || echo "1")

    if [ "${READY}" = "${DESIRED}" ] && [ "${READY}" != "0" ]; then
        log_success "Pod 준비 완료! (${READY}/${DESIRED})"
        break
    fi

    echo -n "."
    sleep 5
done
echo ""

# 최종 상태 출력
echo ""
log_info "=== 최종 배포 상태 ==="
echo ""
kubectl get pods -n "${NAMESPACE}" -l "app=${DEPLOYMENT_NAME}" -o wide

# 현재 사용 중인 이미지 확인
echo ""
log_info "현재 실행 중인 이미지:"
kubectl get pods -n "${NAMESPACE}" -l "app=${DEPLOYMENT_NAME}" \
    -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' 2>/dev/null || true

##############################################################################
# 7. 완료
##############################################################################

echo ""
log_success "=== 배포 완료! ==="
echo ""
echo "  📊 대시보드 접속:"
echo "     NodePort: http://<노드IP>:30080"
echo "     Ingress:  http://dashboard.local"
echo ""
echo "  🔍 로그 확인:"
echo "     kubectl logs -n ${NAMESPACE} -l app=${DEPLOYMENT_NAME} -f"
echo ""
echo "  ⚠️  브라우저 캐시 초기화 권장:"
echo "     Windows/Linux: Ctrl + Shift + R"
echo "     Mac: Cmd + Shift + R"
echo ""
