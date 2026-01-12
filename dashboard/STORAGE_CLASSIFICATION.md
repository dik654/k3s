# K3s 클러스터 스토리지 분류 규칙

## 개요

K3s 대시보드는 스토리지를 논리적으로 분류하여 표시합니다. 새로운 Pod나 PVC를 추가할 때 이 규칙에 맞춰 정의하면 대시보드에서 올바르게 분류됩니다.

## PVC (Persistent Volume Claim) 분류 규칙

### 1. 루트 디스크 사용 (Root Disk Usage)

**Storage Class**: `local-path`

루트 디스크의 스토리지를 사용하는 PVC입니다. 대시보드의 "루트 디스크 사용 현황" 섹션에 표시됩니다.

**사용 예시**:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-qdrant-0
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path  # 루트 디스크 사용
  resources:
    requests:
      storage: 10Gi
```

**특징**:
- Master 노드의 로컬 디스크에 저장됨
- 빠른 I/O 성능
- 노드에 종속적 (Pod가 다른 노드로 이동 불가)
- 백업 필요시 별도 처리 필요

**적합한 용도**:
- 데이터베이스 (PostgreSQL, MySQL, Qdrant 등)
- 캐시 저장소 (Redis)
- 로그 및 메트릭 저장소
- 개발/테스트 환경

---

### 2. 별도 스토리지 (Remote Storage)

**Storage Class**: `local-path` 이외의 모든 클래스

외부 스토리지나 네트워크 스토리지를 사용하는 PVC입니다. 대시보드의 "Persistent Volumes (별도 스토리지)" 섹션에 표시됩니다.

**사용 예시**:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-data
  namespace: default
spec:
  accessModes:
    - ReadWriteMany  # 여러 Pod에서 동시 접근 가능
  storageClassName: nfs-client  # 별도 스토리지 사용
  resources:
    requests:
      storage: 100Gi
```

**일반적인 Storage Class 예시**:
- `nfs-client`: NFS 네트워크 스토리지
- `ceph-rbd`: Ceph 블록 스토리지
- `longhorn`: Longhorn 분산 스토리지
- `portworx`: Portworx 스토리지
- `aws-ebs`: AWS Elastic Block Store
- `gce-pd`: Google Persistent Disk

**특징**:
- 네트워크를 통한 스토리지 접근
- Pod가 다른 노드로 이동 가능
- 고가용성 지원 가능
- 여러 Pod에서 동시 접근 가능 (ReadWriteMany)
- 자동 백업/복제 지원 (스토리지 솔루션에 따라 다름)

**적합한 용도**:
- 공유 파일 시스템
- 대용량 미디어 파일
- 프로덕션 환경의 중요 데이터
- 멀티 노드 클러스터에서 고가용성이 필요한 경우

---

## 루트 디스크 스토리지 카테고리

대시보드는 루트 디스크 사용량을 다음과 같이 세부 분류합니다:

### 카테고리 목록

| 타입 | 설명 | 경로 예시 |
|------|------|-----------|
| `rustfs` | RustFS/MinIO 스토리지 | `/mnt/rustfs/`, `/mnt/minio/` |
| `system` | 시스템 및 부팅 파일 | `/boot/`, `/usr/`, `/lib/` |
| `k3s` | K3s 클러스터 데이터 | `/var/lib/rancher/k3s/` |
| `docker` | Docker 이미지 및 컨테이너 | `/var/lib/docker/` |
| `pvc-local` | local-path PVC | `/var/lib/rancher/k3s/storage/` |
| `other` | 기타 파일 | 위 카테고리에 속하지 않는 모든 파일 |
| `free` | 사용 가능한 공간 | - |

### 분류 로직 (Backend)

```python
# main.py 참조
if "rustfs" in path or "minio" in path:
    category = "rustfs"
elif path.startswith("/boot") or path.startswith("/usr") or path.startswith("/lib"):
    category = "system"
elif "/rancher/k3s/" in path and "/storage/" not in path:
    category = "k3s"
elif "/docker/" in path:
    category = "docker"
elif storage_class == "local-path":
    category = "pvc-local"
else:
    category = "other"
```

---

## 추가 디스크 (HDD) 분류

Master 노드에 추가로 마운트된 HDD는 자동으로 감지되어 "추가 디스크 (HDD)" 섹션에 표시됩니다.

**감지 기준**:
- `/sys/block/{device}/queue/rotational` 값이 `1`인 디스크
- SSD는 `0`, HDD는 `1`

**사용 정보 표시**:
- 마운트되지 않음: "미할당"
- PVC 마운트: "PVC 마운트"
- Pod 사용: "Kubernetes Pod 사용"
- 일반 마운트: "마운트: /path/to/mount"

---

## 새 Pod 추가시 권장사항

### 1. 데이터베이스 Pod

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path  # 루트 디스크 사용 (빠른 I/O)
  resources:
    requests:
      storage: 20Gi
```

### 2. 공유 파일 스토리지

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-files
spec:
  accessModes:
    - ReadWriteMany  # 여러 Pod 동시 접근
  storageClassName: nfs-client  # 별도 스토리지 사용
  resources:
    requests:
      storage: 100Gi
```

### 3. 로그 수집기

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: logs-storage
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path  # 루트 디스크 사용 (임시 데이터)
  resources:
    requests:
      storage: 50Gi
```

---

## 트러블슈팅

### PVC가 대시보드에 표시되지 않는 경우

1. **PVC 상태 확인**:
   ```bash
   kubectl get pvc -A
   ```

2. **PV 바인딩 확인**:
   ```bash
   kubectl get pv
   ```

3. **Storage Class 확인**:
   ```bash
   kubectl get storageclass
   ```

### 잘못된 섹션에 표시되는 경우

- `local-path`를 사용하는데 "별도 스토리지"에 표시: Backend 로그 확인
- 별도 스토리지인데 "루트 디스크"에 표시: Storage Class 이름 확인

---

## 참고 자료

- **Backend 코드**: `/home/saiadmin/k3s-cluster/dashboard/backend/main.py`
  - PVC 분류 로직: Lines 4366-4389
  - 스토리지 사용량 API: Lines 3943-4090

- **Frontend 코드**: `/home/saiadmin/k3s-cluster/dashboard/frontend/src/pages/Overview/OverviewPage.tsx`
  - 루트 디스크 표시: Lines 457-480
  - 별도 스토리지 표시: Lines 542-548

- **Kubernetes Storage Classes**: https://kubernetes.io/docs/concepts/storage/storage-classes/
- **K3s Local Path Provisioner**: https://github.com/rancher/local-path-provisioner

---

**최종 수정일**: 2026-01-12
