import axios from 'axios';
import type {
  NodeMetrics,
  GpuStatus,
  GpuDetailed,
  Workloads,
  PodsData,
  StorageInfo,
  ClusterOverview,
} from '@/types';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// 클러스터 관련 API
export const clusterApi = {
  getNodes: () => api.get<NodeMetrics[]>('/nodes'),
  getNodeMetrics: () => api.get<NodeMetrics[]>('/node-metrics'),
  getPods: () => api.get<PodsData>('/pods'),
  getOverview: () => api.get<ClusterOverview>('/cluster/overview'),
};

// GPU 관련 API
export const gpuApi = {
  getStatus: () => api.get<GpuStatus>('/gpu/status'),
  getDetailed: () => api.get<GpuDetailed>('/gpu/detailed'),
};

// 워크로드 관련 API
export const workloadApi = {
  getStatus: () => api.get<Workloads>('/workloads/status'),
  start: (name: string, config?: Record<string, any>) =>
    api.post(`/workloads/${name}`, { action: 'start', config }),
  stop: (name: string) =>
    api.post(`/workloads/${name}`, { action: 'stop' }),
};

// 스토리지 관련 API
export const storageApi = {
  getInfo: () => api.get<StorageInfo>('/storage'),
  getVolumes: () => api.get('/storage/volumes'),
  getBuckets: () => api.get('/storage/buckets'),
  createBucket: (name: string) => api.post('/storage/buckets', { name }),
  deleteBucket: (name: string) => api.delete(`/storage/buckets/${name}`),
  listObjects: (bucket: string, prefix?: string) =>
    api.get(`/storage/buckets/${bucket}/objects`, { params: { prefix } }),
  uploadObject: (bucket: string, formData: FormData) =>
    api.post(`/storage/buckets/${bucket}/upload`, formData),
  deleteObject: (bucket: string, key: string) =>
    api.delete(`/storage/buckets/${bucket}/objects/${encodeURIComponent(key)}`),
};

// LangGraph 관련 API
export const langGraphApi = {
  generateCode: (workflowId: string) =>
    api.post(`/langgraph/generate-code`, { workflow_id: workflowId }),
  build: (workflowId: string, code: string) =>
    api.post(`/langgraph/build`, { workflow_id: workflowId, code }),
  getBuildStatus: (buildId: string) =>
    api.get(`/langgraph/build/${buildId}/status`),
  getBuilds: () => api.get('/langgraph/builds'),
  deploy: (buildId: string) => api.post(`/langgraph/deploy/${buildId}`),
};

// Qdrant 관련 API
export const qdrantApi = {
  getCollections: () => api.get('/qdrant/collections'),
  createCollection: (name: string, config: Record<string, any>) =>
    api.post('/qdrant/collections', { name, ...config }),
  deleteCollection: (name: string) => api.delete(`/qdrant/collections/${name}`),
  getPoints: (collection: string, limit?: number) =>
    api.get(`/qdrant/collections/${collection}/points`, { params: { limit } }),
};

// Neo4j 관련 API
export const neo4jApi = {
  query: (cypher: string) => api.post('/neo4j/query', { cypher }),
  getStats: () => api.get('/neo4j/stats'),
};

export default api;
