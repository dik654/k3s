import clsx from 'clsx';
import { ProgressBar, StatusIndicator } from '@/components/ui';

export interface NodeMetrics {
  name: string;
  status: 'Ready' | 'NotReady' | 'Unknown';
  roles: string[];
  cpu_percent: number;
  memory_percent: number;
  cpu_used: string;
  cpu_total: string;
  memory_used: string;
  memory_total: string;
  gpu_capacity?: number;
  gpu_used?: number;
  gpu_type?: string;
}

export interface NodeMetricCardProps {
  node: NodeMetrics;
  className?: string;
}

export function NodeMetricCard({ node, className }: NodeMetricCardProps) {
  const isReady = node.status === 'Ready';
  const hasGpu = (node.gpu_capacity || 0) > 0;

  // 역할 표시 최적화
  const displayRoles = (() => {
    const hasControlPlane = node.roles.includes('control-plane');
    const hasMaster = node.roles.includes('master');
    const hasEtcd = node.roles.includes('etcd');
    const otherRoles = node.roles.filter(
      (r) => !['control-plane', 'master', 'etcd'].includes(r)
    );

    const result: string[] = [];
    if (hasControlPlane || hasMaster) {
      result.push('control-plane/master');
    }
    if (hasEtcd) {
      result.push('etcd');
    }
    return [...result, ...otherRoles];
  })();

  return (
    <div
      className={clsx(
        'bg-white dark:bg-dark-800 rounded-lg border border-gray-200 dark:border-dark-700 p-4',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <StatusIndicator
            status={isReady ? 'online' : 'error'}
            pulse={isReady}
          />
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {node.name}
            </h3>
            <div className="flex gap-1 mt-1">
              {displayRoles.map((role) => (
                <span
                  key={role}
                  className="px-1.5 py-0.5 text-[10px] bg-gray-100 dark:bg-dark-700 text-gray-600 dark:text-dark-400 rounded"
                >
                  {role}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="space-y-3">
        {/* CPU */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-medium text-gray-600 dark:text-dark-400">
              CPU
            </span>
            <span className="text-xs text-gray-500 dark:text-dark-500">
              {node.cpu_used} / {node.cpu_total}
            </span>
          </div>
          <ProgressBar value={node.cpu_percent} size="md" showLabel />
        </div>

        {/* Memory */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs font-medium text-gray-600 dark:text-dark-400">
              Memory
            </span>
            <span className="text-xs text-gray-500 dark:text-dark-500">
              {node.memory_used} / {node.memory_total}
            </span>
          </div>
          <ProgressBar value={node.memory_percent} size="md" showLabel />
        </div>

        {/* GPU */}
        {hasGpu && (
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs font-medium text-gray-600 dark:text-dark-400">
                GPU
              </span>
              <span className="text-xs text-gray-500 dark:text-dark-500">
                {node.gpu_used} / {node.gpu_capacity}
              </span>
            </div>
            <ProgressBar
              value={node.gpu_used || 0}
              max={node.gpu_capacity || 1}
              variant="auto"
              size="md"
              showLabel
            />
            {node.gpu_type && (
              <div className="text-[10px] text-gray-400 dark:text-dark-500 mt-1">
                {node.gpu_type}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default NodeMetricCard;
