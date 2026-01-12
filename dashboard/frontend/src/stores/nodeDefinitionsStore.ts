import { create } from 'zustand';
import type { NodeDefinition } from '@/types';

// Mock node definitions - in production, these would come from the API
const mockNodeDefinitions: NodeDefinition[] = [
  // LangGraph Nodes
  {
    type: 'langgraph.start',
    name: 'Start',
    description: 'Entry point for LangGraph workflow',
    category: 'langgraph',
    icon: 'play',
    color: '#22C55E',
    version: 1,
    inputs: [],
    outputs: [
      { id: 'state', name: 'State', type: 'output', dataType: 'state' },
    ],
    parameters: [
      { name: 'stateSchema', displayName: 'State Schema', type: 'code', default: '{\n  "messages": [],\n  "context": ""\n}' },
    ],
  },
  {
    type: 'langgraph.end',
    name: 'End',
    description: 'Exit point for LangGraph workflow',
    category: 'langgraph',
    icon: 'square',
    color: '#EF4444',
    version: 1,
    inputs: [
      { id: 'state', name: 'State', type: 'input', dataType: 'state', required: true },
    ],
    outputs: [],
    parameters: [],
  },
  {
    type: 'langgraph.agent',
    name: 'Agent Node',
    description: 'LLM-powered agent node with tool calling',
    category: 'langgraph',
    icon: 'bot',
    color: '#8B5CF6',
    version: 1,
    inputs: [
      { id: 'state', name: 'State', type: 'input', dataType: 'state', required: true },
    ],
    outputs: [
      { id: 'state', name: 'State', type: 'output', dataType: 'state' },
      { id: 'tools', name: 'To Tools', type: 'output', dataType: 'state' },
    ],
    parameters: [
      { name: 'name', displayName: 'Node Name', type: 'string', default: 'agent' },
      { name: 'model', displayName: 'Model', type: 'select', default: 'gpt-4', options: [
        { label: 'GPT-4', value: 'gpt-4' },
        { label: 'GPT-4 Turbo', value: 'gpt-4-turbo' },
        { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
        { label: 'Claude 3 Opus', value: 'claude-3-opus' },
        { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet' },
      ]},
      { name: 'systemPrompt', displayName: 'System Prompt', type: 'code', default: 'You are a helpful assistant.' },
      { name: 'temperature', displayName: 'Temperature', type: 'number', default: 0.7 },
    ],
  },
  {
    type: 'langgraph.tool',
    name: 'Tool Node',
    description: 'Execute tools called by agent',
    category: 'langgraph',
    icon: 'wrench',
    color: '#F59E0B',
    version: 1,
    inputs: [
      { id: 'state', name: 'State', type: 'input', dataType: 'state', required: true },
    ],
    outputs: [
      { id: 'state', name: 'State', type: 'output', dataType: 'state' },
    ],
    parameters: [
      { name: 'name', displayName: 'Node Name', type: 'string', default: 'tools' },
      { name: 'tools', displayName: 'Available Tools', type: 'select', default: 'web_search', options: [
        { label: 'Web Search', value: 'web_search' },
        { label: 'Calculator', value: 'calculator' },
        { label: 'Python REPL', value: 'python_repl' },
        { label: 'SQL Query', value: 'sql_query' },
        { label: 'RAG Retriever', value: 'rag_retriever' },
      ]},
    ],
  },
  {
    type: 'langgraph.condition',
    name: 'Conditional Edge',
    description: 'Route based on state conditions',
    category: 'langgraph',
    icon: 'git-branch',
    color: '#EC4899',
    version: 1,
    inputs: [
      { id: 'state', name: 'State', type: 'input', dataType: 'state', required: true },
    ],
    outputs: [
      { id: 'continue', name: 'Continue', type: 'output', dataType: 'state' },
      { id: 'end', name: 'End', type: 'output', dataType: 'state' },
    ],
    parameters: [
      { name: 'condition', displayName: 'Condition Code', type: 'code', default: '# Return "continue" or "end"\nif state.get("should_continue"):\n    return "continue"\nreturn "end"' },
    ],
  },
  {
    type: 'langgraph.subgraph',
    name: 'Subgraph',
    description: 'Nested LangGraph workflow',
    category: 'langgraph',
    icon: 'layers',
    color: '#06B6D4',
    version: 1,
    inputs: [
      { id: 'state', name: 'State', type: 'input', dataType: 'state', required: true },
    ],
    outputs: [
      { id: 'state', name: 'State', type: 'output', dataType: 'state' },
    ],
    parameters: [
      { name: 'name', displayName: 'Subgraph Name', type: 'string', default: 'subgraph' },
      { name: 'graphId', displayName: 'Graph ID', type: 'string', default: '' },
    ],
  },
  {
    type: 'langgraph.human',
    name: 'Human in Loop',
    description: 'Pause for human input/approval',
    category: 'langgraph',
    icon: 'user',
    color: '#3B82F6',
    version: 1,
    inputs: [
      { id: 'state', name: 'State', type: 'input', dataType: 'state', required: true },
    ],
    outputs: [
      { id: 'approved', name: 'Approved', type: 'output', dataType: 'state' },
      { id: 'rejected', name: 'Rejected', type: 'output', dataType: 'state' },
    ],
    parameters: [
      { name: 'name', displayName: 'Node Name', type: 'string', default: 'human_approval' },
      { name: 'message', displayName: 'Prompt Message', type: 'string', default: 'Please review and approve.' },
    ],
  },
  {
    type: 'langgraph.retriever',
    name: 'RAG Retriever',
    description: 'Retrieve context from vector store',
    category: 'langgraph',
    icon: 'search',
    color: '#6366F1',
    version: 1,
    inputs: [
      { id: 'state', name: 'State', type: 'input', dataType: 'state', required: 1 },
    ],
    outputs: [
      { id: 'state', name: 'State', type: 'output', dataType: 'state' },
    ],
    parameters: [
      { name: 'name', displayName: 'Node Name', type: 'string', default: 'retriever' },
      { name: 'vectorStore', displayName: 'Vector Store', type: 'select', default: 'qdrant', options: [
        { label: 'Qdrant', value: 'qdrant' },
        { label: 'Chroma', value: 'chroma' },
        { label: 'Pinecone', value: 'pinecone' },
        { label: 'FAISS', value: 'faiss' },
      ]},
      { name: 'topK', displayName: 'Top K Results', type: 'number', default: 5 },
    ],
  },
  // AI Nodes
  {
    type: 'ai.llm',
    name: 'LLM',
    description: 'Send prompts to Large Language Models',
    category: 'ai',
    icon: 'message-square',
    color: '#10B981',
    version: 1,
    inputs: [
      { id: 'prompt', name: 'Prompt', type: 'input', dataType: 'string', required: true },
      { id: 'context', name: 'Context', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'output', dataType: 'string' },
    ],
    parameters: [
      { name: 'provider', displayName: 'Provider', type: 'select', default: 'openai', options: [
        { label: 'OpenAI', value: 'openai' },
        { label: 'Anthropic', value: 'anthropic' },
      ]},
      { name: 'model', displayName: 'Model', type: 'string', default: 'gpt-4' },
      { name: 'temperature', displayName: 'Temperature', type: 'number', default: 0.7 },
      { name: 'systemPrompt', displayName: 'System Prompt', type: 'code', default: 'You are a helpful assistant.' },
    ],
  },
  {
    type: 'ai.rag',
    name: 'RAG Query',
    description: 'Retrieve documents and generate responses',
    category: 'ai',
    icon: 'search',
    color: '#8B5CF6',
    version: 1,
    inputs: [
      { id: 'query', name: 'Query', type: 'input', dataType: 'string', required: true },
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'output', dataType: 'string' },
      { id: 'sources', name: 'Sources', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'vectorStore', displayName: 'Vector Store', type: 'select', default: 'memory', options: [
        { label: 'In-Memory', value: 'memory' },
        { label: 'Pinecone', value: 'pinecone' },
        { label: 'Chroma', value: 'chroma' },
      ]},
      { name: 'topK', displayName: 'Top K', type: 'number', default: 5 },
    ],
  },
  {
    type: 'ai.agent',
    name: 'AI Agent',
    description: 'Autonomous AI agent with tools',
    category: 'ai',
    icon: 'bot',
    color: '#F59E0B',
    version: 1,
    inputs: [
      { id: 'task', name: 'Task', type: 'input', dataType: 'string', required: true },
      { id: 'tools', name: 'Tools', type: 'input', dataType: 'tool', multiple: true },
    ],
    outputs: [
      { id: 'result', name: 'Result', type: 'output', dataType: 'string' },
      { id: 'steps', name: 'Steps', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'agentType', displayName: 'Agent Type', type: 'select', default: 'react', options: [
        { label: 'ReAct', value: 'react' },
        { label: 'Plan and Execute', value: 'plan-and-execute' },
      ]},
      { name: 'maxIterations', displayName: 'Max Iterations', type: 'number', default: 10 },
    ],
  },
  {
    type: 'knowledge.ontology',
    name: 'Ontology',
    description: 'Knowledge graph operations',
    category: 'knowledge',
    icon: 'share-2',
    color: '#EC4899',
    version: 1,
    inputs: [
      { id: 'data', name: 'Data', type: 'input', dataType: 'any', multiple: true },
      { id: 'query', name: 'Query', type: 'input', dataType: 'string' },
    ],
    outputs: [
      { id: 'graph', name: 'Knowledge Graph', type: 'output', dataType: 'object' },
      { id: 'entities', name: 'Entities', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'extract', options: [
        { label: 'Extract', value: 'extract' },
        { label: 'Build Graph', value: 'build' },
        { label: 'Query', value: 'query' },
      ]},
    ],
  },
  // Input Nodes
  {
    type: 'input.document',
    name: 'Document Loader',
    description: 'Load documents from files or URLs',
    category: 'input',
    icon: 'file-text',
    color: '#3B82F6',
    version: 1,
    inputs: [],
    outputs: [
      { id: 'documents', name: 'Documents', type: 'output', dataType: 'document' },
    ],
    parameters: [
      { name: 'sourceType', displayName: 'Source Type', type: 'select', default: 'file', options: [
        { label: 'File', value: 'file' },
        { label: 'URL', value: 'url' },
        { label: 'Text', value: 'text' },
      ]},
    ],
  },
  // Knowledge Nodes
  {
    type: 'knowledge.vectorstore',
    name: 'Vector Store',
    description: 'Store and query vector embeddings',
    category: 'knowledge',
    icon: 'database',
    color: '#6366F1',
    version: 1,
    inputs: [
      { id: 'documents', name: 'Documents', type: 'input', dataType: 'document', multiple: true },
      { id: 'query', name: 'Query', type: 'input', dataType: 'string' },
    ],
    outputs: [
      { id: 'results', name: 'Results', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'upsert', options: [
        { label: 'Upsert', value: 'upsert' },
        { label: 'Search', value: 'search' },
      ]},
      { name: 'provider', displayName: 'Provider', type: 'select', default: 'memory', options: [
        { label: 'In-Memory', value: 'memory' },
        { label: 'Pinecone', value: 'pinecone' },
        { label: 'Chroma', value: 'chroma' },
      ]},
    ],
  },
  // Control Flow Nodes
  {
    type: 'control.switch',
    name: 'Switch',
    description: 'Route data based on conditions',
    category: 'control',
    icon: 'git-branch',
    color: '#EF4444',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'output0', name: 'Output 1', type: 'output', dataType: 'any' },
      { id: 'output1', name: 'Output 2', type: 'output', dataType: 'any' },
      { id: 'fallback', name: 'Fallback', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'mode', displayName: 'Mode', type: 'select', default: 'rules', options: [
        { label: 'Rules', value: 'rules' },
        { label: 'Expression', value: 'expression' },
      ]},
    ],
  },
  {
    type: 'control.loop',
    name: 'Loop',
    description: 'Iterate over items or repeat until condition',
    category: 'control',
    icon: 'repeat',
    color: '#F97316',
    version: 1,
    inputs: [
      { id: 'items', name: 'Items', type: 'input', dataType: 'array', required: true },
    ],
    outputs: [
      { id: 'item', name: 'Current Item', type: 'output', dataType: 'any' },
      { id: 'index', name: 'Index', type: 'output', dataType: 'number' },
      { id: 'done', name: 'Loop Done', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'mode', displayName: 'Mode', type: 'select', default: 'foreach', options: [
        { label: 'For Each', value: 'foreach' },
        { label: 'While', value: 'while' },
        { label: 'Fixed Count', value: 'count' },
      ]},
      { name: 'maxIterations', displayName: 'Max Iterations', type: 'number', default: 100 },
      { name: 'batchSize', displayName: 'Batch Size', type: 'number', default: 1 },
      { name: 'condition', displayName: 'Condition (for While)', type: 'code', default: '// Return true to continue\nreturn index < items.length;' },
    ],
  },
  {
    type: 'control.loopEnd',
    name: 'Loop End',
    description: 'Mark the end of a loop body',
    category: 'control',
    icon: 'corner-down-left',
    color: '#F97316',
    version: 1,
    inputs: [
      { id: 'result', name: 'Loop Result', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'collected', name: 'Collected Results', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'aggregation', displayName: 'Aggregation', type: 'select', default: 'array', options: [
        { label: 'Collect as Array', value: 'array' },
        { label: 'Merge Objects', value: 'merge' },
        { label: 'Last Value Only', value: 'last' },
      ]},
    ],
  },
  {
    type: 'control.merge',
    name: 'Merge',
    description: 'Combine multiple inputs',
    category: 'control',
    icon: 'git-merge',
    color: '#06B6D4',
    version: 1,
    inputs: [
      { id: 'input1', name: 'Input 1', type: 'input', dataType: 'any', multiple: true },
      { id: 'input2', name: 'Input 2', type: 'input', dataType: 'any', multiple: true },
    ],
    outputs: [
      { id: 'output', name: 'Merged', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'mode', displayName: 'Mode', type: 'select', default: 'append', options: [
        { label: 'Append', value: 'append' },
        { label: 'Combine by Position', value: 'position' },
      ]},
    ],
  },
  {
    type: 'control.wait',
    name: 'Wait',
    description: 'Wait for specified time or condition',
    category: 'control',
    icon: 'clock',
    color: '#64748B',
    version: 1,
    inputs: [
      { id: 'trigger', name: 'Trigger', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'output', name: 'Continue', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'waitType', displayName: 'Wait Type', type: 'select', default: 'time', options: [
        { label: 'Fixed Time', value: 'time' },
        { label: 'Until Condition', value: 'condition' },
        { label: 'External Trigger', value: 'webhook' },
      ]},
      { name: 'duration', displayName: 'Duration (seconds)', type: 'number', default: 5 },
      { name: 'condition', displayName: 'Condition', type: 'code', default: '// Return true when ready\nreturn true;' },
    ],
  },
  {
    type: 'control.parallel',
    name: 'Parallel',
    description: 'Execute branches in parallel',
    category: 'control',
    icon: 'columns',
    color: '#8B5CF6',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'branch1', name: 'Branch 1', type: 'output', dataType: 'any' },
      { id: 'branch2', name: 'Branch 2', type: 'output', dataType: 'any' },
      { id: 'branch3', name: 'Branch 3', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'waitForAll', displayName: 'Wait for All', type: 'boolean', default: true },
      { name: 'timeout', displayName: 'Timeout (seconds)', type: 'number', default: 300 },
    ],
  },
  // Transform Nodes
  {
    type: 'transform.data',
    name: 'Transform',
    description: 'Transform data with code',
    category: 'transform',
    icon: 'shuffle',
    color: '#22C55E',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'output', name: 'Output', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'code', displayName: 'Code', type: 'code', default: 'return item;' },
    ],
  },
  {
    type: 'transform.filter',
    name: 'Filter',
    description: 'Filter items based on condition',
    category: 'transform',
    icon: 'filter',
    color: '#14B8A6',
    version: 1,
    inputs: [
      { id: 'items', name: 'Items', type: 'input', dataType: 'array', required: true },
    ],
    outputs: [
      { id: 'passed', name: 'Passed', type: 'output', dataType: 'array' },
      { id: 'rejected', name: 'Rejected', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'condition', displayName: 'Condition', type: 'code', default: '// Return true to keep item\nreturn item.value > 0;' },
    ],
  },
  {
    type: 'transform.aggregate',
    name: 'Aggregate',
    description: 'Aggregate and summarize data',
    category: 'transform',
    icon: 'layers',
    color: '#0EA5E9',
    version: 1,
    inputs: [
      { id: 'items', name: 'Items', type: 'input', dataType: 'array', required: true },
    ],
    outputs: [
      { id: 'result', name: 'Result', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'sum', options: [
        { label: 'Sum', value: 'sum' },
        { label: 'Average', value: 'avg' },
        { label: 'Count', value: 'count' },
        { label: 'Min', value: 'min' },
        { label: 'Max', value: 'max' },
        { label: 'Group By', value: 'group' },
      ]},
      { name: 'field', displayName: 'Field', type: 'string', default: 'value' },
    ],
  },
  {
    type: 'transform.split',
    name: 'Split',
    description: 'Split text or array into parts',
    category: 'transform',
    icon: 'scissors',
    color: '#F472B6',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'parts', name: 'Parts', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'splitBy', displayName: 'Split By', type: 'string', default: ',' },
      { name: 'limit', displayName: 'Max Parts', type: 'number', default: 0 },
    ],
  },
  // HTTP/API Nodes
  {
    type: 'http.request',
    name: 'HTTP Request',
    description: 'Make HTTP API calls',
    category: 'http',
    icon: 'globe',
    color: '#6366F1',
    version: 1,
    inputs: [
      { id: 'trigger', name: 'Trigger', type: 'input', dataType: 'any' },
      { id: 'body', name: 'Body', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'output', dataType: 'any' },
      { id: 'error', name: 'Error', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'method', displayName: 'Method', type: 'select', default: 'GET', options: [
        { label: 'GET', value: 'GET' },
        { label: 'POST', value: 'POST' },
        { label: 'PUT', value: 'PUT' },
        { label: 'DELETE', value: 'DELETE' },
        { label: 'PATCH', value: 'PATCH' },
      ]},
      { name: 'url', displayName: 'URL', type: 'string', default: 'https://api.example.com' },
      { name: 'headers', displayName: 'Headers', type: 'code', default: '{\n  "Content-Type": "application/json"\n}' },
      { name: 'timeout', displayName: 'Timeout (ms)', type: 'number', default: 30000 },
    ],
  },
  {
    type: 'http.webhook',
    name: 'Webhook Trigger',
    description: 'Trigger workflow via webhook',
    category: 'http',
    icon: 'webhook',
    color: '#8B5CF6',
    version: 1,
    inputs: [],
    outputs: [
      { id: 'body', name: 'Body', type: 'output', dataType: 'any' },
      { id: 'headers', name: 'Headers', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'path', displayName: 'Path', type: 'string', default: '/webhook/trigger' },
      { name: 'method', displayName: 'Method', type: 'select', default: 'POST', options: [
        { label: 'POST', value: 'POST' },
        { label: 'GET', value: 'GET' },
      ]},
      { name: 'authentication', displayName: 'Authentication', type: 'select', default: 'none', options: [
        { label: 'None', value: 'none' },
        { label: 'API Key', value: 'apikey' },
        { label: 'Basic Auth', value: 'basic' },
      ]},
    ],
  },
  // Data Storage Nodes
  {
    type: 'data.cache',
    name: 'Cache',
    description: 'Cache data with TTL',
    category: 'data',
    icon: 'hard-drive',
    color: '#F59E0B',
    version: 1,
    inputs: [
      { id: 'data', name: 'Data', type: 'input', dataType: 'any' },
      { id: 'key', name: 'Key', type: 'input', dataType: 'string' },
    ],
    outputs: [
      { id: 'cached', name: 'Cached Data', type: 'output', dataType: 'any' },
      { id: 'hit', name: 'Cache Hit', type: 'output', dataType: 'boolean' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'get', options: [
        { label: 'Get', value: 'get' },
        { label: 'Set', value: 'set' },
        { label: 'Delete', value: 'delete' },
      ]},
      { name: 'ttl', displayName: 'TTL (seconds)', type: 'number', default: 3600 },
    ],
  },
  {
    type: 'data.variable',
    name: 'Set Variable',
    description: 'Store and retrieve workflow variables',
    category: 'data',
    icon: 'variable',
    color: '#84CC16',
    version: 1,
    inputs: [
      { id: 'value', name: 'Value', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'output', name: 'Output', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'name', displayName: 'Variable Name', type: 'string', default: 'myVariable' },
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'set', options: [
        { label: 'Set', value: 'set' },
        { label: 'Get', value: 'get' },
        { label: 'Increment', value: 'increment' },
        { label: 'Append', value: 'append' },
      ]},
    ],
  },
  // Text Processing Nodes
  {
    type: 'text.template',
    name: 'Text Template',
    description: 'Generate text from template',
    category: 'text',
    icon: 'file-text',
    color: '#64748B',
    version: 1,
    inputs: [
      { id: 'data', name: 'Data', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'text', name: 'Text', type: 'output', dataType: 'string' },
    ],
    parameters: [
      { name: 'template', displayName: 'Template', type: 'code', default: 'Hello {{name}}, your order #{{orderId}} is ready.' },
    ],
  },
  {
    type: 'text.regex',
    name: 'Regex',
    description: 'Extract or replace with regex',
    category: 'text',
    icon: 'regex',
    color: '#EC4899',
    version: 1,
    inputs: [
      { id: 'text', name: 'Text', type: 'input', dataType: 'string', required: true },
    ],
    outputs: [
      { id: 'matches', name: 'Matches', type: 'output', dataType: 'array' },
      { id: 'result', name: 'Result', type: 'output', dataType: 'string' },
    ],
    parameters: [
      { name: 'pattern', displayName: 'Pattern', type: 'string', default: '\\d+' },
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'match', options: [
        { label: 'Match', value: 'match' },
        { label: 'Replace', value: 'replace' },
        { label: 'Split', value: 'split' },
        { label: 'Test', value: 'test' },
      ]},
      { name: 'replacement', displayName: 'Replacement', type: 'string', default: '' },
      { name: 'flags', displayName: 'Flags', type: 'string', default: 'g' },
    ],
  },
  // Error Handling
  {
    type: 'error.catch',
    name: 'Error Catch',
    description: 'Catch and handle errors',
    category: 'control',
    icon: 'shield',
    color: '#DC2626',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'success', name: 'Success', type: 'output', dataType: 'any' },
      { id: 'error', name: 'Error', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'retries', displayName: 'Retries', type: 'number', default: 3 },
      { name: 'retryDelay', displayName: 'Retry Delay (ms)', type: 'number', default: 1000 },
    ],
  },
  {
    type: 'error.throw',
    name: 'Throw Error',
    description: 'Throw custom error',
    category: 'control',
    icon: 'alert-triangle',
    color: '#EF4444',
    version: 1,
    inputs: [
      { id: 'trigger', name: 'Trigger', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [],
    parameters: [
      { name: 'message', displayName: 'Error Message', type: 'string', default: 'Custom error occurred' },
      { name: 'code', displayName: 'Error Code', type: 'string', default: 'CUSTOM_ERROR' },
    ],
  },
  // Debug/Utility
  {
    type: 'util.log',
    name: 'Log',
    description: 'Log data for debugging',
    category: 'utility',
    icon: 'terminal',
    color: '#71717A',
    version: 1,
    inputs: [
      { id: 'data', name: 'Data', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'passthrough', name: 'Passthrough', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'level', displayName: 'Log Level', type: 'select', default: 'info', options: [
        { label: 'Debug', value: 'debug' },
        { label: 'Info', value: 'info' },
        { label: 'Warning', value: 'warn' },
        { label: 'Error', value: 'error' },
      ]},
      { name: 'message', displayName: 'Message', type: 'string', default: '' },
    ],
  },
  {
    type: 'util.delay',
    name: 'Delay',
    description: 'Add delay between operations',
    category: 'utility',
    icon: 'timer',
    color: '#A855F7',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'output', name: 'Output', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'delay', displayName: 'Delay (ms)', type: 'number', default: 1000 },
      { name: 'jitter', displayName: 'Random Jitter (ms)', type: 'number', default: 0 },
    ],
  },
  {
    type: 'util.manual',
    name: 'Manual Trigger',
    description: 'Manually trigger workflow',
    category: 'utility',
    icon: 'play-circle',
    color: '#22C55E',
    version: 1,
    inputs: [],
    outputs: [
      { id: 'output', name: 'Output', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'data', displayName: 'Test Data', type: 'code', default: '{\n  "test": true\n}' },
    ],
  },
  // Schedule Trigger
  {
    type: 'trigger.schedule',
    name: 'Schedule',
    description: 'Trigger on schedule (cron)',
    category: 'trigger',
    icon: 'calendar',
    color: '#0891B2',
    version: 1,
    inputs: [],
    outputs: [
      { id: 'trigger', name: 'Trigger', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'cron', displayName: 'Cron Expression', type: 'string', default: '0 0 * * *' },
      { name: 'timezone', displayName: 'Timezone', type: 'string', default: 'Asia/Seoul' },
    ],
  },
  // Database Nodes (n8n style)
  {
    type: 'db.postgres',
    name: 'PostgreSQL',
    description: 'Execute PostgreSQL queries',
    category: 'database',
    icon: 'database',
    color: '#336791',
    version: 1,
    inputs: [
      { id: 'trigger', name: 'Trigger', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'results', name: 'Results', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'executeQuery', options: [
        { label: 'Execute Query', value: 'executeQuery' },
        { label: 'Insert', value: 'insert' },
        { label: 'Update', value: 'update' },
        { label: 'Delete', value: 'delete' },
      ]},
      { name: 'query', displayName: 'Query', type: 'code', default: 'SELECT * FROM users LIMIT 10' },
      { name: 'host', displayName: 'Host', type: 'string', default: 'localhost' },
      { name: 'port', displayName: 'Port', type: 'number', default: 5432 },
      { name: 'database', displayName: 'Database', type: 'string', default: 'postgres' },
    ],
  },
  {
    type: 'db.mongodb',
    name: 'MongoDB',
    description: 'MongoDB database operations',
    category: 'database',
    icon: 'database',
    color: '#13AA52',
    version: 1,
    inputs: [
      { id: 'trigger', name: 'Trigger', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'results', name: 'Results', type: 'output', dataType: 'array' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'find', options: [
        { label: 'Find', value: 'find' },
        { label: 'Insert', value: 'insert' },
        { label: 'Update', value: 'update' },
        { label: 'Delete', value: 'delete' },
        { label: 'Aggregate', value: 'aggregate' },
      ]},
      { name: 'collection', displayName: 'Collection', type: 'string', default: 'collection' },
      { name: 'query', displayName: 'Query', type: 'code', default: '{}' },
    ],
  },
  {
    type: 'db.redis',
    name: 'Redis',
    description: 'Redis key-value operations',
    category: 'database',
    icon: 'database',
    color: '#DC382D',
    version: 1,
    inputs: [
      { id: 'trigger', name: 'Trigger', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'result', name: 'Result', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'get', options: [
        { label: 'Get', value: 'get' },
        { label: 'Set', value: 'set' },
        { label: 'Delete', value: 'del' },
        { label: 'Increment', value: 'incr' },
        { label: 'Push to List', value: 'lpush' },
      ]},
      { name: 'key', displayName: 'Key', type: 'string', default: 'mykey' },
      { name: 'value', displayName: 'Value', type: 'code', default: '' },
      { name: 'ttl', displayName: 'TTL (seconds)', type: 'number', default: 0 },
    ],
  },
  // Communication Nodes
  {
    type: 'comm.slack',
    name: 'Slack',
    description: 'Send messages to Slack',
    category: 'communication',
    icon: 'message-circle',
    color: '#4A154B',
    version: 1,
    inputs: [
      { id: 'message', name: 'Message', type: 'input', dataType: 'string', required: true },
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'postMessage', options: [
        { label: 'Post Message', value: 'postMessage' },
        { label: 'Update Message', value: 'updateMessage' },
        { label: 'Get Channel', value: 'getChannel' },
      ]},
      { name: 'channel', displayName: 'Channel', type: 'string', default: '#general' },
      { name: 'username', displayName: 'Bot Name', type: 'string', default: 'Bot' },
    ],
  },
  {
    type: 'comm.email',
    name: 'Email Send',
    description: 'Send emails via SMTP',
    category: 'communication',
    icon: 'mail',
    color: '#EA4335',
    version: 1,
    inputs: [
      { id: 'trigger', name: 'Trigger', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'result', name: 'Result', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'to', displayName: 'To', type: 'string', default: 'user@example.com' },
      { name: 'subject', displayName: 'Subject', type: 'string', default: 'Email Subject' },
      { name: 'body', displayName: 'Body', type: 'code', default: 'Email body content' },
      { name: 'isHTML', displayName: 'HTML Email', type: 'boolean', default: false },
    ],
  },
  {
    type: 'comm.discord',
    name: 'Discord',
    description: 'Send messages to Discord',
    category: 'communication',
    icon: 'message-square',
    color: '#5865F2',
    version: 1,
    inputs: [
      { id: 'message', name: 'Message', type: 'input', dataType: 'string', required: true },
    ],
    outputs: [
      { id: 'response', name: 'Response', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'webhookUrl', displayName: 'Webhook URL', type: 'string', default: '' },
      { name: 'username', displayName: 'Bot Name', type: 'string', default: 'Bot' },
    ],
  },
  // File Nodes
  {
    type: 'file.read',
    name: 'Read File',
    description: 'Read file from filesystem or URL',
    category: 'file',
    icon: 'file',
    color: '#6366F1',
    version: 1,
    inputs: [
      { id: 'trigger', name: 'Trigger', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'data', name: 'File Data', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'filePath', displayName: 'File Path', type: 'string', default: '/path/to/file.txt' },
      { name: 'format', displayName: 'Format', type: 'select', default: 'text', options: [
        { label: 'Text', value: 'text' },
        { label: 'JSON', value: 'json' },
        { label: 'CSV', value: 'csv' },
        { label: 'Binary', value: 'binary' },
      ]},
    ],
  },
  {
    type: 'file.write',
    name: 'Write File',
    description: 'Write data to file',
    category: 'file',
    icon: 'file-plus',
    color: '#10B981',
    version: 1,
    inputs: [
      { id: 'data', name: 'Data', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'result', name: 'Result', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'filePath', displayName: 'File Path', type: 'string', default: '/path/to/output.txt' },
      { name: 'format', displayName: 'Format', type: 'select', default: 'text', options: [
        { label: 'Text', value: 'text' },
        { label: 'JSON', value: 'json' },
        { label: 'CSV', value: 'csv' },
      ]},
      { name: 'append', displayName: 'Append Mode', type: 'boolean', default: false },
    ],
  },
  {
    type: 'file.csv',
    name: 'CSV Parser',
    description: 'Parse and generate CSV',
    category: 'file',
    icon: 'file-spreadsheet',
    color: '#22C55E',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'output', name: 'Output', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'parse', options: [
        { label: 'Parse CSV to JSON', value: 'parse' },
        { label: 'Generate CSV from JSON', value: 'generate' },
      ]},
      { name: 'delimiter', displayName: 'Delimiter', type: 'string', default: ',' },
      { name: 'hasHeader', displayName: 'Has Header', type: 'boolean', default: true },
    ],
  },
  // Crypto/Hash Nodes
  {
    type: 'crypto.hash',
    name: 'Hash',
    description: 'Generate cryptographic hashes',
    category: 'crypto',
    icon: 'lock',
    color: '#7C3AED',
    version: 1,
    inputs: [
      { id: 'data', name: 'Data', type: 'input', dataType: 'string', required: true },
    ],
    outputs: [
      { id: 'hash', name: 'Hash', type: 'output', dataType: 'string' },
    ],
    parameters: [
      { name: 'algorithm', displayName: 'Algorithm', type: 'select', default: 'sha256', options: [
        { label: 'SHA-256', value: 'sha256' },
        { label: 'SHA-512', value: 'sha512' },
        { label: 'MD5', value: 'md5' },
        { label: 'SHA-1', value: 'sha1' },
      ]},
      { name: 'encoding', displayName: 'Encoding', type: 'select', default: 'hex', options: [
        { label: 'Hex', value: 'hex' },
        { label: 'Base64', value: 'base64' },
      ]},
    ],
  },
  {
    type: 'crypto.jwt',
    name: 'JWT',
    description: 'Create and verify JWT tokens',
    category: 'crypto',
    icon: 'key',
    color: '#EC4899',
    version: 1,
    inputs: [
      { id: 'data', name: 'Payload', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'result', name: 'Result', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'sign', options: [
        { label: 'Sign', value: 'sign' },
        { label: 'Verify', value: 'verify' },
        { label: 'Decode', value: 'decode' },
      ]},
      { name: 'algorithm', displayName: 'Algorithm', type: 'select', default: 'HS256', options: [
        { label: 'HS256', value: 'HS256' },
        { label: 'RS256', value: 'RS256' },
      ]},
      { name: 'secret', displayName: 'Secret', type: 'string', default: '' },
    ],
  },
  // JSON/XML Nodes
  {
    type: 'data.json',
    name: 'JSON',
    description: 'Parse and manipulate JSON',
    category: 'data',
    icon: 'braces',
    color: '#F59E0B',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'output', name: 'Output', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'parse', options: [
        { label: 'Parse', value: 'parse' },
        { label: 'Stringify', value: 'stringify' },
        { label: 'Extract Path', value: 'extract' },
      ]},
      { name: 'path', displayName: 'JSON Path', type: 'string', default: '$.data' },
      { name: 'pretty', displayName: 'Pretty Print', type: 'boolean', default: true },
    ],
  },
  {
    type: 'data.xml',
    name: 'XML',
    description: 'Parse and generate XML',
    category: 'data',
    icon: 'code',
    color: '#EF4444',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'output', name: 'Output', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'parse', options: [
        { label: 'XML to JSON', value: 'parse' },
        { label: 'JSON to XML', value: 'generate' },
      ]},
      { name: 'rootElement', displayName: 'Root Element', type: 'string', default: 'root' },
    ],
  },
  // Date/Time Nodes
  {
    type: 'util.datetime',
    name: 'Date & Time',
    description: 'Format and manipulate dates',
    category: 'utility',
    icon: 'calendar-clock',
    color: '#0891B2',
    version: 1,
    inputs: [
      { id: 'date', name: 'Date', type: 'input', dataType: 'any' },
    ],
    outputs: [
      { id: 'result', name: 'Result', type: 'output', dataType: 'string' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'format', options: [
        { label: 'Format', value: 'format' },
        { label: 'Add Time', value: 'add' },
        { label: 'Subtract Time', value: 'subtract' },
        { label: 'Diff', value: 'diff' },
      ]},
      { name: 'format', displayName: 'Format', type: 'string', default: 'YYYY-MM-DD HH:mm:ss' },
      { name: 'timezone', displayName: 'Timezone', type: 'string', default: 'Asia/Seoul' },
    ],
  },
  // Comparison/Math Nodes
  {
    type: 'util.compare',
    name: 'Compare',
    description: 'Compare values',
    category: 'utility',
    icon: 'equal',
    color: '#64748B',
    version: 1,
    inputs: [
      { id: 'value1', name: 'Value 1', type: 'input', dataType: 'any', required: true },
      { id: 'value2', name: 'Value 2', type: 'input', dataType: 'any', required: true },
    ],
    outputs: [
      { id: 'true', name: 'True', type: 'output', dataType: 'any' },
      { id: 'false', name: 'False', type: 'output', dataType: 'any' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'equal', options: [
        { label: 'Equal', value: 'equal' },
        { label: 'Not Equal', value: 'notEqual' },
        { label: 'Greater Than', value: 'greaterThan' },
        { label: 'Less Than', value: 'lessThan' },
        { label: 'Contains', value: 'contains' },
        { label: 'Regex Match', value: 'regex' },
      ]},
    ],
  },
  {
    type: 'util.math',
    name: 'Math',
    description: 'Mathematical operations',
    category: 'utility',
    icon: 'calculator',
    color: '#3B82F6',
    version: 1,
    inputs: [
      { id: 'input', name: 'Input', type: 'input', dataType: 'number', required: true },
    ],
    outputs: [
      { id: 'result', name: 'Result', type: 'output', dataType: 'number' },
    ],
    parameters: [
      { name: 'operation', displayName: 'Operation', type: 'select', default: 'add', options: [
        { label: 'Add', value: 'add' },
        { label: 'Subtract', value: 'subtract' },
        { label: 'Multiply', value: 'multiply' },
        { label: 'Divide', value: 'divide' },
        { label: 'Round', value: 'round' },
        { label: 'Ceil', value: 'ceil' },
        { label: 'Floor', value: 'floor' },
        { label: 'Random', value: 'random' },
      ]},
      { name: 'value', displayName: 'Value', type: 'number', default: 0 },
    ],
  },
];

const categories = [
  { id: 'langgraph', name: 'LangGraph', icon: 'workflow' },
  { id: 'ai', name: 'AI', icon: 'brain' },
  { id: 'knowledge', name: 'Knowledge', icon: 'database' },
  { id: 'database', name: 'Database', icon: 'database' },
  { id: 'communication', name: 'Communication', icon: 'message-circle' },
  { id: 'file', name: 'Files', icon: 'file' },
  { id: 'crypto', name: 'Crypto', icon: 'lock' },
  { id: 'control', name: 'Control Flow', icon: 'git-branch' },
  { id: 'transform', name: 'Transform', icon: 'shuffle' },
  { id: 'http', name: 'HTTP/API', icon: 'globe' },
  { id: 'data', name: 'Data', icon: 'hard-drive' },
  { id: 'text', name: 'Text', icon: 'file-text' },
  { id: 'trigger', name: 'Triggers', icon: 'zap' },
  { id: 'utility', name: 'Utility', icon: 'settings' },
  { id: 'input', name: 'Input', icon: 'download' },
  { id: 'output', name: 'Output', icon: 'upload' },
];

interface NodeDefinitionsState {
  nodeDefinitions: NodeDefinition[];
  categories: typeof categories;
  searchQuery: string;
  selectedCategory: string | null;

  // Actions
  setSearchQuery: (query: string) => void;
  setSelectedCategory: (category: string | null) => void;
  getFilteredNodes: () => NodeDefinition[];
  getNodeDefinition: (type: string) => NodeDefinition | undefined;
}

export const useNodeDefinitionsStore = create<NodeDefinitionsState>((set, get) => ({
  nodeDefinitions: mockNodeDefinitions,
  categories,
  searchQuery: '',
  selectedCategory: null,

  setSearchQuery: (query) => set({ searchQuery: query }),

  setSelectedCategory: (category) => set({ selectedCategory: category }),

  getFilteredNodes: () => {
    const { nodeDefinitions, searchQuery, selectedCategory } = get();

    return nodeDefinitions.filter((node) => {
      const matchesSearch =
        searchQuery === '' ||
        node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory =
        selectedCategory === null || node.category === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  },

  getNodeDefinition: (type) => {
    return get().nodeDefinitions.find((n) => n.type === type);
  },
}));
