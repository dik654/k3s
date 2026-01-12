#!/bin/bash
#===============================================================================
# K3s 노드 라벨/테인트 관리 스크립트
#
# 사용법: ./04-node-labels.sh <명령> [옵션]
#
# 명령:
#   list              모든 노드의 라벨과 테인트 조회
#   label-gpu         GPU 노드 라벨 설정
#   label-cpu         CPU 노드 라벨 설정
#   label-storage     Storage 노드 라벨 설정
#   taint-gpu         GPU 전용 테인트 설정 (다른 워크로드 방지)
#   untaint           테인트 제거
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

# kubectl 확인
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl이 설치되어 있지 않습니다."
    exit 1
fi

# 도움말
show_help() {
    echo "K3s 노드 라벨/테인트 관리 스크립트"
    echo ""
    echo "사용법: $0 <명령> [옵션]"
    echo ""
    echo "명령:"
    echo "  list                          모든 노드의 라벨과 테인트 조회"
    echo "  label-gpu <노드명> [옵션]     GPU 노드 라벨 설정"
    echo "  label-cpu <노드명>            CPU 노드 라벨 설정"
    echo "  label-storage <노드명>        Storage 노드 라벨 설정"
    echo "  taint-gpu <노드명>            GPU 전용 테인트 설정"
    echo "  taint-storage <노드명>        Storage 전용 테인트 설정"
    echo "  untaint <노드명> <테인트키>   테인트 제거"
    echo ""
    echo "옵션 (label-gpu):"
    echo "  --gpu-type <타입>             GPU 타입 (예: rtx3090, a100)"
    echo "  --gpu-count <개수>            GPU 개수"
    echo ""
    echo "예시:"
    echo "  $0 list"
    echo "  $0 label-gpu gpu-node-01 --gpu-type rtx4090 --gpu-count 4"
    echo "  $0 taint-gpu gpu-node-01"
    echo "  $0 label-storage storage-node-01"
    echo ""
}

# 모든 노드 라벨/테인트 조회
list_nodes() {
    echo ""
    echo "=============================================="
    echo "       노드 목록 및 라벨"
    echo "=============================================="
    echo ""

    kubectl get nodes -o wide
    echo ""

    echo "----------------------------------------------"
    echo "노드별 상세 라벨:"
    echo "----------------------------------------------"

    for node in $(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'); do
        echo ""
        echo "📍 노드: ${node}"
        echo "   라벨:"
        kubectl get node ${node} -o jsonpath='{.metadata.labels}' | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'      {k}: {v}') for k,v in sorted(d.items()) if not k.startswith('beta.kubernetes') and not k.startswith('kubernetes.io') and not k.startswith('node.kubernetes.io')]" 2>/dev/null || \
        kubectl get node ${node} -o jsonpath='{.metadata.labels}' | tr ',' '\n' | sed 's/^/      /'

        echo "   테인트:"
        taints=$(kubectl get node ${node} -o jsonpath='{.spec.taints[*].key}')
        if [ -z "$taints" ]; then
            echo "      (없음)"
        else
            kubectl get node ${node} -o jsonpath='{range .spec.taints[*]}      {.key}={.value}:{.effect}{"\n"}{end}'
        fi
    done
    echo ""
}

# GPU 노드 라벨 설정
label_gpu() {
    local node=$1
    shift

    local gpu_type=""
    local gpu_count=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --gpu-type)
                gpu_type="$2"
                shift 2
                ;;
            --gpu-count)
                gpu_count="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if [ -z "$node" ]; then
        log_error "노드명을 지정하세요."
        exit 1
    fi

    log_info "GPU 노드 라벨 설정 중: ${node}"

    kubectl label node ${node} node-type=gpu --overwrite
    kubectl label node ${node} workload-type=gpu --overwrite
    kubectl label node ${node} gpu=true --overwrite

    if [ -n "$gpu_type" ]; then
        kubectl label node ${node} gpu-type=${gpu_type} --overwrite
    fi

    if [ -n "$gpu_count" ]; then
        kubectl label node ${node} gpu-count=${gpu_count} --overwrite
    fi

    log_success "GPU 노드 라벨 설정 완료: ${node}"
}

# CPU 노드 라벨 설정
label_cpu() {
    local node=$1

    if [ -z "$node" ]; then
        log_error "노드명을 지정하세요."
        exit 1
    fi

    log_info "CPU 노드 라벨 설정 중: ${node}"

    kubectl label node ${node} node-type=cpu --overwrite
    kubectl label node ${node} workload-type=compute --overwrite
    kubectl label node ${node} cpu-optimized=true --overwrite

    log_success "CPU 노드 라벨 설정 완료: ${node}"
}

# Storage 노드 라벨 설정
label_storage() {
    local node=$1

    if [ -z "$node" ]; then
        log_error "노드명을 지정하세요."
        exit 1
    fi

    log_info "Storage 노드 라벨 설정 중: ${node}"

    kubectl label node ${node} node-type=storage --overwrite
    kubectl label node ${node} workload-type=storage --overwrite
    kubectl label node ${node} storage=true --overwrite

    log_success "Storage 노드 라벨 설정 완료: ${node}"
}

# GPU 전용 테인트 설정
taint_gpu() {
    local node=$1

    if [ -z "$node" ]; then
        log_error "노드명을 지정하세요."
        exit 1
    fi

    log_info "GPU 전용 테인트 설정 중: ${node}"

    kubectl taint node ${node} gpu=true:NoSchedule --overwrite

    log_success "GPU 전용 테인트 설정 완료: ${node}"
    log_warn "이 노드에는 tolerations이 있는 Pod만 스케줄링됩니다."
    echo ""
    echo "Pod에 다음 tolerations 추가 필요:"
    echo "  tolerations:"
    echo "  - key: \"gpu\""
    echo "    operator: \"Equal\""
    echo "    value: \"true\""
    echo "    effect: \"NoSchedule\""
    echo ""
}

# Storage 전용 테인트 설정
taint_storage() {
    local node=$1

    if [ -z "$node" ]; then
        log_error "노드명을 지정하세요."
        exit 1
    fi

    log_info "Storage 전용 테인트 설정 중: ${node}"

    kubectl taint node ${node} storage=true:NoSchedule --overwrite

    log_success "Storage 전용 테인트 설정 완료: ${node}"
}

# 테인트 제거
untaint() {
    local node=$1
    local key=$2

    if [ -z "$node" ] || [ -z "$key" ]; then
        log_error "노드명과 테인트 키를 지정하세요."
        exit 1
    fi

    log_info "테인트 제거 중: ${node} (${key})"

    kubectl taint node ${node} ${key}- || true

    log_success "테인트 제거 완료"
}

# 메인
case "${1:-}" in
    list)
        list_nodes
        ;;
    label-gpu)
        shift
        label_gpu "$@"
        ;;
    label-cpu)
        shift
        label_cpu "$@"
        ;;
    label-storage)
        shift
        label_storage "$@"
        ;;
    taint-gpu)
        shift
        taint_gpu "$@"
        ;;
    taint-storage)
        shift
        taint_storage "$@"
        ;;
    untaint)
        shift
        untaint "$@"
        ;;
    -h|--help|"")
        show_help
        ;;
    *)
        log_error "알 수 없는 명령: $1"
        show_help
        exit 1
        ;;
esac
