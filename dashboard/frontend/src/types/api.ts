// API 관련 타입 정의

export interface NodeMetrics {
  name: string;
  status: 'Ready' | 'NotReady' | 'Unknown';
  role: string;
  roles: string[];
  cpu_percent: number;
  memory_percent: number;
  cpu_used: string;
  cpu_total: string;
  memory_used: string;
  memory_total: string;
  cpu_requests?: number;
  cpu_limits?: number;
  memory_requests?: number;
  memory_limits?: number;
  gpu_capacity?: number;
  gpu_used?: number;
  gpu_type?: string;
}

export interface GpuInfo {
  index: number;
  name: string;
  node?: string;
  temperature: number;
  utilization: number;
  memory_used: number;
  memory_total: number;
  power_draw: number;
  power_limit: number;
  status: 'available' | 'in_use' | 'error';
}

export interface GpuStatus {
  available: boolean;
  total_gpus: number;
  gpu_nodes?: {
    node: string;
    gpu_type: string;
    gpu_count: number;
    status: string;
  }[];
}

export interface GpuDetailed {
  available: boolean;
  gpus: GpuInfo[];
}

export interface WorkloadStatus {
  status: 'running' | 'stopped' | 'not_deployed' | 'error' | 'pending';
  ready_replicas?: number;
  desired_replicas?: number;
  message?: string;
}

export interface Workloads {
  vllm?: WorkloadStatus;
  ollama?: WorkloadStatus;
  comfyui?: WorkloadStatus;
  qdrant?: WorkloadStatus;
  neo4j?: WorkloadStatus;
  loki?: WorkloadStatus;
  promtail?: WorkloadStatus;
  langfuse?: WorkloadStatus;
  minio?: WorkloadStatus;
  redis?: WorkloadStatus;
  [key: string]: WorkloadStatus | undefined;
}

export interface Pod {
  name: string;
  namespace: string;
  status: 'Running' | 'Pending' | 'Failed' | 'Succeeded' | 'Unknown';
  node?: string;
  ip?: string;
  cpu_usage?: number;
  memory_usage?: number;
  restarts?: number;
  age?: string;
}

export interface PodsData {
  total: number;
  by_namespace: Record<string, Pod[]>;
}

export interface StorageInfo {
  total: string;
  used: string;
  available: string;
  percent: number;
  volumes?: VolumeInfo[];
}

export interface VolumeInfo {
  name: string;
  namespace: string;
  status: string;
  capacity: string;
  storageClass: string;
  accessModes: string[];
}

export interface ClusterOverview {
  nodes: NodeMetrics[];
  pods: PodsData;
  workloads: Workloads;
  gpu_status: GpuStatus;
  storage: StorageInfo;
}

// API Action Loading 상태
export interface ActionLoading {
  loading: boolean;
  action?: 'start' | 'stop';
}

export interface ActionLoadingMap {
  [key: string]: ActionLoading | undefined;
}

// 워크로드 설정
export interface VllmConfig {
  model: string;
  gpuMemory: number;
  quantization: string;
  nodeSelector: string;
}

export interface OllamaConfig {
  model: string;
  nodeSelector: string;
  enableGpu: boolean;
}

export interface QdrantConfig {
  replicas: number;
  storageSize: number;
  nodeSelector: string;
}

export interface Neo4jConfig {
  useCase: string;
  replicas: number;
  memoryLimit: string;
  storageSize: number;
  nodeSelector: string;
}

export interface ComfyuiConfig {
  nodeSelector: string;
  enableHighVram: boolean;
}
