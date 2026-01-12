// @ai-workflow/shared 대체 타입 정의

// Knowledge Graph Types
export interface KnowledgeGraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
}

export interface KnowledgeGraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label?: string;
  weight?: number;
}

export interface KnowledgeGraphMetadata {
  createdAt: string;
  updatedAt: string;
  version: number;
  nodeCount: number;
  edgeCount: number;
}

export interface KnowledgeGraph {
  id: string;
  name: string;
  description: string;
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  metadata: KnowledgeGraphMetadata;
}

export type GraphLayoutType = 'force' | 'hierarchical' | 'circular' | 'grid';

// Workflow Types
export interface NodePort {
  id: string;
  name: string;
  type: 'input' | 'output';
  dataType: string;
  required?: boolean;
  multiple?: boolean;
}

export interface NodeParameter {
  name: string;
  displayName: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'code';
  default: any;
  options?: { label: string; value: string }[];
}

export interface NodeDefinition {
  type: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  version: number;
  inputs: NodePort[];
  outputs: NodePort[];
  parameters: NodeParameter[];
}

export interface WorkflowNode {
  id: string;
  type: string;
  name: string;
  position: { x: number; y: number };
  parameters: Record<string, any>;
}

export interface WorkflowConnection {
  id: string;
  sourceNodeId: string;
  sourcePortId: string;
  targetNodeId: string;
  targetPortId: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
  createdAt: string;
  updatedAt: string;
}

// Re-export API types
export * from './api';

// ============================================
// Dashboard Types
// ============================================

// Cluster Types
export interface ClusterSummary {
  status: string;
  nodes: { ready: number; total: number };
  pods: { running: number; total: number; pending: number; failed: number };
  resources: {
    cpu: { usage: number; capacity: number; percent: number };
    memory: { usage: number; capacity: number; percent: number };
  };
}

export interface NodeMetrics {
  name: string;
  status: string;
  role: string;
  roles?: string[];
  cpu_percent: number;
  cpu_usage?: number;
  cpu_used: number;
  cpu_capacity: number;
  cpu_requests_percent?: number;
  cpu_limits?: number;
  memory_percent: number;
  memory_usage?: number;
  memory_used: number;
  memory_capacity: number;
  memory_requests_percent?: number;
  memory_limits?: number;
  gpu_capacity?: number;
  gpu_used?: number;
  gpu_status_array?: boolean[];
  gpu_type?: string;
  storage_capacity?: number;
  storage_used?: number;
  storage_percent?: number;
}

// Pod Types
export interface Pod {
  name: string;
  status: string;
  node: string;
  ip: string;
  cpu_usage: number;
  memory_usage: number;
}

export interface Pods {
  total: number;
  by_namespace: Record<string, Pod[]>;
}

// Workload Types
export interface Workloads {
  [key: string]: {
    status: string;
  };
}

// GPU Types
export interface GpuInfo {
  index: number;
  name: string;
  node?: string;
  utilization: number;
  memory_used: number;
  memory_total: number;
  temperature: number;
  power_draw: number;
  power_limit: number;
  status: string;
}

export interface GpuDetailed {
  available: boolean;
  gpus: GpuInfo[];
}

export interface GpuStatus {
  total_gpus: number;
  gpu_nodes: Array<{
    node: string;
    gpu_type: string;
    gpu_count: number;
    status: string;
  }>;
}

// Tab Types
export interface Tab {
  id: string;
  label: string;
}

// ============================================
// Storage Types
// ============================================

export interface StorageStatus {
  status: 'connected' | 'disconnected';
  message?: string;
  error?: string;
}

export interface Bucket {
  name: string;
  object_count: number;
  total_size_human: string;
  creation_date?: string;
}

export interface StorageObject {
  name: string;
  display_name: string;
  is_folder: boolean;
  size: number;
  size_human: string;
  last_modified: string | null;
  content_type?: string;
  etag?: string;
  isParentDir?: boolean;
}

export interface PreviewFile {
  name: string;
  fullName: string;
  content: string;
  contentType: string;
  fileType: string;
  size: string;
}

export interface PresignedExpiry {
  days: number;
  hours: number;
  minutes: number;
}

export interface DeleteConfirm {
  type: 'bucket' | 'object';
  name: string;
  hasObjects?: boolean;
  isFolder?: boolean;
}

// ============================================
// Pipeline Types
// ============================================

export interface PipelineComponent {
  name: string;
  icon: string;
  role: string;
  status: string;
  connections?: string[];
}

export interface PipelineStatus {
  pipeline_health: 'healthy' | 'partial' | 'error';
  components: Record<string, PipelineComponent>;
  connections?: Array<{ from: string; to: string }>;
  recent_errors?: Array<{ source: string; reason: string; message: string }>;
}

export interface ClusterEvent {
  type: string;
  reason: string;
  message: string;
  namespace: string;
  last_timestamp: string;
  object?: { kind: string; name: string };
}

export interface ClusterEvents {
  warning_count: number;
  normal_count: number;
  events: ClusterEvent[];
}

// ============================================
// Benchmark Types
// ============================================

export interface BenchmarkResult {
  id: string;
  model: string;
  prompt_tokens: number;
  output_tokens: number;
  duration_ms: number;
  tokens_per_second: number;
  timestamp: string;
}

export interface BenchmarkHistory {
  results: BenchmarkResult[];
  avg_tokens_per_second: number;
  total_runs: number;
}

export interface StorageBenchmarkResult {
  operation: string;
  size: string;
  duration_ms: number;
  throughput_mbps: number;
}

// ============================================
// Qdrant/Vector DB Types
// ============================================

export interface QdrantCollection {
  name: string;
  vectors_count: number;
  points_count: number;
  status: string;
  vector_size: number;
  distance: string;
}

export interface QdrantInfo {
  version: string;
  collections_count: number;
  total_vectors: number;
}

export interface EmbeddingResult {
  text: string;
  vector: number[];
  metadata?: Record<string, unknown>;
}

export interface SearchResult {
  id: string;
  score: number;
  payload: Record<string, unknown>;
}

// ============================================
// Neo4j/Ontology Types
// ============================================

export interface Neo4jSchema {
  node_labels: string[];
  relationship_types: string[];
  node_count: number;
  relationship_count: number;
}

export interface Neo4jQueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  summary?: {
    nodes_created?: number;
    relationships_created?: number;
    properties_set?: number;
  };
}

// ============================================
// ComfyUI Types
// ============================================

export interface ComfyUIStatus {
  status: 'running' | 'stopped' | 'error';
  queue_remaining: number;
  current_workflow?: string;
}

export interface ComfyUIWorkflow {
  id: string;
  name: string;
  description?: string;
  thumbnail?: string;
}

export interface ComfyUIGeneration {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress?: number;
  output_images?: string[];
  error?: string;
}

// ============================================
// LLM Types
// ============================================

export interface LLMModel {
  id: string;
  name: string;
  size: string;
  context_length: number;
  quantization?: string;
}

export interface LLMStatus {
  status: 'running' | 'stopped' | 'loading';
  model_loaded?: string;
  gpu_memory_used?: number;
  gpu_memory_total?: number;
}

export interface LLMChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface LLMChatRequest {
  messages: LLMChatMessage[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

// ============================================
// Agent/Workflow Types
// ============================================

export interface AgentDefinition {
  id: string;
  name: string;
  description: string;
  type: 'llm' | 'tool' | 'retrieval' | 'composite';
  config: Record<string, unknown>;
}

export interface AgentExecution {
  id: string;
  agent_id: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  started_at: string;
  completed_at?: string;
}

// ============================================
// Toast Types
// ============================================

export interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}
