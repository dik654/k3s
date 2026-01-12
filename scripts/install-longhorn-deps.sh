#!/bin/bash
# Longhorn 필수 패키지 설치 스크립트
# 실행: sudo ./install-longhorn-deps.sh

set -e

echo "=== Longhorn 의존성 패키지 설치 ==="

# Ubuntu/Debian
if command -v apt-get &> /dev/null; then
    echo "Installing open-iscsi and nfs-common..."
    apt-get update
    apt-get install -y open-iscsi nfs-common

    # Enable and start iscsid
    systemctl enable iscsid
    systemctl start iscsid

    echo "=== 설치 완료 ==="
    echo "iscsid status:"
    systemctl status iscsid --no-pager
else
    echo "Unsupported OS. Please install open-iscsi manually."
    exit 1
fi

echo ""
echo "이제 Longhorn pods가 정상 작동할 것입니다."
echo "확인: kubectl get pods -n longhorn-system"
