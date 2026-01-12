# K3s Dashboard - 빠른 참조 카드

## 🚀 가장 자주 사용하는 명령어

### 빌드 및 배포

```bash
# 1️⃣ 모든 것을 한 번에 (권장)
make all

# 또는
./build-and-deploy.sh
```

### 모니터링

```bash
# 2️⃣ 상태 확인
make status

# 3️⃣ 로그 확인
make logs

# 4️⃣ Pod 재시작
make restart
```

---

## 📋 전체 명령어 목록

| 명령어 | 설명 |
|--------|------|
| `make help` | 도움말 표시 |
| `make all` | 빌드 → push → 배포 (전체) |
| `make build` | Docker 이미지만 빌드 |
| `make deploy` | 이미 빌드된 이미지 배포 |
| `make push` | 이미지를 Registry에 push |
| `make redeploy` | 기존 Pod 업데이트 및 재시작 |
| `make status` | Deployment 및 Pod 상태 확인 |
| `make logs` | Pod 로그 출력 (실시간) |
| `make events` | 최근 K8s 이벤트 확인 |
| `make describe` | Deployment 상세 정보 |
| `make shell` | Pod에 대화형 셸 접속 |
| `make restart` | Pod 강제 재시작 |
| `make monitor` | 모든 정보 한 번에 확인 |
| `make pods` | Pod 목록 확인 |
| `make services` | Service 목록 확인 |
| `make ingress` | Ingress 목록 확인 |
| `make clean` | Deployment 삭제 |

---

## 🔧 옵션 지정

### Makefile에서 변수 지정

```bash
# 이미지 이름 변경
make all IMAGE_NAME=myregistry/dashboard

# 이미지 태그 변경
make all IMAGE_TAG=v1.0.0

# 네임스페이스 변경
make all NAMESPACE=production

# 모두 함께 사용
make all \
  IMAGE_NAME=myregistry/dashboard \
  IMAGE_TAG=v1.0.0 \
  NAMESPACE=production
```

### 스크립트에서 옵션 지정

```bash
./build-and-deploy.sh \
  --image myregistry/dashboard \
  --tag v1.0.0 \
  --namespace production \
  --force-restart
```

---

## 🐛 빠른 문제 해결

| 증상 | 해결책 |
|------|--------|
| Pod이 Running 상태인데 오류 | `make logs` |
| Pod이 계속 재시작됨 | `make logs` 후 코드 수정 |
| Pod이 생성되지 않음 | `make status` 확인 |
| 로컬 이미지만 사용하고 싶음 | `make build --skip-push` |
| Registry에 업로드하고 싶음 | `make push` |
| 이미지를 완전히 재빌드 | `make clean-build` 후 `make all` |

---

## 📍 주요 경로

```
/home/saiadmin/k3s-cluster/
├── build-and-deploy.sh         # 메인 빌드 & 배포 스크립트
├── monitor-deployment.sh        # 모니터링 스크립트
├── Makefile                     # Make 명령어 정의
├── BUILD_AND_DEPLOY_GUIDE.md   # 상세 가이드
├── QUICK_REFERENCE.md          # 이 파일
├── dashboard/                   # 대시보드 코드
│   ├── Dockerfile              # Docker 빌드 설정
│   ├── frontend/               # React 프론트엔드
│   └── backend/                # Python 백엔드
├── dashboard-deployment.yaml    # K8s 배포 설정
└── dashboard-rbac.yaml         # K8s RBAC 설정
```

---

## 🎯 일반적인 워크플로우

### 📝 개발 중

```bash
# 1. 코드 수정 (NodeCard.tsx 등)
# 2. 빌드 및 배포
make redeploy

# 3. 로그에서 확인
make logs

# 4. 다시 코드 수정...
```

### 🚀 프로덕션 배포

```bash
# 1. 기본 빌드
make clean-build

# 2. 버전 태그로 빌드
make all IMAGE_TAG=v1.0.0

# 3. 상태 확인
make status
```

### 🔄 업데이트

```bash
# 1. 코드 수정
# 2. 빌드 및 배포 (이전 Pod 자동 종료)
make all IMAGE_TAG=v1.0.1

# 3. 상태 모니터링
watch "make status"
```

---

## 💾 Docker 이미지 관리

```bash
# 로컬 이미지 목록
docker images | grep k3s-dashboard

# 이미지 상세 정보
docker inspect localhost:5000/k3s-dashboard:latest

# 로컬 이미지 삭제
docker rmi localhost:5000/k3s-dashboard:latest

# 이미지 크기 확인
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" \
  | grep k3s-dashboard
```

---

## 🐳 Docker 빌드 캐시

```bash
# 캐시 사용 (빠름, 권장)
./build-and-deploy.sh

# 캐시 무시 (전체 재빌드, 느림)
docker build --no-cache -f Dockerfile -t localhost:5000/k3s-dashboard:latest .
```

---

## ☸️ Kubernetes 직접 명령어

```bash
# Deployment 상태
kubectl get deployment k3s-dashboard -n default

# Pod 상태
kubectl get pods -n default -l app=k3s-dashboard -w

# Pod 로그
kubectl logs -n default -l app=k3s-dashboard -f

# Pod에 셸 접속
kubectl exec -it POD_NAME -n default -- /bin/bash

# Pod 재시작
kubectl rollout restart deployment/k3s-dashboard -n default

# 배포 상태 모니터링
kubectl rollout status deployment/k3s-dashboard -n default
```

---

## 🌐 접근 URL

```
대시보드: http://dashboard.14.32.100.220.nip.io
포트포워딩: http://localhost:8000 (kubectl port-forward 실행 시)
```

---

## 🆘 긴급 조치

```bash
# Pod 강제 삭제 (새로 생성됨)
kubectl delete pod POD_NAME -n default

# Deployment 삭제
kubectl delete deployment k3s-dashboard -n default

# 네임스페이스 삭제 (모든 리소스 삭제)
kubectl delete namespace default
```

---

## 📊 성능 모니터링

```bash
# Pod 리소스 사용량
kubectl top pod -n default -l app=k3s-dashboard

# Node 리소스 사용량
kubectl top node

# 실시간 모니터링
watch "kubectl top pod -n default -l app=k3s-dashboard"
```

---

## 🔐 보안 확인

```bash
# RBAC 설정 확인
kubectl get serviceaccount -n default

# Role 확인
kubectl get roles -n default

# RoleBinding 확인
kubectl get rolebindings -n default
```

---

## 📱 일반적인 포트

| 서비스 | 포트 | 설명 |
|--------|------|------|
| 대시보드 | 8000 | Python FastAPI 백엔드 |
| Ingress | 80/443 | Traefik 리버스 프록시 |
| K8s API | 6443 | Kubernetes API 서버 |

---

## 💡 팁과 요령

```bash
# alias 설정 (~/.bashrc에 추가)
alias k='kubectl'
alias kb='cd /home/saiadmin/k3s-cluster && make'
alias kbl='make logs'
alias kbs='make status'

# source ~/.bashrc 후 사용
kb all     # make all 대신
kbl        # make logs 대신
kbs        # make status 대신
```

---

## 🆘 도움말 보기

```bash
./build-and-deploy.sh --help
./monitor-deployment.sh
make help

# 상세 가이드 보기
cat BUILD_AND_DEPLOY_GUIDE.md
```

---

**업데이트**: 2026-01-12 | **버전**: 1.0
