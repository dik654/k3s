import type { ReactNode, HTMLAttributes } from 'react';
import clsx from 'clsx';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: 'default' | 'stat' | 'workload';
  accentColor?: string;
}

export function Card({ children, variant = 'default', accentColor, className, style, ...props }: CardProps) {
  const baseStyles = 'rounded-lg border border-slate-700 bg-slate-800 overflow-hidden';
  
  const variantStyles = {
    default: 'p-4',
    stat: 'p-4',
    workload: 'p-0',
  };

  const cardStyle = accentColor 
    ? { ...style, borderLeftWidth: '3px', borderLeftColor: accentColor }
    : style;

  return (
    <div
      className={clsx(baseStyles, variantStyles[variant], className)}
      style={cardStyle}
      {...props}
    >
      {children}
    </div>
  );
}

export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function CardHeader({ children, className, ...props }: CardHeaderProps) {
  return (
    <div
      className={clsx('p-4 border-b border-slate-700', className)}
      {...props}
    >
      {children}
    </div>
  );
}

export interface CardContentProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function CardContent({ children, className, ...props }: CardContentProps) {
  return (
    <div className={clsx('p-4', className)} {...props}>
      {children}
    </div>
  );
}

export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function CardFooter({ children, className, ...props }: CardFooterProps) {
  return (
    <div
      className={clsx('px-4 py-3 bg-slate-800/50 border-t border-slate-700', className)}
      {...props}
    >
      {children}
    </div>
  );
}

export default Card;
