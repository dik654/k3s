# K3s Dashboard - 빌드 및 배포 가이드

GPU 게이지 기능 추가 후 Docker 이미지를 빌드하고 K8s Pod으로 배포하는 방법을 설명합니다.

## 📋 목차

1. [빠른 시작](#빠른-시작)
2. [상세 가이드](#상세-가이드)
3. [트러블슈팅](#트러블슈팅)
4. [고급 사용법](#고급-사용법)

---

## 빠른 시작

### 기본 배포 (가장 간단한 방법)

```bash
cd /home/saiadmin/k3s-cluster

# 1. 전체 프로세스 (빌드 → 배포)
make all

# 또는 직접 스크립트 실행
./build-and-deploy.sh
```

**완료!** 🎉 Pod이 자동으로 배포되고 실행됩니다.

### Makefile 주요 명령어

```bash
# 빌드만
make build

# 배포만 (이미 빌드된 이미지 사용)
make deploy

# 상태 확인
make status

# 로그 확인
make logs

# Pod 재시작
make restart
```

---

## 상세 가이드

### 1️⃣ 코드 수정 후 빌드

GPU 게이지 기능이 추가된 코드를 빌드합니다.

#### 자동 빌드 (권장)

```bash
cd /home/saiadmin/k3s-cluster

# 기본값 사용 (localhost:5000/k3s-dashboard:latest)
./build-and-deploy.sh

# 또는 Makefile 사용
make all
```

#### 커스텀 이미지 이름으로 빌드

```bash
# 방법 1: 스크립트 사용
./build-and-deploy.sh \
  --image myregistry.com/dashboard \
  --tag v1.0.0

# 방법 2: Makefile 사용
make all IMAGE_NAME=myregistry.com/dashboard IMAGE_TAG=v1.0.0
```

**스크립트 옵션:**
- `--image`: Docker 이미지 이름 (기본값: localhost:5000/k3s-dashboard)
- `--tag`: 이미지 태그 (기본값: latest)
- `--namespace`: K8s 네임스페이스 (기본값: default)
- `--skip-build`: Docker 빌드 스킵
- `--skip-push`: Registry push 스킵
- `--skip-deploy`: K8s 배포 스킵
- `--force-restart`: 기존 Pod 강제 재시작

### 2️⃣ 배포 상태 확인

```bash
# 방법 1: Makefile
make status

# 방법 2: 모니터링 스크립트
./monitor-deployment.sh default status

# 방법 3: kubectl 직접 사용
kubectl get pods -n default -l app=k3s-dashboard -o wide
kubectl get deployment k3s-dashboard -n default
```

#### 성공적인 배포 확인

```
NAME                           READY   STATUS    RESTARTS   AGE
k3s-dashboard-1234567890-abcd  1/1     Running   0          2m
```

- `READY`: 1/1 (Pod이 준비됨)
- `STATUS`: Running (실행 중)
- `RESTARTS`: 0 (재시작 없음)

### 3️⃣ 로그 확인

```bash
# 방법 1: Makefile
make logs

# 방법 2: 모니터링 스크립트
./monitor-deployment.sh default logs

# 방법 3: kubectl 직접 사용
kubectl logs -n default -l app=k3s-dashboard -f

# 특정 Pod의 로그
POD=$(kubectl get pods -n default -l app=k3s-dashboard -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n default $POD -f
```

### 4️⃣ Pod 재시작

코드 수정 후 이미 배포된 Pod을 업데이트합니다.

```bash
# 방법 1: Makefile (가장 간단)
make redeploy

# 방법 2: 스크립트
./build-and-deploy.sh --force-restart

# 방법 3: kubectl
kubectl rollout restart deployment/k3s-dashboard -n default

# 상태 확인
kubectl rollout status deployment/k3s-dashboard -n default
```

### 5️⃣ 대시보드 접근

배포 후 대시보드에 접근합니다.

```bash
# Ingress 정보 확인
kubectl get ingress -n default k3s-dashboard

# 예상 출력:
# NAME            CLASS   HOSTS                          ADDRESS   PORTS
# k3s-dashboard   -       dashboard.14.32.100.220.nip.io localhost 80
```

**대시보드 URL**: http://dashboard.14.32.100.220.nip.io

또는 포트포워딩으로 접근:

```bash
# 로컬에서 8000 포트로 포워딩
kubectl port-forward -n default svc/k3s-dashboard 8000:8000

# 브라우저에서 접속
# http://localhost:8000
```

---

## 트러블슈팅

### ❌ "ErrImagePull" 또는 "ImagePullBackOff"

**증상**: Pod이 `ErrImagePull` 상태로 계속 시간이 지나감

**원인**: Registry에서 이미지를 다운로드할 수 없음

**해결책**:

```bash
# 1. Pod 상태 자세히 확인
kubectl describe pod <pod-name> -n default

# 2. 이미지가 Registry에 존재하는지 확인
docker images | grep k3s-dashboard

# 3. 이미지가 없으면 빌드 및 push
make clean-build
make push

# 4. 기존 Pod 재시작
make restart
```

### ❌ "CrashLoopBackOff"

**증상**: Pod이 계속 시작했다 종료됨을 반복

**원인**: 애플리케이션이 실행 중에 에러 발생

**해결책**:

```bash
# 1. Pod 로그 확인
make logs

# 2. 에러 메시지 확인 후 코드 수정

# 3. 다시 빌드 및 배포
make redeploy
```

### ❌ "ErrImageNeverPull"

**증상**: `imagePullPolicy: Never`로 설정되었을 때 로컬 이미지가 없음

**원인**: Worker 노드에 이미지가 없음

**해결책** (아래 중 하나 선택):

**방법 1: Master 노드에서만 실행**
```bash
kubectl patch deployment k3s-dashboard -n default \
  --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/nodeSelector", "value": {"node-role.kubernetes.io/master": "true"}}]'
```

**방법 2: 모든 노드에 이미지 배포**
```bash
# Master에서 이미지 저장
docker save -o /tmp/k3s-dashboard.tar localhost:5000/k3s-dashboard:latest

# Worker 노드들에 복사 및 import
for NODE in worker1 worker2; do
  scp /tmp/k3s-dashboard.tar $NODE:/tmp/
  ssh $NODE "sudo k3s ctr images import /tmp/k3s-dashboard.tar"
done

# Pod 재시작
kubectl rollout restart deployment/k3s-dashboard -n default
```

### ❌ Docker 빌드 실패

**증상**: `docker build` 명령이 실패

**해결책**:

```bash
# 1. Docker 데몬이 실행 중인지 확인
docker ps

# 2. 디렉토리 확인
cd /home/saiadmin/k3s-cluster
ls -la Dockerfile frontend/ backend/

# 3. 빌드 로그 확인
./build-and-deploy.sh --skip-deploy 2>&1 | tail -50

# 4. BuildKit 활성화
export DOCKER_BUILDKIT=1
./build-and-deploy.sh
```

### ❌ Pod에 셸을 접속할 수 없음

**증상**: `kubectl exec` 명령이 실패

**해결책**:

```bash
# 1. Pod 이름 확인
kubectl get pods -n default -l app=k3s-dashboard

# 2. 특정 Pod에 접속
POD=$(kubectl get pods -n default -l app=k3s-dashboard -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -n default -c dashboard -- /bin/bash

# 3. Pod에 bash가 없으면 sh 사용
kubectl exec -it $POD -n default -c dashboard -- /bin/sh
```

---

## 고급 사용법

### 다중 버전 배포

```bash
# v1.0.0 배포
make all IMAGE_TAG=v1.0.0

# v1.0.1 배포 (동시에 v1.0.0과 구분)
make all IMAGE_TAG=v1.0.1
```

### 프로덕션 배포

```bash
# 프로덕션 네임스페이스에 배포
make all NAMESPACE=production

# 상태 확인
make status NAMESPACE=production

# 로그 확인
make logs NAMESPACE=production
```

### 모든 노드에 이미지 배포 (DaemonSet)

```bash
#!/bin/bash
# deploy-to-all-nodes.sh

IMAGE=$1
WORKERS=$(kubectl get nodes -l '!node-role.kubernetes.io/master' \
  -o jsonpath='{.items[*].metadata.name}')

docker save -o /tmp/image.tar $IMAGE

for WORKER in $WORKERS; do
  echo "Deploying to $WORKER..."
  scp /tmp/image.tar $WORKER:/tmp/
  ssh $WORKER "sudo k3s ctr images import /tmp/image.tar"
done
```

사용법:
```bash
chmod +x deploy-to-all-nodes.sh
./deploy-to-all-nodes.sh localhost:5000/k3s-dashboard:latest
```

### 자동 배포 스케줄링

```bash
# 매일 자정에 배포
0 0 * * * cd /home/saiadmin/k3s-cluster && make all >> /var/log/k3s-deploy.log 2>&1

# crontab에 추가
crontab -e
```

### 배포 전 테스트

```bash
# Docker 이미지 빌드 테스트만
make test-build

# 모든 검사 실행
make lint
make test
make test-build
```

---

## 📊 배포 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│  GPU 게이지 기능 코드 수정 완료                              │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  make all (또는 ./build-and-deploy.sh)                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
        ┌──────────────┴──────────────┐
        ↓                             ↓
   ┌─────────────┐          ┌─────────────────┐
   │   빌드      │          │  Dockerfile     │
   │  (Frontend) │─────────→│  Multi-stage    │
   │             │          │  (Node+Python)  │
   │  (Backend)  │          │                 │
   └─────────────┘          └────────┬────────┘
                                     ↓
                            ┌────────────────┐
                            │ Docker 이미지   │
                            │ 생성됨          │
                            └────────┬────────┘
                                     ↓
                            ┌────────────────┐
                            │  Registry push  │
                            │  (필요시)        │
                            └────────┬────────┘
                                     ↓
                            ┌────────────────┐
                            │ K8s 배포        │
                            │ (kubectl apply) │
                            └────────┬────────┘
                                     ↓
                            ┌────────────────┐
                            │  Pod 시작       │
                            │  준비 완료      │
                            └────────┬────────┘
                                     ↓
                            ┌────────────────┐
                            │ 대시보드 접근   │
                            │ GPU 게이지 확인 │
                            └────────────────┘
```

---

## 🔧 커스터마이징

### 이미지 이름 변경

```bash
# 환경 변수로 설정
export IMAGE_NAME="my-registry.com/k3s-dashboard"
export IMAGE_TAG="v1.0.0"
make all

# 또는 직접 지정
make all IMAGE_NAME=my-registry.com/k3s-dashboard IMAGE_TAG=v1.0.0
```

### 배포 파일 수정

K8s 배포 설정을 커스터마이징하려면:

```bash
# deployment-deployment.yaml 수정
nano /home/saiadmin/k3s-cluster/dashboard-deployment.yaml

# 변경 사항 적용
kubectl apply -f /home/saiadmin/k3s-cluster/dashboard-deployment.yaml
```

### Pod 리소스 제한

```yaml
# dashboard-deployment.yaml에서
spec:
  containers:
  - name: dashboard
    resources:
      limits:
        cpu: "2"
        memory: "2Gi"
      requests:
        cpu: "500m"
        memory: "512Mi"
```

---

## 📚 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [K3s 공식 문서](https://k3s.io/)
- [Docker Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)

---

## 💡 팁

### 개발 중 빠른 배포

```bash
# 변경사항만 빌드하고 배포
make build && make deploy
```

### 배포 진행 상황 모니터링

```bash
# 터미널 분할: 터미널 1에서
make logs

# 터미널 2에서
watch "kubectl get pods -n default -l app=k3s-dashboard"
```

### 배포 실패 시 빠른 확인

```bash
# 모든 정보 한 번에 확인
./monitor-deployment.sh default all
```

---

## 🆘 도움말

스크립트 도움말 확인:

```bash
./build-and-deploy.sh --help
./monitor-deployment.sh
make help
```

---

**마지막 수정**: 2026-01-12
**작성자**: K3s Dashboard 개발팀
