# K3s 클러스터 이미지 배포 문제 해결 가이드

## 문제 상황

### 증상
```
k3s-dashboard-ccbc98bbb-dwwbk   0/1     ErrImageNeverPull   0          11s
```

Dashboard Pod가 `ErrImageNeverPull` 에러로 시작되지 않음.

### 원인
새로 추가한 **Worker 노드(filadmin)**에 이미지가 없는데, Pod가 해당 노드에 스케줄링됨.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         K3s 클러스터                                 │
├────────────────────────────────┬────────────────────────────────────┤
│   Master (saiadmin)            │   Worker (filadmin)                │
│   14.32.100.220                │   14.32.100.232                    │
│                                │                                    │
│   containerd 이미지:            │   containerd 이미지:                │
│   ├─ k3s-dashboard:latest ✅   │   └─ (없음) ❌                     │
│   └─ 기타 이미지들...            │                                    │
│                                │                                    │
│   sudo k3s ctr images import   │   이미지가 없어서                    │
│   → 여기에만 저장됨              │   ErrImageNeverPull 발생!           │
└────────────────────────────────┴────────────────────────────────────┘
```

## 핵심 개념

### 1. 각 노드는 독립적인 이미지 저장소를 가짐

```bash
# Master 노드에서 실행
sudo k3s ctr images import /tmp/k3s-dashboard.tar
```

이 명령은 **실행한 노드(Master)에만** 이미지를 저장함. Worker 노드에는 저장되지 않음.

### 2. Kubernetes 스케줄러의 동작

```bash
kubectl rollout restart deployment k3s-dashboard -n dashboard
```

이 명령은 스케줄러에게 "Pod를 재시작해줘"라고 요청함.
스케줄러는 **리소스 상황에 따라 아무 노드나 선택**할 수 있음.

### 3. imagePullPolicy: Never

```yaml
spec:
  containers:
  - image: k3s-dashboard:latest
    imagePullPolicy: Never  # 레지스트리에서 pull 하지 않음
```

- 로컬 이미지만 사용하겠다는 설정
- 해당 노드에 이미지가 없으면 → `ErrImageNeverPull`

## 문제 발생 흐름

```
1. Master 노드에서 이미지 import 실행
   └─ Master에만 이미지 저장됨

2. kubectl rollout restart 실행
   └─ 스케줄러가 Pod 배치할 노드 선택

3. 스케줄러: "Worker 노드 리소스 여유있네, 거기서 실행하자"
   └─ Worker 노드에 Pod 스케줄링

4. Worker 노드의 kubelet: "k3s-dashboard:latest 이미지 찾는 중..."
   └─ 로컬에 없음

5. imagePullPolicy: Never 설정
   └─ 레지스트리에서 pull 안 함

6. 결과: ErrImageNeverPull ❌
```

## 해결 방법

### 방법 1: nodeSelector로 특정 노드에서만 실행 (적용됨)

```bash
kubectl patch deployment k3s-dashboard -n dashboard \
  --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/nodeSelector", "value": {"node-role.kubernetes.io/master": "true"}}]'
```

**장점**: 간단함, 이미지가 있는 노드에서만 실행 보장
**단점**: 특정 노드에 고정됨, HA 구성 어려움

### 방법 2: 모든 노드에 이미지 배포

```bash
# Master에서 이미지 저장
docker save -o /tmp/k3s-dashboard.tar k3s-dashboard:latest

# Worker 노드로 복사
scp /tmp/k3s-dashboard.tar filadmin@14.32.100.232:/tmp/

# Worker 노드에서 import (SSH 접속 후)
sudo k3s ctr images import /tmp/k3s-dashboard.tar
```

**장점**: 모든 노드에서 실행 가능
**단점**: 노드 추가 시마다 반복 필요

### 방법 3: Private Registry 사용 (권장)

```bash
# 1. Registry 배포 (예: Harbor)
helm install harbor harbor/harbor

# 2. 이미지 push
docker tag k3s-dashboard:latest harbor.local/library/k3s-dashboard:latest
docker push harbor.local/library/k3s-dashboard:latest

# 3. Deployment에서 Registry 이미지 사용
spec:
  containers:
  - image: harbor.local/library/k3s-dashboard:latest
    imagePullPolicy: Always
```

**장점**: 중앙 관리, 모든 노드에서 자동 pull
**단점**: Registry 인프라 필요

### 방법 4: DaemonSet으로 이미지 사전 배포

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: image-prepuller
spec:
  selector:
    matchLabels:
      app: image-prepuller
  template:
    spec:
      initContainers:
      - name: prepull
        image: k3s-dashboard:latest
        command: ["echo", "Image pulled"]
      containers:
      - name: pause
        image: k8s.gcr.io/pause:3.1
```

**장점**: 모든 노드에 자동으로 이미지 배포
**단점**: 복잡함

## 현재 적용된 설정

### Deployment YAML (nodeSelector 추가)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k3s-dashboard
  namespace: dashboard
spec:
  template:
    spec:
      nodeSelector:
        node-role.kubernetes.io/master: "true"  # Master 노드에서만 실행
      containers:
      - name: dashboard
        image: k3s-dashboard:latest
        imagePullPolicy: Never
```

### 확인 명령어

```bash
# Pod가 어느 노드에서 실행 중인지 확인
kubectl get pods -n dashboard -o wide

# 노드별 이미지 목록 확인 (각 노드에서 실행)
sudo k3s ctr images list | grep dashboard

# Deployment의 nodeSelector 확인
kubectl get deployment k3s-dashboard -n dashboard -o yaml | grep -A5 nodeSelector
```

## 향후 권장사항

1. **개발 환경**: nodeSelector 방식으로 충분
2. **프로덕션 환경**: Private Registry(Harbor 등) 구축 권장
3. **노드 추가 시**: 이미지 배포 자동화 스크립트 작성 또는 Registry 사용

## 참고: 이미지 배포 스크립트

```bash
#!/bin/bash
# deploy-image.sh - 모든 노드에 이미지 배포

IMAGE_NAME=$1
TAR_FILE="/tmp/${IMAGE_NAME//\//-}.tar"

# 이미지 저장
docker save -o $TAR_FILE $IMAGE_NAME

# 모든 Worker 노드에 배포
WORKERS=$(kubectl get nodes -l '!node-role.kubernetes.io/master' -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}')

for WORKER in $WORKERS; do
    echo "Deploying to $WORKER..."
    scp $TAR_FILE $WORKER:/tmp/
    ssh $WORKER "sudo k3s ctr images import /tmp/$(basename $TAR_FILE)"
done

echo "Done!"
```

사용법:
```bash
./deploy-image.sh k3s-dashboard:latest
```
