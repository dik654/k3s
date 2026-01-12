#!/bin/bash
#
# 로컬 개발 환경 실행 스크립트
#
# 사용법: ./scripts/dev-local.sh
#
# 기능:
# 1. Fleet 및 기타 서비스 포트포워딩 설정
# 2. 백엔드 FastAPI 서버 실행 (uvicorn --reload)
# 3. 프론트엔드 Vite 개발 서버 실행
# 4. 종료 시 모든 백그라운드 프로세스 정리

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 스크립트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/dashboard/backend"
FRONTEND_DIR="$PROJECT_ROOT/dashboard/frontend"

# PID 파일
PID_FILE="/tmp/k3s-dev-local-pids"

# 로그 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 정리 함수 - 종료 시 모든 백그라운드 프로세스 정리
cleanup() {
    log_info "개발 환경 종료 중..."

    # 저장된 PID들 종료
    if [[ -f "$PID_FILE" ]]; then
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                log_info "프로세스 종료: $pid"
                kill "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi

    # kubectl port-forward 프로세스 종료
    pkill -f "kubectl port-forward" 2>/dev/null || true

    log_success "정리 완료"
}

# 종료 시 정리 함수 실행
trap cleanup EXIT INT TERM

# PID 저장 함수
save_pid() {
    echo "$1" >> "$PID_FILE"
}

# 의존성 확인
check_dependencies() {
    log_info "의존성 확인 중..."

    local deps=("kubectl" "python3" "node" "npm")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "$dep 이 설치되어 있지 않습니다."
            exit 1
        fi
    done

    # kubectl 연결 확인
    if ! kubectl cluster-info &> /dev/null; then
        log_error "kubectl로 클러스터에 연결할 수 없습니다. ~/.kube/config를 확인하세요."
        exit 1
    fi

    # Python 패키지 확인 및 설치
    log_info "Python 패키지 확인 중..."
    cd "$BACKEND_DIR"
    if ! python3 -c "import uvicorn" &> /dev/null; then
        log_warn "uvicorn이 설치되어 있지 않습니다. 설치 중..."
        pip3 install -r requirements.txt
    fi

    log_success "모든 의존성 확인 완료"
}

# 포트포워딩 설정
setup_port_forwarding() {
    log_info "서비스 포트포워딩 설정 중..."

    # Fleet API 포트포워딩 (있는 경우)
    if kubectl get svc -n cattle-fleet-system fleet-controller &> /dev/null; then
        log_info "Fleet API 포트포워딩 설정 (8081)"
        kubectl port-forward -n cattle-fleet-system svc/fleet-controller 8081:8080 &> /dev/null &
        save_pid $!
    else
        log_warn "Fleet 서비스를 찾을 수 없습니다. 포트포워딩 건너뜀."
    fi

    # vLLM 포트포워딩 (선택)
    if kubectl get svc -n llm vllm &> /dev/null; then
        log_info "vLLM 포트포워딩 설정 (8001)"
        kubectl port-forward -n llm svc/vllm 8001:8000 &> /dev/null &
        save_pid $!
    fi

    # Qdrant 포트포워딩 (선택)
    if kubectl get svc -n qdrant qdrant &> /dev/null; then
        log_info "Qdrant 포트포워딩 설정 (6333)"
        kubectl port-forward -n qdrant svc/qdrant 6333:6333 &> /dev/null &
        save_pid $!
    fi

    # Neo4j 포트포워딩 (선택)
    if kubectl get svc -n neo4j neo4j &> /dev/null; then
        log_info "Neo4j 포트포워딩 설정 (7687, 7474)"
        kubectl port-forward -n neo4j svc/neo4j 7687:7687 7474:7474 &> /dev/null &
        save_pid $!
    fi

    # MinIO 포트포워딩 (선택)
    if kubectl get svc -n minio minio &> /dev/null; then
        log_info "MinIO 포트포워딩 설정 (9000, 9001)"
        kubectl port-forward -n minio svc/minio 9000:9000 9001:9001 &> /dev/null &
        save_pid $!
    fi

    sleep 2  # 포트포워딩 안정화 대기
    log_success "포트포워딩 설정 완료"
}

# 백엔드 실행
start_backend() {
    log_info "백엔드 서버 시작 중..."

    cd "$BACKEND_DIR"

    # 환경 변수 설정
    export ENV=development
    export LOG_LEVEL=debug
    export CORS_ORIGINS="http://localhost:5173,http://localhost:3000"

    # .env.development 파일이 있으면 로드
    if [[ -f ".env.development" ]]; then
        log_info ".env.development 파일 로드"
        set -a
        source .env.development
        set +a
    fi

    # uvicorn 실행 (--reload 모드)
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    save_pid $!

    log_success "백엔드 서버 시작됨 (http://localhost:8000)"
}

# 프론트엔드 실행
start_frontend() {
    log_info "프론트엔드 서버 시작 중..."

    cd "$FRONTEND_DIR"

    # node_modules 확인
    if [[ ! -d "node_modules" ]]; then
        log_info "npm install 실행 중..."
        npm install
    fi

    # Vite 개발 서버 실행 (--host로 외부 접속 허용)
    npx vite --host 0.0.0.0 --port 5173 &
    save_pid $!

    # 로컬 IP 가져오기
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    log_success "프론트엔드 서버 시작됨 (http://localhost:5173, http://${LOCAL_IP}:5173)"
}

# 상태 표시
show_status() {
    # 로컬 IP 가져오기
    LOCAL_IP=$(hostname -I | awk '{print $1}')

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  로컬 개발 환경 실행 중${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "  ${BLUE}프론트엔드:${NC}"
    echo -e "    - http://localhost:5173"
    echo -e "    - http://${LOCAL_IP}:5173  (외부 접속)"
    echo ""
    echo -e "  ${BLUE}백엔드 API:${NC}"
    echo -e "    - http://localhost:8000"
    echo -e "    - http://${LOCAL_IP}:8000  (외부 접속)"
    echo ""
    echo -e "  ${BLUE}API 문서:${NC}   http://${LOCAL_IP}:8000/docs"
    echo ""
    echo -e "  ${YELLOW}포트포워딩 (가능한 경우):${NC}"
    echo -e "    - Fleet API:  localhost:8081"
    echo -e "    - vLLM:       localhost:8001"
    echo -e "    - Qdrant:     localhost:6333"
    echo -e "    - Neo4j:      localhost:7687 (bolt), :7474 (http)"
    echo -e "    - MinIO:      localhost:9000 (api), :9001 (console)"
    echo ""
    echo -e "  ${RED}종료하려면 Ctrl+C를 누르세요${NC}"
    echo ""
}

# 메인 실행
main() {
    log_info "로컬 개발 환경 시작..."

    # 기존 PID 파일 정리
    rm -f "$PID_FILE"

    # 의존성 확인
    check_dependencies

    # 포트포워딩 설정
    setup_port_forwarding

    # 백엔드 시작
    start_backend

    # 프론트엔드 시작
    start_frontend

    # 상태 표시
    show_status

    # 프로세스 대기 (Ctrl+C까지)
    wait
}

# 실행
main "$@"
