import { forwardRef, type SelectHTMLAttributes } from 'react';
import clsx from 'clsx';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, className, children, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label className="text-xs font-medium text-slate-400">{label}</label>
        )}
        <select
          ref={ref}
          className={clsx(
            'w-full px-3 py-2 rounded-lg text-sm',
            'bg-slate-700 border border-slate-600 text-white',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            error && 'border-red-500',
            className
          )}
          {...props}
        >
          {children}
        </select>
        {error && <span className="text-xs text-red-400">{error}</span>}
      </div>
    );
  }
);

Select.displayName = 'Select';
export default Select;
