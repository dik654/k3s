# AI Platform Storage Architecture

## 개요

K3s 클러스터 기반 AI 플랫폼을 위한 3-Tier 스토리지 아키텍처 설계 문서입니다.
SSD/HDD를 효율적으로 활용하여 성능과 비용을 최적화합니다.

---

## 목차

1. [아키텍처 개요](#아키텍처-개요)
2. [스토리지 계층 구조](#스토리지-계층-구조)
3. [데이터 분류 및 배치 전략](#데이터-분류-및-배치-전략)
4. [JuiceFS vs RustFS 비교](#juicefs-vs-rustfs-비교)
5. [구현 가이드](#구현-가이드)
6. [운영 가이드](#운영-가이드)

---

## 아키텍처 개요

### 클러스터 구성

```
┌────────────────────────────────────────────────────────────────┐
│  K3s Cluster (2 Nodes)                                         │
├─────────────────────────────┬──────────────────────────────────┤
│  Master Node (saiadmin)     │  Worker Node (filadmin)          │
│  14.32.100.220              │  14.32.100.232                   │
│                             │                                  │
│  역할: GPU 워크로드          │  역할: 스토리지 전용              │
│  - vLLM 추론                │  - JuiceFS 백엔드                │
│  - ComfyUI 이미지 생성       │  - 데이터 장기 보관              │
│  - 활성 모델 캐싱            │  - 웹 UI 파일 관리               │
└─────────────────────────────┴──────────────────────────────────┘
```

### 스토리지 솔루션 선택: JuiceFS

**선택 이유:**

1. **즉시 시작 가능**
   - Pod 시작 시 모델 다운로드 불필요 (30초 vs 5분)
   - 파일시스템 마운트로 바로 접근

2. **AI 워크로드 최적화**
   - 대용량 모델 파일 스트리밍
   - 자동 캐싱으로 재사용 시 빠름
   - 여러 Pod 간 캐시 공유

3. **확장성**
   - 노드 추가 시 자동으로 접근 가능
   - 중앙 집중식 관리

**트레이드오프:**

- 추가 리소스: +1.5Gi 메모리 (Redis + MinIO)
- 운영 복잡도 증가 (3개 컴포넌트 관리)
- **하지만 AI 서비스 특성상 감수할 가치 있음**

---

## 스토리지 계층 구조

### 3-Tier Storage Strategy

```
┌──────────────────────────────────────────────────────────┐
│  Tier 1: Hot Storage (SSD)                               │
│  - 실시간 접근 필요한 데이터                              │
│  - 지연시간: <10ms, IOPS: 높음                           │
│  - 크기: 200-300GB                                       │
├──────────────────────────────────────────────────────────┤
│  • 활성 모델 가중치 (배포 중인 모델)                      │
│  • JuiceFS 캐시                                          │
│  • Redis (활성 세션)                                     │
│  • 생성 중/최근 결과물                                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Tier 2: Warm Storage (SSD)                              │
│  - 자주 접근하는 데이터                                   │
│  - 지연시간: <50ms, IOPS: 중간                           │
│  - 크기: 100-200GB                                       │
├──────────────────────────────────────────────────────────┤
│  • PostgreSQL (유저 컨텍스트 30일)                        │
│  • JuiceFS 메타데이터 (Redis)                            │
│  • MinIO 인덱스                                          │
│  • 프롬프트 템플릿                                        │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Tier 3: Cold Storage (HDD)                              │
│  - 보관/백업 데이터                                       │
│  - 지연시간: <500ms, IOPS: 낮음                          │
│  - 크기: 1TB+                                            │
├──────────────────────────────────────────────────────────┤
│  • 미사용 모델 아카이브 (30일+)                           │
│  • PostgreSQL Archive (오래된 컨텍스트)                   │
│  • 생성 이미지 백업                                       │
│  • 로그 아카이브                                          │
└──────────────────────────────────────────────────────────┘
```

### 노드별 스토리지 배치

#### Master Node (saiadmin) - GPU 워크로드

```
/dev/nvme0n1 (SSD 500GB)
├─ /mnt/ssd/hot-models (200GB)
│  └─ JuiceFS Hot Cache
│     • llama-7b (13GB)
│     • llama-13b (26GB)
│     • stable-diffusion-xl (10GB)
│
├─ /mnt/ssd/user-context (50GB)
│  └─ PostgreSQL (활성 데이터)
│     • user_contexts (최근 7일)
│     • chat_sessions
│
└─ /mnt/ssd/temp (100GB)
   └─ 로컬 캐시
      • Pod emptyDir
      • 임시 작업 파일
```

#### Worker Node (filadmin) - 스토리지 전용

```
/dev/sda (SSD 200GB)
├─ /mnt/ssd/juicefs-meta (50GB)
│  └─ Redis (JuiceFS 메타데이터)
│     • 파일시스템 메타데이터
│     • 접근 통계
│
├─ /mnt/ssd/minio-index (50GB)
│  └─ MinIO 인덱스
│     • 객체 메타데이터
│
└─ /mnt/ssd/warm-db (100GB)
   └─ PostgreSQL Replica
      • user_contexts (최근 30일)

/dev/sdb (HDD 2TB)
├─ /mnt/hdd/minio-data (1.5TB)
│  └─ MinIO 데이터
│     • cold-models/
│     • generated-outputs/
│     • backups/
│
├─ /mnt/hdd/db-archive (300GB)
│  └─ PostgreSQL Archive
│     • user_contexts_archive
│
└─ /mnt/hdd/logs (200GB)
   └─ 로그 아카이브
      • application-logs/
      • audit-logs/
```

---

## 데이터 분류 및 배치 전략

### 1. 모델 가중치 (Hot/Cold 분리)

#### 데이터 특성

- **크기**: 7B 모델 ~13GB, 70B 모델 ~140GB
- **접근 패턴**: 배포 시 집중 읽기, 이후 재사용
- **생명주기**: 활성 → 미사용 → 아카이브

#### 저장 전략

```python
# Hot Storage (JuiceFS on SSD)
활성 모델 (배포 중):
- 위치: /mnt/juicefs/hot-models/
- 보관 기간: 마지막 접근 후 30일
- 자동 캐싱: 로컬 SSD에 캐시
- 접근 시간: <100ms (캐시 히트 시 <10ms)

# Cold Storage (MinIO on HDD)
비활성 모델:
- 위치: s3://cold-models/
- 보관 기간: 영구
- 승격 조건: 재배포 요청 시 Hot으로 자동 복사
- 접근 시간: 수 분 (복사 시간)
```

#### 자동화 정책

```yaml
정책:
  - 마지막 접근 후 30일 경과 → Hot에서 삭제 (Cold만 유지)
  - 재배포 요청 시 → Cold에서 Hot으로 자동 복사
  - 디스크 부족 시 → LRU 알고리즘으로 오래된 모델 제거

구현:
  - CronJob: cleanup-unused-models (매일 2시 실행)
  - 모니터링: model_locations 테이블
```

---

### 2. 유저 컨텍스트 (시간 기반 계층화)

#### 데이터 특성

- **크기**: 대화 1건당 ~10-100KB
- **접근 패턴**: 최근 대화는 빈번, 오래된 대화는 드물게
- **생명주기**: 실시간 → 최근 → 아카이브

#### 저장 전략

```python
# Tier 1: Redis (Hot - SSD)
활성 세션:
- 위치: Redis DB 1
- 보관 기간: 24시간 (TTL)
- 용량: ~10GB (약 10만 세션)
- 접근 시간: <1ms

# Tier 2: PostgreSQL (Warm - SSD)
최근 컨텍스트:
- 테이블: user_contexts
- 보관 기간: 30일
- 용량: ~50GB
- 접근 시간: <10ms

# Tier 3: PostgreSQL Archive (Cold - HDD)
오래된 컨텍스트:
- 테이블: user_contexts_archive
- 보관 기간: 1년 (이후 삭제 가능)
- 용량: ~300GB
- 접근 시간: <100ms
```

#### 데이터 흐름

```
[새 대화]
   ↓
Redis (24시간)
   ↓
PostgreSQL Warm (30일)
   ↓
PostgreSQL Cold (1년)
   ↓
[삭제 또는 영구 백업]

[다시 활성화]
Cold → Warm → Redis
(자동 승격)
```

#### 자동화 정책

```yaml
정책:
  - 24시간 경과 → Redis에서 자동 만료
  - 30일 경과 → Warm에서 Cold로 이동
  - 1년 경과 → 삭제 또는 S3 Glacier 백업

구현:
  - Redis TTL: 자동
  - CronJob: archive-old-contexts (매일 3시 실행)
  - 백업: 월 1회 전체 백업
```

---

### 3. 생성 결과물 (이미지, 오디오 등)

#### 데이터 특성

- **크기**: 이미지 1-10MB, 오디오 10-100MB
- **접근 패턴**: 생성 직후 빈번, 이후 드물게
- **생명주기**: 최근 → 백업 → 선택적 삭제

#### 저장 전략

```python
# Hot Storage (JuiceFS on SSD)
최근 결과물:
- 위치: /mnt/juicefs/outputs/
- 보관 기간: 7일
- 접근: 즉시 다운로드 가능
- 용량: ~100GB

# Cold Storage (MinIO on HDD)
백업 및 장기 보관:
- 위치: s3://generated-outputs/
- 보관 기간: 영구 (사용자 삭제 전까지)
- 접근: 5초 이내 (HDD 읽기)
- 용량: ~1TB
```

#### 파일 구조

```
/user_id/YYYY/MM/DD/uuid.{png,jpg,mp3,wav}

예시:
/user123/2026/01/12/a1b2c3d4-e5f6-7890-abcd-ef1234567890.png
```

#### 자동화 정책

```yaml
정책:
  - 7일 경과 → Hot Storage에서 삭제 (Cold만 유지)
  - 접근 빈도 높음 (5회+) → 자동으로 Hot으로 재승격
  - 사용자 삭제 요청 → 모든 계층에서 삭제

구현:
  - CronJob: cleanup-old-outputs (매일 4시 실행)
  - 모니터링: generated_outputs 테이블
```

---

## JuiceFS vs RustFS 비교

### 기술 비교

| 항목 | JuiceFS | RustFS |
|------|---------|--------|
| **타입** | 분산 POSIX 파일시스템 | S3 호환 객체 스토리지 |
| **주요 사용법** | 파일시스템 마운트 | S3 API |
| **접근 방식** | `/mnt/juicefs/file.pt` | `s3://bucket/file.pt` |
| **Pod 접근** | 즉시 접근 가능 | 다운로드 후 사용 |

### 성능 비교

#### 시나리오: Llama-70B 모델 (70GB) 로드

**RustFS:**
```
Pod 시작
  ↓
initContainer: S3 다운로드 (5분)
  ↓
로컬 디스크에 저장 (/tmp/model)
  ↓
메인 컨테이너 시작
  ↓
vLLM 로드 (30초)

총 시간: 5분 30초
```

**JuiceFS:**
```
Pod 시작
  ↓
JuiceFS 마운트 (즉시)
  ↓
메인 컨테이너 시작
  ↓
vLLM 로드 (필요한 부분만 스트리밍, 30초)

총 시간: 30초
캐시 히트 시: 10초
```

### 리소스 비교 (2노드 클러스터)

**RustFS:**
```
메모리: 512Mi
CPU: 500m
컴포넌트: 1개 (RustFS)
```

**JuiceFS:**
```
메모리: 1.5Gi (Redis 512Mi + MinIO 512Mi + CSI 512Mi)
CPU: 700m
컴포넌트: 3개 (Redis + MinIO + CSI Driver)

추가 비용: +1Gi 메모리, +200m CPU
```

### 선택 기준

| 상황 | 권장 솔루션 |
|------|------------|
| **AI 워크로드 (모델 추론)** | **JuiceFS** - 즉시 시작, 캐싱 |
| **단순 파일 저장/공유** | RustFS - 간단, 웹 UI |
| **소규모 파일 대량 처리** | RustFS - 고성능 |
| **여러 Pod 동일 파일 접근** | **JuiceFS** - 캐시 공유 |
| **최소 리소스 환경** | RustFS - 낮은 오버헤드 |

### 최종 선택: JuiceFS

**이유:**

1. **AI 워크로드 특성상 필수**
   - 대용량 모델 파일 (수십~수백 GB)
   - Pod 즉시 시작 필요 (Auto-scaling)
   - 여러 Pod 동일 모델 공유

2. **운영 효율**
   - 모델 다운로드 시간 절약 (5분 → 30초)
   - 네트워크 대역폭 절약 (캐시 공유)
   - 디스크 공간 절약 (중복 저장 방지)

3. **확장성**
   - 노드 추가 시 자동 접근
   - 중앙 집중식 관리

**트레이드오프 감수:**
- 추가 메모리 1Gi는 Pod 시작 시간 절약으로 상쇄
- 운영 복잡도는 문서화 및 자동화로 해결

---

## 구현 가이드

### Phase 1: JuiceFS 기본 설치

#### 1.1 네임스페이스 생성

```bash
kubectl create namespace storage
```

#### 1.2 Redis 배포 (메타데이터)

파일: `k8s/storage/redis.yaml`

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-data-pvc
  namespace: storage
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 10Gi

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: juicefs-redis
  namespace: storage
spec:
  replicas: 1
  selector:
    matchLabels:
      app: juicefs-redis
  template:
    metadata:
      labels:
        app: juicefs-redis
    spec:
      nodeSelector:
        kubernetes.io/hostname: filadmin-192-168-10-2-server
      containers:
      - name: redis
        image: redis:7-alpine
        args:
          - --appendonly yes
          - --save 60 1
          - --maxmemory 512mb
          - --maxmemory-policy allkeys-lru
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: 512Mi
            cpu: 250m
          limits:
            memory: 1Gi
            cpu: 500m
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: redis-data-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: juicefs-redis
  namespace: storage
spec:
  type: ClusterIP
  ports:
  - port: 6379
    targetPort: 6379
  selector:
    app: juicefs-redis
```

배포:
```bash
kubectl apply -f k8s/storage/redis.yaml
```

#### 1.3 MinIO 배포 (데이터 백엔드)

파일: `k8s/storage/minio.yaml`

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-data-pvc
  namespace: storage
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 500Gi

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: juicefs-minio
  namespace: storage
spec:
  replicas: 1
  selector:
    matchLabels:
      app: juicefs-minio
  template:
    metadata:
      labels:
        app: juicefs-minio
    spec:
      nodeSelector:
        kubernetes.io/hostname: filadmin-192-168-10-2-server
      containers:
      - name: minio
        image: minio/minio:latest
        args:
          - server
          - /data
          - --console-address
          - ":9001"
        env:
        - name: MINIO_ROOT_USER
          value: "admin"
        - name: MINIO_ROOT_PASSWORD
          value: "changeme123"  # ⚠️ 프로덕션에서는 Secret 사용
        ports:
        - containerPort: 9000
          name: api
        - containerPort: 9001
          name: console
        resources:
          requests:
            memory: 512Mi
            cpu: 250m
          limits:
            memory: 1Gi
            cpu: 500m
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: minio-data-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: juicefs-minio
  namespace: storage
spec:
  type: ClusterIP
  ports:
  - port: 9000
    targetPort: 9000
    name: api
  - port: 9001
    targetPort: 9001
    name: console
  selector:
    app: juicefs-minio
```

배포:
```bash
kubectl apply -f k8s/storage/minio.yaml
```

#### 1.4 JuiceFS 파일시스템 생성

MinIO 버킷 생성:
```bash
# MinIO Pod에 접속
kubectl exec -it -n storage deployment/juicefs-minio -- sh

# mc 설정
mc alias set myminio http://localhost:9000 admin changeme123

# 버킷 생성
mc mb myminio/juicefs-data
mc mb myminio/cold-models
mc mb myminio/generated-outputs

exit
```

JuiceFS 포맷:
```bash
# 임시 Pod에서 실행
kubectl run juicefs-format -n storage --rm -it \
  --image=juicedata/mount:latest \
  --restart=Never -- \
  juicefs format \
  --storage minio \
  --bucket http://juicefs-minio:9000/juicefs-data \
  --access-key admin \
  --secret-key changeme123 \
  redis://juicefs-redis:6379/0 \
  ai-platform
```

#### 1.5 JuiceFS CSI Driver 설치

Helm 설치:
```bash
helm repo add juicefs https://juicedata.github.io/charts/
helm repo update

helm install juicefs-csi-driver juicefs/juicefs-csi-driver \
  --namespace kube-system \
  --set storageClasses[0].enabled=true \
  --set storageClasses[0].name=juicefs \
  --set storageClasses[0].backend.name=ai-platform \
  --set storageClasses[0].backend.metaurl=redis://juicefs-redis.storage:6379/0 \
  --set storageClasses[0].backend.storage=minio \
  --set storageClasses[0].backend.bucket=http://juicefs-minio.storage:9000/juicefs-data \
  --set storageClasses[0].backend.accessKey=admin \
  --set storageClasses[0].backend.secretKey=changeme123
```

확인:
```bash
kubectl get pods -n kube-system | grep juicefs
kubectl get storageclass juicefs
```

---

### Phase 2: StorageClass 구성

파일: `k8s/storage/storage-classes.yaml`

```yaml
---
# Hot Storage - GPU 노드용
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: juicefs-gpu-hot
provisioner: csi.juicefs.com
parameters:
  juicefs/mount-cache-dir: "/var/jfsCache"
  juicefs/cache-size: "204800"  # 200GB
  juicefs/free-space-ratio: "0.1"
mountOptions:
  - writeback
  - cache-size=204800
  - free-space-ratio=0.1
volumeBindingMode: Immediate
reclaimPolicy: Retain

---
# Shared Storage - 공용
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: juicefs-shared
provisioner: csi.juicefs.com
parameters:
  juicefs/mount-cache-dir: "/var/jfsCache"
  juicefs/cache-size: "102400"  # 100GB
mountOptions:
  - cache-size=102400
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
```

배포:
```bash
kubectl apply -f k8s/storage/storage-classes.yaml
```

---

### Phase 3: PVC 생성

파일: `k8s/storage/pvcs.yaml`

```yaml
---
# GPU 워크로드용 PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: juicefs-gpu-models
  namespace: ai-services
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: juicefs-gpu-hot
  resources:
    requests:
      storage: 200Gi

---
# 공유 스토리지 PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: juicefs-shared-data
  namespace: ai-services
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: juicefs-shared
  resources:
    requests:
      storage: 500Gi
```

배포:
```bash
kubectl apply -f k8s/storage/pvcs.yaml
```

확인:
```bash
kubectl get pvc -n ai-services
```

---

### Phase 4: 데이터베이스 설정

#### 4.1 PostgreSQL 배포

파일: `k8s/storage/postgresql.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-init
  namespace: storage
data:
  init.sql: |
    -- 모델 위치 추적
    CREATE TABLE IF NOT EXISTS model_locations (
        model_id VARCHAR(255) PRIMARY KEY,
        tier VARCHAR(10) NOT NULL CHECK (tier IN ('hot', 'cold')),
        size_bytes BIGINT NOT NULL,
        last_access TIMESTAMP NOT NULL DEFAULT NOW(),
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_model_last_access ON model_locations(last_access);
    CREATE INDEX IF NOT EXISTS idx_model_tier ON model_locations(tier);

    -- 사용자 컨텍스트 (Warm)
    CREATE TABLE IF NOT EXISTS user_contexts (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        conversation_id VARCHAR(255) NOT NULL,
        messages JSONB NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, conversation_id)
    );
    CREATE INDEX IF NOT EXISTS idx_user_updated ON user_contexts(user_id, updated_at);
    CREATE INDEX IF NOT EXISTS idx_updated_at ON user_contexts(updated_at);

    -- 사용자 컨텍스트 아카이브 (Cold)
    CREATE TABLE IF NOT EXISTS user_contexts_archive (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        conversation_id VARCHAR(255) NOT NULL,
        messages JSONB NOT NULL,
        created_at TIMESTAMP NOT NULL,
        archived_at TIMESTAMP NOT NULL DEFAULT NOW(),
        UNIQUE (user_id, conversation_id)
    );
    CREATE INDEX IF NOT EXISTS idx_archive_user ON user_contexts_archive(user_id, conversation_id);

    -- 생성 결과물 메타데이터
    CREATE TABLE IF NOT EXISTS generated_outputs (
        output_id UUID PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        filename VARCHAR(500) NOT NULL,
        output_type VARCHAR(50) NOT NULL,
        size_bytes BIGINT,
        hot_storage BOOLEAN DEFAULT true,
        cold_storage BOOLEAN DEFAULT true,
        access_count INT DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        last_accessed TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_output_user ON generated_outputs(user_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_output_hot ON generated_outputs(hot_storage, created_at);

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: storage
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        env:
        - name: POSTGRES_DB
          value: ai_platform
        - name: POSTGRES_USER
          value: platform
        - name: POSTGRES_PASSWORD
          value: changeme123  # ⚠️ Secret 사용 권장
        ports:
        - containerPort: 5432
        resources:
          requests:
            memory: 512Mi
            cpu: 250m
          limits:
            memory: 1Gi
            cpu: 500m
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        - name: init
          mountPath: /docker-entrypoint-initdb.d
      volumes:
      - name: init
        configMap:
          name: postgres-init
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: local-path
      resources:
        requests:
          storage: 50Gi

---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: storage
spec:
  type: ClusterIP
  ports:
  - port: 5432
  selector:
    app: postgres
```

배포:
```bash
kubectl apply -f k8s/storage/postgresql.yaml
```

---

### Phase 5: 백엔드 코드 통합

#### 5.1 모델 스토리지 컨트롤러

파일: `backend/app/controllers/model_storage_controller.py`

```python
"""
모델 가중치 스토리지 관리
Hot/Cold 티어 자동 관리
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import asyncpg
from app.config import settings


class ModelStorageController:
    """모델 스토리지 Hot/Cold 티어 관리"""

    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.juicefs_base = "/mnt/juicefs"

    async def initialize(self):
        """데이터베이스 연결 초기화"""
        self.db_pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )

    async def get_model_path(self, model_id: str) -> str:
        """
        모델 경로 반환
        Cold Storage에 있으면 Hot으로 자동 승격
        """
        # 모델 위치 확인
        async with self.db_pool.acquire() as conn:
            location = await conn.fetchrow(
                """
                SELECT tier, last_access
                FROM model_locations
                WHERE model_id = $1
                """,
                model_id
            )

        if not location:
            # 첫 사용 - Cold에서 Hot으로
            await self._promote_to_hot(model_id)
        elif location['tier'] == 'cold':
            # Cold에서 Hot으로 승격
            await self._promote_to_hot(model_id)

        # 접근 시간 업데이트
        await self._update_last_access(model_id)

        return f"{self.juicefs_base}/models/{model_id}"

    async def _promote_to_hot(self, model_id: str):
        """Cold → Hot 승격"""
        # JuiceFS는 자동으로 캐싱하므로 경로만 반환
        # 실제 복사는 JuiceFS가 처리

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO model_locations
                (model_id, tier, size_bytes, last_access)
                VALUES ($1, 'hot', 0, NOW())
                ON CONFLICT (model_id)
                DO UPDATE SET tier = 'hot', last_access = NOW()
                """,
                model_id
            )

    async def _update_last_access(self, model_id: str):
        """마지막 접근 시간 업데이트"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE model_locations
                SET last_access = NOW()
                WHERE model_id = $1
                """,
                model_id
            )

    async def cleanup_unused_models(self, days: int = 30):
        """
        미사용 모델 정리 (CronJob에서 호출)
        30일 이상 미사용 → Cold로 강등
        """
        threshold = datetime.utcnow() - timedelta(days=days)

        async with self.db_pool.acquire() as conn:
            # 미사용 모델 조회
            unused = await conn.fetch(
                """
                SELECT model_id
                FROM model_locations
                WHERE tier = 'hot'
                  AND last_access < $1
                """,
                threshold
            )

            for row in unused:
                model_id = row['model_id']

                # Cold로 변경 (JuiceFS 캐시는 자동 정리됨)
                await conn.execute(
                    """
                    UPDATE model_locations
                    SET tier = 'cold'
                    WHERE model_id = $1
                    """,
                    model_id
                )

                print(f"Model {model_id} demoted to cold storage")

        return len(unused)
```

#### 5.2 사용자 컨텍스트 매니저

파일: `backend/app/models/user_context.py`

```python
"""
사용자 컨텍스트 3-tier 관리
Redis (Hot) → PostgreSQL (Warm) → PostgreSQL Archive (Cold)
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncpg
import redis.asyncio as aioredis


class UserContextManager:
    """사용자 대화 컨텍스트 관리"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.pg_pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """초기화"""
        # Redis 연결
        self.redis = await aioredis.from_url(
            "redis://juicefs-redis.storage:6379/1",
            decode_responses=True
        )

        # PostgreSQL 연결
        self.pg_pool = await asyncpg.create_pool(
            host="postgres.storage",
            database="ai_platform",
            user="platform",
            password="changeme123"
        )

    async def save_context(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict]
    ):
        """컨텍스트 저장 (Hot + Warm)"""
        context_key = f"context:{user_id}:{conversation_id}"
        context_data = {
            "messages": messages,
            "updated_at": datetime.utcnow().isoformat()
        }

        # 1. Redis (Hot) - 24시간
        await self.redis.setex(
            context_key,
            86400,  # 24시간
            json.dumps(context_data)
        )

        # 2. PostgreSQL (Warm) - 영구
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_contexts
                (user_id, conversation_id, messages, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id, conversation_id)
                DO UPDATE SET messages = $3, updated_at = NOW()
                """,
                user_id, conversation_id, json.dumps(messages)
            )

    async def get_context(
        self,
        user_id: str,
        conversation_id: str
    ) -> Optional[List[Dict]]:
        """컨텍스트 조회 (Hot → Warm → Cold)"""
        context_key = f"context:{user_id}:{conversation_id}"

        # 1. Redis (Hot) 확인
        cached = await self.redis.get(context_key)
        if cached:
            data = json.loads(cached)
            return data['messages']

        # 2. PostgreSQL Warm 확인
        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT messages
                FROM user_contexts
                WHERE user_id = $1 AND conversation_id = $2
                """,
                user_id, conversation_id
            )

            if row:
                messages = json.loads(row['messages'])

                # Redis에 캐시
                await self.redis.setex(
                    context_key,
                    3600,  # 1시간
                    json.dumps({
                        "messages": messages,
                        "updated_at": datetime.utcnow().isoformat()
                    })
                )

                return messages

            # 3. PostgreSQL Cold 확인
            row = await conn.fetchrow(
                """
                SELECT messages
                FROM user_contexts_archive
                WHERE user_id = $1 AND conversation_id = $2
                """,
                user_id, conversation_id
            )

            if row:
                messages = json.loads(row['messages'])

                # Warm으로 승격
                await self._promote_to_warm(
                    user_id, conversation_id, messages
                )

                return messages

        return None

    async def _promote_to_warm(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict]
    ):
        """Cold → Warm 승격"""
        async with self.pg_pool.acquire() as conn:
            # Warm에 추가
            await conn.execute(
                """
                INSERT INTO user_contexts
                (user_id, conversation_id, messages, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id, conversation_id)
                DO UPDATE SET messages = $3, updated_at = NOW()
                """,
                user_id, conversation_id, json.dumps(messages)
            )

            # Cold에서 삭제
            await conn.execute(
                """
                DELETE FROM user_contexts_archive
                WHERE user_id = $1 AND conversation_id = $2
                """,
                user_id, conversation_id
            )

    async def archive_old_contexts(self, days: int = 30):
        """오래된 컨텍스트 아카이브 (CronJob)"""
        threshold = datetime.utcnow() - timedelta(days=days)

        async with self.pg_pool.acquire() as conn:
            # Warm → Cold 이동
            archived = await conn.fetch(
                """
                WITH old_contexts AS (
                    DELETE FROM user_contexts
                    WHERE updated_at < $1
                    RETURNING user_id, conversation_id, messages, created_at
                )
                INSERT INTO user_contexts_archive
                (user_id, conversation_id, messages, created_at, archived_at)
                SELECT user_id, conversation_id, messages, created_at, NOW()
                FROM old_contexts
                RETURNING user_id, conversation_id
                """,
                threshold
            )

            return len(archived)
```

---

### Phase 6: CronJob 설정

파일: `k8s/storage/cronjobs.yaml`

```yaml
---
# 모델 정리 Job
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cleanup-unused-models
  namespace: ai-services
spec:
  schedule: "0 2 * * *"  # 매일 2시
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: cleanup
            image: platform-backend:latest
            command:
              - python
              - -c
              - |
                import asyncio
                from app.controllers.model_storage_controller import ModelStorageController

                async def main():
                    controller = ModelStorageController()
                    await controller.initialize()
                    count = await controller.cleanup_unused_models(days=30)
                    print(f"Cleaned up {count} models")

                asyncio.run(main())
            env:
            - name: POSTGRES_HOST
              value: postgres.storage
            - name: POSTGRES_DB
              value: ai_platform
            - name: POSTGRES_USER
              value: platform
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password

---
# 컨텍스트 아카이브 Job
apiVersion: batch/v1
kind: CronJob
metadata:
  name: archive-old-contexts
  namespace: ai-services
spec:
  schedule: "0 3 * * *"  # 매일 3시
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: archive
            image: platform-backend:latest
            command:
              - python
              - -c
              - |
                import asyncio
                from app.models.user_context import UserContextManager

                async def main():
                    manager = UserContextManager()
                    await manager.initialize()
                    count = await manager.archive_old_contexts(days=30)
                    print(f"Archived {count} contexts")

                asyncio.run(main())
```

배포:
```bash
kubectl apply -f k8s/storage/cronjobs.yaml
```

수동 실행 (테스트):
```bash
kubectl create job --from=cronjob/cleanup-unused-models manual-cleanup -n ai-services
kubectl logs -f job/manual-cleanup -n ai-services
```

---

## 운영 가이드

### 모니터링

#### 1. 스토리지 사용량 확인

```bash
# JuiceFS 상태
kubectl exec -n storage deployment/juicefs-redis -- redis-cli INFO stats

# MinIO 사용량
kubectl port-forward -n storage svc/juicefs-minio 9001:9001
# 브라우저: http://localhost:9001

# PVC 사용량
kubectl get pvc -n ai-services
kubectl describe pvc juicefs-gpu-models -n ai-services
```

#### 2. 데이터베이스 모니터링

```bash
# PostgreSQL 접속
kubectl exec -it -n storage statefulset/postgres -- psql -U platform -d ai_platform

# 테이블 크기 확인
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# 모델 티어 분포
SELECT tier, COUNT(*), SUM(size_bytes)/1024/1024/1024 AS gb
FROM model_locations
GROUP BY tier;

# 오래된 컨텍스트 확인
SELECT
  COUNT(*) AS count,
  SUM(pg_column_size(messages))/1024/1024 AS size_mb
FROM user_contexts
WHERE updated_at < NOW() - INTERVAL '30 days';
```

#### 3. 캐시 히트율

```bash
# JuiceFS 메트릭 (Prometheus 설정 필요)
kubectl port-forward -n kube-system svc/juicefs-csi-controller 9567:9567

# 브라우저: http://localhost:9567/metrics
# 확인 항목:
# - juicefs_blockcache_hit_ratio
# - juicefs_blockcache_miss
```

---

### 백업 및 복구

#### 1. 데이터베이스 백업

```bash
# PostgreSQL 백업
kubectl exec -n storage statefulset/postgres-0 -- \
  pg_dump -U platform ai_platform > backup-$(date +%Y%m%d).sql

# 복원
kubectl exec -i -n storage statefulset/postgres-0 -- \
  psql -U platform ai_platform < backup-20260112.sql
```

#### 2. JuiceFS 백업

```bash
# MinIO 데이터 백업 (mc 사용)
kubectl exec -n storage deployment/juicefs-minio -- \
  mc mirror myminio/juicefs-data /backup/juicefs-data

# Redis 메타데이터 백업
kubectl exec -n storage deployment/juicefs-redis -- \
  redis-cli SAVE

kubectl cp storage/juicefs-redis-xxx:/data/dump.rdb ./redis-backup.rdb
```

#### 3. 전체 백업 스크립트

파일: `scripts/backup-storage.sh`

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

echo "Backing up PostgreSQL..."
kubectl exec -n storage statefulset/postgres-0 -- \
  pg_dump -U platform ai_platform > $BACKUP_DIR/postgres.sql

echo "Backing up Redis..."
kubectl exec -n storage deployment/juicefs-redis -- redis-cli SAVE
kubectl cp storage/juicefs-redis-0:/data/dump.rdb $BACKUP_DIR/redis.rdb

echo "Backing up MinIO metadata..."
kubectl exec -n storage deployment/juicefs-minio -- \
  mc mirror myminio/juicefs-data $BACKUP_DIR/minio-data

echo "Backup completed: $BACKUP_DIR"
```

실행:
```bash
chmod +x scripts/backup-storage.sh
./scripts/backup-storage.sh
```

---

### 트러블슈팅

#### 문제 1: JuiceFS 마운트 실패

**증상:**
```
Pod pending, event: "MountVolume.MountDevice failed"
```

**확인:**
```bash
# CSI Driver 상태
kubectl get pods -n kube-system | grep juicefs

# CSI Node 로그
kubectl logs -n kube-system daemonset/juicefs-csi-node -c juicefs-plugin

# Redis 연결 확인
kubectl exec -n storage deployment/juicefs-redis -- redis-cli PING
```

**해결:**
```bash
# CSI Driver 재시작
kubectl rollout restart daemonset/juicefs-csi-node -n kube-system

# PVC 재생성
kubectl delete pvc juicefs-gpu-models -n ai-services
kubectl apply -f k8s/storage/pvcs.yaml
```

#### 문제 2: 디스크 부족

**증상:**
```
Error: no space left on device
```

**확인:**
```bash
# 노드 디스크 사용량
kubectl get nodes
kubectl describe node saiadmin-system-product-name

# JuiceFS 캐시 사용량
kubectl exec -n kube-system daemonset/juicefs-csi-node -- \
  df -h /var/jfsCache
```

**해결:**
```bash
# 캐시 수동 정리
kubectl exec -n kube-system daemonset/juicefs-csi-node -- \
  rm -rf /var/jfsCache/*

# 오래된 모델 강제 정리
kubectl create job --from=cronjob/cleanup-unused-models force-cleanup -n ai-services
```

#### 문제 3: 성능 저하

**증상:**
모델 로딩이 느림

**확인:**
```bash
# JuiceFS 캐시 히트율
kubectl exec -n kube-system daemonset/juicefs-csi-node -- \
  juicefs stats /jfs

# MinIO 성능
kubectl exec -n storage deployment/juicefs-minio -- \
  mc admin info myminio
```

**해결:**
```bash
# 캐시 크기 증가
kubectl patch storageclass juicefs-gpu-hot -p '{"parameters":{"juicefs/cache-size":"307200"}}'

# MinIO 리소스 증가
kubectl patch deployment juicefs-minio -n storage -p '{"spec":{"template":{"spec":{"containers":[{"name":"minio","resources":{"limits":{"memory":"2Gi","cpu":"1000m"}}}]}}}}'
```

---

### 성능 튜닝

#### 1. JuiceFS 캐시 최적화

```yaml
# StorageClass 파라미터 조정
parameters:
  juicefs/cache-size: "307200"  # 300GB (기본 200GB)
  juicefs/buffer-size: "1024"   # 1GB (기본 300MB)
  juicefs/prefetch: "1"         # Prefetch 활성화
  juicefs/writeback: "true"     # Write-back 캐싱
```

#### 2. PostgreSQL 튜닝

```sql
-- postgresql.conf 설정
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';

-- 인덱스 최적화
REINDEX TABLE user_contexts;
ANALYZE user_contexts;
```

#### 3. Redis 튜닝

```bash
# redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

---

### 비용 최적화

#### 현재 리소스 사용량

```yaml
총 메모리 사용량:
  Redis:      512Mi
  MinIO:      512Mi
  PostgreSQL: 512Mi
  CSI Driver: 512Mi (2노드)
  ────────────────
  합계:       ~2Gi

총 CPU 사용량:
  Redis:      250m
  MinIO:      250m
  PostgreSQL: 250m
  CSI Driver: 400m (2노드)
  ────────────────
  합계:       ~1.15 cores
```

#### 절감 방안

1. **Redis 메모리 최적화**
   ```bash
   # 사용하지 않는 데이터 정리
   redis-cli --scan --pattern "context:*" | \
     xargs -L 1000 redis-cli DEL
   ```

2. **오래된 데이터 삭제**
   ```sql
   -- 1년 초과 아카이브 삭제
   DELETE FROM user_contexts_archive
   WHERE archived_at < NOW() - INTERVAL '1 year';
   ```

3. **MinIO 압축**
   ```bash
   # 오래된 이미지 압축
   find /mnt/hdd/minio-data/generated-outputs \
     -mtime +30 -name "*.png" \
     -exec convert {} -quality 80 {} \;
   ```

---

## 참고 자료

- [JuiceFS Documentation](https://juicefs.com/docs/community/introduction/)
- [MinIO Documentation](https://min.io/docs/minio/kubernetes/upstream/)
- [K3s Storage Documentation](https://docs.k3s.io/storage)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-01-12 | 1.0 | 초안 작성 |

---

## 문의

기술 지원이 필요하거나 문의사항이 있으면 다음을 참고하세요:

- GitHub Issues: [프로젝트 저장소]
- 내부 문서: `/home/saiadmin/k3s-cluster/docs/`
