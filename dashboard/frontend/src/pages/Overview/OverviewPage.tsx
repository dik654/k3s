import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Server, Box, Cpu, MemoryStick, RefreshCw, Zap, HardDrive, Play, Square,
  Plus, Minus, ChevronUp, ChevronDown, Database, Package
} from 'lucide-react';
import type { NodeMetrics, Workloads, ActionLoadingMap } from '@/types';

interface ClusterSummary {
  status: 'healthy' | 'warning' | 'error';
  nodes: { ready: number; total: number };
  pods: { running: number; total: number; pending: number; failed: number };
  resources: {
    cpu: { usage: number; capacity: number; percent: number };
    memory: { usage: number; capacity: number; percent: number };
  };
}

interface StorageCapacity {
  current_pvc_size: number;
  current_pvc_size_human: string;
  max_allocatable: number;
  max_allocatable_human: string;
  current_storage_class: string;
  supports_expansion: boolean;
  nodes?: { node: string; allocatable_human: string }[];
}

interface StorageInfo {
  status: string;
  total_capacity_human: string;
  used_capacity_human: string;
  available_capacity_human: string;
  usage_percent: number;
}

interface StorageCategory {
  name: string;
  description: string;
  allocated: number;
  allocated_human: string;
  used: number;
  used_human: string;
  type: string;
  color: string;
}

interface StorageBreakdown {
  categories: StorageCategory[];
  total_capacity: number;
  total_used: number;
  total_available: number;
  total_capacity_human: string;
  total_used_human: string;
  total_available_human: string;
  usage_percent: number;
}

interface NodeStorageInfo {
  node_name: string;
  role: string;
  root_disk_type?: string;
  categories: StorageCategory[];
  total_capacity: number;
  total_used: number;
  total_available: number;
  total_capacity_human: string;
  total_used_human: string;
  total_available_human: string;
  usage_percent: number;
}

interface StorageByNode {
  nodes: NodeStorageInfo[];
}

// Model requirements map
const MODEL_REQUIREMENTS: Record<string, { minGpu: number; recommendedGpu: number; vram: string }> = {
  'Qwen/Qwen2.5-7B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '16GB' },
  'Qwen/Qwen2.5-14B-Instruct': { minGpu: 1, recommendedGpu: 2, vram: '32GB' },
  'Qwen/Qwen2.5-32B-Instruct': { minGpu: 2, recommendedGpu: 4, vram: '80GB' },
  'Qwen/Qwen2.5-72B-Instruct': { minGpu: 4, recommendedGpu: 8, vram: '160GB' },
  'yanolja/EEVE-Korean-Instruct-10.8B-v1.0': { minGpu: 1, recommendedGpu: 1, vram: '24GB' },
  'beomi/Llama-3-Open-Ko-8B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '16GB' },
  'Qwen/Qwen2.5-Coder-7B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '16GB' },
  'Qwen/Qwen2.5-Coder-32B-Instruct': { minGpu: 2, recommendedGpu: 4, vram: '80GB' },
  'Qwen/Qwen2.5-3B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '8GB' },
  'Qwen/Qwen2.5-1.5B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '4GB' },
  'microsoft/Phi-3-mini-4k-instruct': { minGpu: 1, recommendedGpu: 1, vram: '8GB' },
};

// Use case configurations
const QDRANT_USE_CASES: Record<string, { name: string; description: string }> = {
  'rag': { name: 'RAG 검색', description: '문서 임베딩 및 시맨틱 검색' },
  'recommendation': { name: '추천 시스템', description: '사용자/아이템 유사도 기반 추천' },
  'dedup': { name: '중복 제거', description: '유사 문서/이미지 클러스터링' },
};

// Image model categories and models
const IMAGE_MODEL_CATEGORIES = {
  'pony': {
    name: 'Pony Diffusion',
    description: 'Community models with extensive tag-based prompt support',
    models: [
      { id: 'pony_diffusion', name: 'Pony Diffusion', vram: '8GB' },
      { id: 'pony_diffusion_v7', name: 'Pony Diffusion V7', vram: '8GB' },
    ]
  },
  'sdxl_community': {
    name: 'SDXL Community',
    description: 'Community-trained models built on the SDXL architecture',
    models: [
      { id: 'illustrious', name: 'Illustrious', vram: '12GB' },
      { id: 'noobai', name: 'NoobAI', vram: '12GB' },
    ]
  },
  'stable_diffusion': {
    name: 'Stable Diffusion',
    description: "Stability AI's foundational open-source diffusion models",
    models: [
      { id: 'sd15', name: 'Stable Diffusion 1.x', vram: '8GB' },
      { id: 'sdxl', name: 'Stable Diffusion XL', vram: '12GB' },
    ]
  }
};

const COMFYUI_USE_CASES: Record<string, { name: string; description: string }> = {
  'image': { name: '이미지 생성', description: '다양한 모델로 이미지 생성' },
  'video': { name: '동영상 생성', description: 'WAN 2.2 비디오 생성 (24GB+ VRAM)' },
};

const NEO4J_USE_CASES: Record<string, { name: string; description: string }> = {
  'knowledge': { name: '지식 그래프', description: 'Ontology 및 관계 추론' },
  'social': { name: '소셜 네트워크', description: '사용자 관계 분석' },
  'fraud': { name: '이상 탐지', description: '패턴 기반 사기 탐지' },
};

// Progress Bar component
const ProgressBar = ({ value, max, color = 'blue', showLabel = true }: { value: number; max: number; color?: string; showLabel?: boolean }) => {
  const percent = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const colorClass: Record<string, string> = {
    blue: 'var(--accent-blue)',
    green: 'var(--accent-green)',
    red: 'var(--accent-red)',
    yellow: 'var(--accent-yellow)',
    purple: 'var(--accent-purple)',
    auto: percent >= 90 ? 'var(--accent-red)' : percent >= 70 ? 'var(--accent-yellow)' : 'var(--accent-green)'
  };
  const barColor = colorClass[color] || color;

  return (
    <div className="progress-container">
      <div className="progress-bar" style={{ height: 8 }}>
        <div className="progress-fill" style={{ width: `${percent}%`, background: barColor }} />
      </div>
      {showLabel && <span className="progress-label">{percent.toFixed(1)}%</span>}
    </div>
  );
};

export function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [clusterSummary, setClusterSummary] = useState<ClusterSummary | null>(null);
  const [nodeMetrics, setNodeMetrics] = useState<NodeMetrics[]>([]);
  const [workloads, setWorkloads] = useState<Workloads>({});
  const [actionLoading, setActionLoading] = useState<ActionLoadingMap>({});

  // Storage states
  const [storageCapacity, setStorageCapacity] = useState<StorageCapacity | null>(null);
  const [storageInfo, setStorageInfo] = useState<StorageInfo | null>(null);
  const [storageBreakdown, setStorageBreakdown] = useState<StorageBreakdown | null>(null);
  const [storageByNode, setStorageByNode] = useState<StorageByNode | null>(null);
  const [rustfsAllocSize, setRustfsAllocSize] = useState(50);

  // vLLM config
  const [vllmConfig, setVllmConfig] = useState({
    model: 'Qwen/Qwen2.5-7B-Instruct',
    gpuCount: 1,
    gpuIndices: [] as number[],
    nodeSelector: '',
    cpuLimit: '4',
    memoryLimit: '16Gi'
  });

  // Qdrant config
  const [qdrantConfig, setQdrantConfig] = useState({
    useCase: 'rag',
    storageSize: 20,
    replicas: 1,
    nodeSelector: ''
  });

  // ComfyUI config
  const [comfyuiConfig, setComfyuiConfig] = useState({
    useCase: 'image',
    imageModel: 'sdxl',
    imageModelCategory: 'stable_diffusion',
    videoModel: 'wan22',
    gpuCount: 1,
    gpuIndices: [] as number[],
    nodeSelector: '',
    memoryLimit: '16Gi',
    storageSize: 100
  });

  // Neo4j config
  const [neo4jConfig, setNeo4jConfig] = useState({
    useCase: 'knowledge',
    replicas: 1,
    nodeSelector: '',
    memoryLimit: '8Gi',
    storageSize: 50
  });

  const currentModelReq = MODEL_REQUIREMENTS[vllmConfig.model] || { minGpu: 1, recommendedGpu: 1, vram: '16GB' };

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [summaryRes, metricsRes, workloadsRes] = await Promise.all([
        axios.get('/api/cluster/summary'),
        axios.get('/api/nodes/metrics'),
        axios.get('/api/workloads'),
      ]);
      setClusterSummary(summaryRes.data);
      const metricsData = metricsRes.data?.nodes || metricsRes.data || [];
      setNodeMetrics(Array.isArray(metricsData) ? metricsData : []);
      setWorkloads(workloadsRes.data?.workloads || {});

      // Try to fetch storage info
      try {
        const [capacityRes, infoRes, breakdownRes, byNodeRes] = await Promise.all([
          axios.get('/api/storage/capacity'),
          axios.get('/api/storage/info'),
          axios.get('/api/storage/usage-breakdown'),
          axios.get('/api/storage/usage-by-node')
        ]);
        setStorageCapacity(capacityRes.data);
        setStorageInfo(infoRes.data);
        setStorageBreakdown(breakdownRes.data);
        setStorageByNode(byNodeRes.data);
      } catch {
        // Storage API might not be available
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleModelChange = (model: string) => {
    const req = MODEL_REQUIREMENTS[model] || { minGpu: 1, recommendedGpu: 1, vram: '16GB' };
    setVllmConfig(prev => ({
      ...prev,
      model,
      gpuCount: Math.max(prev.gpuCount, req.minGpu)
    }));
  };

  const handleWorkloadAction = async (name: string, action: 'start' | 'stop' | 'scale' | 'expand', replicas = 1, storageSizeGb: number | null = null) => {
    setActionLoading(prev => ({ ...prev, [name]: { loading: true, action } }));
    try {
      const payload: Record<string, unknown> = { action, replicas };
      if (storageSizeGb !== null) {
        payload.storage_size_gb = storageSizeGb;
      }
      // Include config for specific workloads
      if (name === 'vllm' && action === 'start') {
        payload.config = vllmConfig;
      } else if (name === 'qdrant' && action === 'start') {
        payload.config = qdrantConfig;
      } else if (name === 'comfyui' && action === 'start') {
        payload.config = comfyuiConfig;
      } else if (name === 'neo4j' && action === 'start') {
        payload.config = neo4jConfig;
      }

      await axios.post(`/api/workloads/${name}`, payload);
      setTimeout(() => {
        fetchData();
        setActionLoading(prev => ({ ...prev, [name]: { loading: false } }));
      }, 2000);
    } catch (error) {
      console.error(`Failed to ${action} ${name}:`, error);
      setActionLoading(prev => ({ ...prev, [name]: { loading: false } }));
    }
  };

  const getGpuNodes = () => {
    return nodeMetrics.filter(node => (node.gpu_capacity || 0) > 0);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  const resources = clusterSummary?.resources || { cpu: { usage: 0, capacity: 0, percent: 0 }, memory: { usage: 0, capacity: 0, percent: 0 } };
  const pods = clusterSummary?.pods || { running: 0, total: 0, pending: 0, failed: 0 };

  return (
    <div className="dashboard">
      {/* Stats Cards */}
      <section className="section">
        <h2 className="section-title">클러스터 상태</h2>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-header">
              <div className="stat-icon" style={{ background: 'var(--accent-blue)' }}>
                <Server size={18} color="white" />
              </div>
              <span className="stat-label">노드</span>
            </div>
            <div className="stat-value">{clusterSummary?.nodes?.ready || 0}</div>
            <div className="stat-sub">/ {clusterSummary?.nodes?.total || 0} 전체</div>
          </div>

          <div className="stat-card">
            <div className="stat-header">
              <div className="stat-icon" style={{ background: 'var(--accent-green)' }}>
                <Box size={18} color="white" />
              </div>
              <span className="stat-label">Pod</span>
            </div>
            <div className="stat-value">{pods.running || 0}</div>
            <div className="stat-sub">
              실행중 / {pods.total || 0} 전체
              {pods.pending > 0 && <span className="badge warning" style={{ marginLeft: 8 }}>{pods.pending} 대기</span>}
              {pods.failed > 0 && <span className="badge error" style={{ marginLeft: 4 }}>{pods.failed} 실패</span>}
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-header">
              <div className="stat-icon" style={{ background: 'var(--accent-purple)' }}>
                <Cpu size={18} color="white" />
              </div>
              <span className="stat-label">CPU 사용률</span>
            </div>
            <div className="stat-value">{resources.cpu?.percent || 0}%</div>
            <div className="stat-sub">{((resources.cpu?.usage || 0) / 1000).toFixed(1)} / {((resources.cpu?.capacity || 0) / 1000).toFixed(0)} cores</div>
            <ProgressBar value={resources.cpu?.percent || 0} max={100} color="auto" showLabel={false} />
          </div>

          <div className="stat-card">
            <div className="stat-header">
              <div className="stat-icon" style={{ background: 'var(--accent-orange)' }}>
                <MemoryStick size={18} color="white" />
              </div>
              <span className="stat-label">메모리 사용률</span>
            </div>
            <div className="stat-value">{resources.memory?.percent || 0}%</div>
            <div className="stat-sub">{((resources.memory?.usage || 0) / 1024).toFixed(1)} / {((resources.memory?.capacity || 0) / 1024).toFixed(0)} GB</div>
            <ProgressBar value={resources.memory?.percent || 0} max={100} color="auto" showLabel={false} />
          </div>
        </div>
      </section>

      {/* Storage Usage Breakdown - Per Node */}
      {storageByNode && storageByNode.nodes && storageByNode.nodes.length > 0 && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">
              <HardDrive size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              스토리지 사용량 (노드별)
            </h2>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {storageByNode.nodes.map((nodeStorage) => (
              <div key={nodeStorage.node_name} className="storage-breakdown-container" style={{ background: 'var(--bg-secondary)', borderRadius: 8, padding: 16 }}>
                {/* Node Header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Server size={16} />
                    <span style={{ fontWeight: 600, fontSize: 15 }}>{nodeStorage.node_name}</span>
                    <span style={{
                      fontSize: 11,
                      padding: '2px 8px',
                      borderRadius: 10,
                      background: nodeStorage.role === 'Master' ? 'var(--accent-blue)' : 'var(--accent-green)',
                      color: 'white'
                    }}>
                      {nodeStorage.role}
                    </span>
                    {nodeStorage.root_disk_type && (
                      <span style={{
                        fontSize: 11,
                        padding: '2px 8px',
                        borderRadius: 10,
                        background: nodeStorage.root_disk_type === 'SSD' ? 'var(--accent-purple)' : 'var(--accent-orange)',
                        color: 'white'
                      }}>
                        {nodeStorage.root_disk_type}
                      </span>
                    )}
                  </div>
                  <div className="storage-total-info" style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 13 }}>
                    <span>{nodeStorage.total_used_human} / {nodeStorage.total_capacity_human}</span>
                    <span className="storage-usage-percent" style={{
                      background: nodeStorage.usage_percent >= 90 ? 'var(--accent-red)' : nodeStorage.usage_percent >= 70 ? 'var(--accent-yellow)' : 'var(--accent-green)',
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: 12,
                      fontSize: 11
                    }}>
                      {nodeStorage.usage_percent}% 사용
                    </span>
                  </div>
                </div>

                {/* Storage Bar Chart */}
                <div className="storage-breakdown-bar" style={{
                  display: 'flex',
                  height: 20,
                  borderRadius: 4,
                  overflow: 'hidden',
                  background: 'var(--bg-tertiary)',
                  marginBottom: 12
                }}>
                  {nodeStorage.categories?.filter(cat => cat.type !== 'free').map((cat) => (
                    <div
                      key={cat.type}
                      className="storage-breakdown-segment"
                      style={{
                        width: `${(cat.allocated / nodeStorage.total_capacity) * 100}%`,
                        backgroundColor: cat.color,
                        minWidth: cat.allocated > 0 ? 2 : 0,
                        transition: 'width 0.3s ease'
                      }}
                      title={`${cat.name}: ${cat.allocated_human}`}
                    />
                  ))}
                </div>

                {/* 루트 디스크 사용량 요약 */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--text-muted)' }}>
                    루트 디스크 사용 현황 ({nodeStorage.root_disk_type || 'Unknown'})
                  </div>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
                    gap: 8
                  }}>
                    {nodeStorage.categories?.filter(cat =>
                      cat.type !== 'free' &&
                      cat.type !== 'hdd' &&
                      cat.type !== 'pvc-remote'
                    ).map((cat) => (
                      <div key={cat.name} style={{
                        padding: '6px 10px',
                        background: 'var(--bg-tertiary)',
                        borderRadius: 5,
                        borderLeft: `3px solid ${cat.color}`
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                          <span style={{ fontWeight: 500, fontSize: 12 }}>{cat.name}</span>
                          <span style={{ fontFamily: 'monospace', color: 'var(--text-muted)', fontSize: 11 }}>{cat.allocated_human}</span>
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{cat.description}</div>
                        {cat.type === 'rustfs' && cat.used && cat.used > 0 && (
                          <div style={{ fontSize: 10, color: 'var(--accent-blue)', marginTop: 2 }}>
                            사용: {cat.used_human}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* 추가 디스크 (HDD) */}
                {nodeStorage.categories?.filter(cat => cat.type === 'hdd').length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--text-muted)' }}>
                      추가 디스크
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {nodeStorage.categories?.filter(cat => cat.type === 'hdd').map((disk: any) => (
                        <div key={disk.name} style={{
                          padding: '10px 12px',
                          background: 'var(--bg-tertiary)',
                          borderRadius: 6,
                          borderLeft: `3px solid ${disk.color}`
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <HardDrive size={14} style={{ color: disk.color }} />
                              <span style={{ fontWeight: 600, fontSize: 13 }}>{disk.name}</span>
                              <span style={{
                                fontSize: 10,
                                padding: '2px 6px',
                                borderRadius: 8,
                                background: disk.usage_info === '미할당' ? 'var(--bg-secondary)' : 'var(--accent-blue)',
                                color: disk.usage_info === '미할당' ? 'var(--text-muted)' : 'white'
                              }}>
                                {disk.usage_info || '미할당'}
                              </span>
                            </div>
                            <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{disk.allocated_human}</span>
                          </div>
                          {/* 디스크 사용량 바 */}
                          {disk.used > 0 && (
                            <div style={{ marginTop: 6 }}>
                              <div style={{
                                height: 4,
                                background: 'var(--bg-secondary)',
                                borderRadius: 2,
                                overflow: 'hidden'
                              }}>
                                <div style={{
                                  height: '100%',
                                  width: `${(disk.used / disk.allocated) * 100}%`,
                                  background: disk.color,
                                  transition: 'width 0.3s ease'
                                }} />
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 11, color: 'var(--text-muted)' }}>
                                <span>사용: {disk.used_human}</span>
                                <span>여유: {((disk.allocated - disk.used) / 1024 / 1024 / 1024).toFixed(1)} GB</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* PVC (별도 스토리지만 표시) */}
                {nodeStorage.categories?.filter(cat => cat.type === 'pvc-remote').length > 0 && (
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--text-muted)' }}>
                      Persistent Volumes (별도 스토리지)
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {nodeStorage.categories?.filter(cat => cat.type === 'pvc-remote').map((pvc) => (
                        <div key={pvc.name} style={{
                          padding: '6px 10px',
                          background: 'var(--bg-tertiary)',
                          borderRadius: 5,
                          borderLeft: `3px solid ${pvc.color}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}>
                          <div>
                            <span style={{ fontWeight: 500, fontSize: 12 }}>{pvc.name}</span>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{pvc.description}</div>
                          </div>
                          <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{pvc.allocated_human}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Node Metrics */}
      <section className="section">
        <div className="section-header" style={{ flexWrap: 'wrap' }}>
          <h2 className="section-title">노드 현황</h2>
          <div style={{ flex: 1 }} />
          <div className="resource-legend" style={{ marginBottom: 0 }}>
            <div className="legend-item">
              <div className="legend-color usage"></div>
              <span className="legend-label">사용량</span>
            </div>
            <div className="legend-item">
              <div className="legend-color requests"></div>
              <span className="legend-label">Requests</span>
            </div>
            <div className="legend-item">
              <div className="legend-color limits"></div>
              <span className="legend-label">Limits</span>
            </div>
          </div>
        </div>
        <div className="node-htop-list">
          {nodeMetrics.map((node) => {
            const cpuUsageClass = (node.cpu_percent || 0) >= 90 ? 'danger' : (node.cpu_percent || 0) >= 70 ? 'warning' : '';
            const memUsageClass = (node.memory_percent || 0) >= 90 ? 'danger' : (node.memory_percent || 0) >= 70 ? 'warning' : '';
            const gpuCapacity = node.gpu_capacity || 0;
            const gpuUsed = node.gpu_used || 0;
            const gpuType = node.gpu_type || '';
            const gpuStatusArray = node.gpu_status_array || [];

            // roles 처리
            const nodeRoles = node.roles || (node.role ? [node.role] : []);
            const hasControlPlane = nodeRoles.includes('control-plane');
            const hasMaster = nodeRoles.includes('master');
            const hasEtcd = nodeRoles.includes('etcd');
            const otherRoles = nodeRoles.filter(r => !['control-plane', 'master', 'etcd'].includes(r));

            const displayRoles: string[] = [];
            if (hasControlPlane || hasMaster) {
              displayRoles.push('control-plane');
            }
            if (hasEtcd) {
              displayRoles.push('etcd');
            }
            displayRoles.push(...otherRoles);

            return (
              <div key={node.name} className="node-htop-card">
                <div className="node-htop-header">
                  <div className="node-htop-info">
                    <span className={`status-dot ${node.status === 'Ready' ? 'healthy' : 'error'}`}></span>
                    <span className="node-htop-name">{node.name}</span>
                    <div className="node-htop-roles">
                      {displayRoles.map((role) => (
                        <span key={role} className="node-htop-role">{role}</span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="node-htop-body">
                  {/* CPU 바 (htop 스타일) */}
                  <div className="htop-bar-wrapper">
                    <div className="htop-bar htop-bar-cpu">
                      <span className="htop-label">CPU</span>
                      <div className="htop-bar-container">
                        {/* Limits 바 (가장 뒤) */}
                        <div
                          className="htop-bar-fill limits"
                          style={{ width: `${Math.min((node.cpu_limits || 0) / (node.cpu_capacity || 1) * 100, 100)}%` }}
                        />
                        {/* Requests 바 */}
                        <div
                          className="htop-bar-fill requests"
                          style={{ width: `${node.cpu_requests_percent || 0}%` }}
                        />
                        {/* 사용량 바 (가장 앞) */}
                        <div
                          className={`htop-bar-fill usage ${cpuUsageClass}`}
                          style={{ width: `${node.cpu_percent || 0}%` }}
                        />
                        {/* 구분선 */}
                        <div className="htop-bar-segments">
                          {[...Array(10)].map((_, i) => <div key={i} className="htop-bar-segment" />)}
                        </div>
                      </div>
                      <span className="htop-bar-value">
                        {((node.cpu_usage || node.cpu_used || 0) / 1000).toFixed(1)} / {((node.cpu_capacity || 0) / 1000).toFixed(0)} cores
                      </span>
                      <span className="htop-bar-percent">{(node.cpu_percent || 0).toFixed(0)}%</span>
                    </div>
                    <div className="htop-resource-detail">
                      <span className="resource-detail-item requests">
                        Req: {((node.cpu_requests || 0) / 1000).toFixed(1)}c ({(node.cpu_requests_percent || 0).toFixed(0)}%)
                      </span>
                      <span className="resource-detail-item limits">
                        Lim: {((node.cpu_limits || 0) / 1000).toFixed(1)}c ({Math.min((node.cpu_limits || 0) / (node.cpu_capacity || 1) * 100, 100).toFixed(0)}%)
                      </span>
                    </div>
                  </div>

                  {/* 메모리 바 (htop 스타일) */}
                  <div className="htop-bar-wrapper">
                    <div className="htop-bar htop-bar-mem">
                      <span className="htop-label">MEM</span>
                      <div className="htop-bar-container">
                        {/* Limits 바 */}
                        <div
                          className="htop-bar-fill limits"
                          style={{ width: `${Math.min((node.memory_limits || 0) / (node.memory_capacity || 1) * 100, 100)}%` }}
                        />
                        {/* Requests 바 */}
                        <div
                          className="htop-bar-fill requests"
                          style={{ width: `${node.memory_requests_percent || 0}%` }}
                        />
                        {/* 사용량 바 */}
                        <div
                          className={`htop-bar-fill usage ${memUsageClass}`}
                          style={{ width: `${node.memory_percent || 0}%` }}
                        />
                        <div className="htop-bar-segments">
                          {[...Array(10)].map((_, i) => <div key={i} className="htop-bar-segment" />)}
                        </div>
                      </div>
                      <span className="htop-bar-value">
                        {((node.memory_usage || node.memory_used || 0) / 1024).toFixed(1)} / {((node.memory_capacity || 0) / 1024).toFixed(0)} GB
                      </span>
                      <span className="htop-bar-percent">{(node.memory_percent || 0).toFixed(0)}%</span>
                    </div>
                    <div className="htop-resource-detail">
                      <span className="resource-detail-item requests">
                        Req: {((node.memory_requests || 0) / 1024).toFixed(1)}G ({(node.memory_requests_percent || 0).toFixed(0)}%)
                      </span>
                      <span className="resource-detail-item limits">
                        Lim: {((node.memory_limits || 0) / 1024).toFixed(1)}G ({Math.min((node.memory_limits || 0) / (node.memory_capacity || 1) * 100, 100).toFixed(0)}%)
                      </span>
                    </div>
                  </div>

                  {/* 스토리지 바 */}
                  {(node.storage_capacity || 0) > 0 && (
                    <div className="htop-bar htop-bar-storage">
                      <span className="htop-label">
                        <HardDrive size={12} style={{ marginRight: 4 }} />
                        Disk
                      </span>
                      <div className="htop-bar-container">
                        <div
                          className={`htop-bar-fill usage ${(node.storage_percent || 0) >= 90 ? 'danger' : (node.storage_percent || 0) >= 70 ? 'warning' : ''}`}
                          style={{ width: `${node.storage_percent || 0}%` }}
                        />
                        <div className="htop-bar-segments">
                          {[...Array(10)].map((_, i) => <div key={i} className="htop-bar-segment" />)}
                        </div>
                      </div>
                      <span className="htop-bar-value">
                        {((node.storage_used || 0) / 1024).toFixed(0)} / {((node.storage_capacity || 0) / 1024).toFixed(0)} GB
                      </span>
                      <span className="htop-bar-percent">{(node.storage_percent || 0).toFixed(0)}%</span>
                    </div>
                  )}

                  {/* GPU 미터 (nvtop 스타일) - 각 GPU별 상세 표시 */}
                  {gpuCapacity > 0 && (
                    <div className="gpu-detailed-section" style={{ marginTop: 12 }}>
                      <div className="gpu-section-header" style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Zap size={14} style={{ color: 'var(--accent-yellow)' }} />
                        <span style={{ fontWeight: 600 }}>GPU ({gpuType || 'Unknown'})</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{gpuUsed} / {gpuCapacity} 사용</span>
                      </div>
                      {node.gpu_details && node.gpu_details.length > 0 ? (
                        node.gpu_details.map((gpu: any) => (
                          <div key={gpu.index} className="htop-bar" style={{ marginBottom: 8 }}>
                            <span className="htop-label" style={{ minWidth: 60 }}>
                              GPU {gpu.index}
                              <span style={{
                                marginLeft: 6,
                                color: gpu.in_use ? 'var(--accent-green)' : 'var(--text-muted)',
                                fontWeight: gpu.in_use ? 'bold' : 'normal'
                              }}>
                                {gpu.in_use ? '●' : '○'}
                              </span>
                            </span>
                            <div className="htop-bar-container">
                              <div
                                className={`htop-bar-fill usage ${gpu.memory_percent >= 90 ? 'danger' : gpu.memory_percent >= 70 ? 'warning' : ''}`}
                                style={{ width: `${gpu.memory_percent || 0}%` }}
                              />
                              <div className="htop-bar-segments">
                                {[...Array(10)].map((_, i) => <div key={i} className="htop-bar-segment" />)}
                              </div>
                            </div>
                            <span className="htop-bar-value" style={{ minWidth: 120 }}>
                              {(gpu.memory_used / 1024).toFixed(1)} / {(gpu.memory_total / 1024).toFixed(1)} GB
                            </span>
                            <span className="htop-bar-percent">{gpu.memory_percent}%</span>
                            <span className="htop-bar-util" style={{ marginLeft: 8, color: 'var(--text-muted)', fontSize: 12 }}>
                              ({gpu.utilization_percent}% util)
                            </span>
                          </div>
                        ))
                      ) : (
                        // Fallback: 상세 정보가 없으면 간단한 표시
                        [...Array(gpuCapacity)].map((_, i) => {
                          const isUsed = gpuStatusArray && gpuStatusArray[i] === true;
                          return (
                            <div key={i} className="gpu-simple-bar" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                              <span style={{ minWidth: 60, fontSize: 13 }}>GPU {i}</span>
                              <span style={{
                                color: isUsed ? 'var(--accent-green)' : 'var(--text-muted)',
                                fontWeight: isUsed ? 'bold' : 'normal'
                              }}>
                                {isUsed ? '●' : '○'}
                              </span>
                              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                                {isUsed ? '사용 중' : '사용 가능'}
                              </span>
                            </div>
                          );
                        })
                      )}

                      {node.gpu_pod_list && node.gpu_pod_list.length > 0 && (
                        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border-color)', fontSize: 12 }}>
                          <div style={{ color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>
                            🐳 GPU 사용 Pod:
                          </div>
                          {node.gpu_pod_list.map((pod: any, idx: number) => (
                            <div
                              key={idx}
                              style={{
                                padding: '6px 8px',
                                marginBottom: 4,
                                backgroundColor: 'var(--bg-secondary)',
                                borderRadius: 4,
                                fontSize: 11,
                                color: 'var(--text-secondary)'
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                  <strong>{pod.pod}</strong>
                                  <span style={{ marginLeft: 8, color: 'var(--accent-blue)' }}>
                                    {pod.gpu_count} GPU{pod.gpu_count > 1 ? 's' : ''}
                                  </span>
                                </div>
                                {pod.gpu_indices && pod.gpu_indices.length > 0 && (
                                  <span style={{
                                    fontSize: 10,
                                    color: 'var(--accent-green)',
                                    backgroundColor: 'rgba(52, 211, 153, 0.1)',
                                    padding: '2px 6px',
                                    borderRadius: 4
                                  }}>
                                    GPU #{pod.gpu_indices.join(', #')}
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, display: 'flex', gap: 8 }}>
                                <span>{pod.namespace} / {pod.container}</span>
                                {pod.node && <span style={{ color: 'var(--accent-yellow)' }}>@ {pod.node}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Workloads Control */}
      <section className="section">
        <div className="section-header">
          <h2 className="section-title">워크로드 컨트롤</h2>
        </div>
        <div className="workloads-grid">
          {/* vLLM */}
          <div className="card workload-card">
            <div className="workload-header">
              <div className="workload-info">
                <h3>🤖 vLLM</h3>
                <p>LLM 추론 서버</p>
              </div>
              <span className={`workload-status ${workloads.vllm?.status === 'running' ? 'running' : workloads.vllm?.status === 'stopped' ? 'stopped' : 'not_deployed'}`}>
                {workloads.vllm?.status === 'running' ? '실행중' : workloads.vllm?.status === 'stopped' ? '중지됨' : '미배포'}
              </span>
            </div>

            {/* vLLM Config (when stopped) */}
            {(workloads.vllm?.status === 'stopped' || workloads.vllm?.status === 'not_deployed' || !workloads.vllm?.status) && (
              <div className="workload-config-section">
                <div className="workload-config-row">
                  <div className="config-group" style={{ flex: 2 }}>
                    <label>모델 선택</label>
                    <select value={vllmConfig.model} onChange={(e) => handleModelChange(e.target.value)}>
                      <optgroup label="Agent/Tool Use 최적화">
                        <option value="Qwen/Qwen2.5-7B-Instruct">Qwen2.5-7B-Instruct (추천) - 1 GPU</option>
                        <option value="Qwen/Qwen2.5-14B-Instruct">Qwen2.5-14B-Instruct - 1~2 GPU</option>
                        <option value="Qwen/Qwen2.5-32B-Instruct">Qwen2.5-32B-Instruct - 2~4 GPU</option>
                        <option value="Qwen/Qwen2.5-72B-Instruct">Qwen2.5-72B-Instruct - 4~8 GPU</option>
                      </optgroup>
                      <optgroup label="한국어 특화">
                        <option value="yanolja/EEVE-Korean-Instruct-10.8B-v1.0">EEVE-Korean 10.8B - 1 GPU</option>
                        <option value="beomi/Llama-3-Open-Ko-8B-Instruct">Llama-3-Ko 8B - 1 GPU</option>
                      </optgroup>
                      <optgroup label="코딩 특화">
                        <option value="Qwen/Qwen2.5-Coder-7B-Instruct">Qwen2.5-Coder-7B - 1 GPU</option>
                        <option value="Qwen/Qwen2.5-Coder-32B-Instruct">Qwen2.5-Coder-32B - 2~4 GPU</option>
                      </optgroup>
                      <optgroup label="경량 모델">
                        <option value="Qwen/Qwen2.5-3B-Instruct">Qwen2.5-3B-Instruct - 1 GPU</option>
                        <option value="Qwen/Qwen2.5-1.5B-Instruct">Qwen2.5-1.5B-Instruct - 1 GPU</option>
                        <option value="microsoft/Phi-3-mini-4k-instruct">Phi-3-mini-4k - 1 GPU</option>
                      </optgroup>
                    </select>
                  </div>
                  <div className="config-group">
                    <label>GPU 수 (최소: {currentModelReq.minGpu})</label>
                    <select
                      value={vllmConfig.gpuCount}
                      onChange={(e) => setVllmConfig({ ...vllmConfig, gpuCount: parseInt(e.target.value) })}
                    >
                      {[1, 2, 4, 8].filter(n => n >= currentModelReq.minGpu).map(n => (
                        <option key={n} value={n}>
                          {n} GPU {n === currentModelReq.recommendedGpu ? '(권장)' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="workload-config-row">
                  <div className="config-group">
                    <label>노드 선택 (GPU)</label>
                    <select
                      value={vllmConfig.nodeSelector}
                      onChange={(e) => setVllmConfig({ ...vllmConfig, nodeSelector: e.target.value, gpuIndices: [] })}
                    >
                      <option value="">자동 (스케줄러 결정)</option>
                      {getGpuNodes().map(node => {
                        const gpuCount = node.gpu_capacity || 0;
                        const isEligible = gpuCount >= vllmConfig.gpuCount;
                        return (
                          <option key={node.name} value={node.name} disabled={!isEligible}>
                            {node.name} ({gpuCount} GPU){!isEligible ? ' - GPU 부족' : ''}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                  <div className="config-group">
                    <label>CPU</label>
                    <select value={vllmConfig.cpuLimit} onChange={(e) => setVllmConfig({ ...vllmConfig, cpuLimit: e.target.value })}>
                      <option value="2">2 코어</option>
                      <option value="4">4 코어</option>
                      <option value="8">8 코어</option>
                      <option value="16">16 코어</option>
                    </select>
                  </div>
                  <div className="config-group">
                    <label>메모리</label>
                    <select value={vllmConfig.memoryLimit} onChange={(e) => setVllmConfig({ ...vllmConfig, memoryLimit: e.target.value })}>
                      <option value="8Gi">8 GB</option>
                      <option value="16Gi">16 GB</option>
                      <option value="32Gi">32 GB</option>
                      <option value="64Gi">64 GB</option>
                      <option value="128Gi">128 GB</option>
                    </select>
                  </div>
                </div>
                {/* GPU Index Selection - 노드 선택 시 또는 GPU 노드가 있을 때 표시 */}
                {(() => {
                  const selectedNode = vllmConfig.nodeSelector
                    ? nodeMetrics.find(n => n.name === vllmConfig.nodeSelector)
                    : null;
                  const gpuCapacity = selectedNode?.gpu_capacity || 0;
                  const gpuStatusArray = selectedNode?.gpu_status_array || [];
                  const gpuNodes = getGpuNodes();
                  const maxGpuOnAnyNode = Math.max(...gpuNodes.map(n => n.gpu_capacity || 0), 0);
                  const displayGpuCount = vllmConfig.nodeSelector ? gpuCapacity : maxGpuOnAnyNode;

                  if (displayGpuCount > 0) {
                    return (
                      <div className="gpu-index-selection">
                        <label>GPU 인덱스 선택 {!vllmConfig.nodeSelector && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(노드 선택 시 적용)</span>}</label>
                        <div className="gpu-index-buttons">
                          {[...Array(displayGpuCount)].map((_, idx) => {
                            const isSelected = vllmConfig.gpuIndices.includes(idx);
                            const isInUse = vllmConfig.nodeSelector && gpuStatusArray[idx] === true;
                            const isDisabled = (!isSelected && vllmConfig.gpuIndices.length >= vllmConfig.gpuCount) || isInUse;
                            return (
                              <button
                                key={idx}
                                className={`gpu-index-btn ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''} ${isInUse ? 'in-use' : ''}`}
                                onClick={() => {
                                  if (isInUse) return;
                                  if (isSelected) {
                                    setVllmConfig({ ...vllmConfig, gpuIndices: vllmConfig.gpuIndices.filter(i => i !== idx) });
                                  } else if (!isDisabled) {
                                    setVllmConfig({ ...vllmConfig, gpuIndices: [...vllmConfig.gpuIndices, idx].sort((a, b) => a - b) });
                                  }
                                }}
                                disabled={isDisabled}
                                title={isInUse ? `GPU ${idx} (사용 중)` : `GPU ${idx}`}
                              >
                                GPU {idx}
                                {isInUse && <span style={{ marginLeft: 4, color: 'var(--accent-red)' }}>●</span>}
                              </button>
                            );
                          })}
                        </div>
                        <div className="gpu-index-hint">
                          {vllmConfig.gpuIndices.length > 0
                            ? `선택됨: GPU ${vllmConfig.gpuIndices.join(', ')}`
                            : `${vllmConfig.gpuCount}개의 GPU를 선택하세요 (미선택 시 자동 할당)`}
                        </div>
                      </div>
                    );
                  }
                  return null;
                })()}

                <div className="resource-preview">
                  <div className="resource-item">
                    <Zap size={14} />
                    <span>GPU {vllmConfig.gpuCount}개</span>
                    <span className="value">VRAM {currentModelReq.vram} 필요</span>
                  </div>
                  {vllmConfig.gpuIndices.length > 0 && (
                    <div className="resource-item">
                      <span>인덱스:</span>
                      <span className="value">{vllmConfig.gpuIndices.join(', ')}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="workload-controls">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('vllm', 'start')}
                disabled={actionLoading.vllm?.loading || workloads.vllm?.status === 'running'}
              >
                <Play size={16} /> {actionLoading.vllm?.loading && actionLoading.vllm?.action === 'start' ? '시작 중...' : '실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('vllm', 'stop')}
                disabled={actionLoading.vllm?.loading || workloads.vllm?.status !== 'running'}
              >
                <Square size={16} /> {actionLoading.vllm?.loading && actionLoading.vllm?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>

            {/* Running state info */}
            {workloads.vllm?.status === 'running' && !actionLoading.vllm?.loading && (
              <>
                <div className="resource-preview" style={{ marginTop: 8 }}>
                  <div className="resource-item">
                    <Box size={14} />
                    <span>모델:</span>
                    <span className="value" style={{ fontSize: 11 }}>{vllmConfig.model.split('/').pop()}</span>
                  </div>
                </div>
                <div className="replica-counter">
                  <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>Replicas:</span>
                  <button onClick={() => handleWorkloadAction('vllm', 'scale', Math.max(1, (workloads.vllm?.replicas || 1) - 1))}>
                    <Minus size={16} />
                  </button>
                  <span>{workloads.vllm?.replicas || 0}</span>
                  <button onClick={() => handleWorkloadAction('vllm', 'scale', (workloads.vllm?.replicas || 0) + 1)}>
                    <Plus size={16} />
                  </button>
                </div>
              </>
            )}
          </div>

          {/* RustFS */}
          <div className="card workload-card">
            <div className="workload-header">
              <div className="workload-info">
                <h3>💾 RustFS</h3>
                <p>분산 스토리지</p>
              </div>
              <span className={`workload-status ${workloads.rustfs?.status === 'running' ? 'running' : workloads.rustfs?.status === 'stopped' ? 'stopped' : 'not_deployed'}`}>
                {workloads.rustfs?.status === 'running' ? '실행중' : workloads.rustfs?.status === 'stopped' ? '중지됨' : '미배포'}
              </span>
            </div>

            {/* Storage Allocator (when stopped) */}
            {(workloads.rustfs?.status === 'stopped' || workloads.rustfs?.status === 'not_deployed' || !workloads.rustfs?.status) && (
              <div className="storage-allocator">
                <div className="allocator-header">
                  <HardDrive size={16} />
                  <span>스토리지 할당</span>
                  <span className="allocator-value">{rustfsAllocSize} GB</span>
                </div>
                <input
                  type="range"
                  className="allocator-slider"
                  min={10}
                  max={storageCapacity ? Math.floor(storageCapacity.max_allocatable / (1024 * 1024 * 1024)) : 500}
                  value={rustfsAllocSize}
                  onChange={(e) => setRustfsAllocSize(Number(e.target.value))}
                />
                <div className="allocator-labels">
                  <span>10 GB</span>
                  <span>최대 {storageCapacity?.max_allocatable_human || '500 GB'}</span>
                </div>
                {storageCapacity?.current_pvc_size_human && (
                  <div className="allocator-current">
                    현재 할당됨: {storageCapacity.current_pvc_size_human}
                    {storageCapacity.supports_expansion && (
                      <span className="allocator-note allocator-note-success">✓ 동적 확장 지원</span>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="workload-controls">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('rustfs', 'start', 1, rustfsAllocSize)}
                disabled={actionLoading.rustfs?.loading || workloads.rustfs?.status === 'running'}
              >
                <Play size={16} /> {actionLoading.rustfs?.loading && actionLoading.rustfs?.action === 'start' ? '시작 중...' : `실행 (${rustfsAllocSize}GB)`}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('rustfs', 'stop')}
                disabled={actionLoading.rustfs?.loading || workloads.rustfs?.status !== 'running'}
              >
                <Square size={16} /> {actionLoading.rustfs?.loading && actionLoading.rustfs?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>

            {/* Storage expand panel (when running with dynamic expansion) */}
            {workloads.rustfs?.status === 'running' && storageCapacity?.supports_expansion && (
              <div className="storage-expand-panel">
                <div className="expand-header">
                  <HardDrive size={14} />
                  <span>스토리지 확장</span>
                  <span className="expand-badge">실시간</span>
                </div>
                <div className="expand-controls">
                  <button
                    className="expand-btn"
                    onClick={() => setRustfsAllocSize(prev => Math.max(10, prev - 10))}
                    disabled={rustfsAllocSize <= 10}
                  >
                    <ChevronDown size={14} />
                  </button>
                  <div className="expand-input-wrapper">
                    <input
                      type="number"
                      className="expand-input"
                      value={rustfsAllocSize}
                      min={10}
                      onChange={(e) => setRustfsAllocSize(Math.max(10, parseInt(e.target.value) || 10))}
                    />
                    <span className="expand-unit">GB</span>
                  </div>
                  <button
                    className="expand-btn"
                    onClick={() => setRustfsAllocSize(prev => prev + 10)}
                  >
                    <ChevronUp size={14} />
                  </button>
                </div>
                <button
                  className="btn btn-primary expand-apply-btn"
                  onClick={() => handleWorkloadAction('rustfs', 'expand', 1, rustfsAllocSize)}
                  disabled={actionLoading.rustfs?.loading}
                >
                  {rustfsAllocSize}GB로 확장
                </button>
              </div>
            )}

            {/* Storage info (when running) */}
            {storageInfo?.status === 'connected' && workloads.rustfs?.status === 'running' && (
              <div className="storage-info">
                <div className="storage-info-row">
                  <HardDrive size={16} color="var(--text-muted)" />
                  <span className="storage-label">전체 용량</span>
                  <span className="storage-value">{storageInfo.total_capacity_human}</span>
                </div>
                <div className="storage-info-row">
                  <Database size={16} color="var(--accent-blue)" />
                  <span className="storage-label">사용 중</span>
                  <span className="storage-value">{storageInfo.used_capacity_human}</span>
                </div>
                <div className="storage-progress">
                  <div className="storage-progress-bar" style={{ width: `${storageInfo.usage_percent || 0}%` }} />
                </div>
                <span className="storage-percent">{storageInfo.usage_percent || 0}% 사용</span>
              </div>
            )}
          </div>

          {/* Qdrant */}
          <div className="card workload-card">
            <div className="workload-header">
              <div className="workload-info">
                <h3>🔍 Qdrant</h3>
                <p>벡터 데이터베이스</p>
              </div>
              <span className={`workload-status ${workloads.qdrant?.status === 'running' ? 'running' : workloads.qdrant?.status === 'stopped' ? 'stopped' : 'not_deployed'}`}>
                {workloads.qdrant?.status === 'running' ? '실행중' : workloads.qdrant?.status === 'stopped' ? '중지됨' : '미배포'}
              </span>
            </div>

            {/* Qdrant Config (when stopped) */}
            {(workloads.qdrant?.status === 'stopped' || workloads.qdrant?.status === 'not_deployed' || !workloads.qdrant?.status) && (
              <div className="workload-config-section">
                <div className="workload-config-row">
                  <div className="config-group" style={{ flex: 2 }}>
                    <label>사용 용도</label>
                    <select value={qdrantConfig.useCase} onChange={(e) => setQdrantConfig({ ...qdrantConfig, useCase: e.target.value })}>
                      {Object.entries(QDRANT_USE_CASES).map(([key, value]) => (
                        <option key={key} value={key}>{value.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="use-case-description">{QDRANT_USE_CASES[qdrantConfig.useCase]?.description}</div>
                <div className="workload-config-row">
                  <div className="config-group">
                    <label>스토리지 크기</label>
                    <select value={qdrantConfig.storageSize} onChange={(e) => setQdrantConfig({ ...qdrantConfig, storageSize: parseInt(e.target.value) })}>
                      <option value="10">10 GB</option>
                      <option value="20">20 GB</option>
                      <option value="50">50 GB</option>
                      <option value="100">100 GB</option>
                      <option value="200">200 GB</option>
                    </select>
                  </div>
                  <div className="config-group">
                    <label>Replicas</label>
                    <select value={qdrantConfig.replicas} onChange={(e) => setQdrantConfig({ ...qdrantConfig, replicas: parseInt(e.target.value) })}>
                      <option value="1">1 (단일)</option>
                      <option value="2">2 (HA 기본)</option>
                      <option value="3">3 (권장)</option>
                    </select>
                  </div>
                  <div className="config-group">
                    <label>노드 선택</label>
                    <select value={qdrantConfig.nodeSelector} onChange={(e) => setQdrantConfig({ ...qdrantConfig, nodeSelector: e.target.value })}>
                      <option value="">자동 (스케줄러 결정)</option>
                      {nodeMetrics.map(node => (
                        <option key={node.name} value={node.name}>{node.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="resource-preview">
                  <div className="resource-item">
                    <Database size={14} />
                    <span>Storage:</span>
                    <span className="value">{qdrantConfig.storageSize} GB</span>
                  </div>
                  <div className="resource-item">
                    <Server size={14} />
                    <span>Replicas:</span>
                    <span className="value">{qdrantConfig.replicas}</span>
                  </div>
                  <div className="resource-item">
                    <Package size={14} />
                    <span>용도:</span>
                    <span className="value">{QDRANT_USE_CASES[qdrantConfig.useCase]?.name}</span>
                  </div>
                </div>
              </div>
            )}

            <div className="workload-controls">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('qdrant', 'start')}
                disabled={actionLoading.qdrant?.loading || workloads.qdrant?.status === 'running'}
              >
                <Play size={16} /> {actionLoading.qdrant?.loading && actionLoading.qdrant?.action === 'start' ? '시작 중...' : '실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('qdrant', 'stop')}
                disabled={actionLoading.qdrant?.loading || workloads.qdrant?.status !== 'running'}
              >
                <Square size={16} /> {actionLoading.qdrant?.loading && actionLoading.qdrant?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>

            {workloads.qdrant?.status === 'running' && !actionLoading.qdrant?.loading && (
              <div className="replica-counter">
                <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>Replicas:</span>
                <button onClick={() => handleWorkloadAction('qdrant', 'scale', Math.max(1, (workloads.qdrant?.replicas || 1) - 1))}>
                  <Minus size={16} />
                </button>
                <span>{workloads.qdrant?.replicas || 0}</span>
                <button onClick={() => handleWorkloadAction('qdrant', 'scale', (workloads.qdrant?.replicas || 0) + 1)}>
                  <Plus size={16} />
                </button>
              </div>
            )}
          </div>

          {/* ComfyUI */}
          <div className="card workload-card">
            <div className="workload-header">
              <div className="workload-info">
                <h3>🎨 ComfyUI</h3>
                <p>이미지/동영상 생성</p>
              </div>
              <span className={`workload-status ${workloads.comfyui?.status === 'running' ? 'running' : workloads.comfyui?.status === 'stopped' ? 'stopped' : 'not_deployed'}`}>
                {workloads.comfyui?.status === 'running' ? '실행중' : workloads.comfyui?.status === 'stopped' ? '중지됨' : '미배포'}
              </span>
            </div>

            {/* ComfyUI Config (when stopped) */}
            {(workloads.comfyui?.status === 'stopped' || workloads.comfyui?.status === 'not_deployed' || !workloads.comfyui?.status) && (
              <div className="workload-config-section">
                <div className="workload-config-row">
                  <div className="config-group" style={{ flex: 2 }}>
                    <label>생성 유형</label>
                    <select value={comfyuiConfig.useCase} onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, useCase: e.target.value })}>
                      {Object.entries(COMFYUI_USE_CASES).map(([key, value]) => (
                        <option key={key} value={key}>{value.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="config-group">
                    <label>GPU 수</label>
                    <select value={comfyuiConfig.gpuCount} onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, gpuCount: parseInt(e.target.value) })}>
                      <option value="1">1 GPU</option>
                      <option value="2">2 GPU</option>
                      <option value="4">4 GPU</option>
                    </select>
                  </div>
                </div>
                <div className="use-case-description">{COMFYUI_USE_CASES[comfyuiConfig.useCase]?.description}</div>

                {/* Image Model Selection */}
                {comfyuiConfig.useCase === 'image' && (
                  <div className="model-selection-section">
                    <div className="model-category-tabs">
                      {Object.entries(IMAGE_MODEL_CATEGORIES).map(([key, category]) => (
                        <button
                          key={key}
                          className={`model-category-tab ${comfyuiConfig.imageModelCategory === key ? 'active' : ''}`}
                          onClick={() => {
                            const firstModel = category.models[0]?.id || 'sdxl';
                            setComfyuiConfig({ ...comfyuiConfig, imageModelCategory: key, imageModel: firstModel });
                          }}
                        >
                          {category.name}
                        </button>
                      ))}
                    </div>
                    <div className="model-category-description">
                      {IMAGE_MODEL_CATEGORIES[comfyuiConfig.imageModelCategory as keyof typeof IMAGE_MODEL_CATEGORIES]?.description}
                    </div>
                    <div className="model-buttons">
                      {IMAGE_MODEL_CATEGORIES[comfyuiConfig.imageModelCategory as keyof typeof IMAGE_MODEL_CATEGORIES]?.models.map((model) => (
                        <button
                          key={model.id}
                          className={`model-btn ${comfyuiConfig.imageModel === model.id ? 'active' : ''}`}
                          onClick={() => setComfyuiConfig({ ...comfyuiConfig, imageModel: model.id })}
                        >
                          {model.name}
                          <span className="model-vram">{model.vram}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Video Model - WAN 2.2 fixed */}
                {comfyuiConfig.useCase === 'video' && (
                  <div className="model-selection-section">
                    <div className="video-model-info">
                      <div className="video-model-badge">
                        <span className="model-name">WAN 2.2</span>
                        <span className="model-tag">Video Generation</span>
                      </div>
                      <div className="video-model-specs">
                        <span className="spec-item">VRAM: 24GB+</span>
                        <span className="spec-item">고품질 비디오 생성</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="workload-config-row">
                  <div className="config-group">
                    <label>노드 선택 (GPU)</label>
                    <select value={comfyuiConfig.nodeSelector} onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, nodeSelector: e.target.value, gpuIndices: [] })}>
                      <option value="">자동 (스케줄러 결정)</option>
                      {getGpuNodes().map(node => {
                        const gpuCount = node.gpu_capacity || 0;
                        const isEligible = gpuCount >= comfyuiConfig.gpuCount;
                        return (
                          <option key={node.name} value={node.name} disabled={!isEligible}>
                            {node.name} ({gpuCount} GPU){!isEligible ? ' - GPU 부족' : ''}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                  <div className="config-group">
                    <label>메모리</label>
                    <select value={comfyuiConfig.memoryLimit} onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, memoryLimit: e.target.value })}>
                      <option value="8Gi">8 GB</option>
                      <option value="16Gi">16 GB</option>
                      <option value="32Gi">32 GB</option>
                      <option value="64Gi">64 GB</option>
                    </select>
                  </div>
                  <div className="config-group">
                    <label>스토리지</label>
                    <select value={comfyuiConfig.storageSize} onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, storageSize: parseInt(e.target.value) })}>
                      <option value="50">50 GB</option>
                      <option value="100">100 GB</option>
                      <option value="200">200 GB</option>
                      <option value="500">500 GB</option>
                    </select>
                  </div>
                </div>

                {/* GPU Index Selection - 노드 선택 시 또는 GPU 노드가 있을 때 표시 */}
                {(() => {
                  const selectedNode = comfyuiConfig.nodeSelector
                    ? nodeMetrics.find(n => n.name === comfyuiConfig.nodeSelector)
                    : null;
                  const gpuCapacity = selectedNode?.gpu_capacity || 0;
                  const gpuStatusArray = selectedNode?.gpu_status_array || [];
                  const gpuNodes = getGpuNodes();
                  const maxGpuOnAnyNode = Math.max(...gpuNodes.map(n => n.gpu_capacity || 0), 0);
                  const displayGpuCount = comfyuiConfig.nodeSelector ? gpuCapacity : maxGpuOnAnyNode;

                  if (displayGpuCount > 0) {
                    return (
                      <div className="gpu-index-selection">
                        <label>GPU 인덱스 선택 {!comfyuiConfig.nodeSelector && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(노드 선택 시 적용)</span>}</label>
                        <div className="gpu-index-buttons">
                          {[...Array(displayGpuCount)].map((_, idx) => {
                            const isSelected = comfyuiConfig.gpuIndices.includes(idx);
                            const isInUse = comfyuiConfig.nodeSelector && gpuStatusArray[idx] === true;
                            const isDisabled = (!isSelected && comfyuiConfig.gpuIndices.length >= comfyuiConfig.gpuCount) || isInUse;
                            return (
                              <button
                                key={idx}
                                className={`gpu-index-btn ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''} ${isInUse ? 'in-use' : ''}`}
                                onClick={() => {
                                  if (isInUse) return;
                                  if (isSelected) {
                                    setComfyuiConfig({ ...comfyuiConfig, gpuIndices: comfyuiConfig.gpuIndices.filter(i => i !== idx) });
                                  } else if (!isDisabled) {
                                    setComfyuiConfig({ ...comfyuiConfig, gpuIndices: [...comfyuiConfig.gpuIndices, idx].sort((a, b) => a - b) });
                                  }
                                }}
                                disabled={isDisabled}
                                title={isInUse ? `GPU ${idx} (사용 중)` : `GPU ${idx}`}
                              >
                                GPU {idx}
                                {isInUse && <span style={{ marginLeft: 4, color: 'var(--accent-red)' }}>●</span>}
                              </button>
                            );
                          })}
                        </div>
                        <div className="gpu-index-hint">
                          {comfyuiConfig.gpuIndices.length > 0
                            ? `선택됨: GPU ${comfyuiConfig.gpuIndices.join(', ')}`
                            : `${comfyuiConfig.gpuCount}개의 GPU를 선택하세요 (미선택 시 자동 할당)`}
                        </div>
                      </div>
                    );
                  }
                  return null;
                })()}

                <div className="resource-preview">
                  <div className="resource-item">
                    <Zap size={14} />
                    <span>GPU {comfyuiConfig.gpuCount}개</span>
                  </div>
                  {comfyuiConfig.gpuIndices.length > 0 && (
                    <div className="resource-item">
                      <span>인덱스:</span>
                      <span className="value">{comfyuiConfig.gpuIndices.join(', ')}</span>
                    </div>
                  )}
                  <div className="resource-item">
                    <HardDrive size={14} />
                    <span>Storage {comfyuiConfig.storageSize}GB</span>
                  </div>
                  <div className="resource-item">
                    <Package size={14} />
                    <span>
                      {comfyuiConfig.useCase === 'image'
                        ? IMAGE_MODEL_CATEGORIES[comfyuiConfig.imageModelCategory as keyof typeof IMAGE_MODEL_CATEGORIES]?.models.find(m => m.id === comfyuiConfig.imageModel)?.name || comfyuiConfig.imageModel
                        : 'WAN 2.2'}
                    </span>
                  </div>
                </div>

                {/* API Info */}
                <div className="api-info-box">
                  <div className="api-info-header">
                    <Package size={14} />
                    <span>API 연동</span>
                  </div>
                  <div className="api-info-content">
                    <div className="api-endpoint">
                      <span className="label">Endpoint:</span>
                      <code>http://comfyui.14.32.100.220.nip.io/api</code>
                    </div>
                    <div className="api-features">
                      <span className="feature-tag">이미지 생성</span>
                      <span className="feature-tag">동영상 생성</span>
                      <span className="feature-tag">워크플로우 실행</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="workload-controls">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('comfyui', 'start')}
                disabled={actionLoading.comfyui?.loading || workloads.comfyui?.status === 'running'}
              >
                <Play size={16} /> {actionLoading.comfyui?.loading && actionLoading.comfyui?.action === 'start' ? '시작 중...' : '실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('comfyui', 'stop')}
                disabled={actionLoading.comfyui?.loading || workloads.comfyui?.status !== 'running'}
              >
                <Square size={16} /> {actionLoading.comfyui?.loading && actionLoading.comfyui?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>

            {/* Running state - API status */}
            {workloads.comfyui?.status === 'running' && !actionLoading.comfyui?.loading && (
              <div className="api-status-panel">
                <div className="api-status-item">
                  <span className="status-indicator active"></span>
                  <span>API 서버 활성</span>
                </div>
                <div className="api-links">
                  <a href="/comfyui" className="api-link" style={{ background: 'var(--accent-blue)', color: 'white' }}>워크플로우 에디터</a>
                  <a href="http://comfyui.14.32.100.220.nip.io" target="_blank" rel="noopener noreferrer" className="api-link">WebUI 열기</a>
                  <a href="http://comfyui.14.32.100.220.nip.io/api" target="_blank" rel="noopener noreferrer" className="api-link">API Docs</a>
                </div>
              </div>
            )}
          </div>

          {/* Neo4j */}
          <div className="card workload-card">
            <div className="workload-header">
              <div className="workload-info">
                <h3>🕸️ Neo4j</h3>
                <p>그래프 DB / Ontology</p>
              </div>
              <span className={`workload-status ${workloads.neo4j?.status === 'running' ? 'running' : workloads.neo4j?.status === 'stopped' ? 'stopped' : 'not_deployed'}`}>
                {workloads.neo4j?.status === 'running' ? '실행중' : workloads.neo4j?.status === 'stopped' ? '중지됨' : '미배포'}
              </span>
            </div>

            {/* Neo4j Config (when stopped) */}
            {(workloads.neo4j?.status === 'stopped' || workloads.neo4j?.status === 'not_deployed' || !workloads.neo4j?.status) && (
              <div className="workload-config-section">
                <div className="workload-config-row">
                  <div className="config-group" style={{ flex: 2 }}>
                    <label>사용 용도</label>
                    <select value={neo4jConfig.useCase} onChange={(e) => setNeo4jConfig({ ...neo4jConfig, useCase: e.target.value })}>
                      {Object.entries(NEO4J_USE_CASES).map(([key, value]) => (
                        <option key={key} value={key}>{value.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="config-group">
                    <label>Replicas</label>
                    <select value={neo4jConfig.replicas} onChange={(e) => setNeo4jConfig({ ...neo4jConfig, replicas: parseInt(e.target.value) })}>
                      <option value="1">1 (단일)</option>
                      <option value="2">2 (HA)</option>
                      <option value="3">3 (클러스터)</option>
                    </select>
                  </div>
                </div>
                <div className="use-case-description">{NEO4J_USE_CASES[neo4jConfig.useCase]?.description}</div>
                <div className="workload-config-row">
                  <div className="config-group">
                    <label>노드 선택</label>
                    <select value={neo4jConfig.nodeSelector} onChange={(e) => setNeo4jConfig({ ...neo4jConfig, nodeSelector: e.target.value })}>
                      <option value="">자동 (스케줄러 결정)</option>
                      {nodeMetrics.map(node => (
                        <option key={node.name} value={node.name}>{node.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="config-group">
                    <label>메모리</label>
                    <select value={neo4jConfig.memoryLimit} onChange={(e) => setNeo4jConfig({ ...neo4jConfig, memoryLimit: e.target.value })}>
                      <option value="4Gi">4 GB</option>
                      <option value="8Gi">8 GB</option>
                      <option value="16Gi">16 GB</option>
                      <option value="32Gi">32 GB</option>
                    </select>
                  </div>
                  <div className="config-group">
                    <label>스토리지</label>
                    <select value={neo4jConfig.storageSize} onChange={(e) => setNeo4jConfig({ ...neo4jConfig, storageSize: parseInt(e.target.value) })}>
                      <option value="20">20 GB</option>
                      <option value="50">50 GB</option>
                      <option value="100">100 GB</option>
                      <option value="200">200 GB</option>
                    </select>
                  </div>
                </div>
                <div className="resource-preview">
                  <div className="resource-item">
                    <HardDrive size={14} />
                    <span>Storage {neo4jConfig.storageSize}GB</span>
                  </div>
                  <div className="resource-item">
                    <Server size={14} />
                    <span>Replicas {neo4jConfig.replicas}</span>
                  </div>
                </div>

                {/* API Info */}
                <div className="api-info-box">
                  <div className="api-info-header">
                    <Package size={14} />
                    <span>연동 정보</span>
                  </div>
                  <div className="api-info-content">
                    <div className="api-endpoint">
                      <span className="label">Bolt:</span>
                      <code>bolt://neo4j.14.32.100.220.nip.io:7687</code>
                    </div>
                    <div className="api-endpoint">
                      <span className="label">Browser:</span>
                      <code>http://neo4j.14.32.100.220.nip.io</code>
                    </div>
                    <div className="api-features">
                      <span className="feature-tag">Cypher 쿼리</span>
                      <span className="feature-tag">그래프 시각화</span>
                      <span className="feature-tag">관계 추론</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="workload-controls">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('neo4j', 'start')}
                disabled={actionLoading.neo4j?.loading || workloads.neo4j?.status === 'running'}
              >
                <Play size={16} /> {actionLoading.neo4j?.loading && actionLoading.neo4j?.action === 'start' ? '시작 중...' : '실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('neo4j', 'stop')}
                disabled={actionLoading.neo4j?.loading || workloads.neo4j?.status !== 'running'}
              >
                <Square size={16} /> {actionLoading.neo4j?.loading && actionLoading.neo4j?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>

            {/* Running state */}
            {workloads.neo4j?.status === 'running' && !actionLoading.neo4j?.loading && (
              <div className="api-status-panel">
                <div className="api-status-item">
                  <span className="status-indicator active"></span>
                  <span>Neo4j 활성</span>
                </div>
                <div className="api-links">
                  <a href="http://neo4j.14.32.100.220.nip.io" target="_blank" rel="noopener noreferrer" className="api-link">Browser 열기</a>
                </div>
              </div>
            )}
          </div>

          {/* Loki - Logging Stack */}
          <div className="card workload-card">
            <div className="workload-header">
              <div className="workload-info">
                <h3>📋 Logging Stack</h3>
                <p>Loki + Promtail 로그 수집</p>
              </div>
              <span className={`workload-status ${workloads.loki?.status === 'running' ? 'running' : workloads.loki?.status === 'stopped' ? 'stopped' : 'not_deployed'}`}>
                {workloads.loki?.status === 'running' ? '실행중' : workloads.loki?.status === 'stopped' ? '중지됨' : '미배포'}
              </span>
            </div>

            <div className="logging-stack-info">
              <div className="logging-component">
                <div className="component-icon">📥</div>
                <div className="component-details">
                  <div className="component-name">Promtail</div>
                  <div className="component-desc">로그 수집기 (DaemonSet)</div>
                </div>
              </div>
              <div className="logging-arrow">↓</div>
              <div className="logging-component">
                <div className="component-icon">📦</div>
                <div className="component-details">
                  <div className="component-name">Loki</div>
                  <div className="component-desc">로그 저장소 (중앙 집중식)</div>
                </div>
              </div>
            </div>

            {/* API Info (when running) */}
            {workloads.loki?.status === 'running' && (
              <div className="api-info-box">
                <div className="api-info-header">
                  <Package size={14} />
                  <span>연동 정보</span>
                </div>
                <div className="api-info-content">
                  <div className="api-endpoint">
                    <span className="label">Loki API:</span>
                    <code>http://loki.14.32.100.220.nip.io:3100</code>
                  </div>
                  <div className="api-features">
                    <span className="feature-tag">LogQL 쿼리</span>
                    <span className="feature-tag">Grafana 연동</span>
                    <span className="feature-tag">7일 보관</span>
                  </div>
                </div>
              </div>
            )}

            <div className="workload-controls">
              <button
                className="btn btn-success"
                onClick={() => {
                  handleWorkloadAction('loki', 'start');
                  handleWorkloadAction('promtail', 'start');
                }}
                disabled={actionLoading.loki?.loading || workloads.loki?.status === 'running'}
              >
                <Play size={16} /> {actionLoading.loki?.loading && actionLoading.loki?.action === 'start' ? '시작 중...' : '전체 실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => {
                  handleWorkloadAction('loki', 'stop');
                  handleWorkloadAction('promtail', 'stop');
                }}
                disabled={actionLoading.loki?.loading || workloads.loki?.status !== 'running'}
              >
                <Square size={16} /> {actionLoading.loki?.loading && actionLoading.loki?.action === 'stop' ? '중지 중...' : '전체 중지'}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default OverviewPage;
