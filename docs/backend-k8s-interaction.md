# K3s 대시보드 백엔드 - Kubernetes 상호작용 가이드

## 개요

백엔드는 Python Kubernetes 클라이언트(`kubernetes` 라이브러리)를 통해 K3s API 서버와 통신합니다.
Pod 내부에서 실행될 때는 ServiceAccount 토큰을 사용하고, 외부에서 실행될 때는 kubeconfig를 사용합니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         K3s Cluster                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    K3s API Server                            │   │
│  │  - CoreV1Api: Pods, Services, Nodes, Namespaces, Events     │   │
│  │  - AppsV1Api: Deployments, StatefulSets, DaemonSets         │   │
│  │  - CustomObjectsApi: Longhorn, CRDs                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▲                                       │
│                              │ HTTPS (인증: ServiceAccount Token)   │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────┐     │
│  │              Dashboard Backend (FastAPI)                   │     │
│  │  ┌─────────────────────────────────────────────────────┐ │     │
│  │  │  kubernetes-python client                           │ │     │
│  │  │  - config.load_incluster_config()                   │ │     │
│  │  │  - 자동으로 /var/run/secrets/... 토큰 사용          │ │     │
│  │  └─────────────────────────────────────────────────────┘ │     │
│  │                                                           │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │     │
│  │  │  Cluster    │  │  Workloads  │  │     GPU     │      │     │
│  │  │  Router     │  │   Router    │  │   Router    │      │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │     │
│  └───────────────────────────────────────────────────────────┘     │
│                              │                                       │
│                              │ HTTP                                  │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │              External Services (Pod 내부)                  │     │
│  │  vLLM, Neo4j, MinIO, Qdrant, ComfyUI, RAGflow            │     │
│  └───────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

## 핵심 모듈

### 1. Kubernetes 클라이언트 초기화

**파일**: `core/kubernetes.py`, `utils/k8s.py`

```python
from kubernetes import client, config

def get_k8s_clients():
    """Kubernetes API 클라이언트 초기화"""
    try:
        # Pod 내부에서 실행 시: ServiceAccount 토큰 자동 사용
        # 위치: /var/run/secrets/kubernetes.io/serviceaccount/token
        config.load_incluster_config()
    except config.ConfigException:
        # 로컬 개발 시: ~/.kube/config 파일 사용
        config.load_kube_config()

    return (
        client.CoreV1Api(),      # Pods, Nodes, Services, Events
        client.AppsV1Api(),      # Deployments, StatefulSets
        client.CustomObjectsApi() # Longhorn CRDs
    )
```

**인증 흐름**:
1. Pod 시작 → ServiceAccount 마운트됨
2. `load_incluster_config()` → 토큰 파일 읽기
3. API 요청 시 `Authorization: Bearer <token>` 헤더 자동 추가

---

## 기능별 K8s 상호작용

### 2. Cluster Router (`routers/cluster/`)

#### 2.1 클러스터 상태 조회

**엔드포인트**: `GET /api/cluster/status`

```python
@router.get("/cluster/status")
async def get_cluster_status():
    core_v1, apps_v1, _ = get_k8s_clients()

    # 노드 목록 조회 (K8s API: GET /api/v1/nodes)
    nodes = core_v1.list_node()

    # 노드 Ready 상태 확인
    ready_nodes = sum(1 for n in nodes.items
                     if any(c.type == "Ready" and c.status == "True"
                           for c in n.status.conditions))

    # 모든 Pod 조회 (K8s API: GET /api/v1/pods)
    pods = core_v1.list_pod_for_all_namespaces()
    running_pods = sum(1 for p in pods.items if p.status.phase == "Running")

    return {
        "status": "healthy" if ready_nodes == node_count else "degraded",
        "nodes": {"total": node_count, "ready": ready_nodes},
        "pods": {"running": running_pods, "total": len(pods.items)}
    }
```

**K8s API 호출**:
| 메서드 | K8s API | 목적 |
|--------|---------|------|
| `list_node()` | `GET /api/v1/nodes` | 모든 노드 목록 |
| `list_pod_for_all_namespaces()` | `GET /api/v1/pods` | 모든 Pod 목록 |
| `list_namespace()` | `GET /api/v1/namespaces` | 네임스페이스 목록 |

#### 2.2 노드 상세 정보

```python
@router.get("/nodes")
async def get_nodes():
    core_v1, _, _ = get_k8s_clients()
    nodes = core_v1.list_node()

    for node in nodes.items:
        # 노드 리소스 정보
        capacity = node.status.capacity    # 총 리소스
        allocatable = node.status.allocatable  # 할당 가능한 리소스

        # GPU 정보 (nvidia device plugin이 추가한 리소스)
        gpu_count = int(capacity.get("nvidia.com/gpu", "0"))

        # 노드 라벨에서 GPU 타입 추출
        labels = node.metadata.labels
        gpu_type = labels.get("nvidia.com/gpu.product", "Unknown")
```

---

### 3. Workloads Router (`routers/cluster/workloads.py`)

#### 3.1 워크로드 상태 조회

**설정 파일** (`utils/config.py`):
```python
WORKLOADS = {
    "vllm": {
        "namespace": "ai-workloads",
        "deployment": "vllm-server",  # Deployment 이름
        "description": "vLLM 추론 서버"
    },
    "qdrant": {
        "namespace": "ai-workloads",
        "statefulset": "qdrant",  # StatefulSet 이름
        "description": "Qdrant 벡터 데이터베이스"
    },
    "promtail": {
        "namespace": "logging",
        "daemonset": "promtail",  # DaemonSet 이름
        "description": "로그 수집기"
    }
}
```

**상태 조회 로직**:
```python
@router.get("")
async def get_workloads():
    core_v1, apps_v1, _ = get_k8s_clients()

    for name, config in WORKLOADS.items():
        namespace = config["namespace"]

        if "deployment" in config:
            # K8s API: GET /apis/apps/v1/namespaces/{ns}/deployments/{name}
            deploy = apps_v1.read_namespaced_deployment(
                config["deployment"], namespace
            )
            status = "running" if deploy.status.ready_replicas > 0 else "stopped"

        elif "statefulset" in config:
            # K8s API: GET /apis/apps/v1/namespaces/{ns}/statefulsets/{name}
            sts = apps_v1.read_namespaced_stateful_set(
                config["statefulset"], namespace
            )

        elif "daemonset" in config:
            # K8s API: GET /apis/apps/v1/namespaces/{ns}/daemonsets/{name}
            ds = apps_v1.read_namespaced_daemon_set(
                config["daemonset"], namespace
            )
```

#### 3.2 워크로드 제어 (시작/중지/스케일)

```python
@router.post("/{workload_name}")
async def control_workload(workload_name: str, action: WorkloadAction):
    core_v1, apps_v1, _ = get_k8s_clients()

    if action.action == "stop":
        # replicas를 0으로 설정하여 중지
        # K8s API: PATCH /apis/apps/v1/namespaces/{ns}/deployments/{name}
        apps_v1.patch_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body={"spec": {"replicas": 0}}
        )

    elif action.action == "start":
        # replicas를 1 이상으로 설정하여 시작
        apps_v1.patch_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body={"spec": {"replicas": action.replicas}}
        )

    elif action.action == "scale":
        # 원하는 수로 스케일
        apps_v1.patch_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body={"spec": {"replicas": action.replicas}}
        )
```

---

### 4. GPU Router (`routers/monitoring/gpu.py`)

#### 4.1 GPU 정보 조회 방법

**방법 1: Kubernetes 노드 리소스에서 조회** (기본)
```python
def get_gpu_info_from_k8s():
    core_v1, _, _ = get_k8s_clients()
    nodes = core_v1.list_node()

    for node in nodes.items:
        capacity = node.status.capacity
        labels = node.metadata.labels

        # NVIDIA Device Plugin이 노드에 추가한 리소스
        gpu_count = int(capacity.get("nvidia.com/gpu", "0"))

        # 노드 라벨에서 GPU 정보 추출
        # (nvidia-gpu-feature-discovery가 자동 추가)
        gpu_type = labels.get("nvidia.com/gpu.product", "NVIDIA GPU")
        gpu_memory = labels.get("nvidia.com/gpu.memory", "0")
```

**방법 2: GPU Metrics Collector Pod에서 조회** (실시간)
```python
async def get_gpu_metrics_from_collectors():
    core_v1, _, _ = get_k8s_clients()

    # GPU 메트릭 수집 Pod 조회
    pods = core_v1.list_namespaced_pod(
        namespace="dashboard",
        label_selector="app=gpu-metrics"
    )

    # 각 노드의 collector Pod에 HTTP 요청
    async with httpx.AsyncClient() as client:
        for pod in pods.items:
            pod_ip = pod.status.pod_ip
            # Pod 내부의 GPU 메트릭 서비스 호출
            response = await client.get(f"http://{pod_ip}:9400/metrics")
            # nvidia-smi 기반 실시간 데이터 반환
```

#### 4.2 GPU 사용 Pod 조회

```python
def get_pods_using_gpu():
    core_v1, _, _ = get_k8s_clients()
    pods = core_v1.list_pod_for_all_namespaces()

    gpu_pods = []
    for pod in pods.items:
        if pod.status.phase != "Running":
            continue

        for container in pod.spec.containers:
            resources = container.resources or {}
            requests = resources.requests or {}
            limits = resources.limits or {}

            # nvidia.com/gpu 리소스 요청 확인
            gpu_req = requests.get("nvidia.com/gpu", "0")
            gpu_limit = limits.get("nvidia.com/gpu", "0")

            if int(gpu_req) > 0 or int(gpu_limit) > 0:
                gpu_pods.append({
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "node": pod.spec.node_name,
                    "gpu_count": max(int(gpu_req), int(gpu_limit)),
                    # GPU 인덱스는 환경변수에서 추출
                    "gpu_indices": get_gpu_indices_from_env(container.env)
                })
```

**GPU 인덱스 환경변수**:
```python
def get_gpu_indices_from_env(env_vars):
    """NVIDIA_VISIBLE_DEVICES 환경변수에서 GPU 인덱스 추출"""
    for env in (env_vars or []):
        if env.name == "NVIDIA_VISIBLE_DEVICES":
            if env.value and env.value != "all":
                return [int(x) for x in env.value.split(",")]
    return []
```

---

### 5. Storage Router (`routers/storage/`)

#### 5.1 MinIO 연동 (`minio.py`)

MinIO는 K8s 내부 서비스로 배포되어 있으며, Python `minio` 클라이언트로 직접 통신합니다.

```python
from minio import Minio

# K8s 서비스 DNS를 통한 연결
MINIO_ENDPOINT = "minio-service.storage.svc.cluster.local:9000"

def get_minio_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )

@router.get("/buckets")
async def list_buckets():
    client = get_minio_client()
    buckets = client.list_buckets()
    return {"buckets": [{"name": b.name, "created": b.creation_date} for b in buckets]}
```

#### 5.2 Longhorn 연동 (`longhorn.py`)

Longhorn은 K8s CRD(Custom Resource Definition)로 관리됩니다.

```python
@router.get("/volumes")
async def list_longhorn_volumes():
    _, _, custom_api = get_k8s_clients()

    # Longhorn CRD 조회
    # K8s API: GET /apis/longhorn.io/v1beta2/namespaces/longhorn-system/volumes
    volumes = custom_api.list_namespaced_custom_object(
        group="longhorn.io",
        version="v1beta2",
        namespace="longhorn-system",
        plural="volumes"
    )

    return volumes
```

**Longhorn CRD 구조**:
```yaml
apiVersion: longhorn.io/v1beta2
kind: Volume
metadata:
  name: pvc-xxxx
  namespace: longhorn-system
spec:
  size: "10Gi"
  numberOfReplicas: 2
status:
  state: attached
  robustness: healthy
```

---

### 6. AI 서비스 Router (`routers/ai/`)

#### 6.1 vLLM 연동 (`vllm.py`)

vLLM은 K8s Service를 통해 노출됩니다. 백엔드는 HTTP로 직접 통신합니다.

```python
# K8s 서비스 DNS
VLLM_URL = "http://vllm-service.ai-workloads.svc.cluster.local:8000"

@router.post("/chat")
async def vllm_chat(request: ChatRequest):
    # 서비스 연결 상태 확인
    await check_vllm_connection()

    async with httpx.AsyncClient() as client:
        # vLLM OpenAI 호환 API 호출
        response = await client.post(
            f"{VLLM_URL}/v1/chat/completions",
            json={
                "model": request.model,
                "messages": [{"role": m.role, "content": m.content}
                            for m in request.messages],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
        )
        return response.json()
```

**데모 모드 패턴**:
```python
_vllm_demo_mode = True

async def check_vllm_connection():
    """서비스 연결 가능 여부 확인 → 불가시 데모 모드 활성화"""
    global _vllm_demo_mode
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{VLLM_URL}/v1/models")
            _vllm_demo_mode = (resp.status_code != 200)
    except:
        _vllm_demo_mode = True

@router.get("/status")
async def get_status():
    await check_vllm_connection()
    if _vllm_demo_mode:
        return {"status": "demo", "message": "서비스 미연결"}
    return {"status": "running"}
```

---

### 7. Events Router (`routers/cluster/events.py`)

K8s 이벤트는 클러스터에서 발생하는 모든 활동을 기록합니다.

```python
@router.get("/events")
async def get_events(namespace: str = None, limit: int = 100):
    core_v1, _, _ = get_k8s_clients()

    if namespace:
        # 특정 네임스페이스 이벤트
        events = core_v1.list_namespaced_event(namespace)
    else:
        # 모든 이벤트
        events = core_v1.list_event_for_all_namespaces()

    return [{
        "type": e.type,           # Normal, Warning
        "reason": e.reason,        # Scheduled, Pulling, Started, Killing
        "message": e.message,
        "object": f"{e.involved_object.kind}/{e.involved_object.name}",
        "namespace": e.metadata.namespace,
        "time": e.last_timestamp or e.event_time
    } for e in sorted(events.items, key=lambda x: x.last_timestamp, reverse=True)[:limit]]
```

---

## K8s 리소스 단위 변환

백엔드는 K8s API의 리소스 단위를 사람이 읽기 쉬운 형태로 변환합니다.

```python
def parse_cpu(cpu_str: str) -> float:
    """CPU 문자열 → 밀리코어"""
    if cpu_str.endswith('n'):   # 나노코어: 100n = 0.0001m
        return float(cpu_str[:-1]) / 1000000
    if cpu_str.endswith('u'):   # 마이크로코어: 100u = 0.1m
        return float(cpu_str[:-1]) / 1000
    if cpu_str.endswith('m'):   # 밀리코어: 1000m = 1 core
        return float(cpu_str[:-1])
    return float(cpu_str) * 1000  # 코어: 1 = 1000m

def parse_memory(mem_str: str) -> int:
    """메모리 문자열 → MB"""
    if mem_str.endswith('Ki'):  # Kibibyte
        return int(float(mem_str[:-2]) / 1024)
    if mem_str.endswith('Mi'):  # Mebibyte
        return int(float(mem_str[:-2]))
    if mem_str.endswith('Gi'):  # Gibibyte
        return int(float(mem_str[:-2]) * 1024)
    if mem_str.endswith('Ti'):  # Tebibyte
        return int(float(mem_str[:-2]) * 1024 * 1024)
```

---

## RBAC 권한

대시보드 Pod가 K8s API에 접근하려면 적절한 권한이 필요합니다.

**ServiceAccount 및 ClusterRole** (`manifests/20-dashboard.yaml`):
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k3s-dashboard
  namespace: k3s-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k3s-dashboard
rules:
# 기본 리소스 접근
- apiGroups: [""]
  resources: ["pods", "pods/log", "services", "namespaces",
              "persistentvolumeclaims", "persistentvolumes",
              "nodes", "events"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# 앱 리소스 접근
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# 스토리지 클래스
- apiGroups: ["storage.k8s.io"]
  resources: ["storageclasses"]
  verbs: ["get", "list", "watch"]

# Longhorn CRD
- apiGroups: ["longhorn.io"]
  resources: ["*"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# Ingress
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

---

## 데이터 흐름 요약

```
사용자 브라우저
      │
      │ HTTP (React → FastAPI)
      ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Backend                                            │
│                                                             │
│  1. API 요청 수신                                          │
│  2. kubernetes-python 클라이언트로 K8s API 호출            │
│  3. 또는 httpx로 내부 서비스 호출 (vLLM, MinIO 등)         │
│  4. 응답 가공 후 JSON 반환                                 │
└─────────────────────────────────────────────────────────────┘
      │                          │
      │ K8s API                  │ HTTP (Service DNS)
      │ (HTTPS + Token)          │
      ▼                          ▼
┌───────────────┐    ┌──────────────────────────────┐
│  K3s API      │    │  K8s Services                │
│  Server       │    │  - vllm-service:8000         │
│               │    │  - minio-service:9000        │
│ - CoreV1Api   │    │  - qdrant-service:6333       │
│ - AppsV1Api   │    │  - neo4j-service:7687        │
│ - CustomObj   │    │  - ragflow:9380              │
└───────────────┘    └──────────────────────────────┘
```

---

## Pod 내부 프로세스와의 상호작용

백엔드는 K8s API 외에도 클러스터 내부에서 실행되는 서비스 Pod들과 직접 HTTP 통신합니다.

### 서비스 디스커버리

K8s는 각 Service에 대해 DNS 레코드를 자동 생성합니다:

```
<service-name>.<namespace>.svc.cluster.local
```

**예시**:
| 서비스 | DNS 주소 | 포트 |
|--------|----------|------|
| vLLM | `vllm-service.ai-workloads.svc.cluster.local` | 8000 |
| MinIO | `minio-service.storage.svc.cluster.local` | 9000 |
| Qdrant | `qdrant.ai-workloads.svc.cluster.local` | 6333 |
| Neo4j | `neo4j-service.ai-workloads.svc.cluster.local` | 7687 |
| ComfyUI | `comfyui-service.ai-workloads.svc.cluster.local` | 8188 |
| RAGflow | `ragflow.ai-workloads.svc.cluster.local` | 9380 |
| Embedding | `embedding-service.ai-workloads.svc.cluster.local` | 8080 |

---

### 1. vLLM Pod (LLM 추론)

**서비스 URL**: `http://vllm-service.ai-workloads.svc.cluster.local:8000`

**프로토콜**: OpenAI 호환 REST API

```python
VLLM_URL = "http://vllm-service.ai-workloads.svc.cluster.local:8000"

@router.post("/chat")
async def vllm_chat(request: ChatRequest):
    async with httpx.AsyncClient(timeout=60.0) as client:
        # vLLM Pod 내부 FastAPI 서버로 요청
        resp = await client.post(
            f"{VLLM_URL}/v1/chat/completions",
            json={
                "model": request.model,
                "messages": [{"role": m.role, "content": m.content}
                            for m in request.messages],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
        )
        return resp.json()
```

**Pod 내부 구조**:
```
┌─────────────────────────────────────────┐
│  vLLM Pod                               │
│  ┌───────────────────────────────────┐  │
│  │  vLLM Server Process              │  │
│  │  - GPU 메모리에 모델 로드         │  │
│  │  - PagedAttention으로 효율적 추론 │  │
│  │  - OpenAI 호환 API 제공          │  │
│  │    • /v1/models                   │  │
│  │    • /v1/chat/completions         │  │
│  │    • /v1/completions              │  │
│  └───────────────────────────────────┘  │
│  Port: 8000                             │
│  GPU: nvidia.com/gpu 리소스            │
└─────────────────────────────────────────┘
```

---

### 2. Qdrant Pod (벡터 DB)

**서비스 URL**: `http://qdrant.ai-workloads.svc.cluster.local:6333`

**프로토콜**: Qdrant REST API

```python
QDRANT_URL = "http://qdrant.ai-workloads.svc.cluster.local:6333"

# 벡터 검색
@router.post("/search")
async def vector_search(request: SearchRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{QDRANT_URL}/collections/{request.collection}/points/search",
            json={
                "vector": request.vector,
                "limit": request.top_k,
                "with_payload": True
            }
        )
        return resp.json()

# 벡터 삽입
@router.post("/upsert")
async def upsert_vectors(request: UpsertRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{QDRANT_URL}/collections/{request.collection}/points",
            json={"points": request.points}
        )
        return resp.json()
```

**Pod 내부 구조**:
```
┌─────────────────────────────────────────┐
│  Qdrant Pod                             │
│  ┌───────────────────────────────────┐  │
│  │  Qdrant Engine (Rust)             │  │
│  │  - HNSW 인덱스 관리              │  │
│  │  - 벡터 유사도 검색              │  │
│  │    • Cosine, Euclidean, Dot      │  │
│  │  - 컬렉션/포인트 CRUD            │  │
│  └───────────────────────────────────┘  │
│  REST: 6333, gRPC: 6334                 │
│  Volume: /qdrant/storage (PVC)          │
└─────────────────────────────────────────┘
```

---

### 3. Neo4j Pod (그래프 DB)

**서비스 URL**: `bolt://neo4j-service.ai-workloads.svc.cluster.local:7687`

**프로토콜**: Bolt (Neo4j 바이너리 프로토콜)

```python
from neo4j import GraphDatabase

NEO4J_URL = "bolt://neo4j-service.ai-workloads.svc.cluster.local:7687"

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URL, auth=("neo4j", "password")
        )

    def execute_query(self, query: str, params: dict = None):
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

# Cypher 쿼리 실행
@router.post("/query")
async def execute_cypher(request: CypherQuery):
    client = Neo4jClient()
    results = client.execute_query(request.query, request.parameters)
    return {"results": results}
```

**Pod 내부 구조**:
```
┌─────────────────────────────────────────┐
│  Neo4j Pod                              │
│  ┌───────────────────────────────────┐  │
│  │  Neo4j Database Server            │  │
│  │  - 그래프 스토리지 엔진          │  │
│  │  - Cypher 쿼리 파서/실행기       │  │
│  │  - 트랜잭션 관리                 │  │
│  └───────────────────────────────────┘  │
│  Bolt: 7687, HTTP: 7474                 │
│  Volume: /data (PVC)                    │
└─────────────────────────────────────────┘
```

---

### 4. MinIO Pod (오브젝트 스토리지)

**서비스 URL**: `minio-service.storage.svc.cluster.local:9000`

**프로토콜**: S3 호환 API

```python
from minio import Minio

MINIO_ENDPOINT = "minio-service.storage.svc.cluster.local:9000"

def get_minio_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )

# 파일 업로드
@router.post("/buckets/{bucket}/objects")
async def upload_object(bucket: str, file: UploadFile):
    client = get_minio_client()
    client.put_object(
        bucket_name=bucket,
        object_name=file.filename,
        data=file.file,
        length=-1,
        part_size=10*1024*1024
    )
    return {"uploaded": file.filename}

# 파일 다운로드
@router.get("/buckets/{bucket}/objects/{name}/download")
async def download_object(bucket: str, name: str):
    client = get_minio_client()
    response = client.get_object(bucket, name)
    return StreamingResponse(response, media_type="application/octet-stream")
```

**Pod 내부 구조**:
```
┌─────────────────────────────────────────┐
│  MinIO Pod                              │
│  ┌───────────────────────────────────┐  │
│  │  MinIO Server Process             │  │
│  │  - S3 호환 API 제공              │  │
│  │  - 버킷/오브젝트 관리            │  │
│  │  - IAM 사용자 관리               │  │
│  └───────────────────────────────────┘  │
│  API: 9000, Console: 9001               │
│  Volume: /data (PVC)                    │
└─────────────────────────────────────────┘
```

---

### 5. ComfyUI Pod (이미지/비디오 생성)

**서비스 URL**: `http://comfyui-service.ai-workloads.svc.cluster.local:8188`

**프로토콜**: ComfyUI REST API

```python
COMFYUI_URL = "http://comfyui-service.ai-workloads.svc.cluster.local:8188"

# 워크플로우 실행
@router.post("/generate")
async def generate_image(request: GenerateRequest):
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 워크플로우 제출
        resp = await client.post(
            f"{COMFYUI_URL}/prompt",
            json={
                "prompt": request.workflow,
                "client_id": str(uuid.uuid4())
            }
        )
        prompt_id = resp.json()["prompt_id"]

        # 완료 대기 (폴링)
        while True:
            history = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
            if prompt_id in history.json():
                return history.json()[prompt_id]
            await asyncio.sleep(1)

# 생성된 이미지 조회
@router.get("/view")
async def view_image(filename: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{COMFYUI_URL}/view",
            params={"filename": filename, "type": "output"}
        )
        return Response(content=resp.content, media_type="image/png")
```

**Pod 내부 구조**:
```
┌─────────────────────────────────────────┐
│  ComfyUI Pod                            │
│  ┌───────────────────────────────────┐  │
│  │  ComfyUI Server (Python)          │  │
│  │  - 노드 기반 워크플로우 엔진     │  │
│  │  - Stable Diffusion 모델 로드    │  │
│  │  - WebSocket 실시간 진행률       │  │
│  └───────────────────────────────────┘  │
│  HTTP: 8188                             │
│  Volume: /models, /output               │
│  GPU: nvidia.com/gpu 리소스            │
└─────────────────────────────────────────┘
```

---

### 6. RAGflow Pod (RAG 엔진)

**서비스 URL**: `http://ragflow.ai-workloads.svc.cluster.local:9380`

**프로토콜**: RAGflow REST API

```python
RAGFLOW_URL = "http://ragflow.ai-workloads.svc.cluster.local:9380"

# 지식 베이스 목록
@router.get("/knowledge-bases")
async def list_knowledge_bases():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{RAGFLOW_URL}/v1/kb/list")
        return resp.json()

# RAG 채팅
@router.post("/chat")
async def rag_chat(request: ChatRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{RAGFLOW_URL}/v1/chat/completion",
            json={
                "kb_ids": request.kb_ids,
                "question": request.question,
                "top_k": request.top_k
            }
        )
        return resp.json()  # answer + sources
```

**RAGflow 의존성**:
```
┌─────────────────────────────────────────────────────┐
│  RAGflow Deployment                                 │
│  ┌───────────┐  ┌───────────┐  ┌─────────────────┐ │
│  │  RAGflow  │──│  MySQL    │──│  Elasticsearch  │ │
│  │  :9380    │  │  :3306    │  │  :9200          │ │
│  └───────────┘  └───────────┘  └─────────────────┘ │
│       │         ┌───────────┐  ┌─────────────────┐ │
│       └─────────│  Redis    │──│  MinIO          │ │
│                 │  :6379    │  │  :9000          │ │
│                 └───────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

### 7. GPU Metrics Collector (DaemonSet)

각 GPU 노드에서 nvidia-smi 데이터를 수집합니다.

```python
async def get_gpu_metrics_from_collectors():
    core_v1, _, _ = get_k8s_clients()

    # DaemonSet Pod 조회
    pods = core_v1.list_namespaced_pod(
        namespace="dashboard",
        label_selector="app=gpu-metrics"
    )

    all_gpus = []
    async with httpx.AsyncClient() as client:
        for pod in pods.items:
            pod_ip = pod.status.pod_ip
            try:
                # 각 노드 collector에 직접 요청
                resp = await client.get(f"http://{pod_ip}:9400/metrics")
                """
                반환: {
                    "node": "gpu-node-1",
                    "gpus": [{
                        "index": 0,
                        "name": "RTX 4090",
                        "temperature": 45,
                        "memory_used": 2048,
                        "memory_total": 24576,
                        "utilization": 15
                    }]
                }
                """
                all_gpus.extend(resp.json()["gpus"])
            except:
                continue

    return all_gpus
```

**Pod 내부 구조**:
```
┌─────────────────────────────────────────┐
│  GPU Metrics Pod (각 GPU 노드마다 1개)  │
│  ┌───────────────────────────────────┐  │
│  │  Python Script                    │  │
│  │  - nvidia-smi 주기적 실행        │  │
│  │  - GPU 상태 파싱                 │  │
│  │  - HTTP 서버로 메트릭 제공       │  │
│  └───────────────────────────────────┘  │
│  HTTP: 9400                             │
│  hostPID: true (nvidia-smi 접근)        │
└─────────────────────────────────────────┘
```

---

### 데모 모드 패턴

모든 외부 서비스 라우터는 연결 실패 시 데모 모드로 전환:

```python
_demo_mode = True

async def check_connection():
    global _demo_mode
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{SERVICE_URL}/health")
            _demo_mode = (resp.status_code != 200)
    except:
        _demo_mode = True

@router.get("/data")
async def get_data():
    await check_connection()

    if _demo_mode:
        return {"data": [...], "mode": "demo"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SERVICE_URL}/data")
        return resp.json()
```

---

## 디버깅 팁

### Pod 내부에서 API 접근 테스트
```bash
# Dashboard Pod에 접속
kubectl exec -it -n k3s-dashboard deployment/k3s-dashboard -- /bin/sh

# ServiceAccount 토큰 확인
cat /var/run/secrets/kubernetes.io/serviceaccount/token

# curl로 API 테스트
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
curl -k -H "Authorization: Bearer $TOKEN" \
  https://kubernetes.default.svc/api/v1/namespaces
```

### K8s API 직접 호출
```bash
# 모든 노드 조회
kubectl get --raw /api/v1/nodes | jq

# 특정 Deployment 조회
kubectl get --raw /apis/apps/v1/namespaces/ai-workloads/deployments/vllm-server | jq

# Longhorn 볼륨 조회
kubectl get --raw /apis/longhorn.io/v1beta2/namespaces/longhorn-system/volumes | jq
```
