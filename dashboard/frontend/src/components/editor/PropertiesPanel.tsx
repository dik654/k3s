import { X, Trash2 } from 'lucide-react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { useNodeDefinitionsStore } from '@/stores/nodeDefinitionsStore';

const inputStyle = {
  width: '100%',
  padding: '8px 12px',
  background: '#334155',
  border: '1px solid #475569',
  borderRadius: 6,
  fontSize: 13,
  color: '#fff'
};

export function PropertiesPanel() {
  const { nodes, selectedNodeId, updateNodeData, deleteNode, togglePropertiesPanel } = useWorkflowStore();
  const { getNodeDefinition } = useNodeDefinitionsStore();

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  if (!selectedNode) return null;

  const nodeDefinition = getNodeDefinition(selectedNode.data.type);

  const handleParameterChange = (paramName: string, value: any) => {
    updateNodeData(selectedNodeId!, {
      parameters: {
        ...selectedNode.data.parameters,
        [paramName]: value,
      },
    });
  };

  const handleDelete = () => {
    deleteNode(selectedNodeId!);
  };

  return (
    <div style={{
      width: 320,
      background: '#1e293b',
      borderLeft: '1px solid #334155',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header */}
      <div style={{
        height: 56,
        padding: '0 16px',
        borderBottom: '1px solid #334155',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 12,
              height: 12,
              borderRadius: 2,
              backgroundColor: selectedNode.data.color
            }}
          />
          <span style={{ color: '#fff', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {selectedNode.data.name}
          </span>
        </div>
        <button
          onClick={togglePropertiesPanel}
          style={{ padding: 4, background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
        >
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Node Name */}
        <div>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#cbd5e1', marginBottom: 6 }}>
            이름
          </label>
          <input
            type="text"
            value={selectedNode.data.name}
            onChange={(e) => updateNodeData(selectedNodeId!, { name: e.target.value })}
            style={inputStyle}
          />
        </div>

        {/* Parameters */}
        {nodeDefinition?.parameters.map((param) => (
          <div key={param.name}>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#cbd5e1', marginBottom: 6 }}>
              {param.displayName}
            </label>
            {param.type === 'select' ? (
              <select
                value={selectedNode.data.parameters?.[param.name] ?? param.default}
                onChange={(e) => handleParameterChange(param.name, e.target.value)}
                style={inputStyle}
              >
                {param.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            ) : param.type === 'number' ? (
              <input
                type="number"
                value={selectedNode.data.parameters?.[param.name] ?? param.default}
                onChange={(e) => handleParameterChange(param.name, parseFloat(e.target.value))}
                style={inputStyle}
              />
            ) : param.type === 'boolean' ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={selectedNode.data.parameters?.[param.name] ?? param.default}
                  onChange={(e) => handleParameterChange(param.name, e.target.checked)}
                  style={{ width: 16, height: 16 }}
                />
                <span style={{ fontSize: 13, color: '#94a3b8' }}>활성화</span>
              </div>
            ) : param.type === 'code' ? (
              <textarea
                value={selectedNode.data.parameters?.[param.name] ?? param.default}
                onChange={(e) => handleParameterChange(param.name, e.target.value)}
                rows={4}
                style={{ ...inputStyle, fontFamily: 'monospace', resize: 'vertical' }}
              />
            ) : (
              <input
                type="text"
                value={selectedNode.data.parameters?.[param.name] ?? param.default}
                onChange={(e) => handleParameterChange(param.name, e.target.value)}
                style={inputStyle}
              />
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding: 16, borderTop: '1px solid #334155' }}>
        <button
          onClick={handleDelete}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            padding: '10px 16px',
            background: 'rgba(239, 68, 68, 0.2)',
            border: 'none',
            borderRadius: 8,
            color: '#f87171',
            cursor: 'pointer',
            fontSize: 13
          }}
        >
          <Trash2 size={16} />
          노드 삭제
        </button>
      </div>
    </div>
  );
}

export default PropertiesPanel;
