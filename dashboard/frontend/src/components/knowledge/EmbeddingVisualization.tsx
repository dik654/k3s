import React, { useCallback, useMemo, useState, useEffect, useRef } from 'react';
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
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Search,
  Filter,
  Download,
  Info,
  Play,
  Pause,
} from 'lucide-react';
import type {
  KnowledgeGraph,
  KnowledgeGraphNode,
  KnowledgeGraphEdge,
} from '@/types';

// Custom node component for embedding visualization
const EmbeddingNode: React.FC<{ data: KnowledgeGraphNode & { selected?: boolean } }> = ({
  data,
}) => {
  const nodeColors: Record<string, string> = {
    person: '#3b82f6',
    company: '#10b981',
    entity: '#8b5cf6',
    concept: '#f59e0b',
    event: '#ef4444',
    location: '#06b6d4',
    default: '#6b7280',
  };

  const bgColor = nodeColors[data.type] || nodeColors.default;

  return (
    <div
      className={`px-4 py-2 rounded-lg shadow-lg border-2 transition-all duration-200 hover:scale-105 ${
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
  embedding: EmbeddingNode,
};

// Physics simulation parameters
const PHYSICS_CONFIG = {
  repulsion: 5000,
  attraction: 0.03,
  damping: 0.45,
  idealDistance: 150,
  centerGravity: 0.008,
  maxVelocity: 8,
  velocityThreshold: 0.8,
};

interface NodePhysics {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface EmbeddingVisualizationProps {
  graph: KnowledgeGraph;
  onNodeSelect?: (node: KnowledgeGraphNode | null) => void;
  onEdgeSelect?: (edge: KnowledgeGraphEdge | null) => void;
  showMiniMap?: boolean;
  showControls?: boolean;
  className?: string;
}

const EmbeddingVisualizationInner: React.FC<EmbeddingVisualizationProps> = ({
  graph,
  onNodeSelect,
  onEdgeSelect,
  showMiniMap = true,
  showControls = true,
  className = '',
}) => {
  const reactFlowInstance = useReactFlow();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string | null>(null);
  const [isSimulationRunning, setIsSimulationRunning] = useState(true);

  const physicsRef = useRef<Map<string, NodePhysics>>(new Map());
  const animationFrameRef = useRef<number | undefined>(undefined);
  const draggedNodeRef = useRef<string | null>(null);

  // Calculate initial positions - cluster by type
  const calculateInitialPositions = useCallback(
    (nodes: KnowledgeGraphNode[]) => {
      const positions = new Map<string, { x: number; y: number }>();
      const centerX = 400;
      const centerY = 300;

      const typeGroups = new Map<string, KnowledgeGraphNode[]>();
      nodes.forEach((node) => {
        const group = typeGroups.get(node.type) || [];
        group.push(node);
        typeGroups.set(node.type, group);
      });

      const types = Array.from(typeGroups.keys());
      const typeRadius = 200;

      types.forEach((type, typeIndex) => {
        const typeAngle = (2 * Math.PI * typeIndex) / types.length - Math.PI / 2;
        const typeCenterX = centerX + Math.cos(typeAngle) * typeRadius;
        const typeCenterY = centerY + Math.sin(typeAngle) * typeRadius;

        const nodesInType = typeGroups.get(type) || [];
        const nodeRadius = Math.min(80, 30 + nodesInType.length * 15);

        nodesInType.forEach((node, nodeIndex) => {
          const nodeAngle = (2 * Math.PI * nodeIndex) / nodesInType.length;
          positions.set(node.id, {
            x: typeCenterX + Math.cos(nodeAngle) * nodeRadius,
            y: typeCenterY + Math.sin(nodeAngle) * nodeRadius,
          });
        });
      });

      return positions;
    },
    []
  );

  // Filter nodes and edges
  const { filteredNodes, filteredEdges, graphNodeTypes } = useMemo(() => {
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
      graphNodeTypes: Array.from(types),
    };
  }, [graph, searchQuery, filterType]);

  // Initialize physics state
  useEffect(() => {
    const positions = calculateInitialPositions(filteredNodes);
    const newPhysics = new Map<string, NodePhysics>();

    filteredNodes.forEach((node) => {
      const pos = positions.get(node.id) || { x: 400, y: 300 };
      const existing = physicsRef.current.get(node.id);
      newPhysics.set(node.id, {
        x: existing?.x ?? pos.x,
        y: existing?.y ?? pos.y,
        vx: existing?.vx ?? 0,
        vy: existing?.vy ?? 0,
      });
    });

    physicsRef.current = newPhysics;
  }, [filteredNodes, calculateInitialPositions]);

  // Create ReactFlow nodes from physics state
  const createNodesFromPhysics = useCallback(() => {
    return filteredNodes.map((node) => {
      const physics = physicsRef.current.get(node.id);
      return {
        id: node.id,
        type: 'embedding',
        position: physics ? { x: physics.x, y: physics.y } : { x: 0, y: 0 },
        data: { ...node, selected: node.id === selectedNodeId },
      };
    });
  }, [filteredNodes, selectedNodeId]);

  // Create edges
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

  const [nodes, setNodes, onNodesChange] = useNodesState(createNodesFromPhysics());
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  useEffect(() => {
    setEdges(flowEdges);
  }, [flowEdges, setEdges]);

  // Physics simulation step
  const simulationStep = useCallback(() => {
    if (!isSimulationRunning) return;

    const physics = physicsRef.current;
    const { repulsion, damping, idealDistance, centerGravity, maxVelocity, velocityThreshold } = PHYSICS_CONFIG;

    filteredNodes.forEach((node1) => {
      const p1 = physics.get(node1.id);
      if (!p1 || draggedNodeRef.current === node1.id) return;

      let fx = 0;
      let fy = 0;

      // Repulsion from other nodes
      filteredNodes.forEach((node2) => {
        if (node1.id === node2.id) return;
        const p2 = physics.get(node2.id);
        if (!p2) return;

        const dx = p1.x - p2.x;
        const dy = p1.y - p2.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsion / (dist * dist);

        fx += (dx / dist) * force;
        fy += (dy / dist) * force;
      });

      // Attraction for same type nodes
      filteredNodes.forEach((node2) => {
        if (node1.id === node2.id || node1.type !== node2.type) return;
        const p2 = physics.get(node2.id);
        if (!p2) return;

        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        if (dist > idealDistance * 0.5) {
          const force = (dist - idealDistance * 0.5) * 0.01;
          fx += (dx / dist) * force;
          fy += (dy / dist) * force;
        }
      });

      // Center gravity
      const toCenterX = 400 - p1.x;
      const toCenterY = 300 - p1.y;
      fx += toCenterX * centerGravity;
      fy += toCenterY * centerGravity;

      // Apply force to velocity
      p1.vx += fx;
      p1.vy += fy;

      // Damping
      p1.vx *= damping;
      p1.vy *= damping;

      // Clamp velocity
      const speed = Math.sqrt(p1.vx * p1.vx + p1.vy * p1.vy);
      if (speed > maxVelocity) {
        p1.vx = (p1.vx / speed) * maxVelocity;
        p1.vy = (p1.vy / speed) * maxVelocity;
      } else if (speed < velocityThreshold) {
        p1.vx = 0;
        p1.vy = 0;
      }

      // Update position
      p1.x += p1.vx;
      p1.y += p1.vy;
    });

    setNodes(createNodesFromPhysics());
  }, [filteredNodes, isSimulationRunning, setNodes, createNodesFromPhysics]);

  // Animation loop
  useEffect(() => {
    if (!isSimulationRunning) return;

    const animate = () => {
      simulationStep();
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isSimulationRunning, simulationStep]);

  // Handle node drag
  const handleNodesChange = useCallback(
    (changes: any) => {
      onNodesChange(changes);

      changes.forEach((change: any) => {
        if (change.type === 'position' && change.position) {
          const physics = physicsRef.current.get(change.id);
          if (physics) {
            physics.x = change.position.x;
            physics.y = change.position.y;
            if (change.dragging) {
              physics.vx = 0;
              physics.vy = 0;
              draggedNodeRef.current = change.id;
            } else {
              draggedNodeRef.current = null;
            }
          }
        }
      });
    },
    [onNodesChange]
  );

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
    link.download = `${graph.name || 'embedding-graph'}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [graph]);

  const nodeColors: Record<string, string> = {
    person: '#3b82f6',
    company: '#10b981',
    entity: '#8b5cf6',
    concept: '#f59e0b',
    event: '#ef4444',
    location: '#06b6d4',
    default: '#6b7280',
  };

  return (
    <div className={`w-full h-full bg-dark-900 ${className}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
        fitView
        fitViewOptions={{ padding: 0.25, minZoom: 0.5, maxZoom: 1.5 }}
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={20} />
        {showControls && <Controls />}
        {showMiniMap && (
          <MiniMap
            nodeColor={(node) => nodeColors[node.data.type] || nodeColors.default}
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
                placeholder="Search embeddings..."
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

        {/* Actions Panel */}
        <Panel position="top-right" className="flex gap-2">
          <button
            onClick={() => setIsSimulationRunning(!isSimulationRunning)}
            className={`p-2 rounded-lg shadow-lg transition-colors ${
              isSimulationRunning
                ? 'bg-primary-600 hover:bg-primary-700 text-white'
                : 'bg-dark-800 hover:bg-dark-700 text-white'
            }`}
            title={isSimulationRunning ? 'Pause simulation' : 'Resume simulation'}
          >
            {isSimulationRunning ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={handleExport}
            className="bg-dark-800 hover:bg-dark-700 text-white p-2 rounded-lg shadow-lg transition-colors"
            title="Export Graph"
          >
            <Download className="w-4 h-4" />
          </button>
        </Panel>

        {/* Legend Panel */}
        <Panel position="bottom-left">
          <div className="bg-dark-800 rounded-lg p-3 shadow-lg">
            <div className="text-xs font-medium text-dark-400 mb-2">Embedding Types</div>
            <div className="flex flex-wrap gap-2">
              {graphNodeTypes.map((type) => (
                <div
                  key={type}
                  className="flex items-center gap-1.5 text-xs cursor-pointer hover:opacity-80"
                  onClick={() => setFilterType(filterType === type ? null : type)}
                >
                  <div
                    className="w-3 h-3 rounded"
                    style={{ backgroundColor: nodeColors[type] || nodeColors.default }}
                  />
                  <span className={filterType === type ? 'text-white' : 'text-dark-400'}>
                    {type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        {/* Stats Panel */}
        <Panel position="bottom-right">
          <div className="bg-dark-800 rounded-lg p-3 shadow-lg text-xs text-dark-400">
            <div className="flex items-center gap-1 mb-1">
              <Info className="w-3 h-3" />
              <span className="font-medium">t-SNE Style Visualization</span>
            </div>
            <div>Embeddings: {graph.nodes.length}</div>
            <div>Relationships: {graph.edges.length}</div>
            {searchQuery && <div>Filtered: {nodes.length} items</div>}
            <div className="mt-1 text-primary-400">
              {isSimulationRunning ? '● Live Clustering' : '○ Paused'}
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

export const EmbeddingVisualization: React.FC<EmbeddingVisualizationProps> = (props) => {
  return (
    <ReactFlowProvider>
      <EmbeddingVisualizationInner {...props} />
    </ReactFlowProvider>
  );
};

export default EmbeddingVisualization;
