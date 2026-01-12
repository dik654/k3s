import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { StorageAdvancedTabs, ObjectTagsManager } from './StorageAdvanced';
import MermaidChart from './MermaidChart';
import { KnowledgeGraphViewer, KnowledgeGraph3D, NodeDetailPanel, EmbeddingVisualization } from './components/knowledge';
import { WorkflowList } from './pages/WorkflowList';
import { WorkflowEditor } from './pages/WorkflowEditor';
import {
  Server,
  Cpu,
  HardDrive,
  Database,
  Play,
  Square,
  RefreshCw,
  Layers,
  Box,
  Zap,
  Cloud,
  Plus,
  Minus,
  Thermometer,
  Activity,
  MemoryStick,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Circle,
  AlertCircle,
  CheckCircle,
  Clock,
  Folder,
  FolderPlus,
  File,
  Upload,
  Download,
  Trash2,
  ArrowLeft,
  Search,
  MoreVertical,
  X,
  Archive,
  BarChart3,
  Settings,
  PlayCircle,
  Loader2,
  TrendingUp,
  Timer,
  Target,
  Copy,
  Edit3,
  Info,
  Tag,
  Link2,
  Shield,
  Lock,
  Eye,
  ExternalLink,
  AlertTriangle,
  RotateCcw,
  Crown,
  PauseCircle,
  ArrowRightLeft,
  Package,
  MonitorDot,
  Bell,
  FileText,
  BookOpen,
  Brain,
  GitBranch,
  Workflow,
  Image,
  Film,
  List,
  XCircle,
  Globe,
  FileType,
  Scissors,
  Sparkles,
  Grid2X2,
  Share2
} from 'lucide-react';

const API_BASE = '/api';

// 진행률 바 컴포넌트
const ProgressBar = ({ value, max, color = 'blue', showLabel = true, height = 8 }) => {
  const percent = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const colorClass = {
    blue: 'var(--accent-blue)',
    green: 'var(--accent-green)',
    red: 'var(--accent-red)',
    yellow: 'var(--accent-yellow)',
    purple: 'var(--accent-purple)'
  }[color] || color;

  // 색상 자동 변경 (사용률에 따라)
  let barColor = colorClass;
  if (color === 'auto') {
    if (percent >= 90) barColor = 'var(--accent-red)';
    else if (percent >= 70) barColor = 'var(--accent-yellow)';
    else barColor = 'var(--accent-green)';
  }

  return (
    <div className="progress-container">
      <div className="progress-bar" style={{ height }}>
        <div
          className="progress-fill"
          style={{ width: `${percent}%`, background: barColor }}
        />
      </div>
      {showLabel && <span className="progress-label">{percent.toFixed(1)}%</span>}
    </div>
  );
};

// GPU 카드 컴포넌트 (nvtop 스타일)
const GpuCard = ({ gpu }) => {
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
            <span>{gpu.power_draw.toFixed(0)}W / {gpu.power_limit.toFixed(0)}W</span>
            <span>{powerPercent.toFixed(0)}%</span>
          </div>
        </div>

        <div className="nvtop-metric">
          <span className="nvtop-metric-label">상태</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
            <span className={`status-dot ${gpu.status === 'available' ? 'healthy' : 'error'}`}></span>
            <span style={{ fontSize: 11, color: gpu.status === 'available' ? '#22c55e' : '#ef4444' }}>
              {gpu.status === 'available' ? 'Available' : gpu.status}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

// GPU 모니터링 섹션 컴포넌트 (노드별 확장 가능)
const GpuMonitorSection = ({ gpuStatus, gpuDetailed, nodeMetrics }) => {
  const [expandedNodes, setExpandedNodes] = useState({});

  // 노드별 GPU 그룹화
  const gpusByNode = {};
  if (gpuDetailed?.available && gpuDetailed.gpus) {
    gpuDetailed.gpus.forEach(gpu => {
      const nodeName = gpu.node || 'unknown';
      if (!gpusByNode[nodeName]) {
        gpusByNode[nodeName] = [];
      }
      gpusByNode[nodeName].push(gpu);
    });
  }

  // gpuStatus에서 노드 정보 추가 (gpuDetailed에 없는 노드도 표시)
  if (gpuStatus?.gpu_nodes) {
    gpuStatus.gpu_nodes.forEach(node => {
      if (!gpusByNode[node.node]) {
        gpusByNode[node.node] = [];
      }
    });
  }

  const nodeNames = Object.keys(gpusByNode);
  const totalGpus = gpuStatus?.total_gpus || Object.values(gpusByNode).reduce((acc, gpus) => acc + gpus.length, 0);

  const toggleNode = (nodeName) => {
    setExpandedNodes(prev => ({
      ...prev,
      [nodeName]: !prev[nodeName]
    }));
  };

  const expandAll = () => {
    const allExpanded = {};
    nodeNames.forEach(name => { allExpanded[name] = true; });
    setExpandedNodes(allExpanded);
  };

  const collapseAll = () => {
    setExpandedNodes({});
  };

  // 노드 정보 가져오기
  const getNodeInfo = (nodeName) => {
    const nodeData = gpuStatus?.gpu_nodes?.find(n => n.node === nodeName);
    const metric = nodeMetrics?.find(m => m.name === nodeName);
    return {
      gpuType: nodeData?.gpu_type || 'NVIDIA GPU',
      status: nodeData?.status || 'unknown',
      gpuCapacity: metric?.gpu_capacity || nodeData?.gpu_count || gpusByNode[nodeName]?.length || 0,
      gpuUsed: metric?.gpu_used || 0
    };
  };

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">GPU 모니터링 (nvtop 스타일)</h2>
        <div className="gpu-summary">
          <span>총 {totalGpus}개 GPU</span>
          {nodeNames.length > 1 && (
            <span style={{ marginLeft: 12 }}>({nodeNames.length}개 노드)</span>
          )}
        </div>
      </div>

      {nodeNames.length > 0 ? (
        <div className="gpu-nodes-container">
          {/* 전체 확장/축소 버튼 */}
          {nodeNames.length > 1 && (
            <div className="gpu-expand-controls">
              <button className="btn-text" onClick={expandAll}>
                <ChevronDown size={14} /> 모두 펼치기
              </button>
              <button className="btn-text" onClick={collapseAll}>
                <ChevronUp size={14} /> 모두 접기
              </button>
            </div>
          )}

          {/* 노드별 GPU 목록 */}
          {nodeNames.map(nodeName => {
            const nodeInfo = getNodeInfo(nodeName);
            const gpus = gpusByNode[nodeName];
            const isExpanded = expandedNodes[nodeName] !== false; // 기본값 true
            const hasDetailedMetrics = gpus.length > 0 && gpus[0].utilization !== undefined;

            return (
              <div key={nodeName} className="gpu-node-section">
                <div
                  className="gpu-node-header"
                  onClick={() => toggleNode(nodeName)}
                >
                  <div className="gpu-node-info">
                    <Server size={18} />
                    <span className="gpu-node-name">{nodeName}</span>
                    <span className="gpu-node-type">{nodeInfo.gpuType}</span>
                    <span className={`status-badge small ${nodeInfo.status === 'ready' ? 'running' : 'stopped'}`}>
                      {nodeInfo.status}
                    </span>
                  </div>
                  <div className="gpu-node-summary">
                    <span className="gpu-count">
                      <Zap size={14} />
                      {gpus.length > 0 ? gpus.length : nodeInfo.gpuCapacity}개 GPU
                    </span>
                    <span className="gpu-usage">
                      {nodeInfo.gpuUsed} / {nodeInfo.gpuCapacity} 사용 중
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
                            <Zap size={14} />
                            실시간 메트릭
                          </div>
                          <span style={{ fontSize: 11, color: '#888' }}>
                            {new Date().toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="nvtop-gpu-list">
                          {gpus.map((gpu) => (
                            <GpuCard key={gpu.index} gpu={gpu} />
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="gpu-node-basic">
                        <div className="gpu-meter">
                          <span className="gpu-meter-label">GPU 할당</span>
                          <div className="gpu-meter-bar">
                            {[...Array(nodeInfo.gpuCapacity)].map((_, i) => (
                              <div
                                key={i}
                                className={`gpu-meter-slot ${i < nodeInfo.gpuUsed ? 'used' : ''}`}
                                title={i < nodeInfo.gpuUsed ? `GPU ${i}: 사용 중` : `GPU ${i}: 사용 가능`}
                              />
                            ))}
                          </div>
                          <span className="gpu-meter-value">{nodeInfo.gpuUsed} / {nodeInfo.gpuCapacity}</span>
                        </div>
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
        <div className="nvtop-container">
          <div className="nvtop-header">
            <div className="nvtop-title">
              <Zap size={16} />
              NVIDIA GPU Monitor
            </div>
          </div>
          <div style={{ padding: 24, textAlign: 'center', color: '#888' }}>
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
    </section>
  );
};

// Pods 목록 섹션 컴포넌트 (노드별/네임스페이스별 뷰 전환)
const PodsListSection = ({ pods, nodes, expandedNamespaces, toggleNamespace }) => {
  const [viewMode, setViewMode] = useState('namespace'); // 'namespace' or 'node'
  const [expandedNodes, setExpandedNodes] = useState({});

  // 노드별 pods 그룹화
  const podsByNode = {};
  Object.entries(pods.by_namespace || {}).forEach(([namespace, nsPods]) => {
    nsPods.forEach(pod => {
      const nodeName = pod.node || 'Unscheduled';
      if (!podsByNode[nodeName]) {
        podsByNode[nodeName] = [];
      }
      podsByNode[nodeName].push({ ...pod, namespace });
    });
  });

  const toggleNode = (nodeName) => {
    setExpandedNodes(prev => ({
      ...prev,
      [nodeName]: !prev[nodeName]
    }));
  };

  // 노드 정보 가져오기
  const getNodeInfo = (nodeName) => {
    const node = nodes?.find(n => n.name === nodeName);
    return {
      role: node?.role || 'worker',
      status: node?.status || 'unknown'
    };
  };

  // Pod 상태별 카운트
  const getPodStatusCounts = (podList) => {
    return podList.reduce((acc, pod) => {
      const status = pod.status.toLowerCase();
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    }, {});
  };

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">Pod 목록 ({pods.total}개)</h2>
        <div className="view-mode-toggle">
          <button
            className={`view-btn ${viewMode === 'namespace' ? 'active' : ''}`}
            onClick={() => setViewMode('namespace')}
          >
            <Folder size={14} /> 네임스페이스별
          </button>
          <button
            className={`view-btn ${viewMode === 'node' ? 'active' : ''}`}
            onClick={() => setViewMode('node')}
          >
            <Server size={14} /> 노드별
          </button>
        </div>
      </div>

      {/* 네임스페이스별 뷰 */}
      {viewMode === 'namespace' && (
        <div className="card">
          <div className="pods-list">
            {Object.entries(pods.by_namespace || {}).map(([namespace, nsPods]) => (
              <div key={namespace} className="namespace-group">
                <div
                  className="namespace-header"
                  onClick={() => toggleNamespace(namespace)}
                >
                  {expandedNamespaces[namespace] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                  <span className="namespace-name">{namespace}</span>
                  <span className="namespace-count">{nsPods.length}개</span>
                </div>
                {expandedNamespaces[namespace] && (
                  <div className="namespace-pods">
                    {nsPods.map((pod) => (
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
                            <span className="pod-detail">
                              IP: {pod.ip || '-'}
                            </span>
                            {pod.cpu_usage > 0 && (
                              <span className="pod-detail">
                                CPU: {pod.cpu_usage.toFixed(0)}m
                              </span>
                            )}
                            {pod.memory_usage > 0 && (
                              <span className="pod-detail">
                                Mem: {pod.memory_usage}Mi
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 노드별 뷰 */}
      {viewMode === 'node' && (
        <div className="pods-by-node-container">
          {Object.entries(podsByNode).map(([nodeName, nodePods]) => {
            const nodeInfo = getNodeInfo(nodeName);
            const statusCounts = getPodStatusCounts(nodePods);
            const isExpanded = expandedNodes[nodeName] !== false; // 기본값 true

            return (
              <div key={nodeName} className="pods-node-section">
                <div
                  className="pods-node-header"
                  onClick={() => toggleNode(nodeName)}
                >
                  <div className="pods-node-info">
                    <Server size={16} />
                    <span className="pods-node-name">{nodeName}</span>
                    {nodeName !== 'Unscheduled' && (
                      <span className="pods-node-role">{nodeInfo.role}</span>
                    )}
                  </div>
                  <div className="pods-node-summary">
                    <span className="pods-count">{nodePods.length}개 Pod</span>
                    <div className="pods-status-summary">
                      {statusCounts.running > 0 && (
                        <>
                          <span className="status-dot running"></span>
                          <span>{statusCounts.running}</span>
                        </>
                      )}
                      {statusCounts.pending > 0 && (
                        <>
                          <span className="status-dot pending"></span>
                          <span>{statusCounts.pending}</span>
                        </>
                      )}
                      {(statusCounts.failed || statusCounts.error) > 0 && (
                        <>
                          <span className="status-dot failed"></span>
                          <span>{(statusCounts.failed || 0) + (statusCounts.error || 0)}</span>
                        </>
                      )}
                    </div>
                    <ChevronDown size={16} className={`chevron ${isExpanded ? 'expanded' : ''}`} />
                  </div>
                </div>

                {isExpanded && (
                  <div className="pods-node-content">
                    <div className="pods-node-list">
                      {nodePods.map((pod, idx) => (
                        <div key={`${pod.namespace}-${pod.name}-${idx}`} className="pod-item">
                          <div className="pod-info">
                            <PodStatusIcon status={pod.status} />
                            <span className="pod-name">{pod.name}</span>
                            <span className="pod-namespace">{pod.namespace}</span>
                          </div>
                          <div className="pod-status">
                            <span className={`status-text ${pod.status.toLowerCase()}`}>
                              {pod.status === 'Pending' ? '준비 중' :
                               pod.status === 'Running' ? '실행중' :
                               pod.status === 'Failed' ? '실패' :
                               pod.status === 'Succeeded' ? '완료' : pod.status}
                            </span>
                            {pod.ip && <span className="pod-age">IP: {pod.ip}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};

// Pod 상태 아이콘
const PodStatusIcon = ({ status }) => {
  switch (status) {
    case 'Running':
      return <CheckCircle size={14} color="var(--accent-green)" />;
    case 'Pending':
      return <Clock size={14} color="var(--accent-yellow)" className="spinning" />;
    case 'Failed':
    case 'Error':
      return <AlertCircle size={14} color="var(--accent-red)" />;
    default:
      return <Circle size={14} color="var(--text-muted)" />;
  }
};

// Pending 상태 표시 컴포넌트
const PendingIndicator = () => (
  <div className="pending-indicator">
    <div className="pending-spinner"></div>
    <span>준비 중...</span>
  </div>
);

// ============================================
// Storage Manager 컴포넌트 (AWS S3 스타일)
// ============================================
const StorageManager = ({ showToast }) => {
  const [storageStatus, setStorageStatus] = useState(null);
  const [buckets, setBuckets] = useState([]);
  const [selectedBucket, setSelectedBucket] = useState(null);
  const [objects, setObjects] = useState([]);
  const [currentPath, setCurrentPath] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showCreateBucket, setShowCreateBucket] = useState(false);
  const [showCreateFolder, setShowCreateFolder] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [newBucketName, setNewBucketName] = useState('');
  const [newFolderName, setNewFolderName] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [previewFile, setPreviewFile] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedObject, setSelectedObject] = useState(null);
  const [showTagsModal, setShowTagsModal] = useState(null);
  const [objectDetail, setObjectDetail] = useState(null);
  const [objectTags, setObjectTags] = useState({});
  const [objectVersions, setObjectVersions] = useState([]);
  const [presignedUrl, setPresignedUrl] = useState('');
  const [presignedExpiry, setPresignedExpiry] = useState({ days: 0, hours: 1, minutes: 0 });
  const [detailLoading, setDetailLoading] = useState(false);
  const [draggedItem, setDraggedItem] = useState(null);
  const [dragOverTarget, setDragOverTarget] = useState(null);

  // 스토리지 상태 및 버킷 목록 조회
  const fetchStorageData = useCallback(async () => {
    try {
      const [statusRes, bucketsRes] = await Promise.all([
        axios.get(`${API_BASE}/storage/status`),
        axios.get(`${API_BASE}/storage/buckets`).catch(() => ({ data: { buckets: [] } }))
      ]);
      setStorageStatus(statusRes.data);
      setBuckets(bucketsRes.data.buckets || []);
      setLoading(false);
    } catch (error) {
      console.error('Storage fetch error:', error);
      setStorageStatus({ status: 'disconnected', error: error.message });
      setLoading(false);
    }
  }, []);

  // 버킷 내 객체 목록 조회
  const fetchObjects = useCallback(async (bucketName, prefix = '') => {
    try {
      setActionLoading(true);
      const res = await axios.get(`${API_BASE}/storage/buckets/${bucketName}/objects`, {
        params: { prefix }
      });
      setObjects(res.data.objects || []);
    } catch (error) {
      showToast('객체 목록 조회 실패: ' + error.message, 'error');
    } finally {
      setActionLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchStorageData();
  }, [fetchStorageData]);

  // selectedBucket이나 currentPath가 변경될 때만 객체 목록 조회 (최초 1회)
  useEffect(() => {
    if (!selectedBucket) return;

    let isCancelled = false;
    const loadObjects = async () => {
      try {
        setActionLoading(true);
        const res = await axios.get(`${API_BASE}/storage/buckets/${selectedBucket}/objects`, {
          params: { prefix: currentPath }
        });
        if (!isCancelled) {
          setObjects(res.data.objects || []);
        }
      } catch (error) {
        if (!isCancelled) {
          console.error('객체 목록 조회 실패:', error.message);
        }
      } finally {
        if (!isCancelled) {
          setActionLoading(false);
        }
      }
    };
    loadObjects();

    return () => { isCancelled = true; };
  }, [selectedBucket, currentPath]);

  // 버킷 생성
  const handleCreateBucket = async () => {
    if (!newBucketName.trim()) return;
    try {
      setActionLoading(true);
      await axios.post(`${API_BASE}/storage/buckets`, { name: newBucketName.toLowerCase() });
      showToast(`버킷 '${newBucketName}'이 생성되었습니다`);
      setNewBucketName('');
      setShowCreateBucket(false);
      fetchStorageData();
    } catch (error) {
      showToast(error.response?.data?.detail || '버킷 생성 실패', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // 버킷 삭제
  const handleDeleteBucket = async (bucketName, force = false) => {
    try {
      setActionLoading(true);
      await axios.delete(`${API_BASE}/storage/buckets/${bucketName}`, { params: { force } });
      showToast(`버킷 '${bucketName}'이 삭제되었습니다`);
      setDeleteConfirm(null);
      if (selectedBucket === bucketName) {
        setSelectedBucket(null);
        setObjects([]);
      }
      fetchStorageData();
    } catch (error) {
      showToast(error.response?.data?.detail || '버킷 삭제 실패', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // 폴더 생성
  const handleCreateFolder = async () => {
    if (!newFolderName.trim() || !selectedBucket) return;
    try {
      setActionLoading(true);
      const folderPath = currentPath + newFolderName;
      await axios.post(`${API_BASE}/storage/buckets/${selectedBucket}/folders`, {
        folder_name: folderPath
      });
      showToast(`폴더 '${newFolderName}'이 생성되었습니다`);
      setNewFolderName('');
      setShowCreateFolder(false);
      fetchObjects(selectedBucket, currentPath);
    } catch (error) {
      showToast(error.response?.data?.detail || '폴더 생성 실패', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // 파일 업로드
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !selectedBucket) {
      showToast('파일을 선택해주세요', 'error');
      return;
    }

    setActionLoading(true);
    const reader = new FileReader();

    reader.onload = async (e) => {
      try {
        const base64Content = e.target.result.split(',')[1];
        await axios.post(`${API_BASE}/storage/buckets/${selectedBucket}/objects`, {
          object_name: currentPath + file.name,
          content: base64Content,
          content_type: file.type || 'application/octet-stream'
        });
        showToast(`'${file.name}'이 업로드되었습니다`);
        setShowUpload(false);
        fetchObjects(selectedBucket, currentPath);
      } catch (error) {
        showToast(error.response?.data?.detail || '업로드 실패', 'error');
      } finally {
        setActionLoading(false);
      }
    };

    reader.onerror = () => {
      showToast('파일을 읽는 중 오류가 발생했습니다', 'error');
      setActionLoading(false);
    };

    reader.readAsDataURL(file);
  };

  // 객체 삭제
  const handleDeleteObject = async (objectName) => {
    try {
      setActionLoading(true);
      await axios.delete(`${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(objectName)}`);
      showToast('삭제되었습니다');
      setDeleteConfirm(null);
      fetchObjects(selectedBucket, currentPath);
    } catch (error) {
      showToast(error.response?.data?.detail || '삭제 실패', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // 파일 다운로드
  const handleDownload = async (objectName) => {
    try {
      setActionLoading(true);
      const res = await axios.get(`${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(objectName)}/download`);
      const link = document.createElement('a');
      link.href = `data:${res.data.content_type};base64,${res.data.content}`;
      link.download = objectName.split('/').pop();
      link.click();
      showToast('다운로드가 시작되었습니다');
    } catch (error) {
      showToast(error.response?.data?.detail || '다운로드 실패', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // 폴더 진입
  const handleNavigate = (obj) => {
    if (obj.is_folder) {
      setCurrentPath(obj.name);
    }
  };

  // Base64를 UTF-8 문자열로 디코딩하는 헬퍼 함수
  const decodeBase64UTF8 = (base64) => {
    try {
      const binaryString = atob(base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      return new TextDecoder('utf-8').decode(bytes);
    } catch {
      return atob(base64); // fallback
    }
  };

  // 미리보기 가능한 파일 타입 확인
  const isPreviewable = (filename) => {
    const ext = filename.toLowerCase().split('.').pop();
    const previewableExtensions = [
      // 이미지
      'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico',
      // 비디오
      'mp4', 'webm', 'ogg', 'mov',
      // 오디오
      'mp3', 'wav', 'ogg', 'aac',
      // 문서
      'pdf',
      // 텍스트/코드
      'txt', 'md', 'json', 'xml', 'html', 'htm', 'css', 'js', 'ts', 'py', 'yaml', 'yml', 'log', 'csv'
    ];
    return previewableExtensions.includes(ext);
  };

  // 파일 타입 분류
  const getFileType = (filename, contentType) => {
    const ext = filename.toLowerCase().split('.').pop();
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(ext)) return 'image';
    if (['mp4', 'webm', 'ogg', 'mov'].includes(ext)) return 'video';
    if (['mp3', 'wav', 'aac'].includes(ext) || (ext === 'ogg' && contentType?.includes('audio'))) return 'audio';
    if (ext === 'pdf') return 'pdf';
    if (['html', 'htm'].includes(ext)) return 'html';
    if (['txt', 'md', 'json', 'xml', 'css', 'js', 'ts', 'py', 'yaml', 'yml', 'log', 'csv'].includes(ext)) return 'text';
    return 'unknown';
  };

  // 파일 미리보기
  const handlePreview = async (obj) => {
    if (obj.is_folder) return;

    try {
      setPreviewLoading(true);
      const res = await axios.get(`${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(obj.name)}/download`);
      const fileType = getFileType(obj.display_name, res.data.content_type);

      setPreviewFile({
        name: obj.display_name,
        fullName: obj.name,
        content: res.data.content,
        contentType: res.data.content_type,
        fileType: fileType,
        size: obj.size_human
      });
    } catch (error) {
      showToast('파일 미리보기 실패: ' + error.message, 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // 파일 클릭 핸들러
  const handleFileClick = (obj) => {
    if (obj.is_folder) {
      handleNavigate(obj);
    } else if (isPreviewable(obj.display_name)) {
      handlePreview(obj);
    }
  };

  // 상위 폴더로
  const handleGoBack = () => {
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    setCurrentPath(parts.length > 0 ? parts.join('/') + '/' : '');
  };

  // 드래그 앤 드롭 핸들러
  const handleDragStart = (e, obj) => {
    // 폴더와 상위 폴더(..)는 드래그 불가, 파일만 드래그 가능
    if (obj.is_folder || obj.isParentDir) {
      e.preventDefault();
      return;
    }
    setDraggedItem(obj);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', obj.name);
  };

  const handleDragOver = (e, targetObj) => {
    e.preventDefault();
    // 폴더 또는 상위 폴더(..)로만 드롭 가능
    if (targetObj && (targetObj.is_folder || targetObj.isParentDir)) {
      e.dataTransfer.dropEffect = 'move';
      setDragOverTarget(targetObj.name);
    }
  };

  const handleDragLeave = () => {
    setDragOverTarget(null);
  };

  const handleDrop = async (e, targetObj) => {
    e.preventDefault();
    setDragOverTarget(null);

    if (!draggedItem || !targetObj) return;
    if (draggedItem.name === targetObj.name) return;

    // 상위 폴더(..)로 드롭하는 경우
    if (targetObj.isParentDir) {
      const parts = currentPath.split('/').filter(Boolean);
      parts.pop(); // 현재 폴더 제거
      const parentPath = parts.length > 0 ? parts.join('/') + '/' : '';
      const fileName = draggedItem.display_name;
      const newPath = parentPath + fileName;

      try {
        setActionLoading(true);
        await axios.post(`${API_BASE}/storage/buckets/${selectedBucket}/objects/move`, {
          source: draggedItem.name,
          destination: newPath
        });
        showToast(`'${fileName}'을 상위 폴더로 이동했습니다`);
        fetchObjects(selectedBucket, currentPath);
      } catch (error) {
        showToast('파일 이동 실패: ' + error.message, 'error');
      } finally {
        setActionLoading(false);
      }
    }
    // 폴더로 드롭하는 경우
    else if (targetObj.is_folder) {
      const fileName = draggedItem.display_name;
      const newPath = targetObj.name + fileName;

      try {
        setActionLoading(true);
        await axios.post(`${API_BASE}/storage/buckets/${selectedBucket}/objects/move`, {
          source: draggedItem.name,
          destination: newPath
        });
        showToast(`'${fileName}'을 '${targetObj.display_name}' 폴더로 이동했습니다`);
        fetchObjects(selectedBucket, currentPath);
      } catch (error) {
        showToast('파일 이동 실패: ' + error.message, 'error');
      } finally {
        setActionLoading(false);
      }
    }

    setDraggedItem(null);
  };

  const handleDragEnd = () => {
    setDraggedItem(null);
    setDragOverTarget(null);
  };

  // 필터링된 객체 (현재 경로가 있으면 상위 폴더 항목 추가)
  const filteredObjects = [
    // 상위 폴더 항목 (currentPath가 있을 때만)
    ...(currentPath ? [{
      name: '..',
      display_name: '..',
      is_folder: true,
      size_human: '-',
      last_modified: null,
      isParentDir: true
    }] : []),
    // 실제 객체들 (현재 폴더 자체는 제외)
    ...objects.filter(obj => {
      // 현재 폴더 자체인 경우 제외 (폴더이고 이름이 currentPath와 같으면)
      if (obj.is_folder && currentPath && obj.name === currentPath) {
        return false;
      }
      return obj.display_name.toLowerCase().includes(searchTerm.toLowerCase());
    })
  ];

  // 객체 세부 정보 조회
  const handleShowDetail = async (obj) => {
    if (obj.is_folder) return;

    setDetailLoading(true);
    setObjectDetail(obj);
    setPresignedUrl('');
    setPresignedExpiry({ days: 0, hours: 1, minutes: 0 });

    try {
      // 태그 조회
      const tagsRes = await axios.get(
        `${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(obj.name)}/tags`
      ).catch(() => ({ data: { tags: {} } }));
      setObjectTags(tagsRes.data.tags || {});

      // 버전 조회 (버전 관리 활성화 시)
      const versionsRes = await axios.get(
        `${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(obj.name)}/versions`
      ).catch(() => ({ data: { versions: [] } }));
      setObjectVersions(versionsRes.data.versions || []);
    } catch (error) {
      console.error('Failed to fetch object details:', error);
    } finally {
      setDetailLoading(false);
    }
  };

  // Presigned URL 생성
  const handleGeneratePresignedUrl = async () => {
    if (!objectDetail) return;

    const expirySeconds =
      (presignedExpiry.days * 86400) +
      (presignedExpiry.hours * 3600) +
      (presignedExpiry.minutes * 60);

    if (expirySeconds <= 0) {
      showToast('만료 시간을 설정해주세요', 'error');
      return;
    }

    try {
      const res = await axios.post(
        `${API_BASE}/storage/buckets/${selectedBucket}/presigned-url`,
        {
          object_name: objectDetail.name,
          method: 'GET',
          expires: expirySeconds
        }
      );
      setPresignedUrl(res.data.url);
      showToast('임시 URL이 생성되었습니다', 'success');
    } catch (error) {
      showToast('URL 생성 실패: ' + error.message, 'error');
    }
  };

  // 태그 추가
  const handleAddTag = async (key, value) => {
    if (!objectDetail || !key.trim()) return;

    try {
      const newTags = { ...objectTags, [key]: value };
      await axios.put(
        `${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(objectDetail.name)}/tags`,
        { tags: newTags }
      );
      setObjectTags(newTags);
      showToast('태그가 추가되었습니다', 'success');
    } catch (error) {
      showToast('태그 추가 실패: ' + error.message, 'error');
    }
  };

  // 태그 삭제
  const handleRemoveTag = async (key) => {
    if (!objectDetail) return;

    try {
      const newTags = { ...objectTags };
      delete newTags[key];
      await axios.put(
        `${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(objectDetail.name)}/tags`,
        { tags: newTags }
      );
      setObjectTags(newTags);
      showToast('태그가 삭제되었습니다', 'success');
    } catch (error) {
      showToast('태그 삭제 실패: ' + error.message, 'error');
    }
  };

  // URL 복사
  const handleCopyUrl = async (url) => {
    try {
      await navigator.clipboard.writeText(url);
      showToast('URL이 복사되었습니다', 'success');
    } catch {
      showToast('URL 복사 실패', 'error');
    }
  };

  if (loading) {
    return (
      <section className="section">
        <div className="card">
          <div className="loading-container">
            <div className="spinner large"></div>
            <p>스토리지 정보를 불러오는 중...</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="section storage-section">
      {/* Storage Status */}
      <div className="storage-header">
        <div className="storage-status-card">
          <Archive size={24} />
          <div>
            <h3>RustFS Storage</h3>
            <span className={`status-badge ${storageStatus?.status === 'connected' ? 'running' : 'stopped'}`}>
              {storageStatus?.status === 'connected' ? '연결됨' : '연결 안됨'}
            </span>
          </div>
          {storageStatus?.status === 'connected' && (
            <span className="bucket-count">{buckets.length}개 버킷</span>
          )}
        </div>
        <div className="header-actions">
          <button
            className={`btn ${showAdvanced ? 'btn-primary' : ''}`}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <Settings size={16} /> 고급 설정
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreateBucket(true)}>
            <Plus size={16} /> 버킷 생성
          </button>
        </div>
      </div>

      {storageStatus?.status !== 'connected' ? (
        <div className="card">
          <div className="no-data">
            <Archive size={48} color="var(--text-muted)" />
            <p>RustFS 서비스에 연결할 수 없습니다</p>
            <p className="hint">{storageStatus?.message || 'RustFS를 먼저 실행하세요'}</p>
          </div>
        </div>
      ) : (
        <div className="storage-layout">
          {/* Bucket List */}
          <div className="bucket-panel">
            <div className="panel-header">
              <h3>버킷</h3>
              <span className="s3-compat-badge" title="AWS S3 API 호환">
                <Cloud size={12} /> S3
              </span>
            </div>
            <div className="bucket-list">
              {buckets.length === 0 ? (
                <div className="empty-state">
                  <Folder size={32} color="var(--text-muted)" />
                  <p>버킷이 없습니다</p>
                </div>
              ) : (
                buckets.map((bucket) => (
                  <div
                    key={bucket.name}
                    className={`bucket-item ${selectedBucket === bucket.name ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedBucket(bucket.name);
                      setCurrentPath('');
                    }}
                  >
                    <div className="bucket-icon">
                      <Archive size={20} />
                    </div>
                    <div className="bucket-details">
                      <div className="bucket-name-row">
                        <span className="bucket-name">{bucket.name}</span>
                        <span className="bucket-type-badge">S3 호환</span>
                      </div>
                      <div className="bucket-stats">
                        <span className="bucket-stat">
                          <File size={12} />
                          {bucket.object_count} 객체
                        </span>
                        <span className="bucket-stat">
                          <HardDrive size={12} />
                          {bucket.total_size_human}
                        </span>
                      </div>
                    </div>
                    <div className="bucket-actions">
                      <button
                        className="btn-icon bucket-settings"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedBucket(bucket.name);
                          setShowAdvanced(true);
                        }}
                        title="버킷 설정"
                      >
                        <Settings size={14} />
                      </button>
                      <button
                        className="btn-icon danger bucket-delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteConfirm({ type: 'bucket', name: bucket.name, hasObjects: bucket.object_count > 0 });
                        }}
                        title="버킷 삭제"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Objects Panel */}
          <div className="objects-panel">
            {!selectedBucket ? (
              <div className="no-bucket-selected">
                <Folder size={48} color="var(--text-muted)" />
                <p>버킷을 선택하세요</p>
              </div>
            ) : (
              <>
                <div className="objects-toolbar">
                  <div className="breadcrumb">
                    <span className="breadcrumb-bucket" onClick={() => setCurrentPath('')}>
                      {selectedBucket}
                    </span>
                    {currentPath && (
                      <>
                        <ChevronRight size={16} />
                        {currentPath.split('/').filter(Boolean).map((part, idx, arr) => (
                          <React.Fragment key={idx}>
                            <span
                              className="breadcrumb-part"
                              onClick={() => setCurrentPath(arr.slice(0, idx + 1).join('/') + '/')}
                            >
                              {part}
                            </span>
                            {idx < arr.length - 1 && <ChevronRight size={16} />}
                          </React.Fragment>
                        ))}
                      </>
                    )}
                  </div>
                  <div className="toolbar-actions">
                    <div className="search-box">
                      <Search size={16} />
                      <input
                        type="text"
                        placeholder="검색..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                      />
                    </div>
                    {currentPath && (
                      <button className="btn btn-outline" onClick={handleGoBack}>
                        <ArrowLeft size={16} /> 상위 폴더
                      </button>
                    )}
                    <button className="btn btn-outline" onClick={() => setShowCreateFolder(true)}>
                      <FolderPlus size={16} /> 폴더
                    </button>
                    <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
                      <Upload size={16} /> 업로드
                    </button>
                  </div>
                </div>

                <div className="objects-list">
                  {actionLoading ? (
                    <div className="loading-container">
                      <div className="spinner"></div>
                    </div>
                  ) : filteredObjects.length === 0 ? (
                    <div className="empty-state">
                      <File size={32} color="var(--text-muted)" />
                      <p>{searchTerm ? '검색 결과가 없습니다' : '이 위치에 파일이 없습니다'}</p>
                    </div>
                  ) : (
                    <table className="objects-table">
                      <thead>
                        <tr>
                          <th>이름</th>
                          <th>크기</th>
                          <th>수정일</th>
                          <th>작업</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredObjects.map((obj) => (
                          <tr
                            key={obj.name}
                            className={`${obj.is_folder ? 'folder-row' : ''} ${obj.isParentDir ? 'parent-dir-row' : ''} ${dragOverTarget === obj.name ? 'drag-over' : ''} ${draggedItem?.name === obj.name ? 'dragging' : ''}`}
                            draggable={!obj.is_folder && !obj.isParentDir}
                            onDragStart={(e) => handleDragStart(e, obj)}
                            onDragOver={(e) => handleDragOver(e, obj)}
                            onDragLeave={handleDragLeave}
                            onDrop={(e) => handleDrop(e, obj)}
                            onDragEnd={handleDragEnd}
                          >
                            <td>
                              <div
                                className="object-name"
                                onClick={() => obj.isParentDir ? handleGoBack() : handleFileClick(obj)}
                                style={{ cursor: obj.is_folder || isPreviewable(obj.display_name) ? 'pointer' : 'default' }}
                              >
                                {obj.isParentDir ? (
                                  <ArrowLeft size={18} color="var(--text-muted)" />
                                ) : obj.is_folder ? (
                                  <Folder size={18} color="var(--accent-yellow)" />
                                ) : (
                                  <File size={18} color={isPreviewable(obj.display_name) ? 'var(--accent-blue)' : 'var(--text-muted)'} />
                                )}
                                <span>{obj.display_name}</span>
                                {!obj.is_folder && isPreviewable(obj.display_name) && (
                                  <span className="preview-hint" title="클릭하여 미리보기">👁</span>
                                )}
                                {obj.is_folder && !obj.isParentDir && (
                                  <span className="drop-hint" title="파일을 여기에 드롭하여 이동">📥</span>
                                )}
                                {obj.isParentDir && (
                                  <span className="drop-hint" title="파일을 여기에 드롭하여 상위 폴더로 이동">📤</span>
                                )}
                              </div>
                            </td>
                            <td>{obj.size_human}</td>
                            <td>{obj.last_modified ? new Date(obj.last_modified).toLocaleDateString() : '-'}</td>
                            <td>
                              <div className="action-buttons">
                                {!obj.is_folder && (
                                  <>
                                    <button
                                      className="btn-icon"
                                      onClick={() => handleShowDetail(obj)}
                                      title="세부 정보"
                                    >
                                      <Info size={14} />
                                    </button>
                                    <button
                                      className="btn-icon"
                                      onClick={() => handleDownload(obj.name)}
                                      title="다운로드"
                                    >
                                      <Download size={14} />
                                    </button>
                                  </>
                                )}
                                {/* 상위 폴더와 현재 경로의 폴더는 삭제 버튼 숨김 */}
                                {!obj.isParentDir && !obj.is_folder && (
                                  <button
                                    className="btn-icon danger"
                                    onClick={() => setDeleteConfirm({ type: 'object', name: obj.name, isFolder: obj.is_folder })}
                                    title="삭제"
                                  >
                                    <Trash2 size={14} />
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Create Bucket Modal */}
      {showCreateBucket && (
        <div className="modal-overlay" onClick={() => setShowCreateBucket(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>버킷 생성</h3>
              <button className="btn-icon" onClick={() => setShowCreateBucket(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <label>버킷 이름</label>
              <input
                type="text"
                value={newBucketName}
                onChange={(e) => setNewBucketName(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                placeholder="my-bucket"
                autoFocus
              />
              <p className="hint">영문 소문자, 숫자, 하이픈만 사용 가능 (3자 이상)</p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setShowCreateBucket(false)}>취소</button>
              <button
                className="btn btn-primary"
                onClick={handleCreateBucket}
                disabled={newBucketName.length < 3 || actionLoading}
              >
                {actionLoading ? '생성 중...' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Folder Modal */}
      {showCreateFolder && (
        <div className="modal-overlay" onClick={() => setShowCreateFolder(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>폴더 생성</h3>
              <button className="btn-icon" onClick={() => setShowCreateFolder(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <label>폴더 이름</label>
              <input
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="new-folder"
                autoFocus
              />
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setShowCreateFolder(false)}>취소</button>
              <button
                className="btn btn-primary"
                onClick={handleCreateFolder}
                disabled={!newFolderName.trim() || actionLoading}
              >
                {actionLoading ? '생성 중...' : '생성'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="modal-overlay" onClick={() => setShowUpload(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>파일 업로드</h3>
              <button className="btn-icon" onClick={() => setShowUpload(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <label className="upload-zone" htmlFor="file-upload-input">
                <Upload size={48} color="var(--text-muted)" />
                <p>클릭하여 파일 선택</p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                  또는 파일을 여기에 드래그하세요
                </p>
                <input
                  id="file-upload-input"
                  type="file"
                  onChange={handleFileUpload}
                  disabled={actionLoading}
                  style={{ display: 'none' }}
                />
              </label>
              {actionLoading && <p className="uploading">업로드 중...</p>}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal modal-danger" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>삭제 확인</h3>
              <button className="btn-icon" onClick={() => setDeleteConfirm(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <AlertCircle size={48} color="var(--accent-red)" />
              {deleteConfirm.type === 'bucket' ? (
                <>
                  <p>버킷 <strong>'{deleteConfirm.name}'</strong>을(를) 삭제하시겠습니까?</p>
                  {deleteConfirm.hasObjects && (
                    <p className="warning">이 버킷에는 객체가 있습니다. 강제 삭제하면 모든 객체가 함께 삭제됩니다.</p>
                  )}
                </>
              ) : (
                <p>
                  {deleteConfirm.isFolder ? '폴더' : '파일'} <strong>'{deleteConfirm.name.split('/').pop()}'</strong>을(를) 삭제하시겠습니까?
                  {deleteConfirm.isFolder && <span className="warning"> 하위 모든 파일이 함께 삭제됩니다.</span>}
                </p>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setDeleteConfirm(null)}>취소</button>
              <button
                className="btn btn-danger"
                onClick={() => {
                  if (deleteConfirm.type === 'bucket') {
                    handleDeleteBucket(deleteConfirm.name, deleteConfirm.hasObjects);
                  } else {
                    handleDeleteObject(deleteConfirm.name);
                  }
                }}
                disabled={actionLoading}
              >
                {actionLoading ? '삭제 중...' : '삭제'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {(previewFile || previewLoading) && (
        <div className="modal-overlay preview-overlay" onClick={() => setPreviewFile(null)}>
          <div className="modal modal-preview" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{previewFile?.name || '파일 미리보기'}</h3>
              <div className="modal-header-actions">
                {previewFile && (
                  <button
                    className="btn btn-sm btn-outline"
                    onClick={() => handleDownload(previewFile.fullName)}
                    title="다운로드"
                  >
                    <Download size={16} /> 다운로드
                  </button>
                )}
                <button className="btn-icon" onClick={() => setPreviewFile(null)}>
                  <X size={20} />
                </button>
              </div>
            </div>
            <div className="modal-body preview-content">
              {previewLoading ? (
                <div className="preview-loading">
                  <RefreshCw className="spin" size={32} />
                  <p>파일을 불러오는 중...</p>
                </div>
              ) : previewFile?.fileType === 'image' ? (
                <img
                  src={`data:${previewFile.contentType};base64,${previewFile.content}`}
                  alt={previewFile.name}
                  className="preview-image"
                />
              ) : previewFile?.fileType === 'video' ? (
                <video
                  src={`data:${previewFile.contentType};base64,${previewFile.content}`}
                  controls
                  autoPlay
                  className="preview-video"
                />
              ) : previewFile?.fileType === 'audio' ? (
                <div className="preview-audio-container">
                  <div className="audio-icon">🎵</div>
                  <p>{previewFile.name}</p>
                  <audio
                    src={`data:${previewFile.contentType};base64,${previewFile.content}`}
                    controls
                    autoPlay
                    className="preview-audio"
                  />
                </div>
              ) : previewFile?.fileType === 'pdf' ? (
                <iframe
                  src={`${API_BASE}/storage/buckets/${selectedBucket}/objects/${encodeURIComponent(previewFile.fullName)}/stream`}
                  className="preview-pdf"
                  title={previewFile.name}
                />
              ) : previewFile?.fileType === 'html' ? (
                <iframe
                  srcDoc={(() => {
                    try {
                      const htmlContent = decodeBase64UTF8(previewFile.content);
                      // 한글 및 다국어 폰트 지원을 위한 스타일 주입
                      const fontStyle = `
                        <meta charset="UTF-8">
                        <style>
                          @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Noto+Sans+JP:wght@400;500;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');
                          * { font-family: 'Noto Sans KR', 'Noto Sans JP', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
                          body { margin: 16px; line-height: 1.6; }
                          pre, code { font-family: 'Consolas', 'Monaco', 'Courier New', monospace; white-space: pre-wrap; }
                        </style>
                      `;
                      // head 태그가 있으면 그 안에, 없으면 문서 앞에 추가
                      if (htmlContent.includes('<head>')) {
                        return htmlContent.replace('<head>', '<head>' + fontStyle);
                      } else if (htmlContent.includes('<html>')) {
                        return htmlContent.replace('<html>', '<html><head>' + fontStyle + '</head>');
                      } else {
                        return '<!DOCTYPE html><html><head>' + fontStyle + '</head><body>' + htmlContent + '</body></html>';
                      }
                    } catch {
                      return '<p>HTML을 표시할 수 없습니다</p>';
                    }
                  })()}
                  className="preview-html"
                  title={previewFile.name}
                  sandbox="allow-same-origin allow-scripts"
                />
              ) : previewFile?.fileType === 'text' ? (
                <pre className="preview-text">
                  {(() => {
                    try {
                      return decodeBase64UTF8(previewFile.content);
                    } catch {
                      return '텍스트를 표시할 수 없습니다';
                    }
                  })()}
                </pre>
              ) : (
                <div className="preview-unsupported">
                  <File size={48} />
                  <p>미리보기를 지원하지 않는 파일 형식입니다</p>
                  <button
                    className="btn btn-primary"
                    onClick={() => handleDownload(previewFile.fullName)}
                  >
                    <Download size={16} /> 다운로드
                  </button>
                </div>
              )}
            </div>
            {previewFile && (
              <div className="modal-footer preview-footer">
                <span className="file-info">
                  크기: {previewFile.size} | 타입: {previewFile.contentType}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 고급 설정 패널 */}
      {showAdvanced && (
        <>
          <div
            className="sidebar-overlay"
            onClick={() => setShowAdvanced(false)}
          />
          <div className="advanced-settings-panel">
            <div className="advanced-panel-header">
              <div className="panel-title">
                <Settings size={20} />
                <div>
                  <h3>버킷 설정</h3>
                  {selectedBucket && <span className="bucket-label">{selectedBucket}</span>}
                </div>
              </div>
              <button className="btn-icon" onClick={() => setShowAdvanced(false)}>
                <X size={20} />
              </button>
            </div>
            <StorageAdvancedTabs
              bucketName={selectedBucket}
              selectedObject={selectedObject}
              showToast={showToast}
            />
          </div>
        </>
      )}

      {/* 객체 세부 정보 패널 */}
      {objectDetail && (
        <div className="object-detail-panel">
          <div className="detail-panel-header">
            <h3>객체 세부 정보</h3>
            <button className="btn-icon" onClick={() => setObjectDetail(null)}>
              <X size={20} />
            </button>
          </div>

          <div className="detail-panel-content">
            {/* 상단 액션 버튼들 */}
            <div className="detail-actions">
              <button
                className="btn btn-outline"
                onClick={() => handleDownload(objectDetail.name)}
              >
                <Download size={16} /> 다운로드
              </button>
              {isPreviewable(objectDetail.display_name) && (
                <button
                  className="btn btn-outline"
                  onClick={() => handlePreview(objectDetail)}
                >
                  <Eye size={16} /> 미리보기
                </button>
              )}
            </div>

            {/* 객체 정보 섹션 */}
            <div className="detail-section">
              <h4><File size={16} /> 객체 정보</h4>
              <div className="detail-info-grid">
                <div className="detail-info-item">
                  <label>객체 이름</label>
                  <span className="info-value monospace">{objectDetail.display_name}</span>
                </div>
                <div className="detail-info-item">
                  <label>전체 경로</label>
                  <span className="info-value monospace">{objectDetail.name}</span>
                </div>
                <div className="detail-info-item">
                  <label>객체 크기</label>
                  <span className="info-value">{objectDetail.size_human} ({objectDetail.size?.toLocaleString()} bytes)</span>
                </div>
                <div className="detail-info-item">
                  <label>객체 유형</label>
                  <span className="info-value">{objectDetail.content_type || 'application/octet-stream'}</span>
                </div>
                <div className="detail-info-item">
                  <label>ETag</label>
                  <span className="info-value monospace">{objectDetail.etag || '-'}</span>
                </div>
                <div className="detail-info-item">
                  <label>마지막 수정 시간</label>
                  <span className="info-value">
                    {objectDetail.last_modified
                      ? new Date(objectDetail.last_modified).toLocaleString('ko-KR')
                      : '-'}
                  </span>
                </div>
              </div>
            </div>

            {/* 태그 섹션 */}
            <div className="detail-section">
              <h4><Tag size={16} /> 태그 설정</h4>
              {detailLoading ? (
                <div className="loading-inline"><RefreshCw className="spin" size={16} /> 로딩 중...</div>
              ) : (
                <>
                  <div className="tags-display">
                    {Object.entries(objectTags).length > 0 ? (
                      Object.entries(objectTags).map(([key, value]) => (
                        <div key={key} className="tag-chip">
                          <span className="tag-chip-key">{key}</span>
                          <span className="tag-chip-value">{value}</span>
                          <button className="tag-chip-remove" onClick={() => handleRemoveTag(key)}>
                            <X size={12} />
                          </button>
                        </div>
                      ))
                    ) : (
                      <p className="no-data-text">설정된 태그가 없습니다</p>
                    )}
                  </div>
                  <div className="add-tag-inline">
                    <input
                      type="text"
                      placeholder="키"
                      id="new-tag-key"
                      className="tag-input"
                    />
                    <input
                      type="text"
                      placeholder="값"
                      id="new-tag-value"
                      className="tag-input"
                    />
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={() => {
                        const key = document.getElementById('new-tag-key').value;
                        const value = document.getElementById('new-tag-value').value;
                        if (key) {
                          handleAddTag(key, value);
                          document.getElementById('new-tag-key').value = '';
                          document.getElementById('new-tag-value').value = '';
                        }
                      }}
                    >
                      추가
                    </button>
                  </div>
                </>
              )}
            </div>

            {/* 버전 정보 섹션 */}
            <div className="detail-section">
              <h4><Clock size={16} /> 버전 정보</h4>
              {detailLoading ? (
                <div className="loading-inline"><RefreshCw className="spin" size={16} /> 로딩 중...</div>
              ) : objectVersions.length > 0 ? (
                <div className="versions-display">
                  {objectVersions.slice(0, 5).map((ver, idx) => (
                    <div key={ver.version_id || idx} className="version-row">
                      <div className="version-row-info">
                        <span className="version-id-text">{ver.version_id || 'null'}</span>
                        <span className="version-date-text">
                          {ver.last_modified ? new Date(ver.last_modified).toLocaleString('ko-KR') : '-'}
                        </span>
                      </div>
                      {ver.is_latest && <span className="version-badge latest">최신</span>}
                      {ver.is_delete_marker && <span className="version-badge deleted">삭제됨</span>}
                    </div>
                  ))}
                  {objectVersions.length > 5 && (
                    <p className="more-text">외 {objectVersions.length - 5}개 버전</p>
                  )}
                </div>
              ) : (
                <p className="no-data-text">버전 관리가 비활성화되어 있거나 버전 정보가 없습니다</p>
              )}
            </div>

            {/* 법적 보관 / 보관 정책 */}
            <div className="detail-section">
              <h4><Shield size={16} /> 법적 보관</h4>
              <div className="legal-hold-status">
                <Lock size={16} color="var(--text-muted)" />
                <span className="no-data-text">법적 보관이 설정되지 않았습니다</span>
              </div>
            </div>

            <div className="detail-section">
              <h4><Shield size={16} /> 보관 정책</h4>
              <div className="retention-status">
                <span className="no-data-text">보관 정책이 설정되지 않았습니다</span>
              </div>
            </div>

            {/* 임시 URL 생성 */}
            <div className="detail-section">
              <h4><Link2 size={16} /> 임시 URL 만료</h4>
              <div className="presigned-form-inline">
                <div className="expiry-inputs">
                  <div className="expiry-input-group">
                    <input
                      type="number"
                      min="0"
                      max="7"
                      value={presignedExpiry.days}
                      onChange={(e) => setPresignedExpiry({ ...presignedExpiry, days: parseInt(e.target.value) || 0 })}
                    />
                    <label>일</label>
                  </div>
                  <div className="expiry-input-group">
                    <input
                      type="number"
                      min="0"
                      max="23"
                      value={presignedExpiry.hours}
                      onChange={(e) => setPresignedExpiry({ ...presignedExpiry, hours: parseInt(e.target.value) || 0 })}
                    />
                    <label>시간</label>
                  </div>
                  <div className="expiry-input-group">
                    <input
                      type="number"
                      min="0"
                      max="59"
                      value={presignedExpiry.minutes}
                      onChange={(e) => setPresignedExpiry({ ...presignedExpiry, minutes: parseInt(e.target.value) || 0 })}
                    />
                    <label>분</label>
                  </div>
                </div>
                <button className="btn btn-primary" onClick={handleGeneratePresignedUrl}>
                  URL 생성
                </button>
              </div>

              {presignedUrl && (
                <div className="presigned-result-inline">
                  <input type="text" value={presignedUrl} readOnly className="presigned-url-input" />
                  <button className="btn btn-outline" onClick={() => handleCopyUrl(presignedUrl)}>
                    <Copy size={14} />
                  </button>
                  <a
                    href={presignedUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-outline"
                  >
                    <ExternalLink size={14} />
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 태그 관리 모달 */}
      {showTagsModal && (
        <div className="modal-overlay" onClick={() => setShowTagsModal(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>객체 태그 관리</h3>
              <button className="btn-icon" onClick={() => setShowTagsModal(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <ObjectTagsManager
                bucketName={selectedBucket}
                objectName={showTagsModal}
                showToast={showToast}
                onClose={() => setShowTagsModal(null)}
              />
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

// ============================================
// Cluster Manager 컴포넌트 (멀티노드 관리)
// ============================================
const ClusterManager = ({ showToast }) => {
  const [nodes, setNodes] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetail, setNodeDetail] = useState(null);
  const [joinCommand, setJoinCommand] = useState(null);
  const [clusterResources, setClusterResources] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialLoaded, setInitialLoaded] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [showJoinModal, setShowJoinModal] = useState(false);

  // 노드 목록 조회
  const fetchNodes = useCallback(async () => {
    try {
      const res = await axios.get('/api/cluster/nodes');
      setNodes(res.data.nodes || []);
    } catch (error) {
      showToast('노드 목록 조회 실패', 'error');
    }
  }, [showToast]);

  // 클러스터 리소스 현황
  const fetchResources = useCallback(async () => {
    try {
      const res = await axios.get('/api/cluster/resources');
      setClusterResources(res.data);
    } catch (error) {
      console.error('리소스 조회 실패:', error);
    }
  }, []);

  // 노드 상세 정보
  const fetchNodeDetail = useCallback(async (nodeName) => {
    try {
      const res = await axios.get(`/api/cluster/nodes/${nodeName}`);
      setNodeDetail(res.data);
    } catch (error) {
      showToast('노드 상세 정보 조회 실패', 'error');
    }
  }, [showToast]);

  // 조인 명령어 조회
  const fetchJoinCommand = useCallback(async () => {
    try {
      const res = await axios.get('/api/cluster/join-command');
      setJoinCommand(res.data);
    } catch (error) {
      showToast('조인 명령어 조회 실패', 'error');
    }
  }, [showToast]);

  useEffect(() => {
    const loadData = async () => {
      // 초기 로딩에만 스피너 표시
      if (!initialLoaded) {
        setLoading(true);
      }
      await Promise.all([fetchNodes(), fetchResources()]);
      if (!initialLoaded) {
        setLoading(false);
        setInitialLoaded(true);
      }
    };
    loadData();
    // 주기적 업데이트는 스피너 없이 백그라운드에서 실행
    const interval = setInterval(() => {
      fetchNodes();
      fetchResources();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchNodes, fetchResources, initialLoaded]);

  useEffect(() => {
    if (selectedNode) {
      fetchNodeDetail(selectedNode);
    }
  }, [selectedNode, fetchNodeDetail]);

  // 노드 작업
  const handleNodeAction = async (nodeName, action) => {
    setActionLoading(prev => ({ ...prev, [nodeName]: action }));
    try {
      let res;
      switch (action) {
        case 'cordon':
          res = await axios.post(`/api/cluster/nodes/${nodeName}/cordon`);
          break;
        case 'uncordon':
          res = await axios.post(`/api/cluster/nodes/${nodeName}/uncordon`);
          break;
        case 'drain':
          if (!window.confirm(`'${nodeName}' 노드를 드레인하시겠습니까? 모든 Pod가 다른 노드로 이동됩니다.`)) return;
          res = await axios.post(`/api/cluster/nodes/${nodeName}/drain`);
          break;
        case 'delete':
          if (!window.confirm(`'${nodeName}' 노드를 클러스터에서 제거하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) return;
          res = await axios.delete(`/api/cluster/nodes/${nodeName}`);
          break;
        default:
          return;
      }
      showToast(res.data.message);
      fetchNodes();
    } catch (error) {
      showToast(error.response?.data?.detail || '작업 실패', 'error');
    } finally {
      setActionLoading(prev => ({ ...prev, [nodeName]: null }));
    }
  };

  // 메모리 포맷
  const formatMemory = (memStr) => {
    if (!memStr) return '0';
    if (memStr.endsWith('Ki')) {
      const kb = parseInt(memStr.slice(0, -2));
      return `${(kb / (1024 * 1024)).toFixed(1)} GB`;
    }
    if (memStr.endsWith('Mi')) {
      const mb = parseInt(memStr.slice(0, -2));
      return `${(mb / 1024).toFixed(1)} GB`;
    }
    if (memStr.endsWith('Gi')) {
      return `${memStr.slice(0, -2)} GB`;
    }
    return memStr;
  };

  if (loading) {
    return (
      <div className="loading-container">
        <Loader2 className="spin" size={32} />
        <span>클러스터 정보 로딩 중...</span>
      </div>
    );
  }

  return (
    <div className="cluster-manager">
      {/* 클러스터 요약 */}
      <div className="cluster-summary-bar">
        <div className="summary-item">
          <Server size={20} />
          <div>
            <span className="label">노드</span>
            <span className="value">{nodes.length}개</span>
          </div>
        </div>
        {clusterResources && (
          <>
            <div className="summary-item">
              <Cpu size={20} />
              <div>
                <span className="label">총 CPU</span>
                <span className="value">{clusterResources.cpu?.total} 코어</span>
              </div>
            </div>
            <div className="summary-item">
              <MemoryStick size={20} />
              <div>
                <span className="label">총 메모리</span>
                <span className="value">{clusterResources.memory?.total_human}</span>
              </div>
            </div>
            <div className="summary-item">
              <MonitorDot size={20} />
              <div>
                <span className="label">총 GPU</span>
                <span className="value">{clusterResources.gpu?.total}개</span>
              </div>
            </div>
            <div className="summary-item">
              <Package size={20} />
              <div>
                <span className="label">Pod</span>
                <span className="value">{clusterResources.pods?.used} / {clusterResources.pods?.capacity}</span>
              </div>
            </div>
          </>
        )}
        <button
          className="btn btn-primary"
          onClick={() => { fetchJoinCommand(); setShowJoinModal(true); }}
        >
          <Plus size={16} />
          노드 추가
        </button>
      </div>

      <div className="cluster-content">
        {/* 노드 목록 */}
        <div className="nodes-panel">
          <div className="panel-header">
            <h3><Server size={18} /> 클러스터 노드</h3>
            <button className="btn-icon" onClick={fetchNodes} title="새로고침">
              <RefreshCw size={14} />
            </button>
          </div>

          <div className="nodes-list">
            {nodes.map(node => (
              <div
                key={node.name}
                className={`node-card ${selectedNode === node.name ? 'selected' : ''} ${node.status !== 'Ready' ? 'not-ready' : ''}`}
                onClick={() => setSelectedNode(node.name)}
              >
                <div className="node-header">
                  <div className="node-identity">
                    <span className={`node-role ${node.role}`}>
                      {node.role === 'master' ? <Crown size={14} /> : <Server size={14} />}
                      {node.role}
                    </span>
                    <span className="node-name">{node.name}</span>
                  </div>
                  <span className={`status-badge ${node.status === 'Ready' ? 'success' : 'error'}`}>
                    {node.status}
                  </span>
                </div>

                <div className="node-info-grid">
                  <div className="info-item">
                    <span className="label">IP</span>
                    <span className="value">{node.internal_ip}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">CPU</span>
                    <span className="value">{node.cpu_capacity} 코어</span>
                  </div>
                  <div className="info-item">
                    <span className="label">메모리</span>
                    <span className="value">{formatMemory(node.memory_capacity)}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">GPU</span>
                    <span className="value">{node.gpu_count}개</span>
                  </div>
                  <div className="info-item">
                    <span className="label">Pod</span>
                    <span className="value">{node.pod_count} / {node.pod_capacity}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">K3s</span>
                    <span className="value">{node.kubelet_version}</span>
                  </div>
                </div>

                <div className="node-actions">
                  {node.role !== 'master' && (
                    <>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={(e) => { e.stopPropagation(); handleNodeAction(node.name, 'cordon'); }}
                        disabled={actionLoading[node.name]}
                        title="스케줄링 비활성화"
                      >
                        <PauseCircle size={12} />
                        Cordon
                      </button>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={(e) => { e.stopPropagation(); handleNodeAction(node.name, 'uncordon'); }}
                        disabled={actionLoading[node.name]}
                        title="스케줄링 활성화"
                      >
                        <PlayCircle size={12} />
                        Uncordon
                      </button>
                      <button
                        className="btn btn-sm btn-warning"
                        onClick={(e) => { e.stopPropagation(); handleNodeAction(node.name, 'drain'); }}
                        disabled={actionLoading[node.name]}
                        title="Pod 퇴거"
                      >
                        <ArrowRightLeft size={12} />
                        Drain
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={(e) => { e.stopPropagation(); handleNodeAction(node.name, 'delete'); }}
                        disabled={actionLoading[node.name]}
                        title="클러스터에서 제거"
                      >
                        <Trash2 size={12} />
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 노드 상세 정보 */}
        <div className="node-detail-panel">
          {nodeDetail ? (
            <>
              <div className="panel-header">
                <h3>
                  {nodeDetail.role === 'master' ? <Crown size={18} /> : <Server size={18} />}
                  {nodeDetail.name}
                </h3>
              </div>

              <div className="detail-sections">
                {/* 시스템 정보 */}
                <div className="detail-section">
                  <h4>시스템 정보</h4>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="label">OS</span>
                      <span className="value">{nodeDetail.os}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">커널</span>
                      <span className="value">{nodeDetail.kernel}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">아키텍처</span>
                      <span className="value">{nodeDetail.architecture}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">컨테이너 런타임</span>
                      <span className="value">{nodeDetail.container_runtime}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">Kubelet 버전</span>
                      <span className="value">{nodeDetail.kubelet_version}</span>
                    </div>
                    <div className="detail-item">
                      <span className="label">내부 IP</span>
                      <span className="value">{nodeDetail.internal_ip}</span>
                    </div>
                  </div>
                </div>

                {/* 실행 중인 Pods */}
                <div className="detail-section">
                  <h4>실행 중인 Pod ({nodeDetail.pod_count})</h4>
                  <div className="pods-mini-list">
                    {nodeDetail.pods?.slice(0, 15).map(pod => (
                      <div key={`${pod.namespace}/${pod.name}`} className="pod-mini-item">
                        <span className={`status-dot ${pod.status === 'Running' ? 'healthy' : 'warning'}`}></span>
                        <span className="pod-namespace">{pod.namespace}/</span>
                        <span className="pod-name">{pod.name}</span>
                      </div>
                    ))}
                    {nodeDetail.pods?.length > 15 && (
                      <div className="pods-more">+{nodeDetail.pods.length - 15}개 더</div>
                    )}
                  </div>
                </div>

                {/* 레이블 */}
                <div className="detail-section">
                  <h4>레이블</h4>
                  <div className="labels-list">
                    {Object.entries(nodeDetail.labels || {}).slice(0, 10).map(([key, value]) => (
                      <span key={key} className="label-tag">
                        {key.length > 30 ? '...' + key.slice(-27) : key}={value.length > 20 ? value.slice(0, 17) + '...' : value}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Taints */}
                {nodeDetail.taints?.length > 0 && (
                  <div className="detail-section">
                    <h4>Taints</h4>
                    <div className="taints-list">
                      {nodeDetail.taints.map((taint, idx) => (
                        <span key={idx} className="taint-tag">
                          {taint.key}={taint.value}:{taint.effect}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state">
              <Server size={48} />
              <p>노드를 선택하여 상세 정보를 확인하세요</p>
            </div>
          )}
        </div>
      </div>

      {/* 노드 추가 모달 */}
      {showJoinModal && joinCommand && (
        <div className="modal-overlay" onClick={() => setShowJoinModal(false)}>
          <div className="modal-content join-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3><Plus size={20} /> 새 노드 추가</h3>
              <button className="btn-icon" onClick={() => setShowJoinModal(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <div className="join-info">
                <div className="info-box">
                  <AlertCircle size={16} />
                  <span>마스터 노드 IP: <strong>{joinCommand.master_ip}</strong></span>
                </div>

                <div className="join-section">
                  <h4>1. 워커 노드 추가</h4>
                  <p>새 서버에서 아래 명령어를 실행하세요:</p>
                  <pre className="code-block">
                    {joinCommand.instructions?.worker}
                  </pre>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => {
                      navigator.clipboard.writeText(joinCommand.instructions?.worker || '');
                      showToast('명령어가 복사되었습니다');
                    }}
                  >
                    <Copy size={14} />
                    복사
                  </button>
                </div>

                <div className="join-section">
                  <h4>2. 마스터 노드 추가 (HA 구성)</h4>
                  <p>고가용성을 위해 추가 마스터 노드를 설정하려면:</p>
                  <pre className="code-block">
                    {joinCommand.instructions?.master}
                  </pre>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => {
                      navigator.clipboard.writeText(joinCommand.instructions?.master || '');
                      showToast('명령어가 복사되었습니다');
                    }}
                  >
                    <Copy size={14} />
                    복사
                  </button>
                </div>

                <div className="info-box warning">
                  <AlertCircle size={16} />
                  <span>{joinCommand.note}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================
// Benchmark Manager 컴포넌트
// ============================================
const BenchmarkManager = ({ showToast }) => {
  const [configs, setConfigs] = useState([]);
  const [results, setResults] = useState([]);
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [selectedResult, setSelectedResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [showCreateConfig, setShowCreateConfig] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [showAutoRange, setShowAutoRange] = useState(false);
  const [compareIds, setCompareIds] = useState([]);
  const [vllmStatus, setVllmStatus] = useState(null);
  const [autoRangeSessions, setAutoRangeSessions] = useState([]);
  const [selectedAutoSession, setSelectedAutoSession] = useState(null);
  const [newConfig, setNewConfig] = useState({
    name: '',
    model: 'facebook/opt-125m',
    max_tokens: 100,
    temperature: 0.7,
    top_p: 0.9,
    num_requests: 10,
    concurrent_requests: 1,
    test_prompts: [
      "Explain quantum computing in simple terms.",
      "Write a short poem about artificial intelligence.",
      "What are the benefits of renewable energy?"
    ],
    // vLLM 런타임 파라미터
    gpu_memory_utilization: null,
    quantization: null,
    tensor_parallel_size: null,
    max_model_len: null,
    dtype: null,
    enforce_eager: false
  });
  const [autoRangeConfig, setAutoRangeConfig] = useState({
    name: '',
    model: 'facebook/opt-125m',
    num_requests: 10,
    max_tokens_range: [32, 512, 128],
    concurrent_range: [1, 8, 2],
    temperature_range: null,
    gpu_memory_utilization: null,
    quantization: null,
    test_prompts: [
      "Explain quantum computing in simple terms.",
      "Write a short poem about artificial intelligence.",
      "What are the benefits of renewable energy?"
    ]
  });
  const [newPrompt, setNewPrompt] = useState('');

  // vLLM 상태 확인
  const fetchVllmStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/benchmark/vllm-status`);
      setVllmStatus(res.data);
    } catch (error) {
      setVllmStatus({ status: 'error', message: '상태 확인 실패', healthy: false });
    }
  }, []);

  // 데이터 로드
  const fetchData = useCallback(async () => {
    try {
      const [configsRes, resultsRes, autoRangeRes] = await Promise.all([
        axios.get(`${API_BASE}/benchmark/configs`),
        axios.get(`${API_BASE}/benchmark/results`),
        axios.get(`${API_BASE}/benchmark/auto-range`)
      ]);
      setConfigs(configsRes.data.configs || []);
      setResults(resultsRes.data.results || []);
      setAutoRangeSessions(autoRangeRes.data.sessions || []);
      setLoading(false);
    } catch (error) {
      console.error('Benchmark fetch error:', error);
      setLoading(false);
    }
    // vLLM 상태도 확인
    fetchVllmStatus();
  }, [fetchVllmStatus]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 설정 생성
  const handleCreateConfig = async () => {
    if (!newConfig.name.trim()) {
      showToast('설정 이름을 입력하세요', 'error');
      return;
    }
    try {
      await axios.post(`${API_BASE}/benchmark/configs`, newConfig);
      showToast(`설정 '${newConfig.name}'이 생성되었습니다`);
      setShowCreateConfig(false);
      setNewConfig({
        name: '',
        model: 'facebook/opt-125m',
        max_tokens: 100,
        temperature: 0.7,
        top_p: 0.9,
        num_requests: 10,
        concurrent_requests: 1,
        test_prompts: [
          "Explain quantum computing in simple terms.",
          "Write a short poem about artificial intelligence.",
          "What are the benefits of renewable energy?"
        ]
      });
      fetchData();
    } catch (error) {
      showToast(error.response?.data?.detail || '설정 생성 실패', 'error');
    }
  };

  // 벤치마크 실행
  const handleRunBenchmark = async (configId) => {
    // vLLM 상태 확인
    if (!vllmStatus?.healthy) {
      showToast(`vLLM 서비스가 준비되지 않았습니다: ${vllmStatus?.message || '상태 확인 필요'}`, 'error');
      return;
    }

    setRunning(true);
    try {
      const res = await axios.post(`${API_BASE}/benchmark/run`, { config_id: configId });
      if (res.data.status === 'completed') {
        showToast('벤치마크가 완료되었습니다');
        setSelectedResult(res.data.result_id);
      } else if (res.data.status === 'failed') {
        showToast(`벤치마크 실패: ${res.data.error}`, 'error');
      }
      fetchData();
    } catch (error) {
      showToast(error.response?.data?.detail || '벤치마크 실행 실패', 'error');
    } finally {
      setRunning(false);
    }
  };

  // 결과 상세 조회
  const handleViewResult = async (resultId) => {
    try {
      const res = await axios.get(`${API_BASE}/benchmark/results/${resultId}`);
      setSelectedResult(res.data);
    } catch (error) {
      showToast('결과 조회 실패', 'error');
    }
  };

  // 설정 삭제
  const handleDeleteConfig = async (configId) => {
    try {
      await axios.delete(`${API_BASE}/benchmark/configs/${configId}`);
      showToast('설정이 삭제되었습니다');
      fetchData();
    } catch (error) {
      showToast('설정 삭제 실패', 'error');
    }
  };

  // 결과 삭제
  const handleDeleteResult = async (resultId) => {
    try {
      await axios.delete(`${API_BASE}/benchmark/results/${resultId}`);
      showToast('결과가 삭제되었습니다');
      if (selectedResult?.id === resultId) {
        setSelectedResult(null);
      }
      fetchData();
    } catch (error) {
      showToast('결과 삭제 실패', 'error');
    }
  };

  // 프롬프트 추가
  const handleAddPrompt = () => {
    if (newPrompt.trim()) {
      setNewConfig({
        ...newConfig,
        test_prompts: [...newConfig.test_prompts, newPrompt.trim()]
      });
      setNewPrompt('');
    }
  };

  // 프롬프트 삭제
  const handleRemovePrompt = (index) => {
    setNewConfig({
      ...newConfig,
      test_prompts: newConfig.test_prompts.filter((_, i) => i !== index)
    });
  };

  // 비교 토글
  const toggleCompare = (resultId) => {
    if (compareIds.includes(resultId)) {
      setCompareIds(compareIds.filter(id => id !== resultId));
    } else if (compareIds.length < 4) {
      setCompareIds([...compareIds, resultId]);
    }
  };

  // 자동 범위 벤치마크 실행
  const handleRunAutoRange = async () => {
    if (!autoRangeConfig.name.trim()) {
      showToast('벤치마크 이름을 입력하세요', 'error');
      return;
    }
    if (!vllmStatus?.healthy) {
      showToast(`vLLM 서비스가 준비되지 않았습니다: ${vllmStatus?.message || '상태 확인 필요'}`, 'error');
      return;
    }
    try {
      const res = await axios.post(`${API_BASE}/benchmark/auto-range`, autoRangeConfig);
      showToast(`자동 범위 벤치마크가 시작되었습니다. ${res.data.total_tests}개의 테스트를 실행합니다.`);
      setShowAutoRange(false);
      fetchData();
    } catch (error) {
      showToast(error.response?.data?.detail || '자동 범위 벤치마크 시작 실패', 'error');
    }
  };

  // 자동 범위 세션 상세 조회
  const handleViewAutoSession = async (sessionId) => {
    try {
      const res = await axios.get(`${API_BASE}/benchmark/auto-range/${sessionId}`);
      setSelectedAutoSession(res.data);
    } catch (error) {
      showToast('세션 조회 실패', 'error');
    }
  };

  // 자동 범위 세션 삭제
  const handleDeleteAutoSession = async (sessionId) => {
    try {
      await axios.delete(`${API_BASE}/benchmark/auto-range/${sessionId}`);
      showToast('세션이 삭제되었습니다');
      if (selectedAutoSession?.id === sessionId) {
        setSelectedAutoSession(null);
      }
      fetchData();
    } catch (error) {
      showToast('세션 삭제 실패', 'error');
    }
  };

  if (loading) {
    return (
      <section className="section">
        <div className="card">
          <div className="loading-container">
            <div className="spinner large"></div>
            <p>벤치마크 정보를 불러오는 중...</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="section benchmark-section">
      {/* Header */}
      <div className="benchmark-header">
        <div className="benchmark-title">
          <BarChart3 size={24} />
          <h2>LLM Benchmark</h2>
        </div>
        <div className="benchmark-actions">
          <button className="btn btn-outline" onClick={fetchData}>
            <RefreshCw size={16} />
          </button>
          <button className="btn btn-secondary" onClick={() => setShowAutoRange(true)}>
            <Zap size={16} /> 자동 범위
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreateConfig(true)}>
            <Plus size={16} /> 새 설정
          </button>
        </div>
      </div>

      {/* vLLM Status */}
      {vllmStatus && (
        <div className={`vllm-status ${vllmStatus.healthy ? 'online' : 'offline'}`}>
          <div className="vllm-status-dot"></div>
          <span className="vllm-status-text">
            vLLM: {vllmStatus.message}
            {vllmStatus.models && vllmStatus.models.length > 0 && (
              <span style={{ marginLeft: 8, color: 'var(--text-muted)' }}>
                (모델: {vllmStatus.models.join(', ')})
              </span>
            )}
          </span>
          {!vllmStatus.healthy && (
            <button
              className="btn btn-outline btn-sm"
              onClick={fetchVllmStatus}
              style={{ marginLeft: 'auto' }}
            >
              <RefreshCw size={14} />
            </button>
          )}
        </div>
      )}

      <div className="benchmark-layout">
        {/* Left: Configs */}
        <div className="benchmark-configs-panel">
          <div className="panel-header">
            <Settings size={18} />
            <h3>벤치마크 설정</h3>
          </div>
          <div className="config-list">
            {configs.map((config) => (
              <div
                key={config.id}
                className={`config-card ${selectedConfig?.id === config.id ? 'selected' : ''}`}
                onClick={() => setSelectedConfig(config)}
              >
                <div className="config-card-header">
                  <div className="config-card-title">
                    <span className="config-name">{config.name}</span>
                    {config.id.startsWith('default') && (
                      <span className="config-badge default">기본</span>
                    )}
                  </div>
                  <div className="config-card-actions">
                    <button
                      className="config-run-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRunBenchmark(config.id);
                      }}
                      disabled={running}
                      title="벤치마크 실행"
                    >
                      {running ? <Loader2 className="spin" size={16} /> : <PlayCircle size={16} />}
                    </button>
                    {!config.id.startsWith('default') && (
                      <button
                        className="config-delete-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteConfig(config.id);
                        }}
                        title="삭제"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
                <div className="config-card-model">
                  <Cpu size={14} />
                  <span>{config.model}</span>
                </div>
                <div className="config-card-params">
                  <div className="param-item">
                    <span className="param-label">요청 수</span>
                    <span className="param-value">{config.num_requests}</span>
                  </div>
                  <div className="param-item">
                    <span className="param-label">최대 토큰</span>
                    <span className="param-value">{config.max_tokens}</span>
                  </div>
                  <div className="param-item">
                    <span className="param-label">동시성</span>
                    <span className="param-value">{config.concurrent_requests}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center: Results List */}
        <div className="benchmark-results-panel">
          <div className="panel-header">
            <TrendingUp size={18} />
            <h3>실행 결과</h3>
            {compareIds.length > 0 && (
              <button
                className="btn btn-primary btn-sm"
                onClick={() => setShowCompare(true)}
              >
                비교 ({compareIds.length})
              </button>
            )}
          </div>
          <div className="results-list">
            {results.length === 0 ? (
              <div className="empty-state">
                <BarChart3 size={32} color="var(--text-muted)" />
                <p>실행된 벤치마크가 없습니다</p>
              </div>
            ) : (
              results.map((result) => (
                <div
                  key={result.id}
                  className={`result-card ${selectedResult?.id === result.id ? 'selected' : ''}`}
                  onClick={() => handleViewResult(result.id)}
                >
                  <div className="result-card-header">
                    <label className="result-checkbox" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={compareIds.includes(result.id)}
                        onChange={() => toggleCompare(result.id)}
                      />
                      <span className="checkmark"></span>
                    </label>
                    <div className="result-card-info">
                      <span className="result-name">{result.config_name}</span>
                      <span className="result-time">
                        <Clock size={12} />
                        {new Date(result.started_at).toLocaleString()}
                      </span>
                    </div>
                    <button
                      className="result-delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteResult(result.id);
                      }}
                      title="삭제"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="result-card-body">
                    {result.status === 'completed' ? (
                      <div className="result-metrics">
                        <div className="result-metric">
                          <Timer size={14} />
                          <span className="metric-value">{result.summary?.avg_latency?.toFixed(2)}</span>
                          <span className="metric-unit">초</span>
                        </div>
                        <div className="result-metric success">
                          <Target size={14} />
                          <span className="metric-value">{result.summary?.success_rate}</span>
                          <span className="metric-unit">%</span>
                        </div>
                        <div className="result-metric">
                          <TrendingUp size={14} />
                          <span className="metric-value">{result.summary?.avg_tokens_per_second?.toFixed(1)}</span>
                          <span className="metric-unit">t/s</span>
                        </div>
                      </div>
                    ) : result.status === 'running' ? (
                      <div className="result-status running">
                        <Loader2 className="spin" size={16} />
                        <span>벤치마크 실행 중...</span>
                      </div>
                    ) : (
                      <div className="result-status failed">
                        <AlertCircle size={16} />
                        <span>실행 실패</span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Result Detail */}
        <div className="benchmark-detail-panel">
          {selectedResult ? (
            <>
              <div className="panel-header">
                <h3>{selectedResult.config_name}</h3>
                <span className={`status-badge ${selectedResult.status}`}>
                  {selectedResult.status === 'completed' ? '완료' :
                   selectedResult.status === 'running' ? '실행 중' : '실패'}
                </span>
              </div>

              {selectedResult.summary && (
                <div className="result-detail-content">
                  {/* Summary Stats */}
                  <div className="summary-grid">
                    <div className="summary-card">
                      <span className="summary-label">총 요청</span>
                      <span className="summary-value">{selectedResult.summary.total_requests}</span>
                    </div>
                    <div className="summary-card">
                      <span className="summary-label">성공률</span>
                      <span className="summary-value success">{selectedResult.summary.success_rate}%</span>
                    </div>
                    <div className="summary-card">
                      <span className="summary-label">평균 지연</span>
                      <span className="summary-value">{selectedResult.summary.avg_latency?.toFixed(3)}s</span>
                    </div>
                    <div className="summary-card">
                      <span className="summary-label">Tokens/sec</span>
                      <span className="summary-value">{selectedResult.summary.avg_tokens_per_second?.toFixed(1)}</span>
                    </div>
                  </div>

                  {/* Latency Stats */}
                  <div className="latency-stats">
                    <h4>지연 시간 분포</h4>
                    <div className="latency-grid">
                      <div className="latency-item">
                        <span>Min</span>
                        <span>{selectedResult.summary.min_latency?.toFixed(3)}s</span>
                      </div>
                      <div className="latency-item">
                        <span>P50</span>
                        <span>{selectedResult.summary.p50_latency?.toFixed(3)}s</span>
                      </div>
                      <div className="latency-item">
                        <span>P95</span>
                        <span>{selectedResult.summary.p95_latency?.toFixed(3) || '-'}s</span>
                      </div>
                      <div className="latency-item">
                        <span>Max</span>
                        <span>{selectedResult.summary.max_latency?.toFixed(3)}s</span>
                      </div>
                    </div>
                  </div>

                  {/* Settings */}
                  <div className="settings-summary">
                    <h4>설정</h4>
                    <div className="settings-grid">
                      <span>Model: {selectedResult.model}</span>
                      <span>Max Tokens: {selectedResult.settings?.max_tokens}</span>
                      <span>Temperature: {selectedResult.settings?.temperature}</span>
                      <span>Concurrent: {selectedResult.settings?.concurrent_requests}</span>
                    </div>
                  </div>

                  {/* Request Details */}
                  {selectedResult.requests && selectedResult.requests.length > 0 && (
                    <div className="requests-detail">
                      <h4>요청 상세 ({selectedResult.requests.length}개)</h4>
                      <div className="requests-table">
                        <table>
                          <thead>
                            <tr>
                              <th>#</th>
                              <th>Prompt</th>
                              <th>Latency</th>
                              <th>Tokens</th>
                              <th>T/s</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedResult.requests.slice(0, 20).map((req, idx) => (
                              <tr key={idx} className={req.success ? '' : 'failed'}>
                                <td>{idx + 1}</td>
                                <td className="prompt-cell">{req.prompt}</td>
                                <td>{req.latency.toFixed(3)}s</td>
                                <td>{req.output_tokens}</td>
                                <td>{req.tokens_per_second.toFixed(1)}</td>
                                <td>
                                  {req.success ? (
                                    <CheckCircle size={14} color="var(--accent-green)" />
                                  ) : (
                                    <AlertCircle size={14} color="var(--accent-red)" />
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {selectedResult.requests.length > 20 && (
                          <p className="more-results">...외 {selectedResult.requests.length - 20}개</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedResult.error && (
                <div className="error-message">
                  <AlertCircle size={20} />
                  <p>{selectedResult.error}</p>
                </div>
              )}
            </>
          ) : (
            <div className="no-selection">
              <BarChart3 size={48} color="var(--text-muted)" />
              <p>결과를 선택하세요</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Config Modal */}
      {showCreateConfig && (
        <div className="modal-overlay" onClick={() => setShowCreateConfig(false)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>새 벤치마크 설정</h3>
              <button className="btn-icon" onClick={() => setShowCreateConfig(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-row">
                <div className="form-group">
                  <label>설정 이름</label>
                  <input
                    type="text"
                    value={newConfig.name}
                    onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
                    placeholder="My Benchmark"
                  />
                </div>
                <div className="form-group">
                  <label>모델</label>
                  <input
                    type="text"
                    value={newConfig.model}
                    onChange={(e) => setNewConfig({ ...newConfig, model: e.target.value })}
                    placeholder="facebook/opt-125m"
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Max Tokens</label>
                  <input
                    type="number"
                    value={newConfig.max_tokens}
                    onChange={(e) => setNewConfig({ ...newConfig, max_tokens: parseInt(e.target.value) || 100 })}
                  />
                </div>
                <div className="form-group">
                  <label>Temperature</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newConfig.temperature}
                    onChange={(e) => setNewConfig({ ...newConfig, temperature: parseFloat(e.target.value) || 0.7 })}
                  />
                </div>
                <div className="form-group">
                  <label>Top P</label>
                  <input
                    type="number"
                    step="0.05"
                    value={newConfig.top_p}
                    onChange={(e) => setNewConfig({ ...newConfig, top_p: parseFloat(e.target.value) || 0.9 })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>요청 수</label>
                  <input
                    type="number"
                    value={newConfig.num_requests}
                    onChange={(e) => setNewConfig({ ...newConfig, num_requests: parseInt(e.target.value) || 10 })}
                  />
                </div>
                <div className="form-group">
                  <label>동시 요청 수</label>
                  <input
                    type="number"
                    value={newConfig.concurrent_requests}
                    onChange={(e) => setNewConfig({ ...newConfig, concurrent_requests: parseInt(e.target.value) || 1 })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>테스트 프롬프트</label>
                <div className="prompts-list">
                  {newConfig.test_prompts.map((prompt, idx) => (
                    <div key={idx} className="prompt-item">
                      <span>{prompt}</span>
                      <button
                        className="btn-icon danger"
                        onClick={() => handleRemovePrompt(idx)}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
                <div className="add-prompt">
                  <input
                    type="text"
                    value={newPrompt}
                    onChange={(e) => setNewPrompt(e.target.value)}
                    placeholder="새 프롬프트 입력..."
                    onKeyPress={(e) => e.key === 'Enter' && handleAddPrompt()}
                  />
                  <button className="btn btn-outline" onClick={handleAddPrompt}>
                    <Plus size={16} />
                  </button>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setShowCreateConfig(false)}>취소</button>
              <button className="btn btn-primary" onClick={handleCreateConfig}>생성</button>
            </div>
          </div>
        </div>
      )}

      {/* Compare Modal */}
      {showCompare && compareIds.length > 0 && (
        <div className="modal-overlay" onClick={() => setShowCompare(false)}>
          <div className="modal modal-xl" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>벤치마크 결과 비교</h3>
              <button className="btn-icon" onClick={() => setShowCompare(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="compare-grid">
                <div className="compare-header">
                  <div className="compare-metric">Metric</div>
                  {results
                    .filter(r => compareIds.includes(r.id))
                    .map(r => (
                      <div key={r.id} className="compare-value">
                        <strong>{r.config_name}</strong>
                        <small>{new Date(r.started_at).toLocaleDateString()}</small>
                      </div>
                    ))}
                </div>
                <div className="compare-row">
                  <div className="compare-metric">성공률</div>
                  {results
                    .filter(r => compareIds.includes(r.id))
                    .map(r => (
                      <div key={r.id} className="compare-value">
                        {r.summary?.success_rate}%
                      </div>
                    ))}
                </div>
                <div className="compare-row">
                  <div className="compare-metric">평균 지연</div>
                  {results
                    .filter(r => compareIds.includes(r.id))
                    .map(r => (
                      <div key={r.id} className="compare-value">
                        {r.summary?.avg_latency?.toFixed(3)}s
                      </div>
                    ))}
                </div>
                <div className="compare-row">
                  <div className="compare-metric">P50 지연</div>
                  {results
                    .filter(r => compareIds.includes(r.id))
                    .map(r => (
                      <div key={r.id} className="compare-value">
                        {r.summary?.p50_latency?.toFixed(3)}s
                      </div>
                    ))}
                </div>
                <div className="compare-row">
                  <div className="compare-metric">Tokens/sec</div>
                  {results
                    .filter(r => compareIds.includes(r.id))
                    .map(r => (
                      <div key={r.id} className="compare-value">
                        {r.summary?.avg_tokens_per_second?.toFixed(1)}
                      </div>
                    ))}
                </div>
                <div className="compare-row">
                  <div className="compare-metric">총 토큰</div>
                  {results
                    .filter(r => compareIds.includes(r.id))
                    .map(r => (
                      <div key={r.id} className="compare-value">
                        {r.summary?.total_output_tokens}
                      </div>
                    ))}
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setCompareIds([])}>선택 초기화</button>
              <button className="btn btn-primary" onClick={() => setShowCompare(false)}>닫기</button>
            </div>
          </div>
        </div>
      )}

      {/* Auto Range Benchmark Modal */}
      {showAutoRange && (
        <div className="modal-overlay" onClick={() => setShowAutoRange(false)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3><Zap size={20} /> 자동 범위 벤치마크</h3>
              <button className="btn-icon" onClick={() => setShowAutoRange(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-description">
                파라미터 범위를 자동으로 순회하며 최적의 설정을 찾습니다.
              </p>

              <div className="form-row">
                <div className="form-group">
                  <label>벤치마크 이름</label>
                  <input
                    type="text"
                    value={autoRangeConfig.name}
                    onChange={(e) => setAutoRangeConfig({ ...autoRangeConfig, name: e.target.value })}
                    placeholder="Auto Range Test"
                  />
                </div>
                <div className="form-group">
                  <label>모델</label>
                  <input
                    type="text"
                    value={autoRangeConfig.model}
                    onChange={(e) => setAutoRangeConfig({ ...autoRangeConfig, model: e.target.value })}
                    placeholder="facebook/opt-125m"
                  />
                </div>
              </div>

              <div className="form-section">
                <h4>파라미터 범위 설정</h4>
                <p className="form-hint">각 파라미터의 [최소값, 최대값, 증가폭]을 설정합니다.</p>

                <div className="range-settings">
                  <div className="range-item">
                    <label>
                      <input
                        type="checkbox"
                        checked={autoRangeConfig.max_tokens_range !== null}
                        onChange={(e) => setAutoRangeConfig({
                          ...autoRangeConfig,
                          max_tokens_range: e.target.checked ? [32, 512, 128] : null
                        })}
                      />
                      Max Tokens
                    </label>
                    {autoRangeConfig.max_tokens_range && (
                      <div className="range-inputs">
                        <input
                          type="number"
                          value={autoRangeConfig.max_tokens_range[0]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            max_tokens_range: [parseInt(e.target.value) || 32, autoRangeConfig.max_tokens_range[1], autoRangeConfig.max_tokens_range[2]]
                          })}
                          placeholder="최소"
                        />
                        <span>~</span>
                        <input
                          type="number"
                          value={autoRangeConfig.max_tokens_range[1]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            max_tokens_range: [autoRangeConfig.max_tokens_range[0], parseInt(e.target.value) || 512, autoRangeConfig.max_tokens_range[2]]
                          })}
                          placeholder="최대"
                        />
                        <span>step:</span>
                        <input
                          type="number"
                          value={autoRangeConfig.max_tokens_range[2]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            max_tokens_range: [autoRangeConfig.max_tokens_range[0], autoRangeConfig.max_tokens_range[1], parseInt(e.target.value) || 64]
                          })}
                          placeholder="증가폭"
                        />
                      </div>
                    )}
                  </div>

                  <div className="range-item">
                    <label>
                      <input
                        type="checkbox"
                        checked={autoRangeConfig.concurrent_range !== null}
                        onChange={(e) => setAutoRangeConfig({
                          ...autoRangeConfig,
                          concurrent_range: e.target.checked ? [1, 8, 2] : null
                        })}
                      />
                      동시 요청 수
                    </label>
                    {autoRangeConfig.concurrent_range && (
                      <div className="range-inputs">
                        <input
                          type="number"
                          value={autoRangeConfig.concurrent_range[0]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            concurrent_range: [parseInt(e.target.value) || 1, autoRangeConfig.concurrent_range[1], autoRangeConfig.concurrent_range[2]]
                          })}
                          placeholder="최소"
                        />
                        <span>~</span>
                        <input
                          type="number"
                          value={autoRangeConfig.concurrent_range[1]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            concurrent_range: [autoRangeConfig.concurrent_range[0], parseInt(e.target.value) || 8, autoRangeConfig.concurrent_range[2]]
                          })}
                          placeholder="최대"
                        />
                        <span>step:</span>
                        <input
                          type="number"
                          value={autoRangeConfig.concurrent_range[2]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            concurrent_range: [autoRangeConfig.concurrent_range[0], autoRangeConfig.concurrent_range[1], parseInt(e.target.value) || 1]
                          })}
                          placeholder="증가폭"
                        />
                      </div>
                    )}
                  </div>

                  <div className="range-item">
                    <label>
                      <input
                        type="checkbox"
                        checked={autoRangeConfig.temperature_range !== null}
                        onChange={(e) => setAutoRangeConfig({
                          ...autoRangeConfig,
                          temperature_range: e.target.checked ? [0.1, 1.0, 0.3] : null
                        })}
                      />
                      Temperature
                    </label>
                    {autoRangeConfig.temperature_range && (
                      <div className="range-inputs">
                        <input
                          type="number"
                          step="0.1"
                          value={autoRangeConfig.temperature_range[0]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            temperature_range: [parseFloat(e.target.value) || 0.1, autoRangeConfig.temperature_range[1], autoRangeConfig.temperature_range[2]]
                          })}
                          placeholder="최소"
                        />
                        <span>~</span>
                        <input
                          type="number"
                          step="0.1"
                          value={autoRangeConfig.temperature_range[1]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            temperature_range: [autoRangeConfig.temperature_range[0], parseFloat(e.target.value) || 1.0, autoRangeConfig.temperature_range[2]]
                          })}
                          placeholder="최대"
                        />
                        <span>step:</span>
                        <input
                          type="number"
                          step="0.1"
                          value={autoRangeConfig.temperature_range[2]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            temperature_range: [autoRangeConfig.temperature_range[0], autoRangeConfig.temperature_range[1], parseFloat(e.target.value) || 0.1]
                          })}
                          placeholder="증가폭"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="form-section">
                <h4>vLLM 파라미터 (선택)</h4>
                <div className="form-row">
                  <div className="form-group">
                    <label>GPU Memory Utilization</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0.1"
                      max="0.95"
                      value={autoRangeConfig.gpu_memory_utilization || ''}
                      onChange={(e) => setAutoRangeConfig({
                        ...autoRangeConfig,
                        gpu_memory_utilization: e.target.value ? parseFloat(e.target.value) : null
                      })}
                      placeholder="0.9 (기본)"
                    />
                  </div>
                  <div className="form-group">
                    <label>Quantization</label>
                    <select
                      value={autoRangeConfig.quantization || ''}
                      onChange={(e) => setAutoRangeConfig({
                        ...autoRangeConfig,
                        quantization: e.target.value || null
                      })}
                    >
                      <option value="">없음</option>
                      <option value="awq">AWQ</option>
                      <option value="gptq">GPTQ</option>
                      <option value="squeezellm">SqueezeLLM</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>테스트당 요청 수</label>
                  <input
                    type="number"
                    value={autoRangeConfig.num_requests}
                    onChange={(e) => setAutoRangeConfig({
                      ...autoRangeConfig,
                      num_requests: parseInt(e.target.value) || 10
                    })}
                  />
                </div>
              </div>

              {/* 자동 범위 세션 목록 */}
              {autoRangeSessions.length > 0 && (
                <div className="form-section">
                  <h4>이전 자동 범위 벤치마크</h4>
                  <div className="auto-sessions-list">
                    {autoRangeSessions.slice(0, 5).map(session => (
                      <div key={session.id} className="auto-session-item" onClick={() => handleViewAutoSession(session.id)}>
                        <div className="session-info">
                          <span className="session-name">{session.name}</span>
                          <span className={`session-status ${session.status}`}>
                            {session.status === 'running' ? (
                              <><Loader2 className="spin" size={12} /> 실행 중 ({session.completed_tests}/{session.total_tests})</>
                            ) : session.status === 'completed' ? '완료' : '실패'}
                          </span>
                        </div>
                        {session.best_performance && (
                          <div className="session-best">
                            최적: {session.best_performance.avg_tokens_per_second?.toFixed(1)} t/s
                          </div>
                        )}
                        <button
                          className="btn-icon danger"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteAutoSession(session.id);
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setShowAutoRange(false)}>취소</button>
              <button className="btn btn-primary" onClick={handleRunAutoRange}>
                <Zap size={16} /> 벤치마크 시작
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Auto Range Session Detail Modal */}
      {selectedAutoSession && (
        <div className="modal-overlay" onClick={() => setSelectedAutoSession(null)}>
          <div className="modal modal-xl" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedAutoSession.name} - 자동 범위 결과</h3>
              <button className="btn-icon" onClick={() => setSelectedAutoSession(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="auto-session-summary">
                <div className="summary-item">
                  <span className="summary-label">상태</span>
                  <span className={`summary-value status-${selectedAutoSession.status}`}>
                    {selectedAutoSession.status === 'running' ? '실행 중' : selectedAutoSession.status === 'completed' ? '완료' : '실패'}
                  </span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">진행</span>
                  <span className="summary-value">{selectedAutoSession.completed_tests} / {selectedAutoSession.total_tests}</span>
                </div>
                {selectedAutoSession.best_params && (
                  <>
                    <div className="summary-item highlight">
                      <span className="summary-label">최적 설정</span>
                      <span className="summary-value">
                        max_tokens: {selectedAutoSession.best_params.max_tokens},
                        concurrent: {selectedAutoSession.best_params.concurrent_requests}
                      </span>
                    </div>
                    <div className="summary-item highlight">
                      <span className="summary-label">최고 성능</span>
                      <span className="summary-value success">
                        {selectedAutoSession.best_performance?.avg_tokens_per_second?.toFixed(1)} tokens/sec
                      </span>
                    </div>
                  </>
                )}
              </div>

              {selectedAutoSession.results && selectedAutoSession.results.length > 0 && (
                <div className="auto-results-table">
                  <h4>테스트 결과</h4>
                  <table>
                    <thead>
                      <tr>
                        <th>테스트 유형</th>
                        <th>Max Tokens</th>
                        <th>Concurrent</th>
                        <th>Temperature</th>
                        <th>성공률</th>
                        <th>평균 지연</th>
                        <th>Tokens/sec</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedAutoSession.results.map((result, idx) => (
                        <tr key={idx} className={result.summary?.avg_tokens_per_second === selectedAutoSession.best_performance?.avg_tokens_per_second ? 'best' : ''}>
                          <td>{result.params.test_type}</td>
                          <td>{result.params.max_tokens}</td>
                          <td>{result.params.concurrent_requests}</td>
                          <td>{result.params.temperature?.toFixed(1)}</td>
                          <td>{result.summary?.success_rate || 0}%</td>
                          <td>{result.summary?.avg_latency?.toFixed(3) || '-'}s</td>
                          <td className={result.summary?.avg_tokens_per_second === selectedAutoSession.best_performance?.avg_tokens_per_second ? 'highlight' : ''}>
                            {result.summary?.avg_tokens_per_second?.toFixed(1) || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={() => setSelectedAutoSession(null)}>닫기</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

// 워크로드가 준비 중인지 확인하는 헬퍼 함수
const isWorkloadPreparing = (workload, isLoading) => {
  const isStarting = workload?.replicas > 0 && workload?.ready_replicas === 0;
  return isLoading || isStarting;
};

// 워크로드 상태 배지 컴포넌트
const WorkloadStatusBadge = ({ workload, isLoading, actionType }) => {
  const isPreparing = isWorkloadPreparing(workload, isLoading && actionType !== 'stop');

  // 중지 중 상태
  if (isLoading && actionType === 'stop') {
    return (
      <span className="workload-status stopping">
        <div className="workload-spinner"></div>
        종료 중
      </span>
    );
  }

  if (isPreparing) {
    return (
      <span className="workload-status preparing">
        <div className="workload-spinner"></div>
        준비 중
      </span>
    );
  }

  const status = workload?.status || 'not_deployed';
  const statusText = {
    running: '실행중',
    stopped: '중지됨',
    not_deployed: '미배포'
  }[status] || status;

  return (
    <span className={`workload-status ${status}`}>
      {statusText}
    </span>
  );
};

// 실시간 임베딩 데모 컴포넌트
const EmbeddingLiveDemo = () => {
  const [inputText, setInputText] = useState('');
  const [compareText1, setCompareText1] = useState('');
  const [compareText2, setCompareText2] = useState('');
  const [selectedModel, setSelectedModel] = useState('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2');
  const [embeddingResult, setEmbeddingResult] = useState(null);
  const [compareResult, setCompareResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isComparing, setIsComparing] = useState(false);
  const [activeTab, setActiveTab] = useState('single'); // single, compare, storage
  const [modelStatus, setModelStatus] = useState({}); // 모델 로딩 상태
  const [isLoadingModel, setIsLoadingModel] = useState(false);

  const models = [
    { id: 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', name: 'MiniLM (다국어, 권장)', dim: 384, sparse: false, size: '480MB' },
    { id: 'BAAI/bge-m3', name: 'BGE-M3', dim: 1024, sparse: true, size: '2.2GB' },
    { id: 'intfloat/multilingual-e5-large', name: 'E5-Large (다국어)', dim: 1024, sparse: false, size: '2.1GB' },
    { id: 'jhgan/ko-sroberta-multitask', name: 'Ko-SROBERTA (한국어)', dim: 768, sparse: false, size: '1.1GB' },
    { id: 'nlpai-lab/KURE-v1', name: 'KURE (한국어 특화)', dim: 1024, sparse: false, size: '1.5GB' },
    { id: 'BAAI/bge-small-en-v1.5', name: 'BGE-Small (영어)', dim: 384, sparse: false, size: '130MB' },
  ];

  // 모델 상태 조회
  const fetchModelStatus = async () => {
    try {
      const response = await axios.get('/api/embedding/models');
      setModelStatus(response.data.models || {});
    } catch (error) {
      console.error('Failed to fetch model status:', error);
    }
  };

  // 모델 로드
  const loadModel = async (modelId) => {
    setIsLoadingModel(true);
    try {
      await axios.post(`/api/embedding/models/${encodeURIComponent(modelId)}/load`);
      // 상태 폴링
      let attempts = 0;
      const poll = setInterval(async () => {
        try {
          const res = await axios.get(`/api/embedding/models/${encodeURIComponent(modelId)}/status`);
          if (res.data.loaded) {
            clearInterval(poll);
            setIsLoadingModel(false);
            fetchModelStatus();
          }
          attempts++;
          if (attempts > 60) { // 5분 타임아웃
            clearInterval(poll);
            setIsLoadingModel(false);
          }
        } catch (e) {
          clearInterval(poll);
          setIsLoadingModel(false);
        }
      }, 5000);
    } catch (error) {
      console.error('Failed to load model:', error);
      setIsLoadingModel(false);
    }
  };

  // 초기 모델 상태 로드
  useEffect(() => {
    fetchModelStatus();
  }, []);

  const runEmbedding = async () => {
    if (!inputText.trim()) return;
    setIsLoading(true);
    try {
      const response = await axios.post('/api/embedding/generate', {
        text: inputText,
        model: selectedModel,
        return_sparse: true,
        return_dense: true
      });
      setEmbeddingResult(response.data);
    } catch (error) {
      console.error('Embedding error:', error);
      setEmbeddingResult({ error: error.message });
    }
    setIsLoading(false);
  };

  const runCompare = async () => {
    if (!compareText1.trim() || !compareText2.trim()) return;
    setIsComparing(true);
    try {
      const response = await axios.post('/api/embedding/compare', {
        text1: compareText1,
        text2: compareText2,
        model: selectedModel
      });
      setCompareResult(response.data);
    } catch (error) {
      console.error('Compare error:', error);
      setCompareResult({ error: error.message });
    }
    setIsComparing(false);
  };

  // 관련 있는 텍스트 쌍
  const relatedTexts = [
    { text: '쿠버네티스에서 파드를 스케일링하는 방법', category: 'K8s' },
    { text: 'K3s 클러스터에서 HPA로 오토스케일링 설정하기', category: 'K8s' },
  ];

  // 관련 없는 텍스트 쌍
  const unrelatedTexts = [
    { text: '오늘 서울 날씨가 맑고 좋습니다', category: '날씨' },
    { text: '맛있는 피자 레시피와 토핑 추천', category: '요리' },
  ];

  const sampleTexts = [
    '쿠버네티스에서 파드를 스케일링하는 방법',
    'K3s 클러스터에서 HPA로 오토스케일링 설정하기',
    '오늘 서울 날씨가 맑고 좋습니다',
    '맛있는 피자 레시피와 토핑 추천',
    'GPU를 사용하여 딥러닝 모델을 학습시키는 방법'
  ];

  return (
    <div className="card embedding-live-demo-card" style={{ marginTop: '20px' }}>
      <div className="card-header">
        <h3><PlayCircle size={18} /> 실시간 임베딩 실행</h3>
        <div className="demo-tabs">
          <button
            className={`demo-tab ${activeTab === 'single' ? 'active' : ''}`}
            onClick={() => setActiveTab('single')}
          >
            단일 임베딩
          </button>
          <button
            className={`demo-tab ${activeTab === 'compare' ? 'active' : ''}`}
            onClick={() => setActiveTab('compare')}
          >
            유사도 비교
          </button>
          <button
            className={`demo-tab ${activeTab === 'storage' ? 'active' : ''}`}
            onClick={() => setActiveTab('storage')}
          >
            저장 형식
          </button>
        </div>
      </div>

      <div className="embedding-demo-content">
        {/* 모델 선택 및 상태 */}
        <div className="model-selector-enhanced">
          <div className="model-select-row">
            <label>임베딩 모델</label>
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              {models.map(m => {
                const status = modelStatus[m.id];
                const isLoaded = status?.loaded;
                return (
                  <option key={m.id} value={m.id}>
                    {isLoaded ? '✓ ' : ''}{m.name} ({m.dim}D, {m.size})
                  </option>
                );
              })}
            </select>
            {(() => {
              const currentStatus = modelStatus[selectedModel];
              const isLoaded = currentStatus?.loaded;
              const isDownloading = currentStatus?.status === 'downloading';
              if (isLoaded) {
                return <span className="model-status ready"><CheckCircle size={14} /> 준비됨</span>;
              } else if (isDownloading || isLoadingModel) {
                return <span className="model-status loading"><Loader2 size={14} className="spinning" /> 로딩중...</span>;
              } else {
                return (
                  <button
                    className="btn btn-sm btn-outline load-model-btn"
                    onClick={() => loadModel(selectedModel)}
                    disabled={isLoadingModel}
                  >
                    <Download size={14} /> 모델 로드
                  </button>
                );
              }
            })()}
          </div>
          <div className="model-info-row">
            {models.find(m => m.id === selectedModel)?.sparse && (
              <span className="feature-tag">Sparse 지원</span>
            )}
            <span className="model-size-info">
              {models.find(m => m.id === selectedModel)?.size}
            </span>
          </div>
        </div>

        {activeTab === 'single' && (
          <div className="single-embedding-demo">
            <div className="demo-input-section">
              <label>텍스트 입력</label>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="임베딩할 텍스트를 입력하세요..."
                rows={3}
              />
              <div className="sample-texts">
                <span className="sample-label">예시:</span>
                {sampleTexts.slice(0, 3).map((text, i) => (
                  <button key={i} className="sample-btn" onClick={() => setInputText(text)}>
                    {text.slice(0, 20)}...
                  </button>
                ))}
              </div>
              <button
                className="btn btn-primary"
                onClick={runEmbedding}
                disabled={isLoading || !inputText.trim()}
              >
                {isLoading ? <><Loader2 size={14} className="spinning" /> 처리중...</> : <><Play size={14} /> 임베딩 실행</>}
              </button>
            </div>

            {embeddingResult && !embeddingResult.error && (
              <div className="embedding-result">
                <div className="result-header">
                  <h4>임베딩 결과</h4>
                  <span className={`source-badge ${embeddingResult.source}`}>
                    {embeddingResult.source === 'cluster-gpu' ? 'GPU 서비스' :
                     embeddingResult.source === 'local-cpu' ? 'CPU 로컬' :
                     embeddingResult.source === 'live' ? '실제 서비스' : '시뮬레이션'}
                  </span>
                  <span className="processing-time">{embeddingResult.processing_time_ms}ms</span>
                </div>

                <div className="result-grid">
                  {/* Dense 벡터 */}
                  <div className="result-section dense-section">
                    <h5>Dense Embedding <span className="dim-badge">{embeddingResult.dimension}D</span></h5>
                    <p className="section-desc">의미 기반 검색에 사용되는 고밀도 벡터</p>
                    <div className="vector-preview">
                      <div className="vector-values">
                        {embeddingResult.dense_embedding.slice(0, 20).map((v, i) => (
                          <span
                            key={i}
                            className="vector-value"
                            style={{
                              backgroundColor: v > 0
                                ? `rgba(34, 197, 94, ${Math.min(Math.abs(v) * 2, 1)})`
                                : `rgba(239, 68, 68, ${Math.min(Math.abs(v) * 2, 1)})`
                            }}
                          >
                            {v.toFixed(3)}
                          </span>
                        ))}
                        <span className="vector-ellipsis">... ({embeddingResult.dimension - 20} more)</span>
                      </div>
                    </div>
                    <div className="vector-stats">
                      <span>Min: {Math.min(...embeddingResult.dense_embedding).toFixed(4)}</span>
                      <span>Max: {Math.max(...embeddingResult.dense_embedding).toFixed(4)}</span>
                      <span>L2 Norm: {Math.sqrt(embeddingResult.dense_embedding.reduce((a, b) => a + b*b, 0)).toFixed(4)}</span>
                    </div>
                    {/* 벡터 히트맵 시각화 */}
                    <div className="vector-heatmap">
                      <div className="heatmap-label">벡터 시각화 (처음 100차원)</div>
                      <div className="heatmap-grid">
                        {embeddingResult.dense_embedding.slice(0, 100).map((v, i) => (
                          <div
                            key={i}
                            className="heatmap-cell"
                            style={{
                              backgroundColor: v > 0
                                ? `rgba(59, 130, 246, ${Math.min(Math.abs(v) * 3, 1)})`
                                : `rgba(239, 68, 68, ${Math.min(Math.abs(v) * 3, 1)})`
                            }}
                            title={`[${i}]: ${v.toFixed(4)}`}
                          />
                        ))}
                      </div>
                      <div className="heatmap-legend">
                        <span className="legend-neg">음수</span>
                        <div className="legend-bar"></div>
                        <span className="legend-pos">양수</span>
                      </div>
                    </div>
                  </div>

                  {/* Sparse 벡터 */}
                  {Object.keys(embeddingResult.sparse_embedding || {}).length > 0 && (
                    <div className="result-section sparse-section">
                      <h5>Sparse Embedding <span className="dim-badge">{Object.keys(embeddingResult.sparse_embedding).length} tokens</span></h5>
                      <p className="section-desc">키워드 기반 검색에 사용되는 희소 벡터 (토큰 ID: 가중치)</p>
                      <div className="sparse-tokens">
                        {Object.entries(embeddingResult.sparse_embedding)
                          .sort((a, b) => b[1] - a[1])
                          .map(([tokenId, weight]) => (
                            <div key={tokenId} className="sparse-token">
                              <span className="token-id">#{tokenId}</span>
                              <div className="token-bar" style={{ width: `${weight * 100}%` }}></div>
                              <span className="token-weight">{weight.toFixed(4)}</span>
                            </div>
                          ))}
                      </div>
                      <div className="sparse-explanation">
                        <Info size={12} />
                        <span>Sparse 벡터는 BM25와 유사하게 특정 토큰의 중요도를 나타냅니다. Dense와 함께 사용하면 하이브리드 검색이 가능합니다.</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'compare' && (
          <div className="compare-embedding-demo">
            {/* 예제 선택 버튼들 */}
            <div className="example-pairs">
              <button
                className="pair-btn related"
                onClick={() => {
                  setCompareText1(relatedTexts[0].text);
                  setCompareText2(relatedTexts[1].text);
                }}
              >
                <span className="pair-icon">🔗</span>
                <span className="pair-label">관련 있는 텍스트 (K8s 스케일링)</span>
                <span className="expected-badge high">높은 유사도 예상</span>
              </button>
              <button
                className="pair-btn unrelated"
                onClick={() => {
                  setCompareText1(unrelatedTexts[0].text);
                  setCompareText2(unrelatedTexts[1].text);
                }}
              >
                <span className="pair-icon">❌</span>
                <span className="pair-label">관련 없는 텍스트 (날씨 vs 요리)</span>
                <span className="expected-badge low">낮은 유사도 예상</span>
              </button>
            </div>

            <div className="compare-inputs">
              <div className="compare-input">
                <label>텍스트 1</label>
                <textarea
                  value={compareText1}
                  onChange={(e) => setCompareText1(e.target.value)}
                  placeholder="첫 번째 텍스트..."
                  rows={2}
                />
                <div className="sample-btns">
                  {sampleTexts.slice(0, 2).map((text, i) => (
                    <button key={i} className="sample-btn" onClick={() => setCompareText1(text)}>예시 {i+1}</button>
                  ))}
                </div>
              </div>
              <div className="compare-input">
                <label>텍스트 2</label>
                <textarea
                  value={compareText2}
                  onChange={(e) => setCompareText2(e.target.value)}
                  placeholder="두 번째 텍스트..."
                  rows={2}
                />
                <div className="sample-btns">
                  {sampleTexts.slice(2, 4).map((text, i) => (
                    <button key={i} className="sample-btn" onClick={() => setCompareText2(text)}>예시 {i+3}</button>
                  ))}
                </div>
              </div>
            </div>
            <button
              className="btn btn-primary"
              onClick={runCompare}
              disabled={isComparing || !compareText1.trim() || !compareText2.trim()}
            >
              {isComparing ? <><Loader2 size={14} className="spinning" /> 비교중...</> : <><Target size={14} /> 유사도 비교</>}
            </button>

            {compareResult && !compareResult.error && (
              <div className="compare-result">
                <div className="similarity-display">
                  <div className="similarity-circle" style={{
                    background: `conic-gradient(${
                      compareResult.cosine_similarity >= 0.7 ? '#22c55e' :
                      compareResult.cosine_similarity >= 0.4 ? '#f59e0b' : '#ef4444'
                    } ${compareResult.similarity_percent}%, transparent 0)`
                  }}>
                    <div className="similarity-inner">
                      <span className="similarity-value">{compareResult.similarity_percent}%</span>
                      <span className="similarity-label">유사도</span>
                    </div>
                  </div>
                  <div className="similarity-interpretation">
                    <h4>{compareResult.interpretation}</h4>
                    <p>코사인 유사도: {compareResult.cosine_similarity.toFixed(6)}</p>
                  </div>
                </div>

                <div className="compare-vectors">
                  <div className="compare-vector-preview">
                    <h5>텍스트 1 벡터 (처음 10차원)</h5>
                    <div className="mini-vector">
                      {compareResult.embedding1_preview.map((v, i) => (
                        <span key={i} className="mini-value" style={{
                          color: v > 0 ? '#22c55e' : '#ef4444'
                        }}>{v.toFixed(3)}</span>
                      ))}
                    </div>
                  </div>
                  <div className="compare-vector-preview">
                    <h5>텍스트 2 벡터 (처음 10차원)</h5>
                    <div className="mini-vector">
                      {compareResult.embedding2_preview.map((v, i) => (
                        <span key={i} className="mini-value" style={{
                          color: v > 0 ? '#22c55e' : '#ef4444'
                        }}>{v.toFixed(3)}</span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="cosine-explanation">
                  <h5>코사인 유사도란?</h5>
                  <div className="formula">
                    <span>cos(θ) = (A · B) / (||A|| × ||B||)</span>
                  </div>
                  <p>두 벡터 사이의 각도를 측정합니다. 1에 가까우면 같은 방향(유사), 0이면 직교(무관), -1이면 반대 방향입니다.</p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'storage' && (
          <div className="storage-format-demo">
            <h4>Qdrant에 저장되는 데이터 형식</h4>

            <div className="format-examples">
              <div className="format-example">
                <h5>Dense Only (기본)</h5>
                <pre className="format-code">{`{
  "id": "doc_001",
  "vector": [0.023, -0.156, 0.872, 0.034, ...],  // 1024차원
  "payload": {
    "text": "원본 텍스트 내용",
    "source": "문서 출처",
    "created_at": "2026-01-08T12:00:00Z",
    "metadata": {
      "author": "홍길동",
      "category": "기술문서"
    }
  }
}`}</pre>
              </div>

              <div className="format-example">
                <h5>Hybrid (Dense + Sparse)</h5>
                <pre className="format-code">{`{
  "id": "doc_002",
  "vector": {
    "dense": [0.023, -0.156, 0.872, ...],  // 1024차원
    "sparse": {
      "indices": [1542, 3891, 7234, 12045],
      "values": [0.45, 0.32, 0.78, 0.21]
    }
  },
  "payload": {
    "text": "하이브리드 검색용 텍스트",
    "chunk_index": 3,
    "total_chunks": 10
  }
}`}</pre>
              </div>
            </div>

            <div className="search-types">
              <h5>검색 방식 비교</h5>
              <div className="search-type-grid">
                <div className="search-type">
                  <div className="search-type-header dense">
                    <span className="type-icon">🎯</span>
                    <span className="type-name">Dense Search</span>
                  </div>
                  <p>의미 기반 검색. "자동차"를 검색하면 "차량", "vehicle"도 찾음</p>
                  <code>query_vector: [0.1, -0.2, 0.3, ...]</code>
                </div>
                <div className="search-type">
                  <div className="search-type-header sparse">
                    <span className="type-icon">🔤</span>
                    <span className="type-name">Sparse Search</span>
                  </div>
                  <p>키워드 기반 검색. 정확한 단어 매칭 (BM25와 유사)</p>
                  <code>indices: [100, 200], values: [0.5, 0.3]</code>
                </div>
                <div className="search-type">
                  <div className="search-type-header hybrid">
                    <span className="type-icon">⚡</span>
                    <span className="type-name">Hybrid Search</span>
                  </div>
                  <p>Dense + Sparse 결합. RRF(Reciprocal Rank Fusion)로 통합</p>
                  <code>fusion: "rrf", alpha: 0.5</code>
                </div>
              </div>
            </div>

            {/* 하이브리드 검색 스코어 처리 설명 */}
            <div className="hybrid-score-section">
              <h5>🧮 하이브리드 검색 스코어 처리</h5>
              <p className="section-intro">Dense와 Sparse 검색 결과를 어떻게 융합하여 최적의 결과를 얻는지 설명합니다.</p>

              <div className="score-methods">
                <div className="score-method">
                  <div className="method-header">
                    <span className="method-icon">🔄</span>
                    <strong>RRF (Reciprocal Rank Fusion)</strong>
                    <span className="method-badge recommended">권장</span>
                  </div>
                  <p>각 검색 방식에서의 순위를 기반으로 점수를 계산합니다.</p>
                  <div className="formula-box">
                    <code>RRF_score(d) = Σ 1 / (k + rank(d))</code>
                    <span className="formula-note">k = 60 (일반적 상수), rank = 해당 검색에서의 순위</span>
                  </div>
                  <div className="example-calc">
                    <strong>예시:</strong> 문서 A가 Dense에서 2위, Sparse에서 5위인 경우
                    <code>RRF = 1/(60+2) + 1/(60+5) = 0.0161 + 0.0154 = 0.0315</code>
                  </div>
                </div>

                <div className="score-method">
                  <div className="method-header">
                    <span className="method-icon">⚖️</span>
                    <strong>Linear Combination (가중 평균)</strong>
                  </div>
                  <p>각 검색 점수에 가중치(alpha)를 적용하여 결합합니다.</p>
                  <div className="formula-box">
                    <code>Final_score = α × Dense_score + (1-α) × Sparse_score</code>
                    <span className="formula-note">α = 0.5일 때 두 검색 방식 동등 반영</span>
                  </div>
                  <div className="alpha-guide">
                    <div className="alpha-item">
                      <span className="alpha-value">α = 0.7</span>
                      <span className="alpha-desc">의미 검색 중시 (유사 개념 찾기)</span>
                    </div>
                    <div className="alpha-item">
                      <span className="alpha-value">α = 0.3</span>
                      <span className="alpha-desc">키워드 매칭 중시 (정확한 용어)</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="score-tip">
                <Info size={14} />
                <span><strong>팁:</strong> 기술 문서 검색은 α=0.6~0.7, 법률/계약서는 α=0.3~0.4가 효과적입니다. 데이터와 사용 사례에 맞게 튜닝하세요.</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Knowledge Graph 시각화 섹션 컴포넌트
const KnowledgeGraphSection = () => {
  const [viewMode, setViewMode] = useState('3d');
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);

  // 동물 분류 체계 온톨로지 샘플 데이터
  const sampleGraph = {
    id: 'animal-ontology',
    name: 'Animal Classification System',
    description: 'Biological classification ontology example',
    nodes: [
      { id: 'living-thing', label: '생물', type: 'class', properties: { description: '최상위 분류' } },
      { id: 'animal', label: '동물', type: 'class', properties: { description: '스스로 움직이는 생물' } },
      { id: 'mammal', label: '포유류', type: 'class', properties: { description: '젖을 먹여 키우는 동물' } },
      { id: 'bird', label: '조류', type: 'class', properties: { description: '깃털이 있는 동물' } },
      { id: 'cat-family', label: '고양이과', type: 'class', properties: { scientificName: 'Felidae' } },
      { id: 'dog-family', label: '개과', type: 'class', properties: { scientificName: 'Canidae' } },
      { id: 'nabi', label: '나비', type: 'instance', properties: { age: 3, color: '치즈색' } },
      { id: 'kong', label: '콩이', type: 'instance', properties: { age: 5, color: '검정색' } },
      { id: 'baduk', label: '바둑이', type: 'instance', properties: { age: 2, breed: '진돗개' } },
      { id: 'my-home', label: '우리집', type: 'instance', properties: { address: '서울시' } },
      { id: 'eats-prop', label: '먹는다', type: 'property', properties: { domain: '동물', range: '음식' } },
    ],
    edges: [
      { id: 'sc1', source: 'animal', target: 'living-thing', type: 'subClassOf', label: 'subClassOf' },
      { id: 'sc2', source: 'mammal', target: 'animal', type: 'subClassOf', label: 'subClassOf' },
      { id: 'sc3', source: 'bird', target: 'animal', type: 'subClassOf', label: 'subClassOf' },
      { id: 'sc4', source: 'cat-family', target: 'mammal', type: 'subClassOf', label: 'subClassOf' },
      { id: 'sc5', source: 'dog-family', target: 'mammal', type: 'subClassOf', label: 'subClassOf' },
      { id: 'io1', source: 'nabi', target: 'cat-family', type: 'instanceOf', label: 'rdf:type' },
      { id: 'io2', source: 'kong', target: 'cat-family', type: 'instanceOf', label: 'rdf:type' },
      { id: 'io3', source: 'baduk', target: 'dog-family', type: 'instanceOf', label: 'rdf:type' },
      { id: 'r1', source: 'nabi', target: 'my-home', type: 'livesIn', label: '산다' },
      { id: 'r2', source: 'nabi', target: 'kong', type: 'friendOf', label: '친구' },
    ],
    metadata: { createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), version: 1, nodeCount: 11, edgeCount: 10 },
  };

  return (
    <div className="card" style={{ marginTop: '20px' }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitBranch size={18} /> Knowledge Graph 시각화
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setViewMode('2d')}
            className={`demo-tab ${viewMode === '2d' ? 'active' : ''}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            2D
          </button>
          <button
            onClick={() => setViewMode('3d')}
            className={`demo-tab ${viewMode === '3d' ? 'active' : ''}`}
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            3D
          </button>
        </div>
      </div>
      <div style={{ display: 'flex', height: '500px', background: '#0f172a', borderRadius: '8px', overflow: 'hidden' }}>
        <div style={{ flex: 1 }}>
          {viewMode === '2d' ? (
            <KnowledgeGraphViewer
              graph={sampleGraph}
              onNodeSelect={setSelectedNode}
              onEdgeSelect={setSelectedEdge}
              layout="hierarchical"
              showMiniMap
              showControls
            />
          ) : (
            <KnowledgeGraph3D
              graph={sampleGraph}
              onNodeSelect={setSelectedNode}
              onEdgeSelect={setSelectedEdge}
            />
          )}
        </div>
        {(selectedNode || selectedEdge) && (
          <NodeDetailPanel
            node={selectedNode}
            edge={selectedEdge}
            onClose={() => { setSelectedNode(null); setSelectedEdge(null); }}
          />
        )}
      </div>
      <div style={{ padding: '12px', fontSize: '12px', color: '#94a3b8' }}>
        <strong>범례:</strong>
        <span style={{ marginLeft: '12px' }}><span style={{ display: 'inline-block', width: '12px', height: '12px', background: '#3b82f6', borderRadius: '2px', marginRight: '4px' }}></span>Class</span>
        <span style={{ marginLeft: '12px' }}><span style={{ display: 'inline-block', width: '12px', height: '12px', background: '#10b981', borderRadius: '2px', marginRight: '4px' }}></span>Instance</span>
        <span style={{ marginLeft: '12px' }}><span style={{ display: 'inline-block', width: '12px', height: '12px', background: '#f59e0b', borderRadius: '2px', marginRight: '4px' }}></span>Property</span>
      </div>
    </div>
  );
};

// Embedding 시각화 섹션 컴포넌트
const EmbeddingVisualizationSection = () => {
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);

  const sampleEmbeddingGraph = {
    id: 'embedding-graph',
    name: 'Embedding Similarity Graph',
    description: 't-SNE style clustering visualization',
    nodes: [
      { id: 'doc1', label: 'AI 연구 논문', type: 'document', properties: { category: 'AI', tokens: 1024 } },
      { id: 'doc2', label: '딥러닝 가이드', type: 'document', properties: { category: 'AI', tokens: 856 } },
      { id: 'doc3', label: 'NLP 튜토리얼', type: 'document', properties: { category: 'AI', tokens: 1200 } },
      { id: 'query1', label: 'AI란 무엇인가?', type: 'query', properties: { similarity: 0.92 } },
      { id: 'query2', label: '딥러닝 설명', type: 'query', properties: { similarity: 0.88 } },
      { id: 'chunk1', label: 'Chunk: 신경망 구조', type: 'chunk', properties: { parent: 'doc1', position: 1 } },
      { id: 'chunk2', label: 'Chunk: 학습 방법', type: 'chunk', properties: { parent: 'doc1', position: 2 } },
      { id: 'chunk3', label: 'Chunk: 트랜스포머', type: 'chunk', properties: { parent: 'doc2', position: 1 } },
      { id: 'entity1', label: 'GPT-4', type: 'entity', properties: { type: 'Model' } },
      { id: 'entity2', label: 'Transformer', type: 'entity', properties: { type: 'Architecture' } },
    ],
    edges: [
      { id: 'e1', source: 'doc1', target: 'doc2', type: 'similar', label: '0.85', weight: 3 },
      { id: 'e2', source: 'doc2', target: 'doc3', type: 'similar', label: '0.78', weight: 2 },
      { id: 'e3', source: 'query1', target: 'doc1', type: 'matches', label: '0.92' },
      { id: 'e4', source: 'query2', target: 'doc2', type: 'matches', label: '0.88' },
      { id: 'e5', source: 'chunk1', target: 'doc1', type: 'partOf', label: 'chunk' },
      { id: 'e6', source: 'chunk2', target: 'doc1', type: 'partOf', label: 'chunk' },
      { id: 'e7', source: 'chunk3', target: 'doc2', type: 'partOf', label: 'chunk' },
      { id: 'e8', source: 'entity1', target: 'chunk3', type: 'mentioned', label: 'mentions' },
      { id: 'e9', source: 'entity2', target: 'chunk1', type: 'mentioned', label: 'mentions' },
    ],
    metadata: { createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), version: 1, nodeCount: 10, edgeCount: 9 },
  };

  return (
    <div className="card" style={{ marginTop: '20px' }}>
      <div className="card-header">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap size={18} /> Embedding 시각화 (t-SNE Style)
        </h3>
        <span style={{ fontSize: '12px', color: '#94a3b8' }}>같은 타입 = 유사한 임베딩 = 가까이 클러스터링</span>
      </div>
      <div style={{ display: 'flex', height: '500px', background: '#0f172a', borderRadius: '8px', overflow: 'hidden' }}>
        <div style={{ flex: 1 }}>
          <EmbeddingVisualization
            graph={sampleEmbeddingGraph}
            onNodeSelect={setSelectedNode}
            onEdgeSelect={setSelectedEdge}
            showMiniMap
            showControls
          />
        </div>
        {(selectedNode || selectedEdge) && (
          <NodeDetailPanel
            node={selectedNode}
            edge={selectedEdge}
            onClose={() => { setSelectedNode(null); setSelectedEdge(null); }}
          />
        )}
      </div>
      <div style={{ padding: '12px', fontSize: '12px', color: '#94a3b8' }}>
        <strong>범례:</strong>
        <span style={{ marginLeft: '12px' }}><span style={{ display: 'inline-block', width: '12px', height: '12px', background: '#3b82f6', borderRadius: '2px', marginRight: '4px' }}></span>Document</span>
        <span style={{ marginLeft: '12px' }}><span style={{ display: 'inline-block', width: '12px', height: '12px', background: '#f59e0b', borderRadius: '2px', marginRight: '4px' }}></span>Query</span>
        <span style={{ marginLeft: '12px' }}><span style={{ display: 'inline-block', width: '12px', height: '12px', background: '#8b5cf6', borderRadius: '2px', marginRight: '4px' }}></span>Chunk</span>
        <span style={{ marginLeft: '12px' }}><span style={{ display: 'inline-block', width: '12px', height: '12px', background: '#10b981', borderRadius: '2px', marginRight: '4px' }}></span>Entity</span>
      </div>
    </div>
  );
};

// Workflow 섹션 컴포넌트
const WorkflowSection = () => {
  const [showEditor, setShowEditor] = useState(false);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState(null);

  if (showEditor && selectedWorkflowId) {
    return (
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Workflow size={18} /> Workflow Editor
          </h3>
          <button
            onClick={() => { setShowEditor(false); setSelectedWorkflowId(null); }}
            className="demo-tab"
            style={{ padding: '6px 12px', fontSize: '12px' }}
          >
            ← 목록으로
          </button>
        </div>
        <div style={{ height: '600px', background: '#0f172a', borderRadius: '8px', overflow: 'hidden' }}>
          <WorkflowEditor />
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginTop: '20px' }}>
      <div className="card-header">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Workflow size={18} /> AI Workflow Builder
        </h3>
        <span style={{ fontSize: '12px', color: '#94a3b8' }}>드래그 앤 드롭으로 AI 파이프라인 구성</span>
      </div>
      <div style={{ background: '#0f172a', borderRadius: '8px', overflow: 'hidden' }}>
        <WorkflowList />
      </div>
    </div>
  );
};

// 온톨로지 라이브 데모 컴포넌트
const OntologyLiveDemo = () => {
  const [activeTab, setActiveTab] = useState('schema'); // schema, query, rag, index
  const [schemaData, setSchemaData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [ragData, setRagData] = useState(null);
  const [indexData, setIndexData] = useState(null);
  const [cypherQuery, setCypherQuery] = useState('MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 10');
  const [queryResult, setQueryResult] = useState(null);
  const [isQuerying, setIsQuerying] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    loadOntologyData();
  }, []);

  const loadOntologyData = async () => {
    try {
      const [schema, graph, rag, index] = await Promise.all([
        axios.get('/api/ontology/schema'),
        axios.get('/api/ontology/graph-data'),
        axios.get('/api/ontology/rag-integration'),
        axios.get('/api/ontology/index-types')
      ]);
      setSchemaData(schema.data);
      setGraphData(graph.data);
      setRagData(rag.data);
      setIndexData(index.data);
    } catch (error) {
      console.error('Failed to load ontology data:', error);
    }
  };

  const executeQuery = async () => {
    setIsQuerying(true);
    try {
      const response = await axios.post('/api/ontology/query', { query: cypherQuery });
      setQueryResult(response.data);
    } catch (error) {
      setQueryResult({ error: error.message });
    }
    setIsQuerying(false);
  };

  const exampleQueries = [
    { label: '모든 노드', query: 'MATCH (n) RETURN n LIMIT 10' },
    { label: '모든 관계', query: 'MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 10' },
    { label: '최단 경로', query: 'MATCH path = shortestPath((a)-[*]-(b)) RETURN path' },
    { label: '노드 수', query: 'MATCH (n) RETURN count(n) as count' }
  ];

  const nodeColors = {
    'Person': '#4ecdc4',
    'Department': '#45b7d1',
    'Project': '#96ceb4',
    'Technology': '#ffeaa7',
    'Company': '#dfe6e9'
  };

  return (
    <div className="ontology-live-demo-card">
      <div className="demo-header">
        <h4><GitBranch size={18} /> Ontology (Neo4j) 라이브 데모</h4>
        <p>그래프 데이터베이스로 개념과 관계를 표현하고 탐색합니다</p>
      </div>

      <div className="demo-tabs">
        <button
          className={activeTab === 'schema' ? 'active' : ''}
          onClick={() => setActiveTab('schema')}
        >
          <Database size={14} /> 스키마 비교
        </button>
        <button
          className={activeTab === 'query' ? 'active' : ''}
          onClick={() => setActiveTab('query')}
        >
          <Play size={14} /> Cypher 실행
        </button>
        <button
          className={activeTab === 'rag' ? 'active' : ''}
          onClick={() => setActiveTab('rag')}
        >
          <Workflow size={14} /> RAG 통합
        </button>
        <button
          className={activeTab === 'index' ? 'active' : ''}
          onClick={() => setActiveTab('index')}
        >
          <Layers size={14} /> 인덱스
        </button>
      </div>

      <div className="demo-content">
        {/* 스키마 비교 탭 */}
        {activeTab === 'schema' && schemaData && (
          <div className="schema-comparison">
            <div className="comparison-intro">
              <Info size={16} />
              <span>온톨로지(그래프 스키마)는 기존 RDBMS 스키마와 유사하지만, 관계를 1급 시민으로 취급합니다</span>
            </div>

            <div className="schema-grid">
              {/* RDBMS 스키마 */}
              <div className="schema-section rdbms">
                <h5>🗄️ RDBMS 스키마</h5>
                <div className="tables-list">
                  {schemaData.rdbms_schema.tables.map((table, idx) => (
                    <div key={idx} className="table-card">
                      <div className="table-name">{table.name}</div>
                      <div className="table-columns">
                        {table.columns.map((col, cidx) => (
                          <span key={cidx} className={col.includes('PK') ? 'pk' : col.includes('FK') ? 'fk' : ''}>
                            {col}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="query-example">
                  <h6>SQL 쿼리 예시</h6>
                  <pre>{schemaData.rdbms_schema.sql_example}</pre>
                </div>
              </div>

              {/* Graph 스키마 */}
              <div className="schema-section graph">
                <h5>🕸️ Graph 스키마 (온톨로지)</h5>

                {/* Mermaid 차트로 그래프 스키마 시각화 */}
                <div className="ontology-mermaid-chart">
                  <h6>그래프 구조 시각화</h6>
                  <MermaidChart
                    chart={`graph LR
    subgraph Nodes["노드 (Entities)"]
        P[("👤 Person<br/>name, email, role")]
        D[("📁 Department<br/>name, budget")]
        PR[("📋 Project<br/>name, status")]
        T[("💻 Technology<br/>name, type")]
    end

    subgraph Relationships["관계"]
        P -->|WORKS_IN| D
        P -->|MANAGES| PR
        P -->|KNOWS| T
        PR -->|USES| T
        D -->|OWNS| PR
    end

    style P fill:#4ecdc4,stroke:#333,stroke-width:2px
    style D fill:#45b7d1,stroke:#333,stroke-width:2px
    style PR fill:#96ceb4,stroke:#333,stroke-width:2px
    style T fill:#ffeaa7,stroke:#333,stroke-width:2px`}
                    className="ontology-graph-mermaid"
                  />
                </div>

                <div className="nodes-list">
                  <h6>노드 (Node Labels)</h6>
                  {schemaData.graph_schema.nodes.map((node, idx) => (
                    <div key={idx} className="node-card" style={{ borderLeftColor: node.color }}>
                      <div className="node-label" style={{ backgroundColor: node.color }}>{node.label}</div>
                      <div className="node-properties">
                        {node.properties.map((prop, pidx) => (
                          <span key={pidx}>{prop}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="relations-list">
                  <h6>관계 (Relationships)</h6>
                  {schemaData.graph_schema.relationships.map((rel, idx) => (
                    <div key={idx} className="relation-card">
                      <span className="rel-from">{rel.from}</span>
                      <span className="rel-arrow">-[:{rel.type}]-&gt;</span>
                      <span className="rel-to">{rel.to}</span>
                    </div>
                  ))}
                </div>
                <div className="query-example">
                  <h6>Cypher 쿼리 예시</h6>
                  <pre>{schemaData.graph_schema.cypher_example}</pre>
                </div>
              </div>
            </div>

            {/* 비교 표 */}
            <div className="comparison-table">
              <h5>RDBMS vs Graph 비교</h5>
              <table>
                <thead>
                  <tr>
                    <th>항목</th>
                    <th>RDBMS</th>
                    <th>Graph DB</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(schemaData.comparison).map(([key, value]) => (
                    <tr key={key}>
                      <td>{key.replace(/_/g, ' ')}</td>
                      <td className="rdbms-cell">{value.rdbms}</td>
                      <td className="graph-cell">{value.graph}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Cypher 쿼리 실행 탭 */}
        {activeTab === 'query' && (
          <div className="cypher-query-section">
            <div className="query-panel">
              <div className="query-input-section">
                <h5>Cypher 쿼리 실행</h5>
                <div className="example-queries">
                  {exampleQueries.map((eq, idx) => (
                    <button key={idx} onClick={() => setCypherQuery(eq.query)}>
                      {eq.label}
                    </button>
                  ))}
                </div>
                <textarea
                  value={cypherQuery}
                  onChange={(e) => setCypherQuery(e.target.value)}
                  placeholder="Cypher 쿼리를 입력하세요..."
                  rows={4}
                />
                <button className="execute-btn" onClick={executeQuery} disabled={isQuerying}>
                  {isQuerying ? <Loader2 size={14} className="spinning" /> : <Play size={14} />}
                  {isQuerying ? '실행 중...' : '쿼리 실행'}
                </button>
              </div>

              {queryResult && (
                <div className="query-result">
                  <div className="result-header">
                    <h5>실행 결과</h5>
                    {queryResult.mode && (
                      <span className={`mode-badge ${queryResult.mode}`}>
                        {queryResult.mode === 'live' ? '🟢 Live' : '🟡 Simulation'}
                      </span>
                    )}
                  </div>
                  {queryResult.error ? (
                    <div className="result-error">{queryResult.error}</div>
                  ) : (
                    <pre className="result-json">{JSON.stringify(queryResult.results, null, 2)}</pre>
                  )}
                  {queryResult.note && (
                    <div className="result-note"><Info size={14} /> {queryResult.note}</div>
                  )}
                </div>
              )}
            </div>

            {/* 그래프 시각화 */}
            {graphData && (
              <div className="graph-visualization">
                <h5>그래프 시각화</h5>
                <svg viewBox="0 0 800 400" className="graph-svg">
                  {/* 엣지 그리기 */}
                  {graphData.edges.map((edge, idx) => {
                    const fromNode = graphData.nodes.find(n => n.id === edge.from);
                    const toNode = graphData.nodes.find(n => n.id === edge.to);
                    if (!fromNode || !toNode) return null;

                    const midX = (fromNode.x + toNode.x) / 2;
                    const midY = (fromNode.y + toNode.y) / 2;

                    return (
                      <g key={idx}>
                        <line
                          x1={fromNode.x}
                          y1={fromNode.y}
                          x2={toNode.x}
                          y2={toNode.y}
                          className="graph-edge"
                        />
                        <text x={midX} y={midY - 5} className="edge-label">{edge.type}</text>
                      </g>
                    );
                  })}

                  {/* 노드 그리기 */}
                  {graphData.nodes.map((node, idx) => (
                    <g
                      key={idx}
                      className={`graph-node ${selectedNode?.id === node.id ? 'selected' : ''}`}
                      onClick={() => setSelectedNode(node)}
                    >
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r={30}
                        fill={nodeColors[node.label] || '#ddd'}
                      />
                      <text x={node.x} y={node.y - 40} className="node-label-text">{node.label}</text>
                      <text x={node.x} y={node.y + 5} className="node-name-text">{node.name}</text>
                    </g>
                  ))}
                </svg>

                {selectedNode && (
                  <div className="node-details">
                    <h6>선택된 노드</h6>
                    <div className="node-info">
                      <span className="node-type" style={{ backgroundColor: nodeColors[selectedNode.label] }}>
                        {selectedNode.label}
                      </span>
                      <span className="node-name">{selectedNode.name}</span>
                    </div>
                    <div className="node-props">
                      {Object.entries(selectedNode.properties).map(([key, value]) => (
                        <div key={key}><strong>{key}:</strong> {value}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* RAG 통합 탭 */}
        {activeTab === 'rag' && ragData && (
          <div className="rag-integration-section">
            <div className="rag-comparison">
              {/* Traditional RAG */}
              <div className="rag-flow traditional">
                <h5>📚 Traditional RAG</h5>
                <div className="flow-diagram">
                  {ragData.traditional_rag.flow.map((step, idx) => (
                    <React.Fragment key={idx}>
                      <div className="flow-step">{step}</div>
                      {idx < ragData.traditional_rag.flow.length - 1 && (
                        <div className="flow-arrow">→</div>
                      )}
                    </React.Fragment>
                  ))}
                </div>
                <div className="limitations">
                  <h6>한계점</h6>
                  <ul>
                    {ragData.traditional_rag.limitations.map((lim, idx) => (
                      <li key={idx}><AlertTriangle size={12} /> {lim}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Graph Enhanced RAG */}
              <div className="rag-flow enhanced">
                <h5>🕸️ Graph-Enhanced RAG</h5>
                <div className="flow-diagram vertical">
                  {ragData.graph_enhanced_rag.flow.map((step, idx) => (
                    <div key={idx} className="flow-step-detailed">
                      <div className="step-number">{idx + 1}</div>
                      <div className="step-content">
                        <div className="step-name">{step.step}</div>
                        <div className="step-desc">{step.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="advantages">
                  <h6>장점</h6>
                  <ul>
                    {ragData.graph_enhanced_rag.advantages.map((adv, idx) => (
                      <li key={idx}><CheckCircle size={12} /> {adv}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* 실제 예제 */}
            <div className="rag-example">
              <h5>실제 동작 예시</h5>
              <div className="example-query">
                <strong>질문:</strong> {ragData.example.query}
              </div>
              <div className="graph-context">
                <h6>🕸️ 그래프 컨텍스트</h6>
                <div className="traversal-path">
                  {ragData.example.graph_context.traversal.map((path, idx) => (
                    <div key={idx} className="path-step">
                      <code>{path}</code>
                    </div>
                  ))}
                </div>
                <div className="related-info">
                  {ragData.example.graph_context.related_info.map((info, idx) => (
                    <span key={idx} className="info-tag">{info}</span>
                  ))}
                </div>
              </div>
              <div className="enhanced-response">
                <h6>✨ 강화된 응답</h6>
                <p>{ragData.example.enhanced_response}</p>
              </div>
            </div>
          </div>
        )}

        {/* 인덱스 탭 */}
        {activeTab === 'index' && indexData && (
          <div className="index-section">
            <div className="index-grid">
              {indexData.index_types.map((idx, i) => (
                <div key={i} className="index-card">
                  <div className="index-header">
                    <span className="index-icon">{idx.icon}</span>
                    <span className="index-type">{idx.type}</span>
                  </div>
                  <p className="index-description">{idx.description}</p>
                  <div className="index-use-case">
                    <Tag size={12} /> {idx.use_case}
                  </div>
                  <pre className="index-cypher">{idx.cypher}</pre>
                </div>
              ))}
            </div>

            {/* 하이브리드 검색 예제 */}
            <div className="hybrid-search-example">
              <h5>🔍 Vector + Graph 하이브리드 검색</h5>
              <p>{indexData.hybrid_search_example.description}</p>
              <pre className="hybrid-cypher">{indexData.hybrid_search_example.cypher}</pre>
              <div className="explanation-steps">
                {indexData.hybrid_search_example.explanation.map((exp, idx) => (
                  <div key={idx} className="explanation-step">
                    <span className="step-num">{idx + 1}</span>
                    <span>{exp}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Vector DB RAG 관리 가이드 컴포넌트
const VectorDBRAGGuide = () => {
  const [guideData, setGuideData] = useState(null);
  const [activeSection, setActiveSection] = useState('collection');
  const [expandedStrategy, setExpandedStrategy] = useState(0);

  useEffect(() => {
    loadGuideData();
  }, []);

  const loadGuideData = async () => {
    try {
      const response = await axios.get('/api/vectordb/rag-guide');
      setGuideData(response.data);
    } catch (error) {
      console.error('Failed to load RAG guide:', error);
    }
  };

  if (!guideData) return null;

  const sections = [
    { key: 'collection', label: '컬렉션 전략', icon: <Folder size={14} /> },
    { key: 'metadata', label: '메타데이터', icon: <Tag size={14} /> },
    { key: 'rbac', label: 'RBAC', icon: <Shield size={14} /> },
    { key: 'chunking', label: '청킹', icon: <Layers size={14} /> },
    { key: 'search', label: '검색 최적화', icon: <Search size={14} /> },
    { key: 'maintenance', label: '유지보수', icon: <Settings size={14} /> }
  ];

  return (
    <div className="rag-guide-card">
      <div className="guide-header">
        <h4><BookOpen size={18} /> Vector DB RAG 관리 가이드</h4>
        <p>효과적인 RAG 시스템 구축을 위한 실무 가이드</p>
      </div>

      <div className="guide-nav">
        {sections.map(section => (
          <button
            key={section.key}
            className={activeSection === section.key ? 'active' : ''}
            onClick={() => setActiveSection(section.key)}
          >
            {section.icon} {section.label}
          </button>
        ))}
      </div>

      <div className="guide-content">
        {/* 컬렉션 전략 */}
        {activeSection === 'collection' && (
          <div className="collection-section">
            <div className="section-header">
              <h5>{guideData.collection_strategies.title}</h5>
              <p>{guideData.collection_strategies.description}</p>
            </div>

            <div className="strategies-accordion">
              {guideData.collection_strategies.strategies.map((strategy, idx) => (
                <div key={idx} className={`strategy-item ${expandedStrategy === idx ? 'expanded' : ''}`}>
                  <div
                    className="strategy-header"
                    onClick={() => setExpandedStrategy(expandedStrategy === idx ? -1 : idx)}
                  >
                    <span className="strategy-icon">{strategy.icon}</span>
                    <span className="strategy-name">{strategy.name}</span>
                    <ChevronDown size={16} className={`chevron ${expandedStrategy === idx ? 'rotated' : ''}`} />
                  </div>

                  {expandedStrategy === idx && (
                    <div className="strategy-content">
                      <div className="collections-grid">
                        {strategy.collections.map((col, cidx) => (
                          <div key={cidx} className="collection-item">
                            <div className="col-name">{col.name}</div>
                            <div className="col-desc">{col.description}</div>
                            <div className="col-example">{col.example}</div>
                          </div>
                        ))}
                      </div>
                      <div className="pros-cons">
                        <div className="pros">
                          <h6><CheckCircle size={12} /> 장점</h6>
                          <ul>
                            {strategy.pros.map((pro, pidx) => (
                              <li key={pidx}>{pro}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="cons">
                          <h6><AlertCircle size={12} /> 단점</h6>
                          <ul>
                            {strategy.cons.map((con, cidx) => (
                              <li key={cidx}>{con}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 메타데이터 태깅 */}
        {activeSection === 'metadata' && (
          <div className="metadata-section">
            <div className="section-header">
              <h5>{guideData.metadata_tagging.title}</h5>
              <p>{guideData.metadata_tagging.description}</p>
            </div>

            <div className="fields-grid">
              <div className="fields-column required">
                <h6>필수 필드</h6>
                {guideData.metadata_tagging.required_fields.map((field, idx) => (
                  <div key={idx} className="field-card">
                    <div className="field-header">
                      <code className="field-name">{field.field}</code>
                      <span className="field-type">{field.type}</span>
                    </div>
                    <div className="field-desc">{field.description}</div>
                    <div className="field-example">예: {field.example}</div>
                  </div>
                ))}
              </div>
              <div className="fields-column recommended">
                <h6>권장 필드</h6>
                {guideData.metadata_tagging.recommended_fields.map((field, idx) => (
                  <div key={idx} className="field-card">
                    <div className="field-header">
                      <code className="field-name">{field.field}</code>
                      <span className="field-type">{field.type}</span>
                      {field.filter && <span className="filter-badge">필터용</span>}
                    </div>
                    <div className="field-desc">{field.description}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="filter-example">
              <h6>{guideData.metadata_tagging.filter_example.description}</h6>
              <pre>{guideData.metadata_tagging.filter_example.code}</pre>
            </div>
          </div>
        )}

        {/* RBAC */}
        {activeSection === 'rbac' && (
          <div className="rbac-section">
            <div className="section-header">
              <h5>{guideData.rbac_implementation.title}</h5>
              <p>{guideData.rbac_implementation.description}</p>
            </div>

            <div className="rbac-approaches">
              {guideData.rbac_implementation.approaches.map((approach, idx) => (
                <div key={idx} className="approach-card">
                  <div className="approach-header">
                    <h6>{approach.name}</h6>
                    <span className="approach-impl">{approach.implementation}</span>
                  </div>
                  <p>{approach.description}</p>
                  <pre className="approach-code">{approach.code}</pre>
                </div>
              ))}
            </div>

            <div className="best-practices">
              <h6><CheckCircle size={14} /> 베스트 프랙티스</h6>
              <ul>
                {guideData.rbac_implementation.best_practices.map((practice, idx) => (
                  <li key={idx}>{practice}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* 청킹 전략 */}
        {activeSection === 'chunking' && (
          <div className="chunking-section">
            <div className="section-header">
              <h5>{guideData.chunking_strategies.title}</h5>
              <p>{guideData.chunking_strategies.description}</p>
            </div>

            <div className="chunking-grid">
              {guideData.chunking_strategies.strategies.map((strategy, idx) => (
                <div key={idx} className="chunking-card">
                  <div className="chunking-type">{strategy.type}</div>
                  <div className="chunking-details">
                    <div className="detail-row">
                      <span className="label">청크 크기</span>
                      <span className="value">{strategy.chunk_size}</span>
                    </div>
                    <div className="detail-row">
                      <span className="label">오버랩</span>
                      <span className="value">{strategy.overlap}</span>
                    </div>
                    <div className="detail-row">
                      <span className="label">분리 방법</span>
                      <span className="value">{strategy.method}</span>
                    </div>
                  </div>
                  <div className="chunking-tip">
                    <Info size={12} /> {strategy.tip}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 검색 최적화 */}
        {activeSection === 'search' && (
          <div className="search-section">
            <div className="section-header">
              <h5>{guideData.search_optimization.title}</h5>
            </div>

            <div className="optimization-grid">
              {guideData.search_optimization.tips.map((tip, idx) => (
                <div key={idx} className="tip-card">
                  <h6>{tip.category}</h6>
                  <ul>
                    {tip.items.map((item, iidx) => (
                      <li key={iidx}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 유지보수 */}
        {activeSection === 'maintenance' && (
          <div className="maintenance-section">
            <div className="section-header">
              <h5>{guideData.maintenance.title}</h5>
            </div>

            <div className="tasks-grid">
              {guideData.maintenance.tasks.map((task, idx) => (
                <div key={idx} className="task-card">
                  <div className="task-header">
                    <span className="task-name">{task.task}</span>
                    <span className="task-frequency">{task.frequency}</span>
                  </div>
                  <p>{task.description}</p>
                </div>
              ))}
            </div>

            <div className="backup-section">
              <h6><Archive size={14} /> {guideData.maintenance.backup_strategy.description}</h6>
              <ul>
                {guideData.maintenance.backup_strategy.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

function App() {
  const [clusterSummary, setClusterSummary] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [nodeMetrics, setNodeMetrics] = useState([]);
  const [workloads, setWorkloads] = useState({});
  const [gpuStatus, setGpuStatus] = useState(null);
  const [gpuDetailed, setGpuDetailed] = useState(null);
  const [pods, setPods] = useState({ total: 0, by_namespace: {} });
  const [storageInfo, setStorageInfo] = useState(null);
  const [storageCapacity, setStorageCapacity] = useState(null);
  const [rustfsAllocSize, setRustfsAllocSize] = useState(100); // GB 단위
  const [bucketUsage, setBucketUsage] = useState([]);

  // 파이프라인 및 이벤트 상태
  const [pipelineStatus, setPipelineStatus] = useState(null);
  const [clusterEvents, setClusterEvents] = useState({ events: [], total: 0 });
  const [selectedPodLog, setSelectedPodLog] = useState(null);
  const [podLogs, setPodLogs] = useState(null);

  // vLLM 워크로드 설정
  const [vllmConfig, setVllmConfig] = useState({
    model: 'Qwen/Qwen2.5-7B-Instruct',
    nodeSelector: '',
    gpuCount: 1,
    cpuLimit: '4',
    memoryLimit: '16Gi'
  });

  // Qdrant 워크로드 설정
  const [qdrantConfig, setQdrantConfig] = useState({
    useCase: 'agent-context',
    storageSize: 10,
    replicas: 1,
    nodeSelector: ''
  });

  // ComfyUI 워크로드 설정 (실제 사용량 기준)
  const [comfyuiConfig, setComfyuiConfig] = useState({
    useCase: 'image-generation',
    nodeSelector: '',
    gpuCount: 1,
    cpuLimit: '2',          // SD 1.5: CPU는 거의 안씀
    memoryLimit: '8Gi',     // SDXL: ~6GB, SD 1.5: ~4GB
    storageSize: 20         // 모델 + 출력물 저장
  });

  // Neo4j (Ontology) 워크로드 설정 (실제 사용량 기준)
  const [neo4jConfig, setNeo4jConfig] = useState({
    useCase: 'knowledge-graph',
    nodeSelector: '',
    cpuLimit: '1',          // 그래프 쿼리는 CPU 적게 사용
    memoryLimit: '2Gi',     // 소규모 그래프: 1-2GB
    storageSize: 10,        // 시작 용량
    replicas: 1
  });

  // 모델별 최소 GPU 요구사항
  const MODEL_GPU_REQUIREMENTS = {
    // Agent/Tool Use 최적화
    'Qwen/Qwen2.5-7B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '16GB' },
    'Qwen/Qwen2.5-14B-Instruct': { minGpu: 1, recommendedGpu: 2, vram: '32GB' },
    'Qwen/Qwen2.5-32B-Instruct': { minGpu: 2, recommendedGpu: 4, vram: '64GB' },
    'Qwen/Qwen2.5-72B-Instruct': { minGpu: 4, recommendedGpu: 8, vram: '160GB' },
    // 한국어 특화
    'yanolja/EEVE-Korean-Instruct-10.8B-v1.0': { minGpu: 1, recommendedGpu: 1, vram: '24GB' },
    'beomi/Llama-3-Open-Ko-8B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '16GB' },
    // 코딩 특화
    'Qwen/Qwen2.5-Coder-7B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '16GB' },
    'Qwen/Qwen2.5-Coder-32B-Instruct': { minGpu: 2, recommendedGpu: 4, vram: '64GB' },
    'deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct': { minGpu: 1, recommendedGpu: 2, vram: '32GB' },
    // 경량 모델
    'Qwen/Qwen2.5-3B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '8GB' },
    'Qwen/Qwen2.5-1.5B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '4GB' },
    'microsoft/Phi-3-mini-4k-instruct': { minGpu: 1, recommendedGpu: 1, vram: '8GB' },
    // 대형 모델
    'meta-llama/Llama-3.1-70B-Instruct': { minGpu: 4, recommendedGpu: 8, vram: '160GB' },
    'mistralai/Mixtral-8x7B-Instruct-v0.1': { minGpu: 2, recommendedGpu: 4, vram: '96GB' },
    // VLM (Vision-Language Model)
    'llava-hf/llava-1.5-7b-hf': { minGpu: 1, recommendedGpu: 1, vram: '16GB', type: 'vlm' },
    'llava-hf/llava-1.5-13b-hf': { minGpu: 1, recommendedGpu: 2, vram: '28GB', type: 'vlm' },
    'Qwen/Qwen2-VL-7B-Instruct': { minGpu: 1, recommendedGpu: 1, vram: '18GB', type: 'vlm' },
    'Qwen/Qwen2-VL-72B-Instruct': { minGpu: 4, recommendedGpu: 8, vram: '160GB', type: 'vlm' },
    'openbmb/MiniCPM-V-2_6': { minGpu: 1, recommendedGpu: 1, vram: '12GB', type: 'vlm' },
    'microsoft/Phi-3.5-vision-instruct': { minGpu: 1, recommendedGpu: 1, vram: '10GB', type: 'vlm' }
  };

  // Qdrant use case 설정 (실제 사용량 기준)
  // 1536차원 벡터 기준: 100만 벡터 ≈ 6GB
  const QDRANT_USE_CASES = {
    'agent-context': {
      name: 'Agent 메모리',
      description: '유저별 대화 히스토리 및 컨텍스트 저장',
      recommendedStorage: 5,    // 수천~수만 벡터
      recommendedReplicas: 1
    },
    'rag-search': {
      name: 'RAG 문서 검색',
      description: '문서 청크 임베딩 저장 및 검색',
      recommendedStorage: 10,   // 수만~십만 벡터
      recommendedReplicas: 1
    },
    'document-embedding': {
      name: '대용량 임베딩',
      description: '대규모 문서 벡터 저장소',
      recommendedStorage: 50,   // 백만+ 벡터
      recommendedReplicas: 1
    },
    'multimodal-search': {
      name: '멀티모달 검색',
      description: '이미지/텍스트 임베딩 통합',
      recommendedStorage: 20,   // 이미지 벡터는 더 큼
      recommendedReplicas: 1
    }
  };

  // 현재 모델의 GPU 요구사항
  const currentModelReq = MODEL_GPU_REQUIREMENTS[vllmConfig.model] || { minGpu: 1, recommendedGpu: 1, vram: '16GB' };

  // 모델 변경 시 GPU 자동 조정
  const handleModelChange = (model) => {
    const req = MODEL_GPU_REQUIREMENTS[model] || { minGpu: 1, recommendedGpu: 1 };
    setVllmConfig({
      ...vllmConfig,
      model,
      gpuCount: Math.max(vllmConfig.gpuCount, req.minGpu)
    });
  };

  // Qdrant use case 변경 시 권장 설정 적용
  const handleQdrantUseCaseChange = (useCase) => {
    const caseConfig = QDRANT_USE_CASES[useCase];
    setQdrantConfig({
      ...qdrantConfig,
      useCase,
      storageSize: caseConfig.recommendedStorage,
      replicas: caseConfig.recommendedReplicas
    });
  };

  // 클러스터 노드 중 GPU가 있는 노드 필터링
  const getGpuNodes = () => {
    if (!nodes || nodes.length === 0) return [];
    return nodes.filter(node => {
      const gpuCapacity = node.allocatable?.['nvidia.com/gpu'] || node.capacity?.['nvidia.com/gpu'] || 0;
      return parseInt(gpuCapacity) > 0;
    });
  };

  // ComfyUI use case 설정 (실제 VRAM/메모리 사용량 기준)
  const COMFYUI_USE_CASES = {
    'image-generation': {
      name: '이미지 생성 (SD 1.5)',
      description: 'SD 1.5 기반 - VRAM 4GB, RAM 6GB',
      recommendedGpu: 1,
      recommendedStorage: 15,   // 모델 2GB + 출력물
      recommendedMemory: '6Gi'
    },
    'image-generation-xl': {
      name: '이미지 생성 (SDXL)',
      description: 'SDXL 기반 - VRAM 8GB, RAM 10GB',
      recommendedGpu: 1,
      recommendedStorage: 20,   // 모델 6GB + 출력물
      recommendedMemory: '10Gi'
    },
    'video-generation': {
      name: '동영상 생성',
      description: 'AnimateDiff - VRAM 10GB, RAM 16GB',
      recommendedGpu: 1,
      recommendedStorage: 30,
      recommendedMemory: '16Gi'
    },
    'image-editing': {
      name: '이미지 편집',
      description: 'Inpainting/ControlNet - VRAM 6GB',
      recommendedGpu: 1,
      recommendedStorage: 20,
      recommendedMemory: '8Gi'
    },
    'api-service': {
      name: 'API 서비스',
      description: 'REST API 서비스용 (SD 1.5 기준)',
      recommendedGpu: 1,
      recommendedStorage: 20,
      recommendedMemory: '8Gi'
    }
  };

  // ComfyUI use case 변경 시 권장 설정 적용
  const handleComfyUIUseCaseChange = (useCase) => {
    const caseConfig = COMFYUI_USE_CASES[useCase];
    setComfyuiConfig({
      ...comfyuiConfig,
      useCase,
      gpuCount: caseConfig.recommendedGpu,
      storageSize: caseConfig.recommendedStorage,
      memoryLimit: caseConfig.recommendedMemory
    });
  };

  // Neo4j (Ontology) use case 설정 (실제 사용량 기준)
  // Neo4j: 노드 100만개 + 관계 500만개 ≈ 2-3GB
  const NEO4J_USE_CASES = {
    'knowledge-graph': {
      name: '지식 그래프',
      description: '엔티티/관계 저장 - 소규모',
      recommendedStorage: 10,   // 노드 수십만개
      recommendedMemory: '2Gi', // heap 1GB + 여유
      recommendedReplicas: 1
    },
    'entity-relationship': {
      name: '엔티티 관계 분석',
      description: '문서 엔티티 추출 결과 저장',
      recommendedStorage: 20,
      recommendedMemory: '4Gi',
      recommendedReplicas: 1
    },
    'graph-rag': {
      name: 'Graph RAG',
      description: '벡터DB + 그래프 하이브리드 검색',
      recommendedStorage: 10,
      recommendedMemory: '2Gi',
      recommendedReplicas: 1
    }
  };

  // Neo4j use case 변경 시 권장 설정 적용
  const handleNeo4jUseCaseChange = (useCase) => {
    const caseConfig = NEO4J_USE_CASES[useCase];
    setNeo4jConfig({
      ...neo4jConfig,
      useCase,
      storageSize: caseConfig.recommendedStorage,
      memoryLimit: caseConfig.recommendedMemory,
      replicas: caseConfig.recommendedReplicas
    });
  };

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);
  const [actionLoading, setActionLoading] = useState({});
  const [expandedNamespaces, setExpandedNamespaces] = useState({});

  // URL 라우팅 연동
  const navigate = useNavigate();
  const location = useLocation();

  // URL 경로와 탭 이름 매핑
  const TAB_ROUTES = {
    '/': 'overview',
    '/overview': 'overview',
    '/goal': 'goal',
    '/pods': 'pods',
    '/gpu': 'gpu',
    '/storage': 'storage',
    '/benchmark': 'benchmark',
    '/cluster': 'cluster',
    '/agent': 'agent',
    '/pipeline': 'pipeline',
    '/qdrant': 'qdrant',
    '/comfyui': 'comfyui',
    '/neo4j': 'neo4j',
    '/llm': 'llm'
  };

  // URL에서 현재 탭 결정
  const getTabFromPath = (pathname) => {
    return TAB_ROUTES[pathname] || 'overview';
  };

  const [activeTab, setActiveTab] = useState(() => getTabFromPath(location.pathname));

  // URL 변경 시 탭 동기화
  useEffect(() => {
    const newTab = getTabFromPath(location.pathname);
    if (newTab !== activeTab) {
      setActiveTab(newTab);
    }
  }, [location.pathname]);

  // 탭 변경 시 URL 업데이트 함수
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    const path = tab === 'overview' ? '/' : `/${tab}`;
    navigate(path);
  };

  // 임베딩 모델 선택 상태
  const [selectedEmbeddingModel, setSelectedEmbeddingModel] = useState('bge-m3');

  // 임베딩 모델 데이터
  const embeddingModels = {
    'bge-m3': {
      name: 'BAAI/bge-m3',
      dimension: 1024,
      maxTokens: 8192,
      language: '다국어 (100+)',
      params: '568M',
      batchSize: 32,
      speed: '~50 doc/sec',
      device: 'GPU (CUDA)',
      features: ['Dense', 'Sparse', 'Multi-vector'],
      mteb: 67.2,
      retrieval: 89.5,
      similarity: 85.3,
      description: '한국어 포함 100+ 언어 지원, Dense/Sparse/Multi-vector 통합 지원. RAG에 최적화된 권장 모델'
    },
    'e5-large': {
      name: 'intfloat/multilingual-e5-large',
      dimension: 1024,
      maxTokens: 512,
      language: '다국어',
      params: '560M',
      batchSize: 32,
      speed: '~40 doc/sec',
      device: 'GPU (CUDA)',
      features: ['Dense'],
      mteb: 64.5,
      retrieval: 87.2,
      similarity: 83.1,
      description: 'Microsoft E5 다국어 모델, 안정적인 성능'
    },
    'minilm': {
      name: 'sentence-transformers/all-MiniLM-L6-v2',
      dimension: 384,
      maxTokens: 256,
      language: '영어',
      params: '22M',
      batchSize: 64,
      speed: '~200 doc/sec',
      device: 'CPU/GPU',
      features: ['Dense'],
      mteb: 56.3,
      retrieval: 78.4,
      similarity: 76.2,
      description: '경량 모델, 빠른 추론 속도. 리소스 제한 환경에 적합'
    },
    'kure': {
      name: 'nlpai-lab/KURE-v1',
      dimension: 1024,
      maxTokens: 8192,
      language: '한국어 특화',
      params: '326M',
      batchSize: 32,
      speed: '~60 doc/sec',
      device: 'GPU (CUDA)',
      features: ['Dense', 'Korean-optimized'],
      mteb: 71.8,
      retrieval: 92.1,
      similarity: 88.7,
      description: '고려대학교 NLP & AI 연구실 + HIAI 연구소 개발 한국어 특화 임베딩 모델. 한국어 문서 RAG에 최적'
    }
  };

  // ComfyUI 데모 상태
  const [comfyuiDemoMode, setComfyuiDemoMode] = useState('image'); // 'image' | 'video'
  const [comfyuiPrompt, setComfyuiPrompt] = useState('');
  const [comfyuiNegativePrompt, setComfyuiNegativePrompt] = useState('bad quality, blurry, distorted');
  const [comfyuiSettings, setComfyuiSettings] = useState({
    width: '1024',
    height: '1024',
    steps: '20',
    cfg: '7',
    frames: '16',
    fps: '8',
    videoWidth: '512'
  });
  const [comfyuiGenerating, setComfyuiGenerating] = useState(false);
  const [comfyuiProgress, setComfyuiProgress] = useState(0);
  const [comfyuiResult, setComfyuiResult] = useState(null);
  const [comfyuiQueue, setComfyuiQueue] = useState({ running: 0, pending: 0, completed: 0 });

  // ComfyUI 생성 핸들러
  const handleComfyuiGenerate = async () => {
    if (!comfyuiPrompt.trim()) return;

    setComfyuiGenerating(true);
    setComfyuiProgress(0);
    setComfyuiResult(null);

    try {
      // 워크플로우 생성 (이미지/동영상 모드에 따라)
      const workflow = comfyuiDemoMode === 'image'
        ? createText2ImgWorkflow()
        : createAnimateDiffWorkflow();

      const response = await axios.post(`${API_BASE}/comfyui/prompt`, {
        prompt: workflow,
        client_id: 'dashboard-' + Date.now()
      });

      const promptId = response.data.prompt_id;

      // 진행률 시뮬레이션 (실제로는 WebSocket 사용)
      const progressInterval = setInterval(() => {
        setComfyuiProgress(prev => {
          if (prev >= 95) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + Math.random() * 10;
        });
      }, 500);

      // 결과 폴링
      let attempts = 0;
      const maxAttempts = 60;

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 2000));

        try {
          const historyRes = await axios.get(`${API_BASE}/comfyui/history/${promptId}`);
          const history = historyRes.data;

          if (history[promptId]?.outputs) {
            clearInterval(progressInterval);
            setComfyuiProgress(100);

            // 출력 찾기
            const outputs = history[promptId].outputs;
            for (const nodeId in outputs) {
              const nodeOutput = outputs[nodeId];
              if (nodeOutput.images && nodeOutput.images[0]) {
                const img = nodeOutput.images[0];
                setComfyuiResult(`${API_BASE}/comfyui/view?filename=${img.filename}&subfolder=${img.subfolder || ''}&type=${img.type || 'output'}`);
                break;
              }
              if (nodeOutput.gifs && nodeOutput.gifs[0]) {
                const video = nodeOutput.gifs[0];
                setComfyuiResult(`${API_BASE}/comfyui/view?filename=${video.filename}&subfolder=${video.subfolder || ''}&type=${video.type || 'output'}`);
                break;
              }
            }
            break;
          }
        } catch (pollError) {
          console.log('Polling history:', pollError);
        }
        attempts++;
      }

      setComfyuiGenerating(false);
      fetchComfyuiQueue();
    } catch (error) {
      console.error('ComfyUI generation error:', error);
      setComfyuiGenerating(false);
      showToast('생성 실패: ' + (error.response?.data?.detail || error.message), 'error');
    }
  };

  // txt2img 워크플로우 생성
  const createText2ImgWorkflow = () => ({
    "3": {
      "class_type": "KSampler",
      "inputs": {
        "seed": Math.floor(Math.random() * 1000000000),
        "steps": parseInt(comfyuiSettings.steps),
        "cfg": parseFloat(comfyuiSettings.cfg),
        "sampler_name": "euler",
        "scheduler": "normal",
        "denoise": 1,
        "model": ["4", 0],
        "positive": ["6", 0],
        "negative": ["7", 0],
        "latent_image": ["5", 0]
      }
    },
    "4": {
      "class_type": "CheckpointLoaderSimple",
      "inputs": { "ckpt_name": "sd_xl_base_1.0.safetensors" }
    },
    "5": {
      "class_type": "EmptyLatentImage",
      "inputs": {
        "width": parseInt(comfyuiSettings.width),
        "height": parseInt(comfyuiSettings.height),
        "batch_size": 1
      }
    },
    "6": {
      "class_type": "CLIPTextEncode",
      "inputs": { "text": comfyuiPrompt, "clip": ["4", 1] }
    },
    "7": {
      "class_type": "CLIPTextEncode",
      "inputs": { "text": comfyuiNegativePrompt, "clip": ["4", 1] }
    },
    "8": {
      "class_type": "VAEDecode",
      "inputs": { "samples": ["3", 0], "vae": ["4", 2] }
    },
    "9": {
      "class_type": "SaveImage",
      "inputs": { "filename_prefix": "Dashboard", "images": ["8", 0] }
    }
  });

  // AnimateDiff 워크플로우 생성
  const createAnimateDiffWorkflow = () => ({
    "1": {
      "class_type": "CheckpointLoaderSimple",
      "inputs": { "ckpt_name": "realisticVisionV51_v51VAE.safetensors" }
    },
    "2": {
      "class_type": "ADE_LoadAnimateDiffModel",
      "inputs": { "model_name": "mm_sd_v15_v2.ckpt" }
    },
    "3": {
      "class_type": "ADE_ApplyAnimateDiffModel",
      "inputs": { "model": ["1", 0], "motion_model": ["2", 0] }
    },
    "4": {
      "class_type": "CLIPTextEncode",
      "inputs": { "text": comfyuiPrompt, "clip": ["1", 1] }
    },
    "5": {
      "class_type": "CLIPTextEncode",
      "inputs": { "text": comfyuiNegativePrompt, "clip": ["1", 1] }
    },
    "6": {
      "class_type": "EmptyLatentImage",
      "inputs": {
        "width": parseInt(comfyuiSettings.videoWidth),
        "height": parseInt(comfyuiSettings.videoWidth),
        "batch_size": parseInt(comfyuiSettings.frames)
      }
    },
    "7": {
      "class_type": "KSampler",
      "inputs": {
        "seed": Math.floor(Math.random() * 1000000000),
        "steps": 20,
        "cfg": 7,
        "sampler_name": "euler_ancestral",
        "scheduler": "normal",
        "denoise": 1,
        "model": ["3", 0],
        "positive": ["4", 0],
        "negative": ["5", 0],
        "latent_image": ["6", 0]
      }
    },
    "8": {
      "class_type": "VAEDecode",
      "inputs": { "samples": ["7", 0], "vae": ["1", 2] }
    },
    "9": {
      "class_type": "VHS_VideoCombine",
      "inputs": {
        "images": ["8", 0],
        "frame_rate": parseInt(comfyuiSettings.fps),
        "format": "video/h264-mp4",
        "filename_prefix": "AnimateDiff"
      }
    }
  });

  // ComfyUI 큐 상태 조회
  const fetchComfyuiQueue = async () => {
    try {
      const response = await axios.get(`${API_BASE}/comfyui/queue`);
      setComfyuiQueue({
        running: response.data.queue_running?.length || 0,
        pending: response.data.queue_pending?.length || 0,
        completed: 0 // history에서 가져와야 함
      });
    } catch (error) {
      console.log('Queue fetch error:', error);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchData = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    try {
      const [summaryRes, nodesRes, metricsRes, workloadsRes, gpuRes, gpuDetailRes, podsRes, storageRes, capacityRes, breakdownRes, pipelineRes, eventsRes] = await Promise.all([
        axios.get(`${API_BASE}/cluster/summary`),
        axios.get(`${API_BASE}/nodes`),
        axios.get(`${API_BASE}/nodes/metrics`),
        axios.get(`${API_BASE}/workloads`),
        axios.get(`${API_BASE}/gpu/status`),
        axios.get(`${API_BASE}/gpu/detailed`),
        axios.get(`${API_BASE}/pods`),
        axios.get(`${API_BASE}/storage/status`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/storage/available-capacity`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/storage/usage-breakdown`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/pipeline/status`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/events?limit=30`).catch(() => ({ data: { events: [], total: 0 } }))
      ]);

      setClusterSummary(summaryRes.data);
      setNodes(nodesRes.data.nodes);
      setNodeMetrics(metricsRes.data.nodes);
      setWorkloads(workloadsRes.data.workloads);
      setGpuStatus(gpuRes.data);
      setGpuDetailed(gpuDetailRes.data);
      setPods(podsRes.data);
      setStorageInfo(storageRes.data);
      setStorageCapacity(capacityRes.data);
      setBucketUsage(breakdownRes.data);
      setPipelineStatus(pipelineRes.data);
      setClusterEvents(eventsRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      // 초기 로딩 완료 처리 (한 번만)
      if (loading) setLoading(false);
      if (manual) setRefreshing(false);
    }
  }, [loading]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleWorkloadAction = async (workload, action, replicas = 1, storageSizeGb = null) => {
    // 먼저 로딩 상태 설정
    setActionLoading(prev => ({ ...prev, [workload]: { loading: true, action } }));

    try {
      const payload = { action, replicas };
      if (storageSizeGb) {
        payload.storage_size_gb = storageSizeGb;
      }
      await axios.post(`${API_BASE}/workloads/${workload}`, payload);

      // start일 경우: API 성공 후 로딩 유지 (준비 중 표시), 백그라운드에서 상태 폴링
      if (action === 'start') {
        // 데이터 갱신 (준비 중 상태로 전환)
        await fetchData();
        // 로딩 해제 - 이후 isWorkloadPreparing이 준비 중 상태 관리
        setActionLoading(prev => ({ ...prev, [workload]: { loading: false, action: null } }));
        showToast(`${workload} 시작 완료!`);
      }
      // stop일 경우: 실제 Pod가 종료될 때까지 대기
      else if (action === 'stop') {
        // 종료 완료될 때까지 폴링
        let attempts = 0;
        const maxAttempts = 30; // 최대 30초 대기
        let stopped = false;

        while (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 1000));
          try {
            const res = await axios.get(`${API_BASE}/workloads`);
            const currentWorkload = res.data[workload];

            // 종료 완료 조건: 상태가 stopped이거나 replicas가 0이거나 ready_replicas가 0
            if (currentWorkload?.status === 'stopped' ||
                currentWorkload?.replicas === 0 ||
                currentWorkload?.ready_replicas === 0) {
              setWorkloads(res.data);
              stopped = true;
              break;
            }
          } catch (pollError) {
            // 폴링 중 에러는 무시하고 계속 진행
            console.log('Polling error (ignored):', pollError);
          }
          attempts++;
        }

        // 로딩 해제 후 토스트 (30초 후에도 안 끝났어도 성공으로 처리)
        setActionLoading(prev => ({ ...prev, [workload]: { loading: false, action: null } }));
        showToast(`${workload} 종료 ${stopped ? '완료' : '요청됨'}!`);
        await fetchData();
      }
      // scale
      else {
        await fetchData();
        setActionLoading(prev => ({ ...prev, [workload]: { loading: false, action: null } }));
        showToast(`${workload} 스케일 완료!`);
      }
    } catch (error) {
      setActionLoading(prev => ({ ...prev, [workload]: { loading: false, action: null } }));
      showToast(error.response?.data?.detail || '작업 실패', 'error');
    }
  };

  const toggleNamespace = (ns) => {
    setExpandedNamespaces(prev => ({
      ...prev,
      [ns]: !prev[ns]
    }));
  };

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  const resources = clusterSummary?.resources || {};

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="header">
        <h1>
          <div className="logo">
            <Layers size={24} color="white" />
          </div>
          K3s Cluster Dashboard
        </h1>
        <div className="header-right">
          <div className="tab-buttons">
            <button
              className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => handleTabChange('overview')}
            >
              개요
            </button>
            <button
              className={`tab-btn ${activeTab === 'goal' ? 'active' : ''}`}
              onClick={() => handleTabChange('goal')}
            >
              Goal
            </button>
            <button
              className={`tab-btn ${activeTab === 'pods' ? 'active' : ''}`}
              onClick={() => handleTabChange('pods')}
            >
              Pods ({pods.total})
            </button>
            <button
              className={`tab-btn ${activeTab === 'gpu' ? 'active' : ''}`}
              onClick={() => handleTabChange('gpu')}
            >
              GPU
            </button>
            <button
              className={`tab-btn ${activeTab === 'storage' ? 'active' : ''}`}
              onClick={() => handleTabChange('storage')}
            >
              Storage
            </button>
            <button
              className={`tab-btn ${activeTab === 'benchmark' ? 'active' : ''}`}
              onClick={() => handleTabChange('benchmark')}
            >
              Benchmark
            </button>
            <button
              className={`tab-btn ${activeTab === 'cluster' ? 'active' : ''}`}
              onClick={() => handleTabChange('cluster')}
            >
              Cluster
            </button>
            <button
              className={`tab-btn ${activeTab === 'agent' ? 'active' : ''}`}
              onClick={() => handleTabChange('agent')}
            >
              Agent
            </button>
            <button
              className={`tab-btn ${activeTab === 'pipeline' ? 'active' : ''}`}
              onClick={() => handleTabChange('pipeline')}
            >
              Logging
            </button>
            <button
              className={`tab-btn ${activeTab === 'qdrant' ? 'active' : ''}`}
              onClick={() => handleTabChange('qdrant')}
            >
              Vector DB
            </button>
            <button
              className={`tab-btn ${activeTab === 'comfyui' ? 'active' : ''}`}
              onClick={() => handleTabChange('comfyui')}
            >
              ComfyUI
            </button>
            <button
              className={`tab-btn ${activeTab === 'neo4j' ? 'active' : ''}`}
              onClick={() => handleTabChange('neo4j')}
            >
              Ontology
            </button>
            <button
              className={`tab-btn ${activeTab === 'llm' ? 'active' : ''}`}
              onClick={() => handleTabChange('llm')}
            >
              LLM
            </button>
            <button
              className={`tab-btn ${activeTab === 'parser' ? 'active' : ''}`}
              onClick={() => handleTabChange('parser')}
            >
              Parser
            </button>
          </div>
          <div className="cluster-status">
            <span className={`status-dot ${clusterSummary?.status || 'error'}`}></span>
            <span>{clusterSummary?.status === 'healthy' ? '정상' : '점검 필요'}</span>
          </div>
          <button
            className={`btn-icon ${refreshing ? 'spinning' : ''}`}
            onClick={() => fetchData(true)}
            disabled={refreshing}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      {activeTab === 'overview' && (
        <>
          {/* Stats Overview with Resource Usage */}
          <section className="section">
            <div className="grid grid-4">
              <div className="card stat-card">
                <div className="icon blue"><Server size={24} /></div>
                <div className="card-title">노드</div>
                <div className="card-value">{clusterSummary?.nodes?.ready || 0}</div>
                <div className="card-subtitle">/ {clusterSummary?.nodes?.total || 0} 전체</div>
              </div>

              <div className="card stat-card">
                <div className="icon green"><Box size={24} /></div>
                <div className="card-title">Pod</div>
                <div className="card-value">{clusterSummary?.pods?.running || 0}</div>
                <div className="card-subtitle">
                  실행중 / {clusterSummary?.pods?.total || 0} 전체
                  {(clusterSummary?.pods?.pending || 0) > 0 && (
                    <span className="badge yellow"> {clusterSummary.pods.pending} 대기</span>
                  )}
                  {(clusterSummary?.pods?.failed || 0) > 0 && (
                    <span className="badge red"> {clusterSummary.pods.failed} 실패</span>
                  )}
                </div>
              </div>

              <div className="card stat-card">
                <div className="icon purple"><Cpu size={24} /></div>
                <div className="card-title">CPU 사용률</div>
                <div className="card-value">{resources.cpu?.percent || 0}%</div>
                <div className="card-subtitle">
                  {(resources.cpu?.usage / 1000 || 0).toFixed(1)} / {(resources.cpu?.capacity / 1000 || 0).toFixed(0)} cores
                </div>
                <ProgressBar value={resources.cpu?.percent || 0} max={100} color="auto" showLabel={false} />
              </div>

              <div className="card stat-card">
                <div className="icon orange"><MemoryStick size={24} /></div>
                <div className="card-title">메모리 사용률</div>
                <div className="card-value">{resources.memory?.percent || 0}%</div>
                <div className="card-subtitle">
                  {((resources.memory?.usage || 0) / 1024).toFixed(1)} / {((resources.memory?.capacity || 0) / 1024).toFixed(0)} GB
                </div>
                <ProgressBar value={resources.memory?.percent || 0} max={100} color="auto" showLabel={false} />
              </div>
            </div>
          </section>

          {/* Storage Usage Breakdown */}
          {bucketUsage && (
            <section className="section">
              <div className="section-header">
                <h2 className="section-title">스토리지 사용량</h2>
                <div className="storage-total-info">
                  <span>{bucketUsage.total_used_human} / {bucketUsage.total_capacity_human}</span>
                  <span className="storage-usage-percent">({bucketUsage.usage_percent}% 사용)</span>
                </div>
              </div>
              <div className="storage-breakdown-container">
                {/* 스토리지 바 차트 */}
                <div className="storage-breakdown-bar">
                  {bucketUsage.categories?.filter(cat => cat.type !== 'free').map((cat, idx) => (
                    <div
                      key={cat.type}
                      className="storage-breakdown-segment"
                      style={{
                        width: `${(cat.allocated / bucketUsage.total_capacity) * 100}%`,
                        backgroundColor: cat.color
                      }}
                      title={`${cat.name}: ${cat.allocated_human}`}
                    />
                  ))}
                </div>
                {/* 범례 및 상세 정보 */}
                <div className="storage-breakdown-legend">
                  {bucketUsage.categories?.map((cat) => (
                    <div key={cat.type} className="storage-breakdown-item">
                      <div className="storage-item-header">
                        <span className="storage-item-color" style={{ backgroundColor: cat.color }} />
                        <span className="storage-item-name">{cat.name}</span>
                        <span className="storage-item-size">{cat.allocated_human}</span>
                      </div>
                      <div className="storage-item-desc">{cat.description}</div>
                      {cat.type === 'rustfs' && cat.used > 0 && (
                        <div className="storage-item-used">
                          실제 데이터: {cat.used_human}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Nodes with Metrics - htop/nvtop 스타일 */}
          <section className="section">
            <div className="section-header">
              <h2 className="section-title">노드 현황</h2>
              <div className="resource-legend">
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
              {nodes.map((node) => {
                const metrics = nodeMetrics.find(m => m.name === node.name) || {};
                const cpuUsageClass = metrics.cpu_percent >= 90 ? 'danger' : metrics.cpu_percent >= 70 ? 'warning' : '';
                const memUsageClass = metrics.memory_percent >= 90 ? 'danger' : metrics.memory_percent >= 70 ? 'warning' : '';
                const gpuCapacity = metrics.gpu_capacity || node.gpu_count || 0;
                const gpuUsed = metrics.gpu_used || 0;
                const gpuType = metrics.gpu_type || node.gpu_type || '';

                return (
                  <div key={node.name} className="node-htop-card">
                    <div className="node-htop-header">
                      <div className="node-htop-info">
                        <span className={`status-dot ${node.status === 'Ready' ? 'healthy' : 'error'}`}></span>
                        <span className="node-htop-name">{node.name}</span>
                        <div className="node-htop-roles">
                          {(() => {
                            // control-plane과 master를 합치기
                            const hasControlPlane = node.roles.includes('control-plane');
                            const hasMaster = node.roles.includes('master');
                            const hasEtcd = node.roles.includes('etcd');
                            const otherRoles = node.roles.filter(r => !['control-plane', 'master', 'etcd'].includes(r));

                            const displayRoles = [];
                            if (hasControlPlane || hasMaster) {
                              displayRoles.push('control-plane/master');
                            }
                            if (hasEtcd) {
                              displayRoles.push('etcd');
                            }
                            displayRoles.push(...otherRoles);

                            return displayRoles.map((role) => (
                              <span key={role} className="node-htop-role">{role}</span>
                            ));
                          })()}
                        </div>
                      </div>
                    </div>

                    <div className="node-htop-body">
                      {/* CPU 바 (htop 스타일) */}
                      <div className="htop-bar htop-bar-cpu">
                        <span className="htop-label">CPU</span>
                        <div className="htop-bar-container">
                          {/* Limits 바 (가장 뒤) */}
                          <div
                            className="htop-bar-fill limits"
                            style={{ width: `${Math.min((metrics.cpu_limits || 0) / (metrics.cpu_capacity || 1) * 100, 100)}%` }}
                          />
                          {/* Requests 바 */}
                          <div
                            className="htop-bar-fill requests"
                            style={{ width: `${metrics.cpu_requests_percent || 0}%` }}
                          />
                          {/* 사용량 바 (가장 앞) */}
                          <div
                            className={`htop-bar-fill usage ${cpuUsageClass}`}
                            style={{ width: `${metrics.cpu_percent || 0}%` }}
                          />
                          {/* 구분선 */}
                          <div className="htop-bar-segments">
                            {[...Array(10)].map((_, i) => <div key={i} className="htop-bar-segment" />)}
                          </div>
                        </div>
                        <span className="htop-bar-value">
                          {((metrics.cpu_usage || 0) / 1000).toFixed(1)} / {((metrics.cpu_capacity || 0) / 1000).toFixed(0)} cores
                        </span>
                        <span className="htop-bar-percent">{metrics.cpu_percent || 0}%</span>
                      </div>

                      {/* 메모리 바 (htop 스타일) */}
                      <div className="htop-bar htop-bar-mem">
                        <span className="htop-label">MEM</span>
                        <div className="htop-bar-container">
                          {/* Limits 바 */}
                          <div
                            className="htop-bar-fill limits"
                            style={{ width: `${Math.min((metrics.memory_limits || 0) / (metrics.memory_capacity || 1) * 100, 100)}%` }}
                          />
                          {/* Requests 바 */}
                          <div
                            className="htop-bar-fill requests"
                            style={{ width: `${metrics.memory_requests_percent || 0}%` }}
                          />
                          {/* 사용량 바 */}
                          <div
                            className={`htop-bar-fill usage ${memUsageClass}`}
                            style={{ width: `${metrics.memory_percent || 0}%` }}
                          />
                          <div className="htop-bar-segments">
                            {[...Array(10)].map((_, i) => <div key={i} className="htop-bar-segment" />)}
                          </div>
                        </div>
                        <span className="htop-bar-value">
                          {((metrics.memory_usage || 0) / 1024).toFixed(1)} / {((metrics.memory_capacity || 0) / 1024).toFixed(0)} GB
                        </span>
                        <span className="htop-bar-percent">{metrics.memory_percent || 0}%</span>
                      </div>

                      {/* GPU 미터 (nvtop 스타일) - 인덱스별 상세 표시 */}
                      {gpuCapacity > 0 && (
                        <div className="gpu-meter-detailed">
                          <div className="gpu-meter-header">
                            <span className="gpu-meter-label">GPU</span>
                            <span className="gpu-meter-type">{gpuType}</span>
                            <span className="gpu-meter-summary">{gpuUsed} / {gpuCapacity} 사용</span>
                          </div>
                          <div className="gpu-meter-slots">
                            {[...Array(gpuCapacity)].map((_, i) => (
                              <div
                                key={i}
                                className={`gpu-slot ${i < gpuUsed ? 'used' : 'available'}`}
                                title={`GPU ${i}: ${i < gpuUsed ? '사용 중' : '사용 가능'}`}
                              >
                                <span className="gpu-slot-index">{i}</span>
                                <span className="gpu-slot-status">{i < gpuUsed ? '●' : '○'}</span>
                              </div>
                            ))}
                          </div>
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
                  <WorkloadStatusBadge
                    workload={workloads.vllm}
                    isLoading={actionLoading.vllm?.loading}
                    actionType={actionLoading.vllm?.action}
                  />
                </div>

                {/* vLLM 설정 (중지 상태에서만 표시) */}
                {(workloads.vllm?.status === 'stopped' || workloads.vllm?.status === 'not_deployed') && (
                  <div className="workload-config-section">
                    <div className="workload-config-row">
                      <div className="config-group" style={{ flex: 2 }}>
                        <label>모델 선택</label>
                        <select
                          value={vllmConfig.model}
                          onChange={(e) => handleModelChange(e.target.value)}
                        >
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
                            <option value="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct">DeepSeek-Coder-V2 - 1~2 GPU</option>
                          </optgroup>
                          <optgroup label="경량 모델">
                            <option value="Qwen/Qwen2.5-3B-Instruct">Qwen2.5-3B-Instruct - 1 GPU</option>
                            <option value="Qwen/Qwen2.5-1.5B-Instruct">Qwen2.5-1.5B-Instruct - 1 GPU</option>
                            <option value="microsoft/Phi-3-mini-4k-instruct">Phi-3-mini-4k - 1 GPU</option>
                          </optgroup>
                          <optgroup label="대형 모델 (고성능 GPU 필요)">
                            <option value="meta-llama/Llama-3.1-70B-Instruct">Llama-3.1-70B - 4~8 GPU</option>
                            <option value="mistralai/Mixtral-8x7B-Instruct-v0.1">Mixtral-8x7B - 2~4 GPU</option>
                          </optgroup>
                          <optgroup label="VLM (Vision-Language Model)">
                            <option value="llava-hf/llava-1.5-7b-hf">LLaVA 1.5-7B - 1 GPU (VLM)</option>
                            <option value="llava-hf/llava-1.5-13b-hf">LLaVA 1.5-13B - 1~2 GPU (VLM)</option>
                            <option value="Qwen/Qwen2-VL-7B-Instruct">Qwen2-VL-7B - 1 GPU (VLM)</option>
                            <option value="Qwen/Qwen2-VL-72B-Instruct">Qwen2-VL-72B - 4~8 GPU (VLM)</option>
                            <option value="openbmb/MiniCPM-V-2_6">MiniCPM-V 2.6 - 1 GPU (VLM)</option>
                            <option value="microsoft/Phi-3.5-vision-instruct">Phi-3.5-Vision - 1 GPU (VLM)</option>
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
                        <label>노드 선택 (GPU 노드)</label>
                        <select
                          value={vllmConfig.nodeSelector}
                          onChange={(e) => setVllmConfig({ ...vllmConfig, nodeSelector: e.target.value })}
                        >
                          <option value="">자동 (스케줄러 결정)</option>
                          {getGpuNodes().map(node => {
                            const gpuCount = parseInt(node.allocatable?.['nvidia.com/gpu'] || node.capacity?.['nvidia.com/gpu'] || 0);
                            const isEligible = gpuCount >= vllmConfig.gpuCount;
                            return (
                              <option
                                key={node.name}
                                value={node.name}
                                disabled={!isEligible}
                              >
                                {node.name} ({gpuCount} GPU){!isEligible ? ' - GPU 부족' : ''}
                              </option>
                            );
                          })}
                          {getGpuNodes().length === 0 && (
                            <option value="" disabled>GPU 노드 없음</option>
                          )}
                        </select>
                      </div>
                      <div className="config-group">
                        <label>CPU</label>
                        <select
                          value={vllmConfig.cpuLimit}
                          onChange={(e) => setVllmConfig({ ...vllmConfig, cpuLimit: e.target.value })}
                        >
                          <option value="2">2 코어</option>
                          <option value="4">4 코어</option>
                          <option value="8">8 코어</option>
                          <option value="16">16 코어</option>
                        </select>
                      </div>
                      <div className="config-group">
                        <label>메모리</label>
                        <select
                          value={vllmConfig.memoryLimit}
                          onChange={(e) => setVllmConfig({ ...vllmConfig, memoryLimit: e.target.value })}
                        >
                          <option value="8Gi">8 GB</option>
                          <option value="16Gi">16 GB</option>
                          <option value="32Gi">32 GB</option>
                          <option value="64Gi">64 GB</option>
                          <option value="128Gi">128 GB</option>
                        </select>
                      </div>
                    </div>
                    <div className="resource-preview">
                      <div className="resource-item">
                        <MonitorDot size={14} />
                        <span>GPU {vllmConfig.gpuCount}개</span>
                        <span className="value">VRAM {currentModelReq.vram} 필요</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="workload-controls">
                  <button
                    className="btn btn-success"
                    onClick={() => handleWorkloadAction('vllm', 'start')}
                    disabled={actionLoading.vllm?.loading || workloads.vllm?.status === 'running' || isWorkloadPreparing(workloads.vllm, false)}
                  >
                    <Play size={16} /> 실행
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleWorkloadAction('vllm', 'stop')}
                    disabled={actionLoading.vllm?.loading || (workloads.vllm?.status === 'stopped' && !isWorkloadPreparing(workloads.vllm, false)) || workloads.vllm?.status === 'not_deployed'}
                  >
                    <Square size={16} /> {isWorkloadPreparing(workloads.vllm, false) ? '취소' : '중지'}
                  </button>
                </div>
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
                  <WorkloadStatusBadge
                    workload={workloads.rustfs}
                    isLoading={actionLoading.rustfs?.loading}
                    actionType={actionLoading.rustfs?.action}
                  />
                </div>

                {/* 스토리지 할당 슬라이더 (실행 전에만 표시) */}
                {(workloads.rustfs?.status === 'stopped' || workloads.rustfs?.status === 'not_deployed') && storageCapacity && (() => {
                  const currentPvcGb = storageCapacity.current_pvc_size
                    ? Math.ceil(storageCapacity.current_pvc_size / (1024 * 1024 * 1024))
                    : 0;
                  const minSize = Math.max(10, currentPvcGb); // 현재 할당량 이상만 선택 가능
                  const maxSize = Math.floor(storageCapacity.max_allocatable / (1024 * 1024 * 1024));

                  return (
                    <div className="storage-allocator">
                      <div className="allocator-header">
                        <HardDrive size={16} />
                        <span>스토리지 할당</span>
                        <span className="allocator-value">{rustfsAllocSize} GB</span>
                      </div>
                      <input
                        type="range"
                        className="allocator-slider"
                        min={minSize}
                        max={maxSize}
                        value={Math.max(rustfsAllocSize, minSize)}
                        onChange={(e) => setRustfsAllocSize(Number(e.target.value))}
                      />
                      <div className="allocator-labels">
                        <span>{minSize} GB{currentPvcGb > 0 ? ' (최소)' : ''}</span>
                        <span>최대 {storageCapacity.max_allocatable_human}</span>
                      </div>
                      {storageCapacity.current_pvc_size_human && (
                        <div className="allocator-current">
                          현재 할당됨: {storageCapacity.current_pvc_size_human}
                          {storageCapacity.current_storage_class && (
                            <span className="allocator-storage-class">
                              ({storageCapacity.current_storage_class})
                            </span>
                          )}
                          {storageCapacity.supports_expansion ? (
                            <span className="allocator-note allocator-note-success">✓ Longhorn 동적 확장 지원</span>
                          ) : (
                            <span className="allocator-note">⚠️ {storageCapacity.current_storage_class || 'local-path'}는 동적 확장/축소 미지원 - 크기 변경시 초기화 필요</span>
                          )}
                        </div>
                      )}
                      {/* 노드별 가용 스토리지 정보 */}
                      {storageCapacity.nodes && storageCapacity.nodes.length > 0 && (
                        <div className="allocator-nodes">
                          <div className="allocator-nodes-header">노드별 가용 용량</div>
                          {storageCapacity.nodes.map((node, idx) => (
                            <div key={idx} className="allocator-node-item">
                              <span className="node-name">{node.node}</span>
                              <span className="node-capacity">{node.allocatable_human}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()}

                <div className="workload-controls">
                  <button
                    className="btn btn-success"
                    onClick={() => handleWorkloadAction('rustfs', 'start', 1, rustfsAllocSize)}
                    disabled={actionLoading.rustfs?.loading || workloads.rustfs?.status === 'running' || isWorkloadPreparing(workloads.rustfs, false)}
                  >
                    <Play size={16} /> 실행 ({rustfsAllocSize}GB)
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleWorkloadAction('rustfs', 'stop')}
                    disabled={actionLoading.rustfs?.loading || (workloads.rustfs?.status === 'stopped' && !isWorkloadPreparing(workloads.rustfs, false)) || workloads.rustfs?.status === 'not_deployed'}
                  >
                    <Square size={16} /> {isWorkloadPreparing(workloads.rustfs, false) ? '취소' : '중지'}
                  </button>
                </div>
                {/* 실행 중 PVC 확장 (Longhorn 동적 확장 지원 시) */}
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
                        onClick={() => setRustfsAllocSize(prev => Math.max(
                          Math.ceil((storageCapacity.current_pvc_size || 0) / (1024 * 1024 * 1024)),
                          prev - 1
                        ))}
                        disabled={rustfsAllocSize <= Math.ceil((storageCapacity.current_pvc_size || 0) / (1024 * 1024 * 1024))}
                      >
                        <ChevronDown size={14} />
                      </button>
                      <div className="expand-input-wrapper">
                        <input
                          type="number"
                          className="expand-input"
                          value={rustfsAllocSize}
                          min={Math.ceil((storageCapacity.current_pvc_size || 0) / (1024 * 1024 * 1024))}
                          max={Math.floor((storageCapacity.max_allocatable || 0) / (1024 * 1024 * 1024))}
                          onChange={(e) => {
                            const val = parseInt(e.target.value) || 0;
                            const minVal = Math.ceil((storageCapacity.current_pvc_size || 0) / (1024 * 1024 * 1024));
                            const maxVal = Math.floor((storageCapacity.max_allocatable || 0) / (1024 * 1024 * 1024));
                            setRustfsAllocSize(Math.min(maxVal, Math.max(minVal, val)));
                          }}
                        />
                        <span className="expand-unit">GB</span>
                      </div>
                      <button
                        className="expand-btn"
                        onClick={() => setRustfsAllocSize(prev => Math.min(
                          Math.floor((storageCapacity.max_allocatable || 0) / (1024 * 1024 * 1024)),
                          prev + 1
                        ))}
                        disabled={rustfsAllocSize >= Math.floor((storageCapacity.max_allocatable || 0) / (1024 * 1024 * 1024))}
                      >
                        <ChevronUp size={14} />
                      </button>
                    </div>
                    <input
                      type="range"
                      className="expand-slider"
                      min={Math.ceil((storageCapacity.current_pvc_size || 0) / (1024 * 1024 * 1024))}
                      max={Math.floor((storageCapacity.max_allocatable || 0) / (1024 * 1024 * 1024))}
                      value={rustfsAllocSize}
                      onChange={(e) => setRustfsAllocSize(Number(e.target.value))}
                    />
                    <div className="expand-info">
                      <span>현재: {storageCapacity.current_pvc_size_human}</span>
                      <span>최대: {storageCapacity.max_allocatable_human}</span>
                    </div>
                    {rustfsAllocSize > Math.ceil((storageCapacity.current_pvc_size || 0) / (1024 * 1024 * 1024)) && (
                      <button
                        className="btn btn-primary expand-apply-btn"
                        onClick={() => handleWorkloadAction('rustfs', 'expand', 1, rustfsAllocSize)}
                        disabled={actionLoading.rustfs?.loading}
                      >
                        {rustfsAllocSize}GB로 확장
                      </button>
                    )}
                  </div>
                )}

                {/* 스토리지 용량 정보 (실행 중일 때만 표시) */}
                {storageInfo?.status === 'connected' && (
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
                    <div className="storage-info-row">
                      <Archive size={16} color="var(--accent-green)" />
                      <span className="storage-label">사용 가능</span>
                      <span className="storage-value">{storageInfo.available_capacity_human}</span>
                    </div>
                    <div className="storage-progress">
                      <div
                        className="storage-progress-bar"
                        style={{ width: `${storageInfo.usage_percent || 0}%` }}
                      />
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
                  <WorkloadStatusBadge
                    workload={workloads.qdrant}
                    isLoading={actionLoading.qdrant?.loading}
                    actionType={actionLoading.qdrant?.action}
                  />
                </div>

                {/* Qdrant 설정 (중지 상태에서만 표시) */}
                {(workloads.qdrant?.status === 'stopped' || workloads.qdrant?.status === 'not_deployed') && (
                  <div className="workload-config-section">
                    <div className="workload-config-row">
                      <div className="config-group" style={{ flex: 2 }}>
                        <label>사용 용도</label>
                        <select
                          value={qdrantConfig.useCase}
                          onChange={(e) => handleQdrantUseCaseChange(e.target.value)}
                        >
                          {Object.entries(QDRANT_USE_CASES).map(([key, value]) => (
                            <option key={key} value={key}>
                              {value.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="use-case-description">
                      {QDRANT_USE_CASES[qdrantConfig.useCase]?.description}
                    </div>
                    <div className="workload-config-row">
                      <div className="config-group">
                        <label>스토리지 크기</label>
                        <select
                          value={qdrantConfig.storageSize}
                          onChange={(e) => setQdrantConfig({ ...qdrantConfig, storageSize: parseInt(e.target.value) })}
                        >
                          <option value="10">10 GB</option>
                          <option value="20">20 GB</option>
                          <option value="50">50 GB</option>
                          <option value="100">100 GB</option>
                          <option value="200">200 GB</option>
                          <option value="500">500 GB</option>
                        </select>
                      </div>
                      <div className="config-group">
                        <label>Replicas</label>
                        <select
                          value={qdrantConfig.replicas}
                          onChange={(e) => setQdrantConfig({ ...qdrantConfig, replicas: parseInt(e.target.value) })}
                        >
                          <option value="1">1 (단일)</option>
                          <option value="2">2 (HA 기본)</option>
                          <option value="3">3 (권장)</option>
                          <option value="5">5 (고가용성)</option>
                        </select>
                      </div>
                      <div className="config-group">
                        <label>노드 선택</label>
                        <select
                          value={qdrantConfig.nodeSelector}
                          onChange={(e) => setQdrantConfig({ ...qdrantConfig, nodeSelector: e.target.value })}
                        >
                          <option value="">자동 (스케줄러 결정)</option>
                          {nodes && nodes.map(node => (
                            <option key={node.name} value={node.name}>
                              {node.name}
                            </option>
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
                    disabled={actionLoading.qdrant?.loading || workloads.qdrant?.status === 'running' || isWorkloadPreparing(workloads.qdrant, false)}
                  >
                    <Play size={16} /> 실행
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleWorkloadAction('qdrant', 'stop')}
                    disabled={actionLoading.qdrant?.loading || (workloads.qdrant?.status === 'stopped' && !isWorkloadPreparing(workloads.qdrant, false)) || workloads.qdrant?.status === 'not_deployed'}
                  >
                    <Square size={16} /> {isWorkloadPreparing(workloads.qdrant, false) ? '취소' : '중지'}
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

              {/* ComfyUI - 이미지/동영상 생성 */}
              <div className="card workload-card comfyui-card">
                <div className="workload-header">
                  <div className="workload-info">
                    <h3>🎨 ComfyUI</h3>
                    <p>이미지/동영상 생성 API</p>
                  </div>
                  <WorkloadStatusBadge
                    workload={workloads.comfyui}
                    isLoading={actionLoading.comfyui?.loading}
                    actionType={actionLoading.comfyui?.action}
                  />
                </div>

                {/* ComfyUI 설정 (중지 상태에서만 표시) */}
                {(workloads.comfyui?.status === 'stopped' || workloads.comfyui?.status === 'not_deployed') && (
                  <div className="workload-config-section">
                    <div className="workload-config-row">
                      <div className="config-group" style={{ flex: 2 }}>
                        <label>사용 용도</label>
                        <select
                          value={comfyuiConfig.useCase}
                          onChange={(e) => handleComfyUIUseCaseChange(e.target.value)}
                        >
                          {Object.entries(COMFYUI_USE_CASES).map(([key, value]) => (
                            <option key={key} value={key}>
                              {value.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="config-group">
                        <label>GPU 수</label>
                        <select
                          value={comfyuiConfig.gpuCount}
                          onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, gpuCount: parseInt(e.target.value) })}
                        >
                          <option value="1">1 GPU</option>
                          <option value="2">2 GPU</option>
                          <option value="4">4 GPU</option>
                        </select>
                      </div>
                    </div>
                    <div className="use-case-description">
                      {COMFYUI_USE_CASES[comfyuiConfig.useCase]?.description}
                    </div>
                    <div className="workload-config-row">
                      <div className="config-group">
                        <label>노드 선택 (GPU 노드)</label>
                        <select
                          value={comfyuiConfig.nodeSelector}
                          onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, nodeSelector: e.target.value })}
                        >
                          <option value="">자동 (스케줄러 결정)</option>
                          {getGpuNodes().map(node => {
                            const gpuCount = parseInt(node.allocatable?.['nvidia.com/gpu'] || node.capacity?.['nvidia.com/gpu'] || 0);
                            const isEligible = gpuCount >= comfyuiConfig.gpuCount;
                            return (
                              <option
                                key={node.name}
                                value={node.name}
                                disabled={!isEligible}
                              >
                                {node.name} ({gpuCount} GPU){!isEligible ? ' - GPU 부족' : ''}
                              </option>
                            );
                          })}
                        </select>
                      </div>
                      <div className="config-group">
                        <label>메모리</label>
                        <select
                          value={comfyuiConfig.memoryLimit}
                          onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, memoryLimit: e.target.value })}
                        >
                          <option value="8Gi">8 GB</option>
                          <option value="16Gi">16 GB</option>
                          <option value="32Gi">32 GB</option>
                          <option value="64Gi">64 GB</option>
                        </select>
                      </div>
                      <div className="config-group">
                        <label>스토리지</label>
                        <select
                          value={comfyuiConfig.storageSize}
                          onChange={(e) => setComfyuiConfig({ ...comfyuiConfig, storageSize: parseInt(e.target.value) })}
                        >
                          <option value="50">50 GB</option>
                          <option value="100">100 GB</option>
                          <option value="200">200 GB</option>
                          <option value="500">500 GB</option>
                        </select>
                      </div>
                    </div>
                    <div className="resource-preview">
                      <div className="resource-item">
                        <MonitorDot size={14} />
                        <span>GPU {comfyuiConfig.gpuCount}개</span>
                      </div>
                      <div className="resource-item">
                        <HardDrive size={14} />
                        <span>Storage {comfyuiConfig.storageSize}GB</span>
                      </div>
                    </div>

                    {/* API 연동 안내 */}
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
                    disabled={actionLoading.comfyui?.loading || workloads.comfyui?.status === 'running' || isWorkloadPreparing(workloads.comfyui, false)}
                  >
                    <Play size={16} /> 실행
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleWorkloadAction('comfyui', 'stop')}
                    disabled={actionLoading.comfyui?.loading || (workloads.comfyui?.status === 'stopped' && !isWorkloadPreparing(workloads.comfyui, false)) || workloads.comfyui?.status === 'not_deployed'}
                  >
                    <Square size={16} /> {isWorkloadPreparing(workloads.comfyui, false) ? '취소' : '중지'}
                  </button>
                </div>

                {/* 실행 중일 때 API 상태 표시 */}
                {workloads.comfyui?.status === 'running' && !actionLoading.comfyui?.loading && (
                  <div className="api-status-panel">
                    <div className="api-status-item">
                      <span className="status-indicator active"></span>
                      <span>API 서버 활성</span>
                    </div>
                    <div className="api-links">
                      <a href="http://comfyui.local" target="_blank" rel="noopener noreferrer" className="api-link">
                        WebUI 열기
                      </a>
                      <a href="http://comfyui.local/api" target="_blank" rel="noopener noreferrer" className="api-link">
                        API Docs
                      </a>
                    </div>
                  </div>
                )}
              </div>

              {/* Logging Stack - Loki + Promtail */}
              <div className="card workload-card logging-card">
                <div className="workload-header">
                  <div className="workload-info">
                    <h3>📋 Logging Stack</h3>
                    <p>Loki + Promtail 로그 수집</p>
                  </div>
                  <div className="logging-status-badges">
                    <WorkloadStatusBadge
                      workload={workloads.loki}
                      isLoading={actionLoading.loki?.loading}
                      actionType={actionLoading.loki?.action}
                    />
                  </div>
                </div>

                <div className="logging-stack-info" style={{ flexDirection: 'column', gap: '8px' }}>
                  <div className="logging-component">
                    <div className="component-icon">📥</div>
                    <div className="component-details">
                      <div className="component-name">Promtail</div>
                      <div className="component-desc">로그 수집기 (DaemonSet)</div>
                      <span className={`component-status ${workloads.promtail?.status === 'running' ? 'running' : 'stopped'}`}>
                        {workloads.promtail?.status === 'running' ? `실행중 (${workloads.promtail?.ready_replicas || 0}개 노드)` : '중지됨'}
                      </span>
                    </div>
                  </div>
                  <div className="logging-arrow">↓</div>
                  <div className="logging-component">
                    <div className="component-icon">📦</div>
                    <div className="component-details">
                      <div className="component-name">Loki</div>
                      <div className="component-desc">로그 저장소 (중앙 집중식)</div>
                      <span className={`component-status ${workloads.loki?.status === 'running' ? 'running' : 'stopped'}`}>
                        {workloads.loki?.status === 'running' ? '실행중' : '중지됨'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* API 연동 안내 (실행 중일 때) */}
                {workloads.loki?.status === 'running' && (
                  <div className="api-info-box">
                    <div className="api-info-header">
                      <Package size={14} />
                      <span>연동 정보</span>
                    </div>
                    <div className="api-info-content">
                      <div className="api-endpoint">
                        <span className="label">Loki API:</span>
                        <code>http://loki.14.32.100.220.nip.io</code>
                      </div>
                      <div className="api-endpoint">
                        <span className="label">Internal:</span>
                        <code>http://loki.logging:3100</code>
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
                    disabled={actionLoading.loki?.loading || actionLoading.promtail?.loading || (workloads.loki?.status === 'running' && workloads.promtail?.status === 'running')}
                  >
                    <Play size={16} /> 전체 실행
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => {
                      handleWorkloadAction('loki', 'stop');
                      handleWorkloadAction('promtail', 'stop');
                    }}
                    disabled={actionLoading.loki?.loading || actionLoading.promtail?.loading || (workloads.loki?.status === 'stopped' && workloads.promtail?.status === 'stopped')}
                  >
                    <Square size={16} /> 전체 중지
                  </button>
                </div>
              </div>

              {/* Neo4j - Ontology / 그래프 DB */}
              <div className="card workload-card neo4j-card">
                <div className="workload-header">
                  <div className="workload-info">
                    <h3>🕸️ Neo4j</h3>
                    <p>그래프 DB / Ontology</p>
                  </div>
                  <WorkloadStatusBadge
                    workload={workloads.neo4j}
                    isLoading={actionLoading.neo4j?.loading}
                    actionType={actionLoading.neo4j?.action}
                  />
                </div>

                {/* Neo4j 설정 (중지 상태에서만 표시) */}
                {(workloads.neo4j?.status === 'stopped' || workloads.neo4j?.status === 'not_deployed') && (
                  <div className="workload-config-section">
                    <div className="workload-config-row">
                      <div className="config-group" style={{ flex: 2 }}>
                        <label>사용 용도</label>
                        <select
                          value={neo4jConfig.useCase}
                          onChange={(e) => handleNeo4jUseCaseChange(e.target.value)}
                        >
                          {Object.entries(NEO4J_USE_CASES).map(([key, value]) => (
                            <option key={key} value={key}>
                              {value.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="config-group">
                        <label>Replicas</label>
                        <select
                          value={neo4jConfig.replicas}
                          onChange={(e) => setNeo4jConfig({ ...neo4jConfig, replicas: parseInt(e.target.value) })}
                        >
                          <option value="1">1 (단일)</option>
                          <option value="2">2 (HA)</option>
                          <option value="3">3 (클러스터)</option>
                        </select>
                      </div>
                    </div>
                    <div className="use-case-description">
                      {NEO4J_USE_CASES[neo4jConfig.useCase]?.description}
                    </div>
                    <div className="workload-config-row">
                      <div className="config-group">
                        <label>노드 선택</label>
                        <select
                          value={neo4jConfig.nodeSelector}
                          onChange={(e) => setNeo4jConfig({ ...neo4jConfig, nodeSelector: e.target.value })}
                        >
                          <option value="">자동 (스케줄러 결정)</option>
                          {nodes && nodes.map(node => (
                            <option key={node.name} value={node.name}>
                              {node.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="config-group">
                        <label>메모리</label>
                        <select
                          value={neo4jConfig.memoryLimit}
                          onChange={(e) => setNeo4jConfig({ ...neo4jConfig, memoryLimit: e.target.value })}
                        >
                          <option value="4Gi">4 GB</option>
                          <option value="8Gi">8 GB</option>
                          <option value="16Gi">16 GB</option>
                          <option value="32Gi">32 GB</option>
                        </select>
                      </div>
                      <div className="config-group">
                        <label>스토리지</label>
                        <select
                          value={neo4jConfig.storageSize}
                          onChange={(e) => setNeo4jConfig({ ...neo4jConfig, storageSize: parseInt(e.target.value) })}
                        >
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

                    {/* API 연동 안내 */}
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
                    disabled={actionLoading.neo4j?.loading || workloads.neo4j?.status === 'running' || isWorkloadPreparing(workloads.neo4j, false)}
                  >
                    <Play size={16} /> 실행
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleWorkloadAction('neo4j', 'stop')}
                    disabled={actionLoading.neo4j?.loading || (workloads.neo4j?.status === 'stopped' && !isWorkloadPreparing(workloads.neo4j, false)) || workloads.neo4j?.status === 'not_deployed'}
                  >
                    <Square size={16} /> {isWorkloadPreparing(workloads.neo4j, false) ? '취소' : '중지'}
                  </button>
                </div>

                {/* 실행 중일 때 상태 표시 */}
                {workloads.neo4j?.status === 'running' && !actionLoading.neo4j?.loading && (
                  <div className="api-status-panel">
                    <div className="api-status-item">
                      <span className="status-indicator active"></span>
                      <span>Neo4j 활성</span>
                    </div>
                    <div className="api-links">
                      <a href="http://neo4j.local:7474" target="_blank" rel="noopener noreferrer" className="api-link">
                        Browser 열기
                      </a>
                    </div>
                  </div>
                )}
              </div>

              {/* LangGraph */}
              <div className="card workload-card langgraph-card">
                <div className="workload-header">
                  <div className="workload-info">
                    <h3>🔀 LangGraph</h3>
                    <p>Agent 오케스트레이션</p>
                  </div>
                  <span className="status-badge info">Library</span>
                </div>
                <div className="workload-config-section">
                  <div className="component-desc">
                    <p>LangChain 기반 상태 관리 멀티 에이전트 프레임워크</p>
                    <ul className="feature-list compact">
                      <li>그래프 기반 워크플로우</li>
                      <li>상태 체크포인트/복구</li>
                      <li>Human-in-the-loop</li>
                    </ul>
                  </div>

                  {/* 워크플로우 목록 및 배포 */}
                  <div className="api-info-box" style={{ marginTop: '12px' }}>
                    <div className="api-info-header">
                      <Workflow size={14} />
                      <span>워크플로우 배포</span>
                    </div>
                    <div className="api-info-content">
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                        Agent 섹션에서 만든 워크플로우를 K8s에 배포
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {[
                          { id: '1', name: 'Customer Support RAG', status: 'ready' },
                          { id: '2', name: 'Document Processing', status: 'deployed' },
                          { id: '4', name: 'AI Agent Pipeline', status: 'ready' }
                        ].map(wf => (
                          <div key={wf.id} style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '6px 8px',
                            background: 'var(--bg-secondary)',
                            borderRadius: '4px',
                            fontSize: '11px'
                          }}>
                            <span style={{ color: 'var(--text-primary)' }}>{wf.name}</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{
                                padding: '2px 6px',
                                borderRadius: '3px',
                                fontSize: '10px',
                                background: wf.status === 'deployed' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                                color: wf.status === 'deployed' ? '#16a34a' : '#3b82f6'
                              }}>
                                {wf.status === 'deployed' ? '배포됨' : '준비됨'}
                              </span>
                              {wf.status !== 'deployed' && (
                                <button
                                  onClick={() => {
                                    // TODO: 실제 배포 API 호출
                                    alert(`워크플로우 "${wf.name}" 배포를 시작합니다.`);
                                  }}
                                  style={{
                                    padding: '2px 8px',
                                    fontSize: '10px',
                                    background: '#8b5cf6',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '3px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  배포
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                      <a
                        href="#agent"
                        onClick={(e) => { e.preventDefault(); setActiveTab('agent'); }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          marginTop: '8px',
                          fontSize: '11px',
                          color: 'var(--accent-blue)',
                          textDecoration: 'none'
                        }}
                      >
                        <Plus size={12} />
                        새 워크플로우 만들기
                      </a>
                    </div>
                  </div>

                  <div className="api-info-box" style={{ marginTop: '12px' }}>
                    <div className="api-info-header">
                      <Package size={14} />
                      <span>설치 방법</span>
                    </div>
                    <div className="api-info-content">
                      <code style={{ display: 'block', padding: '8px', fontSize: '11px' }}>pip install langgraph</code>
                    </div>
                  </div>
                </div>
                <div className="integration-note">
                  <Info size={14} />
                  <span>vLLM + Qdrant + Neo4j와 통합하여 RAG Agent 구축</span>
                </div>
              </div>

              {/* Langfuse */}
              <div className="card workload-card langfuse-card">
                <div className="workload-header">
                  <div className="workload-info">
                    <h3>📊 Langfuse</h3>
                    <p>LLM Observability</p>
                  </div>
                  <span className={`status-badge ${workloads.langfuse?.status === 'running' ? 'success' : 'warning'}`}>
                    {workloads.langfuse?.status === 'running' ? '실행중' : '미배포'}
                  </span>
                </div>
                <div className="workload-config-section">
                  <div className="component-desc">
                    <p>LLM 애플리케이션 모니터링 및 분석 플랫폼</p>
                    <ul className="feature-list compact">
                      <li>Trace/Span 추적</li>
                      <li>비용 및 토큰 분석</li>
                      <li>프롬프트 버전 관리</li>
                      <li>평가 및 A/B 테스트</li>
                    </ul>
                  </div>
                  <div className="resource-preview">
                    <div className="resource-item">
                      <Database size={14} />
                      <span>PostgreSQL 필요</span>
                    </div>
                    <div className="resource-item">
                      <HardDrive size={14} />
                      <span>Storage 10GB</span>
                    </div>
                  </div>
                  <div className="api-info-box">
                    <div className="api-info-header">
                      <Package size={14} />
                      <span>연동 정보</span>
                    </div>
                    <div className="api-info-content">
                      <div className="api-endpoint">
                        <span className="label">Dashboard:</span>
                        <code>http://langfuse.14.32.100.220.nip.io</code>
                      </div>
                      <div className="api-endpoint">
                        <span className="label">API:</span>
                        <code>http://langfuse.14.32.100.220.nip.io/api</code>
                      </div>
                      <div className="api-endpoint">
                        <span className="label">Internal:</span>
                        <code>http://langfuse.langfuse:3000</code>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="workload-controls">
                  <button
                    className="btn btn-success"
                    onClick={() => handleWorkloadAction('langfuse', 'start')}
                    disabled={actionLoading.langfuse?.loading || workloads.langfuse?.status === 'running'}
                  >
                    <Play size={16} /> 배포
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleWorkloadAction('langfuse', 'stop')}
                    disabled={actionLoading.langfuse?.loading || workloads.langfuse?.status !== 'running'}
                  >
                    <Square size={16} /> 중지
                  </button>
                </div>
              </div>
            </div>
          </section>
        </>
      )}

      {activeTab === 'pods' && (
        <PodsListSection
          pods={pods}
          nodes={nodes}
          expandedNamespaces={expandedNamespaces}
          toggleNamespace={toggleNamespace}
        />
      )}

      {activeTab === 'gpu' && (
        <GpuMonitorSection
          gpuStatus={gpuStatus}
          gpuDetailed={gpuDetailed}
          nodeMetrics={nodeMetrics}
        />
      )}

      {/* Storage Tab */}
      {activeTab === 'storage' && (
        <StorageManager showToast={showToast} />
      )}

      {/* Benchmark Tab */}
      {activeTab === 'benchmark' && (
        <BenchmarkManager showToast={showToast} />
      )}

      {/* Cluster Tab */}
      {activeTab === 'cluster' && (
        <ClusterManager showToast={showToast} />
      )}

      {activeTab === 'pipeline' && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">AI 파이프라인 시각화</h2>
            <div className="pipeline-health-badge" data-status={pipelineStatus?.pipeline_health || 'partial'}>
              {pipelineStatus?.pipeline_health === 'healthy' ? '모든 컴포넌트 활성' : '일부 컴포넌트 비활성'}
            </div>
          </div>

          {/* 파이프라인 다이어그램 */}
          <div className="pipeline-diagram-container">
            <div className="pipeline-diagram">
              {/* 왼쪽: 입력 소스 */}
              <div className="pipeline-column">
                <div className="pipeline-section-title">데이터 소스</div>
                <div className={`pipeline-node ${pipelineStatus?.components?.rustfs?.status === 'running' ? 'active' : 'inactive'}`}>
                  <div className="node-icon">💾</div>
                  <div className="node-info">
                    <span className="node-name">RustFS</span>
                    <span className="node-role">오브젝트 저장소</span>
                  </div>
                  <span className={`node-status ${pipelineStatus?.components?.rustfs?.status || 'stopped'}`}>
                    {pipelineStatus?.components?.rustfs?.status === 'running' ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>

              {/* 화살표 */}
              <div className="pipeline-arrow">
                <div className={`arrow-line ${pipelineStatus?.connections?.some(c => c.from === 'rustfs' || c.to === 'rustfs') ? 'active' : ''}`}></div>
                <ArrowRightLeft size={16} />
              </div>

              {/* 중앙: 처리 계층 */}
              <div className="pipeline-column">
                <div className="pipeline-section-title">AI 처리</div>
                <div className={`pipeline-node ${pipelineStatus?.components?.vllm?.status === 'running' ? 'active' : 'inactive'}`}>
                  <div className="node-icon">🤖</div>
                  <div className="node-info">
                    <span className="node-name">vLLM</span>
                    <span className="node-role">LLM 추론</span>
                  </div>
                  <span className={`node-status ${pipelineStatus?.components?.vllm?.status || 'stopped'}`}>
                    {pipelineStatus?.components?.vllm?.status === 'running' ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className={`pipeline-node ${pipelineStatus?.components?.comfyui?.status === 'running' ? 'active' : 'inactive'}`}>
                  <div className="node-icon">🎨</div>
                  <div className="node-info">
                    <span className="node-name">ComfyUI</span>
                    <span className="node-role">이미지/동영상</span>
                  </div>
                  <span className={`node-status ${pipelineStatus?.components?.comfyui?.status || 'stopped'}`}>
                    {pipelineStatus?.components?.comfyui?.status === 'running' ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>

              {/* 화살표 */}
              <div className="pipeline-arrow">
                <div className={`arrow-line ${pipelineStatus?.connections?.some(c => c.from === 'vllm' || c.to === 'vllm') ? 'active' : ''}`}></div>
                <ArrowRightLeft size={16} />
              </div>

              {/* 오른쪽: 데이터베이스 계층 */}
              <div className="pipeline-column">
                <div className="pipeline-section-title">데이터 저장</div>
                <div className={`pipeline-node ${pipelineStatus?.components?.qdrant?.status === 'running' ? 'active' : 'inactive'}`}>
                  <div className="node-icon">🔍</div>
                  <div className="node-info">
                    <span className="node-name">Qdrant</span>
                    <span className="node-role">벡터 검색</span>
                  </div>
                  <span className={`node-status ${pipelineStatus?.components?.qdrant?.status || 'stopped'}`}>
                    {pipelineStatus?.components?.qdrant?.status === 'running' ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className={`pipeline-node ${pipelineStatus?.components?.neo4j?.status === 'running' ? 'active' : 'inactive'}`}>
                  <div className="node-icon">🕸️</div>
                  <div className="node-info">
                    <span className="node-name">Neo4j</span>
                    <span className="node-role">그래프 DB</span>
                  </div>
                  <span className={`node-status ${pipelineStatus?.components?.neo4j?.status || 'stopped'}`}>
                    {pipelineStatus?.components?.neo4j?.status === 'running' ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* 이벤트 및 로그 섹션 */}
          <div className="pipeline-logs-section">
            <div className="logs-grid">
              {/* 최근 이벤트 */}
              <div className="card events-card">
                <div className="card-header">
                  <h3><AlertCircle size={16} /> 클러스터 이벤트</h3>
                  <div className="event-stats">
                    <span className="stat warning">{clusterEvents?.warning_count || 0} 경고</span>
                    <span className="stat normal">{clusterEvents?.normal_count || 0} 정상</span>
                  </div>
                </div>
                <div className="events-list">
                  {(clusterEvents?.events || []).slice(0, 15).map((event, idx) => (
                    <div key={idx} className={`event-item ${event.type?.toLowerCase()}`}>
                      <div className="event-header">
                        <span className={`event-type ${event.type?.toLowerCase()}`}>{event.type}</span>
                        <span className="event-reason">{event.reason}</span>
                        <span className="event-time">
                          {event.last_timestamp ? new Date(event.last_timestamp).toLocaleTimeString() : '-'}
                        </span>
                      </div>
                      <div className="event-message">{event.message}</div>
                      <div className="event-source">
                        {event.object?.kind}: {event.object?.name} ({event.namespace})
                      </div>
                    </div>
                  ))}
                  {(!clusterEvents?.events || clusterEvents.events.length === 0) && (
                    <div className="no-events">이벤트 없음</div>
                  )}
                </div>
              </div>

              {/* 파이프라인 연결 상태 */}
              <div className="card connections-card">
                <div className="card-header">
                  <h3><Link2 size={16} /> 연결 상태</h3>
                </div>
                <div className="connections-list">
                  {pipelineStatus?.components && Object.entries(pipelineStatus.components).map(([key, comp]) => (
                    <div key={key} className={`connection-item ${comp.status}`}>
                      <span className="conn-icon">{comp.icon}</span>
                      <div className="conn-info">
                        <span className="conn-name">{comp.name}</span>
                        <span className="conn-role">{comp.role}</span>
                      </div>
                      <span className={`conn-badge ${comp.status}`}>
                        {comp.status === 'running' ? '연결' : '미연결'}
                      </span>
                      <span className="conn-targets-inline">
                        → {comp.connections && comp.connections.length > 0
                          ? comp.connections.map(c => pipelineStatus.components[c]?.name || c).join(', ')
                          : '-'}
                      </span>
                    </div>
                  ))}
                </div>

                {/* 최근 에러 */}
                <div className="recent-errors">
                  <h4><AlertTriangle size={14} /> 최근 에러</h4>
                  {pipelineStatus?.recent_errors && pipelineStatus.recent_errors.length > 0 ? (
                    pipelineStatus.recent_errors.map((err, idx) => (
                      <div key={idx} className="error-item">
                        <span className="error-source">{err.source}</span>
                        <span className="error-reason">{err.reason}</span>
                        <span className="error-message">{err.message}</span>
                      </div>
                    ))
                  ) : (
                    <div className="no-errors">
                      <CheckCircle size={14} />
                      <span>최근 에러 없음</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* K3s 로깅 파이프라인 아키텍처 */}
          <div className="card k3s-logging-arch-card">
            <div className="card-header">
              <h3><GitBranch size={18} /> K3s 로깅 파이프라인 아키텍처</h3>
              <span className="status-badge success">운영중</span>
            </div>

            {/* 전체 파이프라인 다이어그램 */}
            <div className="logging-arch-diagram">
              {/* 1단계: 로그 소스 (K8s 컴포넌트) */}
              <div className="logging-arch-layer">
                <div className="layer-header">
                  <span className="layer-num">1</span>
                  <span className="layer-title">로그 소스</span>
                  <span className="layer-subtitle">K3s 클러스터 컴포넌트</span>
                </div>
                <div className="layer-components">
                  <div className="log-source-item">
                    <span className="source-icon">🤖</span>
                    <div className="source-info">
                      <span className="source-name">vLLM</span>
                      <span className="source-ns">ai-workloads</span>
                    </div>
                    <span className={`source-status ${pipelineStatus?.components?.vllm?.status === 'running' ? 'running' : 'stopped'}`}></span>
                  </div>
                  <div className="log-source-item">
                    <span className="source-icon">🧠</span>
                    <div className="source-info">
                      <span className="source-name">Embedding</span>
                      <span className="source-ns">ai-workloads</span>
                    </div>
                    <span className={`source-status ${pipelineStatus?.components?.embedding?.status === 'running' ? 'running' : 'stopped'}`}></span>
                  </div>
                  <div className="log-source-item">
                    <span className="source-icon">🔍</span>
                    <div className="source-info">
                      <span className="source-name">Qdrant</span>
                      <span className="source-ns">ai-workloads</span>
                    </div>
                    <span className={`source-status ${pipelineStatus?.components?.qdrant?.status === 'running' ? 'running' : 'stopped'}`}></span>
                  </div>
                  <div className="log-source-item">
                    <span className="source-icon">🎨</span>
                    <div className="source-info">
                      <span className="source-name">ComfyUI</span>
                      <span className="source-ns">ai-workloads</span>
                    </div>
                    <span className={`source-status ${pipelineStatus?.components?.comfyui?.status === 'running' ? 'running' : 'stopped'}`}></span>
                  </div>
                  <div className="log-source-item">
                    <span className="source-icon">🕸️</span>
                    <div className="source-info">
                      <span className="source-name">Neo4j</span>
                      <span className="source-ns">ai-workloads</span>
                    </div>
                    <span className={`source-status ${pipelineStatus?.components?.neo4j?.status === 'running' ? 'running' : 'stopped'}`}></span>
                  </div>
                  <div className="log-source-item">
                    <span className="source-icon">💾</span>
                    <div className="source-info">
                      <span className="source-name">RustFS</span>
                      <span className="source-ns">rustfs</span>
                    </div>
                    <span className={`source-status ${pipelineStatus?.components?.rustfs?.status === 'running' ? 'running' : 'stopped'}`}></span>
                  </div>
                  <div className="log-source-item">
                    <span className="source-icon">📊</span>
                    <div className="source-info">
                      <span className="source-name">Dashboard</span>
                      <span className="source-ns">dashboard</span>
                    </div>
                    <span className="source-status running"></span>
                  </div>
                </div>
              </div>

              <div className="logging-arch-arrow">
                <div className="arrow-line"></div>
                <span className="arrow-label">stdout/stderr → /var/log/pods/</span>
              </div>

              {/* 2단계: 수집 계층 - Promtail */}
              <div className="logging-arch-layer">
                <div className="layer-header">
                  <span className="layer-num">2</span>
                  <span className="layer-title">로그 수집 (Promtail)</span>
                  <span className="layer-subtitle">DaemonSet으로 각 노드에서 수집</span>
                </div>
                <div className="layer-components horizontal">
                  <div className="collector-component promtail">
                    <div className="collector-icon">📥</div>
                    <div className="collector-info">
                      <strong>Promtail</strong>
                      <span>Loki 전용 수집기</span>
                      <span className={`collector-status ${workloads?.promtail?.status === 'running' ? 'running' : 'stopped'}`}>
                        {workloads?.promtail?.status === 'running' ? '실행중' : '중지됨'}
                      </span>
                    </div>
                    <div className="collector-config">
                      <code>scrape → /var/log/pods/**/*.log</code>
                    </div>
                  </div>
                  <div className="collector-feature">
                    <span className="feature-tag">파싱</span>
                    <span className="feature-desc">CRI, JSON, Regex Pipeline</span>
                  </div>
                  <div className="collector-feature">
                    <span className="feature-tag">라벨</span>
                    <span className="feature-desc">namespace, pod, container 자동 추가</span>
                  </div>
                  <div className="collector-feature">
                    <span className="feature-tag">메트릭</span>
                    <span className="feature-desc">수집 상태 Prometheus 노출</span>
                  </div>
                </div>
              </div>

              <div className="logging-arch-arrow">
                <div className="arrow-line"></div>
                <span className="arrow-label">HTTP Push → Loki API (/loki/api/v1/push)</span>
              </div>

              {/* 3단계: 처리 계층 */}
              <div className="logging-arch-layer">
                <div className="layer-header">
                  <span className="layer-num">3</span>
                  <span className="layer-title">로그 처리 및 분석</span>
                  <span className="layer-subtitle">집계, 분류, AI 분석</span>
                </div>
                <div className="layer-components processing">
                  <div className="processing-box">
                    <div className="processing-header">
                      <span className="processing-icon">⚙️</span>
                      <strong>로그 집계</strong>
                    </div>
                    <ul className="processing-list">
                      <li>앱별 로그 분류</li>
                      <li>에러/경고/정보 분류</li>
                      <li>타임스탬프 정규화</li>
                      <li>중복 제거</li>
                    </ul>
                  </div>
                  <div className="processing-arrow">→</div>
                  <div className="processing-box highlight">
                    <div className="processing-header">
                      <span className="processing-icon">🤖</span>
                      <strong>LLM 분석</strong>
                    </div>
                    <ul className="processing-list">
                      <li>에러 패턴 감지</li>
                      <li>근본 원인 분석</li>
                      <li>해결책 제안</li>
                      <li>트렌드 요약</li>
                    </ul>
                  </div>
                  <div className="processing-arrow">→</div>
                  <div className="processing-box">
                    <div className="processing-header">
                      <span className="processing-icon">📊</span>
                      <strong>메트릭 생성</strong>
                    </div>
                    <ul className="processing-list">
                      <li>에러율 통계</li>
                      <li>응답시간 분포</li>
                      <li>앱별 로그량</li>
                      <li>이상치 탐지</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="logging-arch-arrow split">
                <div className="arrow-branch">
                  <div className="arrow-line"></div>
                  <span className="arrow-label">Alert Rules</span>
                </div>
                <div className="arrow-branch">
                  <div className="arrow-line"></div>
                  <span className="arrow-label">Storage API</span>
                </div>
                <div className="arrow-branch">
                  <div className="arrow-line"></div>
                  <span className="arrow-label">Knowledge Base</span>
                </div>
              </div>

              {/* 4단계: 출력 계층 */}
              <div className="logging-arch-layer outputs">
                <div className="layer-header">
                  <span className="layer-num">4</span>
                  <span className="layer-title">출력 및 액션</span>
                  <span className="layer-subtitle">알림, 저장, 학습</span>
                </div>
                <div className="layer-components output-grid">
                  {/* 알림 */}
                  <div className="output-box alert">
                    <div className="output-header">
                      <Bell size={16} />
                      <strong>알림 전송</strong>
                    </div>
                    <div className="output-content">
                      <div className="output-target">
                        <span className="target-icon">💬</span>
                        <span>Slack #k3s-alerts</span>
                        <span className="target-status connected">연결됨</span>
                      </div>
                      <div className="output-target">
                        <span className="target-icon">📧</span>
                        <span>Email 알림</span>
                        <span className="target-status connected">활성</span>
                      </div>
                      <div className="alert-rule-preview">
                        <code>if error_count &gt; 5 in 5min → Slack</code>
                      </div>
                    </div>
                  </div>

                  {/* 저장소 */}
                  <div className="output-box storage">
                    <div className="output-header">
                      <Archive size={16} />
                      <strong>로그 저장</strong>
                    </div>
                    <div className="output-content">
                      <div className="storage-tier">
                        <span className="tier-label">Hot</span>
                        <span className="tier-desc">최근 7일 - 빠른 검색</span>
                      </div>
                      <div className="storage-tier">
                        <span className="tier-label">Warm</span>
                        <span className="tier-desc">30일 - 압축 저장</span>
                      </div>
                      <div className="storage-tier">
                        <span className="tier-label">Cold</span>
                        <span className="tier-desc">90일 - RustFS 백업</span>
                      </div>
                      <div className="storage-stats-mini">
                        <span>압축률: 81%</span>
                        <span>용량: 8.7GB</span>
                      </div>
                    </div>
                  </div>

                  {/* 학습 */}
                  <div className="output-box learning">
                    <div className="output-header">
                      <BookOpen size={16} />
                      <strong>지식 베이스</strong>
                    </div>
                    <div className="output-content">
                      <div className="learning-item">
                        <span className="learning-icon">✅</span>
                        <span>해결된 문제 저장</span>
                      </div>
                      <div className="learning-item">
                        <span className="learning-icon">🔄</span>
                        <span>유사 패턴 자동 매칭</span>
                      </div>
                      <div className="learning-item">
                        <span className="learning-icon">📈</span>
                        <span>해결 시간 단축</span>
                      </div>
                      <div className="learning-stats">
                        <span>학습된 케이스: 127건</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 구성 요소 상세 - 2열 그리드 */}
          <div className="logging-detail-grid">
            {/* K8s 리소스 구성 */}
            <div className="card logging-k8s-config-card">
              <div className="card-header">
                <h3><Layers size={18} /> K8s 리소스 구성</h3>
              </div>
              <div className="k8s-resources-list">
                <div className="k8s-resource">
                  <div className="resource-header">
                    <span className="resource-kind">DaemonSet</span>
                    <span className="resource-name">promtail</span>
                    <span className="resource-ns">logging</span>
                    <span className={`resource-status ${workloads?.promtail?.status === 'running' ? 'running' : 'stopped'}`}>
                      {workloads?.promtail?.status === 'running' ? `● ${workloads?.promtail?.ready_replicas || 0} pods` : '○ stopped'}
                    </span>
                  </div>
                  <div className="resource-spec">
                    <code>
{`apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: promtail
  namespace: logging
spec:
  selector:
    matchLabels:
      app: promtail
  template:
    spec:
      containers:
      - name: promtail
        image: grafana/promtail:2.9.0
        args:
          - -config.file=/etc/promtail/promtail.yaml
        volumeMounts:
        - name: logs
          mountPath: /var/log
        - name: pods
          mountPath: /var/log/pods
          readOnly: true`}
                    </code>
                  </div>
                </div>
                <div className="k8s-resource">
                  <div className="resource-header">
                    <span className="resource-kind">Deployment</span>
                    <span className="resource-name">loki</span>
                    <span className="resource-ns">logging</span>
                    <span className={`resource-status ${workloads?.loki?.status === 'running' ? 'running' : 'stopped'}`}>
                      {workloads?.loki?.status === 'running' ? '● running' : '○ stopped'}
                    </span>
                  </div>
                  <div className="resource-spec">
                    <code>
{`apiVersion: apps/v1
kind: Deployment
metadata:
  name: loki
  namespace: logging
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: loki
        image: grafana/loki:2.9.0
        ports:
        - containerPort: 3100
        volumeMounts:
        - name: storage
          mountPath: /loki`}
                    </code>
                  </div>
                </div>
                <div className="k8s-resource">
                  <div className="resource-header">
                    <span className="resource-kind">ConfigMap</span>
                    <span className="resource-name">promtail-config</span>
                    <span className="resource-ns">logging</span>
                  </div>
                  <div className="resource-spec">
                    <code>
{`server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod`}
                    </code>
                  </div>
                </div>
              </div>
            </div>

            {/* LLM 분석 파이프라인 */}
            <div className="card llm-pipeline-card">
              <div className="card-header">
                <h3><Brain size={18} /> LLM 분석 파이프라인</h3>
                <span className="status-badge success">vLLM 연동</span>
              </div>
              <div className="llm-pipeline-flow">
                <div className="llm-step">
                  <div className="llm-step-num">1</div>
                  <div className="llm-step-content">
                    <strong>로그 배치 수집</strong>
                    <p>5분 간격 또는 에러 발생 시 즉시</p>
                  </div>
                </div>
                <div className="llm-step">
                  <div className="llm-step-num">2</div>
                  <div className="llm-step-content">
                    <strong>컨텍스트 구성</strong>
                    <p>앱 정보 + 최근 변경사항 + 관련 로그</p>
                  </div>
                </div>
                <div className="llm-step">
                  <div className="llm-step-num">3</div>
                  <div className="llm-step-content">
                    <strong>vLLM 분석 요청</strong>
                    <p>프롬프트: 에러 분석 + 해결책 제안</p>
                  </div>
                </div>
                <div className="llm-step">
                  <div className="llm-step-num">4</div>
                  <div className="llm-step-content">
                    <strong>결과 처리</strong>
                    <p>알림 생성 / 대시보드 표시 / DB 저장</p>
                  </div>
                </div>
              </div>
              <div className="llm-example">
                <div className="example-header">
                  <span className="example-label">분석 예시</span>
                </div>
                <div className="example-input">
                  <strong>입력:</strong> vLLM에서 "CUDA out of memory" 에러 3회 발생
                </div>
                <div className="example-output">
                  <strong>LLM 분석:</strong>
                  <ul>
                    <li><strong>원인:</strong> batch_size=64로 설정되어 GPU 메모리 초과</li>
                    <li><strong>해결책:</strong> batch_size를 32로 조정 권장</li>
                    <li><strong>추가:</strong> gradient_checkpointing 활성화 고려</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* 해결 히스토리 및 학습 데이터 */}
          <div className="card resolution-knowledge-card">
            <div className="card-header">
              <h3><CheckCircle size={18} /> 해결 히스토리 &amp; 학습 데이터</h3>
              <div className="history-stats">
                <span className="stat-item">총 127건</span>
                <span className="stat-item">이번 달 15건</span>
                <span className="stat-item success">자동 해결 32%</span>
              </div>
            </div>
            <div className="resolution-timeline">
              <div className="timeline-item resolved">
                <div className="timeline-marker">✅</div>
                <div className="timeline-content">
                  <div className="timeline-header">
                    <span className="timeline-app">vLLM</span>
                    <span className="timeline-type">메모리 에러</span>
                    <span className="timeline-date">2026-01-08 14:30</span>
                  </div>
                  <div className="timeline-problem">CUDA OOM 반복 발생 (batch_size=64)</div>
                  <div className="timeline-solution">
                    <strong>해결:</strong> batch_size 32로 조정, gradient_checkpointing 활성화
                  </div>
                  <div className="timeline-meta">
                    <span className="meta-item"><BookOpen size={12} /> 학습 데이터 저장</span>
                    <span className="meta-item">🔄 유사 패턴 3회 자동 감지</span>
                  </div>
                </div>
              </div>
              <div className="timeline-item resolved">
                <div className="timeline-marker">✅</div>
                <div className="timeline-content">
                  <div className="timeline-header">
                    <span className="timeline-app">Qdrant</span>
                    <span className="timeline-type">성능 이슈</span>
                    <span className="timeline-date">2026-01-07 09:15</span>
                  </div>
                  <div className="timeline-problem">검색 쿼리 지연 (평균 5초 이상)</div>
                  <div className="timeline-solution">
                    <strong>해결:</strong> HNSW 인덱스 파라미터 조정 (ef_construct: 128→256)
                  </div>
                  <div className="timeline-meta">
                    <span className="meta-item"><BookOpen size={12} /> 학습 데이터 저장</span>
                    <span className="meta-item">📊 성능 임계값 추가</span>
                  </div>
                </div>
              </div>
              <div className="timeline-item analyzing">
                <div className="timeline-marker">🔄</div>
                <div className="timeline-content">
                  <div className="timeline-header">
                    <span className="timeline-app">ComfyUI</span>
                    <span className="timeline-type">타임아웃</span>
                    <span className="timeline-date">2026-01-08 16:45</span>
                  </div>
                  <div className="timeline-problem">워크플로우 실행 시 간헐적 타임아웃</div>
                  <div className="timeline-analysis">
                    <strong>LLM 분석중...</strong> 예상 원인: 동시 요청 과다로 인한 큐 지연
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {activeTab === 'qdrant' && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">Vector DB (Qdrant)</h2>
            <span className="section-subtitle">벡터 임베딩 저장 및 유사도 검색</span>
          </div>

          <div className="grid grid-3">
            {/* Qdrant 상태 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><Database size={18} /> Qdrant 상태</h3>
                <span className={`status-badge ${pipelineStatus?.components?.qdrant?.status === 'running' ? 'success' : 'warning'}`}>
                  {pipelineStatus?.components?.qdrant?.status === 'running' ? '실행중' : '중지됨'}
                </span>
              </div>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">포트</span>
                  <span className="stat-value">6333 (REST), 6334 (gRPC)</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">네임스페이스</span>
                  <span className="stat-value">ai-workloads</span>
                </div>
              </div>
            </div>

            {/* 용도 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><Target size={18} /> 주요 용도</h3>
              </div>
              <div className="use-case-list">
                <div className="use-case-item">
                  <span className="use-case-icon">🔍</span>
                  <div>
                    <strong>RAG (Retrieval-Augmented Generation)</strong>
                    <p>문서 임베딩 저장 후 유사 문서 검색</p>
                  </div>
                </div>
                <div className="use-case-item">
                  <span className="use-case-icon">🤖</span>
                  <div>
                    <strong>Agent Context</strong>
                    <p>AI 에이전트 대화 컨텍스트 저장</p>
                  </div>
                </div>
                <div className="use-case-item">
                  <span className="use-case-icon">🖼️</span>
                  <div>
                    <strong>이미지/멀티모달 검색</strong>
                    <p>이미지 임베딩 기반 유사 이미지 검색</p>
                  </div>
                </div>
              </div>
            </div>

            {/* API 연동 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><ExternalLink size={18} /> API 연동</h3>
              </div>
              <div className="api-info">
                <div className="api-endpoint">
                  <label>REST API (외부)</label>
                  <code>http://qdrant.14.32.100.220.nip.io</code>
                </div>
                <div className="api-endpoint">
                  <label>REST API (내부)</label>
                  <code>http://qdrant.ai-workloads:6333</code>
                </div>
                <div className="api-endpoint">
                  <label>gRPC (내부)</label>
                  <code>qdrant.ai-workloads:6334</code>
                </div>
              </div>
              <div className="code-example">
                <h4>Python 예제 (외부 접근)</h4>
                <pre>{`from qdrant_client import QdrantClient
# 외부에서 접근 시
client = QdrantClient("qdrant.14.32.100.220.nip.io", port=80)

# 컬렉션 생성
client.create_collection(
    collection_name="documents",
    vectors_config={"size": 1536, "distance": "Cosine"}
)

# 벡터 검색
results = client.search(
    collection_name="documents",
    query_vector=embedding,
    limit=10
)`}</pre>
              </div>
            </div>
          </div>

          {/* 임베딩 모델 섹션 */}
          <div className="card embedding-overview-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Zap size={18} /> 임베딩이란?</h3>
            </div>
            <div className="embedding-concept">
              {/* 전체 RAG 파이프라인 플로우 */}
              <div className="embedding-pipeline-title">
                <h4>📋 문서에서 벡터까지: 전체 파이프라인</h4>
              </div>
              <div className="embedding-flow-visual extended">
                {/* 1. 문서 수집 */}
                <div className="embedding-step source">
                  <div className="embedding-step-icon">📁</div>
                  <div className="embedding-step-label">문서 수집</div>
                  <div className="embedding-step-example">PDF, DOCX, HTML, TXT</div>
                </div>
                <div className="embedding-arrow">→</div>
                {/* 2. 파싱 */}
                <div className="embedding-step">
                  <div className="embedding-step-icon">🔧</div>
                  <div className="embedding-step-label">파싱 (Parsing)</div>
                  <div className="embedding-step-example">텍스트 추출</div>
                </div>
                <div className="embedding-arrow">→</div>
                {/* 3. 전처리 */}
                <div className="embedding-step">
                  <div className="embedding-step-icon">🧹</div>
                  <div className="embedding-step-label">전처리</div>
                  <div className="embedding-step-example">정규화, 클리닝</div>
                </div>
                <div className="embedding-arrow">→</div>
                {/* 4. 청킹 */}
                <div className="embedding-step">
                  <div className="embedding-step-icon">✂️</div>
                  <div className="embedding-step-label">청킹 (Chunking)</div>
                  <div className="embedding-step-example">512~1024 토큰</div>
                </div>
                <div className="embedding-arrow">→</div>
                {/* 5. 임베딩 */}
                <div className="embedding-step highlight">
                  <div className="embedding-step-icon">🧠</div>
                  <div className="embedding-step-label">임베딩</div>
                  <div className="embedding-step-example">벡터 변환</div>
                </div>
                <div className="embedding-arrow">→</div>
                {/* 6. 저장 */}
                <div className="embedding-step">
                  <div className="embedding-step-icon">💾</div>
                  <div className="embedding-step-label">벡터 DB 저장</div>
                  <div className="embedding-step-example">Qdrant</div>
                </div>
              </div>

              {/* 각 단계 상세 설명 */}
              <div className="pipeline-details">
                <div className="pipeline-step-detail">
                  <div className="step-number">1</div>
                  <div className="step-content">
                    <strong>문서 수집 (Document Ingestion)</strong>
                    <p>다양한 형식의 원본 문서를 수집합니다. 지원 포맷: PDF, Word (.docx), HTML, Markdown, 텍스트 파일, 웹 크롤링 데이터 등</p>
                  </div>
                </div>
                <div className="pipeline-step-detail">
                  <div className="step-number">2</div>
                  <div className="step-content">
                    <strong>파싱 (Parsing & Extraction)</strong>
                    <p>문서에서 텍스트를 추출합니다. PDF의 경우 PyMuPDF/pdfplumber, Word는 python-docx, HTML은 BeautifulSoup 등 사용. 테이블, 이미지 캡션, 메타데이터도 추출</p>
                  </div>
                </div>
                <div className="pipeline-step-detail">
                  <div className="step-number">3</div>
                  <div className="step-content">
                    <strong>전처리 (Preprocessing)</strong>
                    <p>텍스트 정규화: 특수문자 제거, 공백 정리, 인코딩 통일(UTF-8), 불용어 처리(선택적), 언어 감지. 노이즈 제거로 임베딩 품질 향상</p>
                  </div>
                </div>
                <div className="pipeline-step-detail">
                  <div className="step-number">4</div>
                  <div className="step-content">
                    <strong>청킹 (Chunking)</strong>
                    <p>긴 문서를 적절한 크기로 분할. 전략: 고정 크기(512토큰), 문장 기반, 의미 기반(Semantic), 오버랩(10~20%). 모델의 max_token 제한 고려</p>
                  </div>
                </div>
                <div className="pipeline-step-detail">
                  <div className="step-number">5</div>
                  <div className="step-content">
                    <strong>임베딩 (Embedding)</strong>
                    <p>각 청크를 고차원 벡터로 변환. 의미적으로 유사한 텍스트는 벡터 공간에서 가까운 위치에 배치됨</p>
                  </div>
                </div>
                <div className="pipeline-step-detail">
                  <div className="step-number">6</div>
                  <div className="step-content">
                    <strong>벡터 DB 저장 (Storage)</strong>
                    <p>벡터와 메타데이터를 Qdrant에 저장. 인덱싱(HNSW)으로 빠른 유사도 검색 지원. 필터링을 위한 페이로드도 함께 저장</p>
                  </div>
                </div>
              </div>

              <div className="embedding-explanation">
                <p><strong>핵심 개념:</strong> 임베딩은 텍스트의 <em>의미</em>를 고차원 벡터 공간의 좌표로 변환합니다.</p>
                <p>의미가 비슷한 문장은 벡터 공간에서 <em>가까운 위치</em>에 배치되어, 키워드가 다르더라도 유사한 의미의 문서를 찾을 수 있습니다.</p>
              </div>
            </div>
          </div>

          <div className="grid grid-3" style={{ marginTop: '20px' }}>
            {/* 모델 목록 */}
            <div className="card">
              <div className="card-header">
                <h3><Layers size={18} /> 지원 임베딩 모델</h3>
              </div>
              <div className="model-list">
                <div
                  className={`model-item clickable ${selectedEmbeddingModel === 'bge-m3' ? 'active' : ''}`}
                  onClick={() => setSelectedEmbeddingModel('bge-m3')}
                >
                  <div className="model-info">
                    <strong>BAAI/bge-m3</strong>
                    <span className="model-badge recommended">권장</span>
                  </div>
                  <div className="model-specs">
                    <span>1024 dim</span>
                    <span>다국어</span>
                    <span>568M params</span>
                  </div>
                  <p className="model-desc">한국어 포함 100+ 언어 지원, Dense/Sparse/Multi-vector 통합</p>
                </div>
                <div
                  className={`model-item clickable ${selectedEmbeddingModel === 'kure' ? 'active' : ''}`}
                  onClick={() => setSelectedEmbeddingModel('kure')}
                >
                  <div className="model-info">
                    <strong>nlpai-lab/KURE-v1</strong>
                    <span className="model-badge korean">한국어</span>
                  </div>
                  <div className="model-specs">
                    <span>1024 dim</span>
                    <span>한국어 특화</span>
                    <span>326M params</span>
                  </div>
                  <p className="model-desc">KAIST NLP 연구실의 한국어 특화 임베딩 모델</p>
                </div>
                <div
                  className={`model-item clickable ${selectedEmbeddingModel === 'e5-large' ? 'active' : ''}`}
                  onClick={() => setSelectedEmbeddingModel('e5-large')}
                >
                  <div className="model-info">
                    <strong>intfloat/multilingual-e5-large</strong>
                  </div>
                  <div className="model-specs">
                    <span>1024 dim</span>
                    <span>다국어</span>
                    <span>560M params</span>
                  </div>
                  <p className="model-desc">Microsoft E5 모델, 다국어 임베딩</p>
                </div>
                <div
                  className={`model-item clickable ${selectedEmbeddingModel === 'minilm' ? 'active' : ''}`}
                  onClick={() => setSelectedEmbeddingModel('minilm')}
                >
                  <div className="model-info">
                    <strong>sentence-transformers/all-MiniLM-L6-v2</strong>
                  </div>
                  <div className="model-specs">
                    <span>384 dim</span>
                    <span>영어</span>
                    <span>22M params</span>
                  </div>
                  <p className="model-desc">경량 모델, 빠른 추론 속도</p>
                </div>
              </div>
            </div>

            {/* 현재 설정 - 선택된 모델에 따라 동적 변경 */}
            <div className="card">
              <div className="card-header">
                <h3><Settings size={18} /> 모델 설정</h3>
                <span className="status-badge success">선택됨</span>
              </div>
              <div className="selected-model-name">
                <strong>{embeddingModels[selectedEmbeddingModel]?.name}</strong>
              </div>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">벡터 차원</span>
                  <span className="stat-value">{embeddingModels[selectedEmbeddingModel]?.dimension}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">최대 토큰</span>
                  <span className="stat-value">{embeddingModels[selectedEmbeddingModel]?.maxTokens}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">지원 언어</span>
                  <span className="stat-value">{embeddingModels[selectedEmbeddingModel]?.language}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">파라미터</span>
                  <span className="stat-value">{embeddingModels[selectedEmbeddingModel]?.params}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">배치 크기</span>
                  <span className="stat-value">{embeddingModels[selectedEmbeddingModel]?.batchSize}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">추론 장치</span>
                  <span className="stat-value">{embeddingModels[selectedEmbeddingModel]?.device}</span>
                </div>
              </div>
              <div className="model-features" style={{ marginTop: '12px' }}>
                <span className="stat-label">지원 기능</span>
                <div className="feature-tags">
                  {embeddingModels[selectedEmbeddingModel]?.features.map((feat, idx) => (
                    <span key={idx} className="feature-tag">{feat}</span>
                  ))}
                </div>
              </div>
              <div className="model-description" style={{ marginTop: '12px' }}>
                <p>{embeddingModels[selectedEmbeddingModel]?.description}</p>
              </div>
            </div>

            {/* 성능 지표 - 선택된 모델에 따라 동적 변경 */}
            <div className="card">
              <div className="card-header">
                <h3><BarChart3 size={18} /> 성능 벤치마크</h3>
              </div>
              <div className="benchmark-results">
                <div className="benchmark-item">
                  <div className="benchmark-header">
                    <span>MTEB (한국어)</span>
                    <span className="benchmark-score">{embeddingModels[selectedEmbeddingModel]?.mteb}</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${embeddingModels[selectedEmbeddingModel]?.mteb}%`, background: 'var(--accent-green)' }}></div>
                  </div>
                </div>
                <div className="benchmark-item">
                  <div className="benchmark-header">
                    <span>Retrieval Accuracy</span>
                    <span className="benchmark-score">{embeddingModels[selectedEmbeddingModel]?.retrieval}%</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${embeddingModels[selectedEmbeddingModel]?.retrieval}%`, background: 'var(--accent-blue)' }}></div>
                  </div>
                </div>
                <div className="benchmark-item">
                  <div className="benchmark-header">
                    <span>Semantic Similarity</span>
                    <span className="benchmark-score">{embeddingModels[selectedEmbeddingModel]?.similarity}%</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${embeddingModels[selectedEmbeddingModel]?.similarity}%`, background: 'var(--accent-purple)' }}></div>
                  </div>
                </div>
                <div className="benchmark-item">
                  <div className="benchmark-header">
                    <span>처리 속도</span>
                    <span className="benchmark-score">{embeddingModels[selectedEmbeddingModel]?.speed}</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: selectedEmbeddingModel === 'minilm' ? '100%' : selectedEmbeddingModel === 'kure' ? '85%' : '70%', background: 'var(--accent-yellow)' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 실시간 임베딩 실행 데모 */}
          <EmbeddingLiveDemo />

          {/* 임베딩 모델 파인튜닝 가이드 */}
          <div className="card finetuning-guide" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Zap size={18} /> 임베딩 모델 파인튜닝 가이드</h3>
            </div>
            <div className="finetuning-content">
              {/* 파인튜닝이 필요한 경우 */}
              <div className="finetuning-section">
                <h4>언제 파인튜닝이 필요한가?</h4>
                <div className="when-to-finetune">
                  <div className="finetune-case good">
                    <div className="case-header">
                      <CheckCircle size={16} />
                      <strong>파인튜닝 권장</strong>
                    </div>
                    <ul>
                      <li>도메인 특화 용어가 많은 경우 (법률, 의료, 기술 문서)</li>
                      <li>기존 모델의 검색 정확도가 낮을 때</li>
                      <li>특정 언어나 방언에 최적화가 필요할 때</li>
                      <li>사내 전문 용어/약어를 이해해야 할 때</li>
                      <li>질문-문서 매칭 품질 향상이 필요할 때</li>
                    </ul>
                  </div>
                  <div className="finetune-case bad">
                    <div className="case-header">
                      <XCircle size={16} />
                      <strong>파인튜닝 불필요</strong>
                    </div>
                    <ul>
                      <li>일반적인 텍스트 검색 (뉴스, 블로그 등)</li>
                      <li>데이터가 충분하지 않을 때 (&lt;1000 쌍)</li>
                      <li>빠른 프로토타이핑이 목적일 때</li>
                      <li>이미 좋은 성능을 보이는 경우</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* 데이터 구조 */}
              <div className="finetuning-section">
                <h4>파인튜닝 데이터 구조</h4>
                <div className="data-structure">
                  <div className="data-format">
                    <h5>Triplet 형식 (권장)</h5>
                    <pre className="code-block">{`{
  "query": "쿠버네티스 파드 재시작 방법",
  "positive": "kubectl rollout restart deployment...",
  "negative": "도커 컨테이너 빌드하는 방법..."
}`}</pre>
                    <p className="format-desc">쿼리와 관련 문서(positive), 무관 문서(negative)로 구성</p>
                  </div>
                  <div className="data-format">
                    <h5>Pair 형식</h5>
                    <pre className="code-block">{`{
  "sentence1": "K8s에서 HPA 설정하기",
  "sentence2": "Horizontal Pod Autoscaler 구성...",
  "label": 1.0
}`}</pre>
                    <p className="format-desc">두 문장의 유사도 점수 (0~1)로 레이블링</p>
                  </div>
                </div>
              </div>

              {/* 좋은 데이터 기준 */}
              <div className="finetuning-section">
                <h4>좋은 학습 데이터의 조건</h4>
                <div className="data-quality-grid">
                  <div className="quality-item">
                    <div className="quality-icon">📊</div>
                    <strong>충분한 양</strong>
                    <p>최소 1,000~10,000개 이상의 쿼리-문서 쌍</p>
                  </div>
                  <div className="quality-item">
                    <div className="quality-icon">🎯</div>
                    <strong>다양성</strong>
                    <p>다양한 쿼리 유형과 문서 스타일 포함</p>
                  </div>
                  <div className="quality-item">
                    <div className="quality-icon">✅</div>
                    <strong>정확한 레이블</strong>
                    <p>수동 검증된 positive/negative 쌍</p>
                  </div>
                  <div className="quality-item">
                    <div className="quality-icon">🔄</div>
                    <strong>하드 네거티브</strong>
                    <p>비슷해 보이지만 다른 의미의 negative 샘플</p>
                  </div>
                </div>
              </div>

              {/* 파인튜닝 방법 */}
              <div className="finetuning-section">
                <h4>파인튜닝 방법</h4>
                <div className="finetune-methods">
                  <div className="method-card">
                    <h5>1. Sentence Transformers 사용</h5>
                    <pre className="code-block">{`from sentence_transformers import SentenceTransformer
from sentence_transformers.losses import MultipleNegativesRankingLoss

model = SentenceTransformer('BAAI/bge-m3')
train_loss = MultipleNegativesRankingLoss(model)

model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=3,
    warmup_steps=100,
    output_path='./finetuned-model'
)`}</pre>
                  </div>
                  <div className="method-card">
                    <h5>2. 주요 Loss 함수</h5>
                    <div className="loss-functions">
                      <div className="loss-item">
                        <strong>MultipleNegativesRankingLoss</strong>
                        <p>In-batch negatives 활용, Triplet 데이터에 적합</p>
                      </div>
                      <div className="loss-item">
                        <strong>CosineSimilarityLoss</strong>
                        <p>유사도 점수가 있는 Pair 데이터에 적합</p>
                      </div>
                      <div className="loss-item">
                        <strong>TripletLoss</strong>
                        <p>명시적 positive/negative 쌍이 있을 때</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 파인튜닝 팁 */}
              <div className="finetuning-section">
                <h4>파인튜닝 Best Practices</h4>
                <div className="tips-grid">
                  <div className="tip-item">
                    <span className="tip-number">1</span>
                    <div>
                      <strong>Base 모델 선택</strong>
                      <p>도메인/언어에 맞는 사전학습 모델 선택 (한국어: KURE, BGE-M3)</p>
                    </div>
                  </div>
                  <div className="tip-item">
                    <span className="tip-number">2</span>
                    <div>
                      <strong>학습률 조정</strong>
                      <p>2e-5 ~ 5e-5 범위에서 시작, warmup 단계 포함</p>
                    </div>
                  </div>
                  <div className="tip-item">
                    <span className="tip-number">3</span>
                    <div>
                      <strong>검증 데이터 분리</strong>
                      <p>10~20% 데이터를 검증용으로 분리하여 과적합 방지</p>
                    </div>
                  </div>
                  <div className="tip-item">
                    <span className="tip-number">4</span>
                    <div>
                      <strong>평가 지표 모니터링</strong>
                      <p>MRR, NDCG, Recall@K 등 검색 품질 지표 추적</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Vector DB RAG 관리 가이드 */}
          <VectorDBRAGGuide />

          {/* Embedding Visualization */}
          <EmbeddingVisualizationSection />
        </section>
      )}

      {activeTab === 'comfyui' && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">ComfyUI</h2>
            <span className="section-subtitle">이미지/동영상 생성 워크플로우</span>
          </div>

          <div className="grid grid-3">
            {/* ComfyUI 상태 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><MonitorDot size={18} /> ComfyUI 상태</h3>
                <span className={`status-badge ${pipelineStatus?.components?.comfyui?.status === 'running' ? 'success' : 'warning'}`}>
                  {pipelineStatus?.components?.comfyui?.status === 'running' ? '실행중' : '중지됨'}
                </span>
              </div>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">포트</span>
                  <span className="stat-value">8188 (WebUI)</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">네임스페이스</span>
                  <span className="stat-value">ai-workloads</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">GPU 사용</span>
                  <span className="stat-value">CUDA 필요</span>
                </div>
              </div>
            </div>

            {/* 용도 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><Target size={18} /> 주요 용도</h3>
              </div>
              <div className="use-case-list">
                <div className="use-case-item">
                  <span className="use-case-icon">🎨</span>
                  <div>
                    <strong>이미지 생성</strong>
                    <p>Stable Diffusion 기반 이미지 생성</p>
                  </div>
                </div>
                <div className="use-case-item">
                  <span className="use-case-icon">🎬</span>
                  <div>
                    <strong>동영상 생성</strong>
                    <p>AnimateDiff, SVD 등 동영상 워크플로우</p>
                  </div>
                </div>
                <div className="use-case-item">
                  <span className="use-case-icon">✏️</span>
                  <div>
                    <strong>이미지 편집</strong>
                    <p>Inpainting, Outpainting, ControlNet</p>
                  </div>
                </div>
                <div className="use-case-item">
                  <span className="use-case-icon">⚡</span>
                  <div>
                    <strong>배치 처리</strong>
                    <p>API를 통한 대량 이미지 생성</p>
                  </div>
                </div>
              </div>
            </div>

            {/* API 연동 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><ExternalLink size={18} /> API 연동</h3>
              </div>
              <div className="api-info">
                <div className="api-endpoint">
                  <label>Web UI / API (외부)</label>
                  <code>http://comfyui.14.32.100.220.nip.io</code>
                </div>
                <div className="api-endpoint">
                  <label>WebSocket (외부)</label>
                  <code>ws://comfyui.14.32.100.220.nip.io/ws</code>
                </div>
                <div className="api-endpoint">
                  <label>내부 클러스터</label>
                  <code>http://comfyui.ai-workloads:8188</code>
                </div>
              </div>
              <div className="code-example">
                <h4>Python 예제 (외부 접근)</h4>
                <pre>{`import requests
import json

# 외부에서 워크플로우 실행
workflow = {...}  # ComfyUI 워크플로우 JSON
response = requests.post(
    "http://comfyui.14.32.100.220.nip.io/prompt",
    json={"prompt": workflow}
)
prompt_id = response.json()["prompt_id"]

# 결과 확인
history = requests.get(
    f"http://comfyui.14.32.100.220.nip.io/history/{prompt_id}"
).json()`}</pre>
              </div>
            </div>
          </div>

          {/* 워크플로우 예시 */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Package size={18} /> 지원 워크플로우</h3>
            </div>
            <div className="workflow-grid">
              <div className="workflow-item">
                <span className="workflow-icon">📷</span>
                <strong>txt2img</strong>
                <p>텍스트에서 이미지 생성</p>
              </div>
              <div className="workflow-item">
                <span className="workflow-icon">🔄</span>
                <strong>img2img</strong>
                <p>이미지 변환/스타일 전이</p>
              </div>
              <div className="workflow-item">
                <span className="workflow-icon">🎭</span>
                <strong>ControlNet</strong>
                <p>포즈/엣지/뎁스 기반 제어</p>
              </div>
              <div className="workflow-item">
                <span className="workflow-icon">🎥</span>
                <strong>AnimateDiff</strong>
                <p>이미지 애니메이션</p>
              </div>
              <div className="workflow-item">
                <span className="workflow-icon">⬆️</span>
                <strong>Upscale</strong>
                <p>이미지 해상도 향상</p>
              </div>
              <div className="workflow-item">
                <span className="workflow-icon">🖌️</span>
                <strong>Inpainting</strong>
                <p>이미지 부분 수정</p>
              </div>
            </div>
          </div>

          {/* 파이프라인 아키텍처 */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><GitBranch size={18} /> 파이프라인 아키텍처</h3>
            </div>
            <div className="comfyui-pipeline-architecture">
              <svg viewBox="0 0 900 200" className="pipeline-arch-svg">
                {/* Frontend */}
                <g className="arch-node frontend">
                  <rect x="20" y="70" width="140" height="60" rx="8" fill="var(--accent-primary)" fillOpacity="0.15" stroke="var(--accent-primary)" strokeWidth="2"/>
                  <text x="90" y="95" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="600">Frontend</text>
                  <text x="90" y="115" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">(React)</text>
                </g>

                {/* Arrow 1 */}
                <g className="arch-arrow">
                  <path d="M160 100 L220 100" stroke="var(--accent-primary)" strokeWidth="2" markerEnd="url(#arrowhead)"/>
                  <text x="190" y="90" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">REST/WS</text>
                </g>

                {/* Backend */}
                <g className="arch-node backend">
                  <rect x="220" y="70" width="140" height="60" rx="8" fill="var(--accent-secondary)" fillOpacity="0.15" stroke="var(--accent-secondary)" strokeWidth="2"/>
                  <text x="290" y="95" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="600">Backend API</text>
                  <text x="290" y="115" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">(FastAPI)</text>
                </g>

                {/* Arrow 2 */}
                <g className="arch-arrow">
                  <path d="M360 100 L420 100" stroke="var(--accent-secondary)" strokeWidth="2" markerEnd="url(#arrowhead)"/>
                  <text x="390" y="90" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">Proxy</text>
                </g>

                {/* ComfyUI */}
                <g className="arch-node comfyui">
                  <rect x="420" y="70" width="140" height="60" rx="8" fill="#ff6b6b" fillOpacity="0.15" stroke="#ff6b6b" strokeWidth="2"/>
                  <text x="490" y="95" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="600">ComfyUI</text>
                  <text x="490" y="115" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">(K3s Pod + GPU)</text>
                </g>

                {/* Arrow 3 */}
                <g className="arch-arrow">
                  <path d="M560 100 L620 100" stroke="#ff6b6b" strokeWidth="2" markerEnd="url(#arrowhead)"/>
                  <text x="590" y="90" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">Save</text>
                </g>

                {/* RustFS */}
                <g className="arch-node rustfs">
                  <rect x="620" y="70" width="140" height="60" rx="8" fill="#ffd43b" fillOpacity="0.15" stroke="#ffd43b" strokeWidth="2"/>
                  <text x="690" y="95" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="600">RustFS</text>
                  <text x="690" y="115" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">(S3 Storage)</text>
                </g>

                {/* Arrow 4 - Return path */}
                <g className="arch-arrow return">
                  <path d="M690 130 L690 160 L90 160 L90 130" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="4,4" fill="none"/>
                  <text x="390" y="175" textAnchor="middle" fill="var(--text-muted)" fontSize="10">Result (Image/Video URL)</text>
                </g>

                {/* Arrowhead marker */}
                <defs>
                  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="var(--text-secondary)"/>
                  </marker>
                </defs>
              </svg>

              <div className="arch-flow-description">
                <div className="flow-step">
                  <span className="step-num">1</span>
                  <div>
                    <strong>요청 생성</strong>
                    <p>Frontend에서 프롬프트와 설정을 JSON 워크플로우로 변환</p>
                  </div>
                </div>
                <div className="flow-step">
                  <span className="step-num">2</span>
                  <div>
                    <strong>API 프록시</strong>
                    <p>Backend가 ComfyUI로 요청 전달 및 WebSocket 실시간 연결 관리</p>
                  </div>
                </div>
                <div className="flow-step">
                  <span className="step-num">3</span>
                  <div>
                    <strong>GPU 처리</strong>
                    <p>ComfyUI가 노드 기반 워크플로우 실행 (Stable Diffusion)</p>
                  </div>
                </div>
                <div className="flow-step">
                  <span className="step-num">4</span>
                  <div>
                    <strong>결과 저장</strong>
                    <p>생성된 이미지/영상을 RustFS(S3)에 영구 저장</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 이미지 생성 파이프라인 */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Image size={18} /> 이미지 생성 파이프라인 (txt2img)</h3>
            </div>
            <div className="comfyui-node-pipeline">
              <svg viewBox="0 0 950 300" className="node-pipeline-svg">
                {/* Checkpoint Loader */}
                <g className="pipeline-node checkpoint">
                  <rect x="20" y="100" width="120" height="80" rx="6" fill="#4dabf7" fillOpacity="0.2" stroke="#4dabf7" strokeWidth="2"/>
                  <text x="80" y="130" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Checkpoint</text>
                  <text x="80" y="145" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Loader</text>
                  <text x="80" y="165" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">sd_xl_base_1.0</text>
                  {/* Output ports */}
                  <circle cx="140" cy="115" r="5" fill="#ff8787" stroke="#fff" strokeWidth="1.5"/>
                  <circle cx="140" cy="135" r="5" fill="#74c0fc" stroke="#fff" strokeWidth="1.5"/>
                  <circle cx="140" cy="155" r="5" fill="#b197fc" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* CLIP Text Encode (Positive) */}
                <g className="pipeline-node clip-positive">
                  <rect x="180" y="30" width="110" height="70" rx="6" fill="#69db7c" fillOpacity="0.2" stroke="#69db7c" strokeWidth="2"/>
                  <text x="235" y="55" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">CLIP Encode</text>
                  <text x="235" y="70" textAnchor="middle" fill="#69db7c" fontSize="10">(Positive)</text>
                  <text x="235" y="88" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">"beautiful landscape"</text>
                  <circle cx="180" cy="65" r="4" fill="#74c0fc" stroke="#fff" strokeWidth="1"/>
                  <circle cx="290" cy="65" r="5" fill="#69db7c" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* CLIP Text Encode (Negative) */}
                <g className="pipeline-node clip-negative">
                  <rect x="180" y="180" width="110" height="70" rx="6" fill="#ff8787" fillOpacity="0.2" stroke="#ff8787" strokeWidth="2"/>
                  <text x="235" y="205" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">CLIP Encode</text>
                  <text x="235" y="220" textAnchor="middle" fill="#ff8787" fontSize="10">(Negative)</text>
                  <text x="235" y="238" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">"bad quality, blurry"</text>
                  <circle cx="180" cy="215" r="4" fill="#74c0fc" stroke="#fff" strokeWidth="1"/>
                  <circle cx="290" cy="215" r="5" fill="#ff8787" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* Empty Latent Image */}
                <g className="pipeline-node latent">
                  <rect x="180" y="105" width="110" height="70" rx="6" fill="#b197fc" fillOpacity="0.2" stroke="#b197fc" strokeWidth="2"/>
                  <text x="235" y="130" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Empty Latent</text>
                  <text x="235" y="145" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Image</text>
                  <text x="235" y="163" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">1024 x 1024</text>
                  <circle cx="290" cy="140" r="5" fill="#b197fc" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* KSampler */}
                <g className="pipeline-node ksampler">
                  <rect x="340" y="80" width="130" height="120" rx="6" fill="#ffd43b" fillOpacity="0.2" stroke="#ffd43b" strokeWidth="2"/>
                  <text x="405" y="110" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="700">KSampler</text>
                  <text x="405" y="130" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">steps: 20</text>
                  <text x="405" y="145" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">cfg: 7</text>
                  <text x="405" y="160" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">sampler: euler</text>
                  <text x="405" y="175" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">seed: random</text>
                  {/* Input ports */}
                  <circle cx="340" cy="100" r="4" fill="#ff8787" stroke="#fff" strokeWidth="1"/>
                  <circle cx="340" cy="120" r="4" fill="#69db7c" stroke="#fff" strokeWidth="1"/>
                  <circle cx="340" cy="140" r="4" fill="#ff8787" stroke="#fff" strokeWidth="1"/>
                  <circle cx="340" cy="160" r="4" fill="#b197fc" stroke="#fff" strokeWidth="1"/>
                  {/* Output port */}
                  <circle cx="470" cy="140" r="5" fill="#ffd43b" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* VAE Decode */}
                <g className="pipeline-node vae">
                  <rect x="520" y="100" width="110" height="80" rx="6" fill="#f783ac" fillOpacity="0.2" stroke="#f783ac" strokeWidth="2"/>
                  <text x="575" y="130" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">VAE Decode</text>
                  <text x="575" y="150" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">Latent to Image</text>
                  <text x="575" y="168" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">Pixel Space</text>
                  <circle cx="520" cy="130" r="4" fill="#ffd43b" stroke="#fff" strokeWidth="1"/>
                  <circle cx="520" cy="150" r="4" fill="#b197fc" stroke="#fff" strokeWidth="1"/>
                  <circle cx="630" cy="140" r="5" fill="#f783ac" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* Save Image */}
                <g className="pipeline-node save">
                  <rect x="680" y="100" width="110" height="80" rx="6" fill="#51cf66" fillOpacity="0.2" stroke="#51cf66" strokeWidth="2"/>
                  <text x="735" y="130" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Save Image</text>
                  <text x="735" y="150" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">ComfyUI_00001</text>
                  <text x="735" y="168" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">PNG Output</text>
                  <circle cx="680" cy="140" r="4" fill="#f783ac" stroke="#fff" strokeWidth="1"/>
                </g>

                {/* Connections */}
                <g className="pipeline-connections">
                  {/* Checkpoint to CLIP+ */}
                  <path d="M140 135 Q160 135 160 65 Q160 65 180 65" fill="none" stroke="#74c0fc" strokeWidth="2"/>
                  {/* Checkpoint to CLIP- */}
                  <path d="M140 135 Q160 135 160 215 Q160 215 180 215" fill="none" stroke="#74c0fc" strokeWidth="2"/>
                  {/* Checkpoint to KSampler (model) */}
                  <path d="M140 115 Q240 115 240 100 Q240 100 340 100" fill="none" stroke="#ff8787" strokeWidth="2"/>
                  {/* Checkpoint to VAE */}
                  <path d="M140 155 Q160 155 160 250 Q160 250 500 250 Q500 250 500 150 Q500 150 520 150" fill="none" stroke="#b197fc" strokeWidth="1.5" strokeDasharray="4,2"/>
                  {/* CLIP+ to KSampler */}
                  <path d="M290 65 Q315 65 315 120 Q315 120 340 120" fill="none" stroke="#69db7c" strokeWidth="2"/>
                  {/* CLIP- to KSampler */}
                  <path d="M290 215 Q315 215 315 140 Q315 140 340 140" fill="none" stroke="#ff8787" strokeWidth="2"/>
                  {/* Latent to KSampler */}
                  <path d="M290 140 Q315 140 315 160 Q315 160 340 160" fill="none" stroke="#b197fc" strokeWidth="2"/>
                  {/* KSampler to VAE */}
                  <path d="M470 140 Q495 140 495 130 Q495 130 520 130" fill="none" stroke="#ffd43b" strokeWidth="2"/>
                  {/* VAE to Save */}
                  <path d="M630 140 L680 140" fill="none" stroke="#f783ac" strokeWidth="2"/>
                </g>

                {/* Legend */}
                <g className="pipeline-legend" transform="translate(820, 20)">
                  <text x="0" y="0" fill="var(--text-secondary)" fontSize="10" fontWeight="600">Port Types:</text>
                  <circle cx="10" cy="20" r="4" fill="#ff8787"/>
                  <text x="20" y="24" fill="var(--text-secondary)" fontSize="10">MODEL</text>
                  <circle cx="10" cy="40" r="4" fill="#74c0fc"/>
                  <text x="20" y="44" fill="var(--text-secondary)" fontSize="10">CLIP</text>
                  <circle cx="10" cy="60" r="4" fill="#b197fc"/>
                  <text x="20" y="64" fill="var(--text-secondary)" fontSize="10">VAE/LATENT</text>
                  <circle cx="10" cy="80" r="4" fill="#69db7c"/>
                  <text x="20" y="84" fill="var(--text-secondary)" fontSize="10">CONDITIONING</text>
                  <circle cx="10" cy="100" r="4" fill="#f783ac"/>
                  <text x="20" y="104" fill="var(--text-secondary)" fontSize="10">IMAGE</text>
                </g>
              </svg>

              <div className="pipeline-node-explanation">
                <div className="node-exp-item">
                  <span className="node-color" style={{background: '#4dabf7'}}></span>
                  <div>
                    <strong>Checkpoint Loader</strong>
                    <p>Stable Diffusion 모델 파일(.safetensors)을 로드하여 MODEL, CLIP, VAE 3가지 출력 제공</p>
                  </div>
                </div>
                <div className="node-exp-item">
                  <span className="node-color" style={{background: '#69db7c'}}></span>
                  <div>
                    <strong>CLIP Text Encode</strong>
                    <p>텍스트 프롬프트를 CLIP 모델로 인코딩하여 이미지 생성 조건(conditioning) 생성</p>
                  </div>
                </div>
                <div className="node-exp-item">
                  <span className="node-color" style={{background: '#ffd43b'}}></span>
                  <div>
                    <strong>KSampler</strong>
                    <p>Diffusion 프로세스의 핵심. 노이즈 제거를 반복하며 이미지 생성 (steps, cfg, sampler 설정)</p>
                  </div>
                </div>
                <div className="node-exp-item">
                  <span className="node-color" style={{background: '#f783ac'}}></span>
                  <div>
                    <strong>VAE Decode</strong>
                    <p>Latent space의 잠재 표현을 실제 픽셀 이미지로 디코딩</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 동영상 생성 파이프라인 */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Film size={18} /> 동영상 생성 파이프라인 (AnimateDiff)</h3>
            </div>
            <div className="comfyui-node-pipeline video-pipeline">
              <svg viewBox="0 0 1000 320" className="node-pipeline-svg">
                {/* Checkpoint Loader */}
                <g className="pipeline-node checkpoint">
                  <rect x="20" y="100" width="110" height="75" rx="6" fill="#4dabf7" fillOpacity="0.2" stroke="#4dabf7" strokeWidth="2"/>
                  <text x="75" y="125" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Checkpoint</text>
                  <text x="75" y="140" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Loader</text>
                  <text x="75" y="158" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">realisticVision</text>
                  <circle cx="130" cy="115" r="4" fill="#ff8787" stroke="#fff" strokeWidth="1"/>
                  <circle cx="130" cy="135" r="4" fill="#74c0fc" stroke="#fff" strokeWidth="1"/>
                  <circle cx="130" cy="155" r="4" fill="#b197fc" stroke="#fff" strokeWidth="1"/>
                </g>

                {/* AnimateDiff Loader */}
                <g className="pipeline-node animatediff-loader">
                  <rect x="20" y="200" width="110" height="65" rx="6" fill="#f06595" fillOpacity="0.2" stroke="#f06595" strokeWidth="2"/>
                  <text x="75" y="225" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">AnimateDiff</text>
                  <text x="75" y="240" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Loader</text>
                  <text x="75" y="255" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">mm_sd_v15_v2</text>
                  <circle cx="130" cy="232" r="4" fill="#f06595" stroke="#fff" strokeWidth="1"/>
                </g>

                {/* AnimateDiff Apply */}
                <g className="pipeline-node animatediff-apply">
                  <rect x="160" y="100" width="110" height="100" rx="6" fill="#e599f7" fillOpacity="0.2" stroke="#e599f7" strokeWidth="2"/>
                  <text x="215" y="130" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">AnimateDiff</text>
                  <text x="215" y="145" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Apply</text>
                  <text x="215" y="165" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">Motion Module</text>
                  <text x="215" y="180" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">Integration</text>
                  <circle cx="160" cy="125" r="4" fill="#ff8787" stroke="#fff" strokeWidth="1"/>
                  <circle cx="160" cy="175" r="4" fill="#f06595" stroke="#fff" strokeWidth="1"/>
                  <circle cx="270" cy="150" r="5" fill="#e599f7" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* CLIP Positive */}
                <g className="pipeline-node clip-positive">
                  <rect x="160" y="20" width="100" height="55" rx="6" fill="#69db7c" fillOpacity="0.2" stroke="#69db7c" strokeWidth="2"/>
                  <text x="210" y="42" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">CLIP Encode</text>
                  <text x="210" y="55" textAnchor="middle" fill="#69db7c" fontSize="10">(Positive)</text>
                  <text x="210" y="68" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">"a cat walking"</text>
                  <circle cx="160" cy="47" r="3" fill="#74c0fc" stroke="#fff" strokeWidth="1"/>
                  <circle cx="260" cy="47" r="4" fill="#69db7c" stroke="#fff" strokeWidth="1"/>
                </g>

                {/* CLIP Negative */}
                <g className="pipeline-node clip-negative">
                  <rect x="160" y="225" width="100" height="55" rx="6" fill="#ff8787" fillOpacity="0.2" stroke="#ff8787" strokeWidth="2"/>
                  <text x="210" y="247" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">CLIP Encode</text>
                  <text x="210" y="260" textAnchor="middle" fill="#ff8787" fontSize="10">(Negative)</text>
                  <text x="210" y="273" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">"static, blurry"</text>
                  <circle cx="160" cy="252" r="3" fill="#74c0fc" stroke="#fff" strokeWidth="1"/>
                  <circle cx="260" cy="252" r="4" fill="#ff8787" stroke="#fff" strokeWidth="1"/>
                </g>

                {/* Empty Latent (Batch) */}
                <g className="pipeline-node latent-batch">
                  <rect x="300" y="205" width="100" height="70" rx="6" fill="#b197fc" fillOpacity="0.2" stroke="#b197fc" strokeWidth="2"/>
                  <text x="350" y="228" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Empty Latent</text>
                  <text x="350" y="243" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Image</text>
                  <text x="350" y="258" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">512x512</text>
                  <text x="350" y="270" textAnchor="middle" fill="#ffd43b" fontSize="10" fontWeight="600">batch: 16 frames</text>
                  <circle cx="400" cy="240" r="4" fill="#b197fc" stroke="#fff" strokeWidth="1"/>
                </g>

                {/* KSampler */}
                <g className="pipeline-node ksampler">
                  <rect x="430" y="80" width="120" height="120" rx="6" fill="#ffd43b" fillOpacity="0.2" stroke="#ffd43b" strokeWidth="2"/>
                  <text x="490" y="105" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="700">KSampler</text>
                  <text x="490" y="125" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">steps: 20</text>
                  <text x="490" y="140" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">cfg: 7</text>
                  <text x="490" y="155" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">euler_ancestral</text>
                  <text x="490" y="175" textAnchor="middle" fill="#f06595" fontSize="10" fontWeight="600">Motion-aware</text>
                  <text x="490" y="188" textAnchor="middle" fill="#f06595" fontSize="10" fontWeight="600">Denoising</text>
                  <circle cx="430" cy="100" r="3" fill="#e599f7" stroke="#fff" strokeWidth="1"/>
                  <circle cx="430" cy="120" r="3" fill="#69db7c" stroke="#fff" strokeWidth="1"/>
                  <circle cx="430" cy="140" r="3" fill="#ff8787" stroke="#fff" strokeWidth="1"/>
                  <circle cx="430" cy="160" r="3" fill="#b197fc" stroke="#fff" strokeWidth="1"/>
                  <circle cx="550" cy="140" r="5" fill="#ffd43b" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* VAE Decode */}
                <g className="pipeline-node vae">
                  <rect x="580" y="100" width="100" height="80" rx="6" fill="#f783ac" fillOpacity="0.2" stroke="#f783ac" strokeWidth="2"/>
                  <text x="630" y="125" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">VAE Decode</text>
                  <text x="630" y="145" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">16 Latent Frames</text>
                  <text x="630" y="160" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">to 16 Images</text>
                  <circle cx="580" cy="130" r="3" fill="#ffd43b" stroke="#fff" strokeWidth="1"/>
                  <circle cx="580" cy="150" r="3" fill="#b197fc" stroke="#fff" strokeWidth="1"/>
                  <circle cx="680" cy="140" r="5" fill="#f783ac" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* Video Combine */}
                <g className="pipeline-node video-combine">
                  <rect x="710" y="90" width="110" height="100" rx="6" fill="#20c997" fillOpacity="0.2" stroke="#20c997" strokeWidth="2"/>
                  <text x="765" y="115" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">VHS Video</text>
                  <text x="765" y="130" textAnchor="middle" fill="var(--text-primary)" fontSize="10" fontWeight="600">Combine</text>
                  <text x="765" y="150" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">frame_rate: 8 fps</text>
                  <text x="765" y="165" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">format: H.264 MP4</text>
                  <text x="765" y="180" textAnchor="middle" fill="#20c997" fontSize="10" fontWeight="600">AnimateDiff.mp4</text>
                  <circle cx="710" cy="140" r="4" fill="#f783ac" stroke="#fff" strokeWidth="1"/>
                  <circle cx="820" cy="140" r="5" fill="#20c997" stroke="#fff" strokeWidth="1.5"/>
                </g>

                {/* Output indicator */}
                <g className="output-indicator">
                  <rect x="850" y="115" width="90" height="50" rx="25" fill="var(--bg-tertiary)" stroke="var(--border-color)" strokeWidth="1"/>
                  <text x="895" y="138" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">OUTPUT</text>
                  <text x="895" y="153" textAnchor="middle" fill="#20c997" fontSize="10" fontWeight="600">.mp4 Video</text>
                </g>

                {/* Connections */}
                <g className="pipeline-connections">
                  {/* Checkpoint to AnimateDiff Apply */}
                  <path d="M130 115 Q145 115 145 125 Q145 125 160 125" fill="none" stroke="#ff8787" strokeWidth="1.5"/>
                  {/* AnimateDiff Loader to Apply */}
                  <path d="M130 232 Q145 232 145 175 Q145 175 160 175" fill="none" stroke="#f06595" strokeWidth="1.5"/>
                  {/* Checkpoint to CLIP+ */}
                  <path d="M130 135 Q145 135 145 47 Q145 47 160 47" fill="none" stroke="#74c0fc" strokeWidth="1.5"/>
                  {/* Checkpoint to CLIP- */}
                  <path d="M130 135 Q145 135 145 252 Q145 252 160 252" fill="none" stroke="#74c0fc" strokeWidth="1.5"/>
                  {/* Checkpoint to VAE */}
                  <path d="M130 155 Q145 155 145 295 Q145 295 565 295 Q565 295 565 150 Q565 150 580 150" fill="none" stroke="#b197fc" strokeWidth="1.5" strokeDasharray="4,2"/>
                  {/* AnimateDiff Apply to KSampler */}
                  <path d="M270 150 Q350 150 350 100 Q350 100 430 100" fill="none" stroke="#e599f7" strokeWidth="2"/>
                  {/* CLIP+ to KSampler */}
                  <path d="M260 47 Q290 47 290 85 Q290 85 410 85 Q410 85 410 120 Q410 120 430 120" fill="none" stroke="#69db7c" strokeWidth="1.5"/>
                  {/* CLIP- to KSampler */}
                  <path d="M260 252 Q290 252 290 215 Q290 215 410 215 Q410 215 410 140 Q410 140 430 140" fill="none" stroke="#ff8787" strokeWidth="1.5"/>
                  {/* Latent to KSampler */}
                  <path d="M400 240 Q415 240 415 160 Q415 160 430 160" fill="none" stroke="#b197fc" strokeWidth="1.5"/>
                  {/* KSampler to VAE */}
                  <path d="M550 140 Q565 140 565 130 Q565 130 580 130" fill="none" stroke="#ffd43b" strokeWidth="2"/>
                  {/* VAE to Video Combine */}
                  <path d="M680 140 L710 140" fill="none" stroke="#f783ac" strokeWidth="2"/>
                  {/* Video Combine to Output */}
                  <path d="M820 140 L850 140" fill="none" stroke="#20c997" strokeWidth="2"/>
                </g>

                {/* Motion module highlight */}
                <g className="motion-highlight">
                  <rect x="15" y="195" width="270" height="80" rx="8" fill="none" stroke="#f06595" strokeWidth="1" strokeDasharray="4,4" opacity="0.5"/>
                  <text x="150" y="290" textAnchor="middle" fill="#f06595" fontSize="10" fontWeight="600">AnimateDiff Motion Module</text>
                </g>
              </svg>

              <div className="pipeline-video-explanation">
                <div className="video-exp-header">
                  <span className="video-badge">AnimateDiff</span>
                  <span>이미지 생성 파이프라인에 Motion Module을 추가하여 동영상 생성</span>
                </div>
                <div className="video-exp-grid">
                  <div className="video-exp-item">
                    <span className="node-color" style={{background: '#f06595'}}></span>
                    <div>
                      <strong>Motion Module</strong>
                      <p>Temporal attention layers를 SD 모델에 주입하여 프레임 간 일관성 있는 움직임 생성</p>
                    </div>
                  </div>
                  <div className="video-exp-item">
                    <span className="node-color" style={{background: '#b197fc'}}></span>
                    <div>
                      <strong>Batch Latent (16 frames)</strong>
                      <p>batch_size=16으로 설정하여 16개 프레임을 동시에 생성 (약 2초 @8fps)</p>
                    </div>
                  </div>
                  <div className="video-exp-item">
                    <span className="node-color" style={{background: '#ffd43b'}}></span>
                    <div>
                      <strong>Motion-aware Sampling</strong>
                      <p>euler_ancestral sampler가 프레임 간 자연스러운 전환을 위한 노이즈 처리</p>
                    </div>
                  </div>
                  <div className="video-exp-item">
                    <span className="node-color" style={{background: '#20c997'}}></span>
                    <div>
                      <strong>VHS Video Combine</strong>
                      <p>16개 이미지 프레임을 H.264 MP4 동영상으로 인코딩 (8fps = 2초)</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 이미지/동영상 생성 데모 */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Zap size={18} /> 생성 데모</h3>
              <div className="demo-header-right">
                <span className={`service-status-badge ${workloads.comfyui?.status === 'running' ? 'running' : 'stopped'}`}>
                  {workloads.comfyui?.status === 'running' ? '서비스 실행중' : '서비스 중지됨'}
                </span>
                <div className="demo-mode-toggle">
                  <button
                    className={`demo-mode-btn ${comfyuiDemoMode === 'image' ? 'active' : ''}`}
                    onClick={() => setComfyuiDemoMode('image')}
                  >
                    <Image size={14} /> 이미지
                  </button>
                  <button
                    className={`demo-mode-btn ${comfyuiDemoMode === 'video' ? 'active' : ''}`}
                    onClick={() => setComfyuiDemoMode('video')}
                  >
                    <Film size={14} /> 동영상
                  </button>
                </div>
              </div>
            </div>
            {workloads.comfyui?.status !== 'running' && (
              <div className="demo-service-warning">
                <AlertTriangle size={20} />
                <div>
                  <strong>ComfyUI 서비스가 실행중이 아닙니다</strong>
                  <p>개요 탭에서 ComfyUI 서비스를 시작해주세요.</p>
                </div>
              </div>
            )}
            {workloads.comfyui?.status === 'running' && (
            <div className="comfyui-demo-section">
              <div className="demo-input-area">
                <div className="demo-form-group">
                  <label>Positive Prompt</label>
                  <textarea
                    placeholder={comfyuiDemoMode === 'image'
                      ? "a beautiful mountain landscape at sunset, masterpiece, high quality"
                      : "a cat walking on grass, smooth motion, high quality animation"}
                    value={comfyuiPrompt}
                    onChange={(e) => setComfyuiPrompt(e.target.value)}
                    rows={3}
                  />
                </div>
                <div className="demo-form-group">
                  <label>Negative Prompt</label>
                  <textarea
                    placeholder="bad quality, blurry, distorted"
                    value={comfyuiNegativePrompt}
                    onChange={(e) => setComfyuiNegativePrompt(e.target.value)}
                    rows={2}
                  />
                </div>
                <div className="demo-settings-row">
                  {comfyuiDemoMode === 'image' ? (
                    <>
                      <div className="demo-setting">
                        <label>Resolution</label>
                        <select value={comfyuiSettings.width} onChange={(e) => setComfyuiSettings({...comfyuiSettings, width: e.target.value, height: e.target.value})}>
                          <option value="512">512x512</option>
                          <option value="768">768x768</option>
                          <option value="1024">1024x1024</option>
                        </select>
                      </div>
                      <div className="demo-setting">
                        <label>Steps</label>
                        <select value={comfyuiSettings.steps} onChange={(e) => setComfyuiSettings({...comfyuiSettings, steps: e.target.value})}>
                          <option value="15">15 (Fast)</option>
                          <option value="20">20 (Balanced)</option>
                          <option value="30">30 (Quality)</option>
                        </select>
                      </div>
                      <div className="demo-setting">
                        <label>CFG Scale</label>
                        <select value={comfyuiSettings.cfg} onChange={(e) => setComfyuiSettings({...comfyuiSettings, cfg: e.target.value})}>
                          <option value="5">5 (Creative)</option>
                          <option value="7">7 (Balanced)</option>
                          <option value="10">10 (Strict)</option>
                        </select>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="demo-setting">
                        <label>Frames</label>
                        <select value={comfyuiSettings.frames} onChange={(e) => setComfyuiSettings({...comfyuiSettings, frames: e.target.value})}>
                          <option value="8">8 (~1s)</option>
                          <option value="16">16 (~2s)</option>
                          <option value="24">24 (~3s)</option>
                        </select>
                      </div>
                      <div className="demo-setting">
                        <label>FPS</label>
                        <select value={comfyuiSettings.fps} onChange={(e) => setComfyuiSettings({...comfyuiSettings, fps: e.target.value})}>
                          <option value="8">8 fps</option>
                          <option value="12">12 fps</option>
                          <option value="16">16 fps</option>
                        </select>
                      </div>
                      <div className="demo-setting">
                        <label>Resolution</label>
                        <select value={comfyuiSettings.videoWidth} onChange={(e) => setComfyuiSettings({...comfyuiSettings, videoWidth: e.target.value})}>
                          <option value="512">512x512</option>
                          <option value="576">576x320 (Wide)</option>
                        </select>
                      </div>
                    </>
                  )}
                </div>
                <button
                  className="demo-generate-btn"
                  onClick={handleComfyuiGenerate}
                  disabled={comfyuiGenerating || !comfyuiPrompt.trim()}
                >
                  {comfyuiGenerating ? (
                    <>
                      <RefreshCw size={16} className="spinning" />
                      생성 중... {comfyuiProgress}%
                    </>
                  ) : (
                    <>
                      <Zap size={16} />
                      {comfyuiDemoMode === 'image' ? '이미지 생성' : '동영상 생성'}
                    </>
                  )}
                </button>
                {comfyuiGenerating && (
                  <div className="demo-progress-bar">
                    <div className="demo-progress-fill" style={{width: `${comfyuiProgress}%`}}></div>
                  </div>
                )}
              </div>

              <div className="demo-output-area">
                <div className="demo-output-header">
                  <span>Output Preview</span>
                  {comfyuiResult && (
                    <button className="demo-download-btn">
                      <Download size={14} /> Download
                    </button>
                  )}
                </div>
                <div className="demo-output-preview">
                  {comfyuiResult ? (
                    comfyuiDemoMode === 'image' ? (
                      <img src={comfyuiResult} alt="Generated" />
                    ) : (
                      <video controls autoPlay loop>
                        <source src={comfyuiResult} type="video/mp4" />
                      </video>
                    )
                  ) : (
                    <div className="demo-placeholder">
                      {comfyuiDemoMode === 'image' ? (
                        <>
                          <Image size={48} />
                          <span>생성된 이미지가 여기에 표시됩니다</span>
                        </>
                      ) : (
                        <>
                          <Film size={48} />
                          <span>생성된 동영상이 여기에 표시됩니다</span>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Queue Status */}
              <div className="comfyui-queue-status">
              <div className="queue-header">
                <h4><List size={16} /> Queue Status</h4>
                <button onClick={fetchComfyuiQueue} className="refresh-queue-btn">
                  <RefreshCw size={14} />
                </button>
              </div>
              <div className="queue-stats">
                <div className="queue-stat">
                  <span className="queue-stat-label">Running</span>
                  <span className="queue-stat-value running">{comfyuiQueue.running}</span>
                </div>
                <div className="queue-stat">
                  <span className="queue-stat-label">Pending</span>
                  <span className="queue-stat-value pending">{comfyuiQueue.pending}</span>
                </div>
                <div className="queue-stat">
                  <span className="queue-stat-label">Completed</span>
                  <span className="queue-stat-value completed">{comfyuiQueue.completed}</span>
                </div>
              </div>
              </div>
            </div>
            )}
          </div>
        </section>
      )}

      {activeTab === 'neo4j' && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">Ontology (Neo4j)</h2>
            <span className="section-subtitle">그래프 데이터베이스 - 지식 그래프 및 관계 저장</span>
          </div>

          <div className="grid grid-3">
            {/* Neo4j 상태 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><Database size={18} /> Neo4j 상태</h3>
                <span className={`status-badge ${pipelineStatus?.components?.neo4j?.status === 'running' ? 'success' : 'warning'}`}>
                  {pipelineStatus?.components?.neo4j?.status === 'running' ? '실행중' : '중지됨'}
                </span>
              </div>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">Bolt 포트</span>
                  <span className="stat-value">7687</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">HTTP 포트</span>
                  <span className="stat-value">7474</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">네임스페이스</span>
                  <span className="stat-value">ai-workloads</span>
                </div>
              </div>
            </div>

            {/* 용도 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><Target size={18} /> 주요 용도</h3>
              </div>
              <div className="use-case-list">
                <div className="use-case-item">
                  <span className="use-case-icon">🕸️</span>
                  <div>
                    <strong>지식 그래프 (Knowledge Graph)</strong>
                    <p>엔티티 간 관계를 그래프로 저장</p>
                  </div>
                </div>
                <div className="use-case-item">
                  <span className="use-case-icon">🔗</span>
                  <div>
                    <strong>Entity-Relationship</strong>
                    <p>문서/개체 간 관계 추출 및 저장</p>
                  </div>
                </div>
                <div className="use-case-item">
                  <span className="use-case-icon">🧠</span>
                  <div>
                    <strong>Ontology Reasoning</strong>
                    <p>온톨로지 기반 추론 및 쿼리</p>
                  </div>
                </div>
                <div className="use-case-item">
                  <span className="use-case-icon">📚</span>
                  <div>
                    <strong>RAG 컨텍스트 보강</strong>
                    <p>벡터 검색 + 그래프 관계 결합</p>
                  </div>
                </div>
              </div>
            </div>

            {/* API 연동 카드 */}
            <div className="card">
              <div className="card-header">
                <h3><ExternalLink size={18} /> API 연동</h3>
              </div>
              <div className="api-info">
                <div className="api-endpoint">
                  <label>Browser UI (외부)</label>
                  <code>http://neo4j.14.32.100.220.nip.io</code>
                </div>
                <div className="api-endpoint">
                  <label>Bolt (외부)</label>
                  <code>bolt://neo4j.14.32.100.220.nip.io:7687</code>
                </div>
                <div className="api-endpoint">
                  <label>내부 클러스터</label>
                  <code>neo4j.ai-workloads:7687 / :7474</code>
                </div>
              </div>
              <div className="code-example">
                <h4>Python 예제 (외부 접근)</h4>
                <pre>{`from neo4j import GraphDatabase

# 외부에서 접근 시
driver = GraphDatabase.driver(
    "bolt://neo4j.14.32.100.220.nip.io:7687",
    auth=("neo4j", "password")
)

with driver.session() as session:
    # 노드 생성
    session.run("""
        CREATE (d:Document {name: $name})
        CREATE (e:Entity {name: $entity})
        CREATE (d)-[:MENTIONS]->(e)
    """, name="doc1", entity="AI")

    # 관계 쿼리
    result = session.run("""
        MATCH (d:Document)-[:MENTIONS]->(e:Entity)
        RETURN d.name, e.name
    """)`}</pre>
              </div>
            </div>
          </div>

          {/* Cypher 쿼리 예시 */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Settings size={18} /> Cypher 쿼리 예시</h3>
            </div>
            <div className="cypher-examples">
              <div className="cypher-item">
                <h4>지식 그래프 구축</h4>
                <pre>{`// 문서와 엔티티 관계 생성
CREATE (d:Document {id: "doc001", title: "AI 연구"})
CREATE (e1:Entity {name: "딥러닝", type: "Technology"})
CREATE (e2:Entity {name: "신경망", type: "Concept"})
CREATE (d)-[:CONTAINS]->(e1)
CREATE (d)-[:CONTAINS]->(e2)
CREATE (e1)-[:RELATED_TO]->(e2)`}</pre>
              </div>
              <div className="cypher-item">
                <h4>관계 탐색</h4>
                <pre>{`// 2단계 관계 탐색
MATCH path = (start:Entity {name: "딥러닝"})-[*1..2]-(end)
RETURN path

// 최단 경로 찾기
MATCH path = shortestPath(
  (a:Entity {name: "AI"})-[*]-(b:Entity {name: "자연어처리"})
)
RETURN path`}</pre>
              </div>
            </div>
          </div>

          {/* Ontology Live Demo - 라이브 데모 */}
          <OntologyLiveDemo />

          {/* Knowledge Graph 시각화 */}
          <KnowledgeGraphSection />
        </section>
      )}

      {activeTab === 'agent' && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">Advanced LLM Application Architecture</h2>
            <span className="section-subtitle">에이전트 기반 LLM 애플리케이션의 동작 원리와 구현</span>
          </div>

          {/* 기본 vs 고급 아키텍처 비교 */}
          <div className="card architecture-comparison-card">
            <div className="card-header">
              <h3><Layers size={18} /> LLM Application Architecture 비교</h3>
            </div>
            <div className="architecture-comparison">
              {/* 기본 아키텍처 */}
              <div className="arch-column basic">
                <div className="arch-title">
                  <span className="arch-badge basic">Basic</span>
                  <h4>기본 LLM 호출</h4>
                </div>
                <div className="arch-flow-vertical">
                  <div className="arch-node">👤 User Input</div>
                  <div className="arch-arrow-v">↓</div>
                  <div className="arch-node highlight-cyan">Safety Filter</div>
                  <div className="arch-arrow-v">↓</div>
                  <div className="arch-node">Prompt Template</div>
                  <div className="arch-arrow-v">↓</div>
                  <div className="arch-node highlight-green">LLM</div>
                  <div className="arch-arrow-v">↓</div>
                  <div className="arch-node">Output Formatter</div>
                  <div className="arch-arrow-v">↓</div>
                  <div className="arch-node">📤 Response</div>
                </div>
                <div className="arch-desc">단일 LLM 호출, 단순 입출력</div>
              </div>

              <div className="arch-divider">
                <span>→</span>
                <span className="divider-label">확장</span>
              </div>

              {/* 고급 아키텍처 */}
              <div className="arch-column advanced">
                <div className="arch-title">
                  <span className="arch-badge advanced">Advanced</span>
                  <h4>Agent 기반 아키텍처</h4>
                </div>
                <div className="arch-flow-complex">
                  <div className="arch-row">
                    <div className="arch-node">👤 User</div>
                    <div className="arch-arrow-h">→</div>
                    <div className="arch-node highlight-cyan">Safety Filter</div>
                    <div className="arch-arrow-h">→</div>
                    <div className="arch-node">Prompt Selector</div>
                  </div>
                  <div className="arch-row center">
                    <div className="arch-node">Memory</div>
                    <div className="arch-arrow-h">↔</div>
                    <div className="arch-node highlight-purple orchestration">
                      <span>Orchestration</span>
                      <small>(Pipeline/Graph)</small>
                    </div>
                    <div className="arch-arrow-h">↔</div>
                    <div className="arch-node">Cache</div>
                  </div>
                  <div className="arch-row">
                    <div className="arch-node-group">
                      <div className="arch-node highlight-green small">Agent</div>
                      <div className="arch-node highlight-green small">RAG</div>
                      <div className="arch-node highlight-green small">LLM</div>
                    </div>
                    <div className="arch-arrow-h">→</div>
                    <div className="arch-node">Tools</div>
                  </div>
                </div>
                <div className="arch-desc">멀티 스텝, 병렬 처리, 외부 도구 연동</div>
              </div>
            </div>
          </div>

          {/* 에이전트란? */}
          <div className="card agent-concept-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Zap size={18} /> Agent란 무엇인가?</h3>
            </div>
            <div className="agent-concept-content">
              <div className="concept-visual">
                <div className="concept-brain">
                  <div className="brain-icon">🧠</div>
                  <div className="brain-label">LLM (두뇌)</div>
                  <div className="brain-desc">학습된 지식만으로 답변</div>
                </div>
                <div className="concept-plus">+</div>
                <div className="concept-tools">
                  <div className="tool-item">
                    <span className="tool-icon">🔍</span>
                    <span>Web Search</span>
                  </div>
                  <div className="tool-item">
                    <span className="tool-icon">📄</span>
                    <span>Doc Search</span>
                  </div>
                  <div className="tool-item">
                    <span className="tool-icon">📧</span>
                    <span>Email</span>
                  </div>
                  <div className="tool-item">
                    <span className="tool-icon">💬</span>
                    <span>Slack</span>
                  </div>
                </div>
                <div className="concept-equals">=</div>
                <div className="concept-agent">
                  <div className="agent-icon">🤖</div>
                  <div className="agent-label">Agent</div>
                  <div className="agent-desc">외부 도구로 실제 작업 수행</div>
                </div>
              </div>
              <div className="concept-explanation">
                <p><strong>LLM</strong>은 학습 당시 배운 지식만으로 답변합니다 (두뇌만 있는 상태).</p>
                <p><strong>Agent</strong>는 LLM에 <em>손발</em>을 달아준 것입니다. 필요시 외부 도구(Tool)를 호출하여 실시간 데이터를 검색하거나 실제 액션(이메일 발송, 슬랙 메시지 등)을 수행할 수 있습니다.</p>
              </div>
            </div>
          </div>

          {/* ReAct 패턴 */}
          <div className="card react-pattern-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Activity size={18} /> ReAct 패턴 (Reason + Action)</h3>
              <span className="section-subtitle">에이전트의 사고 과정</span>
            </div>
            <div className="react-pattern-content">
              <div className="react-loop-diagram">
                <div className="react-loop">
                  <div className="react-step thought">
                    <div className="step-icon">💭</div>
                    <div className="step-name">Thought</div>
                    <div className="step-desc">생각: 무엇을 해야 할까?</div>
                  </div>
                  <div className="react-arrow">→</div>
                  <div className="react-step action">
                    <div className="step-icon">⚡</div>
                    <div className="step-name">Action</div>
                    <div className="step-desc">실행: Tool 호출</div>
                  </div>
                  <div className="react-arrow">→</div>
                  <div className="react-step observation">
                    <div className="step-icon">👁️</div>
                    <div className="step-name">Observation</div>
                    <div className="step-desc">관찰: 결과 확인</div>
                  </div>
                  <div className="react-arrow loop-back">↩</div>
                </div>
                <div className="react-final">
                  <div className="react-step evaluation">
                    <div className="step-icon">✅</div>
                    <div className="step-name">Evaluation</div>
                    <div className="step-desc">평가: 답변 가능한가?</div>
                  </div>
                  <div className="react-arrow">→</div>
                  <div className="react-step final-answer">
                    <div className="step-icon">📝</div>
                    <div className="step-name">Final Answer</div>
                    <div className="step-desc">최종 답변 생성</div>
                  </div>
                </div>
              </div>
              <div className="react-note">
                <Info size={14} />
                <span>Agent는 필요한 정보를 모두 얻을 때까지 Thought → Action → Observation 루프를 반복합니다.</span>
              </div>
            </div>
          </div>

          {/* 실행 데모 */}
          <div className="card agent-demo-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><PlayCircle size={18} /> Agent 실행 데모</h3>
              <span className="section-subtitle">실제 ReAct 루프 트레이스</span>
            </div>
            <div className="agent-demo-content">
              <div className="demo-question">
                <div className="demo-label">질문</div>
                <div className="demo-text">"2023년 PJ 챔피언의 고향을 알려줘"</div>
              </div>

              <div className="demo-trace">
                <div className="trace-step">
                  <div className="trace-header">
                    <span className="trace-badge thought">Thought #1</span>
                    <span className="trace-time">0ms</span>
                  </div>
                  <div className="trace-content">
                    챔피언 이름을 알기 위해 구글 서치를 해야겠다.
                  </div>
                </div>

                <div className="trace-step">
                  <div className="trace-header">
                    <span className="trace-badge action">Action #1</span>
                    <span className="trace-time">50ms</span>
                  </div>
                  <div className="trace-content">
                    <code>google_search("2023 PJ champion")</code>
                  </div>
                </div>

                <div className="trace-step">
                  <div className="trace-header">
                    <span className="trace-badge observation">Observation #1</span>
                    <span className="trace-time">1,200ms</span>
                  </div>
                  <div className="trace-content">
                    검색 결과: "2023년 PJ 챔피언은 <strong>Clark</strong>입니다."
                  </div>
                </div>

                <div className="trace-step">
                  <div className="trace-header">
                    <span className="trace-badge evaluation">Evaluation</span>
                    <span className="trace-time">1,250ms</span>
                  </div>
                  <div className="trace-content evaluation-result">
                    <span className="eval-icon">❌</span>
                    챔피언 이름은 알았지만, 고향은 아직 모른다. 추가 검색 필요.
                  </div>
                </div>

                <div className="trace-step">
                  <div className="trace-header">
                    <span className="trace-badge thought">Thought #2</span>
                    <span className="trace-time">1,300ms</span>
                  </div>
                  <div className="trace-content">
                    Clark의 고향을 알기 위해 LinkedIn 검색을 해야겠다.
                  </div>
                </div>

                <div className="trace-step">
                  <div className="trace-header">
                    <span className="trace-badge action">Action #2</span>
                    <span className="trace-time">1,350ms</span>
                  </div>
                  <div className="trace-content">
                    <code>linkedin_search("Clark hometown")</code>
                  </div>
                </div>

                <div className="trace-step">
                  <div className="trace-header">
                    <span className="trace-badge observation">Observation #2</span>
                    <span className="trace-time">2,500ms</span>
                  </div>
                  <div className="trace-content">
                    검색 결과: "Clark의 고향은 <strong>Arizona, USA</strong>입니다."
                  </div>
                </div>

                <div className="trace-step">
                  <div className="trace-header">
                    <span className="trace-badge evaluation">Evaluation</span>
                    <span className="trace-time">2,550ms</span>
                  </div>
                  <div className="trace-content evaluation-result success">
                    <span className="eval-icon">✅</span>
                    챔피언 이름과 고향 모두 확인. 답변 가능!
                  </div>
                </div>

                <div className="trace-step final">
                  <div className="trace-header">
                    <span className="trace-badge final">Final Answer</span>
                    <span className="trace-time">2,600ms</span>
                  </div>
                  <div className="trace-content">
                    2023년 PJ 챔피언은 <strong>Clark</strong>이며, 그의 고향은 <strong>Arizona, USA</strong>입니다.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tool 정의 예시 */}
          <div className="grid grid-2" style={{ marginTop: '20px' }}>
            <div className="card">
              <div className="card-header">
                <h3><Settings size={18} /> Tool 정의</h3>
                <span className="section-subtitle">Agent가 사용할 도구 등록</span>
              </div>
              <div className="code-example">
                <pre>{`from langchain.tools import Tool

# Tool 정의 - description이 매우 중요!
google_search = Tool(
    name="google_search",
    description="""인터넷에서 최신 정보를 검색합니다.
    사용 시점: 실시간 정보, 뉴스, 인물 정보가 필요할 때
    입력: 검색할 키워드""",
    func=search_google
)

linkedin_search = Tool(
    name="linkedin_search",
    description="""LinkedIn에서 인물 정보를 검색합니다.
    사용 시점: 특정 인물의 경력, 학력, 고향 등이 필요할 때
    입력: 인물 이름과 검색할 정보""",
    func=search_linkedin
)

# Agent에 Tool 등록
tools = [google_search, linkedin_search]`}</pre>
              </div>
              <div className="tool-tip">
                <Info size={14} />
                <span><strong>description</strong>이 LLM이 어떤 상황에서 이 Tool을 사용할지 판단하는 핵심 힌트입니다.</span>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3><Activity size={18} /> ReAct Prompt 템플릿</h3>
                <span className="section-subtitle">Agent의 사고 과정 유도</span>
              </div>
              <div className="code-example">
                <pre>{`REACT_PROMPT = """
Answer the following questions as best you can.
You have access to the following tools:
{tools}

Use the following format:

Question: the input question
Thought: think about what to do
Action: the action to take, one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: the final answer

Question: {input}
{agent_scratchpad}
"""`}</pre>
              </div>
            </div>
          </div>

          {/* LangGraph 아키텍처 다이어그램 */}
          <div className="card langgraph-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><GitBranch size={18} /> LangGraph 워크플로우</h3>
              <span className="section-subtitle">상태 기반 그래프 오케스트레이션</span>
            </div>
            <div className="langgraph-content">
              <div className="langgraph-charts">
                <div className="langgraph-section">
                  <h4>ReAct Agent 그래프</h4>
                  <MermaidChart
                    chart={`
graph TD
    START((Start)) --> A[Agent Node]
    A -->|"tool_call"| B[Tool Node]
    B -->|"result"| A
    A -->|"final_answer"| END((End))

    style START fill:#22c55e,stroke:#16a34a,color:#fff
    style END fill:#ef4444,stroke:#dc2626,color:#fff
    style A fill:#3b82f6,stroke:#2563eb,color:#fff
    style B fill:#f97316,stroke:#ea580c,color:#fff
                    `}
                    className="mermaid-react"
                  />
                </div>
                <div className="langgraph-section">
                  <h4>Multi-Agent Supervisor 그래프</h4>
                  <MermaidChart
                    chart={`
graph TD
    START((Start)) --> S[Supervisor]
    S -->|"research"| R[Research Agent]
    S -->|"write"| W[Writer Agent]
    S -->|"review"| V[Reviewer Agent]
    R -->|"done"| S
    W -->|"done"| S
    V -->|"done"| S
    S -->|"FINISH"| END((End))

    style START fill:#22c55e,stroke:#16a34a,color:#fff
    style END fill:#ef4444,stroke:#dc2626,color:#fff
    style S fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style R fill:#3b82f6,stroke:#2563eb,color:#fff
    style W fill:#f97316,stroke:#ea580c,color:#fff
    style V fill:#22c55e,stroke:#16a34a,color:#fff
                    `}
                    className="mermaid-supervisor"
                  />
                </div>
              </div>
              <div className="langgraph-code">
                <h4>LangGraph 코드 예시</h4>
                <pre>{`from langgraph.graph import StateGraph, END

# 상태 정의
class AgentState(TypedDict):
    messages: List[BaseMessage]
    next: str

# 그래프 생성
workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node("supervisor", supervisor_chain)
workflow.add_node("researcher", research_agent)
workflow.add_node("writer", writer_agent)

# 조건부 엣지
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next"],
    {
        "researcher": "researcher",
        "writer": "writer",
        "FINISH": END
    }
)

# 컴파일
graph = workflow.compile()`}</pre>
              </div>
            </div>
          </div>

          {/* Multi-Agent 아키텍처 */}
          <div className="card multi-agent-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Layers size={18} /> Multi-Agent 아키텍처</h3>
              <span className="section-subtitle">여러 에이전트 협업 패턴</span>
            </div>
            <div className="multi-agent-content">
              <div className="multi-agent-diagram">
                <div className="supervisor-agent">
                  <div className="agent-box supervisor">
                    <div className="agent-icon">👑</div>
                    <div className="agent-name">Supervisor Agent</div>
                    <div className="agent-role">작업 분배 및 조율</div>
                  </div>
                </div>
                <div className="agent-connections">
                  <div className="connection-line"></div>
                  <div className="connection-line"></div>
                  <div className="connection-line"></div>
                </div>
                <div className="sub-agents">
                  <div className="agent-box sub">
                    <div className="agent-icon">👤</div>
                    <div className="agent-name">Customer Agent</div>
                    <div className="agent-role">고객 정보 처리</div>
                    <div className="agent-tools">
                      <span>CRM</span>
                      <span>LinkedIn</span>
                    </div>
                  </div>
                  <div className="agent-box sub">
                    <div className="agent-icon">💰</div>
                    <div className="agent-name">Sales Agent</div>
                    <div className="agent-role">매출/영업 정보</div>
                    <div className="agent-tools">
                      <span>ERP</span>
                      <span>Forecast</span>
                    </div>
                  </div>
                  <div className="agent-box sub">
                    <div className="agent-icon">📝</div>
                    <div className="agent-name">Writer Agent</div>
                    <div className="agent-role">문서 작성</div>
                    <div className="agent-tools">
                      <span>Docs</span>
                      <span>Email</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="multi-agent-patterns">
                <h4>협업 패턴</h4>
                <div className="pattern-list">
                  <div className="pattern-item">
                    <span className="pattern-icon">📋</span>
                    <div className="pattern-info">
                      <strong>Commander 패턴</strong>
                      <p>Supervisor가 작업을 분배하고 결과를 수집</p>
                    </div>
                  </div>
                  <div className="pattern-item">
                    <span className="pattern-icon">📢</span>
                    <div className="pattern-info">
                      <strong>Broadcast 패턴</strong>
                      <p>여러 에이전트에게 동시에 질문 (그룹 채팅)</p>
                    </div>
                  </div>
                  <div className="pattern-item">
                    <span className="pattern-icon">💬</span>
                    <div className="pattern-info">
                      <strong>Conversation 패턴</strong>
                      <p>에이전트끼리 토론하여 결론 도출</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 오케스트레이션 비교 */}
          <div className="grid grid-2" style={{ marginTop: '20px' }}>
            <div className="card">
              <div className="card-header">
                <h3><ArrowRightLeft size={18} /> Pipeline (순차 실행)</h3>
              </div>
              <div className="orchestration-diagram pipeline">
                <div className="orch-step">질문</div>
                <div className="orch-arrow">→</div>
                <div className="orch-step">LLM #1</div>
                <div className="orch-arrow">→</div>
                <div className="orch-step">LLM #2</div>
                <div className="orch-arrow">→</div>
                <div className="orch-step">답변</div>
              </div>
              <div className="orch-example">
                <h4>예시: 여행 정보</h4>
                <pre>{`# Step 1: 장소 추천
places = llm1("한국의 유명 관광지")

# Step 2: 레스토랑 검색 (병렬)
restaurants = llm2(f"{places}의 맛집")

# Step 3: 교통 정보 (병렬)
transport = llm3(f"{places}까지 교통편")`}</pre>
              </div>
              <p className="orch-desc">LangChain LCEL로 구현, 단순한 순차/병렬 처리</p>
            </div>

            <div className="card">
              <div className="card-header">
                <h3><Activity size={18} /> Graph (조건부 루프)</h3>
              </div>
              <div className="orchestration-diagram graph">
                <div className="graph-nodes">
                  <div className="orch-step">Router</div>
                  <div className="orch-arrow">→</div>
                  <div className="orch-step">RAG</div>
                  <div className="orch-arrow">→</div>
                  <div className="orch-step">Tools</div>
                </div>
                <div className="graph-loop">
                  <span>↩ Loop back (조건부)</span>
                </div>
              </div>
              <div className="orch-example">
                <h4>예시: Agent 워크플로우</h4>
                <pre>{`graph = StateGraph(AgentState)
graph.add_node("think", think_node)
graph.add_node("act", action_node)
graph.add_conditional_edges(
    "act", should_continue,
    {"yes": "think", "no": END}
)  # 루프 구조 가능`}</pre>
              </div>
              <p className="orch-desc">LangGraph로 구현, 상태 기반 조건부 분기 및 루프</p>
            </div>
          </div>

          {/* 현재 클러스터 Agent 인프라 상태 */}
          <div className="card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Server size={18} /> 현재 클러스터 Agent 인프라</h3>
            </div>
            <div className="agent-infra-grid">
              <div className="infra-card">
                <div className="infra-header">
                  <span className="infra-icon">🤖</span>
                  <span className="infra-title">LLM Engine</span>
                </div>
                <div className={`infra-status-large ${workloads?.vllm?.status === 'running' ? 'active' : 'inactive'}`}>
                  {workloads?.vllm?.status === 'running' ? 'vLLM 실행중' : '미실행'}
                </div>
                <div className="infra-desc">Agent의 두뇌 역할</div>
              </div>
              <div className="infra-card">
                <div className="infra-header">
                  <span className="infra-icon">🔍</span>
                  <span className="infra-title">Vector Store (RAG)</span>
                </div>
                <div className={`infra-status-large ${workloads?.qdrant?.status === 'running' ? 'active' : 'inactive'}`}>
                  {workloads?.qdrant?.status === 'running' ? 'Qdrant 실행중' : '미실행'}
                </div>
                <div className="infra-desc">문서 검색 Tool</div>
              </div>
              <div className="infra-card">
                <div className="infra-header">
                  <span className="infra-icon">🕸️</span>
                  <span className="infra-title">Graph Store</span>
                </div>
                <div className={`infra-status-large ${workloads?.neo4j?.status === 'running' ? 'active' : 'inactive'}`}>
                  {workloads?.neo4j?.status === 'running' ? 'Neo4j 실행중' : '미실행'}
                </div>
                <div className="infra-desc">관계 검색 Tool</div>
              </div>
              <div className="infra-card">
                <div className="infra-header">
                  <span className="infra-icon">📊</span>
                  <span className="infra-title">Observability</span>
                </div>
                <div className="infra-status-large inactive">Langfuse 미배포</div>
                <div className="infra-desc">Agent 실행 추적</div>
              </div>
            </div>
          </div>

          {/* Langfuse 모니터링 */}
          <div className="card langfuse-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><BarChart3 size={18} /> Langfuse - LLM Observability</h3>
              <span className="section-subtitle">Agent 실행 모니터링 및 분석</span>
            </div>
            <div className="langfuse-features">
              <div className="feature-item">
                <div className="feature-icon">📈</div>
                <div className="feature-content">
                  <strong>Trace 추적</strong>
                  <p>모든 LLM 호출, Tool 실행, 응답 시간 기록</p>
                </div>
              </div>
              <div className="feature-item">
                <div className="feature-icon">💰</div>
                <div className="feature-content">
                  <strong>비용 분석</strong>
                  <p>토큰 사용량 및 API 비용 실시간 추적</p>
                </div>
              </div>
              <div className="feature-item">
                <div className="feature-icon">📝</div>
                <div className="feature-content">
                  <strong>프롬프트 관리</strong>
                  <p>프롬프트 버전 관리 및 A/B 테스트</p>
                </div>
              </div>
              <div className="feature-item">
                <div className="feature-icon">🔍</div>
                <div className="feature-content">
                  <strong>디버깅</strong>
                  <p>Agent 실행 과정 상세 분석</p>
                </div>
              </div>
            </div>
            <div className="code-example">
              <h4>Langfuse 연동 예시</h4>
              <pre>{`from langfuse.callback import CallbackHandler

# Langfuse 핸들러 설정
langfuse_handler = CallbackHandler(
    public_key="pk-...",
    secret_key="sk-...",
    host="http://langfuse.ai-workloads:3000"
)

# Agent 실행 시 Langfuse로 추적
response = agent.invoke(
    {"input": "2023년 챔피언의 고향은?"},
    config={"callbacks": [langfuse_handler]}
)
# → Langfuse 대시보드에서 전체 실행 과정 확인 가능`}</pre>
            </div>
          </div>

          {/* Workflow Editor 섹션 */}
          <WorkflowSection />
        </section>
      )}

      {/* Goal Tab - Service Architecture */}
      {activeTab === 'goal' && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">Service Architecture Goal</h2>
            <span className="section-subtitle">클러스터 리소스 할당 및 API 서비스 제공 플랫폼</span>
          </div>

          {/* Vision Statement */}
          <div className="goal-vision">
            <div className="vision-icon">🎯</div>
            <h3>최종 목표</h3>
            <p>
              <strong>AI 인프라 통합 플랫폼</strong>으로서 사용자에게 Kubernetes 클러스터 리소스를
              동적으로 할당하거나, 베어메탈 GPU 서버를 직접 대여하고,
              완성된 AI 모델을 API 형태로 제공하는 원스톱 서비스
            </p>
          </div>

          {/* Service Modes */}
          <div className="goal-services">
            <h3>🛠️ 제공 서비스 유형</h3>
            <div className="service-cards">
              <div className="service-card cluster">
                <div className="service-icon">☸️</div>
                <h4>Cluster Resource</h4>
                <p className="service-desc">K8s 네임스페이스 할당</p>
                <ul className="service-features">
                  <li>CPU/Memory 동적 스케일링</li>
                  <li>GPU 할당 (vGPU 지원)</li>
                  <li>Storage 자동 프로비저닝</li>
                  <li>네임스페이스 격리</li>
                </ul>
                <div className="service-use-case">
                  <span className="label">적합 대상</span>
                  <span>ML 개발팀, 데이터 사이언티스트</span>
                </div>
              </div>

              <div className="service-card baremetal">
                <div className="service-icon">🖥️</div>
                <h4>Bare Metal</h4>
                <p className="service-desc">전용 GPU 서버 대여</p>
                <ul className="service-features">
                  <li>전용 GPU 할당 (A100/H100)</li>
                  <li>Root 권한 제공</li>
                  <li>커스텀 환경 구성</li>
                  <li>고성능 NVMe SSD</li>
                </ul>
                <div className="service-use-case">
                  <span className="label">적합 대상</span>
                  <span>대규모 모델 학습, 연구팀</span>
                </div>
              </div>

              <div className="service-card api">
                <div className="service-icon">🔌</div>
                <h4>API Service</h4>
                <p className="service-desc">AI 모델 API 제공</p>
                <ul className="service-features">
                  <li>LLM Inference API</li>
                  <li>Embedding API</li>
                  <li>Image Generation API</li>
                  <li>사용량 기반 과금</li>
                </ul>
                <div className="service-use-case">
                  <span className="label">적합 대상</span>
                  <span>앱 개발자, 스타트업</span>
                </div>
              </div>
            </div>
          </div>

          {/* Architecture Diagram */}
          <div className="goal-architecture">
            <h3>🏗️ 전체 시스템 아키텍처</h3>

            <div className="architecture-diagram-full">
              {/* Frontend Layer */}
              <div className="arch-layer frontend-layer">
                <div className="layer-label">Frontend (사용자 인터페이스)</div>
                <div className="layer-content">
                  <div className="arch-component">
                    <div className="comp-icon">🌐</div>
                    <div className="comp-name">Web Dashboard</div>
                    <div className="comp-tech">React + Vite</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">📱</div>
                    <div className="comp-name">User Portal</div>
                    <div className="comp-tech">Next.js</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">📊</div>
                    <div className="comp-name">Admin Console</div>
                    <div className="comp-tech">Grafana</div>
                  </div>
                </div>
              </div>

              <div className="arch-arrow-down">▼</div>

              {/* API Gateway Layer */}
              <div className="arch-layer gateway-layer">
                <div className="layer-label">API Gateway (인증/라우팅)</div>
                <div className="layer-content">
                  <div className="arch-component highlight">
                    <div className="comp-icon">🚪</div>
                    <div className="comp-name">Traefik Ingress</div>
                    <div className="comp-tech">L7 Load Balancer</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">🔐</div>
                    <div className="comp-name">Auth Service</div>
                    <div className="comp-tech">Keycloak / OAuth2</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">📈</div>
                    <div className="comp-name">Rate Limiter</div>
                    <div className="comp-tech">Redis</div>
                  </div>
                </div>
              </div>

              <div className="arch-arrow-down">▼</div>

              {/* Backend Services Layer */}
              <div className="arch-layer backend-layer">
                <div className="layer-label">Backend Services (비즈니스 로직)</div>
                <div className="layer-content">
                  <div className="arch-component">
                    <div className="comp-icon">⚙️</div>
                    <div className="comp-name">Resource Manager</div>
                    <div className="comp-tech">Python FastAPI</div>
                    <div className="comp-desc">리소스 할당/관리</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">📋</div>
                    <div className="comp-name">Billing Service</div>
                    <div className="comp-tech">Go + PostgreSQL</div>
                    <div className="comp-desc">사용량 계산/과금</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">🔔</div>
                    <div className="comp-name">Notification</div>
                    <div className="comp-tech">Node.js</div>
                    <div className="comp-desc">알림/메시징</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">📝</div>
                    <div className="comp-name">Audit Logger</div>
                    <div className="comp-tech">ELK Stack</div>
                    <div className="comp-desc">감사 로그</div>
                  </div>
                </div>
              </div>

              <div className="arch-arrow-down">▼</div>

              {/* Infrastructure Control Layer */}
              <div className="arch-layer infra-layer">
                <div className="layer-label">Infrastructure Control (인프라 제어)</div>
                <div className="layer-content">
                  <div className="arch-component">
                    <div className="comp-icon">☸️</div>
                    <div className="comp-name">K8s Operator</div>
                    <div className="comp-tech">Custom Controller</div>
                    <div className="comp-desc">네임스페이스/Pod 관리</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">🖥️</div>
                    <div className="comp-name">Bare Metal Provisioner</div>
                    <div className="comp-tech">Ansible + IPMI</div>
                    <div className="comp-desc">서버 프로비저닝</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">🎮</div>
                    <div className="comp-name">GPU Scheduler</div>
                    <div className="comp-tech">NVIDIA MPS/MIG</div>
                    <div className="comp-desc">GPU 할당 최적화</div>
                  </div>
                </div>
              </div>

              <div className="arch-arrow-down">▼</div>

              {/* Physical Infrastructure */}
              <div className="arch-layer physical-layer">
                <div className="layer-label">Physical Infrastructure (물리 인프라)</div>
                <div className="layer-content">
                  <div className="arch-component">
                    <div className="comp-icon">🖧</div>
                    <div className="comp-name">K3s Cluster</div>
                    <div className="comp-tech">3 Masters + N Workers</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">💾</div>
                    <div className="comp-name">Longhorn Storage</div>
                    <div className="comp-tech">Distributed Block</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">🎮</div>
                    <div className="comp-name">GPU Nodes</div>
                    <div className="comp-tech">NVIDIA A100/RTX</div>
                  </div>
                  <div className="arch-component">
                    <div className="comp-icon">🗄️</div>
                    <div className="comp-name">Object Storage</div>
                    <div className="comp-tech">MinIO S3</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Data Flow */}
          <div className="goal-dataflow">
            <h3>🔄 데이터 흐름</h3>
            <div className="dataflow-scenarios">

              <div className="dataflow-scenario">
                <h4>📦 Scenario 1: 클러스터 리소스 할당</h4>
                <div className="flow-steps">
                  <div className="flow-step">
                    <div className="step-num">1</div>
                    <div className="step-content">
                      <strong>사용자 요청</strong>
                      <span>Web UI에서 리소스 요청 (CPU 4, Memory 8Gi, GPU 1)</span>
                    </div>
                  </div>
                  <div className="flow-arrow">→</div>
                  <div className="flow-step">
                    <div className="step-num">2</div>
                    <div className="step-content">
                      <strong>인증 & 권한 확인</strong>
                      <span>Keycloak JWT 검증, RBAC 권한 체크</span>
                    </div>
                  </div>
                  <div className="flow-arrow">→</div>
                  <div className="flow-step">
                    <div className="step-num">3</div>
                    <div className="step-content">
                      <strong>리소스 가용성 확인</strong>
                      <span>K8s API로 노드 리소스 조회</span>
                    </div>
                  </div>
                  <div className="flow-arrow">→</div>
                  <div className="flow-step">
                    <div className="step-num">4</div>
                    <div className="step-content">
                      <strong>네임스페이스 생성</strong>
                      <span>ResourceQuota, LimitRange 적용</span>
                    </div>
                  </div>
                  <div className="flow-arrow">→</div>
                  <div className="flow-step">
                    <div className="step-num">5</div>
                    <div className="step-content">
                      <strong>접근 정보 제공</strong>
                      <span>kubeconfig, Dashboard URL 발급</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="dataflow-scenario">
                <h4>🔌 Scenario 2: API 서비스 호출</h4>
                <div className="flow-steps">
                  <div className="flow-step">
                    <div className="step-num">1</div>
                    <div className="step-content">
                      <strong>API 요청</strong>
                      <span>POST /v1/chat/completions (API Key 포함)</span>
                    </div>
                  </div>
                  <div className="flow-arrow">→</div>
                  <div className="flow-step">
                    <div className="step-num">2</div>
                    <div className="step-content">
                      <strong>Rate Limiting</strong>
                      <span>Redis에서 사용량 체크 (100 req/min)</span>
                    </div>
                  </div>
                  <div className="flow-arrow">→</div>
                  <div className="flow-step">
                    <div className="step-num">3</div>
                    <div className="step-content">
                      <strong>모델 라우팅</strong>
                      <span>요청 모델에 따라 vLLM 인스턴스로 전달</span>
                    </div>
                  </div>
                  <div className="flow-arrow">→</div>
                  <div className="flow-step">
                    <div className="step-num">4</div>
                    <div className="step-content">
                      <strong>Inference 실행</strong>
                      <span>GPU에서 모델 추론 수행</span>
                    </div>
                  </div>
                  <div className="flow-arrow">→</div>
                  <div className="flow-step">
                    <div className="step-num">5</div>
                    <div className="step-content">
                      <strong>사용량 기록</strong>
                      <span>Token 수 계산, Billing DB 기록</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Team Roles */}
          <div className="goal-team">
            <h3>👥 팀 역할 및 담당 영역</h3>
            <div className="team-grid">
              <div className="team-role">
                <div className="role-icon">🎨</div>
                <h4>Frontend</h4>
                <ul>
                  <li>User Portal 개발</li>
                  <li>Dashboard UI/UX</li>
                  <li>API Documentation</li>
                </ul>
                <div className="tech-stack">
                  <span>React</span>
                  <span>Next.js</span>
                  <span>TailwindCSS</span>
                </div>
              </div>

              <div className="team-role">
                <div className="role-icon">⚙️</div>
                <h4>Backend</h4>
                <ul>
                  <li>Resource Manager API</li>
                  <li>Billing Logic</li>
                  <li>Auth Integration</li>
                </ul>
                <div className="tech-stack">
                  <span>FastAPI</span>
                  <span>Go</span>
                  <span>PostgreSQL</span>
                </div>
              </div>

              <div className="team-role">
                <div className="role-icon">☸️</div>
                <h4>Infrastructure</h4>
                <ul>
                  <li>K8s Cluster 운영</li>
                  <li>GPU Scheduling</li>
                  <li>Storage 관리</li>
                </ul>
                <div className="tech-stack">
                  <span>K3s</span>
                  <span>Longhorn</span>
                  <span>Traefik</span>
                </div>
              </div>

              <div className="team-role">
                <div className="role-icon">🤖</div>
                <h4>ML/AI</h4>
                <ul>
                  <li>모델 최적화</li>
                  <li>vLLM 운영</li>
                  <li>Fine-tuning Pipeline</li>
                </ul>
                <div className="tech-stack">
                  <span>vLLM</span>
                  <span>PyTorch</span>
                  <span>Qdrant</span>
                </div>
              </div>
            </div>
          </div>

          {/* Implementation Roadmap */}
          <div className="goal-roadmap">
            <h3>📅 구현 로드맵</h3>
            <div className="roadmap-timeline">
              <div className="roadmap-phase current">
                <div className="phase-header">
                  <span className="phase-badge">Phase 1</span>
                  <span className="phase-status">현재</span>
                </div>
                <h4>Foundation</h4>
                <ul>
                  <li className="done">K3s 클러스터 구축</li>
                  <li className="done">Longhorn Storage 연동</li>
                  <li className="done">GPU 노드 설정</li>
                  <li className="done">기본 모니터링 대시보드</li>
                  <li className="done">vLLM 배포</li>
                </ul>
              </div>

              <div className="roadmap-phase next">
                <div className="phase-header">
                  <span className="phase-badge">Phase 2</span>
                  <span className="phase-status">다음</span>
                </div>
                <h4>Platform Services</h4>
                <ul>
                  <li>Resource Manager API 개발</li>
                  <li>사용자 인증 시스템 (Keycloak)</li>
                  <li>네임스페이스 자동 프로비저닝</li>
                  <li>기본 과금 시스템</li>
                  <li>User Portal MVP</li>
                </ul>
              </div>

              <div className="roadmap-phase future">
                <div className="phase-header">
                  <span className="phase-badge">Phase 3</span>
                  <span className="phase-status">계획</span>
                </div>
                <h4>Advanced Features</h4>
                <ul>
                  <li>Bare Metal Provisioning</li>
                  <li>Multi-tenant 완전 격리</li>
                  <li>자동 스케일링</li>
                  <li>SLA 모니터링</li>
                  <li>결제 시스템 연동</li>
                </ul>
              </div>

              <div className="roadmap-phase future">
                <div className="phase-header">
                  <span className="phase-badge">Phase 4</span>
                  <span className="phase-status">장기</span>
                </div>
                <h4>Scale & Optimize</h4>
                <ul>
                  <li>Multi-Cluster 연합</li>
                  <li>글로벌 엣지 노드</li>
                  <li>AI 기반 리소스 최적화</li>
                  <li>Marketplace 오픈</li>
                  <li>Enterprise 기능</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Current Status */}
          <div className="goal-current-status">
            <h3>📊 현재 인프라 현황</h3>
            <div className="status-grid">
              <div className="status-card">
                <div className="status-icon running">✓</div>
                <h4>K3s Cluster</h4>
                <div className="status-detail">
                  <div className="detail-row">
                    <span>Master Nodes</span>
                    <span className="value">{clusterSummary?.nodes?.total || 1}</span>
                  </div>
                  <div className="detail-row">
                    <span>Version</span>
                    <span className="value">v1.31.x</span>
                  </div>
                  <div className="detail-row">
                    <span>Status</span>
                    <span className="value running">운영중</span>
                  </div>
                </div>
              </div>

              <div className="status-card">
                <div className="status-icon running">✓</div>
                <h4>GPU Resources</h4>
                <div className="status-detail">
                  <div className="detail-row">
                    <span>총 GPU</span>
                    <span className="value">{gpuDetailed?.gpus?.length || gpuStatus?.total || 0}개</span>
                  </div>
                  <div className="detail-row">
                    <span>모델</span>
                    <span className="value">{gpuDetailed?.gpus?.[0]?.name || 'N/A'}</span>
                  </div>
                  <div className="detail-row">
                    <span>할당</span>
                    <span className="value">vLLM, ComfyUI</span>
                  </div>
                </div>
              </div>

              <div className="status-card">
                <div className="status-icon running">✓</div>
                <h4>Storage</h4>
                <div className="status-detail">
                  <div className="detail-row">
                    <span>Type</span>
                    <span className="value">Longhorn</span>
                  </div>
                  <div className="detail-row">
                    <span>Replicas</span>
                    <span className="value">2</span>
                  </div>
                  <div className="detail-row">
                    <span>Object Storage</span>
                    <span className="value">MinIO</span>
                  </div>
                </div>
              </div>

              <div className="status-card">
                <div className="status-icon running">✓</div>
                <h4>AI Services</h4>
                <div className="status-detail">
                  <div className="detail-row">
                    <span>LLM</span>
                    <span className="value running">vLLM 운영중</span>
                  </div>
                  <div className="detail-row">
                    <span>Vector DB</span>
                    <span className="value running">Qdrant 운영중</span>
                  </div>
                  <div className="detail-row">
                    <span>Image Gen</span>
                    <span className="value running">ComfyUI 운영중</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* API Examples */}
          <div className="goal-api-examples">
            <h3>🔌 예상 API 인터페이스</h3>
            <div className="api-examples-grid">
              <div className="api-example">
                <h4>리소스 할당 요청</h4>
                <pre>{`POST /api/v1/resources/allocate
{
  "type": "kubernetes",
  "resources": {
    "cpu": "4",
    "memory": "8Gi",
    "gpu": 1,
    "storage": "50Gi"
  },
  "duration": "30d",
  "project_name": "my-ml-project"
}

Response:
{
  "namespace": "user-12345-my-ml-project",
  "kubeconfig": "base64...",
  "dashboard_url": "https://dashboard.example.com/ns/...",
  "expires_at": "2026-02-08T00:00:00Z"
}`}</pre>
              </div>

              <div className="api-example">
                <h4>LLM API 호출</h4>
                <pre>{`POST /api/v1/chat/completions
Authorization: Bearer sk-xxx...
{
  "model": "llama-3.1-8b",
  "messages": [
    {"role": "user", "content": "안녕하세요"}
  ],
  "max_tokens": 100
}

Response:
{
  "id": "chatcmpl-xxx",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "안녕하세요! 무엇을 도와드릴까요?"
    }
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}`}</pre>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* LLM Tab - Transformer Architecture & Training/Inference */}
      {activeTab === 'llm' && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">LLM (Large Language Model)</h2>
            <span className="section-subtitle">Transformer 아키텍처와 학습/추론 과정 이해</span>
          </div>

          {/* LLM as Black Box */}
          <div className="card llm-blackbox-card">
            <div className="card-header">
              <h3><Box size={18} /> LLM = 블랙박스</h3>
              <span className="section-subtitle">기억이 없는 확률적 텍스트 생성기</span>
            </div>
            <div className="llm-blackbox-content">
              <div className="blackbox-diagram">
                <div className="blackbox-input">
                  <div className="input-header">INPUT (Prompt)</div>
                  <div className="input-example">
                    <div className="token-list">
                      <span className="token">"오늘"</span>
                      <span className="token">"날씨가"</span>
                      <span className="token">"어때?"</span>
                    </div>
                    <div className="input-note">텍스트 → 토큰화</div>
                  </div>
                </div>

                <div className="blackbox-arrow">→</div>

                <div className="blackbox-model">
                  <div className="model-box">
                    <div className="model-icon">🧠</div>
                    <div className="model-label">LLM</div>
                    <div className="model-params">7B ~ 405B Parameters</div>
                  </div>
                  <div className="model-notes">
                    <div className="note-item warning">
                      <AlertTriangle size={14} />
                      <span>기억 없음 (Stateless)</span>
                    </div>
                    <div className="note-item">
                      <Info size={14} />
                      <span>매 호출마다 새롭게 시작</span>
                    </div>
                  </div>
                </div>

                <div className="blackbox-arrow">→</div>

                <div className="blackbox-output">
                  <div className="output-header">OUTPUT (Response)</div>
                  <div className="output-example">
                    <div className="token-list">
                      <span className="token generated">"오늘"</span>
                      <span className="token generated">"날씨는"</span>
                      <span className="token generated">"맑고"</span>
                      <span className="token generated">...</span>
                    </div>
                    <div className="output-note">
                      <strong>다음 토큰 확률 예측</strong>
                      <div className="prob-example">
                        <span>"맑고" 35%</span>
                        <span>"흐리고" 25%</span>
                        <span>"좋아요" 20%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="blackbox-key-points">
                <div className="key-point">
                  <span className="point-icon">📝</span>
                  <div>
                    <strong>입력 형식</strong>
                    <p>텍스트를 토큰(단어/서브워드)으로 분리하여 숫자 ID로 변환</p>
                  </div>
                </div>
                <div className="key-point">
                  <span className="point-icon">🎲</span>
                  <div>
                    <strong>확률적 출력</strong>
                    <p>다음에 올 토큰의 확률 분포를 예측하고 샘플링 (temperature로 제어)</p>
                  </div>
                </div>
                <div className="key-point">
                  <span className="point-icon">🧊</span>
                  <div>
                    <strong>기억 없음 (Stateless)</strong>
                    <p>이전 대화를 기억 못함 → 매번 전체 컨텍스트를 입력에 포함해야 함</p>
                  </div>
                </div>
                <div className="key-point">
                  <span className="point-icon">📏</span>
                  <div>
                    <strong>Context Window</strong>
                    <p>최대 입력 길이 제한 (4K ~ 128K tokens), 초과 시 잘림</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Transformer Architecture */}
          <div className="card transformer-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Layers size={18} /> Transformer 아키텍처</h3>
              <span className="section-subtitle">"Attention Is All You Need" (2017)</span>
            </div>
            <div className="transformer-architecture">
              <svg viewBox="0 0 900 600" className="transformer-svg">
                {/* Input Embedding */}
                <g className="input-section">
                  <rect x="50" y="480" width="100" height="60" rx="6" fill="#4dabf7" fillOpacity="0.2" stroke="#4dabf7" strokeWidth="2"/>
                  <text x="100" y="505" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Input</text>
                  <text x="100" y="520" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Embedding</text>
                  <text x="100" y="535" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">토큰 → 벡터</text>
                </g>

                {/* Positional Encoding */}
                <g className="pos-encoding">
                  <rect x="170" y="480" width="100" height="60" rx="6" fill="#69db7c" fillOpacity="0.2" stroke="#69db7c" strokeWidth="2"/>
                  <text x="220" y="505" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Positional</text>
                  <text x="220" y="520" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Encoding</text>
                  <text x="220" y="535" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">위치 정보</text>
                </g>

                {/* Add symbol */}
                <circle cx="135" cy="510" r="12" fill="var(--bg-tertiary)" stroke="var(--border-color)" strokeWidth="1"/>
                <text x="135" y="515" textAnchor="middle" fill="var(--text-primary)" fontSize="16">+</text>

                {/* Transformer Block (repeated Nx) */}
                <g className="transformer-block">
                  <rect x="50" y="150" width="220" height="300" rx="10" fill="var(--bg-secondary)" stroke="var(--accent-primary)" strokeWidth="2" strokeDasharray="5,5"/>
                  <text x="160" y="175" textAnchor="middle" fill="var(--accent-primary)" fontSize="12" fontWeight="700">Transformer Block × N</text>

                  {/* Multi-Head Attention */}
                  <rect x="70" y="195" width="180" height="80" rx="6" fill="#f06595" fillOpacity="0.2" stroke="#f06595" strokeWidth="2"/>
                  <text x="160" y="225" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="700">Multi-Head</text>
                  <text x="160" y="242" textAnchor="middle" fill="var(--text-primary)" fontSize="12" fontWeight="700">Self-Attention</text>
                  <text x="160" y="260" textAnchor="middle" fill="#f06595" fontSize="10">Q, K, V 계산</text>

                  {/* Add & Norm 1 */}
                  <rect x="70" y="290" width="180" height="35" rx="4" fill="#ffd43b" fillOpacity="0.2" stroke="#ffd43b" strokeWidth="1.5"/>
                  <text x="160" y="312" textAnchor="middle" fill="var(--text-primary)" fontSize="10">Add & Layer Norm</text>

                  {/* Feed Forward */}
                  <rect x="70" y="340" width="180" height="60" rx="6" fill="#b197fc" fillOpacity="0.2" stroke="#b197fc" strokeWidth="2"/>
                  <text x="160" y="365" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Feed Forward</text>
                  <text x="160" y="385" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">MLP (Up → Down)</text>

                  {/* Add & Norm 2 */}
                  <rect x="70" y="415" width="180" height="35" rx="4" fill="#ffd43b" fillOpacity="0.2" stroke="#ffd43b" strokeWidth="1.5"/>
                  <text x="160" y="437" textAnchor="middle" fill="var(--text-primary)" fontSize="10">Add & Layer Norm</text>
                </g>

                {/* Output Layer */}
                <g className="output-section">
                  <rect x="50" y="50" width="220" height="60" rx="6" fill="#51cf66" fillOpacity="0.2" stroke="#51cf66" strokeWidth="2"/>
                  <text x="160" y="75" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Linear + Softmax</text>
                  <text x="160" y="95" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">다음 토큰 확률 분포</text>
                </g>

                {/* Arrows */}
                <path d="M160 480 L160 460 L160 450" stroke="var(--text-secondary)" strokeWidth="2" fill="none" markerEnd="url(#arrowhead2)"/>
                <path d="M160 150 L160 110" stroke="var(--text-secondary)" strokeWidth="2" fill="none" markerEnd="url(#arrowhead2)"/>

                {/* Self-Attention Detail (Right side) */}
                <g className="attention-detail" transform="translate(320, 150)">
                  <rect x="0" y="0" width="350" height="300" rx="10" fill="var(--bg-secondary)" stroke="#f06595" strokeWidth="2"/>
                  <text x="175" y="25" textAnchor="middle" fill="#f06595" fontSize="13" fontWeight="700">Self-Attention 상세</text>

                  {/* Q, K, V visualization */}
                  <g transform="translate(20, 50)">
                    <rect x="0" y="0" width="80" height="50" rx="4" fill="#ff8787" fillOpacity="0.3" stroke="#ff8787" strokeWidth="1.5"/>
                    <text x="40" y="20" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Query (Q)</text>
                    <text x="40" y="38" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">"무엇을 찾을까?"</text>

                    <rect x="100" y="0" width="80" height="50" rx="4" fill="#74c0fc" fillOpacity="0.3" stroke="#74c0fc" strokeWidth="1.5"/>
                    <text x="140" y="20" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Key (K)</text>
                    <text x="140" y="38" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">"나는 이런 정보"</text>

                    <rect x="200" y="0" width="80" height="50" rx="4" fill="#69db7c" fillOpacity="0.3" stroke="#69db7c" strokeWidth="1.5"/>
                    <text x="240" y="20" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Value (V)</text>
                    <text x="240" y="38" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">"실제 내용"</text>
                  </g>

                  {/* Attention Score Matrix */}
                  <g transform="translate(20, 120)">
                    <text x="0" y="0" fill="var(--text-primary)" fontSize="10" fontWeight="600">Attention Score = Softmax(Q × K^T / √d)</text>

                    {/* Mini matrix visualization */}
                    <g transform="translate(60, 20)">
                      <rect x="0" y="0" width="100" height="80" fill="var(--bg-tertiary)" stroke="var(--border-color)" strokeWidth="1"/>
                      {/* Grid lines */}
                      <line x1="0" y1="20" x2="100" y2="20" stroke="var(--border-color)" strokeWidth="0.5"/>
                      <line x1="0" y1="40" x2="100" y2="40" stroke="var(--border-color)" strokeWidth="0.5"/>
                      <line x1="0" y1="60" x2="100" y2="60" stroke="var(--border-color)" strokeWidth="0.5"/>
                      <line x1="25" y1="0" x2="25" y2="80" stroke="var(--border-color)" strokeWidth="0.5"/>
                      <line x1="50" y1="0" x2="50" y2="80" stroke="var(--border-color)" strokeWidth="0.5"/>
                      <line x1="75" y1="0" x2="75" y2="80" stroke="var(--border-color)" strokeWidth="0.5"/>
                      {/* Values */}
                      <text x="12" y="14" textAnchor="middle" fill="#51cf66" fontSize="10" fontWeight="600">0.8</text>
                      <text x="37" y="14" textAnchor="middle" fill="var(--text-muted)" fontSize="10">0.1</text>
                      <text x="62" y="14" textAnchor="middle" fill="var(--text-muted)" fontSize="10">0.05</text>
                      <text x="87" y="14" textAnchor="middle" fill="var(--text-muted)" fontSize="10">0.05</text>
                      <text x="12" y="34" textAnchor="middle" fill="var(--text-muted)" fontSize="10">0.2</text>
                      <text x="37" y="34" textAnchor="middle" fill="#51cf66" fontSize="10" fontWeight="600">0.6</text>
                      <text x="62" y="34" textAnchor="middle" fill="var(--text-muted)" fontSize="10">0.1</text>
                      <text x="87" y="34" textAnchor="middle" fill="var(--text-muted)" fontSize="10">0.1</text>
                    </g>
                    <text x="170" y="75" fill="var(--text-secondary)" fontSize="10">각 토큰이 다른 토큰에</text>
                    <text x="170" y="88" fill="var(--text-secondary)" fontSize="10">얼마나 주목하는지</text>
                  </g>

                  {/* Formula */}
                  <g transform="translate(20, 230)">
                    <rect x="0" y="0" width="310" height="50" rx="4" fill="var(--bg-tertiary)"/>
                    <text x="155" y="20" textAnchor="middle" fill="var(--text-primary)" fontSize="11" fontWeight="600">Output = Attention(Q,K,V) × W_o</text>
                    <text x="155" y="40" textAnchor="middle" fill="var(--text-secondary)" fontSize="10">가중치 적용된 V 값들의 합 → 다음 레이어로</text>
                  </g>
                </g>

                {/* Arrowhead marker */}
                <defs>
                  <marker id="arrowhead2" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="var(--text-secondary)"/>
                  </marker>
                </defs>

                {/* Layer counts */}
                <g className="model-specs" transform="translate(700, 400)">
                  <text x="0" y="0" fill="var(--text-secondary)" fontSize="11" fontWeight="600">모델 규모:</text>
                  <text x="0" y="20" fill="var(--text-secondary)" fontSize="10">• 7B: 32 layers, 4096 dim</text>
                  <text x="0" y="35" fill="var(--text-secondary)" fontSize="10">• 13B: 40 layers, 5120 dim</text>
                  <text x="0" y="50" fill="var(--text-secondary)" fontSize="10">• 70B: 80 layers, 8192 dim</text>
                  <text x="0" y="65" fill="var(--text-secondary)" fontSize="10">• 405B: 126 layers, 16384 dim</text>
                </g>
              </svg>

              <div className="transformer-explanation">
                <div className="exp-item">
                  <span className="exp-color" style={{background: '#4dabf7'}}></span>
                  <div>
                    <strong>Embedding</strong>
                    <p>토큰 ID를 고차원 벡터(4096~16384 dim)로 변환. Vocabulary size: 32K~128K</p>
                  </div>
                </div>
                <div className="exp-item">
                  <span className="exp-color" style={{background: '#f06595'}}></span>
                  <div>
                    <strong>Self-Attention</strong>
                    <p>모든 토큰이 서로를 참조. "나"가 "철수"와 관련있는지 파악. Multi-Head로 다양한 관계 학습</p>
                  </div>
                </div>
                <div className="exp-item">
                  <span className="exp-color" style={{background: '#b197fc'}}></span>
                  <div>
                    <strong>Feed Forward (MLP)</strong>
                    <p>Attention 결과를 비선형 변환. 실제 파라미터의 대부분이 여기에 (2/3 이상)</p>
                  </div>
                </div>
                <div className="exp-item">
                  <span className="exp-color" style={{background: '#ffd43b'}}></span>
                  <div>
                    <strong>Residual + LayerNorm</strong>
                    <p>학습 안정화. 깊은 네트워크에서 gradient 소실 방지</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Training vs Inference */}
          <div className="card training-inference-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Activity size={18} /> 학습(Training) vs 추론(Inference)</h3>
              <span className="section-subtitle">왜 학습에 3배 이상 더 많은 리소스가 필요한가?</span>
            </div>
            <div className="training-inference-content">
              <div className="ti-comparison">
                {/* Training Side */}
                <div className="ti-side training">
                  <div className="ti-header">
                    <span className="ti-icon training">🏋️</span>
                    <h4>Training (학습)</h4>
                  </div>
                  <div className="ti-diagram">
                    <div className="ti-flow">
                      <div className="ti-step">Input Batch</div>
                      <div className="ti-arrow">↓</div>
                      <div className="ti-step highlight">Forward Pass</div>
                      <div className="ti-arrow">↓</div>
                      <div className="ti-step">Loss 계산</div>
                      <div className="ti-arrow">↓</div>
                      <div className="ti-step highlight critical">Backward Pass</div>
                      <div className="ti-note">(Gradient 계산)</div>
                      <div className="ti-arrow">↓</div>
                      <div className="ti-step highlight critical">Optimizer Step</div>
                      <div className="ti-note">(파라미터 업데이트)</div>
                    </div>
                  </div>
                  <div className="ti-memory">
                    <h5>VRAM 사용량:</h5>
                    <div className="memory-breakdown">
                      <div className="mem-item">
                        <span className="mem-bar" style={{width: '30%', background: '#4dabf7'}}></span>
                        <span>Model Weights (30%)</span>
                      </div>
                      <div className="mem-item">
                        <span className="mem-bar" style={{width: '30%', background: '#ff8787'}}></span>
                        <span>Gradients (30%)</span>
                      </div>
                      <div className="mem-item">
                        <span className="mem-bar" style={{width: '25%', background: '#ffd43b'}}></span>
                        <span>Optimizer States (25%)</span>
                      </div>
                      <div className="mem-item">
                        <span className="mem-bar" style={{width: '15%', background: '#69db7c'}}></span>
                        <span>Activations (15%)</span>
                      </div>
                    </div>
                    <div className="mem-total">
                      <strong>7B 모델 기준: ~100GB VRAM</strong>
                      <p>A100 80GB × 2개 이상 필요</p>
                    </div>
                  </div>
                </div>

                {/* VS Divider */}
                <div className="ti-vs">VS</div>

                {/* Inference Side */}
                <div className="ti-side inference">
                  <div className="ti-header">
                    <span className="ti-icon inference">🚀</span>
                    <h4>Inference (추론)</h4>
                  </div>
                  <div className="ti-diagram">
                    <div className="ti-flow">
                      <div className="ti-step">Input Tokens</div>
                      <div className="ti-arrow">↓</div>
                      <div className="ti-step highlight">Forward Pass Only</div>
                      <div className="ti-arrow">↓</div>
                      <div className="ti-step">Output Logits</div>
                      <div className="ti-arrow">↓</div>
                      <div className="ti-step">Sampling</div>
                      <div className="ti-note">(다음 토큰 선택)</div>
                      <div className="ti-arrow loop">↩ 반복</div>
                    </div>
                  </div>
                  <div className="ti-memory">
                    <h5>VRAM 사용량:</h5>
                    <div className="memory-breakdown">
                      <div className="mem-item">
                        <span className="mem-bar" style={{width: '70%', background: '#4dabf7'}}></span>
                        <span>Model Weights (70%)</span>
                      </div>
                      <div className="mem-item">
                        <span className="mem-bar" style={{width: '25%', background: '#b197fc'}}></span>
                        <span>KV Cache (25%)</span>
                      </div>
                      <div className="mem-item">
                        <span className="mem-bar" style={{width: '5%', background: '#69db7c'}}></span>
                        <span>Activations (5%)</span>
                      </div>
                    </div>
                    <div className="mem-total">
                      <strong>7B 모델 기준: ~16GB VRAM</strong>
                      <p>RTX 4090 1개로 가능</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="ti-reasons">
                <h4>학습이 3배+ 더 무거운 이유:</h4>
                <div className="reason-grid">
                  <div className="reason-item">
                    <span className="reason-num">1</span>
                    <div>
                      <strong>Gradient 저장</strong>
                      <p>모든 파라미터의 기울기를 저장 (모델과 동일 크기)</p>
                    </div>
                  </div>
                  <div className="reason-item">
                    <span className="reason-num">2</span>
                    <div>
                      <strong>Optimizer States</strong>
                      <p>Adam: momentum + variance = 파라미터의 2배 추가</p>
                    </div>
                  </div>
                  <div className="reason-item">
                    <span className="reason-num">3</span>
                    <div>
                      <strong>Activation 메모리</strong>
                      <p>Backward pass를 위해 중간 결과 모두 저장</p>
                    </div>
                  </div>
                  <div className="reason-item">
                    <span className="reason-num">4</span>
                    <div>
                      <strong>Mixed Precision 오버헤드</strong>
                      <p>FP16 학습 시에도 FP32 마스터 weight 유지</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* KV Cache */}
          <div className="card kvcache-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Database size={18} /> KV Cache란?</h3>
              <span className="section-subtitle">추론 속도의 핵심 최적화</span>
            </div>
            <div className="kvcache-content">
              <div className="kvcache-comparison">
                {/* Without KV Cache */}
                <div className="kvcache-side without">
                  <h4>KV Cache 없이</h4>
                  <div className="kvcache-diagram">
                    <div className="gen-step">
                      <span className="step-label">Step 1:</span>
                      <div className="tokens-row">
                        <span className="token calc">"안녕"</span>
                        <span className="token calc">"하세요"</span>
                        <span className="token new">→ "!"</span>
                      </div>
                      <span className="calc-note">전체 계산</span>
                    </div>
                    <div className="gen-step">
                      <span className="step-label">Step 2:</span>
                      <div className="tokens-row">
                        <span className="token recalc">"안녕"</span>
                        <span className="token recalc">"하세요"</span>
                        <span className="token recalc">"!"</span>
                        <span className="token new">→ "무엇"</span>
                      </div>
                      <span className="calc-note bad">다시 전체 계산 ❌</span>
                    </div>
                    <div className="gen-step">
                      <span className="step-label">Step 3:</span>
                      <div className="tokens-row">
                        <span className="token recalc">"안녕"</span>
                        <span className="token recalc">...</span>
                        <span className="token recalc">"무엇"</span>
                        <span className="token new">→ "을"</span>
                      </div>
                      <span className="calc-note bad">또 전체 계산 ❌</span>
                    </div>
                  </div>
                  <div className="kvcache-perf bad">
                    <span>O(n²) 복잡도</span>
                    <span>100 토큰 생성 시 5050번 계산</span>
                  </div>
                </div>

                {/* With KV Cache */}
                <div className="kvcache-side with">
                  <h4>KV Cache 사용</h4>
                  <div className="kvcache-diagram">
                    <div className="gen-step">
                      <span className="step-label">Step 1:</span>
                      <div className="tokens-row">
                        <span className="token calc">"안녕"</span>
                        <span className="token calc">"하세요"</span>
                        <span className="token new">→ "!"</span>
                      </div>
                      <span className="calc-note">K,V 캐시에 저장</span>
                    </div>
                    <div className="gen-step">
                      <span className="step-label">Step 2:</span>
                      <div className="tokens-row">
                        <span className="token cached">"안녕"</span>
                        <span className="token cached">"하세요"</span>
                        <span className="token cached">"!"</span>
                        <span className="token new">→ "무엇"</span>
                      </div>
                      <span className="calc-note good">새 토큰만 계산 ✓</span>
                    </div>
                    <div className="gen-step">
                      <span className="step-label">Step 3:</span>
                      <div className="tokens-row">
                        <span className="token cached">"안녕"</span>
                        <span className="token cached">...</span>
                        <span className="token cached">"무엇"</span>
                        <span className="token new">→ "을"</span>
                      </div>
                      <span className="calc-note good">새 토큰만 계산 ✓</span>
                    </div>
                  </div>
                  <div className="kvcache-perf good">
                    <span>O(n) 복잡도</span>
                    <span>100 토큰 생성 시 100번만 계산</span>
                  </div>
                </div>
              </div>

              <div className="kvcache-detail">
                <h4>KV Cache 메모리 계산</h4>
                <div className="kvcache-formula">
                  <code>KV Cache Size = 2 × n_layers × n_heads × head_dim × seq_len × batch_size × dtype_size</code>
                </div>
                <div className="kvcache-example">
                  <strong>Llama 7B 예시 (FP16):</strong>
                  <p>= 2 × 32 × 32 × 128 × 4096 × 1 × 2 bytes</p>
                  <p>= <strong>2.1GB per request</strong> (4K context)</p>
                </div>
                <div className="kvcache-note">
                  <Info size={14} />
                  <span>Context가 길수록 KV Cache가 커지므로, 128K context 모델은 수십GB KV Cache 필요</span>
                </div>
              </div>
            </div>
          </div>

          {/* vLLM Optimizations */}
          <div className="card vllm-opt-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Zap size={18} /> vLLM 최적화 기법</h3>
              <span className="section-subtitle">고성능 LLM 서빙의 핵심</span>
            </div>
            <div className="vllm-optimizations">
              <div className="opt-grid">
                <div className="opt-item">
                  <div className="opt-header">
                    <span className="opt-icon">📦</span>
                    <h4>PagedAttention</h4>
                  </div>
                  <div className="opt-diagram">
                    <div className="paged-visual">
                      <div className="page-blocks">
                        <div className="page-block used">KV 1</div>
                        <div className="page-block used">KV 2</div>
                        <div className="page-block free">Free</div>
                        <div className="page-block used">KV 3</div>
                        <div className="page-block free">Free</div>
                      </div>
                      <div className="page-note">비연속 메모리 블록 할당</div>
                    </div>
                  </div>
                  <p className="opt-desc">OS의 가상 메모리처럼 KV Cache를 페이지 단위로 관리. 메모리 단편화 최소화.</p>
                  <div className="opt-benefit">메모리 효율 2-4배 향상</div>
                </div>

                <div className="opt-item">
                  <div className="opt-header">
                    <span className="opt-icon">📊</span>
                    <h4>Continuous Batching</h4>
                  </div>
                  <div className="opt-diagram">
                    <div className="batch-visual">
                      <div className="batch-row">
                        <span className="req active">Req A ████</span>
                        <span className="req done">Done</span>
                      </div>
                      <div className="batch-row">
                        <span className="req active">Req B ██████</span>
                        <span className="req active">████</span>
                      </div>
                      <div className="batch-row">
                        <span className="req waiting">Wait</span>
                        <span className="req active">Req C ██</span>
                      </div>
                    </div>
                  </div>
                  <p className="opt-desc">완료된 요청 자리에 즉시 새 요청 삽입. GPU 유휴 시간 최소화.</p>
                  <div className="opt-benefit">처리량 3-5배 향상</div>
                </div>

                <div className="opt-item">
                  <div className="opt-header">
                    <span className="opt-icon">🔗</span>
                    <h4>Prefix Caching</h4>
                  </div>
                  <div className="opt-diagram">
                    <div className="prefix-visual">
                      <div className="prefix-shared">[System Prompt - 공유]</div>
                      <div className="prefix-unique">
                        <span>[User A 질문]</span>
                        <span>[User B 질문]</span>
                      </div>
                    </div>
                  </div>
                  <p className="opt-desc">동일한 시스템 프롬프트의 KV Cache를 여러 요청이 공유.</p>
                  <div className="opt-benefit">System prompt 재계산 생략</div>
                </div>

                <div className="opt-item">
                  <div className="opt-header">
                    <span className="opt-icon">⚡</span>
                    <h4>Speculative Decoding</h4>
                  </div>
                  <div className="opt-diagram">
                    <div className="speculative-visual">
                      <div className="spec-row">
                        <span className="spec-draft">Draft (작은 모델)</span>
                        <span className="spec-tokens">→ → → → →</span>
                      </div>
                      <div className="spec-row">
                        <span className="spec-verify">Verify (큰 모델)</span>
                        <span className="spec-check">✓ ✓ ✓ ✗ -</span>
                      </div>
                    </div>
                  </div>
                  <p className="opt-desc">작은 모델로 여러 토큰 미리 생성, 큰 모델이 한번에 검증.</p>
                  <div className="opt-benefit">생성 속도 2-3배 향상</div>
                </div>
              </div>
            </div>
          </div>

          {/* Model Size & Hardware Requirements */}
          <div className="card hw-requirements-card" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Cpu size={18} /> 모델 크기별 하드웨어 요구사항</h3>
            </div>
            <div className="hw-requirements-table">
              <table>
                <thead>
                  <tr>
                    <th>모델 크기</th>
                    <th>파라미터</th>
                    <th>추론 (FP16)</th>
                    <th>추론 (INT8)</th>
                    <th>추론 (INT4)</th>
                    <th>학습 (FP16)</th>
                    <th>권장 GPU</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><strong>소형</strong></td>
                    <td>1.5B - 3B</td>
                    <td>4-8 GB</td>
                    <td>2-4 GB</td>
                    <td>1-2 GB</td>
                    <td>16-24 GB</td>
                    <td>RTX 3060 이상</td>
                  </tr>
                  <tr>
                    <td><strong>중형</strong></td>
                    <td>7B - 8B</td>
                    <td>14-16 GB</td>
                    <td>8-10 GB</td>
                    <td>4-6 GB</td>
                    <td>80-100 GB</td>
                    <td>RTX 4090 / A100 40GB</td>
                  </tr>
                  <tr>
                    <td><strong>대형</strong></td>
                    <td>13B - 14B</td>
                    <td>26-32 GB</td>
                    <td>14-16 GB</td>
                    <td>8-10 GB</td>
                    <td>160-200 GB</td>
                    <td>A100 80GB × 2</td>
                  </tr>
                  <tr>
                    <td><strong>초대형</strong></td>
                    <td>70B - 72B</td>
                    <td>140-160 GB</td>
                    <td>70-80 GB</td>
                    <td>35-40 GB</td>
                    <td>700+ GB</td>
                    <td>A100 80GB × 8</td>
                  </tr>
                  <tr className="highlight-row">
                    <td><strong>최대</strong></td>
                    <td>405B</td>
                    <td>810 GB</td>
                    <td>405 GB</td>
                    <td>200 GB</td>
                    <td>3+ TB</td>
                    <td>H100 80GB × 16+</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="hw-notes">
              <div className="hw-note-item">
                <Info size={14} />
                <span><strong>FP16:</strong> 파라미터당 2 bytes, 정확도 유지</span>
              </div>
              <div className="hw-note-item">
                <Info size={14} />
                <span><strong>INT8:</strong> 파라미터당 1 byte, 약간의 정확도 손실</span>
              </div>
              <div className="hw-note-item">
                <Info size={14} />
                <span><strong>INT4 (GPTQ/AWQ):</strong> 파라미터당 0.5 bytes, 정확도 손실 있지만 실용적</span>
              </div>
            </div>
          </div>

          {/* VLM - Vision Language Model */}
          <div className="card vlm-section" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Eye size={18} /> VLM (Vision Language Model)</h3>
            </div>

            {/* VLM Overview */}
            <div className="vlm-overview">
              <div className="vlm-intro">
                <h4>VLM이란?</h4>
                <p>Vision Language Model은 <strong>이미지와 텍스트를 함께 이해</strong>하는 멀티모달 AI입니다.
                   LLM의 언어 이해 능력에 시각적 인지 능력을 결합하여, 이미지에 대한 질문에 답하거나
                   이미지를 설명하고, 이미지 기반 추론이 가능합니다.</p>
              </div>

              {/* VLM Architecture Diagram */}
              <div className="vlm-architecture-diagram">
                <h4>VLM 아키텍처</h4>
                <svg viewBox="0 0 800 400" className="vlm-svg">
                  {/* Background */}
                  <defs>
                    <linearGradient id="vlmGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#667eea" stopOpacity="0.2"/>
                      <stop offset="100%" stopColor="#764ba2" stopOpacity="0.2"/>
                    </linearGradient>
                    <linearGradient id="vlmGrad2" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#f093fb" stopOpacity="0.2"/>
                      <stop offset="100%" stopColor="#f5576c" stopOpacity="0.2"/>
                    </linearGradient>
                  </defs>

                  {/* Input Section */}
                  <g className="vlm-input-section">
                    {/* Image Input */}
                    <rect x="20" y="50" width="120" height="120" rx="8" fill="url(#vlmGrad1)" stroke="#667eea" strokeWidth="2"/>
                    <text x="80" y="30" textAnchor="middle" fontSize="12" fill="#667eea" fontWeight="bold">이미지 입력</text>
                    <rect x="35" y="65" width="90" height="60" rx="4" fill="#e8f0fe"/>
                    <text x="80" y="95" textAnchor="middle" fontSize="24">🖼️</text>
                    <text x="80" y="145" textAnchor="middle" fontSize="10" fill="#666">224×224 또는 더 큰 해상도</text>
                    <text x="80" y="160" textAnchor="middle" fontSize="10" fill="#666">RGB 픽셀 데이터</text>

                    {/* Text Input */}
                    <rect x="20" y="230" width="120" height="120" rx="8" fill="url(#vlmGrad2)" stroke="#f5576c" strokeWidth="2"/>
                    <text x="80" y="215" textAnchor="middle" fontSize="12" fill="#f5576c" fontWeight="bold">텍스트 입력</text>
                    <text x="80" y="270" textAnchor="middle" fontSize="10" fill="#333">"이 이미지에서</text>
                    <text x="80" y="285" textAnchor="middle" fontSize="10" fill="#333">무엇이 보이나요?"</text>
                    <rect x="35" y="300" width="90" height="30" rx="4" fill="#fff0f5"/>
                    <text x="80" y="320" textAnchor="middle" fontSize="10" fill="#666">토큰화된 프롬프트</text>
                  </g>

                  {/* Vision Encoder */}
                  <g className="vlm-vision-encoder">
                    <rect x="180" y="50" width="140" height="120" rx="8" fill="#e8f5e9" stroke="#4caf50" strokeWidth="2"/>
                    <text x="250" y="75" textAnchor="middle" fontSize="11" fill="#2e7d32" fontWeight="bold">Vision Encoder</text>
                    <text x="250" y="95" textAnchor="middle" fontSize="10" fill="#666">(ViT, CLIP, SigLIP)</text>

                    {/* Patch Embedding */}
                    <rect x="195" y="105" width="110" height="25" rx="4" fill="#c8e6c9"/>
                    <text x="250" y="122" textAnchor="middle" fontSize="10" fill="#2e7d32">Patch Embedding</text>

                    {/* Transformer Layers */}
                    <rect x="195" y="135" width="110" height="25" rx="4" fill="#a5d6a7"/>
                    <text x="250" y="152" textAnchor="middle" fontSize="10" fill="#1b5e20">Transformer Layers</text>
                  </g>

                  {/* Projection Layer */}
                  <g className="vlm-projection">
                    <rect x="360" y="120" width="100" height="60" rx="8" fill="#fff3e0" stroke="#ff9800" strokeWidth="2"/>
                    <text x="410" y="145" textAnchor="middle" fontSize="10" fill="#e65100" fontWeight="bold">Projection</text>
                    <text x="410" y="160" textAnchor="middle" fontSize="10" fill="#666">MLP / Q-Former</text>
                    <text x="410" y="172" textAnchor="middle" fontSize="10" fill="#999">Visual → Text Space</text>
                  </g>

                  {/* Text Encoder / LLM */}
                  <g className="vlm-llm">
                    <rect x="180" y="230" width="280" height="120" rx="8" fill="#e3f2fd" stroke="#2196f3" strokeWidth="2"/>
                    <text x="320" y="255" textAnchor="middle" fontSize="11" fill="#1565c0" fontWeight="bold">Large Language Model</text>
                    <text x="320" y="272" textAnchor="middle" fontSize="10" fill="#666">(LLaMA, Vicuna, Qwen, etc.)</text>

                    {/* Combined Input */}
                    <rect x="195" y="285" width="120" height="25" rx="4" fill="#bbdefb"/>
                    <text x="255" y="302" textAnchor="middle" fontSize="10" fill="#1565c0">[Visual Tokens]</text>

                    <rect x="325" y="285" width="120" height="25" rx="4" fill="#90caf9"/>
                    <text x="385" y="302" textAnchor="middle" fontSize="10" fill="#0d47a1">[Text Tokens]</text>

                    <rect x="230" y="315" width="140" height="25" rx="4" fill="#64b5f6"/>
                    <text x="300" y="332" textAnchor="middle" fontSize="10" fill="white">Cross-Modal Attention</text>
                  </g>

                  {/* Output */}
                  <g className="vlm-output">
                    <rect x="500" y="230" width="140" height="120" rx="8" fill="#f3e5f5" stroke="#9c27b0" strokeWidth="2"/>
                    <text x="570" y="255" textAnchor="middle" fontSize="11" fill="#7b1fa2" fontWeight="bold">텍스트 출력</text>
                    <rect x="515" y="270" width="110" height="65" rx="4" fill="#f8f0fc"/>
                    <text x="570" y="290" textAnchor="middle" fontSize="10" fill="#333">"이 이미지에는</text>
                    <text x="570" y="305" textAnchor="middle" fontSize="10" fill="#333">고양이가 소파에</text>
                    <text x="570" y="320" textAnchor="middle" fontSize="10" fill="#333">앉아 있습니다."</text>
                  </g>

                  {/* Arrows */}
                  <defs>
                    <marker id="vlmArrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                      <path d="M0,0 L0,6 L9,3 z" fill="#666"/>
                    </marker>
                  </defs>

                  {/* Image to Vision Encoder */}
                  <line x1="140" y1="110" x2="175" y2="110" stroke="#666" strokeWidth="2" markerEnd="url(#vlmArrow)"/>

                  {/* Vision Encoder to Projection */}
                  <line x1="320" y1="110" x2="320" y2="145" stroke="#666" strokeWidth="2"/>
                  <line x1="320" y1="145" x2="355" y2="145" stroke="#666" strokeWidth="2" markerEnd="url(#vlmArrow)"/>

                  {/* Projection to LLM */}
                  <line x1="410" y1="180" x2="410" y2="200" stroke="#666" strokeWidth="2"/>
                  <line x1="410" y1="200" x2="320" y2="200" stroke="#666" strokeWidth="2"/>
                  <line x1="320" y1="200" x2="320" y2="225" stroke="#666" strokeWidth="2" markerEnd="url(#vlmArrow)"/>

                  {/* Text to LLM */}
                  <line x1="140" y1="290" x2="175" y2="290" stroke="#666" strokeWidth="2" markerEnd="url(#vlmArrow)"/>

                  {/* LLM to Output */}
                  <line x1="460" y1="290" x2="495" y2="290" stroke="#666" strokeWidth="2" markerEnd="url(#vlmArrow)"/>

                  {/* Labels */}
                  <text x="695" y="50" fontSize="11" fill="#333" fontWeight="bold">핵심 포인트:</text>
                  <text x="695" y="70" fontSize="10" fill="#666">• Vision Encoder로 이미지 특징 추출</text>
                  <text x="695" y="85" fontSize="10" fill="#666">• Projection으로 시각/언어 공간 정렬</text>
                  <text x="695" y="100" fontSize="10" fill="#666">• LLM이 멀티모달 추론 수행</text>
                  <text x="695" y="115" fontSize="10" fill="#666">• 텍스트로 응답 생성</text>
                </svg>
              </div>
            </div>

            {/* VLM vs LLM Comparison */}
            <div className="vlm-comparison">
              <h4>LLM vs VLM 비교</h4>
              <div className="comparison-table">
                <table>
                  <thead>
                    <tr>
                      <th>특성</th>
                      <th>LLM (텍스트 전용)</th>
                      <th>VLM (멀티모달)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>입력</strong></td>
                      <td>텍스트만</td>
                      <td>이미지 + 텍스트</td>
                    </tr>
                    <tr>
                      <td><strong>출력</strong></td>
                      <td>텍스트</td>
                      <td>텍스트 (일부 모델은 이미지도)</td>
                    </tr>
                    <tr>
                      <td><strong>추가 컴포넌트</strong></td>
                      <td>없음</td>
                      <td>Vision Encoder + Projection Layer</td>
                    </tr>
                    <tr>
                      <td><strong>메모리 사용</strong></td>
                      <td>기준</td>
                      <td>1.2~1.5배 (Vision 모듈 추가)</td>
                    </tr>
                    <tr>
                      <td><strong>추론 속도</strong></td>
                      <td>기준</td>
                      <td>이미지 처리로 인해 느림</td>
                    </tr>
                    <tr>
                      <td><strong>학습 데이터</strong></td>
                      <td>텍스트 코퍼스</td>
                      <td>이미지-텍스트 페어 데이터</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* VLM Strengths and Weaknesses */}
            <div className="vlm-pros-cons">
              <h4>VLM의 강점과 약점</h4>
              <div className="pros-cons-grid">
                <div className="pros-section">
                  <h5><CheckCircle size={16} /> 강점</h5>
                  <ul>
                    <li>
                      <strong>시각적 이해:</strong> 이미지 내용을 자연어로 설명하고
                      세부 사항을 분석할 수 있음
                    </li>
                    <li>
                      <strong>멀티모달 추론:</strong> 이미지와 텍스트를 결합한
                      복합적인 질문에 답변 가능
                    </li>
                    <li>
                      <strong>OCR 능력:</strong> 이미지 내 텍스트를 읽고
                      해석하는 능력이 뛰어남
                    </li>
                    <li>
                      <strong>문맥 이해:</strong> 이미지의 맥락과 상황을
                      이해하고 관련 정보 제공
                    </li>
                    <li>
                      <strong>다양한 응용:</strong> 이미지 캡셔닝, VQA,
                      문서 분석, 의료 이미지 해석 등
                    </li>
                  </ul>
                </div>
                <div className="cons-section">
                  <h5><AlertTriangle size={16} /> 약점</h5>
                  <ul>
                    <li>
                      <strong>환각 (Hallucination):</strong> 이미지에 없는
                      내용을 있다고 답하는 경우가 있음
                    </li>
                    <li>
                      <strong>공간 추론 한계:</strong> 객체 간 정확한 위치 관계나
                      수량을 세는 데 취약
                    </li>
                    <li>
                      <strong>리소스 요구:</strong> Vision Encoder 추가로 인해
                      LLM보다 더 많은 메모리/컴퓨팅 필요
                    </li>
                    <li>
                      <strong>처리 속도:</strong> 이미지 인코딩 단계로 인해
                      순수 텍스트 LLM보다 느림
                    </li>
                    <li>
                      <strong>해상도 제한:</strong> 대부분 고정 해상도로 리사이즈,
                      세밀한 디테일 손실 가능
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Popular VLM Models */}
            <div className="vlm-models">
              <h4>주요 VLM 모델</h4>
              <div className="model-cards">
                <div className="model-card">
                  <div className="model-header">
                    <span className="model-name">LLaVA</span>
                    <span className="model-badge open">오픈소스</span>
                  </div>
                  <div className="model-details">
                    <p>Visual Instruction Tuning으로 학습된 모델</p>
                    <div className="model-specs">
                      <span>Vision: CLIP ViT-L</span>
                      <span>LLM: Vicuna/LLaMA</span>
                      <span>크기: 7B-13B</span>
                    </div>
                  </div>
                </div>
                <div className="model-card">
                  <div className="model-header">
                    <span className="model-name">Qwen-VL</span>
                    <span className="model-badge open">오픈소스</span>
                  </div>
                  <div className="model-details">
                    <p>알리바바의 고성능 멀티모달 모델</p>
                    <div className="model-specs">
                      <span>Vision: ViT-bigG</span>
                      <span>LLM: Qwen</span>
                      <span>크기: 7B-72B</span>
                    </div>
                  </div>
                </div>
                <div className="model-card">
                  <div className="model-header">
                    <span className="model-name">GPT-4V</span>
                    <span className="model-badge commercial">상용</span>
                  </div>
                  <div className="model-details">
                    <p>OpenAI의 최고 성능 비전 모델</p>
                    <div className="model-specs">
                      <span>Vision: 미공개</span>
                      <span>LLM: GPT-4</span>
                      <span>크기: 미공개</span>
                    </div>
                  </div>
                </div>
                <div className="model-card">
                  <div className="model-header">
                    <span className="model-name">Claude 3</span>
                    <span className="model-badge commercial">상용</span>
                  </div>
                  <div className="model-details">
                    <p>Anthropic의 멀티모달 AI 모델</p>
                    <div className="model-specs">
                      <span>Vision: 미공개</span>
                      <span>LLM: Claude</span>
                      <span>크기: 미공개</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* VLM Use Cases */}
            <div className="vlm-usecases">
              <h4>VLM 활용 사례</h4>
              <div className="usecase-grid">
                <div className="usecase-item">
                  <div className="usecase-icon">🔍</div>
                  <h5>이미지 분석</h5>
                  <p>제품 사진 분석, 결함 탐지, 품질 검사</p>
                </div>
                <div className="usecase-item">
                  <div className="usecase-icon">📄</div>
                  <h5>문서 처리</h5>
                  <p>OCR, 양식 추출, 영수증/인보이스 처리</p>
                </div>
                <div className="usecase-item">
                  <div className="usecase-icon">🏥</div>
                  <h5>의료 이미지</h5>
                  <p>X-ray, CT 스캔 분석 보조</p>
                </div>
                <div className="usecase-item">
                  <div className="usecase-icon">♿</div>
                  <h5>접근성</h5>
                  <p>시각장애인을 위한 이미지 설명</p>
                </div>
                <div className="usecase-item">
                  <div className="usecase-icon">🛒</div>
                  <h5>이커머스</h5>
                  <p>제품 태깅, 유사 상품 검색</p>
                </div>
                <div className="usecase-item">
                  <div className="usecase-icon">🎨</div>
                  <h5>크리에이티브</h5>
                  <p>이미지 캡션 생성, 콘텐츠 제작</p>
                </div>
              </div>
            </div>
          </div>

          {/* Current Cluster LLM Status */}
          <div className="card cluster-llm-status" style={{ marginTop: '20px' }}>
            <div className="card-header">
              <h3><Server size={18} /> 현재 클러스터 LLM 상태</h3>
            </div>
            <div className="llm-status-grid">
              <div className="llm-status-item">
                <div className="status-header">
                  <span className="status-icon">🤖</span>
                  <span className="status-title">vLLM Engine</span>
                </div>
                <div className={`status-value ${workloads?.vllm?.status === 'running' ? 'active' : 'inactive'}`}>
                  {workloads?.vllm?.status === 'running' ? '실행중' : '중지됨'}
                </div>
                <div className="status-detail">
                  {vllmConfig.model && <span>Model: {vllmConfig.model.split('/').pop()}</span>}
                </div>
              </div>
              <div className="llm-status-item">
                <div className="status-header">
                  <span className="status-icon">🎮</span>
                  <span className="status-title">GPU 할당</span>
                </div>
                <div className="status-value">{gpuStatus?.total_gpus || 0} GPUs</div>
                <div className="status-detail">
                  <span>사용 가능: {gpuStatus?.available_gpus || 0}</span>
                </div>
              </div>
              <div className="llm-status-item">
                <div className="status-header">
                  <span className="status-icon">📊</span>
                  <span className="status-title">추론 API</span>
                </div>
                <div className={`status-value ${workloads?.vllm?.status === 'running' ? 'active' : 'inactive'}`}>
                  {workloads?.vllm?.status === 'running' ? 'Ready' : 'Offline'}
                </div>
                <div className="status-detail">
                  <code>/v1/chat/completions</code>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Parser Tab - Document Parsing & Web Crawling */}
      {activeTab === 'parser' && (
        <section className="section">
          <div className="section-header">
            <h2 className="section-title">Parser & Crawler</h2>
            <span className="section-subtitle">문서 파싱 및 웹 크롤링 통합 도구</span>
          </div>

          {/* Parser Overview */}
          <div className="card">
            <div className="card-header">
              <h3><FileText size={18} /> 문서 파싱 개요</h3>
            </div>
            <div className="parser-overview">
              <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                다양한 문서 형식을 파싱하고 AI/LLM 애플리케이션을 위해 전처리하는 종합 도구입니다.
                RAG 파이프라인에서 문서를 처리하기 위한 핵심 단계들을 제공합니다.
              </p>

              {/* Processing Pipeline */}
              <div className="pipeline-flow" style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '24px' }}>
                <div className="pipeline-step" style={{ background: 'var(--bg-tertiary)', padding: '12px 20px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>📄</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>1. 파싱</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>문서 → 텍스트</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', color: 'var(--text-secondary)' }}>→</div>
                <div className="pipeline-step" style={{ background: 'var(--bg-tertiary)', padding: '12px 20px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>👁️</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>2. OCR</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>이미지 → 텍스트</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', color: 'var(--text-secondary)' }}>→</div>
                <div className="pipeline-step" style={{ background: 'var(--bg-tertiary)', padding: '12px 20px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>🧹</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>3. 전처리</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>정규화, 클리닝</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', color: 'var(--text-secondary)' }}>→</div>
                <div className="pipeline-step" style={{ background: 'var(--bg-tertiary)', padding: '12px 20px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>✂️</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>4. 청킹</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>텍스트 분할</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', color: 'var(--text-secondary)' }}>→</div>
                <div className="pipeline-step" style={{ background: 'var(--bg-tertiary)', padding: '12px 20px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', marginBottom: '4px' }}>📊</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>5. 평가</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>품질 검증</div>
                </div>
              </div>
            </div>
          </div>

          {/* Parser + VLM 2-Stage Processing */}
          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">
              <h3><Sparkles size={18} /> Parser + VLM 2단계 처리</h3>
            </div>
            <div style={{ padding: '16px' }}>
              <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                1차로 빠른 파서로 문서를 처리하고, 파서가 놓친 복잡한 요소(표, 차트, 수식, 레이아웃)는
                Vision Language Model(VLM)로 2차 처리하여 정확도를 높이는 하이브리드 방식입니다.
              </p>

              {/* 2-Stage Pipeline Diagram */}
              <div style={{
                background: 'linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary))',
                padding: '24px',
                borderRadius: '12px',
                marginBottom: '20px',
                border: '1px solid var(--border-color)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  {/* Input */}
                  <div style={{ textAlign: 'center', padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                    <div style={{ fontSize: '24px', marginBottom: '4px' }}>📄</div>
                    <div style={{ fontSize: '12px', fontWeight: '600' }}>문서 입력</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>PDF, 이미지 등</div>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>→</div>

                  {/* Stage 1: Fast Parser */}
                  <div style={{
                    textAlign: 'center',
                    padding: '16px 20px',
                    background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(59, 130, 246, 0.1))',
                    borderRadius: '8px',
                    border: '2px solid rgba(59, 130, 246, 0.4)'
                  }}>
                    <div style={{ fontSize: '24px', marginBottom: '4px' }}>⚡</div>
                    <div style={{ fontSize: '13px', fontWeight: '700', color: '#3b82f6' }}>1단계: 빠른 파서</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px' }}>PyMuPDF, pdfplumber</div>
                    <div style={{ fontSize: '10px', color: 'var(--accent-green)', marginTop: '2px' }}>~0.1초/페이지</div>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>→</div>

                  {/* Decision Point */}
                  <div style={{
                    textAlign: 'center',
                    padding: '12px 16px',
                    background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.1))',
                    borderRadius: '50%',
                    border: '2px solid rgba(245, 158, 11, 0.4)',
                    width: '80px',
                    height: '80px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <div style={{ fontSize: '20px' }}>🔍</div>
                    <div style={{ fontSize: '10px', fontWeight: '600', color: '#f59e0b' }}>품질 검증</div>
                  </div>

                  {/* Branch to VLM */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>복잡한 요소 감지시</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>↓</div>

                    {/* Stage 2: VLM */}
                    <div style={{
                      textAlign: 'center',
                      padding: '16px 20px',
                      background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(168, 85, 247, 0.1))',
                      borderRadius: '8px',
                      border: '2px solid rgba(168, 85, 247, 0.4)'
                    }}>
                      <div style={{ fontSize: '24px', marginBottom: '4px' }}>🧠</div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: '#a855f7' }}>2단계: VLM 처리</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px' }}>GPT-4V, Claude Vision</div>
                      <div style={{ fontSize: '10px', color: 'var(--accent-yellow)', marginTop: '2px' }}>~2-5초/페이지</div>
                    </div>
                  </div>

                  <div style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>→</div>

                  {/* Output */}
                  <div style={{ textAlign: 'center', padding: '12px 16px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.1))', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    <div style={{ fontSize: '24px', marginBottom: '4px' }}>✅</div>
                    <div style={{ fontSize: '12px', fontWeight: '600', color: '#10b981' }}>정확한 텍스트</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>구조 보존</div>
                  </div>
                </div>
              </div>

              {/* When to use VLM */}
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>🎯 VLM 2차 처리가 필요한 경우</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px' }}>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '18px' }}>📊</span>
                    <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>복잡한 표</span>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '18px' }}>📈</span>
                    <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>차트/그래프</span>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '18px' }}>∑</span>
                    <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>수식/LaTeX</span>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '18px' }}>🖼️</span>
                    <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>다이어그램</span>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '18px' }}>📐</span>
                    <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>복잡한 레이아웃</span>
                  </div>
                  <div style={{ background: 'var(--bg-tertiary)', padding: '10px 14px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '18px' }}>✍️</span>
                    <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>손글씨 OCR</span>
                  </div>
                </div>
              </div>

              {/* Implementation Code */}
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>💻 구현 코드 예시</h4>
                <div style={{
                  background: 'var(--bg-secondary)',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  border: '1px solid var(--border-color)'
                }}>
                  <div style={{
                    background: 'var(--bg-tertiary)',
                    padding: '8px 16px',
                    borderBottom: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)' }}>parser_vlm.py</span>
                    <Copy size={14} style={{ color: 'var(--text-secondary)', cursor: 'pointer' }} />
                  </div>
                  <pre style={{
                    margin: 0,
                    padding: '16px',
                    fontFamily: 'Monaco, Consolas, monospace',
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                    overflowX: 'auto',
                    lineHeight: '1.5'
                  }}>
{`import fitz  # PyMuPDF
import base64
from openai import OpenAI
from dataclasses import dataclass
from typing import List, Optional
import io
from PIL import Image

@dataclass
class PageContent:
    text: str
    images: List[bytes]
    tables: List[dict]
    needs_vlm: bool = False
    vlm_reason: Optional[str] = None

class HybridParser:
    def __init__(self, vlm_client: OpenAI):
        self.client = vlm_client

    def parse_pdf(self, pdf_path: str) -> List[PageContent]:
        """1단계: 빠른 파서로 먼저 처리"""
        doc = fitz.open(pdf_path)
        results = []

        for page_num, page in enumerate(doc):
            content = self._parse_page_fast(page)

            # 품질 검증: VLM 필요 여부 판단
            if self._needs_vlm_processing(content, page):
                content.needs_vlm = True
                content = self._process_with_vlm(page, content)

            results.append(content)

        return results

    def _parse_page_fast(self, page) -> PageContent:
        """PyMuPDF로 빠른 텍스트 추출"""
        text = page.get_text("text")
        images = []
        tables = []

        # 이미지 추출
        for img in page.get_images():
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            images.append(base_image["image"])

        # 테이블 감지 (간단한 휴리스틱)
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if self._looks_like_table(block):
                tables.append(block)

        return PageContent(text=text, images=images, tables=tables)

    def _needs_vlm_processing(self, content: PageContent, page) -> bool:
        """VLM 처리가 필요한지 판단하는 휴리스틱"""
        reasons = []

        # 1. 복잡한 표 감지
        if len(content.tables) > 0:
            for table in content.tables:
                if self._is_complex_table(table):
                    reasons.append("complex_table")
                    break

        # 2. 텍스트 추출 품질 저하 감지
        text_coverage = len(content.text) / max(page.rect.width * page.rect.height * 0.001, 1)
        if text_coverage < 0.3 and len(content.images) > 0:
            reasons.append("low_text_coverage")

        # 3. 수식 패턴 감지
        math_patterns = ['∫', '∑', '√', 'α', 'β', 'γ', '∂', '∞']
        if any(p in content.text for p in math_patterns):
            reasons.append("math_detected")

        # 4. 이미지에 텍스트가 있을 가능성
        if len(content.images) > 2:
            reasons.append("many_images")

        if reasons:
            content.vlm_reason = ", ".join(reasons)
            return True
        return False

    def _process_with_vlm(self, page, content: PageContent) -> PageContent:
        """2단계: VLM으로 정밀 처리"""
        # 페이지를 이미지로 렌더링
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        base64_image = base64.b64encode(img_bytes).decode('utf-8')

        # VLM API 호출
        response = self.client.chat.completions.create(
            model="gpt-4o",  # or claude-3-5-sonnet
            messages=[
                {
                    "role": "system",
                    "content": """You are a document parser. Extract ALL text content
                    from the image, preserving structure. For tables, output as markdown.
                    For math equations, use LaTeX format."""
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this document page:"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }}
                    ]
                }
            ],
            max_tokens=4096
        )

        # VLM 결과로 텍스트 보강
        vlm_text = response.choices[0].message.content
        content.text = self._merge_texts(content.text, vlm_text)

        return content

    def _merge_texts(self, parser_text: str, vlm_text: str) -> str:
        """파서와 VLM 결과 병합 (VLM 우선)"""
        # 간단한 병합: VLM 텍스트 우선 사용
        # 실제로는 더 정교한 병합 로직 필요
        return vlm_text if len(vlm_text) > len(parser_text) * 0.8 else parser_text

# 사용 예시
if __name__ == "__main__":
    client = OpenAI(api_key="your-api-key")
    parser = HybridParser(vlm_client=client)

    results = parser.parse_pdf("document.pdf")
    for i, page in enumerate(results):
        print(f"Page {i+1}:")
        print(f"  VLM used: {page.needs_vlm} ({page.vlm_reason})")
        print(f"  Text length: {len(page.text)}")`}
                  </pre>
                </div>
              </div>

              {/* Comparison Table */}
              <div>
                <h4 style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>📊 처리 방식 비교</h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '13px',
                    background: 'var(--bg-secondary)',
                    borderRadius: '8px',
                    overflow: 'hidden'
                  }}>
                    <thead>
                      <tr style={{ background: 'var(--bg-tertiary)' }}>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>방식</th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>속도</th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>비용</th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>정확도</th>
                        <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>적합한 경우</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                          <span style={{ color: '#3b82f6', fontWeight: '600' }}>Parser Only</span>
                        </td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', color: 'var(--accent-green)' }}>매우 빠름</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', color: 'var(--accent-green)' }}>무료</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', color: 'var(--accent-yellow)' }}>중간</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>텍스트 위주 문서</td>
                      </tr>
                      <tr>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)' }}>
                          <span style={{ color: '#a855f7', fontWeight: '600' }}>VLM Only</span>
                        </td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', color: 'var(--accent-red)' }}>느림</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', color: 'var(--accent-red)' }}>높음</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', color: 'var(--accent-green)' }}>높음</td>
                        <td style={{ padding: '12px', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>복잡한 레이아웃</td>
                      </tr>
                      <tr style={{ background: 'rgba(16, 185, 129, 0.05)' }}>
                        <td style={{ padding: '12px' }}>
                          <span style={{ color: '#10b981', fontWeight: '600' }}>하이브리드 (권장)</span>
                        </td>
                        <td style={{ padding: '12px', color: 'var(--accent-green)' }}>빠름*</td>
                        <td style={{ padding: '12px', color: 'var(--accent-yellow)' }}>최적화</td>
                        <td style={{ padding: '12px', color: 'var(--accent-green)' }}>높음</td>
                        <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>모든 문서 유형</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                  * 하이브리드 방식은 대부분의 페이지를 빠르게 처리하고, VLM이 필요한 페이지만 추가 처리합니다.
                </p>
              </div>
            </div>
          </div>

          {/* Supported Formats */}
          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">
              <h3><FileType size={18} /> 지원 파일 형식</h3>
            </div>
            <div className="formats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px', padding: '16px' }}>
              <div className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📕</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>PDF</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>PyMuPDF + pdfplumber</div>
                </div>
              </div>
              <div className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📘</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Word (.docx)</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>python-docx</div>
                </div>
              </div>
              <div className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📙</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>PowerPoint (.pptx)</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>python-pptx</div>
                </div>
              </div>
              <div className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📗</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Excel (.xlsx)</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>openpyxl + pandas</div>
                </div>
              </div>
              <div className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📄</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>한글 (.hwp/.hwpx)</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>olefile + xml</div>
                </div>
              </div>
              <div className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>🌐</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>HTML</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>BeautifulSoup</div>
                </div>
              </div>
              <div className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>📝</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Markdown</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>markdown-it-py</div>
                </div>
              </div>
              <div className="format-item" style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>🖼️</span>
                <div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>이미지 (OCR)</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>pytesseract/EasyOCR</div>
                </div>
              </div>
            </div>
          </div>

          {/* Crawl4AI Integration */}
          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">
              <h3><Globe size={18} /> Crawl4AI 웹 크롤링</h3>
            </div>
            <div style={{ padding: '16px' }}>
              <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                Crawl4AI는 LLM 친화적인 고성능 웹 크롤러입니다. 웹 페이지를 깔끔한 마크다운으로 변환하고,
                JavaScript 렌더링, 동적 콘텐츠 추출을 지원합니다.
              </p>

              <div className="crawl-features" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
                  <h4 style={{ marginBottom: '8px', color: 'var(--accent-primary)' }}>⚡ 고성능</h4>
                  <ul style={{ fontSize: '14px', color: 'var(--text-secondary)', paddingLeft: '20px' }}>
                    <li>비동기 크롤링으로 빠른 처리</li>
                    <li>병렬 처리 지원</li>
                    <li>효율적인 메모리 사용</li>
                  </ul>
                </div>
                <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
                  <h4 style={{ marginBottom: '8px', color: 'var(--accent-primary)' }}>🤖 LLM 친화적</h4>
                  <ul style={{ fontSize: '14px', color: 'var(--text-secondary)', paddingLeft: '20px' }}>
                    <li>깔끔한 마크다운 출력</li>
                    <li>불필요한 요소 자동 제거</li>
                    <li>구조화된 데이터 추출</li>
                  </ul>
                </div>
                <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
                  <h4 style={{ marginBottom: '8px', color: 'var(--accent-primary)' }}>🎭 JavaScript 렌더링</h4>
                  <ul style={{ fontSize: '14px', color: 'var(--text-secondary)', paddingLeft: '20px' }}>
                    <li>Playwright 기반 헤드리스 브라우저</li>
                    <li>SPA/동적 콘텐츠 지원</li>
                    <li>사용자 상호작용 시뮬레이션</li>
                  </ul>
                </div>
                <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
                  <h4 style={{ marginBottom: '8px', color: 'var(--accent-primary)' }}>📊 구조화 추출</h4>
                  <ul style={{ fontSize: '14px', color: 'var(--text-secondary)', paddingLeft: '20px' }}>
                    <li>CSS 선택자로 특정 요소 추출</li>
                    <li>JSON 스키마 기반 추출</li>
                    <li>LLM 기반 지능형 추출</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Chunking Strategies */}
          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">
              <h3><Layers size={18} /> 청킹 전략</h3>
            </div>
            <div style={{ padding: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px' }}>
                <div style={{ background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(59, 130, 246, 0.05))', padding: '16px', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                  <h4 style={{ color: '#3b82f6', marginBottom: '8px' }}>Fixed Size</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>고정 문자/토큰 수로 분할. 간단하고 예측 가능.</p>
                </div>
                <div style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(16, 185, 129, 0.05))', padding: '16px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                  <h4 style={{ color: '#10b981', marginBottom: '8px' }}>Sentence-based</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>문장 단위로 분할. 의미 보존에 유리.</p>
                </div>
                <div style={{ background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.05))', padding: '16px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                  <h4 style={{ color: '#f59e0b', marginBottom: '8px' }}>Recursive</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>계층적 분할. 구조 유지에 효과적.</p>
                </div>
                <div style={{ background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1), rgba(168, 85, 247, 0.05))', padding: '16px', borderRadius: '8px', border: '1px solid rgba(168, 85, 247, 0.2)' }}>
                  <h4 style={{ color: '#a855f7', marginBottom: '8px' }}>Semantic</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>임베딩 기반 의미 단위 분할. 최고 품질.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Parser Demo */}
          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">
              <h3><Play size={18} /> 파싱 데모</h3>
            </div>
            <div style={{ padding: '16px' }}>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                {/* File Upload Area */}
                <div style={{ flex: '1', minWidth: '300px' }}>
                  <div style={{
                    border: '2px dashed var(--border-color)',
                    borderRadius: '8px',
                    padding: '32px',
                    textAlign: 'center',
                    background: 'var(--bg-tertiary)'
                  }}>
                    <Upload size={48} style={{ color: 'var(--text-secondary)', marginBottom: '12px' }} />
                    <p style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>파일을 드래그하거나 클릭하여 업로드</p>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>PDF, DOCX, PPTX, XLSX, HWP, HTML, MD 지원</p>
                    <input type="file" style={{ display: 'none' }} accept=".pdf,.docx,.pptx,.xlsx,.hwp,.hwpx,.html,.md,.png,.jpg,.jpeg" />
                    <button
                      style={{
                        marginTop: '16px',
                        padding: '8px 24px',
                        background: 'var(--accent-primary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer'
                      }}
                    >
                      파일 선택
                    </button>
                  </div>
                </div>

                {/* URL Crawl Area */}
                <div style={{ flex: '1', minWidth: '300px' }}>
                  <div style={{
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '24px',
                    background: 'var(--bg-tertiary)'
                  }}>
                    <h4 style={{ marginBottom: '16px', color: 'var(--text-primary)' }}>
                      <Globe size={18} style={{ marginRight: '8px' }} />
                      URL 크롤링
                    </h4>
                    <input
                      type="text"
                      placeholder="https://example.com/page"
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                        marginBottom: '12px'
                      }}
                    />
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                      <label style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <input type="checkbox" /> JavaScript 렌더링
                      </label>
                      <label style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <input type="checkbox" /> 이미지 추출
                      </label>
                    </div>
                    <button
                      style={{
                        width: '100%',
                        padding: '10px',
                        background: 'var(--accent-secondary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer'
                      }}
                    >
                      크롤링 시작
                    </button>
                  </div>
                </div>
              </div>

              {/* Result Preview */}
              <div style={{ marginTop: '20px', border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
                <div style={{ background: 'var(--bg-tertiary)', padding: '12px 16px', borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>파싱 결과</span>
                </div>
                <div style={{ padding: '16px', background: 'var(--bg-secondary)', minHeight: '150px' }}>
                  <pre style={{
                    margin: 0,
                    fontFamily: 'Monaco, Consolas, monospace',
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                    whiteSpace: 'pre-wrap'
                  }}>
{`// 파일을 업로드하거나 URL을 입력하면 결과가 여기에 표시됩니다.

예시 출력:
{
  "metadata": {
    "filename": "document.pdf",
    "pages": 10,
    "char_count": 15234
  },
  "chunks": [
    {
      "content": "첫 번째 청크 내용...",
      "metadata": { "page": 1, "chunk_id": 0 }
    },
    ...
  ]
}`}
                  </pre>
                </div>
              </div>
            </div>
          </div>

          {/* Integration with RAG */}
          <div className="card" style={{ marginTop: '16px' }}>
            <div className="card-header">
              <h3><GitBranch size={18} /> RAG 파이프라인 통합</h3>
            </div>
            <div style={{ padding: '16px' }}>
              <div className="rag-pipeline-diagram" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
                <div style={{ textAlign: 'center', padding: '12px 16px', background: 'var(--bg-tertiary)', borderRadius: '8px' }}>
                  <div style={{ fontSize: '20px', marginBottom: '4px' }}>📁</div>
                  <div style={{ fontSize: '13px', fontWeight: '600' }}>문서/URL</div>
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>→</div>
                <div style={{ textAlign: 'center', padding: '12px 16px', background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(59, 130, 246, 0.1))', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                  <div style={{ fontSize: '20px', marginBottom: '4px' }}>⚙️</div>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: '#3b82f6' }}>Parser</div>
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>→</div>
                <div style={{ textAlign: 'center', padding: '12px 16px', background: 'var(--bg-tertiary)', borderRadius: '8px' }}>
                  <div style={{ fontSize: '20px', marginBottom: '4px' }}>✂️</div>
                  <div style={{ fontSize: '13px', fontWeight: '600' }}>Chunker</div>
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>→</div>
                <div style={{ textAlign: 'center', padding: '12px 16px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.1))', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                  <div style={{ fontSize: '20px', marginBottom: '4px' }}>🔢</div>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: '#10b981' }}>Embedder</div>
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>→</div>
                <div style={{ textAlign: 'center', padding: '12px 16px', background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(168, 85, 247, 0.1))', borderRadius: '8px', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                  <div style={{ fontSize: '20px', marginBottom: '4px' }}>💾</div>
                  <div style={{ fontSize: '13px', fontWeight: '600', color: '#a855f7' }}>Vector DB</div>
                </div>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', textAlign: 'center' }}>
                Parser로 추출한 텍스트를 청킹하고 임베딩하여 Qdrant Vector DB에 저장합니다.
                이후 RAG 쿼리 시 관련 청크를 검색하여 LLM 컨텍스트로 활용합니다.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

// BrowserRouter로 App을 감싸는 래퍼 컴포넌트
function AppWrapper() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<App />} />
      </Routes>
    </BrowserRouter>
  );
}

export default AppWrapper;
