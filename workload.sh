#!/bin/bash
#===============================================================================
# K3s 워크로드 관리 스크립트
#
# 사용법:
#   ./workload.sh status              # 전체 상태 확인
#   ./workload.sh start <서비스>       # 서비스 시작
#   ./workload.sh stop <서비스>        # 서비스 중지
#   ./workload.sh restart <서비스>     # 서비스 재시작
#   ./workload.sh logs <서비스>        # 서비스 로그 확인
#   ./workload.sh switch <서비스>      # 다른 GPU 서비스 끄고 해당 서비스만 켜기
#   ./workload.sh gpu                 # GPU 사용 현황
#   ./workload.sh init                # 네임스페이스 및 스토리지 초기 설정
#
# 서비스 목록: vllm, qdrant, comfyui, vlm, rustfs, all
#===============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MANIFESTS_DIR="${SCRIPT_DIR}/manifests"

export KUBECONFIG=${HOME}/.kube/config

# GPU 서비스 목록 (GPU를 사용하는 서비스들)
GPU_SERVICES=("vllm" "comfyui" "vlm")
# CPU 서비스 목록
CPU_SERVICES=("qdrant" "rustfs")
# 전체 서비스
ALL_SERVICES=("vllm" "qdrant" "comfyui" "vlm" "rustfs")

# 서비스별 네임스페이스
get_namespace() {
    case "$1" in
        rustfs) echo "storage" ;;
        *) echo "ai-workloads" ;;
    esac
}

# 서비스별 매니페스트 파일
get_manifest() {
    case "$1" in
        vllm) echo "${MANIFESTS_DIR}/10-vllm.yaml" ;;
        qdrant) echo "${MANIFESTS_DIR}/11-qdrant.yaml" ;;
        comfyui) echo "${MANIFESTS_DIR}/12-comfyui.yaml" ;;
        vlm) echo "${MANIFESTS_DIR}/13-vlm.yaml" ;;
        rustfs) echo "${MANIFESTS_DIR}/14-rustfs.yaml" ;;
        *) echo "" ;;
    esac
}

# 상태 표시
show_status() {
    echo ""
    echo -e "${CYAN}=============================================="
    echo "       K3s 워크로드 상태"
    echo "==============================================${NC}"
    echo ""

    # GPU 상태
    echo -e "${YELLOW}📊 GPU 사용 현황:${NC}"
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null | \
            while read line; do
                echo "   $line"
            done
    else
        echo "   nvidia-smi를 찾을 수 없습니다"
    fi
    echo ""

    # K8s 노드 GPU 리소스
    echo -e "${YELLOW}📦 K8s GPU 리소스:${NC}"
    GPU_ALLOC=$(kubectl get nodes -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}' 2>/dev/null || echo "N/A")
    GPU_USED=$(kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].resources.limits.nvidia\.com/gpu}{"\n"}{end}' 2>/dev/null | grep -v '^$' | awk '{sum+=$1} END {print sum+0}')
    echo "   할당 가능: ${GPU_ALLOC} GPU"
    echo "   사용 중: ${GPU_USED} GPU"
    echo ""

    # 서비스 상태
    echo -e "${YELLOW}🚀 서비스 상태:${NC}"
    echo ""

    printf "   %-12s %-12s %-8s %-6s %s\n" "서비스" "상태" "Pod" "GPU" "엔드포인트"
    printf "   %-12s %-12s %-8s %-6s %s\n" "------" "------" "------" "----" "----------"

    for svc in "${ALL_SERVICES[@]}"; do
        ns=$(get_namespace $svc)

        # Deployment 상태 확인
        replicas=$(kubectl get deployment $svc -n $ns -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
        ready=$(kubectl get deployment $svc -n $ns -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

        if [ "$replicas" = "0" ] || [ -z "$replicas" ]; then
            status="${RED}Stopped${NC}"
            pod_status="-"
        else
            if [ "$ready" = "$replicas" ]; then
                status="${GREEN}Running${NC}"
                pod_status="${ready}/${replicas}"
            else
                status="${YELLOW}Starting${NC}"
                pod_status="${ready}/${replicas}"
            fi
        fi

        # GPU 사용량
        if [[ " ${GPU_SERVICES[@]} " =~ " ${svc} " ]]; then
            gpu_limit=$(kubectl get deployment $svc -n $ns -o jsonpath='{.spec.template.spec.containers[0].resources.limits.nvidia\.com/gpu}' 2>/dev/null || echo "0")
            if [ "$replicas" != "0" ] && [ -n "$replicas" ]; then
                gpu="${gpu_limit}"
            else
                gpu="-"
            fi
        else
            gpu="-"
        fi

        # 엔드포인트
        case $svc in
            vllm) endpoint="vllm.local:8000" ;;
            qdrant) endpoint="qdrant.local:6333" ;;
            comfyui) endpoint="comfyui.local:8188" ;;
            vlm) endpoint="vlm.local:8001" ;;
            rustfs) endpoint="s3.local:9000" ;;
        esac

        printf "   %-12s %-20b %-8s %-6s %s\n" "$svc" "$status" "$pod_status" "$gpu" "$endpoint"
    done

    echo ""

    # 노드 리소스
    echo -e "${YELLOW}💾 노드 리소스:${NC}"
    kubectl top node 2>/dev/null || echo "   메트릭 서버가 없습니다 (kubectl top 사용 불가)"
    echo ""
}

# 서비스 시작
start_service() {
    local svc=$1
    local ns=$(get_namespace $svc)
    local manifest=$(get_manifest $svc)

    if [ -z "$manifest" ]; then
        echo -e "${RED}[ERROR]${NC} 알 수 없는 서비스: $svc"
        return 1
    fi

    echo -e "${BLUE}[INFO]${NC} $svc 서비스 시작 중..."

    # 이미 실행 중인지 확인
    replicas=$(kubectl get deployment $svc -n $ns -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
    if [ "$replicas" != "0" ] && [ -n "$replicas" ]; then
        echo -e "${YELLOW}[WARN]${NC} $svc 서비스가 이미 실행 중입니다"
        return 0
    fi

    # 매니페스트 적용
    kubectl apply -f $manifest

    echo -e "${GREEN}[SUCCESS]${NC} $svc 서비스 시작됨"
    echo ""
    echo "상태 확인: ./workload.sh status"
    echo "로그 확인: ./workload.sh logs $svc"
}

# 서비스 중지
stop_service() {
    local svc=$1
    local ns=$(get_namespace $svc)

    echo -e "${BLUE}[INFO]${NC} $svc 서비스 중지 중..."

    # Deployment 스케일 다운
    kubectl scale deployment $svc -n $ns --replicas=0 2>/dev/null || {
        echo -e "${YELLOW}[WARN]${NC} $svc 서비스를 찾을 수 없습니다"
        return 0
    }

    echo -e "${GREEN}[SUCCESS]${NC} $svc 서비스 중지됨"
}

# 서비스 재시작
restart_service() {
    local svc=$1
    local ns=$(get_namespace $svc)

    echo -e "${BLUE}[INFO]${NC} $svc 서비스 재시작 중..."

    kubectl rollout restart deployment $svc -n $ns 2>/dev/null || {
        echo -e "${YELLOW}[WARN]${NC} $svc 서비스를 찾을 수 없습니다. 시작합니다..."
        start_service $svc
        return
    }

    echo -e "${GREEN}[SUCCESS]${NC} $svc 서비스 재시작됨"
}

# 서비스 로그
show_logs() {
    local svc=$1
    local ns=$(get_namespace $svc)

    echo -e "${BLUE}[INFO]${NC} $svc 서비스 로그:"
    kubectl logs -n $ns -l app=$svc --tail=100 -f 2>/dev/null || {
        echo -e "${YELLOW}[WARN]${NC} $svc 서비스 Pod를 찾을 수 없습니다"
    }
}

# GPU 서비스 전환 (다른 GPU 서비스 끄고 지정된 서비스만 켜기)
switch_service() {
    local target=$1

    if [[ ! " ${GPU_SERVICES[@]} " =~ " ${target} " ]]; then
        echo -e "${RED}[ERROR]${NC} $target 은(는) GPU 서비스가 아닙니다"
        echo "GPU 서비스: ${GPU_SERVICES[*]}"
        return 1
    fi

    echo -e "${BLUE}[INFO]${NC} GPU 서비스를 $target (으)로 전환합니다..."
    echo ""

    # 다른 GPU 서비스 중지
    for svc in "${GPU_SERVICES[@]}"; do
        if [ "$svc" != "$target" ]; then
            local ns=$(get_namespace $svc)
            replicas=$(kubectl get deployment $svc -n $ns -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
            if [ "$replicas" != "0" ] && [ -n "$replicas" ]; then
                echo -e "  ${YELLOW}중지:${NC} $svc"
                stop_service $svc
            fi
        fi
    done

    # 대상 서비스 시작
    echo -e "  ${GREEN}시작:${NC} $target"
    start_service $target

    echo ""
    echo -e "${GREEN}[SUCCESS]${NC} GPU 서비스가 $target (으)로 전환되었습니다"
}

# GPU 상태만 표시
show_gpu() {
    echo ""
    echo -e "${CYAN}=============================================="
    echo "       GPU 사용 현황"
    echo "==============================================${NC}"
    echo ""

    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi
    else
        echo "nvidia-smi를 찾을 수 없습니다"
    fi

    echo ""
    echo -e "${YELLOW}K8s GPU Pod:${NC}"
    kubectl get pods -A -o custom-columns='NAMESPACE:.metadata.namespace,NAME:.metadata.name,GPU:.spec.containers[*].resources.limits.nvidia\.com/gpu,STATUS:.status.phase' 2>/dev/null | grep -v '<none>' | grep -v '^$' || echo "  GPU를 사용하는 Pod가 없습니다"
    echo ""
}

# 초기 설정 (네임스페이스, 스토리지 생성)
init_setup() {
    echo -e "${BLUE}[INFO]${NC} 초기 설정 시작..."

    # 네임스페이스 생성
    echo -e "${BLUE}[INFO]${NC} 네임스페이스 생성 중..."
    kubectl apply -f ${MANIFESTS_DIR}/00-namespace.yaml

    # 스토리지 생성
    echo -e "${BLUE}[INFO]${NC} 스토리지(PV/PVC) 생성 중..."
    kubectl apply -f ${MANIFESTS_DIR}/01-storage.yaml

    echo ""
    echo -e "${GREEN}[SUCCESS]${NC} 초기 설정 완료!"
    echo ""
    echo "스토리지 상태:"
    kubectl get pv,pvc -A
    echo ""
    echo "서비스 시작: ./workload.sh start <서비스명>"
    echo "예: ./workload.sh start qdrant"
}

# 전체 서비스 시작
start_all() {
    echo -e "${BLUE}[INFO]${NC} 전체 서비스 시작..."

    # CPU 서비스 먼저 시작
    for svc in "${CPU_SERVICES[@]}"; do
        start_service $svc
    done

    # GPU 서비스는 경고 메시지 출력
    echo ""
    echo -e "${YELLOW}[WARN]${NC} GPU 서비스들(vllm, comfyui, vlm)은 동시에 실행하면 GPU 메모리가 부족할 수 있습니다."
    echo "수동으로 필요한 GPU 서비스만 시작하세요:"
    echo "  ./workload.sh start vllm     # 70B LLM 서빙"
    echo "  ./workload.sh start comfyui  # 이미지 생성"
    echo "  ./workload.sh start vlm      # 비전 언어 모델"
    echo ""
    echo "또는 전환 명령어 사용:"
    echo "  ./workload.sh switch vllm    # 다른 GPU 서비스 끄고 vllm만 켜기"
}

# 전체 서비스 중지
stop_all() {
    echo -e "${BLUE}[INFO]${NC} 전체 서비스 중지..."

    for svc in "${ALL_SERVICES[@]}"; do
        stop_service $svc
    done

    echo ""
    echo -e "${GREEN}[SUCCESS]${NC} 전체 서비스 중지됨"
}

# 도움말
show_help() {
    echo ""
    echo "K3s 워크로드 관리 스크립트"
    echo ""
    echo "사용법: ./workload.sh <명령> [서비스]"
    echo ""
    echo "명령어:"
    echo "  status              전체 상태 확인"
    echo "  start <서비스>       서비스 시작"
    echo "  stop <서비스>        서비스 중지"
    echo "  restart <서비스>     서비스 재시작"
    echo "  logs <서비스>        서비스 로그 확인 (Ctrl+C로 종료)"
    echo "  switch <서비스>      다른 GPU 서비스 끄고 해당 서비스만 켜기"
    echo "  gpu                 GPU 사용 현황"
    echo "  init                초기 설정 (네임스페이스, 스토리지)"
    echo ""
    echo "서비스 목록:"
    echo "  GPU 서비스: ${GPU_SERVICES[*]}"
    echo "  CPU 서비스: ${CPU_SERVICES[*]}"
    echo "  all - 전체 서비스"
    echo ""
    echo "예시:"
    echo "  ./workload.sh init            # 최초 설정"
    echo "  ./workload.sh start qdrant    # Qdrant 시작"
    echo "  ./workload.sh switch vllm     # vLLM으로 전환"
    echo "  ./workload.sh logs comfyui    # ComfyUI 로그 확인"
    echo ""
}

# 메인
case "${1:-}" in
    status|s)
        show_status
        ;;
    start)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}[ERROR]${NC} 서비스명을 지정하세요"
            echo "예: ./workload.sh start vllm"
            exit 1
        fi
        if [ "$2" = "all" ]; then
            start_all
        else
            start_service "$2"
        fi
        ;;
    stop)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}[ERROR]${NC} 서비스명을 지정하세요"
            exit 1
        fi
        if [ "$2" = "all" ]; then
            stop_all
        else
            stop_service "$2"
        fi
        ;;
    restart)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}[ERROR]${NC} 서비스명을 지정하세요"
            exit 1
        fi
        restart_service "$2"
        ;;
    logs|log)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}[ERROR]${NC} 서비스명을 지정하세요"
            exit 1
        fi
        show_logs "$2"
        ;;
    switch|sw)
        if [ -z "${2:-}" ]; then
            echo -e "${RED}[ERROR]${NC} GPU 서비스명을 지정하세요"
            echo "GPU 서비스: ${GPU_SERVICES[*]}"
            exit 1
        fi
        switch_service "$2"
        ;;
    gpu|g)
        show_gpu
        ;;
    init|i)
        init_setup
        ;;
    help|h|-h|--help)
        show_help
        ;;
    *)
        show_status
        ;;
esac
