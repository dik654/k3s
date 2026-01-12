import clsx from 'clsx';

export interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'warning' | 'error' | 'loading';
  pulse?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const statusColors = {
  online: 'bg-green-500',
  offline: 'bg-slate-500',
  warning: 'bg-yellow-500',
  error: 'bg-red-500',
  loading: 'bg-blue-500',
};

const sizeStyles = {
  sm: 'w-2 h-2',
  md: 'w-2.5 h-2.5',
  lg: 'w-3 h-3',
};

export function StatusIndicator({
  status,
  pulse = false,
  size = 'md',
  className,
}: StatusIndicatorProps) {
  return (
    <span className={clsx('relative inline-flex', className)}>
      <span
        className={clsx(
          'rounded-full',
          statusColors[status],
          sizeStyles[size]
        )}
      />
      {pulse && status === 'online' && (
        <span
          className={clsx(
            'absolute inline-flex rounded-full opacity-75 animate-ping',
            statusColors[status],
            sizeStyles[size]
          )}
        />
      )}
    </span>
  );
}

export default StatusIndicator;
