import clsx from 'clsx';
import { Loader2 } from 'lucide-react';
import type { WorkloadStatus } from '@/types';

export interface StatusBadgeProps {
  status: WorkloadStatus['status'] | string;
  isLoading?: boolean;
  actionType?: 'start' | 'stop';
  className?: string;
}

const statusLabels: Record<string, string> = {
  running: '실행중',
  stopped: '중지됨',
  not_deployed: '미배포',
  error: '오류',
  pending: '준비중',
};

const statusClasses: Record<string, string> = {
  running: 'success',
  stopped: 'warning',
  not_deployed: 'warning',
  error: 'error',
  pending: 'info',
};

export function StatusBadge({
  status,
  isLoading,
  actionType,
  className,
}: StatusBadgeProps) {
  if (isLoading) {
    return (
      <span className={clsx('status-badge', 'loading', className)}>
        <Loader2 className="animate-spin" size={12} />
        {actionType === 'start' ? '시작 중...' : actionType === 'stop' ? '중지 중...' : '처리 중...'}
      </span>
    );
  }

  const label = statusLabels[status] || status;
  const statusClass = statusClasses[status] || '';

  return (
    <span className={clsx('status-badge', statusClass, className)}>
      {label}
    </span>
  );
}

export default StatusBadge;
