import React, { useCallback, useMemo, useState, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  NodeTypes,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  Panel,
  MarkerType,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Search, Filter, Download, ZoomIn, ZoomOut } from 'lucide-react';
import type {
  KnowledgeGraph,
  KnowledgeGraphNode,
  KnowledgeGraphEdge,
  GraphLayoutType,
} from '@/types';

// Node colors by type
const NODE_COLORS: Record<string, string> = {
  class: '#3b82f6',
  instance: '#10b981',
  property: '#f59e0b',
  person: '#3b82f6',
  company: '#10b981',
  concept: '#f59e0b',
  location: '#06b6d4',
  event: '#ef4444',
  default: '#6b7280',
};

// Custom node component
const OntologyNode: React.FC<{ data: KnowledgeGraphNode & { selected?: boolean } }> = ({
  data,
}) => {
  const bgColor = NODE_COLORS[data.type] || NODE_COLORS.default;

  return (
    <div
      className={`px-4 py-2 rounded-lg shadow-lg border-2 transition-all duration-200 ${
        data.selected
          ? 'border-white ring-2 ring-primary-500 scale-110'
          : 'border-transparent hover:border-white/30'
      }`}
      style={{ backgroundColor: bgColor }}
    >
      <div className="text-white font-medium text-sm">{data.label}</div>
      <div className="text-white/70 text-xs mt-0.5">{data.type}</div>
    </div>
  );
};

const nodeTypes: NodeTypes = {
  ontology: OntologyNode,
};

// Layout calculation functions
const calculateLayout = (
  nodes: KnowledgeGraphNode[],
  edges: KnowledgeGraphEdge[],
  layout: GraphLayoutType
): Map<string, { x: number; y: number }> => {
  const positions = new Map<string, { x: number; y: number }>();

  switch (layout) {
    case 'hierarchical':
      return calculateHierarchicalLayout(nodes, edges);
    case 'circular':
      return calculateCircularLayout(nodes);
    case 'grid':
      return calculateGridLayout(nodes);
    case 'force':
    default:
      return calculateForceLayout(nodes, edges);
  }
};

const calculateForceLayout = (
  nodes: KnowledgeGraphNode[],
  edges: KnowledgeGraphEdge[]
): Map<string, { x: number; y: number }> => {
  const positions = new Map<string, { x: number; y: number }>();
  const centerX = 400;
  const centerY = 300;

  // Group by type for initial clustering
  const typeGroups = new Map<string, KnowledgeGraphNode[]>();
  nodes.forEach((node) => {
    const group = typeGroups.get(node.type) || [];
    group.push(node);
    typeGroups.set(node.type, group);
  });

  const types = Array.from(typeGroups.keys());
  const typeRadius = 250;

  types.forEach((type, typeIndex) => {
    const typeAngle = (2 * Math.PI * typeIndex) / types.length - Math.PI / 2;
    const typeCenterX = centerX + Math.cos(typeAngle) * typeRadius;
    const typeCenterY = centerY + Math.sin(typeAngle) * typeRadius;

    const nodesInType = typeGroups.get(type) || [];
    const nodeRadius = Math.min(100, 40 + nodesInType.length * 20);

    nodesInType.forEach((node, nodeIndex) => {
      const nodeAngle = (2 * Math.PI * nodeIndex) / nodesInType.length;
      positions.set(node.id, {
        x: typeCenterX + Math.cos(nodeAngle) * nodeRadius,
        y: typeCenterY + Math.sin(nodeAngle) * nodeRadius,
      });
    });
  });

  return positions;
};

const calculateHierarchicalLayout = (
  nodes: KnowledgeGraphNode[],
  edges: KnowledgeGraphEdge[]
): Map<string, { x: number; y: number }> => {
  const positions = new Map<string, { x: number; y: number }>();

  // Find root nodes (no incoming edges)
  const hasIncoming = new Set(edges.map((e) => e.target));
  const roots = nodes.filter((n) => !hasIncoming.has(n.id));

  // BFS to assign levels
  const levels = new Map<string, number>();
  const queue = roots.map((n) => ({ id: n.id, level: 0 }));
  const visited = new Set<string>();

  while (queue.length > 0) {
    const { id, level } = queue.shift()!;
    if (visited.has(id)) continue;
    visited.add(id);
    levels.set(id, level);

    edges
      .filter((e) => e.source === id)
      .forEach((e) => {
        if (!visited.has(e.target)) {
          queue.push({ id: e.target, level: level + 1 });
        }
      });
  }

  // Assign unvisited nodes
  nodes.forEach((n) => {
    if (!levels.has(n.id)) {
      levels.set(n.id, 0);
    }
  });

  // Group by level
  const levelGroups = new Map<number, string[]>();
  levels.forEach((level, id) => {
    const group = levelGroups.get(level) || [];
    group.push(id);
    levelGroups.set(level, group);
  });

  // Position nodes
  const levelHeight = 150;
  const nodeWidth = 200;

  levelGroups.forEach((ids, level) => {
    const y = level * levelHeight + 100;
    const totalWidth = ids.length * nodeWidth;
    const startX = 400 - totalWidth / 2;

    ids.forEach((id, index) => {
      positions.set(id, {
        x: startX + index * nodeWidth + nodeWidth / 2,
        y,
      });
    });
  });

  return positions;
};

const calculateCircularLayout = (
  nodes: KnowledgeGraphNode[]
): Map<string, { x: number; y: number }> => {
  const positions = new Map<string, { x: number; y: number }>();
  const centerX = 400;
  const centerY = 300;
  const radius = Math.min(250, 100 + nodes.length * 15);

  nodes.forEach((node, index) => {
    const angle = (2 * Math.PI * index) / nodes.length - Math.PI / 2;
    positions.set(node.id, {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    });
  });

  return positions;
};

const calculateGridLayout = (
  nodes: KnowledgeGraphNode[]
): Map<string, { x: number; y: number }> => {
  const positions = new Map<string, { x: number; y: number }>();
  const cols = Math.ceil(Math.sqrt(nodes.length));
  const cellWidth = 180;
  const cellHeight = 100;

  nodes.forEach((node, index) => {
    const row = Math.floor(index / cols);
    const col = index % cols;
    positions.set(node.id, {
      x: col * cellWidth + 100,
      y: row * cellHeight + 100,
    });
  });

  return positions;
};

interface KnowledgeGraphViewerProps {
  graph: KnowledgeGraph;
  onNodeSelect?: (node: KnowledgeGraphNode | null) => void;
  onEdgeSelect?: (edge: KnowledgeGraphEdge | null) => void;
  layout?: GraphLayoutType;
  showMiniMap?: boolean;
  showControls?: boolean;
  className?: string;
}

const KnowledgeGraphViewerInner: React.FC<KnowledgeGraphViewerProps> = ({
  graph,
  onNodeSelect,
  onEdgeSelect,
  layout = 'force',
  showMiniMap = true,
  showControls = true,
  className = '',
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string | null>(null);

  // Filter nodes and edges
  const { filteredNodes, filteredEdges, nodeTypes: graphNodeTypes } = useMemo(() => {
    let filtered = graph.nodes;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (n) =>
          n.label.toLowerCase().includes(query) ||
          n.type.toLowerCase().includes(query)
      );
    }
    if (filterType) {
      filtered = filtered.filter((n) => n.type === filterType);
    }

    const filteredNodeIds = new Set(filtered.map((n) => n.id));
    const edges = graph.edges.filter(
      (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
    );
    const types = new Set(graph.nodes.map((n) => n.type));

    return {
      filteredNodes: filtered,
      filteredEdges: edges,
      nodeTypes: Array.from(types),
    };
  }, [graph, searchQuery, filterType]);

  // Calculate positions
  const positions = useMemo(
    () => calculateLayout(filteredNodes, filteredEdges, layout),
    [filteredNodes, filteredEdges, layout]
  );

  // Create ReactFlow nodes
  const flowNodes = useMemo<Node[]>(() => {
    return filteredNodes.map((node) => {
      const pos = positions.get(node.id) || { x: 0, y: 0 };
      return {
        id: node.id,
        type: 'ontology',
        position: pos,
        data: { ...node, selected: node.id === selectedNodeId },
      };
    });
  }, [filteredNodes, positions, selectedNodeId]);

  // Create ReactFlow edges
  const flowEdges = useMemo<Edge[]>(() => {
    return filteredEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label || edge.type,
      type: 'smoothstep',
      animated: edge.source === selectedNodeId || edge.target === selectedNodeId,
      style: {
        stroke:
          edge.source === selectedNodeId || edge.target === selectedNodeId
            ? '#3b82f6'
            : '#64748b',
        strokeWidth: edge.weight ? Math.min(edge.weight, 5) : 1,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color:
          edge.source === selectedNodeId || edge.target === selectedNodeId
            ? '#3b82f6'
            : '#64748b',
      },
      labelStyle: { fill: '#94a3b8', fontSize: 10 },
      labelBgStyle: { fill: '#1e293b', fillOpacity: 0.8 },
    }));
  }, [filteredEdges, selectedNodeId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const newSelectedId = node.id === selectedNodeId ? null : node.id;
      setSelectedNodeId(newSelectedId);
      const kgNode = graph.nodes.find((n) => n.id === node.id);
      onNodeSelect?.(kgNode || null);
    },
    [graph.nodes, onNodeSelect, selectedNodeId]
  );

  const handleEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      const kgEdge = graph.edges.find((e) => e.id === edge.id);
      onEdgeSelect?.(kgEdge || null);
    },
    [graph.edges, onEdgeSelect]
  );

  const handlePaneClick = useCallback(() => {
    setSelectedNodeId(null);
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  const handleExport = useCallback(() => {
    const dataStr = JSON.stringify(graph, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${graph.name || 'knowledge-graph'}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [graph]);

  return (
    <div className={`w-full h-full bg-dark-900 ${className}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={20} />
        {showControls && <Controls />}
        {showMiniMap && (
          <MiniMap
            nodeColor={(node) => NODE_COLORS[node.data.type] || NODE_COLORS.default}
            maskColor="rgba(30, 41, 59, 0.8)"
            style={{ backgroundColor: '#1e293b' }}
          />
        )}

        {/* Search and Filter Panel */}
        <Panel position="top-left" className="flex flex-col gap-2">
          <div className="bg-dark-800 rounded-lg p-3 shadow-lg">
            <div className="flex items-center gap-2 mb-2">
              <Search className="w-4 h-4 text-dark-400" />
              <input
                type="text"
                placeholder="Search nodes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-dark-700 border-none text-sm text-white placeholder-dark-400 rounded px-2 py-1 w-40 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-dark-400" />
              <select
                value={filterType || ''}
                onChange={(e) => setFilterType(e.target.value || null)}
                className="bg-dark-700 border-none text-sm text-white rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary-500"
              >
                <option value="">All Types</option>
                {graphNodeTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Panel>

        {/* Export Button */}
        <Panel position="top-right">
          <button
            onClick={handleExport}
            className="bg-dark-800 hover:bg-dark-700 text-white p-2 rounded-lg shadow-lg transition-colors"
            title="Export Graph"
          >
            <Download className="w-4 h-4" />
          </button>
        </Panel>

        {/* Legend */}
        <Panel position="bottom-left">
          <div className="bg-dark-800 rounded-lg p-3 shadow-lg">
            <div className="text-xs font-medium text-dark-400 mb-2">Node Types</div>
            <div className="flex flex-wrap gap-2">
              {graphNodeTypes.map((type) => (
                <div
                  key={type}
                  className="flex items-center gap-1.5 text-xs cursor-pointer hover:opacity-80"
                  onClick={() => setFilterType(filterType === type ? null : type)}
                >
                  <div
                    className="w-3 h-3 rounded"
                    style={{ backgroundColor: NODE_COLORS[type] || NODE_COLORS.default }}
                  />
                  <span className={filterType === type ? 'text-white' : 'text-dark-400'}>
                    {type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        {/* Stats */}
        <Panel position="bottom-right">
          <div className="bg-dark-800 rounded-lg p-3 shadow-lg text-xs text-dark-400">
            <div>Nodes: {graph.nodes.length}</div>
            <div>Edges: {graph.edges.length}</div>
            {searchQuery && <div>Filtered: {nodes.length} nodes</div>}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

export const KnowledgeGraphViewer: React.FC<KnowledgeGraphViewerProps> = (props) => {
  return (
    <ReactFlowProvider>
      <KnowledgeGraphViewerInner {...props} />
    </ReactFlowProvider>
  );
};

export default KnowledgeGraphViewer;
