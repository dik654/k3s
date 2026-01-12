import React from 'react';
import { X, Info, Link as LinkIcon } from 'lucide-react';
import type { KnowledgeGraphNode, KnowledgeGraphEdge } from '@/types';

interface NodeDetailPanelProps {
  node: KnowledgeGraphNode | null;
  edge: KnowledgeGraphEdge | null;
  onClose: () => void;
}

export const NodeDetailPanel: React.FC<NodeDetailPanelProps> = ({
  node,
  edge,
  onClose,
}) => {
  const nodeColors: Record<string, string> = {
    class: '#3b82f6',
    instance: '#10b981',
    property: '#f59e0b',
    person: '#3b82f6',
    company: '#10b981',
    concept: '#f59e0b',
    location: '#06b6d4',
    default: '#6b7280',
  };

  if (node) {
    const bgColor = nodeColors[node.type] || nodeColors.default;

    return (
      <div className="w-80 bg-dark-800 border-l border-dark-700 h-full overflow-y-auto">
        {/* Header */}
        <div className="p-4 border-b border-dark-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: bgColor }}
            />
            <h3 className="text-white font-medium">Node Details</h3>
          </div>
          <button
            onClick={onClose}
            className="text-dark-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Basic Info */}
          <div>
            <h4 className="text-lg font-semibold text-white">{node.label}</h4>
            <div className="flex items-center gap-2 mt-1">
              <span
                className="px-2 py-0.5 rounded text-xs text-white"
                style={{ backgroundColor: bgColor }}
              >
                {node.type}
              </span>
              <span className="text-xs text-dark-400">ID: {node.id}</span>
            </div>
          </div>

          {/* Properties */}
          {Object.keys(node.properties).length > 0 && (
            <div>
              <h5 className="text-sm font-medium text-dark-300 mb-2 flex items-center gap-1">
                <Info className="w-4 h-4" />
                Properties
              </h5>
              <div className="space-y-2">
                {Object.entries(node.properties).map(([key, value]) => (
                  <div
                    key={key}
                    className="bg-dark-700 rounded-lg p-2"
                  >
                    <div className="text-xs text-dark-400">{key}</div>
                    <div className="text-sm text-white mt-0.5">
                      {typeof value === 'object'
                        ? JSON.stringify(value)
                        : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (edge) {
    return (
      <div className="w-80 bg-dark-800 border-l border-dark-700 h-full overflow-y-auto">
        {/* Header */}
        <div className="p-4 border-b border-dark-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <LinkIcon className="w-4 h-4 text-primary-400" />
            <h3 className="text-white font-medium">Edge Details</h3>
          </div>
          <button
            onClick={onClose}
            className="text-dark-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          <div>
            <h4 className="text-lg font-semibold text-white">
              {edge.label || edge.type}
            </h4>
            <span className="text-xs text-dark-400">ID: {edge.id}</span>
          </div>

          <div className="space-y-2">
            <div className="bg-dark-700 rounded-lg p-2">
              <div className="text-xs text-dark-400">Source</div>
              <div className="text-sm text-white mt-0.5">{edge.source}</div>
            </div>
            <div className="bg-dark-700 rounded-lg p-2">
              <div className="text-xs text-dark-400">Target</div>
              <div className="text-sm text-white mt-0.5">{edge.target}</div>
            </div>
            <div className="bg-dark-700 rounded-lg p-2">
              <div className="text-xs text-dark-400">Type</div>
              <div className="text-sm text-white mt-0.5">{edge.type}</div>
            </div>
            {edge.weight && (
              <div className="bg-dark-700 rounded-lg p-2">
                <div className="text-xs text-dark-400">Weight</div>
                <div className="text-sm text-white mt-0.5">{edge.weight}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default NodeDetailPanel;
