import { CheckCircle, Clock, AlertCircle, Circle } from 'lucide-react';

export interface PodStatusIconProps {
  status: string;
  size?: number;
}

export function PodStatusIcon({ status, size = 14 }: PodStatusIconProps) {
  switch (status) {
    case 'Running':
      return <CheckCircle size={size} color="var(--color-accent-green)" />;
    case 'Pending':
      return <Clock size={size} color="var(--color-accent-yellow)" className="spinning" />;
    case 'Failed':
    case 'Error':
      return <AlertCircle size={size} color="var(--color-accent-red)" />;
    default:
      return <Circle size={size} color="var(--color-text-muted)" />;
  }
}

export default PodStatusIcon;
