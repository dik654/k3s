#!/bin/bash
#===============================================================================
# K3s NVIDIA GPU 지원 설정 스크립트
#
# 사용법: sudo ./05-setup-nvidia-gpu.sh
#
# 기능:
# - NVIDIA Device Plugin 설치
# - GPU 리소스를 Kubernetes에서 사용 가능하게 설정
# - RuntimeClass 생성
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

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한이 필요합니다: sudo $0"
    exit 1
fi

echo ""
echo "=============================================="
echo "       K3s NVIDIA GPU 지원 설정"
echo "=============================================="
echo ""

#-----------------------------------------------
# 1. NVIDIA 드라이버 확인
#-----------------------------------------------
log_info "NVIDIA 드라이버 확인 중..."

if ! command -v nvidia-smi &> /dev/null; then
    log_error "NVIDIA 드라이버가 설치되어 있지 않습니다."
    log_error "먼저 NVIDIA 드라이버를 설치하세요."
    exit 1
fi

echo ""
nvidia-smi
echo ""

log_success "NVIDIA 드라이버 확인됨"

#-----------------------------------------------
# 2. NVIDIA Container Toolkit 설치
#-----------------------------------------------
log_info "NVIDIA Container Toolkit 설치 중..."

if ! command -v nvidia-ctk &> /dev/null; then
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

    curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

    apt-get update -qq
    apt-get install -y nvidia-container-toolkit

    log_success "NVIDIA Container Toolkit 설치 완료"
else
    log_info "NVIDIA Container Toolkit이 이미 설치되어 있습니다."
fi

#-----------------------------------------------
# 3. containerd 설정
#-----------------------------------------------
log_info "containerd 런타임 설정 중..."

nvidia-ctk runtime configure --runtime=containerd --set-as-default

# K3s containerd 설정
mkdir -p /var/lib/rancher/k3s/agent/etc/containerd

cat > /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl << 'EOF'
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
EOF

log_success "containerd 설정 완료"

#-----------------------------------------------
# 4. K3s 재시작
#-----------------------------------------------
log_info "K3s 서비스 재시작 중..."

if systemctl is-active --quiet k3s; then
    systemctl restart k3s
elif systemctl is-active --quiet k3s-agent; then
    systemctl restart k3s-agent
fi

sleep 10
log_success "K3s 서비스 재시작 완료"

#-----------------------------------------------
# 5. NVIDIA Device Plugin 설치
#-----------------------------------------------
log_info "NVIDIA Device Plugin 설치 중..."

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# RuntimeClass 생성
kubectl apply -f - << 'EOF'
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
handler: nvidia
EOF

# NVIDIA Device Plugin DaemonSet
kubectl apply -f - << 'EOF'
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin-daemonset
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin-ds
  updateStrategy:
    type: RollingUpdate
  template:
    metadata:
      labels:
        name: nvidia-device-plugin-ds
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      - key: gpu
        operator: Exists
        effect: NoSchedule
      priorityClassName: system-node-critical
      nodeSelector:
        gpu: "true"
      containers:
      - image: nvcr.io/nvidia/k8s-device-plugin:v0.14.3
        name: nvidia-device-plugin-ctr
        env:
        - name: FAIL_ON_INIT_ERROR
          value: "false"
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        volumeMounts:
        - name: device-plugin
          mountPath: /var/lib/kubelet/device-plugins
      volumes:
      - name: device-plugin
        hostPath:
          path: /var/lib/kubelet/device-plugins
EOF

log_success "NVIDIA Device Plugin 설치 완료"

#-----------------------------------------------
# 6. 설치 확인
#-----------------------------------------------
echo ""
log_info "GPU 리소스 확인을 위해 잠시 대기 중..."
sleep 30

echo ""
echo "=============================================="
echo "       설치 완료!"
echo "=============================================="
echo ""

echo "📊 노드 GPU 리소스:"
kubectl describe nodes | grep -A 5 "Allocated resources" | grep nvidia || echo "  (아직 준비 중...)"
echo ""

echo "📦 NVIDIA Device Plugin 상태:"
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds
echo ""

log_success "NVIDIA GPU 지원 설정이 완료되었습니다!"
echo ""
echo "GPU Pod 테스트:"
echo "  kubectl run gpu-test --rm -it --restart=Never \\"
echo "    --image=nvcr.io/nvidia/cuda:12.0.0-base-ubuntu22.04 \\"
echo "    --limits=nvidia.com/gpu=1 -- nvidia-smi"
echo ""
