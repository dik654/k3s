import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Server, Box, ChevronDown, ChevronRight, Zap, Thermometer, Info, Folder } from 'lucide-react';
import type { PodsData, GpuStatus, GpuDetailed, NodeMetrics } from '@/types';

type TabType = 'pods' | 'gpu' | 'storage' | 'cluster';

// Pod Status Icon
const PodStatusIcon = ({ status }: { status: string }) => {
  const statusLower = status.toLowerCase();
  if (statusLower === 'running') return <span className="status-dot healthy" />;
  if (statusLower === 'pending') return <span className="status-dot degraded" />;
  if (statusLower === 'failed' || statusLower === 'error') return <span className="status-dot error" />;
  return <span className="status-dot" />;
};

// GPU Card Component
const GpuCard = ({ gpu }: { gpu: any }) => {
  const memPercent = gpu.memory_total > 0 ? (gpu.memory_used / gpu.memory_total) * 100 : 0;
  const powerPercent = gpu.power_limit > 0 ? (gpu.power_draw / gpu.power_limit) * 100 : 0;
  const tempClass = gpu.temperature >= 80 ? 'hot' : gpu.temperature >= 60 ? 'warm' : 'normal';

  return (
    <div className="nvtop-gpu-item">
      <div className="nvtop-gpu-header">
        <div className="nvtop-gpu-name">
          [{gpu.index}] {gpu.name} {gpu.node && <span style={{ color: '#888', fontSize: 11 }}>@ {gpu.node}</span>}
        </div>
        <div className={`nvtop-gpu-temp ${tempClass}`}>
          <Thermometer size={14} />
          {gpu.temperature}°C
        </div>
      </div>
      <div className="nvtop-metrics">
        <div className="nvtop-metric">
          <span className="nvtop-metric-label">GPU 사용률</span>
          <div className="nvtop-metric-bar">
            <div className="nvtop-metric-fill util" style={{ width: `${gpu.utilization}%` }} />
          </div>
          <div className="nvtop-metric-value">
            <span>{gpu.utilization}%</span>
          </div>
        </div>
        <div className="nvtop-metric">
          <span className="nvtop-metric-label">VRAM</span>
          <div className="nvtop-metric-bar">
            <div className="nvtop-metric-fill memory" style={{ width: `${memPercent}%` }} />
          </div>
          <div className="nvtop-metric-value">
            <span>{(gpu.memory_used / 1024).toFixed(1)}G / {(gpu.memory_total / 1024).toFixed(0)}G</span>
            <span>{memPercent.toFixed(0)}%</span>
          </div>
        </div>
        <div className="nvtop-metric">
          <span className="nvtop-metric-label">전력</span>
          <div className="nvtop-metric-bar">
            <div className="nvtop-metric-fill power" style={{ width: `${powerPercent}%` }} />
          </div>
          <div className="nvtop-metric-value">
            <span>{gpu.power_draw?.toFixed(0)}W / {gpu.power_limit?.toFixed(0)}W</span>
            <span>{powerPercent.toFixed(0)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export function InfrastructurePage() {
  const [activeTab, setActiveTab] = useState<TabType>('pods');
  const [loading, setLoading] = useState(true);
  const [pods, setPods] = useState<PodsData>({ total: 0, by_namespace: {} });
  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null);
  const [gpuDetailed, setGpuDetailed] = useState<GpuDetailed | null>(null);
  const [nodeMetrics, setNodeMetrics] = useState<NodeMetrics[]>([]);
  const [expandedNamespaces, setExpandedNamespaces] = useState<Record<string, boolean>>({});
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});

  const fetchData = useCallback(async () => {
    try {
      const [podsRes, gpuStatusRes, metricsRes] = await Promise.all([
        axios.get('/api/pods'),
        axios.get('/api/gpu/status'),
        axios.get('/api/nodes/metrics'),
      ]);
      setPods(podsRes.data || { total: 0, by_namespace: {} });
      setGpuStatus(gpuStatusRes.data);
      const metricsData = metricsRes.data?.nodes || metricsRes.data || [];
      setNodeMetrics(Array.isArray(metricsData) ? metricsData : []);

      if (gpuStatusRes.data?.total_gpus > 0) {
        try {
          const gpuDetailedRes = await axios.get('/api/gpu/detailed');
          setGpuDetailed(gpuDetailedRes.data);
        } catch {}
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const toggleNamespace = (namespace: string) => {
    setExpandedNamespaces(prev => ({ ...prev, [namespace]: !prev[namespace] }));
  };

  const toggleNode = (nodeName: string) => {
    setExpandedNodes(prev => ({ ...prev, [nodeName]: !prev[nodeName] }));
  };

  // Group GPUs by node
  const gpusByNode: Record<string, any[]> = {};
  if (gpuDetailed?.available && gpuDetailed.gpus) {
    gpuDetailed.gpus.forEach(gpu => {
      const nodeName = gpu.node || 'unknown';
      if (!gpusByNode[nodeName]) gpusByNode[nodeName] = [];
      gpusByNode[nodeName].push(gpu);
    });
  }
  if (gpuStatus?.gpu_nodes) {
    gpuStatus.gpu_nodes.forEach(node => {
      if (!gpusByNode[node.node]) gpusByNode[node.node] = [];
    });
  }

  const tabs = [
    { id: 'pods' as const, label: `Pods (${pods.total})` },
    { id: 'gpu' as const, label: 'GPU' },
    { id: 'storage' as const, label: 'Storage' },
    { id: 'cluster' as const, label: 'Cluster' },
  ];

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <div className="dashboard">
      <section className="section">
        <div className="section-header">
          <h2 className="section-title">인프라</h2>
        </div>

        {/* Tabs */}
        <div className="tab-buttons" style={{ marginBottom: 24 }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Pods Tab */}
        {activeTab === 'pods' && (
          <div className="card">
            <div className="pods-list">
              {Object.entries(pods.by_namespace || {}).map(([namespace, nsPods]) => (
                <div key={namespace} className="namespace-group">
                  <div className="namespace-header" onClick={() => toggleNamespace(namespace)}>
                    {expandedNamespaces[namespace] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                    <span className="namespace-name">{namespace}</span>
                    <span className="namespace-count">{(nsPods as any[]).length}개</span>
                  </div>
                  {expandedNamespaces[namespace] && (
                    <div className="namespace-pods">
                      {(nsPods as any[]).map((pod) => (
                        <div key={`${namespace}-${pod.name}`} className={`pod-item ${pod.status.toLowerCase()}`}>
                          <div className="pod-main">
                            <PodStatusIcon status={pod.status} />
                            <span className="pod-name">{pod.name}</span>
                            <span className={`pod-status ${pod.status.toLowerCase()}`}>
                              {pod.status === 'Pending' ? '준비 중' :
                               pod.status === 'Running' ? '실행중' :
                               pod.status === 'Failed' ? '실패' :
                               pod.status === 'Succeeded' ? '완료' : pod.status}
                            </span>
                          </div>
                          <div className="pod-details">
                            <span className="pod-detail">
                              <Server size={12} /> {pod.node || '-'}
                            </span>
                            <span className="pod-detail">IP: {pod.ip || '-'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* GPU Tab */}
        {activeTab === 'gpu' && (
          <div>
            {Object.keys(gpusByNode).length > 0 ? (
              <div className="gpu-nodes-container">
                {Object.entries(gpusByNode).map(([nodeName, gpus]) => {
                  const nodeInfo = gpuStatus?.gpu_nodes?.find(n => n.node === nodeName);
                  const metric = nodeMetrics?.find(m => m.name === nodeName);
                  const isExpanded = expandedNodes[nodeName] !== false;
                  const hasDetailedMetrics = gpus.length > 0 && gpus[0].utilization !== undefined;

                  return (
                    <div key={nodeName} className="gpu-node-section">
                      <div className="gpu-node-header" onClick={() => toggleNode(nodeName)}>
                        <div className="gpu-node-info">
                          <Server size={18} />
                          <span className="gpu-node-name">{nodeName}</span>
                          <span className="gpu-node-type">{nodeInfo?.gpu_type || 'NVIDIA GPU'}</span>
                          <span className={`status-badge small ${nodeInfo?.status === 'ready' ? 'running' : 'stopped'}`}>
                            {nodeInfo?.status || 'unknown'}
                          </span>
                        </div>
                        <div className="gpu-node-summary">
                          <span className="gpu-count">
                            <Zap size={14} />
                            {gpus.length || metric?.gpu_capacity || 0}개 GPU
                          </span>
                          <ChevronDown size={16} className={`chevron ${isExpanded ? 'expanded' : ''}`} />
                        </div>
                      </div>
                      {isExpanded && (
                        <div className="gpu-node-content">
                          {hasDetailedMetrics ? (
                            <div className="nvtop-container embedded">
                              <div className="nvtop-header">
                                <div className="nvtop-title">
                                  <Zap size={14} /> 실시간 메트릭
                                </div>
                              </div>
                              <div className="nvtop-gpu-list">
                                {gpus.map((gpu) => (
                                  <GpuCard key={gpu.index} gpu={gpu} />
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div className="gpu-node-basic">
                              <div className="gpu-metrics-notice">
                                <Info size={14} />
                                <span>실시간 메트릭 조회를 위해서는 GPU Metrics Collector 설치가 필요합니다</span>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (gpuStatus?.total_gpus || 0) > 0 ? (
              <div className="card">
                <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                  <Zap size={48} color="#76b947" style={{ marginBottom: 12 }} />
                  <p>{gpuStatus?.total_gpus}개의 GPU가 클러스터에 등록되어 있습니다</p>
                  <p style={{ fontSize: 11, marginTop: 8 }}>실시간 메트릭 조회를 위해서는 GPU Metrics Collector 설치가 필요합니다</p>
                </div>
              </div>
            ) : (
              <div className="card">
                <div className="no-data">
                  <Zap size={48} color="var(--text-muted)" />
                  <p>클러스터에 GPU 노드가 없습니다</p>
                  <p className="hint">GPU가 있는 노드를 클러스터에 추가하세요</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Storage Tab */}
        {activeTab === 'storage' && (
          <div className="card">
            <div className="no-data">
              <Folder size={48} color="var(--text-muted)" />
              <p>스토리지 관리 - 개발 중</p>
            </div>
          </div>
        )}

        {/* Cluster Tab */}
        {activeTab === 'cluster' && (
          <div className="card">
            <div className="no-data">
              <Server size={48} color="var(--text-muted)" />
              <p>클러스터 관리 - 개발 중</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default InfrastructurePage;
