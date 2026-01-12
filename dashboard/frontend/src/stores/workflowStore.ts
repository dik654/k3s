import { create } from 'zustand';
import {
  Node,
  Edge,
  Connection,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
} from 'reactflow';
import type { Workflow, WorkflowNode, WorkflowConnection, NodeDefinition } from '@/types';
import axios from 'axios';

// API Base URL
const API_BASE = '/api/workflows';

// 워크플로우 목록 아이템 (간략)
interface WorkflowListItem {
  id: string;
  name: string;
  description: string;
  nodeCount: number;
  createdAt: string;
  updatedAt: string;
}

// 실행 결과 타입
interface NodeExecutionResult {
  node_id: string;
  status: 'pending' | 'running' | 'success' | 'error';
  output?: Record<string, any>;
  error?: string;
  started_at?: string;
  finished_at?: string;
}

interface ExecutionState {
  id: string;
  workflow_id: string;
  status: 'running' | 'completed' | 'failed';
  input?: Record<string, any>;
  output?: Record<string, any>;
  error?: string;
  node_results: Record<string, NodeExecutionResult>;
  started_at: string;
  finished_at?: string;
}

interface ExecutionListItem {
  id: string;
  status: string;
  started_at: string;
  finished_at?: string;
  error?: string;
}

interface WorkflowState {
  // Workflow list
  workflows: WorkflowListItem[];
  isLoadingList: boolean;

  // Current workflow
  workflow: Workflow | null;
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;

  // UI State
  isNodePanelOpen: boolean;
  isPropertiesPanelOpen: boolean;
  isSaving: boolean;
  isExecuting: boolean;
  isLoading: boolean;

  // Execution State
  currentExecution: ExecutionState | null;
  executionHistory: ExecutionListItem[];
  nodeExecutionStatus: Record<string, 'pending' | 'running' | 'success' | 'error'>;

  // Actions - List
  loadWorkflows: () => Promise<void>;
  createWorkflow: (name: string, description?: string) => Promise<string>;
  deleteWorkflow: (id: string) => Promise<void>;

  // Actions - Current workflow
  loadWorkflow: (id: string) => Promise<void>;
  setWorkflow: (workflow: Workflow) => void;
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (nodeDefinition: NodeDefinition, position: { x: number; y: number }) => void;
  updateNodeData: (nodeId: string, data: Partial<any>) => void;
  deleteNode: (nodeId: string) => void;
  selectNode: (nodeId: string | null) => void;
  toggleNodePanel: () => void;
  togglePropertiesPanel: () => void;
  saveWorkflow: () => Promise<void>;
  executeWorkflow: () => Promise<void>;
  clearWorkflow: () => void;

  // Actions - Execution
  loadExecutionHistory: () => Promise<void>;
  pollExecution: (executionId: string) => Promise<void>;
  clearExecution: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  // Initial state
  workflows: [],
  isLoadingList: false,
  workflow: null,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  isNodePanelOpen: true,
  isPropertiesPanelOpen: true,
  isSaving: false,
  isExecuting: false,
  isLoading: false,
  currentExecution: null,
  executionHistory: [],
  nodeExecutionStatus: {},

  // Actions - List
  loadWorkflows: async () => {
    set({ isLoadingList: true });
    try {
      const response = await axios.get(API_BASE);
      set({ workflows: response.data.workflows || [] });
    } catch (error) {
      console.error('Failed to load workflows:', error);
      set({ workflows: [] });
    } finally {
      set({ isLoadingList: false });
    }
  },

  createWorkflow: async (name, description = '') => {
    const response = await axios.post(API_BASE, {
      name,
      description,
      nodes: [],
      connections: [],
    });
    const newWorkflow = response.data.workflow;
    // 목록 새로고침
    get().loadWorkflows();
    return newWorkflow.id;
  },

  deleteWorkflow: async (id) => {
    await axios.delete(`${API_BASE}/${id}`);
    // 목록에서 제거
    set({ workflows: get().workflows.filter((w) => w.id !== id) });
  },

  // Actions - Current workflow
  loadWorkflow: async (id) => {
    set({ isLoading: true });
    try {
      const response = await axios.get(`${API_BASE}/${id}`);
      const workflow = response.data.workflow;

      // API 응답을 Workflow 타입으로 변환
      const convertedWorkflow: Workflow = {
        id: workflow.id,
        name: workflow.name,
        description: workflow.description || '',
        nodes: (workflow.nodes || []).map((n: any) => ({
          id: n.id,
          type: n.type || n.data?.type,
          name: n.name || n.data?.name || n.data?.label,
          position: n.position,
          parameters: n.parameters || n.data?.parameters || {},
        })),
        connections: (workflow.connections || []).map((c: any) => ({
          id: c.id,
          sourceNodeId: c.sourceNodeId || c.source,
          sourcePortId: c.sourcePortId || c.sourceHandle || 'default',
          targetNodeId: c.targetNodeId || c.target,
          targetPortId: c.targetPortId || c.targetHandle || 'default',
        })),
        createdAt: workflow.createdAt,
        updatedAt: workflow.updatedAt,
      };

      get().setWorkflow(convertedWorkflow);
    } catch (error) {
      console.error('Failed to load workflow:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  setWorkflow: (workflow) => {
    // Convert workflow nodes to React Flow nodes
    const nodes: Node[] = workflow.nodes.map((node) => ({
      id: node.id,
      type: 'workflowNode',
      position: node.position,
      data: {
        ...node,
        label: node.name,
      },
    }));

    // Convert workflow connections to React Flow edges
    const edges: Edge[] = workflow.connections.map((conn) => ({
      id: conn.id,
      source: conn.sourceNodeId,
      sourceHandle: conn.sourcePortId,
      target: conn.targetNodeId,
      targetHandle: conn.targetPortId,
      type: 'smoothstep',
      animated: true,
    }));

    set({ workflow, nodes, edges });
  },

  setNodes: (nodes) => set({ nodes }),

  setEdges: (edges) => set({ edges }),

  onNodesChange: (changes) => {
    set({ nodes: applyNodeChanges(changes, get().nodes) });
  },

  onEdgesChange: (changes) => {
    set({ edges: applyEdgeChanges(changes, get().edges) });
  },

  onConnect: (connection) => {
    const newEdge: Edge = {
      id: `edge-${Date.now()}`,
      source: connection.source!,
      sourceHandle: connection.sourceHandle,
      target: connection.target!,
      targetHandle: connection.targetHandle,
      type: 'smoothstep',
      animated: true,
    };
    set({ edges: addEdge(newEdge, get().edges) });
  },

  addNode: (nodeDefinition, position) => {
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: 'workflowNode',
      position,
      data: {
        type: nodeDefinition.type,
        name: nodeDefinition.name,
        label: nodeDefinition.name,
        description: nodeDefinition.description,
        category: nodeDefinition.category,
        icon: nodeDefinition.icon,
        color: nodeDefinition.color,
        inputs: nodeDefinition.inputs,
        outputs: nodeDefinition.outputs,
        parameters: nodeDefinition.parameters.reduce((acc, param) => {
          acc[param.name] = param.default;
          return acc;
        }, {} as Record<string, any>),
      },
    };

    set({ nodes: [...get().nodes, newNode] });
  },

  updateNodeData: (nodeId, data) => {
    set({
      nodes: get().nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
    });
  },

  deleteNode: (nodeId) => {
    set({
      nodes: get().nodes.filter((node) => node.id !== nodeId),
      edges: get().edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
      selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId,
    });
  },

  selectNode: (nodeId) => {
    set({ selectedNodeId: nodeId, isPropertiesPanelOpen: nodeId !== null });
  },

  toggleNodePanel: () => {
    set({ isNodePanelOpen: !get().isNodePanelOpen });
  },

  togglePropertiesPanel: () => {
    set({ isPropertiesPanelOpen: !get().isPropertiesPanelOpen });
  },

  saveWorkflow: async () => {
    const { workflow, nodes, edges } = get();
    if (!workflow) {
      console.error('No workflow to save');
      return;
    }

    set({ isSaving: true });
    try {
      // Convert React Flow nodes/edges back to API format
      const apiNodes = nodes.map((node) => ({
        id: node.id,
        type: node.data.type,
        name: node.data.name || node.data.label,
        position: node.position,
        data: node.data,
        parameters: node.data.parameters || {},
      }));

      const apiConnections = edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        sourceHandle: edge.sourceHandle || 'default',
        target: edge.target,
        targetHandle: edge.targetHandle || 'default',
      }));

      // API 호출
      await axios.put(`${API_BASE}/${workflow.id}`, {
        name: workflow.name,
        description: workflow.description,
        nodes: apiNodes,
        connections: apiConnections,
      });

      console.log('Workflow saved successfully');
    } catch (error) {
      console.error('Failed to save workflow:', error);
      throw error;
    } finally {
      set({ isSaving: false });
    }
  },

  executeWorkflow: async () => {
    const { workflow, nodes } = get();
    if (!workflow) {
      console.error('No workflow to execute');
      return;
    }

    set({ isExecuting: true, nodeExecutionStatus: {} });

    try {
      // 모든 노드를 pending으로 초기화
      const initialStatus: Record<string, 'pending' | 'running' | 'success' | 'error'> = {};
      nodes.forEach((node) => {
        initialStatus[node.id] = 'pending';
      });
      set({ nodeExecutionStatus: initialStatus });

      // 실행 API 호출
      const response = await axios.post(`${API_BASE}/${workflow.id}/execute`, {
        input_data: {},
      });

      const executionId = response.data.execution_id;
      console.log('Workflow execution started:', executionId);

      // 실행 상태 폴링 시작
      await get().pollExecution(executionId);
    } catch (error) {
      console.error('Failed to execute workflow:', error);
      set({ nodeExecutionStatus: {} });
    } finally {
      set({ isExecuting: false });
    }
  },

  clearWorkflow: () => {
    set({
      workflow: null,
      nodes: [],
      edges: [],
      selectedNodeId: null,
      currentExecution: null,
      nodeExecutionStatus: {},
    });
  },

  // Actions - Execution
  loadExecutionHistory: async () => {
    const { workflow } = get();
    if (!workflow) return;

    try {
      const response = await axios.get(`${API_BASE}/${workflow.id}/executions`);
      set({ executionHistory: response.data.executions || [] });
    } catch (error) {
      console.error('Failed to load execution history:', error);
    }
  },

  pollExecution: async (executionId: string) => {
    const maxAttempts = 60;
    let attempts = 0;

    const poll = async (): Promise<void> => {
      try {
        const response = await axios.get(`${API_BASE}/executions/${executionId}`);
        const execution = response.data.execution as ExecutionState;

        set({ currentExecution: execution });

        // 노드 실행 상태 업데이트
        const nodeStatus: Record<string, 'pending' | 'running' | 'success' | 'error'> = {};
        Object.entries(execution.node_results || {}).forEach(([nodeId, result]) => {
          nodeStatus[nodeId] = result.status;
        });
        set({ nodeExecutionStatus: nodeStatus });

        // 실행 완료 여부 확인
        if (execution.status === 'completed' || execution.status === 'failed') {
          console.log('Workflow execution finished:', execution.status);
          // 실행 이력 새로고침
          get().loadExecutionHistory();
          return;
        }

        // 계속 폴링
        attempts++;
        if (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 500));
          return poll();
        }
      } catch (error) {
        console.error('Failed to poll execution:', error);
      }
    };

    await poll();
  },

  clearExecution: () => {
    set({
      currentExecution: null,
      nodeExecutionStatus: {},
    });
  },
}));
