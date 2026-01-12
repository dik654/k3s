import clsx from 'clsx';

export interface ProgressBarProps {
  value: number;
  max?: number;
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'auto' | string;
  showLabel?: boolean;
  height?: number;
  className?: string;
}

const colorMap: Record<string, string> = {
  blue: 'var(--color-accent-blue)',
  green: 'var(--color-accent-green)',
  red: 'var(--color-accent-red)',
  yellow: 'var(--color-accent-yellow)',
  purple: 'var(--color-accent-purple)',
};

export function ProgressBar({
  value,
  max = 100,
  color = 'blue',
  showLabel = true,
  height = 8,
  className,
}: ProgressBarProps) {
  const percent = max > 0 ? Math.min((value / max) * 100, 100) : 0;

  let barColor = colorMap[color] || color;
  if (color === 'auto') {
    if (percent >= 90) barColor = 'var(--color-accent-red)';
    else if (percent >= 70) barColor = 'var(--color-accent-yellow)';
    else barColor = 'var(--color-accent-green)';
  }

  return (
    <div className={clsx('progress-container', className)}>
      <div className="progress-bar" style={{ height }}>
        <div
          className="progress-fill"
          style={{ width: `${percent}%`, background: barColor }}
        />
      </div>
      {showLabel && <span className="progress-label">{percent.toFixed(1)}%</span>}
    </div>
  );
}

export default ProgressBar;
