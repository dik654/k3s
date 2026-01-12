import { useState } from 'react';
import {
  Server, Cpu, MemoryStick, MonitorDot, Package, Plus,
  RefreshCw, Crown, PauseCircle, PlayCircle, ArrowRightLeft,
  Trash2, X, AlertCircle, Copy, Loader2
} from 'lucide-react';
import {
  useCluster, useNodeDetail, useNodeActions, useJoinCommand,
  type ClusterNode
} from './hooks/useCluster';

interface ClusterPageProps {
  showToast: (msg: string, type?: string) => void;
}

// 메모리 포맷
const formatMemory = (memStr: string): string => {
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

export function ClusterPage({ showToast }: ClusterPageProps) {
  const { nodes, clusterResources, loading, refresh } = useCluster(showToast);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [showJoinModal, setShowJoinModal] = useState(false);

  const nodeDetail = useNodeDetail(selectedNode, showToast);
  const { actionLoading, handleNodeAction } = useNodeActions(showToast, refresh);
  const { joinCommand, fetchJoinCommand } = useJoinCommand(showToast);

  const handleOpenJoinModal = () => {
    fetchJoinCommand();
    setShowJoinModal(true);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    showToast('명령어가 복사되었습니다');
  };

  if (loading) {
    return (
      <section className="section">
        <div className="loading-container">
          <Loader2 className="spin" size={32} />
          <span>클러스터 정보 로딩 중...</span>
        </div>
      </section>
    );
  }

  return (
    <section className="section cluster-section">
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
        <button className="btn btn-primary" onClick={handleOpenJoinModal}>
          <Plus size={16} />
          노드 추가
        </button>
      </div>

      <div className="cluster-content">
        {/* 노드 목록 */}
        <div className="nodes-panel">
          <div className="panel-header">
            <h3><Server size={18} /> 클러스터 노드</h3>
            <button className="btn-icon" onClick={refresh} title="새로고침">
              <RefreshCw size={14} />
            </button>
          </div>

          <div className="nodes-list">
            {nodes.map((node: ClusterNode) => (
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
                        disabled={!!actionLoading[node.name]}
                        title="스케줄링 비활성화"
                      >
                        <PauseCircle size={12} />
                        Cordon
                      </button>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={(e) => { e.stopPropagation(); handleNodeAction(node.name, 'uncordon'); }}
                        disabled={!!actionLoading[node.name]}
                        title="스케줄링 활성화"
                      >
                        <PlayCircle size={12} />
                        Uncordon
                      </button>
                      <button
                        className="btn btn-sm btn-warning"
                        onClick={(e) => { e.stopPropagation(); handleNodeAction(node.name, 'drain'); }}
                        disabled={!!actionLoading[node.name]}
                        title="Pod 퇴거"
                      >
                        <ArrowRightLeft size={12} />
                        Drain
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={(e) => { e.stopPropagation(); handleNodeAction(node.name, 'delete'); }}
                        disabled={!!actionLoading[node.name]}
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
                    {(nodeDetail.pods?.length || 0) > 15 && (
                      <div className="pods-more">+{(nodeDetail.pods?.length || 0) - 15}개 더</div>
                    )}
                  </div>
                </div>

                {/* 레이블 */}
                <div className="detail-section">
                  <h4>레이블</h4>
                  <div className="labels-list">
                    {Object.entries(nodeDetail.labels || {}).slice(0, 10).map(([key, value]) => (
                      <span key={key} className="label-tag">
                        {key.length > 30 ? '...' + key.slice(-27) : key}={String(value).length > 20 ? String(value).slice(0, 17) + '...' : value}
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
          <div className="modal join-modal" onClick={e => e.stopPropagation()}>
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
                    onClick={() => copyToClipboard(joinCommand.instructions?.worker || '')}
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
                    onClick={() => copyToClipboard(joinCommand.instructions?.master || '')}
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
    </section>
  );
}

export default ClusterPage;
