#!/bin/bash

##############################################################################
# K3s Dashboard - Docker 빌드 및 K8s Pod 배포 자동화 스크립트
##############################################################################

set -e  # 에러 발생시 즉시 종료

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_DIR="${ROOT_DIR}/dashboard"
IMAGE_NAME="${IMAGE_NAME:-localhost:5000/k3s-dashboard}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
NAMESPACE="${NAMESPACE:-default}"
DEPLOYMENT_NAME="k3s-dashboard"
DOCKER_BUILDKIT=1

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

# 도움말
usage() {
    cat << EOF
사용법: $0 [옵션]

옵션:
    -i, --image IMAGE       Docker 이미지 이름 (기본값: localhost:5000/k3s-dashboard)
    -t, --tag TAG           이미지 태그 (기본값: latest)
    -n, --namespace NS      K8s 네임스페이스 (기본값: default)
    --skip-build            Docker 이미지 빌드 스킵
    --skip-push             Registry push 스킵
    --skip-deploy           K8s 배포 스킵
    --force-restart         기존 Pod 강제 재시작
    --no-cache              Docker 빌드 시 캐시 무시 (코드 변경 후 권장)
    -h, --help              이 메시지 표시

예시:
    # 기본 빌드 및 배포
    $0

    # 커스텀 이미지 이름과 태그로 배포
    $0 --image myregistry/dashboard --tag v1.0.0

    # 빌드만 수행 (배포 스킵)
    $0 --skip-deploy

    # 이미 빌드된 이미지로 배포만 수행
    $0 --skip-build --skip-push

EOF
    exit 1
}

# 옵션 파싱
SKIP_BUILD=false
SKIP_PUSH=false
SKIP_DEPLOY=false
FORCE_RESTART=false
NO_CACHE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-push)
            SKIP_PUSH=true
            shift
            ;;
        --skip-deploy)
            SKIP_DEPLOY=true
            shift
            ;;
        --force-restart)
            FORCE_RESTART=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "알 수 없는 옵션: $1"
            usage
            ;;
    esac
done

# 전체 이미지 이름 업데이트
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

##############################################################################
# 1. 사전 확인
##############################################################################

log_info "사전 확인 중..."

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    log_error "Docker가 설치되지 않았습니다"
    exit 1
fi

# kubectl 설치 확인
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl이 설치되지 않았습니다"
    exit 1
fi

# 대시보드 디렉토리 확인
if [ ! -f "$DASHBOARD_DIR/Dockerfile" ]; then
    log_error "Dockerfile을 찾을 수 없습니다: $DASHBOARD_DIR/Dockerfile"
    exit 1
fi

# 필수 디렉토리 확인
for dir in frontend backend; do
    if [ ! -d "$DASHBOARD_DIR/$dir" ]; then
        log_error "$dir 디렉토리를 찾을 수 없습니다: $DASHBOARD_DIR/$dir"
        exit 1
    fi
done

log_success "사전 확인 완료"

##############################################################################
# 2. Docker 이미지 빌드
##############################################################################

if [ "$SKIP_BUILD" = false ]; then
    log_info "Docker 이미지 빌드 시작..."
    log_info "이미지: $FULL_IMAGE"
    log_info "디렉토리: $DASHBOARD_DIR"

    cd "$DASHBOARD_DIR"

    # 빌드 인자 설정
    BUILD_ARGS="--file Dockerfile --tag $FULL_IMAGE --build-arg BUILDKIT_INLINE_CACHE=1"

    if [ "$NO_CACHE" = true ]; then
        log_warn "캐시를 무시하고 전체 재빌드합니다..."
        BUILD_ARGS="$BUILD_ARGS --no-cache"
    fi

    # 빌드 실행
    if docker build $BUILD_ARGS . ; then
        log_success "Docker 이미지 빌드 완료: $FULL_IMAGE"
    else
        log_error "Docker 이미지 빌드 실패"
        exit 1
    fi
else
    log_warn "Docker 이미지 빌드 스킵"
fi

##############################################################################
# 3. Registry에 Push
##############################################################################

if [ "$SKIP_PUSH" = false ]; then
    # localhost:5000 이 아닌 경우만 push
    if [[ $IMAGE_NAME != localhost:5000/* ]] && [[ $IMAGE_NAME != localhost/* ]]; then
        log_info "Registry에 이미지 Push 중..."

        if docker push "$FULL_IMAGE"; then
            log_success "Registry Push 완료: $FULL_IMAGE"
        else
            log_error "Registry Push 실패"
            exit 1
        fi
    else
        log_info "로컬 레지스트리 이미지이므로 Push 스킵"
    fi
else
    log_warn "Registry Push 스킵"
fi

##############################################################################
# 4. K8s 배포
##############################################################################

if [ "$SKIP_DEPLOY" = false ]; then
    log_info "K8s 배포 시작..."

    # 네임스페이스 확인
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "네임스페이스 '$NAMESPACE' 생성 중..."
        kubectl create namespace "$NAMESPACE"
    fi

    # 현재 배포 상태 확인
    if kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
        log_info "기존 Deployment 찾음: $DEPLOYMENT_NAME"

        # 이미지 업데이트
        log_info "Deployment 이미지 업데이트 중: $FULL_IMAGE"
        kubectl set image deployment/$DEPLOYMENT_NAME \
            dashboard="$FULL_IMAGE" \
            -n "$NAMESPACE" \
            --record

        # Pod 재시작
        if [ "$FORCE_RESTART" = true ]; then
            log_info "Pod 강제 재시작 중..."
            kubectl rollout restart deployment/$DEPLOYMENT_NAME -n "$NAMESPACE"
        else
            log_info "자동 롤아웃 대기 중..."
            kubectl rollout status deployment/$DEPLOYMENT_NAME -n "$NAMESPACE" --timeout=5m
        fi

        log_success "Deployment 업데이트 완료"
    else
        log_warn "기존 Deployment를 찾을 수 없습니다"
        log_info "dashboard-deployment.yaml을 사용하여 배포 중..."

        # deployment.yaml이 있는 경우 배포
        if [ -f "$ROOT_DIR/dashboard-deployment.yaml" ]; then
            kubectl apply -f "$ROOT_DIR/dashboard-deployment.yaml"
            log_success "새 Deployment 배포 완료"
        else
            log_error "dashboard-deployment.yaml을 찾을 수 없습니다: $ROOT_DIR/dashboard-deployment.yaml"
            exit 1
        fi
    fi

    # 배포 상태 확인
    log_info "배포 상태 확인 중..."
    sleep 2
    kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT_NAME"

else
    log_warn "K8s 배포 스킵"
fi

##############################################################################
# 5. 배포 후 확인
##############################################################################

log_info "배포 상태 최종 확인..."

if kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
    READY=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.status.readyReplicas}')
    DESIRED=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.status.desiredReplicas}')

    if [ "$READY" = "$DESIRED" ] && [ "$READY" -gt 0 ]; then
        log_success "Pod가 성공적으로 실행 중입니다 ($READY/$DESIRED)"
    else
        log_warn "Pod 준비 중 ($READY/$DESIRED)"
    fi

    # Pod 상세 정보
    log_info "Pod 상세 정보:"
    kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT_NAME" -o wide

    # 서비스 확인
    if kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
        log_info "서비스 정보:"
        kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE"
    fi

    # Ingress 확인
    if kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
        log_info "Ingress 정보:"
        kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE"
        INGRESS_HOST=$(kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
            -o jsonpath='{.spec.rules[0].host}')
        log_info "대시보드 접근 URL: http://$INGRESS_HOST"
    fi
fi

##############################################################################
# 6. 완료
##############################################################################

log_success "배포 프로세스 완료!"
log_info ""
log_info "📊 배포 상태:"
kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o wide 2>/dev/null || true
echo ""
log_info "📋 Pod 상태:"
kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT_NAME" -o wide 2>/dev/null || true
echo ""
log_info "🔗 접근 주소:"
INGRESS_HOST=$(kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)
if [ -n "$INGRESS_HOST" ]; then
    echo "  http://$INGRESS_HOST"
fi
echo ""
log_info "📝 다음 명령어로 로그를 확인할 수 있습니다:"
echo "  kubectl logs -n $NAMESPACE -l app=$DEPLOYMENT_NAME -f"
echo ""
log_info "⚠️  브라우저 캐시 초기화:"
echo "  Windows/Linux: Ctrl + Shift + R"
echo "  Mac: Cmd + Shift + R"
