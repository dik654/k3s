import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  BarChart3,
  RefreshCw,
  Zap,
  Plus,
  Settings,
  TrendingUp,
  Clock,
  Cpu,
  PlayCircle,
  Trash2,
  Loader2,
  Timer,
  Target,
  AlertCircle,
  CheckCircle,
  X,
} from 'lucide-react';

const API_BASE = '/api';

// Types
interface BenchmarkConfig {
  id: string;
  name: string;
  model: string;
  max_tokens: number;
  temperature: number;
  top_p: number;
  num_requests: number;
  concurrent_requests: number;
  test_prompts: string[];
  gpu_memory_utilization?: number | null;
  quantization?: string | null;
  tensor_parallel_size?: number | null;
  max_model_len?: number | null;
  dtype?: string | null;
  enforce_eager?: boolean;
}

interface BenchmarkSummary {
  total_requests: number;
  success_rate: number;
  avg_latency: number;
  min_latency: number;
  max_latency: number;
  p50_latency: number;
  p95_latency?: number;
  avg_tokens_per_second: number;
  total_output_tokens: number;
}

interface BenchmarkRequest {
  prompt: string;
  latency: number;
  output_tokens: number;
  tokens_per_second: number;
  success: boolean;
}

interface BenchmarkResult {
  id: string;
  config_id: string;
  config_name: string;
  model: string;
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  summary?: BenchmarkSummary;
  settings?: {
    max_tokens: number;
    temperature: number;
    concurrent_requests: number;
  };
  requests?: BenchmarkRequest[];
  error?: string;
}

interface VllmStatus {
  healthy: boolean;
  message: string;
  models?: string[];
}

interface AutoRangeSession {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  total_tests: number;
  completed_tests: number;
  best_params?: {
    max_tokens: number;
    concurrent_requests: number;
  };
  best_performance?: {
    avg_tokens_per_second: number;
  };
  results?: Array<{
    params: {
      test_type: string;
      max_tokens: number;
      concurrent_requests: number;
      temperature?: number;
    };
    summary?: BenchmarkSummary;
  }>;
}

interface BenchmarkPageProps {
  showToast: (message: string, type?: string) => void;
}

export function BenchmarkPage({ showToast }: BenchmarkPageProps) {
  const [configs, setConfigs] = useState<BenchmarkConfig[]>([]);
  const [results, setResults] = useState<BenchmarkResult[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<BenchmarkConfig | null>(null);
  const [selectedResult, setSelectedResult] = useState<BenchmarkResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [showCreateConfig, setShowCreateConfig] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [showAutoRange, setShowAutoRange] = useState(false);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [vllmStatus, setVllmStatus] = useState<VllmStatus | null>(null);
  const [autoRangeSessions, setAutoRangeSessions] = useState<AutoRangeSession[]>([]);
  const [selectedAutoSession, setSelectedAutoSession] = useState<AutoRangeSession | null>(null);
  const [newConfig, setNewConfig] = useState<Partial<BenchmarkConfig>>({
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
    max_tokens_range: [32, 512, 128] as [number, number, number] | null,
    concurrent_range: [1, 8, 2] as [number, number, number] | null,
    temperature_range: null as [number, number, number] | null,
    gpu_memory_utilization: null as number | null,
    quantization: null as string | null,
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
    } catch {
      setVllmStatus({ status: 'error', message: '상태 확인 실패', healthy: false } as unknown as VllmStatus);
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
    fetchVllmStatus();
  }, [fetchVllmStatus]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 설정 생성
  const handleCreateConfig = async () => {
    if (!newConfig.name?.trim()) {
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
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      showToast(axiosError.response?.data?.detail || '설정 생성 실패', 'error');
    }
  };

  // 벤치마크 실행
  const handleRunBenchmark = async (configId: string) => {
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
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      showToast(axiosError.response?.data?.detail || '벤치마크 실행 실패', 'error');
    } finally {
      setRunning(false);
    }
  };

  // 결과 상세 조회
  const handleViewResult = async (resultId: string) => {
    try {
      const res = await axios.get(`${API_BASE}/benchmark/results/${resultId}`);
      setSelectedResult(res.data);
    } catch {
      showToast('결과 조회 실패', 'error');
    }
  };

  // 설정 삭제
  const handleDeleteConfig = async (configId: string) => {
    try {
      await axios.delete(`${API_BASE}/benchmark/configs/${configId}`);
      showToast('설정이 삭제되었습니다');
      fetchData();
    } catch {
      showToast('설정 삭제 실패', 'error');
    }
  };

  // 결과 삭제
  const handleDeleteResult = async (resultId: string) => {
    try {
      await axios.delete(`${API_BASE}/benchmark/results/${resultId}`);
      showToast('결과가 삭제되었습니다');
      if (selectedResult?.id === resultId) {
        setSelectedResult(null);
      }
      fetchData();
    } catch {
      showToast('결과 삭제 실패', 'error');
    }
  };

  // 프롬프트 추가
  const handleAddPrompt = () => {
    if (newPrompt.trim()) {
      setNewConfig({
        ...newConfig,
        test_prompts: [...(newConfig.test_prompts || []), newPrompt.trim()]
      });
      setNewPrompt('');
    }
  };

  // 프롬프트 삭제
  const handleRemovePrompt = (index: number) => {
    setNewConfig({
      ...newConfig,
      test_prompts: (newConfig.test_prompts || []).filter((_, i) => i !== index)
    });
  };

  // 비교 토글
  const toggleCompare = (resultId: string) => {
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
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      showToast(axiosError.response?.data?.detail || '자동 범위 벤치마크 시작 실패', 'error');
    }
  };

  // 자동 범위 세션 상세 조회
  const handleViewAutoSession = async (sessionId: string) => {
    try {
      const res = await axios.get(`${API_BASE}/benchmark/auto-range/${sessionId}`);
      setSelectedAutoSession(res.data);
    } catch {
      showToast('세션 조회 실패', 'error');
    }
  };

  // 자동 범위 세션 삭제
  const handleDeleteAutoSession = async (sessionId: string) => {
    try {
      await axios.delete(`${API_BASE}/benchmark/auto-range/${sessionId}`);
      showToast('세션이 삭제되었습니다');
      if (selectedAutoSession?.id === sessionId) {
        setSelectedAutoSession(null);
      }
      fetchData();
    } catch {
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
                    value={newConfig.name || ''}
                    onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
                    placeholder="My Benchmark"
                  />
                </div>
                <div className="form-group">
                  <label>모델</label>
                  <input
                    type="text"
                    value={newConfig.model || ''}
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
                    value={newConfig.max_tokens || 100}
                    onChange={(e) => setNewConfig({ ...newConfig, max_tokens: parseInt(e.target.value) || 100 })}
                  />
                </div>
                <div className="form-group">
                  <label>Temperature</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newConfig.temperature || 0.7}
                    onChange={(e) => setNewConfig({ ...newConfig, temperature: parseFloat(e.target.value) || 0.7 })}
                  />
                </div>
                <div className="form-group">
                  <label>Top P</label>
                  <input
                    type="number"
                    step="0.05"
                    value={newConfig.top_p || 0.9}
                    onChange={(e) => setNewConfig({ ...newConfig, top_p: parseFloat(e.target.value) || 0.9 })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>요청 수</label>
                  <input
                    type="number"
                    value={newConfig.num_requests || 10}
                    onChange={(e) => setNewConfig({ ...newConfig, num_requests: parseInt(e.target.value) || 10 })}
                  />
                </div>
                <div className="form-group">
                  <label>동시 요청 수</label>
                  <input
                    type="number"
                    value={newConfig.concurrent_requests || 1}
                    onChange={(e) => setNewConfig({ ...newConfig, concurrent_requests: parseInt(e.target.value) || 1 })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>테스트 프롬프트</label>
                <div className="prompts-list">
                  {(newConfig.test_prompts || []).map((prompt, idx) => (
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
                            max_tokens_range: [parseInt(e.target.value) || 32, autoRangeConfig.max_tokens_range![1], autoRangeConfig.max_tokens_range![2]]
                          })}
                          placeholder="최소"
                        />
                        <span>~</span>
                        <input
                          type="number"
                          value={autoRangeConfig.max_tokens_range[1]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            max_tokens_range: [autoRangeConfig.max_tokens_range![0], parseInt(e.target.value) || 512, autoRangeConfig.max_tokens_range![2]]
                          })}
                          placeholder="최대"
                        />
                        <span>step:</span>
                        <input
                          type="number"
                          value={autoRangeConfig.max_tokens_range[2]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            max_tokens_range: [autoRangeConfig.max_tokens_range![0], autoRangeConfig.max_tokens_range![1], parseInt(e.target.value) || 64]
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
                            concurrent_range: [parseInt(e.target.value) || 1, autoRangeConfig.concurrent_range![1], autoRangeConfig.concurrent_range![2]]
                          })}
                          placeholder="최소"
                        />
                        <span>~</span>
                        <input
                          type="number"
                          value={autoRangeConfig.concurrent_range[1]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            concurrent_range: [autoRangeConfig.concurrent_range![0], parseInt(e.target.value) || 8, autoRangeConfig.concurrent_range![2]]
                          })}
                          placeholder="최대"
                        />
                        <span>step:</span>
                        <input
                          type="number"
                          value={autoRangeConfig.concurrent_range[2]}
                          onChange={(e) => setAutoRangeConfig({
                            ...autoRangeConfig,
                            concurrent_range: [autoRangeConfig.concurrent_range![0], autoRangeConfig.concurrent_range![1], parseInt(e.target.value) || 1]
                          })}
                          placeholder="증가폭"
                        />
                      </div>
                    )}
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
}

export default BenchmarkPage;
