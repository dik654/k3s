import { useState } from 'react';
import { Thermometer, Zap, Server, ChevronDown, Info } from 'lucide-react';
import { Badge, ProgressBar } from '@/components/ui';
import clsx from 'clsx';
import type { GpuStatus, GpuDetailed, GpuInfo, NodeMetrics } from '@/types';

interface GpuMonitorProps {
  gpuStatus: GpuStatus | null;
  gpuDetailed: GpuDetailed | null;
  nodeMetrics: NodeMetrics[];
}

function GpuCard({ gpu }: { gpu: GpuInfo }) {
  const memPercent = gpu.memory_total > 0 ? (gpu.memory_used / gpu.memory_total) * 100 : 0;
  const powerPercent = gpu.power_limit > 0 ? (gpu.power_draw / gpu.power_limit) * 100 : 0;
  const tempClass = gpu.temperature >= 80 ? 'text-red-400' : gpu.temperature >= 60 ? 'text-yellow-400' : 'text-green-400';

  return (
    <div className="bg-slate-900 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-sm">[{gpu.index}]</span>
          <span className="text-white font-medium">{gpu.name}</span>
          {gpu.node && (
            <span className="text-xs text-slate-500">@ {gpu.node}</span>
          )}
        </div>
        <div className={clsx('flex items-center gap-1 text-sm', tempClass)}>
          <Thermometer size={14} />
          {gpu.temperature}°C
        </div>
      </div>

      <div className="space-y-2">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">GPU 사용률</span>
            <span className="text-slate-300">{gpu.utilization}%</span>
          </div>
          <ProgressBar value={gpu.utilization} showLabel={false} size="sm" />
        </div>

        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">VRAM</span>
            <span className="text-slate-300">
              {(gpu.memory_used / 1024).toFixed(1)}G / {(gpu.memory_total / 1024).toFixed(0)}G
            </span>
          </div>
          <ProgressBar value={memPercent} showLabel={false} size="sm" />
        </div>

        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">전력</span>
            <span className="text-slate-300">
              {gpu.power_draw.toFixed(0)}W / {gpu.power_limit.toFixed(0)}W
            </span>
          </div>
          <ProgressBar value={powerPercent} showLabel={false} size="sm" />
        </div>
      </div>
    </div>
  );
}

export function GpuMonitor({ gpuStatus, gpuDetailed, nodeMetrics }: GpuMonitorProps) {
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});

  // Group GPUs by node
  const gpusByNode: Record<string, GpuInfo[]> = {};
  if (gpuDetailed?.available && gpuDetailed.gpus) {
    gpuDetailed.gpus.forEach(gpu => {
      const nodeName = gpu.node || 'unknown';
      if (!gpusByNode[nodeName]) gpusByNode[nodeName] = [];
      gpusByNode[nodeName].push(gpu);
    });
  }

  // Add nodes from gpuStatus that might not have detailed info
  gpuStatus?.gpu_nodes?.forEach(node => {
    if (!gpusByNode[node.node]) gpusByNode[node.node] = [];
  });

  const nodeNames = Object.keys(gpusByNode);
  const totalGpus = gpuStatus?.total_gpus || 0;

  if (totalGpus === 0) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-8 text-center">
        <Zap size={48} className="mx-auto text-slate-600 mb-4" />
        <p className="text-slate-400">클러스터에 GPU 노드가 없습니다</p>
        <p className="text-sm text-slate-500 mt-2">GPU가 있는 노드를 클러스터에 추가하세요</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700">
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="text-green-500" size={20} />
          <h3 className="font-semibold text-white">GPU 모니터링</h3>
        </div>
        <div className="text-sm text-slate-400">
          총 {totalGpus}개 GPU ({nodeNames.length}개 노드)
        </div>
      </div>

      <div className="divide-y divide-slate-700">
        {nodeNames.map(nodeName => {
          const gpus = gpusByNode[nodeName];
          const nodeInfo = gpuStatus?.gpu_nodes?.find(n => n.node === nodeName);
          const isExpanded = expandedNodes[nodeName] !== false;
          const hasDetailedMetrics = gpus.length > 0 && gpus[0].utilization !== undefined;

          return (
            <div key={nodeName}>
              <button
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-700/50 transition-colors"
                onClick={() => setExpandedNodes(prev => ({ ...prev, [nodeName]: !prev[nodeName] }))}
              >
                <div className="flex items-center gap-3">
                  <Server size={18} className="text-slate-400" />
                  <span className="font-medium text-white">{nodeName}</span>
                  <span className="text-sm text-slate-500">{nodeInfo?.gpu_type}</span>
                  <Badge
                    variant={nodeInfo?.status === 'ready' ? 'success' : 'warning'}
                    size="sm"
                  >
                    {nodeInfo?.status || 'unknown'}
                  </Badge>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-slate-400">
                    {gpus.length || nodeInfo?.gpu_count || 0}개 GPU
                  </span>
                  <ChevronDown
                    size={16}
                    className={clsx(
                      'text-slate-400 transition-transform',
                      isExpanded && 'rotate-180'
                    )}
                  />
                </div>
              </button>

              {isExpanded && (
                <div className="p-4 bg-slate-900/50">
                  {hasDetailedMetrics ? (
                    <div className="grid grid-cols-2 gap-4">
                      {gpus.map(gpu => (
                        <GpuCard key={gpu.index} gpu={gpu} />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <Info size={20} className="mx-auto text-slate-500 mb-2" />
                      <p className="text-sm text-slate-400">
                        실시간 메트릭 조회를 위해서는 GPU Metrics Collector 설치가 필요합니다
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default GpuMonitor;
