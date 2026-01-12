/**
 * Tests for workflowStore
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useWorkflowStore } from '@/stores/workflowStore';
import axios from 'axios';

// Mock axios
vi.mock('axios');
const mockedAxios = vi.mocked(axios);

describe('workflowStore', () => {
  beforeEach(() => {
    // Reset store state
    useWorkflowStore.setState({
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
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('loadWorkflows', () => {
    it('should load workflows from API', async () => {
      const mockWorkflows = [
        { id: '1', name: 'Workflow 1', description: '', nodeCount: 2 },
        { id: '2', name: 'Workflow 2', description: '', nodeCount: 3 },
      ];

      mockedAxios.get.mockResolvedValueOnce({ data: { workflows: mockWorkflows } });

      await useWorkflowStore.getState().loadWorkflows();

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/workflows');
      expect(useWorkflowStore.getState().workflows).toEqual(mockWorkflows);
      expect(useWorkflowStore.getState().isLoadingList).toBe(false);
    });

    it('should handle API error', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Network error'));

      await useWorkflowStore.getState().loadWorkflows();

      expect(useWorkflowStore.getState().workflows).toEqual([]);
      expect(useWorkflowStore.getState().isLoadingList).toBe(false);
    });
  });

  describe('createWorkflow', () => {
    it('should create a new workflow', async () => {
      const newWorkflow = {
        id: 'new-id',
        name: 'New Workflow',
        description: 'Description',
      };

      mockedAxios.post.mockResolvedValueOnce({ data: { workflow: newWorkflow } });
      mockedAxios.get.mockResolvedValueOnce({ data: { workflows: [newWorkflow] } });

      const id = await useWorkflowStore.getState().createWorkflow('New Workflow', 'Description');

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/workflows', {
        name: 'New Workflow',
        description: 'Description',
        nodes: [],
        connections: [],
      });
      expect(id).toBe('new-id');
    });
  });

  describe('deleteWorkflow', () => {
    it('should delete a workflow', async () => {
      useWorkflowStore.setState({
        workflows: [
          { id: '1', name: 'Workflow 1', description: '', nodeCount: 0, createdAt: '', updatedAt: '' },
          { id: '2', name: 'Workflow 2', description: '', nodeCount: 0, createdAt: '', updatedAt: '' },
        ],
      });

      mockedAxios.delete.mockResolvedValueOnce({ data: { success: true } });

      await useWorkflowStore.getState().deleteWorkflow('1');

      expect(mockedAxios.delete).toHaveBeenCalledWith('/api/workflows/1');
      expect(useWorkflowStore.getState().workflows).toHaveLength(1);
      expect(useWorkflowStore.getState().workflows[0].id).toBe('2');
    });
  });

  describe('node management', () => {
    it('should add a node', () => {
      const nodeDefinition = {
        type: 'llm_agent',
        name: 'LLM Agent',
        description: 'Test',
        category: 'AI',
        icon: '🤖',
        color: '#3b82f6',
        inputs: [],
        outputs: [],
        parameters: [],
      };

      useWorkflowStore.getState().addNode(nodeDefinition, { x: 100, y: 100 });

      const nodes = useWorkflowStore.getState().nodes;
      expect(nodes).toHaveLength(1);
      expect(nodes[0].data.type).toBe('llm_agent');
      expect(nodes[0].position).toEqual({ x: 100, y: 100 });
    });

    it('should delete a node', () => {
      useWorkflowStore.setState({
        nodes: [
          { id: 'node-1', type: 'workflowNode', position: { x: 0, y: 0 }, data: {} },
          { id: 'node-2', type: 'workflowNode', position: { x: 100, y: 0 }, data: {} },
        ],
        edges: [
          { id: 'edge-1', source: 'node-1', target: 'node-2' },
        ],
      });

      useWorkflowStore.getState().deleteNode('node-1');

      expect(useWorkflowStore.getState().nodes).toHaveLength(1);
      expect(useWorkflowStore.getState().edges).toHaveLength(0); // Edge should be removed too
    });

    it('should select a node', () => {
      useWorkflowStore.getState().selectNode('node-123');

      expect(useWorkflowStore.getState().selectedNodeId).toBe('node-123');
      expect(useWorkflowStore.getState().isPropertiesPanelOpen).toBe(true);
    });

    it('should deselect node when null', () => {
      useWorkflowStore.setState({ selectedNodeId: 'node-123' });

      useWorkflowStore.getState().selectNode(null);

      expect(useWorkflowStore.getState().selectedNodeId).toBeNull();
    });
  });

  describe('UI state', () => {
    it('should toggle node panel', () => {
      expect(useWorkflowStore.getState().isNodePanelOpen).toBe(true);

      useWorkflowStore.getState().toggleNodePanel();
      expect(useWorkflowStore.getState().isNodePanelOpen).toBe(false);

      useWorkflowStore.getState().toggleNodePanel();
      expect(useWorkflowStore.getState().isNodePanelOpen).toBe(true);
    });

    it('should toggle properties panel', () => {
      expect(useWorkflowStore.getState().isPropertiesPanelOpen).toBe(true);

      useWorkflowStore.getState().togglePropertiesPanel();
      expect(useWorkflowStore.getState().isPropertiesPanelOpen).toBe(false);
    });
  });

  describe('clearWorkflow', () => {
    it('should clear workflow state', () => {
      useWorkflowStore.setState({
        workflow: { id: '1', name: 'Test', description: '', nodes: [], connections: [], createdAt: '', updatedAt: '' },
        nodes: [{ id: 'n1', type: 'test', position: { x: 0, y: 0 }, data: {} }],
        edges: [{ id: 'e1', source: 'n1', target: 'n2' }],
        selectedNodeId: 'n1',
      });

      useWorkflowStore.getState().clearWorkflow();

      expect(useWorkflowStore.getState().workflow).toBeNull();
      expect(useWorkflowStore.getState().nodes).toEqual([]);
      expect(useWorkflowStore.getState().edges).toEqual([]);
      expect(useWorkflowStore.getState().selectedNodeId).toBeNull();
    });
  });
});
