import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  Activity,
  FileText,
  Gauge,
  RefreshCw,
  Download,
  Play,
  Square,
  Trash2,
  Clock,
  AlertCircle,
  CheckCircle,
  Info
} from 'lucide-react';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardContent, Button, Badge, Select } from '@/components/ui';
import clsx from 'clsx';

type TabType = 'logs' | 'benchmark';

interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  source: string;
  message: string;
}

interface BenchmarkResult {
  id: string;
  model: string;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  latencyMs: number;
  tokensPerSecond: number;
  timestamp: string;
  status: 'success' | 'error';
}

export function MonitoringPage() {
  const [activeTab, setActiveTab] = useState<TabType>('logs');
  const [refreshing, setRefreshing] = useState(false);

  // Log state
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logFilter, setLogFilter] = useState<string>('all');
  const [logSource, setLogSource] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Benchmark state
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkResult[]>([]);
  const [benchmarkRunning, setBenchmarkRunning] = useState(false);
  const [benchmarkConfig, setBenchmarkConfig] = useState({
    model: 'vllm',
    concurrency: 1,
    iterations: 10,
  });

  const fetchLogs = useCallback(async () => {
    try {
      const response = await axios.get('/api/logs', {
        params: {
          level: logFilter !== 'all' ? logFilter : undefined,
          source: logSource !== 'all' ? logSource : undefined,
          limit: 500,
        },
      });
      setLogs(response.data || []);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
      // Mock data for demo
      setLogs([
        { timestamp: new Date().toISOString(), level: 'info', source: 'vllm', message: 'Model loaded successfully' },
        { timestamp: new Date().toISOString(), level: 'info', source: 'qdrant', message: 'Collection created: documents' },
        { timestamp: new Date().toISOString(), level: 'warn', source: 'neo4j', message: 'High memory usage detected' },
        { timestamp: new Date().toISOString(), level: 'error', source: 'comfyui', message: 'Failed to load checkpoint' },
        { timestamp: new Date().toISOString(), level: 'debug', source: 'k3s', message: 'Pod scheduling completed' },
      ]);
    }
  }, [logFilter, logSource]);

  const fetchBenchmarkResults = useCallback(async () => {
    try {
      const response = await axios.get('/api/benchmark/results');
      setBenchmarkResults(response.data || []);
    } catch (error) {
      console.error('Failed to fetch benchmark results:', error);
    }
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    if (activeTab === 'logs') {
      await fetchLogs();
    } else {
      await fetchBenchmarkResults();
    }
    setRefreshing(false);
  };

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
      const interval = setInterval(fetchLogs, 5000);
      return () => clearInterval(interval);
    } else {
      fetchBenchmarkResults();
    }
  }, [activeTab, fetchLogs, fetchBenchmarkResults]);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const runBenchmark = async () => {
    setBenchmarkRunning(true);
    try {
      await axios.post('/api/benchmark/run', benchmarkConfig);
      // Poll for results
      const pollInterval = setInterval(async () => {
        const response = await axios.get('/api/benchmark/status');
        if (response.data.status === 'completed') {
          clearInterval(pollInterval);
          setBenchmarkRunning(false);
          fetchBenchmarkResults();
        }
      }, 2000);
    } catch (error) {
      console.error('Failed to run benchmark:', error);
      setBenchmarkRunning(false);
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const downloadLogs = () => {
    const content = logs.map(log =>
      `[${log.timestamp}] [${log.level.toUpperCase()}] [${log.source}] ${log.message}`
    ).join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs-${new Date().toISOString()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'error': return <AlertCircle size={14} className="text-red-400" />;
      case 'warn': return <AlertCircle size={14} className="text-yellow-400" />;
      case 'info': return <Info size={14} className="text-blue-400" />;
      case 'debug': return <CheckCircle size={14} className="text-slate-400" />;
      default: return <Info size={14} className="text-slate-400" />;
    }
  };

  const getLevelClass = (level: string) => {
    switch (level) {
      case 'error': return 'text-red-400';
      case 'warn': return 'text-yellow-400';
      case 'info': return 'text-blue-400';
      case 'debug': return 'text-slate-500';
      default: return 'text-slate-400';
    }
  };

  const tabs = [
    { id: 'logs' as TabType, label: '로그', icon: <FileText size={16} /> },
    { id: 'benchmark' as TabType, label: '벤치마크', icon: <Gauge size={16} /> },
  ];

  return (
    <div className="min-h-screen bg-slate-950">
      <Header
        title="모니터링"
        onRefresh={handleRefresh}
        isRefreshing={refreshing}
      />

      <div className="p-6">
        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {tabs.map(tab => (
            <Button
              key={tab.id}
              variant={activeTab === tab.id ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setActiveTab(tab.id)}
              leftIcon={tab.icon}
            >
              {tab.label}
            </Button>
          ))}
        </div>

        {/* Logs Tab */}
        {activeTab === 'logs' && (
          <div className="space-y-4">
            {/* Log Controls */}
            <Card>
              <CardContent className="py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <Select
                      label=""
                      value={logFilter}
                      onChange={(e) => setLogFilter(e.target.value)}
                      className="w-32"
                    >
                      <option value="all">모든 레벨</option>
                      <option value="error">Error</option>
                      <option value="warn">Warning</option>
                      <option value="info">Info</option>
                      <option value="debug">Debug</option>
                    </Select>
                    <Select
                      label=""
                      value={logSource}
                      onChange={(e) => setLogSource(e.target.value)}
                      className="w-32"
                    >
                      <option value="all">모든 소스</option>
                      <option value="vllm">vLLM</option>
                      <option value="qdrant">Qdrant</option>
                      <option value="neo4j">Neo4j</option>
                      <option value="comfyui">ComfyUI</option>
                      <option value="k3s">K3s</option>
                    </Select>
                    <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoScroll}
                        onChange={(e) => setAutoScroll(e.target.checked)}
                        className="rounded bg-slate-700 border-slate-600"
                      />
                      자동 스크롤
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={downloadLogs}
                      leftIcon={<Download size={14} />}
                    >
                      다운로드
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={clearLogs}
                      leftIcon={<Trash2 size={14} />}
                    >
                      지우기
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Log Viewer */}
            <Card className="h-[calc(100vh-300px)]">
              <div
                ref={logContainerRef}
                className="h-full overflow-y-auto font-mono text-sm p-4 space-y-1"
              >
                {logs.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-500">
                    <div className="text-center">
                      <FileText size={48} className="mx-auto mb-4 opacity-50" />
                      <p>로그가 없습니다</p>
                    </div>
                  </div>
                ) : (
                  logs.map((log, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2 py-1 hover:bg-slate-800/50 px-2 rounded"
                    >
                      <span className="text-slate-600 shrink-0">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      {getLevelIcon(log.level)}
                      <Badge
                        size="sm"
                        variant={
                          log.level === 'error' ? 'error' :
                          log.level === 'warn' ? 'warning' : 'default'
                        }
                        className="shrink-0"
                      >
                        {log.source}
                      </Badge>
                      <span className={getLevelClass(log.level)}>
                        {log.message}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        )}

        {/* Benchmark Tab */}
        {activeTab === 'benchmark' && (
          <div className="grid grid-cols-3 gap-6">
            {/* Benchmark Config */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Gauge size={18} className="text-blue-400" />
                  <h3 className="font-semibold text-white">벤치마크 설정</h3>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select
                  label="대상 모델"
                  value={benchmarkConfig.model}
                  onChange={(e) => setBenchmarkConfig({
                    ...benchmarkConfig,
                    model: e.target.value
                  })}
                  disabled={benchmarkRunning}
                >
                  <option value="vllm">vLLM (LLM)</option>
                  <option value="qdrant">Qdrant (Vector Search)</option>
                </Select>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">동시 요청 수</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={benchmarkConfig.concurrency}
                    onChange={(e) => setBenchmarkConfig({
                      ...benchmarkConfig,
                      concurrency: parseInt(e.target.value) || 1
                    })}
                    disabled={benchmarkRunning}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">반복 횟수</label>
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    value={benchmarkConfig.iterations}
                    onChange={(e) => setBenchmarkConfig({
                      ...benchmarkConfig,
                      iterations: parseInt(e.target.value) || 10
                    })}
                    disabled={benchmarkRunning}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="pt-4">
                  <Button
                    variant={benchmarkRunning ? 'danger' : 'success'}
                    className="w-full"
                    onClick={benchmarkRunning ? undefined : runBenchmark}
                    isLoading={benchmarkRunning}
                    leftIcon={benchmarkRunning ? <Square size={16} /> : <Play size={16} />}
                  >
                    {benchmarkRunning ? '실행 중...' : '벤치마크 실행'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Results */}
            <div className="col-span-2">
              <Card className="h-full">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Activity size={18} className="text-green-400" />
                      <h3 className="font-semibold text-white">벤치마크 결과</h3>
                    </div>
                    <Badge variant="info">{benchmarkResults.length} 결과</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  {benchmarkResults.length === 0 ? (
                    <div className="flex items-center justify-center h-64 text-slate-500">
                      <div className="text-center">
                        <Gauge size={48} className="mx-auto mb-4 opacity-50" />
                        <p>벤치마크 결과가 없습니다</p>
                        <p className="text-sm mt-2">벤치마크를 실행하여 성능을 측정하세요</p>
                      </div>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-700">
                            <th className="text-left py-2 px-3 text-slate-400 font-medium">시간</th>
                            <th className="text-left py-2 px-3 text-slate-400 font-medium">모델</th>
                            <th className="text-right py-2 px-3 text-slate-400 font-medium">지연시간</th>
                            <th className="text-right py-2 px-3 text-slate-400 font-medium">토큰/초</th>
                            <th className="text-right py-2 px-3 text-slate-400 font-medium">총 토큰</th>
                            <th className="text-center py-2 px-3 text-slate-400 font-medium">상태</th>
                          </tr>
                        </thead>
                        <tbody>
                          {benchmarkResults.map((result) => (
                            <tr
                              key={result.id}
                              className="border-b border-slate-700/50 hover:bg-slate-800/50"
                            >
                              <td className="py-2 px-3 text-slate-500">
                                <div className="flex items-center gap-1">
                                  <Clock size={12} />
                                  {new Date(result.timestamp).toLocaleTimeString()}
                                </div>
                              </td>
                              <td className="py-2 px-3 text-white">{result.model}</td>
                              <td className="py-2 px-3 text-right text-slate-300">
                                {result.latencyMs.toFixed(0)} ms
                              </td>
                              <td className="py-2 px-3 text-right">
                                <span className={clsx(
                                  'font-medium',
                                  result.tokensPerSecond >= 50 ? 'text-green-400' :
                                  result.tokensPerSecond >= 20 ? 'text-yellow-400' :
                                  'text-red-400'
                                )}>
                                  {result.tokensPerSecond.toFixed(1)}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-right text-slate-300">
                                {result.totalTokens}
                              </td>
                              <td className="py-2 px-3 text-center">
                                <Badge
                                  variant={result.status === 'success' ? 'success' : 'error'}
                                  size="sm"
                                >
                                  {result.status === 'success' ? '성공' : '실패'}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MonitoringPage;
