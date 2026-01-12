// API Endpoints
export const API_BASE_URL = '/api';

export const API_ENDPOINTS = {
  // Cluster
  CLUSTER_SUMMARY: `${API_BASE_URL}/cluster/summary`,
  NODES: `${API_BASE_URL}/nodes`,
  NODE_METRICS: `${API_BASE_URL}/node-metrics`,
  PODS: `${API_BASE_URL}/pods`,
  EVENTS: `${API_BASE_URL}/events`,

  // Storage
  STORAGE_INFO: `${API_BASE_URL}/storage/info`,
  STORAGE_CAPACITY: `${API_BASE_URL}/storage/capacity`,
  BUCKET_USAGE: `${API_BASE_URL}/storage/bucket-usage`,

  // GPU
  GPU_STATUS: `${API_BASE_URL}/gpu/status`,
  GPU_DETAILED: `${API_BASE_URL}/gpu/detailed`,

  // Workloads
  WORKLOADS: `${API_BASE_URL}/workloads`,
  WORKLOAD_ACTION: (name: string) => `${API_BASE_URL}/workloads/${name}`,

  // LangGraph
  LANGGRAPH_GENERATE: `${API_BASE_URL}/langgraph/generate-code`,
  LANGGRAPH_BUILD: `${API_BASE_URL}/langgraph/build`,
  LANGGRAPH_BUILD_STATUS: (id: string) => `${API_BASE_URL}/langgraph/build/${id}/status`,
  LANGGRAPH_DEPLOY: (id: string) => `${API_BASE_URL}/langgraph/deploy/${id}`,

  // Ontology
  ONTOLOGY_SCHEMA: `${API_BASE_URL}/ontology/schema`,
  ONTOLOGY_GRAPH: `${API_BASE_URL}/ontology/graph-data`,
  ONTOLOGY_QUERY: `${API_BASE_URL}/ontology/query`,

  // Pipeline
  PIPELINE_STATUS: `${API_BASE_URL}/pipeline/status`,
} as const;

// Refresh intervals (in milliseconds)
export const REFRESH_INTERVALS = {
  CLUSTER: 5000,
  METRICS: 3000,
  PODS: 10000,
  STORAGE: 30000,
  GPU: 5000,
} as const;
