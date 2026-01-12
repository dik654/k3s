import clsx from 'clsx';

export interface ProgressBarProps {
  value: number;
  max?: number;
  variant?: 'default' | 'auto';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  variant = 'default',
  size = 'md',
  showLabel = true,
  className,
}: ProgressBarProps) {
  const percent = max > 0 ? Math.min((value / max) * 100, 100) : 0;

  // Auto color based on percentage
  const getColor = () => {
    if (variant === 'auto') {
      if (percent >= 90) return 'bg-red-500';
      if (percent >= 70) return 'bg-yellow-500';
      return 'bg-green-500';
    }
    return 'bg-blue-500';
  };

  const sizeStyles = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  };

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      <div className={clsx('flex-1 bg-slate-700 rounded-full overflow-hidden', sizeStyles[size])}>
        <div
          className={clsx('h-full rounded-full transition-all duration-300', getColor())}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-slate-400 min-w-[3rem] text-right">
          {percent.toFixed(1)}%
        </span>
      )}
    </div>
  );
}

export default ProgressBar;
