#!/bin/bash

##############################################################################
# K3s Dashboard - 배포 모니터링 및 트러블슈팅 스크립트
##############################################################################

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 설정
NAMESPACE="${1:-default}"
DEPLOYMENT_NAME="k3s-dashboard"

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

log_section() {
    echo -e "${CYAN}=== $1 ===${NC}"
}

# 도움말
usage() {
    cat << EOF
사용법: $0 [네임스페이스] [명령어]

네임스페이스: K8s 네임스페이스 (기본값: default)

명령어:
    status      배포 상태 확인
    logs        Pod 로그 출력
    events      최근 이벤트 확인
    describe    Deployment 상세 정보
    shell       Pod에 대화형 셸 접속
    restart     Pod 재시작
    delete      Deployment 삭제
    all         모든 정보 확인 (기본값)

예시:
    $0 default status
    $0 default logs
    $0 default shell

EOF
    exit 1
}

# 배포 상태 확인
check_deployment_status() {
    log_section "Deployment 상태"

    if ! kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
        log_error "Deployment를 찾을 수 없습니다: $DEPLOYMENT_NAME"
        return 1
    fi

    kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o wide
    echo ""

    # 상세 정보
    local DESIRED=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.status.desiredReplicas}')
    local READY=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.status.readyReplicas}')
    local UPDATED=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.status.updatedReplicas}')
    local AVAILABLE=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.status.availableReplicas}')

    log_info "Desired: $DESIRED, Ready: $READY, Updated: $UPDATED, Available: $AVAILABLE"

    if [ "$READY" = "$DESIRED" ] && [ "$READY" -gt 0 ]; then
        log_success "모든 Pod이 준비되었습니다"
    else
        log_warn "Pod이 준비 중입니다 ($READY/$DESIRED)"
    fi

    echo ""
}

# Pod 상태 확인
check_pod_status() {
    log_section "Pod 상태"

    local POD_COUNT=$(kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT_NAME" \
        --no-headers 2>/dev/null | wc -l)

    if [ "$POD_COUNT" -eq 0 ]; then
        log_error "실행 중인 Pod이 없습니다"
        return 1
    fi

    kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT_NAME" -o wide
    echo ""

    # Pod별 상세 상태
    while IFS= read -r POD; do
        if [ -n "$POD" ]; then
            local STATUS=$(kubectl get pod "$POD" -n "$NAMESPACE" \
                -o jsonpath='{.status.phase}')
            local RESTARTS=$(kubectl get pod "$POD" -n "$NAMESPACE" \
                -o jsonpath='{.status.containerStatuses[0].restartCount}')
            local READY=$(kubectl get pod "$POD" -n "$NAMESPACE" \
                -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')

            if [ "$STATUS" = "Running" ] && [ "$READY" = "True" ]; then
                log_success "Pod: $POD (Ready, Restarts: $RESTARTS)"
            else
                log_warn "Pod: $POD (Status: $STATUS, Ready: $READY, Restarts: $RESTARTS)"
            fi
        fi
    done < <(kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT_NAME" -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n')

    echo ""
}

# Pod 로그 확인
show_pod_logs() {
    log_section "Pod 로그"

    local POD=$(kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT_NAME" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -z "$POD" ]; then
        log_error "Pod을 찾을 수 없습니다"
        return 1
    fi

    log_info "Pod: $POD에서 로그 출력 중 (최근 100줄, -f로 계속 모니터링)..."
    echo "로그를 중지하려면 Ctrl+C를 누르세요"
    echo ""

    kubectl logs -n "$NAMESPACE" "$POD" -c dashboard --tail=100 -f
}

# 최근 이벤트 확인
show_events() {
    log_section "최근 이벤트"

    kubectl get events -n "$NAMESPACE" \
        --sort-by='.lastTimestamp' | tail -20
    echo ""
}

# Deployment 상세 정보
show_deployment_details() {
    log_section "Deployment 상세 정보"

    kubectl describe deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE"
    echo ""
}

# Pod에 셸 접속
pod_shell() {
    local POD=$(kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT_NAME" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -z "$POD" ]; then
        log_error "Pod을 찾을 수 없습니다"
        return 1
    fi

    log_info "Pod에 접속합니다: $POD"
    kubectl exec -it -n "$NAMESPACE" "$POD" -c dashboard -- /bin/bash
}

# Pod 재시작
restart_pod() {
    log_info "Pod을 재시작합니다..."

    kubectl rollout restart deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE"

    log_info "재시작 진행 중..."
    kubectl rollout status deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" --timeout=5m

    log_success "Pod 재시작 완료"
}

# Deployment 삭제
delete_deployment() {
    log_warn "Deployment를 삭제하시겠습니까? (y/n)"
    read -r RESPONSE

    if [ "$RESPONSE" = "y" ] || [ "$RESPONSE" = "Y" ]; then
        log_info "Deployment 삭제 중..."
        kubectl delete deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE"
        log_success "Deployment 삭제 완료"
    else
        log_info "삭제 취소"
    fi
}

# 서비스 정보
show_service_info() {
    log_section "서비스 정보"

    if kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
        kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o wide
        echo ""

        local SERVICE_IP=$(kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
            -o jsonpath='{.spec.clusterIP}')
        local SERVICE_PORT=$(kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
            -o jsonpath='{.spec.ports[0].port}')

        log_info "Service: $SERVICE_IP:$SERVICE_PORT"
        echo ""
    else
        log_warn "Service를 찾을 수 없습니다"
    fi
}

# Ingress 정보
show_ingress_info() {
    log_section "Ingress 정보"

    if kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
        kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o wide
        echo ""

        local INGRESS_HOST=$(kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
            -o jsonpath='{.spec.rules[0].host}')
        local INGRESS_IP=$(kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" \
            -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

        log_info "URL: http://$INGRESS_HOST"
        log_info "IP: $INGRESS_IP"
        echo ""
    else
        log_warn "Ingress를 찾을 수 없습니다"
    fi
}

# 모든 정보 확인
show_all() {
    check_deployment_status
    check_pod_status
    show_service_info
    show_ingress_info
    show_deployment_details
    show_events
}

##############################################################################
# 메인
##############################################################################

# 명령어 파싱
COMMAND="${2:-all}"

case "$COMMAND" in
    status)
        check_deployment_status
        check_pod_status
        ;;
    logs)
        show_pod_logs
        ;;
    events)
        show_events
        ;;
    describe)
        show_deployment_details
        ;;
    shell)
        pod_shell
        ;;
    restart)
        restart_pod
        ;;
    delete)
        delete_deployment
        ;;
    all)
        show_all
        ;;
    *)
        log_error "알 수 없는 명령어: $COMMAND"
        usage
        ;;
esac
