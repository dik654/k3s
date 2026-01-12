import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  ArrowRightLeft,
  AlertCircle,
  Link2,
  AlertTriangle,
  CheckCircle,
  GitBranch,
  Bell,
  Archive,
  Brain,
  RefreshCw,
} from 'lucide-react';
import type { PipelineStatus, ClusterEvents, Workloads } from '@/types';

const API_BASE = '/api';

interface PipelinePageProps {
  showToast: (message: string, type?: string) => void;
}

export function PipelinePage({ showToast }: PipelinePageProps) {
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [clusterEvents, setClusterEvents] = useState<ClusterEvents | null>(null);
  const [workloads, setWorkloads] = useState<Workloads>({});
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [pipelineRes, eventsRes, workloadsRes] = await Promise.all([
        axios.get(`${API_BASE}/pipeline/status`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/events`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/workloads/status`).catch(() => ({ data: {} })),
      ]);
      setPipelineStatus(pipelineRes.data);
      setClusterEvents(eventsRes.data);
      setWorkloads(workloadsRes.data || {});
    } catch (error) {
      console.error('Pipeline fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <section className="section">
        <div className="card">
          <div className="loading-container">
            <div className="spinner large"></div>
            <p>파이프라인 정보를 불러오는 중...</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">AI 파이프라인 시각화</h2>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div className="pipeline-health-badge" data-status={pipelineStatus?.pipeline_health || 'partial'}>
            {pipelineStatus?.pipeline_health === 'healthy' ? '모든 컴포넌트 활성' : '일부 컴포넌트 비활성'}
          </div>
          <button className="btn btn-outline btn-sm" onClick={fetchData}>
            <RefreshCw size={14} />
          </button>
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
          {/* 1단계: 로그 소스 */}
          <div className="logging-arch-layer">
            <div className="layer-header">
              <span className="layer-num">1</span>
              <span className="layer-title">로그 소스</span>
              <span className="layer-subtitle">K3s 클러스터 컴포넌트</span>
            </div>
            <div className="layer-components">
              {[
                { icon: '🤖', name: 'vLLM', ns: 'ai-workloads', key: 'vllm' },
                { icon: '🧠', name: 'Embedding', ns: 'ai-workloads', key: 'embedding' },
                { icon: '🔍', name: 'Qdrant', ns: 'ai-workloads', key: 'qdrant' },
                { icon: '🎨', name: 'ComfyUI', ns: 'ai-workloads', key: 'comfyui' },
                { icon: '🕸️', name: 'Neo4j', ns: 'ai-workloads', key: 'neo4j' },
                { icon: '💾', name: 'RustFS', ns: 'rustfs', key: 'rustfs' },
                { icon: '📊', name: 'Dashboard', ns: 'dashboard', key: 'dashboard' },
              ].map(item => (
                <div key={item.key} className="log-source-item">
                  <span className="source-icon">{item.icon}</span>
                  <div className="source-info">
                    <span className="source-name">{item.name}</span>
                    <span className="source-ns">{item.ns}</span>
                  </div>
                  <span className={`source-status ${
                    item.key === 'dashboard' ? 'running' :
                    pipelineStatus?.components?.[item.key]?.status === 'running' ? 'running' : 'stopped'
                  }`}></span>
                </div>
              ))}
            </div>
          </div>

          <div className="logging-arch-arrow">
            <div className="arrow-line"></div>
            <span className="arrow-label">stdout/stderr → /var/log/pods/</span>
          </div>

          {/* 2단계: 수집 계층 */}
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
                    <span className="tier-desc">최근 30일 - 압축 저장</span>
                  </div>
                  <div className="storage-tier">
                    <span className="tier-label">Cold</span>
                    <span className="tier-desc">90일+ - 아카이브</span>
                  </div>
                </div>
              </div>

              {/* Knowledge Base */}
              <div className="output-box knowledge">
                <div className="output-header">
                  <Brain size={16} />
                  <strong>지식 베이스</strong>
                </div>
                <div className="output-content">
                  <div className="kb-item">
                    <span className="kb-icon">🔍</span>
                    <span>Qdrant - 에러 임베딩</span>
                  </div>
                  <div className="kb-item">
                    <span className="kb-icon">🕸️</span>
                    <span>Neo4j - 인과 관계</span>
                  </div>
                  <div className="kb-stat">
                    <span>유사 에러 검색으로 해결 시간 50% 단축</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default PipelinePage;
