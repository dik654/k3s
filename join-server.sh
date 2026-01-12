#!/bin/bash
#===============================================================================
# K3s 노드 조인 서버
#
# 마스터에서 실행하면 HTTP 서버가 시작되고,
# 새 서버에서 curl로 바로 K3s를 설치할 수 있습니다.
#
# 사용법:
#   마스터에서: ./join-server.sh start
#   새 서버에서: curl -sfL http://<마스터IP>:9999/join/gpu | sudo bash
#
# 명령:
#   start     - 조인 서버 시작 (포그라운드)
#   start-bg  - 조인 서버 백그라운드 시작
#   stop      - 조인 서버 중지
#   status    - 상태 확인
#   show      - 조인 명령어 출력
#===============================================================================

set -e

# 설정
PORT=9999
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="${SCRIPT_DIR}/.join-server.pid"
LOG_FILE="${SCRIPT_DIR}/join-server.log"

# 마스터 IP 자동 감지
MASTER_IP=$(hostname -I | awk '{print $1}')

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 토큰 확인
get_token() {
    local token_file="/var/lib/rancher/k3s/server/node-token"
    if [ -f "$token_file" ]; then
        cat "$token_file"
    elif [ -f "${SCRIPT_DIR}/tokens/node-token" ]; then
        cat "${SCRIPT_DIR}/tokens/node-token"
    else
        echo ""
    fi
}

# 설치 스크립트 생성
generate_install_script() {
    local node_type=$1
    local token=$(get_token)

    if [ -z "$token" ]; then
        echo "echo 'ERROR: K3s 토큰을 찾을 수 없습니다. 마스터가 설치되어 있는지 확인하세요.'; exit 1"
        return
    fi

    cat << SCRIPT
#!/bin/bash
#===============================================================================
# K3s ${node_type^^} Worker 자동 설치 스크립트
# 마스터: ${MASTER_IP}
# 생성시간: $(date)
#===============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "\${BLUE}=============================================="
echo "   K3s ${node_type^^} Worker 자동 설치"
echo "=============================================\${NC}"
echo ""
echo "마스터 서버: ${MASTER_IP}"
echo "노드 타입: ${node_type}"
echo ""

# Root 확인
if [ "\$EUID" -ne 0 ]; then
    echo -e "\${RED}[ERROR] root 권한이 필요합니다: sudo bash\${NC}"
    exit 1
fi

# 이미 설치 확인
if command -v k3s &> /dev/null; then
    echo -e "\${YELLOW}[WARN] K3s가 이미 설치되어 있습니다.\${NC}"
    read -p "계속 진행하시겠습니까? (y/n): " confirm
    if [ "\$confirm" != "y" ]; then
        echo "취소되었습니다."
        exit 0
    fi
fi

echo -e "\${BLUE}[1/4] 시스템 준비 중...\${NC}"

# 필수 패키지
apt-get update -qq
apt-get install -y -qq curl wget ca-certificates

# 스왑 비활성화
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

# 커널 모듈
cat > /etc/modules-load.d/k3s.conf << EOF
br_netfilter
overlay
EOF
modprobe br_netfilter 2>/dev/null || true
modprobe overlay 2>/dev/null || true

# sysctl
cat > /etc/sysctl.d/k3s.conf << EOF
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF
sysctl --system > /dev/null 2>&1

echo -e "\${GREEN}[OK] 시스템 준비 완료\${NC}"

# GPU 노드인 경우 확인
SCRIPT

    if [ "$node_type" = "gpu" ]; then
        cat << 'SCRIPT'
echo -e "${BLUE}[2/4] GPU 환경 확인 중...${NC}"

GPU_LABELS=""
if command -v nvidia-smi &> /dev/null; then
    GPU_TYPE=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g' | sed 's/nvidia-geforce-//' )
    GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
    echo -e "${GREEN}[OK] GPU 감지: ${GPU_TYPE} x ${GPU_COUNT}${NC}"
    GPU_LABELS=",gpu-type=${GPU_TYPE},gpu-count=${GPU_COUNT}"
else
    echo -e "${YELLOW}[WARN] NVIDIA 드라이버가 없습니다. K3s 설치 후 설정하세요.${NC}"
fi

SCRIPT
    else
        echo 'echo -e "${BLUE}[2/4] 환경 확인 완료${NC}"'
        echo 'GPU_LABELS=""'
    fi

    cat << SCRIPT

echo -e "\${BLUE}[3/4] K3s Agent 설치 중...\${NC}"

NODE_NAME=\$(hostname)
NODE_IP=\$(hostname -I | awk '{print \$1}')
NODE_LABELS="node-type=${node_type}\${GPU_LABELS}"

SCRIPT

    # 노드 타입별 추가 라벨
    case $node_type in
        gpu)
            echo 'NODE_LABELS="${NODE_LABELS},gpu=true,workload-type=gpu"'
            ;;
        cpu)
            echo 'NODE_LABELS="${NODE_LABELS},cpu-optimized=true,workload-type=compute"'
            ;;
        storage)
            echo 'NODE_LABELS="${NODE_LABELS},storage=true,workload-type=storage"'
            ;;
    esac

    cat << SCRIPT

curl -sfL https://get.k3s.io | \\
    K3S_URL="https://${MASTER_IP}:6443" \\
    K3S_TOKEN="${token}" \\
    sh -s - agent \\
    --node-name "\${NODE_NAME}" \\
    --node-ip "\${NODE_IP}" \\
    --node-label "\${NODE_LABELS}"

echo -e "\${GREEN}[OK] K3s Agent 설치 완료\${NC}"

SCRIPT

    # GPU 노드인 경우 추가 설정
    if [ "$node_type" = "gpu" ]; then
        cat << 'SCRIPT'
echo -e "${BLUE}[4/4] GPU 런타임 설정 중...${NC}"

if command -v nvidia-smi &> /dev/null; then
    # NVIDIA Container Toolkit 설치
    if ! command -v nvidia-ctk &> /dev/null; then
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
            gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg 2>/dev/null
        curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
        apt-get update -qq
        apt-get install -y -qq nvidia-container-toolkit
    fi

    # containerd 기본 설정
    nvidia-ctk runtime configure --runtime=containerd --set-as-default 2>/dev/null

    # K3s Agent용 containerd 설정 (필수!)
    echo -e "${BLUE}  K3s containerd GPU 런타임 설정 중...${NC}"
    mkdir -p /var/lib/rancher/k3s/agent/etc/containerd

    cat > /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl << 'K3S_CONTAINERD_EOF'
version = 2

[plugins."io.containerd.grpc.v1.cri".containerd]
  default_runtime_name = "nvidia"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  privileged_without_host_devices = false
  runtime_engine = ""
  runtime_root = ""
  runtime_type = "io.containerd.runc.v2"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
  BinaryName = "/usr/bin/nvidia-container-runtime"
  SystemdCgroup = true
K3S_CONTAINERD_EOF

    # K3s Agent 재시작
    echo -e "${BLUE}  K3s Agent 재시작 중...${NC}"
    systemctl restart k3s-agent
    sleep 10

    if systemctl is-active --quiet k3s-agent; then
        echo -e "${GREEN}[OK] GPU 런타임 설정 완료${NC}"
    else
        echo -e "${YELLOW}[WARN] K3s Agent 시작 확인 필요${NC}"
    fi
else
    echo -e "${YELLOW}[SKIP] NVIDIA 드라이버 없음${NC}"
fi
SCRIPT
    else
        echo 'echo -e "${GREEN}[4/4] 완료${NC}"'
    fi

    cat << SCRIPT

echo ""
echo -e "\${GREEN}=============================================="
echo "   설치 완료!"
echo "=============================================\${NC}"
echo ""
echo "노드 이름: \${NODE_NAME}"
echo "노드 IP: \${NODE_IP}"
echo "노드 타입: ${node_type}"
echo ""
echo "마스터에서 확인: kubectl get nodes"
echo ""
SCRIPT
}

# HA 마스터 스크립트 생성
generate_master_script() {
    local token=$(get_token)

    if [ -z "$token" ]; then
        echo "echo 'ERROR: K3s 토큰을 찾을 수 없습니다.'; exit 1"
        return
    fi

    cat << SCRIPT
#!/bin/bash
set -e

echo ""
echo "=============================================="
echo "   K3s HA 마스터 노드 설치"
echo "=============================================="
echo ""

if [ "\$EUID" -ne 0 ]; then
    echo "[ERROR] root 권한 필요: sudo bash"
    exit 1
fi

# 시스템 준비
apt-get update -qq
apt-get install -y -qq curl wget ca-certificates
swapoff -a

NODE_NAME=\$(hostname)
NODE_IP=\$(hostname -I | awk '{print \$1}')

curl -sfL https://get.k3s.io | \\
    K3S_URL="https://${MASTER_IP}:6443" \\
    K3S_TOKEN="${token}" \\
    sh -s - server \\
    --node-name "\${NODE_NAME}" \\
    --node-ip "\${NODE_IP}" \\
    --tls-san "\${NODE_IP}"

echo ""
echo "HA 마스터 설치 완료!"
echo "확인: kubectl get nodes"
SCRIPT
}

# HTML 페이지 생성
generate_html() {
    cat << 'HTML'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>K3s 클러스터 조인</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 40px 20px;
            color: #fff;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { text-align: center; font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 40px; }
        .card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        .card:hover {
            background: rgba(255,255,255,0.1);
            transform: translateY(-2px);
        }
        .card h2 {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        .icon { font-size: 2em; }
        .desc { color: #aaa; margin-bottom: 20px; }
        .cmd {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px 20px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            overflow-x: auto;
            position: relative;
        }
        .cmd code { color: #58a6ff; }
        .copy-btn {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            background: #238636;
            color: #fff;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
        }
        .copy-btn:hover { background: #2ea043; }
        .labels { margin-top: 15px; }
        .label {
            display: inline-block;
            background: rgba(88, 166, 255, 0.2);
            color: #58a6ff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-right: 8px;
        }
        .footer { text-align: center; margin-top: 40px; color: #666; }
HTML
    echo "        .master-ip { color: #f0883e; }"
    echo "    </style>"
    echo "</head>"
    echo "<body>"
    echo "    <div class=\"container\">"
    echo "        <h1>🚀 K3s 클러스터 조인</h1>"
    echo "        <p class=\"subtitle\">마스터: <span class=\"master-ip\">${MASTER_IP}</span></p>"
    cat << 'HTML'

        <div class="card">
            <h2><span class="icon">🎮</span> GPU Worker</h2>
            <p class="desc">NVIDIA GPU가 있는 서버. ML/AI 워크로드용.</p>
            <div class="cmd">
HTML
    echo "                <code>curl -sfL http://${MASTER_IP}:${PORT}/join/gpu | sudo bash</code>"
    cat << 'HTML'
                <button class="copy-btn" onclick="copy(this)">복사</button>
            </div>
            <div class="labels">
                <span class="label">node-type=gpu</span>
                <span class="label">gpu=true</span>
                <span class="label">자동 GPU 감지</span>
            </div>
        </div>

        <div class="card">
            <h2><span class="icon">🖥️</span> CPU Worker</h2>
            <p class="desc">CPU 연산 전용 서버. 일반 워크로드용.</p>
            <div class="cmd">
HTML
    echo "                <code>curl -sfL http://${MASTER_IP}:${PORT}/join/cpu | sudo bash</code>"
    cat << 'HTML'
                <button class="copy-btn" onclick="copy(this)">복사</button>
            </div>
            <div class="labels">
                <span class="label">node-type=cpu</span>
                <span class="label">cpu-optimized=true</span>
            </div>
        </div>

        <div class="card">
            <h2><span class="icon">💾</span> Storage Worker</h2>
            <p class="desc">스토리지 전용 서버. 대용량 디스크 노드.</p>
            <div class="cmd">
HTML
    echo "                <code>curl -sfL http://${MASTER_IP}:${PORT}/join/storage | sudo bash</code>"
    cat << 'HTML'
                <button class="copy-btn" onclick="copy(this)">복사</button>
            </div>
            <div class="labels">
                <span class="label">node-type=storage</span>
                <span class="label">storage=true</span>
            </div>
        </div>

        <div class="card">
            <h2><span class="icon">👑</span> HA 마스터</h2>
            <p class="desc">추가 마스터 노드. HA 구성용 (3대 권장).</p>
            <div class="cmd">
HTML
    echo "                <code>curl -sfL http://${MASTER_IP}:${PORT}/join/master | sudo bash</code>"
    cat << 'HTML'
                <button class="copy-btn" onclick="copy(this)">복사</button>
            </div>
            <div class="labels">
                <span class="label">control-plane</span>
                <span class="label">etcd</span>
            </div>
        </div>

        <p class="footer">K3s Join Server | 토큰이 자동으로 포함됩니다</p>
    </div>
    <script>
        function copy(btn) {
            const code = btn.parentElement.querySelector('code').textContent;
            navigator.clipboard.writeText(code);
            btn.textContent = '복사됨!';
            setTimeout(() => btn.textContent = '복사', 2000);
        }
    </script>
</body>
</html>
HTML
}

# HTTP 서버 시작
start_server() {
    local token=$(get_token)

    if [ -z "$token" ]; then
        log_error "K3s 토큰을 찾을 수 없습니다."
        log_error "먼저 마스터를 설치하세요: sudo ./01-install-master.sh"
        exit 1
    fi

    log_info "K3s 조인 서버 시작 중..."
    log_info "포트: ${PORT}"
    log_info "마스터 IP: ${MASTER_IP}"
    echo ""

    # Python HTTP 서버 실행
    python3 << PYEOF
import http.server
import socketserver
import subprocess

PORT = ${PORT}
MASTER_IP = "${MASTER_IP}"

class JoinHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.client_address[0]}] {args[0]}")

    def do_GET(self):
        path = self.path.rstrip('/')

        if path == '' or path == '/':
            # HTML 페이지
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = subprocess.check_output(['bash', '-c', 'source ${SCRIPT_DIR}/join-server.sh && generate_html'])
            self.wfile.write(html)

        elif path == '/join/gpu':
            self.send_script('gpu')
        elif path == '/join/cpu':
            self.send_script('cpu')
        elif path == '/join/storage':
            self.send_script('storage')
        elif path == '/join/master':
            self.send_script('master')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def send_script(self, node_type):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()

        if node_type == 'master':
            script = subprocess.check_output(['bash', '-c', 'source ${SCRIPT_DIR}/join-server.sh && generate_master_script'])
        else:
            script = subprocess.check_output(['bash', '-c', f'source ${SCRIPT_DIR}/join-server.sh && generate_install_script {node_type}'])
        self.wfile.write(script)

with socketserver.TCPServer(("", PORT), JoinHandler) as httpd:
    print(f"""
============================================
  K3s 조인 서버 실행 중
============================================

  URL: http://{MASTER_IP}:{PORT}

  새 서버에서 실행:
    GPU:     curl -sfL http://{MASTER_IP}:{PORT}/join/gpu | sudo bash
    CPU:     curl -sfL http://{MASTER_IP}:{PORT}/join/cpu | sudo bash
    Storage: curl -sfL http://{MASTER_IP}:{PORT}/join/storage | sudo bash
    Master:  curl -sfL http://{MASTER_IP}:{PORT}/join/master | sudo bash

  종료: Ctrl+C
============================================
""")
    httpd.serve_forever()
PYEOF
}

# 백그라운드 시작
start_background() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        log_warn "조인 서버가 이미 실행 중입니다. (PID: $(cat $PID_FILE))"
        exit 1
    fi

    log_info "조인 서버를 백그라운드에서 시작합니다..."

    nohup "$0" start > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    sleep 2

    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        log_success "조인 서버 시작됨 (PID: $(cat $PID_FILE))"
        echo ""
        show_commands
    else
        log_error "조인 서버 시작 실패. 로그 확인: $LOG_FILE"
        exit 1
    fi
}

# 서버 중지
stop_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            rm -f "$PID_FILE"
            log_success "조인 서버 중지됨"
        else
            rm -f "$PID_FILE"
            log_warn "프로세스가 이미 종료됨"
        fi
    else
        log_warn "실행 중인 조인 서버가 없습니다."
    fi
}

# 상태 확인
show_status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        log_success "조인 서버 실행 중 (PID: $(cat $PID_FILE))"
        echo ""
        show_commands
    else
        log_warn "조인 서버가 실행되고 있지 않습니다."
        echo ""
        echo "시작하려면: $0 start"
    fi
}

# 명령어 출력
show_commands() {
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  새 서버에서 실행할 명령어${NC}"
    echo -e "${CYAN}============================================${NC}"
    echo ""
    echo -e "  ${GREEN}GPU Worker:${NC}"
    echo -e "    curl -sfL http://${MASTER_IP}:${PORT}/join/gpu | sudo bash"
    echo ""
    echo -e "  ${BLUE}CPU Worker:${NC}"
    echo -e "    curl -sfL http://${MASTER_IP}:${PORT}/join/cpu | sudo bash"
    echo ""
    echo -e "  ${YELLOW}Storage Worker:${NC}"
    echo -e "    curl -sfL http://${MASTER_IP}:${PORT}/join/storage | sudo bash"
    echo ""
    echo -e "  ${RED}HA Master:${NC}"
    echo -e "    curl -sfL http://${MASTER_IP}:${PORT}/join/master | sudo bash"
    echo ""
    echo -e "${CYAN}============================================${NC}"
    echo ""
    echo "  웹 UI: http://${MASTER_IP}:${PORT}"
    echo ""
}

# 도움말
show_help() {
    echo "K3s 노드 조인 서버"
    echo ""
    echo "사용법: $0 <명령>"
    echo ""
    echo "명령:"
    echo "  start      조인 서버 시작 (포그라운드)"
    echo "  start-bg   조인 서버 백그라운드 시작"
    echo "  stop       조인 서버 중지"
    echo "  status     상태 확인"
    echo "  show       조인 명령어 출력"
    echo "  -h, --help 도움말"
    echo ""
}

# 메인
case "${1:-}" in
    start)
        start_server
        ;;
    start-bg)
        start_background
        ;;
    stop)
        stop_server
        ;;
    status)
        show_status
        ;;
    show)
        show_commands
        ;;
    -h|--help)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
