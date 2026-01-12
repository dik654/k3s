# Kubernetes 리소스 런타임 스케일링 가이드

## 개요

Kubernetes 1.27부터 **In-Place Pod Vertical Scaling** 기능이 Alpha로 도입되었고, **K8s 1.31에서는 Beta로 기본 활성화**되어 있습니다. 이 기능을 통해 Pod를 재시작하지 않고도 CPU와 Memory 리소스를 실시간으로 조정할 수 있습니다.

## 기능 비교

### 리소스 유형별 런타임 변경 지원

| 리소스 | 런타임 변경 | 증가 | 감소 | Pod 재시작 | 비고 |
|--------|-------------|------|------|------------|------|
| **Storage (PVC)** | ✅ 지원 | ✅ | ❌ | 불필요 | Longhorn/CSI 드라이버 필요 |
| **CPU** | ✅ 지원 | ✅ | ✅ | 불필요 | K8s 1.31 기본 지원 |
| **Memory** | ✅ 지원 | ✅ | ✅ | 불필요 | K8s 1.31 기본 지원 |
| **GPU** | ❌ 미지원 | - | - | 필요 | Pod 재생성 필요 |

### 스토리지 vs CPU/Memory 비교

| 항목 | 스토리지 (Longhorn) | CPU/Memory |
|------|---------------------|------------|
| 특별한 Extension 필요 | ❌ (Longhorn 기본 지원) | ❌ (K8s 1.31 기본 지원) |
| 런타임 변경 가능 | ✅ (증가만) | ✅ (증가/감소 모두) |
| Pod 재시작 필요 | ❌ | ❌ |
| 즉시 적용 | ✅ | ✅ |
| 롤백 가능 | ❌ (축소 불가) | ✅ (축소 가능) |

## 실제 테스트 결과

### 테스트 환경
- **Kubernetes 버전**: v1.31.x (K3s)
- **대상 워크로드**: Qdrant StatefulSet (ai-workloads namespace)
- **테스트 일자**: 2026-01-08

### 테스트 케이스

#### 1. Memory 증가 테스트
```bash
# 변경 전: 2Gi → 변경 후: 3Gi
kubectl patch sts qdrant -n ai-workloads --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "3Gi"}]'

# cgroup 확인
kubectl exec -n ai-workloads qdrant-0 -- cat /sys/fs/cgroup/memory.max
# 결과: 3221225472 (3Gi)
```
✅ **성공** - Pod 재시작 없이 즉시 적용됨

#### 2. CPU 증가 테스트
```bash
# 변경 전: 1 → 변경 후: 2
kubectl patch sts qdrant -n ai-workloads --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/cpu", "value": "2"}]'

# cgroup 확인
kubectl exec -n ai-workloads qdrant-0 -- cat /sys/fs/cgroup/cpu.max
# 결과: 200000 100000 (2 CPUs)
```
✅ **성공** - Pod 재시작 없이 즉시 적용됨

#### 3. Memory 감소 테스트
```bash
# 변경 전: 3Gi → 변경 후: 1Gi
kubectl patch sts qdrant -n ai-workloads --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "1Gi"}]'

# cgroup 확인
kubectl exec -n ai-workloads qdrant-0 -- cat /sys/fs/cgroup/memory.max
# 결과: 1073741824 (1Gi)
```
✅ **성공** - Pod 재시작 없이 즉시 적용됨

## 사용 방법

### StatefulSet 리소스 변경

```bash
# Memory 변경
kubectl patch sts <statefulset-name> -n <namespace> --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "<새값>"}]'

# CPU 변경
kubectl patch sts <statefulset-name> -n <namespace> --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/cpu", "value": "<새값>"}]'

# requests도 함께 변경 (권장)
kubectl patch sts <statefulset-name> -n <namespace> --type='json' \
  -p='[
    {"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/memory", "value": "<새값>"},
    {"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "<새값>"}
  ]'
```

### Deployment 리소스 변경

```bash
# Memory 변경
kubectl patch deployment <deployment-name> -n <namespace> --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "<새값>"}]'

# CPU 변경
kubectl patch deployment <deployment-name> -n <namespace> --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/cpu", "value": "<새값>"}]'
```

### 변경 확인 방법

```bash
# Pod 상태 확인 (재시작 횟수 확인)
kubectl get pods -n <namespace> -o wide

# cgroup으로 실제 적용된 값 확인
# Memory (bytes)
kubectl exec -n <namespace> <pod-name> -- cat /sys/fs/cgroup/memory.max

# CPU (quota period 형식: <quota> <period>)
kubectl exec -n <namespace> <pod-name> -- cat /sys/fs/cgroup/cpu.max
# 예: 200000 100000 = 2 CPUs (200000/100000)
```

## 워크로드별 권장 리소스

### AI/ML 워크로드

| 워크로드 | CPU | Memory | Storage | GPU |
|----------|-----|--------|---------|-----|
| **vLLM (LLaMA 7B)** | 2 | 8Gi | 50Gi | 1 (16GB VRAM) |
| **vLLM (LLaMA 13B)** | 4 | 16Gi | 100Gi | 1 (24GB VRAM) |
| **Qdrant** | 1 | 2Gi | 10Gi | - |
| **Neo4j** | 1 | 2Gi | 10Gi | - |
| **ComfyUI (SD 1.5)** | 2 | 4Gi | 15Gi | 1 (8GB VRAM) |
| **ComfyUI (SDXL)** | 2 | 8Gi | 20Gi | 1 (12GB VRAM) |
| **Langfuse** | 1 | 1Gi | 5Gi | - |

### 리소스 부족 징후 및 대응

| 증상 | 원인 | 대응 |
|------|------|------|
| OOMKilled | Memory 부족 | Memory limit 증가 |
| CPU Throttling | CPU 부족 | CPU limit 증가 |
| 느린 응답 시간 | 리소스 전반 부족 | CPU/Memory 동시 증가 |
| Pod Pending | 노드 리소스 부족 | 다른 워크로드 리소스 감소 또는 노드 추가 |

## 주의사항

### Memory 감소 시 주의점

1. **현재 사용량 확인 필수**
   ```bash
   kubectl top pod <pod-name> -n <namespace>
   ```

2. **사용량보다 낮게 설정 시 OOMKilled 발생 가능**
   - 현재 사용량의 1.2~1.5배 이상으로 설정 권장

### CPU 감소 시 주의점

1. **Throttling 발생 가능**
   - 처리 속도 저하될 수 있음
   - 응답 시간에 민감한 워크로드는 여유있게 설정

### 적용되지 않는 경우

1. **resizePolicy 설정이 RestartContainer인 경우**
   - 일부 워크로드는 재시작이 필요할 수 있음

2. **cgroup v1 사용 환경**
   - cgroup v2 필요 (대부분의 최신 Linux 배포판은 v2 사용)

3. **GPU 리소스**
   - GPU는 In-Place Scaling 미지원
   - Pod 재생성 필요

## 참고 자료

- [KEP-1287: In-Place Update of Pod Resources](https://github.com/kubernetes/enhancements/tree/master/keps/sig-node/1287-in-place-update-pod-resources)
- [Kubernetes 1.27 Release Notes - In-Place Pod Vertical Scaling](https://kubernetes.io/blog/2023/04/11/kubernetes-v1-27-release/#in-place-resource-resize-for-kubernetes-pods-alpha)
- [Kubernetes 1.31 Release Notes](https://kubernetes.io/blog/2024/08/13/kubernetes-v1-31-release/)

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-01-08 | 초기 문서 작성, 실제 테스트 결과 포함 |
