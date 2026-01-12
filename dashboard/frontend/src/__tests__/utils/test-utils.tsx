/**
 * Test utilities and custom render functions
 */
import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';

/**
 * Custom render function that includes common providers
 */
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  route?: string;
}

function AllProviders({ children }: { children: React.ReactNode }) {
  return (
    <BrowserRouter>
      {children}
    </BrowserRouter>
  );
}

function customRender(
  ui: ReactElement,
  options?: CustomRenderOptions
) {
  const { route = '/', ...renderOptions } = options || {};

  // Set the route
  window.history.pushState({}, 'Test page', route);

  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper: AllProviders, ...renderOptions }),
  };
}

// Re-export everything
export * from '@testing-library/react';
export { customRender as render, userEvent };

/**
 * Wait for async operations
 */
export const waitForAsync = () => new Promise((resolve) => setTimeout(resolve, 0));

/**
 * Mock API response helper
 */
export function createMockResponse<T>(data: T, status = 200) {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {},
  };
}

/**
 * Sample test data factories
 */
export const mockWorkflow = {
  id: 'test-workflow-1',
  name: 'Test Workflow',
  description: 'A test workflow',
  nodes: [
    {
      id: 'node-1',
      type: 'llm_agent',
      name: 'LLM Agent',
      position: { x: 100, y: 100 },
      parameters: { model: 'gpt-4' },
    },
  ],
  connections: [],
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

export const mockWorkflowList = [
  {
    id: 'workflow-1',
    name: 'Workflow 1',
    description: 'First workflow',
    nodeCount: 3,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-02T00:00:00Z',
  },
  {
    id: 'workflow-2',
    name: 'Workflow 2',
    description: 'Second workflow',
    nodeCount: 5,
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-03T00:00:00Z',
  },
];
