import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Brain, Database, Image, Network, Play, Square } from 'lucide-react';
import type { Workloads, ActionLoadingMap, NodeMetrics } from '@/types';

interface WorkloadConfig {
  vllm: {
    model: string;
    gpuCount: number;
    nodeSelector: string;
  };
  qdrant: {
    replicas: number;
    storageSize: number;
  };
  neo4j: {
    useCase: string;
    replicas: number;
    memoryLimit: string;
  };
  comfyui: {
    nodeSelector: string;
  };
}

const defaultConfig: WorkloadConfig = {
  vllm: { model: 'Qwen/Qwen2.5-7B-Instruct', gpuCount: 1, nodeSelector: '' },
  qdrant: { replicas: 1, storageSize: 20 },
  neo4j: { useCase: 'rag', replicas: 1, memoryLimit: '4Gi' },
  comfyui: { nodeSelector: '' },
};

export function AIWorkloadsPage() {
  const [loading, setLoading] = useState(true);
  const [workloads, setWorkloads] = useState<Workloads>({});
  const [actionLoading, setActionLoading] = useState<ActionLoadingMap>({});
  const [nodeMetrics, setNodeMetrics] = useState<NodeMetrics[]>([]);
  const [config, setConfig] = useState<WorkloadConfig>(defaultConfig);

  const fetchData = useCallback(async () => {
    try {
      const [workloadsRes, metricsRes] = await Promise.all([
        axios.get('/api/workloads'),
        axios.get('/api/nodes/metrics'),
      ]);
      setWorkloads(workloadsRes.data || {});
      const metricsData = metricsRes.data?.nodes || metricsRes.data || [];
      setNodeMetrics(Array.isArray(metricsData) ? metricsData : []);
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

  const handleWorkloadAction = async (name: string, action: 'start' | 'stop') => {
    setActionLoading(prev => ({ ...prev, [name]: { loading: true, action } }));
    try {
      await axios.post('/api/workloads/' + name + '/' + action);
      setTimeout(() => {
        fetchData();
        setActionLoading(prev => ({ ...prev, [name]: { loading: false } }));
      }, 2000);
    } catch (error) {
      console.error('Failed to ' + action + ' ' + name + ':', error);
      setActionLoading(prev => ({ ...prev, [name]: { loading: false } }));
    }
  };

  const getStatusText = (status?: string) => {
    if (status === 'running') return '실행중';
    if (status === 'stopped') return '중지됨';
    if (status === 'error') return '오류';
    if (status === 'pending') return '준비중';
    return '미배포';
  };

  const gpuNodes = nodeMetrics.filter(n => (n.gpu_capacity || 0) > 0);

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
          <h2 className="section-title">AI 워크로드</h2>
        </div>

        <div className="workload-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
          {/* vLLM */}
          <div className="workload-card" style={{ borderLeft: '3px solid var(--accent-purple)' }}>
            <div className="workload-header">
              <div className="workload-icon" style={{ background: 'var(--accent-purple)' }}>
                <Brain size={20} color="white" />
              </div>
              <div className="workload-info">
                <span className="workload-name">vLLM</span>
                <span className="workload-desc">LLM 추론 서버</span>
              </div>
              <span className={`status-badge ${workloads.vllm?.status === 'running' ? 'running' : 'stopped'}`}>
                {getStatusText(workloads.vllm?.status)}
              </span>
            </div>
            <div style={{ padding: '12px 16px' }}>
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>모델</label>
                <select
                  value={config.vllm.model}
                  onChange={(e) => setConfig({ ...config, vllm: { ...config.vllm, model: e.target.value } })}
                  disabled={workloads.vllm?.status === 'running'}
                >
                  <optgroup label="Agent/Tool Use 최적화">
                    <option value="Qwen/Qwen2.5-7B-Instruct">Qwen2.5-7B-Instruct (추천)</option>
                    <option value="Qwen/Qwen2.5-14B-Instruct">Qwen2.5-14B-Instruct</option>
                    <option value="Qwen/Qwen2.5-32B-Instruct">Qwen2.5-32B-Instruct</option>
                  </optgroup>
                  <optgroup label="한국어 특화">
                    <option value="yanolja/EEVE-Korean-Instruct-10.8B-v1.0">EEVE-Korean 10.8B</option>
                  </optgroup>
                  <optgroup label="코딩 특화">
                    <option value="Qwen/Qwen2.5-Coder-7B-Instruct">Qwen2.5-Coder-7B</option>
                  </optgroup>
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>GPU 노드</label>
                <select
                  value={config.vllm.nodeSelector}
                  onChange={(e) => setConfig({ ...config, vllm: { ...config.vllm, nodeSelector: e.target.value } })}
                  disabled={workloads.vllm?.status === 'running'}
                >
                  <option value="">자동 선택</option>
                  {gpuNodes.map(node => (
                    <option key={node.name} value={node.name}>
                      {node.name} ({node.gpu_capacity} GPU)
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="workload-actions">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('vllm', 'start')}
                disabled={actionLoading.vllm?.loading || workloads.vllm?.status === 'running'}
              >
                <Play size={14} /> {actionLoading.vllm?.loading && actionLoading.vllm?.action === 'start' ? '시작 중...' : '실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('vllm', 'stop')}
                disabled={actionLoading.vllm?.loading || workloads.vllm?.status !== 'running'}
              >
                <Square size={14} /> {actionLoading.vllm?.loading && actionLoading.vllm?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>
          </div>

          {/* Qdrant */}
          <div className="workload-card" style={{ borderLeft: '3px solid var(--accent-green)' }}>
            <div className="workload-header">
              <div className="workload-icon" style={{ background: 'var(--accent-green)' }}>
                <Database size={20} color="white" />
              </div>
              <div className="workload-info">
                <span className="workload-name">Qdrant</span>
                <span className="workload-desc">Vector Database</span>
              </div>
              <span className={`status-badge ${workloads.qdrant?.status === 'running' ? 'running' : 'stopped'}`}>
                {getStatusText(workloads.qdrant?.status)}
              </span>
            </div>
            <div style={{ padding: '12px 16px' }}>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                고성능 벡터 데이터베이스로 임베딩 저장 및 유사도 검색을 지원합니다.
              </p>
              {workloads.qdrant?.status === 'running' && (
                <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>API Endpoint</p>
                  <code style={{ fontSize: 12, color: 'var(--accent-green)' }}>http://qdrant.14.32.100.220.nip.io</code>
                </div>
              )}
            </div>
            <div className="workload-actions">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('qdrant', 'start')}
                disabled={actionLoading.qdrant?.loading || workloads.qdrant?.status === 'running'}
              >
                <Play size={14} /> {actionLoading.qdrant?.loading && actionLoading.qdrant?.action === 'start' ? '시작 중...' : '실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('qdrant', 'stop')}
                disabled={actionLoading.qdrant?.loading || workloads.qdrant?.status !== 'running'}
              >
                <Square size={14} /> {actionLoading.qdrant?.loading && actionLoading.qdrant?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>
          </div>

          {/* Neo4j */}
          <div className="workload-card" style={{ borderLeft: '3px solid var(--accent-blue)' }}>
            <div className="workload-header">
              <div className="workload-icon" style={{ background: 'var(--accent-blue)' }}>
                <Network size={20} color="white" />
              </div>
              <div className="workload-info">
                <span className="workload-name">Neo4j</span>
                <span className="workload-desc">Graph Database</span>
              </div>
              <span className={`status-badge ${workloads.neo4j?.status === 'running' ? 'running' : 'stopped'}`}>
                {getStatusText(workloads.neo4j?.status)}
              </span>
            </div>
            <div style={{ padding: '12px 16px' }}>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                그래프 데이터베이스로 지식 그래프 및 관계 기반 데이터를 관리합니다.
              </p>
              {workloads.neo4j?.status === 'running' && (
                <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Browser</p>
                  <code style={{ fontSize: 12, color: 'var(--accent-blue)' }}>http://neo4j.14.32.100.220.nip.io</code>
                </div>
              )}
            </div>
            <div className="workload-actions">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('neo4j', 'start')}
                disabled={actionLoading.neo4j?.loading || workloads.neo4j?.status === 'running'}
              >
                <Play size={14} /> {actionLoading.neo4j?.loading && actionLoading.neo4j?.action === 'start' ? '시작 중...' : '실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('neo4j', 'stop')}
                disabled={actionLoading.neo4j?.loading || workloads.neo4j?.status !== 'running'}
              >
                <Square size={14} /> {actionLoading.neo4j?.loading && actionLoading.neo4j?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>
          </div>

          {/* ComfyUI */}
          <div className="workload-card" style={{ borderLeft: '3px solid var(--accent-yellow)' }}>
            <div className="workload-header">
              <div className="workload-icon" style={{ background: 'var(--accent-yellow)' }}>
                <Image size={20} color="white" />
              </div>
              <div className="workload-info">
                <span className="workload-name">ComfyUI</span>
                <span className="workload-desc">Image Generation</span>
              </div>
              <span className={`status-badge ${workloads.comfyui?.status === 'running' ? 'running' : 'stopped'}`}>
                {getStatusText(workloads.comfyui?.status)}
              </span>
            </div>
            <div style={{ padding: '12px 16px' }}>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                노드 기반 이미지 생성 워크플로우 도구입니다. Stable Diffusion을 지원합니다.
              </p>
              {workloads.comfyui?.status === 'running' && (
                <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8 }}>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>WebUI</p>
                  <code style={{ fontSize: 12, color: 'var(--accent-yellow)' }}>http://comfyui.14.32.100.220.nip.io</code>
                </div>
              )}
            </div>
            <div className="workload-actions">
              <button
                className="btn btn-success"
                onClick={() => handleWorkloadAction('comfyui', 'start')}
                disabled={actionLoading.comfyui?.loading || workloads.comfyui?.status === 'running'}
              >
                <Play size={14} /> {actionLoading.comfyui?.loading && actionLoading.comfyui?.action === 'start' ? '시작 중...' : '실행'}
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleWorkloadAction('comfyui', 'stop')}
                disabled={actionLoading.comfyui?.loading || workloads.comfyui?.status !== 'running'}
              >
                <Square size={14} /> {actionLoading.comfyui?.loading && actionLoading.comfyui?.action === 'stop' ? '중지 중...' : '중지'}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default AIWorkloadsPage;
