import { Thermometer } from 'lucide-react';
import type { GpuInfo } from '@/types';

export interface GpuCardProps {
  gpu: GpuInfo;
}

export function GpuCard({ gpu }: GpuCardProps) {
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
}

export default GpuCard;
