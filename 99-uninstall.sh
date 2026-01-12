#!/bin/bash
#===============================================================================
# K3s 삭제 스크립트
#
# 사용법: sudo ./99-uninstall.sh
#
# 주의: 이 스크립트는 K3s와 관련 데이터를 완전히 삭제합니다!
#===============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${RED}=============================================="
echo "       K3s 완전 삭제"
echo "==============================================${NC}"
echo ""
echo -e "${YELLOW}주의: 이 작업은 되돌릴 수 없습니다!${NC}"
echo "  - K3s 서비스 중지"
echo "  - 모든 Pod/Service/Deployment 삭제"
echo "  - K3s 데이터 삭제"
echo ""

read -p "정말로 삭제하시겠습니까? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "취소되었습니다."
    exit 0
fi

echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}이 스크립트는 root 권한이 필요합니다: sudo $0${NC}"
    exit 1
fi

# K3s Server 삭제
if [ -f /usr/local/bin/k3s-uninstall.sh ]; then
    echo "[INFO] K3s Server 삭제 중..."
    /usr/local/bin/k3s-uninstall.sh
    echo -e "${GREEN}[SUCCESS]${NC} K3s Server 삭제 완료"
fi

# K3s Agent 삭제
if [ -f /usr/local/bin/k3s-agent-uninstall.sh ]; then
    echo "[INFO] K3s Agent 삭제 중..."
    /usr/local/bin/k3s-agent-uninstall.sh
    echo -e "${GREEN}[SUCCESS]${NC} K3s Agent 삭제 완료"
fi

# 잔여 파일 정리
echo "[INFO] 잔여 파일 정리 중..."
rm -rf /etc/rancher/k3s
rm -rf /var/lib/rancher/k3s
rm -rf /var/lib/kubelet
rm -rf ~/.kube

echo ""
echo -e "${GREEN}=============================================="
echo "       K3s 삭제 완료!"
echo "==============================================${NC}"
echo ""
