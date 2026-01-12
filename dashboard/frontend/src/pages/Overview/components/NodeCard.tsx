import { StatusIndicator, Badge } from '@/components/ui';
import clsx from 'clsx';

export interface NodeCardProps {
  name: string;
  status: 'Ready' | 'NotReady' | 'Unknown';
  roles: string[];
  cpuPercent: number;
  cpuUsed: number;
  cpuCapacity: number;
  cpuRequests?: number;
  cpuLimits?: number;
  memoryPercent: number;
  memoryUsed: number;
  memoryCapacity: number;
  memoryRequests?: number;
  memoryLimits?: number;
  gpuCapacity?: number;
  gpuUsed?: number;
  gpuType?: string;
}

function ResourceBar({
  label,
  usage,
  requests,
  limits,
  capacity,
  percent,
  unit,
}: {
  label: string;
  usage: number;
  requests?: number;
  limits?: number;
  capacity: number;
  percent: number;
  unit: string;
}) {
  const usageClass = percent >= 90 ? 'bg-red-500' : percent >= 70 ? 'bg-yellow-500' : 'bg-green-500';
  const requestsPercent = requests ? (requests / capacity) * 100 : 0;
  const limitsPercent = limits ? Math.min((limits / capacity) * 100, 100) : 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400 font-medium">{label}</span>
        <span className="text-slate-500">
          {usage.toFixed(1)} / {capacity.toFixed(0)} {unit}
        </span>
      </div>
      <div className="relative h-2 bg-slate-700 rounded-full overflow-hidden">
        {/* Limits bar (back) */}
        {limits && limitsPercent > 0 && (
          <div
            className="absolute h-full bg-purple-500/30 rounded-full"
            style={{ width: `${limitsPercent}%` }}
          />
        )}
        {/* Requests bar (middle) */}
        {requests && requestsPercent > 0 && (
          <div
            className="absolute h-full bg-blue-500/40 rounded-full"
            style={{ width: `${requestsPercent}%` }}
          />
        )}
        {/* Usage bar (front) */}
        <div
          className={clsx('absolute h-full rounded-full transition-all', usageClass)}
          style={{ width: `${percent}%` }}
        />
        {/* Segment lines */}
        <div className="absolute inset-0 flex">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="flex-1 border-r border-slate-600/30 last:border-r-0" />
          ))}
        </div>
      </div>
      <div className="text-right text-xs text-slate-400">{percent.toFixed(0)}%</div>
    </div>
  );
}

export function NodeCard({
  name,
  status,
  roles,
  cpuPercent,
  cpuUsed,
  cpuCapacity,
  cpuRequests,
  cpuLimits,
  memoryPercent,
  memoryUsed,
  memoryCapacity,
  memoryRequests,
  memoryLimits,
  gpuCapacity = 0,
  gpuUsed = 0,
  gpuType,
}: NodeCardProps) {
  // Combine control-plane and master roles
  const displayRoles = (() => {
    const hasControlPlane = roles.includes('control-plane');
    const hasMaster = roles.includes('master');
    const hasEtcd = roles.includes('etcd');
    const otherRoles = roles.filter(r => !['control-plane', 'master', 'etcd'].includes(r));

    const result: string[] = [];
    if (hasControlPlane || hasMaster) result.push('control-plane');
    if (hasEtcd) result.push('etcd');
    return [...result, ...otherRoles];
  })();

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <StatusIndicator
            status={status === 'Ready' ? 'online' : 'error'}
            pulse={status === 'Ready'}
          />
          <div>
            <h3 className="font-semibold text-white">{name}</h3>
            <div className="flex gap-1 mt-1">
              {displayRoles.map((role) => (
                <Badge key={role} size="sm" variant="default">
                  {role}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Resource Bars */}
      <div className="space-y-3">
        <ResourceBar
          label="CPU"
          usage={cpuUsed / 1000}
          requests={cpuRequests ? cpuRequests / 1000 : undefined}
          limits={cpuLimits ? cpuLimits / 1000 : undefined}
          capacity={cpuCapacity / 1000}
          percent={cpuPercent}
          unit="cores"
        />
        <ResourceBar
          label="MEM"
          usage={memoryUsed / 1024}
          requests={memoryRequests ? memoryRequests / 1024 : undefined}
          limits={memoryLimits ? memoryLimits / 1024 : undefined}
          capacity={memoryCapacity / 1024}
          percent={memoryPercent}
          unit="GB"
        />

        {/* GPU Section */}
        {gpuCapacity > 0 && (
          <div className="pt-2 border-t border-slate-700">
            <ResourceBar
              label="GPU"
              usage={gpuUsed}
              capacity={gpuCapacity}
              percent={(gpuUsed / gpuCapacity) * 100}
              unit={gpuType || 'devices'}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default NodeCard;
