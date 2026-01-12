import { ReactNode } from 'react';
import clsx from 'clsx';
import { Play, Square, Loader2 } from 'lucide-react';
import { Badge, Button } from '@/components/ui';

export interface WorkloadStatus {
  status: 'running' | 'stopped' | 'not_deployed' | 'error';
  ready_replicas?: number;
  desired_replicas?: number;
}

export interface WorkloadCardProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  status?: WorkloadStatus;
  accentColor?: string;
  isLoading?: boolean;
  loadingAction?: 'start' | 'stop';
  onStart?: () => void;
  onStop?: () => void;
  children?: ReactNode;
  className?: string;
}

const getStatusBadge = (status: WorkloadStatus['status']) => {
  switch (status) {
    case 'running':
      return <Badge variant="success">실행중</Badge>;
    case 'stopped':
      return <Badge variant="error">중지됨</Badge>;
    case 'not_deployed':
      return <Badge variant="warning">미배포</Badge>;
    case 'error':
      return <Badge variant="error">오류</Badge>;
    default:
      return <Badge>알 수 없음</Badge>;
  }
};

export function WorkloadCard({
  title,
  subtitle,
  icon,
  status,
  accentColor = '#3b82f6',
  isLoading = false,
  loadingAction,
  onStart,
  onStop,
  children,
  className,
}: WorkloadCardProps) {
  const isRunning = status?.status === 'running';
  const isStopped = status?.status === 'stopped' || status?.status === 'not_deployed';

  return (
    <div
      className={clsx(
        'bg-white dark:bg-dark-800 rounded-lg border border-gray-200 dark:border-dark-700',
        'overflow-hidden transition-shadow hover:shadow-lg dark:hover:shadow-dark-900/50',
        className
      )}
      style={{ borderLeftWidth: '3px', borderLeftColor: accentColor }}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-100 dark:border-dark-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {icon && (
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center text-white"
                style={{ backgroundColor: accentColor }}
              >
                {icon}
              </div>
            )}
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {title}
              </h3>
              {subtitle && (
                <p className="text-sm text-gray-500 dark:text-dark-400">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          {status && getStatusBadge(status.status)}
        </div>
      </div>

      {/* Content */}
      {children && <div className="p-4">{children}</div>}

      {/* Controls */}
      {(onStart || onStop) && (
        <div className="px-4 py-3 bg-gray-50 dark:bg-dark-800/50 border-t border-gray-100 dark:border-dark-700">
          <div className="flex gap-2">
            {onStart && (
              <Button
                variant="success"
                size="sm"
                onClick={onStart}
                disabled={isLoading || isRunning}
                isLoading={isLoading && loadingAction === 'start'}
                leftIcon={<Play className="w-4 h-4" />}
              >
                실행
              </Button>
            )}
            {onStop && (
              <Button
                variant="danger"
                size="sm"
                onClick={onStop}
                disabled={isLoading || isStopped}
                isLoading={isLoading && loadingAction === 'stop'}
                leftIcon={<Square className="w-4 h-4" />}
              >
                중지
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkloadCard;
