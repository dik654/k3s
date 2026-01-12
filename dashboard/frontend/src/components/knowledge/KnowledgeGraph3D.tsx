import React, { useRef, useMemo, useState, useCallback } from 'react';
import { Canvas, useFrame, ThreeEvent } from '@react-three/fiber';
import { OrbitControls, Billboard, Text } from '@react-three/drei';
import * as THREE from 'three';
import type {
  KnowledgeGraph,
  KnowledgeGraphNode,
  KnowledgeGraphEdge,
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

interface Node3DProps {
  node: KnowledgeGraphNode;
  position: [number, number, number];
  isSelected: boolean;
  isHighlighted: boolean;
  onClick: (node: KnowledgeGraphNode) => void;
}

const Node3D: React.FC<Node3DProps> = ({
  node,
  position,
  isSelected,
  isHighlighted,
  onClick,
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const color = NODE_COLORS[node.type] || NODE_COLORS.default;
  const scale = isSelected ? 1.3 : isHighlighted ? 1.15 : hovered ? 1.1 : 1;
  const size = node.type === 'class' ? 0.6 : node.type === 'property' ? 0.4 : 0.5;

  useFrame((state) => {
    if (meshRef.current) {
      if (isSelected) {
        meshRef.current.rotation.y += 0.02;
      }
    }
  });

  const handleClick = useCallback(
    (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      onClick(node);
    },
    [node, onClick]
  );

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        scale={scale}
        onClick={handleClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        {node.type === 'class' ? (
          <boxGeometry args={[size, size, size]} />
        ) : node.type === 'property' ? (
          <octahedronGeometry args={[size * 0.7]} />
        ) : (
          <sphereGeometry args={[size * 0.5, 32, 32]} />
        )}
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected ? 0.5 : isHighlighted ? 0.3 : hovered ? 0.2 : 0.1}
          metalness={0.3}
          roughness={0.7}
        />
      </mesh>
      <Billboard follow={true} lockX={false} lockY={false} lockZ={false}>
        <Text
          position={[0, size + 0.3, 0]}
          fontSize={0.25}
          color="white"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.02}
          outlineColor="#000000"
        >
          {node.label}
        </Text>
      </Billboard>
    </group>
  );
};

interface Edge3DProps {
  start: [number, number, number];
  end: [number, number, number];
  isHighlighted: boolean;
  label?: string;
}

const Edge3D: React.FC<Edge3DProps> = ({ start, end, isHighlighted, label }) => {
  const lineGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const points = [
      new THREE.Vector3(...start),
      new THREE.Vector3(...end),
    ];
    geometry.setFromPoints(points);
    return geometry;
  }, [start, end]);

  const lineMaterial = useMemo(() => {
    return new THREE.LineBasicMaterial({
      color: isHighlighted ? '#ffffff' : '#4b5563',
      opacity: isHighlighted ? 0.8 : 0.4,
      transparent: true,
    });
  }, [isHighlighted]);

  const midPoint: [number, number, number] = [
    (start[0] + end[0]) / 2,
    (start[1] + end[1]) / 2,
    (start[2] + end[2]) / 2,
  ];

  return (
    <>
      <primitive object={new THREE.Line(lineGeometry, lineMaterial)} />
      {label && isHighlighted && (
        <Billboard position={midPoint}>
          <Text
            fontSize={0.15}
            color="#94a3b8"
            anchorX="center"
            anchorY="middle"
            outlineWidth={0.01}
            outlineColor="#000000"
          >
            {label}
          </Text>
        </Billboard>
      )}
    </>
  );
};

interface KnowledgeGraph3DProps {
  graph: KnowledgeGraph;
  onNodeSelect?: (node: KnowledgeGraphNode | null) => void;
  onEdgeSelect?: (edge: KnowledgeGraphEdge | null) => void;
}

export const KnowledgeGraph3D: React.FC<KnowledgeGraph3DProps> = ({
  graph,
  onNodeSelect,
  onEdgeSelect,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Generate 3D positions for nodes using force-directed layout simulation
  const nodePositions = useMemo(() => {
    const positions: Record<string, [number, number, number]> = {};
    const nodeCount = graph.nodes.length;
    const radius = Math.max(5, nodeCount * 0.5);

    // Simple spherical distribution with type-based layering
    const classNodes = graph.nodes.filter((n) => n.type === 'class');
    const instanceNodes = graph.nodes.filter((n) => n.type === 'instance');
    const propertyNodes = graph.nodes.filter((n) => n.type === 'property');
    const otherNodes = graph.nodes.filter(
      (n) => !['class', 'instance', 'property'].includes(n.type)
    );

    // Classes on top layer
    classNodes.forEach((node, i) => {
      const angle = (i / classNodes.length) * Math.PI * 2;
      positions[node.id] = [
        Math.cos(angle) * radius * 0.6,
        2,
        Math.sin(angle) * radius * 0.6,
      ];
    });

    // Instances in middle layer
    instanceNodes.forEach((node, i) => {
      const angle = (i / instanceNodes.length) * Math.PI * 2;
      positions[node.id] = [
        Math.cos(angle) * radius * 0.8,
        0,
        Math.sin(angle) * radius * 0.8,
      ];
    });

    // Properties on bottom layer
    propertyNodes.forEach((node, i) => {
      const angle = (i / propertyNodes.length) * Math.PI * 2;
      positions[node.id] = [
        Math.cos(angle) * radius * 0.5,
        -2,
        Math.sin(angle) * radius * 0.5,
      ];
    });

    // Other nodes scattered
    otherNodes.forEach((node, i) => {
      const phi = Math.acos(-1 + (2 * i) / otherNodes.length);
      const theta = Math.sqrt(otherNodes.length * Math.PI) * phi;
      positions[node.id] = [
        radius * Math.cos(theta) * Math.sin(phi),
        radius * Math.cos(phi),
        radius * Math.sin(theta) * Math.sin(phi),
      ];
    });

    return positions;
  }, [graph.nodes]);

  // Find connected nodes for highlighting
  const connectedNodeIds = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const connected = new Set<string>();
    graph.edges.forEach((edge) => {
      if (edge.source === selectedNodeId) {
        connected.add(edge.target);
      }
      if (edge.target === selectedNodeId) {
        connected.add(edge.source);
      }
    });
    return connected;
  }, [selectedNodeId, graph.edges]);

  const handleNodeClick = useCallback(
    (node: KnowledgeGraphNode) => {
      const newSelected = selectedNodeId === node.id ? null : node.id;
      setSelectedNodeId(newSelected);
      onNodeSelect?.(newSelected ? node : null);
    },
    [selectedNodeId, onNodeSelect]
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null);
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  return (
    <div className="w-full h-full bg-dark-900">
      <Canvas
        camera={{ position: [0, 5, 15], fov: 60 }}
        onClick={handleBackgroundClick}
      >
        <ambientLight intensity={0.4} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <pointLight position={[-10, -10, -10]} intensity={0.5} />

        {/* Render edges */}
        {graph.edges.map((edge) => {
          const startPos = nodePositions[edge.source];
          const endPos = nodePositions[edge.target];
          if (!startPos || !endPos) return null;

          const isHighlighted =
            edge.source === selectedNodeId || edge.target === selectedNodeId;

          return (
            <Edge3D
              key={edge.id}
              start={startPos}
              end={endPos}
              isHighlighted={isHighlighted}
              label={edge.label}
            />
          );
        })}

        {/* Render nodes */}
        {graph.nodes.map((node) => {
          const position = nodePositions[node.id];
          if (!position) return null;

          return (
            <Node3D
              key={node.id}
              node={node}
              position={position}
              isSelected={selectedNodeId === node.id}
              isHighlighted={connectedNodeIds.has(node.id)}
              onClick={handleNodeClick}
            />
          );
        })}

        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          rotateSpeed={0.5}
          zoomSpeed={0.8}
          minDistance={3}
          maxDistance={50}
        />
      </Canvas>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-dark-800/90 backdrop-blur-sm rounded-lg p-3">
        <div className="text-xs text-dark-400 mb-2">Node Types</div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-500 rounded" />
            <span className="text-xs text-dark-300">Class</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-emerald-500 rounded-full" />
            <span className="text-xs text-dark-300">Instance</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-amber-500 transform rotate-45" />
            <span className="text-xs text-dark-300">Property</span>
          </div>
        </div>
      </div>

      {/* Controls hint */}
      <div className="absolute bottom-4 right-4 bg-dark-800/90 backdrop-blur-sm rounded-lg p-3">
        <div className="text-xs text-dark-400">
          <div>Left click + drag: Rotate</div>
          <div>Right click + drag: Pan</div>
          <div>Scroll: Zoom</div>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeGraph3D;
