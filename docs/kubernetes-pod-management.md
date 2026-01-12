# Kubernetes Pod 관리 및 이미지 갱신 완벽 가이드

재배포 시 기존 이미지가 계속 사용되거나, 되던 기능이 안 되는 문제를 해결하기 위한 핵심 개념 문서입니다.

## 목차

1. [Pod 관리 구조 개요](#1-pod-관리-구조-개요)
2. [컨테이너 이미지 관리의 핵심](#2-컨테이너-이미지-관리의-핵심)
3. [재배포 시 기존 이미지가 사용되는 이유](#3-재배포-시-기존-이미지가-사용되는-이유)
4. [올바른 재배포 방법](#4-올바른-재배포-방법)
5. [일반적인 문제와 해결책](#5-일반적인-문제와-해결책)
6. [실전 트러블슈팅 체크리스트](#6-실전-트러블슈팅-체크리스트)

---

## 1. Pod 관리 구조 개요

### 1.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Kubernetes Control Plane                     │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ API Server  │  │ Scheduler   │  │ Controller  │  │   etcd     │  │
│  │             │←→│             │←→│   Manager   │←→│ (상태저장) │  │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └────────────┘  │
└─────────┼───────────────────────────────────────────────────────────┘
          │
          ↓ kubelet 통신
┌─────────────────────────────────────────────────────────────────────┐
│                           Worker Node                                │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                        kubelet                               │    │
│  │  - Pod 생명주기 관리                                         │    │
│  │  - 컨테이너 상태 보고                                        │    │
│  │  - 이미지 pull 요청                                          │    │
│  └────────────────────────┬────────────────────────────────────┘    │
│                           ↓                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              containerd (컨테이너 런타임)                     │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │              이미지 스토어 (캐시)                      │   │    │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐              │   │    │
│  │  │  │ nginx   │  │ python  │  │ node    │  ...         │   │    │
│  │  │  │ :latest │  │ :3.11   │  │ :18     │              │   │    │
│  │  │  └─────────┘  └─────────┘  └─────────┘              │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │              실행 중인 컨테이너                        │   │    │
│  │  │  ┌─────────────────┐  ┌─────────────────┐           │   │    │
│  │  │  │   Pod A         │  │   Pod B         │           │   │    │
│  │  │  │ ┌─────────────┐ │  │ ┌─────────────┐ │           │   │    │
│  │  │  │ │ Container 1 │ │  │ │ Container 1 │ │           │   │    │
│  │  │  │ └─────────────┘ │  │ └─────────────┘ │           │   │    │
│  │  │  └─────────────────┘  └─────────────────┘           │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Pod 생명주기

```
Pod 생성 요청 (kubectl apply)
        │
        ↓
┌───────────────────┐
│    Pending       │ ← 스케줄링 대기 (노드 선택 중)
└────────┬──────────┘
         │
         ↓
┌───────────────────┐
│ ContainerCreating│ ← 이미지 pull & 컨테이너 생성
└────────┬──────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐  ┌─────────────────┐
│Running │  │ ImagePullBackOff│ ← 이미지 pull 실패
└───┬────┘  └─────────────────┘
    │
    ↓
┌───────────────────────────────┐
│ 정상 실행 중                   │
│ 또는                          │
│ CrashLoopBackOff (앱 에러)    │
└───────────────────────────────┘
```

### 1.3 핵심 개념: Deployment와 ReplicaSet

```
                    Deployment (선언적 상태 정의)
                           │
                           │ 관리
                           ↓
        ┌─────────────────────────────────────┐
        │           ReplicaSet                 │
        │  (특정 버전의 Pod 템플릿 유지)        │
        │  replicas: 3                         │
        └────────────┬────────────────────────┘
                     │
           ┌─────────┼─────────┐
           ↓         ↓         ↓
        ┌─────┐   ┌─────┐   ┌─────┐
        │Pod 1│   │Pod 2│   │Pod 3│
        └─────┘   └─────┘   └─────┘
```

**중요**: Deployment를 업데이트하면 새로운 ReplicaSet이 생성되고, 이전 ReplicaSet의 Pod들이 점진적으로 교체됩니다.

---

## 2. 컨테이너 이미지 관리의 핵심

### 2.1 이미지 식별 체계

```
┌─────────────────────────────────────────────────────────────┐
│                     이미지 전체 이름                         │
│                                                             │
│   registry.example.com/namespace/image-name:tag             │
│   ─────────────────── ───────── ────────── ───             │
│          │               │          │       │               │
│          │               │          │       └─ 태그 (버전)  │
│          │               │          └─ 이미지 이름          │
│          │               └─ 네임스페이스 (조직)             │
│          └─ 레지스트리 주소                                 │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 태그 vs 다이제스트 (SHA)

```
태그 (Mutable - 변경 가능)
─────────────────────────
myapp:latest     ──┐
myapp:v1.0       ──┼──→  실제 이미지 (sha256:abc123...)
myapp:stable     ──┘

다이제스트 (Immutable - 변경 불가)
────────────────────────────────
myapp@sha256:abc123...  ──→  항상 동일한 이미지
```

**핵심 문제**: `latest` 태그는 변경 가능하므로, 같은 `latest`라도 시점에 따라 다른 이미지를 가리킬 수 있습니다.

### 2.3 imagePullPolicy의 동작 방식

```yaml
# Deployment YAML에서 설정
spec:
  containers:
  - name: myapp
    image: myregistry/myapp:latest
    imagePullPolicy: Always  # ← 이 설정이 핵심!
```

| Policy | 동작 | 사용 시점 |
|--------|------|-----------|
| `Always` | **항상** 레지스트리에서 pull | 개발/스테이징 환경, `latest` 태그 사용 시 |
| `IfNotPresent` | 로컬에 없을 때만 pull | 프로덕션 환경, 버전 태그 사용 시 |
| `Never` | 절대 pull 안함 (로컬만 사용) | 로컬 개발, 에어갭 환경 |

**기본값 규칙**:
- 태그가 `latest`이면: 암묵적으로 `Always`처럼 동작해야 하지만...
- 태그가 명시적 버전이면: `IfNotPresent`가 기본값

---

## 3. 재배포 시 기존 이미지가 사용되는 이유

### 3.1 문제 상황 시각화

```
시나리오: 코드 수정 후 docker build && kubectl rollout restart
─────────────────────────────────────────────────────────────

1. 개발자 로컬에서:
   docker build -t myapp:latest .  ← 새 이미지 빌드 (sha256:NEW789)

2. 노드의 이미지 캐시 상태:
   ┌─────────────────────────────────────┐
   │        노드 이미지 캐시              │
   │  myapp:latest → sha256:OLD456      │  ← 예전 이미지가 캐시됨!
   └─────────────────────────────────────┘

3. kubectl rollout restart 실행

4. kubelet의 판단 (imagePullPolicy: IfNotPresent인 경우):
   "myapp:latest가 이미 있네? 그럼 pull 안 해도 되겠다"

5. 결과: 새 코드가 아닌 예전 코드로 Pod 실행됨!
```

### 3.2 근본 원인 분석

```
┌─────────────────────────────────────────────────────────────────┐
│                    문제 발생 원인들                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  원인 1: imagePullPolicy가 Always가 아님                        │
│  ────────────────────────────────────────                       │
│  imagePullPolicy: IfNotPresent  ← 캐시된 이미지 재사용          │
│                                                                 │
│  원인 2: 같은 태그 재사용 (latest의 함정)                        │
│  ────────────────────────────────────────                       │
│  이전: myapp:latest (sha256:OLD)                                │
│  이후: myapp:latest (sha256:NEW)  ← 태그는 같지만 내용 다름     │
│                                                                 │
│  원인 3: 이미지를 Registry에 push하지 않음                       │
│  ────────────────────────────────────────                       │
│  Master에서만 빌드 → Worker에는 예전 이미지만 존재               │
│                                                                 │
│  원인 4: Multi-node 환경에서 이미지 불일치                       │
│  ────────────────────────────────────────                       │
│  Node A: myapp:latest (sha256:NEW)                              │
│  Node B: myapp:latest (sha256:OLD)  ← 스케줄링에 따라 결과 다름 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 노드별 이미지 캐시 문제

```
┌─────────────────────────────────────────────────────────────┐
│                    K3s 클러스터                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Master Node                    Worker Node 1              │
│   ┌─────────────────┐           ┌─────────────────┐        │
│   │ 이미지 캐시      │           │ 이미지 캐시      │        │
│   │ myapp:latest    │           │ myapp:latest    │        │
│   │ (sha256:NEW789) │           │ (sha256:OLD456) │        │
│   │ ← 방금 빌드함   │           │ ← 예전 이미지   │        │
│   └─────────────────┘           └─────────────────┘        │
│                                                             │
│   Pod이 Worker Node 1에 스케줄링되면?                       │
│   → 예전 이미지로 실행됨!                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 올바른 재배포 방법

### 4.1 방법 1: 고유한 태그 사용 (권장)

```bash
# 빌드할 때마다 고유한 태그 사용
VERSION=$(date +%Y%m%d-%H%M%S)
# 또는
VERSION=$(git rev-parse --short HEAD)

docker build -t myregistry/myapp:$VERSION .
docker push myregistry/myapp:$VERSION

# Deployment 업데이트
kubectl set image deployment/myapp myapp=myregistry/myapp:$VERSION
```

**장점**: 이미지가 명확히 다르므로 항상 새 이미지를 pull

### 4.2 방법 2: imagePullPolicy: Always 설정

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: myapp
        image: myregistry/myapp:latest
        imagePullPolicy: Always  # ← 핵심 설정!
```

```bash
# 재배포 시
docker build -t myregistry/myapp:latest .
docker push myregistry/myapp:latest
kubectl rollout restart deployment/myapp
```

### 4.3 방법 3: kubectl set image로 강제 업데이트

```bash
# 이미지 태그에 더미 쿼리 추가 (트릭)
kubectl set image deployment/myapp \
  myapp=myregistry/myapp:latest@$(docker inspect --format='{{.Id}}' myregistry/myapp:latest)

# 또는 annotation 변경으로 강제 재배포
kubectl patch deployment myapp \
  -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"kubectl.kubernetes.io/restartedAt\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}}}}"
```

### 4.4 방법 4: 노드 캐시 강제 정리

```bash
# 특정 노드에서 이미지 삭제 (K3s용)
sudo k3s crictl rmi myregistry/myapp:latest

# 모든 노드에서 삭제 (SSH 접근 필요)
for node in master worker1 worker2; do
  ssh $node "sudo k3s crictl rmi myregistry/myapp:latest"
done

# 이후 재배포
kubectl rollout restart deployment/myapp
```

### 4.5 완전한 재배포 스크립트 예시

```bash
#!/bin/bash
# safe-redeploy.sh - 안전한 재배포 스크립트

set -e

IMAGE_NAME="${1:-localhost:5000/myapp}"
TAG="${2:-$(date +%Y%m%d-%H%M%S)}"
DEPLOYMENT="${3:-myapp}"
NAMESPACE="${4:-default}"

echo "=== 1. 이미지 빌드 ==="
docker build -t ${IMAGE_NAME}:${TAG} .

echo "=== 2. Registry에 Push ==="
docker push ${IMAGE_NAME}:${TAG}

echo "=== 3. Deployment 이미지 업데이트 ==="
kubectl set image deployment/${DEPLOYMENT} \
  ${DEPLOYMENT}=${IMAGE_NAME}:${TAG} \
  -n ${NAMESPACE}

echo "=== 4. 롤아웃 상태 확인 ==="
kubectl rollout status deployment/${DEPLOYMENT} -n ${NAMESPACE}

echo "=== 5. 실행 중인 이미지 확인 ==="
kubectl get pods -n ${NAMESPACE} -l app=${DEPLOYMENT} \
  -o jsonpath='{range .items[*]}{.metadata.name}: {.spec.containers[*].image}{"\n"}{end}'

echo "=== 완료! ==="
```

---

## 5. 일반적인 문제와 해결책

### 5.1 "되던 기능이 안 됨" 디버깅 가이드

```
문제: 코드 수정 후 배포했는데 변경사항이 반영 안됨
─────────────────────────────────────────────────

단계 1: 실제 실행 중인 이미지 확인
────────────────────────────────
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].image}'
kubectl get pod <pod-name> -o jsonpath='{.status.containerStatuses[*].imageID}'

단계 2: 예상 이미지와 비교
────────────────────────
docker images --digests | grep myapp
# → sha256 해시가 Pod의 imageID와 일치하는지 확인

단계 3: 이미지 pull 시점 확인
────────────────────────────
kubectl describe pod <pod-name> | grep -A5 "Events:"
# → "Pulled" 이벤트의 시간과 이미지 확인

단계 4: imagePullPolicy 확인
────────────────────────────
kubectl get deployment <deployment> -o yaml | grep imagePullPolicy
```

### 5.2 이미지 캐시 관련 문제 해결

```bash
# 문제: 같은 태그인데 노드마다 다른 이미지 실행

# 해결책 1: 모든 노드의 이미지 확인
kubectl get nodes -o name | while read node; do
  echo "=== $node ==="
  kubectl debug node/${node#node/} -it --image=busybox -- \
    k3s crictl images | grep myapp
done

# 해결책 2: Registry에서 직접 확인
curl -s http://localhost:5000/v2/myapp/manifests/latest \
  | jq -r '.config.digest'

# 해결책 3: 강제로 모든 노드에서 pull
kubectl rollout restart deployment/myapp
kubectl get pods -w  # 새 Pod이 생성되는지 watch
```

### 5.3 ImagePullBackOff 해결

```
원인 분석:
─────────
1. Registry 접근 불가
2. 이미지 존재하지 않음
3. 인증 실패 (private registry)
4. 네트워크 문제

디버깅:
───────
kubectl describe pod <pod-name>
# Events 섹션에서 정확한 에러 메시지 확인

해결책:
───────
# Registry 접근 테스트
curl -v http://localhost:5000/v2/_catalog

# 이미지 존재 확인
curl http://localhost:5000/v2/myapp/tags/list

# Private registry 인증 설정
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<user> \
  --docker-password=<password>
```

### 5.4 CrashLoopBackOff 해결

```
원인: 컨테이너가 시작 직후 종료됨 (앱 에러)
─────────────────────────────────────────

디버깅:
───────
# 로그 확인 (종료 직전 로그)
kubectl logs <pod-name> --previous

# 컨테이너 내부 진입 (디버깅용)
kubectl run debug --image=myapp:latest --rm -it -- /bin/sh

# 시작 명령 확인
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].command}'

일반적인 원인:
─────────────
1. 환경변수 누락
2. ConfigMap/Secret 마운트 실패
3. 의존 서비스 연결 실패
4. 권한 문제 (파일 접근 등)
5. 포트 충돌
```

---

## 6. 실전 트러블슈팅 체크리스트

### 6.1 재배포 전 체크리스트

```
[ ] 코드 변경사항 확인 (git diff)
[ ] 로컬 빌드 테스트 완료
[ ] 이미지 태그 전략 결정 (버전 태그 or latest + imagePullPolicy: Always)
[ ] Registry push 완료 (multi-node 환경)
[ ] deployment.yaml의 imagePullPolicy 확인
```

### 6.2 재배포 후 확인사항

```bash
# 1. Pod 상태 확인
kubectl get pods -l app=myapp -w

# 2. 새 Pod의 이미지 ID 확인
kubectl get pods -l app=myapp \
  -o jsonpath='{range .items[*]}{.metadata.name}: {.status.containerStatuses[*].imageID}{"\n"}{end}'

# 3. 롤아웃 이력 확인
kubectl rollout history deployment/myapp

# 4. 이벤트 확인
kubectl get events --sort-by='.lastTimestamp' | tail -20

# 5. 로그 확인
kubectl logs -l app=myapp -f --tail=50
```

### 6.3 빠른 문제 해결 명령어 모음

```bash
# 현재 상태 한눈에 보기
kubectl get all -l app=myapp

# Pod 상세 정보 (에러 원인 파악)
kubectl describe pod -l app=myapp

# 강제 재배포 (이미지 변경 없이)
kubectl rollout restart deployment/myapp

# 이전 버전으로 롤백
kubectl rollout undo deployment/myapp

# 특정 버전으로 롤백
kubectl rollout undo deployment/myapp --to-revision=2

# Pod 강제 삭제 (재생성 유도)
kubectl delete pod -l app=myapp

# 노드의 이미지 캐시 확인 (K3s)
sudo k3s crictl images | grep myapp

# 노드의 이미지 강제 삭제 (K3s)
sudo k3s crictl rmi <image-id>
```

---

## 부록: K3s 특화 정보

### K3s의 컨테이너 런타임

```
K3s는 containerd를 사용 (Docker 아님!)
────────────────────────────────────

이미지 관리 명령어:
  sudo k3s crictl images           # 이미지 목록
  sudo k3s crictl pull <image>     # 이미지 pull
  sudo k3s crictl rmi <image>      # 이미지 삭제
  sudo k3s crictl ps               # 실행 중인 컨테이너

Docker 이미지를 K3s에서 사용하려면:
  1. Registry에 push하고 pull (권장)
  2. docker save → k3s ctr images import (로컬 전용)
```

### K3s에서 로컬 이미지 사용

```bash
# Docker에서 빌드한 이미지를 K3s에 import
docker save myapp:latest -o /tmp/myapp.tar
sudo k3s ctr images import /tmp/myapp.tar

# 확인
sudo k3s crictl images | grep myapp

# Deployment에서 사용 (imagePullPolicy: Never 필수!)
# deployment.yaml:
#   imagePullPolicy: Never
```

### 다중 노드 환경에서 이미지 배포

```bash
#!/bin/bash
# distribute-image.sh - 모든 노드에 이미지 배포

IMAGE=$1
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

# Master에서 이미지 저장
docker save $IMAGE -o /tmp/image.tar

# 각 노드에 배포
for NODE in $NODES; do
  echo "Deploying to $NODE..."
  scp /tmp/image.tar $NODE:/tmp/
  ssh $NODE "sudo k3s ctr images import /tmp/image.tar && rm /tmp/image.tar"
done

rm /tmp/image.tar
echo "Done!"
```

---

## 요약: 안전한 재배포를 위한 황금 규칙

```
1. 고유한 버전 태그 사용
   ✓ myapp:v1.2.3
   ✓ myapp:20240115-143022
   ✗ myapp:latest (주의 필요)

2. imagePullPolicy 명시적 설정
   - latest 태그 사용 시: imagePullPolicy: Always
   - 버전 태그 사용 시: imagePullPolicy: IfNotPresent

3. Multi-node 환경에서는 반드시 Registry 사용
   - 로컬 빌드만으로는 다른 노드에 전파 안됨
   - 모든 노드가 Registry에서 pull할 수 있어야 함

4. 배포 후 반드시 확인
   - 실행 중인 이미지 ID 확인
   - 애플리케이션 정상 동작 확인
   - 로그에서 에러 없는지 확인
```

---

**작성일**: 2026-01-12
**버전**: 1.0
