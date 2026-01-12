#!/bin/bash
#===============================================================================
# K3s GPU 런타임 설정 스크립트
#
# 사용법: sudo ./setup-gpu-runtime.sh
#
# 이 스크립트는 K3s containerd를 NVIDIA 런타임으로 설정합니다.
#===============================================================================

set -e

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

log_info "K3s containerd GPU 런타임 설정 중..."

# K3s containerd 설정 디렉토리 생성
mkdir -p /var/lib/rancher/k3s/agent/etc/containerd

# containerd 설정 템플릿 생성 (runc도 유지)
cat > /var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl << 'EOF'
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
  runtime_type = "io.containerd.runc.v2"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
  SystemdCgroup = true

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
  privileged_without_host_devices = false
  runtime_type = "io.containerd.runc.v2"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
  BinaryName = "/usr/bin/nvidia-container-runtime"
  SystemdCgroup = true
EOF

log_success "containerd 설정 파일 생성됨"

# K3s 서비스 재시작
log_info "K3s 서비스 재시작 중..."
systemctl restart k3s

# 노드가 Ready 상태가 될 때까지 대기
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
log_info "노드가 Ready 상태가 될 때까지 대기 중..."

MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    STATUS=$(kubectl get nodes -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
    if [ "$STATUS" = "True" ]; then
        log_success "노드가 Ready 상태입니다"
        break
    fi
    echo -n "."
    sleep 5
    WAITED=$((WAITED + 5))
done
echo ""

if [ $WAITED -ge $MAX_WAIT ]; then
    log_warn "노드가 Ready 상태가 아닙니다. 계속 진행합니다..."
    kubectl get nodes
fi

# RuntimeClass 생성
log_info "NVIDIA RuntimeClass 생성 중..."
kubectl apply -f - << 'RUNTIMECLASS'
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
handler: nvidia
RUNTIMECLASS

# Device Plugin DaemonSet 재배포
log_info "NVIDIA Device Plugin 배포 중..."
kubectl delete daemonset -n kube-system nvidia-device-plugin-daemonset --ignore-not-found 2>/dev/null || true
sleep 5

kubectl apply -f - << 'DAEMONSET'
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
      runtimeClassName: nvidia
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
DAEMONSET

# Device Plugin Pod가 생성될 때까지 대기
log_info "Device Plugin Pod 생성 대기 중..."
sleep 10

MAX_WAIT=90
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    POD_STATUS=$(kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")
    if [ "$POD_STATUS" = "Running" ]; then
        log_success "Device Plugin Pod가 Running 상태입니다"
        break
    fi
    echo -n "."
    sleep 5
    WAITED=$((WAITED + 5))
done
echo ""

# GPU 리소스 확인 대기
log_info "GPU 리소스 등록 대기 중..."
sleep 20

echo ""
echo "=============================================="
echo "       GPU 설정 완료!"
echo "=============================================="
echo ""

echo "📊 노드 상태:"
kubectl get nodes
echo ""

echo "📦 NVIDIA Device Plugin 상태:"
kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds
echo ""

# GPU 리소스 확인
GPU_COUNT=$(kubectl get nodes -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}' 2>/dev/null || echo "")
if [ -n "$GPU_COUNT" ] && [ "$GPU_COUNT" != "0" ]; then
    log_success "GPU ${GPU_COUNT}개가 K8s에서 사용 가능합니다!"
else
    echo ""
    log_warn "GPU가 아직 표시되지 않습니다."
    log_info "Device Plugin 로그 확인:"
    kubectl logs -n kube-system -l name=nvidia-device-plugin-ds --tail=30 2>/dev/null || echo "  로그를 가져올 수 없습니다"
fi
echo ""
