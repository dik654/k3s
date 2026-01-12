import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Zap, RefreshCw, Thermometer } from 'lucide-react';

interface GpuInfo {
  index: number;
  name: string;
  node?: string;
  utilization: number;
  memory_used: number;
  memory_total: number;
  temperature: number;
  power_draw?: number;
  power_limit?: number;
}

interface GpuStatus {
  total_gpus: number;
  available_gpus: number;
  gpu_nodes?: Array<{
    node: string;
    gpu_type: string;
    gpu_count: number;
    status: string;
  }>;
}

interface GpuDetailed {
  available: boolean;
  gpu_count?: number;
  gpus?: GpuInfo[];
}

// GPU Card Component
const GpuCard = ({ gpu }: { gpu: GpuInfo }) => {
  const memPercent = gpu.memory_total > 0 ? (gpu.memory_used / gpu.memory_total) * 100 : 0;
  const powerPercent = gpu.power_limit && gpu.power_limit > 0 ? ((gpu.power_draw || 0) / gpu.power_limit) * 100 : 0;
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
        {gpu.power_draw !== undefined && gpu.power_limit !== undefined && (
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
        )}
      </div>
    </div>
  );
};

export function GpuPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [gpuStatus, setGpuStatus] = useState<GpuStatus | null>(null);
  const [gpuDetailed, setGpuDetailed] = useState<GpuDetailed | null>(null);

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const statusRes = await axios.get('/api/gpu/status');
      setGpuStatus(statusRes.data);

      if (statusRes.data?.total_gpus > 0) {
        try {
          const detailedRes = await axios.get('/api/gpu/detailed');
          setGpuDetailed(detailedRes.data);
        } catch {
          setGpuDetailed(null);
        }
      }
    } catch (error) {
      console.error('Failed to fetch GPU data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(), 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '50vh' }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">
          <Zap size={20} style={{ marginRight: 8 }} />
          GPU 모니터링
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ color: 'var(--text-muted)' }}>총 {gpuStatus?.total_gpus || 0}개 GPU</span>
          <button
            className={`btn-icon ${refreshing ? 'spinning' : ''}`}
            onClick={() => fetchData(true)}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {gpuDetailed?.available && (gpuDetailed.gpus?.length || 0) > 0 ? (
        <div className="nvtop-container">
          <div className="nvtop-header">
            <div className="nvtop-title">
              <Zap size={16} />
              NVIDIA GPU Monitor
            </div>
            <span style={{ fontSize: 11, color: '#888' }}>
              {new Date().toLocaleTimeString()}
            </span>
          </div>
          <div className="nvtop-gpu-list">
            {(gpuDetailed.gpus || []).map((gpu) => (
              <GpuCard key={gpu.index} gpu={gpu} />
            ))}
          </div>
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
    </section>
  );
}

export default GpuPage;
