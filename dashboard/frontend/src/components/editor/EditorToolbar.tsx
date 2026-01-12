import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Save,
  Play,
  Loader2,
  PanelLeftClose,
  PanelLeft,
  Package,
  Rocket,
  Code,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import clsx from 'clsx';
import { useWorkflowStore } from '@/stores/workflowStore';

interface EditorToolbarProps {
  workflowId?: string;
  isSaving: boolean;
  isExecuting: boolean;
  onSave: () => void;
  onExecute: () => void;
  onToggleNodePanel: () => void;
  isNodePanelOpen: boolean;
}

export function EditorToolbar({
  workflowId,
  isSaving,
  isExecuting,
  onSave,
  onExecute,
  onToggleNodePanel,
  isNodePanelOpen,
}: EditorToolbarProps) {
  const { nodes, edges } = useWorkflowStore();
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildStatus, setBuildStatus] = useState<'idle' | 'building' | 'success' | 'error'>('idle');
  const [buildId, setBuildId] = useState<string | null>(null);
  const [showCodeModal, setShowCodeModal] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<Record<string, string>>({});

  const handleGenerateCode = async () => {
    try {
      const workflow = {
        id: workflowId || 'new',
        name: `Workflow ${workflowId}`,
        description: 'Generated from workflow editor',
        nodes: nodes.map(n => ({
          id: n.id,
          type: n.type === 'workflowNode' ? n.data.type : n.type,
          data: n.data,
          position: n.position,
        })),
        connections: edges.map(e => ({
          sourceNodeId: e.source,
          sourcePortId: e.sourceHandle,
          targetNodeId: e.target,
          targetPortId: e.targetHandle,
        })),
      };

      const response = await fetch('/api/langgraph/generate-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow),
      });

      const data = await response.json();
      if (data.success) {
        setGeneratedCode(data.files);
        setShowCodeModal(true);
      }
    } catch (error) {
      console.error('Failed to generate code:', error);
    }
  };

  const handleBuildImage = async () => {
    setIsBuilding(true);
    setBuildStatus('building');

    try {
      const workflow = {
        id: workflowId || 'new',
        name: `Workflow ${workflowId}`,
        description: 'Generated from workflow editor',
        nodes: nodes.map(n => ({
          id: n.id,
          type: n.type === 'workflowNode' ? n.data.type : n.type,
          data: n.data,
          position: n.position,
        })),
        connections: edges.map(e => ({
          sourceNodeId: e.source,
          sourcePortId: e.sourceHandle,
          targetNodeId: e.target,
          targetPortId: e.targetHandle,
        })),
      };

      const response = await fetch('/api/langgraph/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow,
          image_name: `langgraph-${workflowId || 'agent'}`,
          image_tag: 'latest',
        }),
      });

      const data = await response.json();
      if (data.success) {
        setBuildId(data.build_id);
        // Poll for build status
        pollBuildStatus(data.build_id);
      }
    } catch (error) {
      console.error('Failed to build image:', error);
      setBuildStatus('error');
      setIsBuilding(false);
    }
  };

  const pollBuildStatus = async (id: string) => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`/api/langgraph/build/${id}/status`);
        const data = await response.json();

        if (data.status === 'completed') {
          setBuildStatus('success');
          setIsBuilding(false);
        } else if (data.status === 'failed') {
          setBuildStatus('error');
          setIsBuilding(false);
        } else {
          // Still building, check again
          setTimeout(checkStatus, 2000);
        }
      } catch (error) {
        setBuildStatus('error');
        setIsBuilding(false);
      }
    };

    checkStatus();
  };

  const handleDeploy = async () => {
    if (!buildId) return;

    try {
      const response = await fetch(`/api/langgraph/deploy/${buildId}`, {
        method: 'POST',
      });

      const data = await response.json();
      if (data.success) {
        alert('Agent deployed successfully!');
      }
    } catch (error) {
      console.error('Failed to deploy:', error);
    }
  };

  return (
    <>
    {/* Code Preview Modal */}
    {showCodeModal && (
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
        <div className="bg-dark-800 rounded-lg w-4/5 h-4/5 flex flex-col">
          <div className="flex items-center justify-between p-4 border-b border-dark-700">
            <h3 className="text-lg font-semibold text-white">Generated LangGraph Code</h3>
            <button
              onClick={() => setShowCodeModal(false)}
              className="text-dark-400 hover:text-white"
            >
              <XCircle className="w-5 h-5" />
            </button>
          </div>
          <div className="flex-1 overflow-auto p-4">
            {Object.entries(generatedCode).map(([filename, content]) => (
              <div key={filename} className="mb-6">
                <div className="text-sm font-mono text-primary-400 mb-2">{filename}</div>
                <pre className="bg-dark-900 p-4 rounded-lg text-sm text-gray-300 overflow-x-auto">
                  {content}
                </pre>
              </div>
            ))}
          </div>
          <div className="p-4 border-t border-dark-700 flex justify-end gap-2">
            <button
              onClick={() => setShowCodeModal(false)}
              className="px-4 py-2 bg-dark-700 text-white rounded-lg hover:bg-dark-600"
            >
              Close
            </button>
            <button
              onClick={handleBuildImage}
              disabled={isBuilding}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center gap-2"
            >
              <Package className="w-4 h-4" />
              Build Docker Image
            </button>
          </div>
        </div>
      </div>
    )}
    <div className="h-14 bg-dark-800 border-b border-dark-700 flex items-center justify-between px-4">
      {/* Left */}
      <div className="flex items-center gap-3">
        <Link
          to="/workflows"
          className="p-2 text-dark-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>

        <button
          onClick={onToggleNodePanel}
          className="p-2 text-dark-400 hover:text-white transition-colors"
          title={isNodePanelOpen ? 'Hide node panel' : 'Show node panel'}
        >
          {isNodePanelOpen ? (
            <PanelLeftClose className="w-5 h-5" />
          ) : (
            <PanelLeft className="w-5 h-5" />
          )}
        </button>

        <div className="h-6 w-px bg-dark-600" />

        <div>
          <div className="text-white font-medium">
            {workflowId === 'new' ? 'New Workflow' : `Workflow ${workflowId}`}
          </div>
          <div className="text-xs text-dark-400">Editing</div>
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">
        <button
          onClick={onSave}
          disabled={isSaving}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
            'bg-dark-700 text-white hover:bg-dark-600',
            isSaving && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isSaving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Save
        </button>

        <button
          onClick={onExecute}
          disabled={isExecuting}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
            'bg-primary-600 text-white hover:bg-primary-700',
            isExecuting && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isExecuting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          Execute
        </button>

        <div className="h-6 w-px bg-dark-600" />

        {/* LangGraph Build Section */}
        <button
          onClick={handleGenerateCode}
          className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors bg-purple-600 text-white hover:bg-purple-700"
          title="Generate LangGraph Code"
        >
          <Code className="w-4 h-4" />
          Code
        </button>

        <button
          onClick={handleBuildImage}
          disabled={isBuilding}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
            'bg-orange-600 text-white hover:bg-orange-700',
            isBuilding && 'opacity-50 cursor-not-allowed'
          )}
          title="Build Docker Image"
        >
          {isBuilding ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : buildStatus === 'success' ? (
            <CheckCircle className="w-4 h-4" />
          ) : buildStatus === 'error' ? (
            <XCircle className="w-4 h-4" />
          ) : (
            <Package className="w-4 h-4" />
          )}
          Build
        </button>

        {buildStatus === 'success' && (
          <button
            onClick={handleDeploy}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors bg-green-600 text-white hover:bg-green-700"
            title="Deploy to K8s"
          >
            <Rocket className="w-4 h-4" />
            Deploy
          </button>
        )}
      </div>
    </div>
    </>
  );
}

export default EditorToolbar;
