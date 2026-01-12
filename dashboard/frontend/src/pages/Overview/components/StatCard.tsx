import type { ReactNode } from 'react';
import { Card, ProgressBar } from '@/components/ui';
import clsx from 'clsx';

export interface StatCardProps {
  icon: ReactNode;
  iconColor: string;
  title: string;
  value: string | number;
  subtitle?: string;
  progress?: number;
  badges?: Array<{ label: string; color: 'yellow' | 'red' | 'green' }>;
}

export function StatCard({
  icon,
  iconColor,
  title,
  value,
  subtitle,
  progress,
  badges,
}: StatCardProps) {
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-start justify-between">
        <div
          className={clsx(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            iconColor
          )}
        >
          {icon}
        </div>
      </div>
      <div>
        <p className="text-xs text-slate-400">{title}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
        {subtitle && (
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-slate-500">{subtitle}</span>
            {badges?.map((badge, i) => (
              <span
                key={i}
                className={clsx(
                  'text-[10px] px-1.5 py-0.5 rounded',
                  badge.color === 'yellow' && 'bg-yellow-900/40 text-yellow-400',
                  badge.color === 'red' && 'bg-red-900/40 text-red-400',
                  badge.color === 'green' && 'bg-green-900/40 text-green-400'
                )}
              >
                {badge.label}
              </span>
            ))}
          </div>
        )}
      </div>
      {progress !== undefined && (
        <ProgressBar value={progress} variant="auto" showLabel={false} size="sm" />
      )}
    </Card>
  );
}

export default StatCard;
