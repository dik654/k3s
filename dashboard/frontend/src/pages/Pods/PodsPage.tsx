import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { ChevronDown, ChevronRight, Server, RefreshCw, Box, Settings, X, Cpu, MemoryStick } from 'lucide-react';

interface PodContainer {
  name: string;
  image: string;
  cpu_request?: string;
  cpu_limit?: string;
  memory_request?: string;
  memory_limit?: string;
  ports?: { containerPort: number; protocol: string }[];
}

interface Pod {
  name: string;
  namespace?: string;
  status: string;
  node?: string;
  ip?: string;
  cpu_usage?: number;
  memory_usage?: number;
  containers?: PodContainer[];
  labels?: Record<string, string>;
  restarts?: number;
  age?: string;
}

interface PodsData {
  total: number;
  by_namespace: Record<string, Pod[]>;
}

// Pod Status Icon
const PodStatusIcon = ({ status }: { status: string }) => {
  const statusLower = status.toLowerCase();
  if (statusLower === 'running') return <span className="status-dot healthy" />;
  if (statusLower === 'pending') return <span className="status-dot degraded" />;
  if (statusLower === 'failed' || statusLower === 'error') return <span className="status-dot error" />;
  return <span className="status-dot" />;
};

// Pod Config Modal
const PodConfigModal = ({ pod, onClose }: { pod: Pod; onClose: () => void }) => {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal pod-config-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            <Box size={18} />
            {pod.name}
          </h3>
          <button className="btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          {/* Basic Info */}
          <div className="config-section">
            <h4>기본 정보</h4>
            <div className="config-grid">
              <div className="config-item">
                <span className="config-label">상태</span>
                <span className={`config-value status-${pod.status.toLowerCase()}`}>{pod.status}</span>
              </div>
              <div className="config-item">
                <span className="config-label">노드</span>
                <span className="config-value">{pod.node || '-'}</span>
              </div>
              <div className="config-item">
                <span className="config-label">IP</span>
                <span className="config-value">{pod.ip || '-'}</span>
              </div>
              <div className="config-item">
                <span className="config-label">재시작</span>
                <span className="config-value">{pod.restarts ?? 0}회</span>
              </div>
              <div className="config-item">
                <span className="config-label">Age</span>
                <span className="config-value">{pod.age || '-'}</span>
              </div>
            </div>
          </div>

          {/* Resource Usage */}
          {(pod.cpu_usage !== undefined || pod.memory_usage !== undefined) && (
            <div className="config-section">
              <h4>리소스 사용량</h4>
              <div className="resource-bars">
                {pod.cpu_usage !== undefined && (
                  <div className="resource-bar-item">
                    <div className="resource-bar-label">
                      <Cpu size={14} />
                      <span>CPU</span>
                      <span className="resource-bar-value">{pod.cpu_usage.toFixed(0)}m</span>
                    </div>
                  </div>
                )}
                {pod.memory_usage !== undefined && (
                  <div className="resource-bar-item">
                    <div className="resource-bar-label">
                      <MemoryStick size={14} />
                      <span>Memory</span>
                      <span className="resource-bar-value">{pod.memory_usage}Mi</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Containers */}
          {pod.containers && pod.containers.length > 0 && (
            <div className="config-section">
              <h4>컨테이너 ({pod.containers.length})</h4>
              {pod.containers.map((container, idx) => (
                <div key={idx} className="container-info">
                  <div className="container-header">
                    <span className="container-name">{container.name}</span>
                  </div>
                  <div className="container-details">
                    <div className="container-image">
                      <span className="detail-label">이미지:</span>
                      <code>{container.image}</code>
                    </div>
                    {(container.cpu_request || container.cpu_limit || container.memory_request || container.memory_limit) && (
                      <div className="container-resources">
                        <span className="detail-label">리소스:</span>
                        <div className="resource-specs">
                          {container.cpu_request && <span>CPU Req: {container.cpu_request}</span>}
                          {container.cpu_limit && <span>CPU Lim: {container.cpu_limit}</span>}
                          {container.memory_request && <span>Mem Req: {container.memory_request}</span>}
                          {container.memory_limit && <span>Mem Lim: {container.memory_limit}</span>}
                        </div>
                      </div>
                    )}
                    {container.ports && container.ports.length > 0 && (
                      <div className="container-ports">
                        <span className="detail-label">포트:</span>
                        <div className="port-list">
                          {container.ports.map((port, pIdx) => (
                            <span key={pIdx} className="port-badge">
                              {port.containerPort}/{port.protocol}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Labels */}
          {pod.labels && Object.keys(pod.labels).length > 0 && (
            <div className="config-section">
              <h4>Labels</h4>
              <div className="labels-list">
                {Object.entries(pod.labels).map(([key, value]) => (
                  <span key={key} className="label-tag">
                    {key}: {value}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export function PodsPage() {
  const [pods, setPods] = useState<PodsData>({ total: 0, by_namespace: {} });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});
  const [expandedNamespaces, setExpandedNamespaces] = useState<Record<string, boolean>>({});
  const [viewMode, setViewMode] = useState<'node' | 'namespace'>('node');
  const [selectedPod, setSelectedPod] = useState<Pod | null>(null);

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const res = await axios.get('/api/pods');
      setPods(res.data || { total: 0, by_namespace: {} });
    } catch (error) {
      console.error('Failed to fetch pods:', error);
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

  const toggleNode = (node: string) => {
    setExpandedNodes(prev => ({ ...prev, [node]: !prev[node] }));
  };

  const toggleNamespace = (ns: string) => {
    setExpandedNamespaces(prev => ({ ...prev, [ns]: !prev[ns] }));
  };

  // Group pods by node
  const getPodsByNode = () => {
    const byNode: Record<string, Pod[]> = {};
    Object.entries(pods.by_namespace || {}).forEach(([namespace, nsPods]) => {
      nsPods.forEach(pod => {
        const nodeName = pod.node || 'Unscheduled';
        if (!byNode[nodeName]) byNode[nodeName] = [];
        byNode[nodeName].push({ ...pod, namespace });
      });
    });
    return byNode;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '50vh' }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  const podsByNode = getPodsByNode();

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">
          <Box size={20} style={{ marginRight: 8 }} />
          Pod 목록 ({pods.total}개)
        </h2>
        <div className="view-toggle">
          <button
            className={`toggle-btn ${viewMode === 'node' ? 'active' : ''}`}
            onClick={() => setViewMode('node')}
          >
            <Server size={14} />
            노드별
          </button>
          <button
            className={`toggle-btn ${viewMode === 'namespace' ? 'active' : ''}`}
            onClick={() => setViewMode('namespace')}
          >
            <Box size={14} />
            네임스페이스별
          </button>
        </div>
        <button
          className={`btn-icon ${refreshing ? 'spinning' : ''}`}
          onClick={() => fetchData(true)}
        >
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="card">
        <div className="pods-list">
          {viewMode === 'node' ? (
            // View by Node
            Object.keys(podsByNode).length === 0 ? (
              <div className="no-data">
                <Box size={48} color="var(--text-muted)" />
                <p>Pod가 없습니다</p>
              </div>
            ) : (
              Object.entries(podsByNode)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([nodeName, nodePods]) => (
                  <div key={nodeName} className="node-group">
                    <div className="node-header" onClick={() => toggleNode(nodeName)}>
                      {expandedNodes[nodeName] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      <Server size={16} className="node-icon" />
                      <span className="node-name">{nodeName}</span>
                      <span className="node-count">{nodePods.length}개</span>
                    </div>
                    {expandedNodes[nodeName] && (
                      <div className="node-pods">
                        {nodePods.map((pod) => (
                          <div
                            key={`${pod.namespace}-${pod.name}`}
                            className={`pod-item ${pod.status.toLowerCase()}`}
                            onClick={() => setSelectedPod(pod)}
                          >
                            <div className="pod-main">
                              <PodStatusIcon status={pod.status} />
                              <span className="pod-namespace">{pod.namespace}/</span>
                              <span className="pod-name">{pod.name}</span>
                              <span className={`pod-status ${pod.status.toLowerCase()}`}>
                                {pod.status === 'Pending' ? '준비 중' :
                                 pod.status === 'Running' ? '실행중' :
                                 pod.status === 'Failed' ? '실패' :
                                 pod.status === 'Succeeded' ? '완료' : pod.status}
                              </span>
                              <button className="pod-config-btn" onClick={(e) => { e.stopPropagation(); setSelectedPod(pod); }}>
                                <Settings size={14} />
                              </button>
                            </div>
                            {pod.status === 'Pending' ? (
                              <div className="pod-pending-info">
                                <div className="pending-animation">
                                  <div className="pending-dot"></div>
                                  <div className="pending-dot"></div>
                                  <div className="pending-dot"></div>
                                </div>
                                <span>컨테이너 이미지 다운로드 또는 스케줄링 대기 중...</span>
                              </div>
                            ) : (
                              <div className="pod-details">
                                <span className="pod-detail">IP: {pod.ip || '-'}</span>
                                {pod.cpu_usage !== undefined && pod.cpu_usage > 0 && (
                                  <span className="pod-detail">CPU: {pod.cpu_usage.toFixed(0)}m</span>
                                )}
                                {pod.memory_usage !== undefined && pod.memory_usage > 0 && (
                                  <span className="pod-detail">Mem: {pod.memory_usage}Mi</span>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
            )
          ) : (
            // View by Namespace
            Object.keys(pods.by_namespace || {}).length === 0 ? (
              <div className="no-data">
                <Box size={48} color="var(--text-muted)" />
                <p>Pod가 없습니다</p>
              </div>
            ) : (
              Object.entries(pods.by_namespace || {}).map(([namespace, nsPods]) => (
                <div key={namespace} className="namespace-group">
                  <div className="namespace-header" onClick={() => toggleNamespace(namespace)}>
                    {expandedNamespaces[namespace] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                    <span className="namespace-name">{namespace}</span>
                    <span className="namespace-count">{nsPods.length}개</span>
                  </div>
                  {expandedNamespaces[namespace] && (
                    <div className="namespace-pods">
                      {nsPods.map((pod) => (
                        <div
                          key={`${namespace}-${pod.name}`}
                          className={`pod-item ${pod.status.toLowerCase()}`}
                          onClick={() => setSelectedPod({ ...pod, namespace })}
                        >
                          <div className="pod-main">
                            <PodStatusIcon status={pod.status} />
                            <span className="pod-name">{pod.name}</span>
                            <span className={`pod-status ${pod.status.toLowerCase()}`}>
                              {pod.status === 'Pending' ? '준비 중' :
                               pod.status === 'Running' ? '실행중' :
                               pod.status === 'Failed' ? '실패' :
                               pod.status === 'Succeeded' ? '완료' : pod.status}
                            </span>
                            <button className="pod-config-btn" onClick={(e) => { e.stopPropagation(); setSelectedPod({ ...pod, namespace }); }}>
                              <Settings size={14} />
                            </button>
                          </div>
                          {pod.status === 'Pending' ? (
                            <div className="pod-pending-info">
                              <div className="pending-animation">
                                <div className="pending-dot"></div>
                                <div className="pending-dot"></div>
                                <div className="pending-dot"></div>
                              </div>
                              <span>컨테이너 이미지 다운로드 또는 스케줄링 대기 중...</span>
                            </div>
                          ) : (
                            <div className="pod-details">
                              <span className="pod-detail">
                                <Server size={12} /> {pod.node || '-'}
                              </span>
                              <span className="pod-detail">IP: {pod.ip || '-'}</span>
                              {pod.cpu_usage !== undefined && pod.cpu_usage > 0 && (
                                <span className="pod-detail">CPU: {pod.cpu_usage.toFixed(0)}m</span>
                              )}
                              {pod.memory_usage !== undefined && pod.memory_usage > 0 && (
                                <span className="pod-detail">Mem: {pod.memory_usage}Mi</span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )
          )}
        </div>
      </div>

      {/* Pod Config Modal */}
      {selectedPod && (
        <PodConfigModal pod={selectedPod} onClose={() => setSelectedPod(null)} />
      )}
    </section>
  );
}

export default PodsPage;
