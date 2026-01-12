import { RefreshCw } from 'lucide-react';
import { StatusIndicator } from '@/components/ui';
import clsx from 'clsx';

export interface HeaderProps {
  title: string;
  status?: 'healthy' | 'warning' | 'error';
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export function Header({ title, status = 'healthy', onRefresh, isRefreshing }: HeaderProps) {
  const statusMap = {
    healthy: 'online' as const,
    warning: 'warning' as const,
    error: 'error' as const,
  };

  const statusLabel = {
    healthy: '정상',
    warning: '경고',
    error: '오류',
  };

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6">
      <h1 className="text-lg font-semibold text-white">{title}</h1>
      
      <div className="flex items-center gap-4">
        {/* Cluster Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg">
          <StatusIndicator status={statusMap[status]} pulse={status === 'healthy'} />
          <span className="text-sm text-slate-300">{statusLabel[status]}</span>
        </div>

        {/* Refresh Button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className={clsx(
              'p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            <RefreshCw
              size={18}
              className={clsx(isRefreshing && 'animate-spin')}
            />
          </button>
        )}
      </div>
    </header>
  );
}

export default Header;
