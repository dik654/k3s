import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  NodeTypes,
  EdgeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useParams, useNavigate } from 'react-router-dom';
import { Save, Play, Sidebar, Loader2, ArrowLeft, History, X, CheckCircle2, XCircle, Clock } from 'lucide-react';

import { useWorkflowStore } from '@/stores/workflowStore';
import { WorkflowNode } from '@/components/nodes/WorkflowNode';
import { WorkflowEdge } from '@/components/nodes/WorkflowEdge';
import { NodePanel } from '@/components/editor/NodePanel';
import { PropertiesPanel } from '@/components/editor/PropertiesPanel';

const nodeTypes: NodeTypes = {
  workflowNode: WorkflowNode,
};

const edgeTypes: EdgeTypes = {
  workflow: WorkflowEdge,
};

export function WorkflowEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [showExecutionPanel, setShowExecutionPanel] = useState(false);

  const {
    workflow,
    nodes,
    edges,
    selectedNodeId,
    isNodePanelOpen,
    isPropertiesPanelOpen,
    isSaving,
    isExecuting,
    isLoading,
    currentExecution,
    executionHistory,
    nodeExecutionStatus,
    onNodesChange,
    onEdgesChange,
    onConnect,
    selectNode,
    toggleNodePanel,
    saveWorkflow,
    executeWorkflow,
    loadWorkflow,
    clearWorkflow,
    loadExecutionHistory,
    clearExecution,
  } = useWorkflowStore();

  // 워크플로우 로드
  useEffect(() => {
    if (id) {
      loadWorkflow(id);
      loadExecutionHistory();
    }
    return () => {
      clearWorkflow();
    };
  }, [id, loadWorkflow, clearWorkflow, loadExecutionHistory]);

  // 실행 시작 시 패널 표시
  useEffect(() => {
    if (isExecuting || currentExecution) {
      setShowExecutionPanel(true);
    }
  }, [isExecuting, currentExecution]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: any) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const nodeType = event.dataTransfer.getData('application/reactflow');
      if (!nodeType) return;

      const nodeData = JSON.parse(nodeType);
      const position = {
        x: event.clientX - 250,
        y: event.clientY - 100,
      };

      const { addNode } = useWorkflowStore.getState();
      addNode(nodeData, position);
    },
    []
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // 로딩 중일 때
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: 'var(--text-muted)'
      }}>
        <Loader2 size={32} className="spin" style={{ marginBottom: 12 }} />
        <p>워크플로우 로딩 중...</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 16px',
        borderBottom: '1px solid var(--border-color)',
        background: 'var(--bg-secondary)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate('/agent')}
          >
            <ArrowLeft size={14} /> 목록
          </button>
          {workflow && (
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
              {workflow.name}
            </span>
          )}
          <button
            className="btn btn-secondary btn-sm"
            onClick={toggleNodePanel}
          >
            <Sidebar size={14} /> 노드 패널
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowExecutionPanel(!showExecutionPanel)}
          >
            <History size={14} /> 실행 이력
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={saveWorkflow}
            disabled={isSaving || !workflow}
          >
            {isSaving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
            저장
          </button>
          <button
            className="btn btn-success btn-sm"
            onClick={executeWorkflow}
            disabled={isExecuting || !workflow}
          >
            {isExecuting ? <Loader2 size={14} className="spin" /> : <Play size={14} />}
            실행
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Node Panel (Left Sidebar) */}
        {isNodePanelOpen && <NodePanel />}

        {/* Canvas */}
        <div style={{ flex: 1, position: 'relative', background: '#1e293b' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
            defaultEdgeOptions={{
              type: 'workflow',
              animated: false,
            }}
          >
            <Background color="#334155" gap={20} />
            <Controls />
            <MiniMap
              nodeColor={(node) => node.data.color || '#64748b'}
              maskColor="rgba(0, 0, 0, 0.8)"
            />
          </ReactFlow>
        </div>

        {/* Properties Panel (Right Sidebar) */}
        {isPropertiesPanelOpen && selectedNodeId && <PropertiesPanel />}

        {/* Execution Panel */}
        {showExecutionPanel && (
          <div style={{
            width: 320,
            background: 'var(--bg-card)',
            borderLeft: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* Header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
                <History size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />
                실행 결과
              </h3>
              <button
                className="btn btn-icon btn-sm"
                onClick={() => setShowExecutionPanel(false)}
              >
                <X size={14} />
              </button>
            </div>

            {/* Current Execution */}
            {currentExecution && (
              <div style={{
                padding: 16,
                borderBottom: '1px solid var(--border-color)'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 12
                }}>
                  {currentExecution.status === 'running' && (
                    <Loader2 size={16} className="spin" style={{ color: 'var(--color-accent-blue)' }} />
                  )}
                  {currentExecution.status === 'completed' && (
                    <CheckCircle2 size={16} style={{ color: 'var(--color-success)' }} />
                  )}
                  {currentExecution.status === 'failed' && (
                    <XCircle size={16} style={{ color: 'var(--color-error)' }} />
                  )}
                  <span style={{ fontWeight: 500 }}>
                    {currentExecution.status === 'running' ? '실행 중...' :
                     currentExecution.status === 'completed' ? '실행 완료' : '실행 실패'}
                  </span>
                </div>

                {/* Node Results */}
                <div style={{ fontSize: 12 }}>
                  <div style={{
                    color: 'var(--text-muted)',
                    marginBottom: 8,
                    textTransform: 'uppercase',
                    fontWeight: 600
                  }}>
                    노드 실행 상태
                  </div>
                  {Object.entries(nodeExecutionStatus).map(([nodeId, status]) => {
                    const node = nodes.find(n => n.id === nodeId);
                    return (
                      <div key={nodeId} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '6px 0',
                        borderBottom: '1px solid var(--border-color)'
                      }}>
                        {status === 'running' && <Loader2 size={12} className="spin" style={{ color: 'var(--color-accent-blue)' }} />}
                        {status === 'success' && <CheckCircle2 size={12} style={{ color: 'var(--color-success)' }} />}
                        {status === 'error' && <XCircle size={12} style={{ color: 'var(--color-error)' }} />}
                        {status === 'pending' && <Clock size={12} style={{ color: 'var(--text-muted)' }} />}
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {node?.data?.name || nodeId}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {currentExecution.error && (
                  <div style={{
                    marginTop: 12,
                    padding: 12,
                    background: 'rgba(239, 68, 68, 0.1)',
                    borderRadius: 8,
                    color: 'var(--color-error)',
                    fontSize: 12
                  }}>
                    {currentExecution.error}
                  </div>
                )}

                <button
                  className="btn btn-secondary btn-sm"
                  style={{ marginTop: 12, width: '100%' }}
                  onClick={clearExecution}
                >
                  결과 지우기
                </button>
              </div>
            )}

            {/* Execution History */}
            <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
              <div style={{
                color: 'var(--text-muted)',
                marginBottom: 12,
                fontSize: 12,
                textTransform: 'uppercase',
                fontWeight: 600
              }}>
                실행 이력
              </div>
              {executionHistory.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: 20 }}>
                  실행 이력이 없습니다
                </div>
              ) : (
                executionHistory.map((exec) => (
                  <div key={exec.id} style={{
                    padding: 12,
                    marginBottom: 8,
                    background: 'var(--bg-secondary)',
                    borderRadius: 8,
                    fontSize: 12
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      {exec.status === 'completed' && <CheckCircle2 size={12} style={{ color: 'var(--color-success)' }} />}
                      {exec.status === 'failed' && <XCircle size={12} style={{ color: 'var(--color-error)' }} />}
                      {exec.status === 'running' && <Loader2 size={12} className="spin" style={{ color: 'var(--color-accent-blue)' }} />}
                      <span style={{ fontWeight: 500 }}>
                        {exec.status === 'completed' ? '성공' : exec.status === 'failed' ? '실패' : '실행 중'}
                      </span>
                    </div>
                    <div style={{ color: 'var(--text-muted)' }}>
                      {new Date(exec.started_at).toLocaleString('ko-KR')}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default WorkflowEditor;
