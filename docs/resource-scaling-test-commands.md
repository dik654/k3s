# 리소스 동적 스케일링 테스트 명령어

## 테스트 환경
- **Kubernetes**: K3s v1.31.x
- **테스트 대상**: Qdrant StatefulSet (ai-workloads namespace)
- **테스트 일자**: 2026-01-08

---

## 1. Memory 동적 할당 테스트

### 1.1 Memory 증가 (2Gi → 3Gi)

```bash
# Memory limit 변경
kubectl patch sts qdrant -n ai-workloads --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "3Gi"}]'

# cgroup으로 실제 적용 확인 (bytes 단위)
kubectl exec -n ai-workloads qdrant-0 -- cat /sys/fs/cgroup/memory.max
# 결과: 3221225472 (= 3Gi)
```

### 1.2 Memory 감소 (3Gi → 1Gi)

```bash
# Memory limit 변경
kubectl patch sts qdrant -n ai-workloads --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "1Gi"}]'

# cgroup으로 실제 적용 확인
kubectl exec -n ai-workloads qdrant-0 -- cat /sys/fs/cgroup/memory.max
# 결과: 1073741824 (= 1Gi)
```

### Memory 단위 변환 참고
| 설정값 | bytes |
|--------|-------|
| 1Gi | 1073741824 |
| 2Gi | 2147483648 |
| 3Gi | 3221225472 |
| 4Gi | 4294967296 |
| 8Gi | 8589934592 |

---

## 2. CPU 동적 할당 테스트

### 2.1 CPU 증가 (1 → 2)

```bash
# CPU limit 변경
kubectl patch sts qdrant -n ai-workloads --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/cpu", "value": "2"}]'

# cgroup으로 실제 적용 확인
kubectl exec -n ai-workloads qdrant-0 -- cat /sys/fs/cgroup/cpu.max
# 결과: 200000 100000
# 해석: quota=200000, period=100000 → 200000/100000 = 2 CPUs
```

### 2.2 CPU 감소 (2 → 1)

```bash
# CPU limit 변경
kubectl patch sts qdrant -n ai-workloads --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/cpu", "value": "1"}]'

# cgroup으로 실제 적용 확인
kubectl exec -n ai-workloads qdrant-0 -- cat /sys/fs/cgroup/cpu.max
# 결과: 100000 100000
# 해석: 100000/100000 = 1 CPU
```

### CPU cgroup 값 해석
```
cpu.max 형식: <quota> <period>
CPU 개수 = quota / period

예시:
- 100000 100000 = 1 CPU
- 200000 100000 = 2 CPUs
- 500000 100000 = 5 CPUs
- 50000 100000 = 0.5 CPU (500m)
```

---

## 3. GPU 동적 할당 테스트

### 3.1 테스트 Pod 생성

```bash
# GPU 1개 할당된 테스트 Pod 생성
cat << 'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gpu-scaling-test
  namespace: ai-workloads
spec:
  restartPolicy: Never
  containers:
  - name: gpu-test
    image: python:3.11-slim
    command: ["sleep", "3600"]
    resources:
      limits:
        nvidia.com/gpu: 1
EOF

# Pod 실행 확인
kubectl get pod gpu-scaling-test -n ai-workloads -o wide
```

### 3.2 GPU 동적 변경 시도 (1 → 2)

```bash
# GPU 변경 시도
kubectl patch pod gpu-scaling-test -n ai-workloads --type='json' \
  -p='[{"op": "replace", "path": "/spec/containers/0/resources/limits/nvidia.com~1gpu", "value": "2"}]'
```

### 3.3 테스트 결과: 실패

```
The Pod "gpu-scaling-test" is invalid:
spec: Forbidden: pod updates may not change fields other than
`spec.containers[*].image`, `spec.initContainers[*].image`,
`spec.activeDeadlineSeconds`, `spec.tolerations`,
`spec.terminationGracePeriodSeconds`
```

### 3.4 테스트 Pod 정리

```bash
kubectl delete pod gpu-scaling-test -n ai-workloads --force
```

---

## 4. 변경 후 확인 명령어

### Pod 재시작 여부 확인
```bash
# RESTARTS 컬럼이 0이면 재시작 없이 적용된 것
kubectl get pods -n ai-workloads

# 상세 정보 확인
kubectl describe pod <pod-name> -n ai-workloads | grep -A5 "Restart Count"
```

### 현재 리소스 설정 확인
```bash
# Pod의 현재 리소스 limits 확인
kubectl get pod <pod-name> -n ai-workloads -o jsonpath='{.spec.containers[0].resources.limits}'

# StatefulSet의 리소스 설정 확인
kubectl get sts <sts-name> -n ai-workloads -o jsonpath='{.spec.template.spec.containers[0].resources}'
```

### 실제 사용량 확인
```bash
# metrics-server 필요
kubectl top pod <pod-name> -n ai-workloads
```

---

## 5. 테스트 결과 요약

| 리소스 | 동적 변경 | 증가 | 감소 | Pod 재시작 |
|--------|----------|------|------|-----------|
| **Memory** | ✅ 가능 | ✅ | ✅ | 불필요 |
| **CPU** | ✅ 가능 | ✅ | ✅ | 불필요 |
| **GPU** | ❌ 불가능 | - | - | 필요 |

### GPU 변경이 필요한 경우

GPU는 Pod 재생성이 필요합니다:

```bash
# Deployment의 경우 (롤링 업데이트)
kubectl patch deployment <name> -n <namespace> --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/nvidia.com~1gpu", "value": "2"}]'

# StatefulSet의 경우 (Pod 삭제 후 재생성)
kubectl patch sts <name> -n <namespace> --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/nvidia.com~1gpu", "value": "2"}]'
kubectl delete pod <pod-name> -n <namespace>
```

---

## 6. 참고: JSON Patch 경로 규칙

- 슬래시(`/`)는 `~1`로 이스케이프
- 틸드(`~`)는 `~0`으로 이스케이프

```bash
# nvidia.com/gpu → nvidia.com~1gpu
# 예시
-p='[{"op": "replace", "path": "/spec/containers/0/resources/limits/nvidia.com~1gpu", "value": "2"}]'
```
