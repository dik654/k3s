import { Play, Square, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardContent, CardFooter, Button, Badge } from '@/components/ui';
import type { ReactNode } from 'react';

export interface WorkloadCardProps {
  title: string;
  subtitle?: string;
  icon: ReactNode;
  accentColor: string;
  status: 'running' | 'stopped' | 'not_deployed' | 'error' | 'pending';
  readyReplicas?: number;
  desiredReplicas?: number;
  isLoading?: boolean;
  loadingAction?: 'start' | 'stop';
  onStart?: () => void;
  onStop?: () => void;
  children?: ReactNode;
}

const statusConfig = {
  running: { label: '실행중', variant: 'success' as const },
  stopped: { label: '중지됨', variant: 'warning' as const },
  not_deployed: { label: '미배포', variant: 'warning' as const },
  error: { label: '오류', variant: 'error' as const },
  pending: { label: '준비중', variant: 'info' as const },
};

export function WorkloadCard({
  title,
  subtitle,
  icon,
  accentColor,
  status,
  readyReplicas,
  desiredReplicas,
  isLoading = false,
  loadingAction,
  onStart,
  onStop,
  children,
}: WorkloadCardProps) {
  const statusInfo = statusConfig[status];
  const isRunning = status === 'running';
  const isStopped = status === 'stopped' || status === 'not_deployed';

  return (
    <Card accentColor={accentColor} variant="workload">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center text-white"
              style={{ backgroundColor: accentColor }}
            >
              {icon}
            </div>
            <div>
              <h3 className="font-semibold text-white">{title}</h3>
              {subtitle && (
                <p className="text-xs text-slate-400">{subtitle}</p>
              )}
            </div>
          </div>
          {isLoading ? (
            <Badge variant="info" className="gap-1">
              <Loader2 className="animate-spin" size={12} />
              {loadingAction === 'start' ? '시작 중...' : '중지 중...'}
            </Badge>
          ) : (
            <Badge variant={statusInfo.variant}>
              {statusInfo.label}
              {readyReplicas !== undefined && desiredReplicas !== undefined && (
                <span className="ml-1">({readyReplicas}/{desiredReplicas})</span>
              )}
            </Badge>
          )}
        </div>
      </CardHeader>

      {children && <CardContent>{children}</CardContent>}

      {(onStart || onStop) && (
        <CardFooter className="flex gap-2">
          {onStart && (
            <Button
              variant="success"
              size="sm"
              onClick={onStart}
              disabled={isLoading || isRunning}
              isLoading={isLoading && loadingAction === 'start'}
              leftIcon={<Play size={14} />}
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
              leftIcon={<Square size={14} />}
            >
              중지
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  );
}

export default WorkloadCard;
