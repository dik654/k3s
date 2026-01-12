import { useState } from 'react';
import { Server, ChevronDown, ChevronRight, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui';
import clsx from 'clsx';
import type { Pod, PodsData } from '@/types';

interface PodsListProps {
  pods: PodsData;
}

function PodStatusIcon({ status }: { status: string }) {
  switch (status.toLowerCase()) {
    case 'running':
      return <CheckCircle size={14} className="text-green-500" />;
    case 'pending':
      return <Clock size={14} className="text-yellow-500" />;
    case 'failed':
      return <XCircle size={14} className="text-red-500" />;
    case 'succeeded':
      return <CheckCircle size={14} className="text-blue-500" />;
    default:
      return <AlertCircle size={14} className="text-slate-500" />;
  }
}

export function PodsList({ pods }: PodsListProps) {
  const [expandedNamespaces, setExpandedNamespaces] = useState<Record<string, boolean>>({});

  const toggleNamespace = (ns: string) => {
    setExpandedNamespaces(prev => ({ ...prev, [ns]: !prev[ns] }));
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700">
      <div className="p-4 border-b border-slate-700">
        <h3 className="font-semibold text-white">Pod 목록 ({pods.total}개)</h3>
      </div>
      <div className="divide-y divide-slate-700">
        {Object.entries(pods.by_namespace || {}).map(([namespace, nsPods]) => (
          <div key={namespace}>
            <button
              className="w-full flex items-center gap-2 px-4 py-3 hover:bg-slate-700/50 transition-colors"
              onClick={() => toggleNamespace(namespace)}
            >
              {expandedNamespaces[namespace] ? (
                <ChevronDown size={16} className="text-slate-400" />
              ) : (
                <ChevronRight size={16} className="text-slate-400" />
              )}
              <span className="font-medium text-white">{namespace}</span>
              <Badge variant="default" size="sm">{nsPods.length}</Badge>
            </button>
            {expandedNamespaces[namespace] && (
              <div className="bg-slate-900/50 divide-y divide-slate-700/50">
                {nsPods.map((pod) => (
                  <div
                    key={pod.name}
                    className="px-4 py-2 pl-10 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <PodStatusIcon status={pod.status} />
                      <span className="text-sm text-slate-300">{pod.name}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      {pod.node && (
                        <span className="flex items-center gap-1">
                          <Server size={12} />
                          {pod.node}
                        </span>
                      )}
                      {pod.ip && <span>IP: {pod.ip}</span>}
                      {(pod.cpu_usage ?? 0) > 0 && <span>CPU: {pod.cpu_usage}m</span>}
                      {(pod.memory_usage ?? 0) > 0 && <span>Mem: {pod.memory_usage}Mi</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default PodsList;
