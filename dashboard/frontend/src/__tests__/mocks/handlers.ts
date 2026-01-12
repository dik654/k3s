/**
 * MSW (Mock Service Worker) handlers for API mocking
 */
import { http, HttpResponse } from 'msw';

// Sample data
const workflows = new Map();

export const handlers = [
  // Health check
  http.get('/api/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      service: 'k3s-dashboard',
    });
  }),

  // List workflows
  http.get('/api/workflows', () => {
    const workflowList = Array.from(workflows.values()).map((w: any) => ({
      id: w.id,
      name: w.name,
      description: w.description,
      nodeCount: w.nodes?.length || 0,
      createdAt: w.createdAt,
      updatedAt: w.updatedAt,
    }));

    return HttpResponse.json({ workflows: workflowList });
  }),

  // Get workflow by ID
  http.get('/api/workflows/:id', ({ params }) => {
    const { id } = params;
    const workflow = workflows.get(id);

    if (!workflow) {
      return HttpResponse.json(
        { detail: 'Workflow not found' },
        { status: 404 }
      );
    }

    return HttpResponse.json({ workflow });
  }),

  // Create workflow
  http.post('/api/workflows', async ({ request }) => {
    const body = await request.json() as any;
    const id = `workflow-${Date.now()}`;
    const now = new Date().toISOString();

    const workflow = {
      id,
      name: body.name,
      description: body.description || '',
      nodes: body.nodes || [],
      connections: body.connections || [],
      createdAt: now,
      updatedAt: now,
    };

    workflows.set(id, workflow);

    return HttpResponse.json({ success: true, workflow });
  }),

  // Update workflow
  http.put('/api/workflows/:id', async ({ params, request }) => {
    const { id } = params;
    const body = await request.json() as any;
    const workflow = workflows.get(id);

    if (!workflow) {
      return HttpResponse.json(
        { detail: 'Workflow not found' },
        { status: 404 }
      );
    }

    const updated = {
      ...workflow,
      ...body,
      updatedAt: new Date().toISOString(),
    };

    workflows.set(id as string, updated);

    return HttpResponse.json({ success: true, workflow: updated });
  }),

  // Delete workflow
  http.delete('/api/workflows/:id', ({ params }) => {
    const { id } = params;

    if (!workflows.has(id)) {
      return HttpResponse.json(
        { detail: 'Workflow not found' },
        { status: 404 }
      );
    }

    workflows.delete(id as string);

    return HttpResponse.json({ success: true, message: `Workflow ${id} deleted` });
  }),

  // Cluster status (mock)
  http.get('/api/cluster/status', () => {
    return HttpResponse.json({
      status: 'healthy',
      nodes: { ready: 3, total: 3 },
      pods: { running: 25, total: 30, pending: 3, failed: 2 },
    });
  }),
];

// Helper to reset mock data
export function resetMockData() {
  workflows.clear();
}

// Helper to seed mock data
export function seedWorkflows(data: any[]) {
  data.forEach((w) => workflows.set(w.id, w));
}
