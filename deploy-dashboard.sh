#!/bin/bash
# K3s Dashboard 배포 스크립트
# 실행: sudo ./deploy-dashboard.sh

set -e

echo "=== K3s Dashboard 배포 ==="

# 1. Docker 이미지가 있는지 확인
if [ ! -f /tmp/k3s-dashboard.tar ]; then
    echo "Error: /tmp/k3s-dashboard.tar 파일이 없습니다."
    echo "먼저 docker save 명령을 실행하세요:"
    echo "  docker save k3s-dashboard:latest -o /tmp/k3s-dashboard.tar"
    exit 1
fi

# 2. K3s containerd에 이미지 import
echo ""
echo "=== K3s에 이미지 import ==="
k3s ctr images import /tmp/k3s-dashboard.tar

# 3. Kubernetes 리소스 적용
echo ""
echo "=== Kubernetes 리소스 적용 ==="
kubectl apply -f /home/saiadmin/k3s-cluster/manifests/20-dashboard.yaml

# 4. 기존 Pod가 있으면 재시작
echo ""
echo "=== Dashboard Pod 재시작 ==="
kubectl delete pod -n k3s-dashboard -l app=k3s-dashboard --ignore-not-found

# 5. Pod 상태 확인
echo ""
echo "=== Pod 상태 확인 (15초 대기) ==="
sleep 15
kubectl get pods -n k3s-dashboard

echo ""
echo "=== 완료! ==="
echo "대시보드 접속: http://<노드IP>:30080"
echo "또는 dashboard.local (hosts 파일 설정 필요)"
