# Kubernetes RBAC (Role-Based Access Control) 가이드

## 1. RBAC 개요

### RBAC란?
RBAC(Role-Based Access Control)는 Kubernetes에서 **누가(Who)** **무엇을(What)** **어디서(Where)** 할 수 있는지를 제어하는 권한 관리 시스템입니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                      RBAC 핵심 개념                              │
├─────────────────────────────────────────────────────────────────┤
│  Subject (누가)     →  Role (무엇을)    →  Resource (어디서)     │
│  ─────────────────     ──────────────      ─────────────────     │
│  • User              • get               • pods                 │
│  • Group             • list              • deployments          │
│  • ServiceAccount    • create            • services             │
│                      • delete            • secrets              │
│                      • update            • nodes                │
└─────────────────────────────────────────────────────────────────┘
```

### 왜 RBAC가 필요한가?
1. **보안**: 최소 권한 원칙(Principle of Least Privilege) 적용
2. **감사**: 누가 무엇을 했는지 추적 가능
3. **격리**: 팀/애플리케이션별 권한 분리
4. **규정 준수**: 보안 정책 및 규정 준수

---

## 2. RBAC 핵심 리소스

### 2.1 Subject (주체) - 누가?

#### ServiceAccount
Pod 내에서 실행되는 애플리케이션의 신원입니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k3s-dashboard        # ServiceAccount 이름
  namespace: dashboard       # 소속 네임스페이스
```

**특징:**
- 네임스페이스에 종속됨
- Pod에 자동으로 토큰 마운트
- API 서버 인증에 사용

#### User와 Group
- **User**: 외부 인증 시스템(LDAP, OIDC 등)에서 관리
- **Group**: 여러 User를 묶은 그룹
- Kubernetes는 User/Group을 직접 관리하지 않음 (외부 시스템 연동)

### 2.2 Role vs ClusterRole - 무엇을?

#### Role (네임스페이스 범위)
특정 네임스페이스 내에서만 유효한 권한

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: default        # 이 네임스페이스에서만 유효
rules:
- apiGroups: [""]           # core API group
  resources: ["pods"]       # 대상 리소스
  verbs: ["get", "list"]    # 허용되는 작업
```

#### ClusterRole (클러스터 범위)
클러스터 전체에서 유효한 권한

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k3s-dashboard       # 클러스터 전체에서 유효
rules:
- apiGroups: [""]
  resources: ["pods", "nodes", "services", "events"]
  verbs: ["get", "list", "watch", "create", "update", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets"]
  verbs: ["get", "list", "watch", "create", "update", "delete"]
```

**ClusterRole이 필요한 경우:**
- `nodes` 조회 (노드는 클러스터 리소스)
- 모든 네임스페이스의 Pod 조회
- `PersistentVolume` 관리 (클러스터 리소스)
- 클러스터 전체 이벤트 수집

### 2.3 RoleBinding vs ClusterRoleBinding - 연결

#### RoleBinding
Role/ClusterRole을 Subject에 **특정 네임스페이스 내에서** 연결

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default        # 이 네임스페이스에서만 권한 적용
subjects:
- kind: ServiceAccount
  name: my-app
  namespace: default
roleRef:
  kind: Role               # 또는 ClusterRole
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

#### ClusterRoleBinding
ClusterRole을 Subject에 **클러스터 전체에서** 연결

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: k3s-dashboard       # 클러스터 전체에서 권한 적용
subjects:
- kind: ServiceAccount
  name: k3s-dashboard
  namespace: dashboard      # ⚠️ 중요: ServiceAccount가 있는 네임스페이스
roleRef:
  kind: ClusterRole
  name: k3s-dashboard
  apiGroup: rbac.authorization.k8s.io
```

---

## 3. RBAC 관계도

```
┌──────────────────────────────────────────────────────────────────────┐
│                         RBAC 관계 구조                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────────┐                                                │
│   │  ServiceAccount │ ◄─────────────────────────────────┐            │
│   │  (dashboard ns) │                                   │            │
│   └────────┬────────┘                                   │            │
│            │                                            │            │
│            │ 참조                                       │            │
│            ▼                                            │            │
│   ┌─────────────────────┐      연결       ┌─────────────────────┐    │
│   │ ClusterRoleBinding  │ ◄──────────────► │    ClusterRole      │    │
│   │   (k3s-dashboard)   │                 │   (k3s-dashboard)   │    │
│   │                     │                 │                     │    │
│   │ subjects:           │    roleRef:     │ rules:              │    │
│   │  - ServiceAccount   │ ───────────────►│  - pods: get,list   │    │
│   │    name: k3s-dash   │                 │  - nodes: get,list  │    │
│   │    namespace: dash  │                 │  - deployments: *   │    │
│   └─────────────────────┘                 └─────────────────────┘    │
│                                                     │                │
│                                                     │ 권한 부여      │
│                                                     ▼                │
│                                           ┌─────────────────────┐    │
│                                           │  Kubernetes API     │    │
│                                           │  - GET /api/v1/pods │    │
│                                           │  - GET /api/v1/nodes│    │
│                                           └─────────────────────┘    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. 우리 대시보드의 RBAC 문제와 해결

### 4.1 문제 상황

**증상:** 대시보드에서 노드, Pod, 스토리지 정보를 가져오지 못함

**에러 메시지:**
```
nodes is forbidden: User "system:serviceaccount:dashboard:k3s-dashboard"
cannot list resource "nodes" in API group "" at the cluster scope
```

### 4.2 원인 분석

```
┌─────────────────────────────────────────────────────────────────┐
│                      문제 원인 분석                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  실제 Pod 위치:                                                 │
│  ┌─────────────────────┐                                        │
│  │ Namespace: dashboard │  ◄── Pod가 여기서 실행 중             │
│  │ ServiceAccount:      │                                       │
│  │   k3s-dashboard      │                                       │
│  └─────────────────────┘                                        │
│                                                                 │
│  ClusterRoleBinding 설정 (잘못됨):                              │
│  ┌─────────────────────┐                                        │
│  │ subjects:            │                                       │
│  │  - ServiceAccount    │                                       │
│  │    name: k3s-dash    │                                       │
│  │    namespace:        │                                       │
│  │      k3s-dashboard   │  ◄── ❌ 존재하지 않는 네임스페이스!   │
│  └─────────────────────┘                                        │
│                                                                 │
│  결과: ServiceAccount가 일치하지 않아 권한 없음 (403 Forbidden) │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 해결 방법

**ClusterRoleBinding의 namespace를 실제 Pod가 있는 곳으로 수정:**

```bash
# 수정 전 확인
kubectl get clusterrolebinding k3s-dashboard -o yaml

# namespace 수정
kubectl patch clusterrolebinding k3s-dashboard \
  --type='json' \
  -p='[{"op": "replace", "path": "/subjects/0/namespace", "value": "dashboard"}]'
```

**수정 후 ClusterRoleBinding:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: k3s-dashboard
subjects:
- kind: ServiceAccount
  name: k3s-dashboard
  namespace: dashboard      # ✅ 실제 Pod가 있는 네임스페이스로 수정
roleRef:
  kind: ClusterRole
  name: k3s-dashboard
  apiGroup: rbac.authorization.k8s.io
```

---

## 5. API Groups와 Resources

### 5.1 Core API Group (빈 문자열 "")

```yaml
apiGroups: [""]   # Core API
resources:
  - pods
  - pods/log      # 하위 리소스
  - services
  - secrets
  - configmaps
  - namespaces
  - nodes         # 클러스터 리소스
  - persistentvolumes
  - persistentvolumeclaims
  - events
```

### 5.2 Named API Groups

```yaml
# apps 그룹
apiGroups: ["apps"]
resources:
  - deployments
  - statefulsets
  - daemonsets
  - replicasets

# networking.k8s.io 그룹
apiGroups: ["networking.k8s.io"]
resources:
  - ingresses
  - networkpolicies

# storage.k8s.io 그룹
apiGroups: ["storage.k8s.io"]
resources:
  - storageclasses

# 커스텀 리소스 (예: Longhorn)
apiGroups: ["longhorn.io"]
resources:
  - volumes
  - replicas
  - engines
```

### 5.3 Verbs (허용 작업)

| Verb | 설명 | HTTP Method |
|------|------|-------------|
| `get` | 단일 리소스 조회 | GET |
| `list` | 리소스 목록 조회 | GET |
| `watch` | 리소스 변경 감시 | GET (streaming) |
| `create` | 리소스 생성 | POST |
| `update` | 리소스 전체 수정 | PUT |
| `patch` | 리소스 부분 수정 | PATCH |
| `delete` | 리소스 삭제 | DELETE |
| `deletecollection` | 리소스 일괄 삭제 | DELETE |

---

## 6. 권한 범위 비교

### 6.1 Role + RoleBinding (가장 제한적)

```
┌─────────────────────────────────────────┐
│ Namespace: default                      │
│ ┌─────────────────────────────────────┐ │
│ │ Role: pod-reader                    │ │
│ │ - pods: get, list                   │ │
│ └─────────────────────────────────────┘ │
│                 ↓                       │
│ RoleBinding → ServiceAccount            │
│                                         │
│ 결과: default 네임스페이스의 pods만     │
│       get, list 가능                    │
└─────────────────────────────────────────┘
```

### 6.2 ClusterRole + RoleBinding (중간)

```
┌─────────────────────────────────────────┐
│ ClusterRole: pod-reader                 │
│ - pods: get, list (클러스터 전체 정의)  │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ Namespace: default                      │
│ RoleBinding → ServiceAccount            │
│                                         │
│ 결과: default 네임스페이스의 pods만     │
│       get, list 가능                    │
│       (ClusterRole 재사용 가능)         │
└─────────────────────────────────────────┘
```

### 6.3 ClusterRole + ClusterRoleBinding (가장 넓음)

```
┌─────────────────────────────────────────┐
│ ClusterRole: cluster-admin              │
│ - *: * (모든 리소스, 모든 작업)         │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ ClusterRoleBinding → ServiceAccount     │
│                                         │
│ 결과: 클러스터 전체에서                 │
│       모든 리소스에 모든 작업 가능      │
└─────────────────────────────────────────┘
```

---

## 7. 보안 모범 사례

### 7.1 최소 권한 원칙

```yaml
# ❌ 나쁜 예: 모든 권한
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]

# ✅ 좋은 예: 필요한 권한만
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]    # 읽기만 필요하면 읽기만
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]            # 로그 조회만
```

### 7.2 네임스페이스 격리

```yaml
# 개발팀용 Role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: dev-team       # 개발 네임스페이스에만 적용
rules:
- apiGroups: ["", "apps"]
  resources: ["pods", "deployments", "services"]
  verbs: ["get", "list", "create", "update", "delete"]
```

### 7.3 읽기 전용 권한 분리

```yaml
# 모니터링용 ClusterRole (읽기 전용)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-reader
rules:
- apiGroups: [""]
  resources: ["pods", "nodes", "services", "events"]
  verbs: ["get", "list", "watch"]   # 쓰기 권한 없음
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets"]
  verbs: ["get", "list", "watch"]   # 쓰기 권한 없음
```

---

## 8. 우리 대시보드의 최종 RBAC 설정

### 8.1 ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k3s-dashboard
  namespace: dashboard
```

### 8.2 ClusterRole

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k3s-dashboard
rules:
# Core API 리소스
- apiGroups: [""]
  resources:
    - pods
    - pods/log
    - services
    - namespaces
    - persistentvolumeclaims
    - persistentvolumes
    - nodes
    - events
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# Apps API 리소스
- apiGroups: ["apps"]
  resources:
    - deployments
    - statefulsets
    - daemonsets
    - replicasets
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# Storage API 리소스
- apiGroups: ["storage.k8s.io"]
  resources:
    - storageclasses
  verbs: ["get", "list", "watch"]

# Longhorn 커스텀 리소스
- apiGroups: ["longhorn.io"]
  resources: ["*"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

# Ingress
- apiGroups: ["networking.k8s.io"]
  resources:
    - ingresses
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

### 8.3 ClusterRoleBinding

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: k3s-dashboard
subjects:
- kind: ServiceAccount
  name: k3s-dashboard
  namespace: dashboard        # ⚠️ 반드시 실제 SA가 있는 네임스페이스
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: k3s-dashboard
```

---

## 9. RBAC 디버깅 명령어

### 9.1 권한 확인

```bash
# 특정 ServiceAccount의 권한 확인
kubectl auth can-i list pods \
  --as=system:serviceaccount:dashboard:k3s-dashboard

# 모든 권한 확인
kubectl auth can-i --list \
  --as=system:serviceaccount:dashboard:k3s-dashboard

# 특정 네임스페이스에서 권한 확인
kubectl auth can-i get pods -n storage \
  --as=system:serviceaccount:dashboard:k3s-dashboard
```

### 9.2 RBAC 리소스 조회

```bash
# ClusterRole 조회
kubectl get clusterrole k3s-dashboard -o yaml

# ClusterRoleBinding 조회
kubectl get clusterrolebinding k3s-dashboard -o yaml

# 모든 RoleBinding 조회
kubectl get rolebindings -A

# 특정 ServiceAccount가 사용하는 Role 찾기
kubectl get rolebindings,clusterrolebindings -A \
  -o jsonpath='{range .items[?(@.subjects[0].name=="k3s-dashboard")]}{.metadata.name}{"\n"}{end}'
```

### 9.3 API 요청 디버깅

```bash
# API 서버 감사 로그 확인
kubectl logs -n kube-system -l component=kube-apiserver | grep "403"

# Pod 로그에서 권한 에러 확인
kubectl logs -n dashboard -l app=k3s-dashboard | grep -i forbidden
```

---

## 10. 요약

| 개념 | 범위 | 용도 |
|------|------|------|
| **Role** | 네임스페이스 | 특정 NS 내 권한 정의 |
| **ClusterRole** | 클러스터 | 클러스터 전체 권한 정의 |
| **RoleBinding** | 네임스페이스 | Role/ClusterRole을 NS 내에서 연결 |
| **ClusterRoleBinding** | 클러스터 | ClusterRole을 클러스터 전체에서 연결 |
| **ServiceAccount** | 네임스페이스 | Pod의 신원 |

**핵심 포인트:**
1. ClusterRoleBinding의 `subjects.namespace`는 **ServiceAccount가 있는 네임스페이스**를 지정해야 함
2. 클러스터 리소스(nodes, PV 등) 접근 시 **ClusterRole + ClusterRoleBinding** 필요
3. 보안을 위해 **최소 권한 원칙** 적용 권장

---

## 11. 다중 클러스터 환경에서의 RBAC

### 11.1 다중 클러스터 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        다중 클러스터 아키텍처                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    │
│   │  Cluster A      │    │  Cluster B      │    │  Cluster C      │    │
│   │  (Production)   │    │  (Development)  │    │  (Staging)      │    │
│   │                 │    │                 │    │                 │    │
│   │  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │    │
│   │  │ RBAC 설정 │  │    │  │ RBAC 설정 │  │    │  │ RBAC 설정 │  │    │
│   │  │ 독립적    │  │    │  │ 독립적    │  │    │  │ 독립적    │  │    │
│   │  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │    │
│   └────────┬────────┘    └────────┬────────┘    └────────┬────────┘    │
│            │                      │                      │              │
│            └──────────────────────┼──────────────────────┘              │
│                                   │                                     │
│                                   ▼                                     │
│                    ┌─────────────────────────────┐                      │
│                    │  중앙 관리 대시보드           │                      │
│                    │  (Multi-Cluster Dashboard)  │                      │
│                    │                             │                      │
│                    │  각 클러스터별 kubeconfig    │                      │
│                    │  또는 ServiceAccount 토큰   │                      │
│                    └─────────────────────────────┘                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 우리 대시보드에서 발생한 문제

대시보드에서 다중 클러스터 정보를 표시하려 했을 때 RBAC 403 Forbidden 에러가 발생했습니다.

**문제 상황:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    발생한 에러 메시지                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  nodes is forbidden: User                                       │
│  "system:serviceaccount:dashboard:k3s-dashboard"                │
│  cannot list resource "nodes" in API group ""                   │
│  at the cluster scope                                           │
│                                                                 │
│  ───────────────────────────────────────────────────────────    │
│                                                                 │
│  persistentvolumes is forbidden: User                           │
│  "system:serviceaccount:dashboard:k3s-dashboard"                │
│  cannot list resource "persistentvolumes"                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**원인 분석:**
```yaml
# 매니페스트(20-dashboard.yaml)에서 정의한 네임스페이스
apiVersion: v1
kind: Namespace
metadata:
  name: k3s-dashboard    # ← 원래 의도한 네임스페이스

# 하지만 실제 배포된 위치
# Namespace: dashboard   # ← 실제로 Pod가 배포된 네임스페이스

# ClusterRoleBinding 설정
subjects:
- kind: ServiceAccount
  name: k3s-dashboard
  namespace: k3s-dashboard   # ← 존재하지 않는 네임스페이스 참조!
```

### 11.3 왜 이런 문제가 발생했는가?

```
┌─────────────────────────────────────────────────────────────────────┐
│                      네임스페이스 불일치 문제                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   1단계: ServiceAccount 생성                                        │
│   ┌─────────────────────────────────────────────┐                   │
│   │  apiVersion: v1                             │                   │
│   │  kind: ServiceAccount                       │                   │
│   │  metadata:                                  │                   │
│   │    name: k3s-dashboard                      │                   │
│   │    namespace: k3s-dashboard  ◄─── 여기 생성 │                   │
│   └─────────────────────────────────────────────┘                   │
│                                                                     │
│   2단계: 실제 Pod 배포 (다른 네임스페이스)                           │
│   ┌─────────────────────────────────────────────┐                   │
│   │  Pod 실행 위치: dashboard 네임스페이스       │                   │
│   │  Pod가 사용하는 SA:                         │                   │
│   │    system:serviceaccount:dashboard:k3s-dashboard               │
│   │                            ↑                                   │
│   │                     실제 네임스페이스                           │
│   └─────────────────────────────────────────────┘                   │
│                                                                     │
│   3단계: ClusterRoleBinding 확인                                    │
│   ┌─────────────────────────────────────────────┐                   │
│   │  subjects:                                  │                   │
│   │  - kind: ServiceAccount                     │                   │
│   │    name: k3s-dashboard                      │                   │
│   │    namespace: k3s-dashboard  ◄─── 불일치!   │                   │
│   │                                             │                   │
│   │  API 서버 판단:                             │                   │
│   │  "dashboard:k3s-dashboard" ≠               │                   │
│   │  "k3s-dashboard:k3s-dashboard"             │                   │
│   │  → 권한 없음 (403 Forbidden)                │                   │
│   └─────────────────────────────────────────────┘                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.4 해결 방법

**방법 1: ClusterRoleBinding 수정 (우리가 사용한 방법)**

```bash
# namespace를 실제 Pod가 있는 곳으로 수정
kubectl patch clusterrolebinding k3s-dashboard \
  --type='json' \
  -p='[{"op": "replace", "path": "/subjects/0/namespace", "value": "dashboard"}]'
```

**방법 2: 매니페스트 통일**

```yaml
# 모든 리소스를 같은 네임스페이스에 배포
apiVersion: v1
kind: Namespace
metadata:
  name: dashboard         # 일관된 네임스페이스 사용
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k3s-dashboard
  namespace: dashboard    # 같은 네임스페이스
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: k3s-dashboard
subjects:
- kind: ServiceAccount
  name: k3s-dashboard
  namespace: dashboard    # 같은 네임스페이스
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: k3s-dashboard
```

### 11.5 다중 클러스터 접근 패턴

다중 클러스터 대시보드에서 각 클러스터에 접근하는 방법:

**패턴 1: kubeconfig 기반**

```
┌─────────────────────────────────────────────────────────────────┐
│  대시보드 서버                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ~/.kube/config                                         │   │
│  │  ─────────────────                                      │   │
│  │  contexts:                                              │   │
│  │  - name: cluster-a                                      │   │
│  │    cluster: production                                  │   │
│  │  - name: cluster-b                                      │   │
│  │    cluster: development                                 │   │
│  │  - name: cluster-c                                      │   │
│  │    cluster: staging                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  kubectl --context=cluster-a get nodes                         │
│  kubectl --context=cluster-b get nodes                         │
│  kubectl --context=cluster-c get nodes                         │
└─────────────────────────────────────────────────────────────────┘
```

**패턴 2: ServiceAccount 토큰 기반**

```
┌─────────────────────────────────────────────────────────────────┐
│  각 클러스터에서 토큰 생성                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Cluster A:                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. ServiceAccount 생성                                 │   │
│  │  2. ClusterRole + ClusterRoleBinding 설정               │   │
│  │  3. 토큰 추출:                                          │   │
│  │     kubectl create token k3s-dashboard -n dashboard     │   │
│  │                                                         │   │
│  │  4. 대시보드에서 이 토큰으로 API 호출:                   │   │
│  │     Authorization: Bearer <token>                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.6 다중 클러스터 RBAC 체크리스트

각 클러스터에서 확인해야 할 사항:

```bash
# 1. ServiceAccount 존재 확인
kubectl get sa k3s-dashboard -n dashboard

# 2. ClusterRole 확인
kubectl get clusterrole k3s-dashboard -o yaml

# 3. ClusterRoleBinding의 namespace 확인 (가장 중요!)
kubectl get clusterrolebinding k3s-dashboard -o jsonpath='{.subjects[0].namespace}'
# 출력이 실제 Pod가 있는 네임스페이스와 일치해야 함

# 4. 권한 테스트
kubectl auth can-i list nodes \
  --as=system:serviceaccount:dashboard:k3s-dashboard

kubectl auth can-i list pods -A \
  --as=system:serviceaccount:dashboard:k3s-dashboard

# 5. 실제 API 호출 테스트
TOKEN=$(kubectl create token k3s-dashboard -n dashboard)
curl -k -H "Authorization: Bearer $TOKEN" \
  https://localhost:6443/api/v1/nodes
```

### 11.7 흔한 실수와 해결책

| 실수 | 증상 | 해결책 |
|------|------|--------|
| namespace 불일치 | 403 Forbidden | ClusterRoleBinding의 subjects.namespace 확인 |
| ClusterRole 누락 | 403 Forbidden | 필요한 리소스에 대한 rules 추가 |
| RoleBinding 사용 (ClusterRoleBinding 대신) | nodes 조회 불가 | 클러스터 리소스는 ClusterRoleBinding 필요 |
| apiGroups 누락 | 특정 리소스 접근 불가 | apps, storage.k8s.io 등 apiGroup 확인 |
| verbs 부족 | 읽기는 되나 수정 불가 | create, update, patch, delete 추가 |
