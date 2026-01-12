import React, { useState, useCallback } from 'react';
import { Plus, Upload, Box, Grid2X2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { KnowledgeGraphViewer, KnowledgeGraph3D, NodeDetailPanel } from '@/components/knowledge';
import type {
  KnowledgeGraph,
  KnowledgeGraphNode,
  KnowledgeGraphEdge,
  GraphLayoutType,
} from '@/types';

// Animal classification ontology example
const sampleGraph: KnowledgeGraph = {
  id: 'animal-ontology',
  name: 'Animal Classification System',
  description: 'Biological classification ontology example',
  nodes: [
    // Classes
    { id: 'living-thing', label: 'Living Thing', type: 'class', properties: { description: 'Top-level classification', isAbstract: true } },
    { id: 'animal', label: 'Animal', type: 'class', properties: { description: 'Self-moving organisms that consume food' } },
    { id: 'mammal', label: 'Mammal', type: 'class', properties: { description: 'Warm-blooded animals that nurse their young' } },
    { id: 'bird', label: 'Bird', type: 'class', properties: { description: 'Feathered animals that lay eggs' } },
    { id: 'cat-family', label: 'Felidae', type: 'class', properties: { description: 'Cat family including lions, tigers' } },
    { id: 'dog-family', label: 'Canidae', type: 'class', properties: { description: 'Dog family including wolves, foxes' } },
    { id: 'place', label: 'Place', type: 'class', properties: { description: 'Location concept' } },
    { id: 'food', label: 'Food', type: 'class', properties: { description: 'Consumable items' } },

    // Instances
    { id: 'nabi', label: 'Nabi', type: 'instance', properties: { description: 'My cat', age: 3, color: 'orange' } },
    { id: 'kong', label: 'Kong', type: 'instance', properties: { description: "Neighbor's cat", age: 5, color: 'black' } },
    { id: 'baduk', label: 'Baduk', type: 'instance', properties: { description: 'Pet dog', age: 2, breed: 'Jindo' } },
    { id: 'happy', label: 'Happy', type: 'instance', properties: { description: 'Park dog', age: 4, breed: 'Golden Retriever' } },
    { id: 'twitter', label: 'Tweety', type: 'instance', properties: { description: 'Sparrow', species: 'Sparrow' } },
    { id: 'my-home', label: 'My Home', type: 'instance', properties: { description: 'Where I live', address: 'Seoul' } },
    { id: 'neighbor-home', label: "Neighbor's Home", type: 'instance', properties: { description: 'Next door' } },
    { id: 'park', label: 'Park', type: 'instance', properties: { description: 'Local park', name: 'Central Park' } },
    { id: 'cat-food', label: 'Cat Food', type: 'instance', properties: { brand: 'Royal Canin', type: 'Dry' } },
    { id: 'dog-food', label: 'Dog Food', type: 'instance', properties: { brand: 'Nutro', type: 'Dry' } },

    // Properties
    { id: 'eats-prop', label: 'eats', type: 'property', properties: { domain: 'Animal', range: 'Food' } },
    { id: 'lives-in-prop', label: 'livesIn', type: 'property', properties: { domain: 'Animal', range: 'Place' } },
    { id: 'friend-of-prop', label: 'friendOf', type: 'property', properties: { domain: 'Animal', range: 'Animal', isSymmetric: true } },
  ],
  edges: [
    // Class hierarchy
    { id: 'sc1', source: 'animal', target: 'living-thing', type: 'subClassOf', label: 'subClassOf' },
    { id: 'sc2', source: 'mammal', target: 'animal', type: 'subClassOf', label: 'subClassOf' },
    { id: 'sc3', source: 'bird', target: 'animal', type: 'subClassOf', label: 'subClassOf' },
    { id: 'sc4', source: 'cat-family', target: 'mammal', type: 'subClassOf', label: 'subClassOf' },
    { id: 'sc5', source: 'dog-family', target: 'mammal', type: 'subClassOf', label: 'subClassOf' },
    { id: 'sc6', source: 'food', target: 'living-thing', type: 'subClassOf', label: 'subClassOf' },
    { id: 'sc7', source: 'place', target: 'living-thing', type: 'subClassOf', label: 'subClassOf' },

    // Instance-class relationships
    { id: 'io1', source: 'nabi', target: 'cat-family', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io2', source: 'kong', target: 'cat-family', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io3', source: 'baduk', target: 'dog-family', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io4', source: 'happy', target: 'dog-family', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io5', source: 'twitter', target: 'bird', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io6', source: 'my-home', target: 'place', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io7', source: 'neighbor-home', target: 'place', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io8', source: 'park', target: 'place', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io9', source: 'cat-food', target: 'food', type: 'instanceOf', label: 'rdf:type' },
    { id: 'io10', source: 'dog-food', target: 'food', type: 'instanceOf', label: 'rdf:type' },

    // Property domain/range
    { id: 'pd1', source: 'eats-prop', target: 'animal', type: 'hasDomain', label: 'rdfs:domain' },
    { id: 'pr1', source: 'eats-prop', target: 'food', type: 'hasRange', label: 'rdfs:range' },
    { id: 'pd2', source: 'lives-in-prop', target: 'animal', type: 'hasDomain', label: 'rdfs:domain' },
    { id: 'pr2', source: 'lives-in-prop', target: 'place', type: 'hasRange', label: 'rdfs:range' },
    { id: 'pd3', source: 'friend-of-prop', target: 'animal', type: 'hasDomain', label: 'rdfs:domain' },
    { id: 'pr3', source: 'friend-of-prop', target: 'animal', type: 'hasRange', label: 'rdfs:range' },

    // Actual relationships
    { id: 'r1', source: 'nabi', target: 'my-home', type: 'livesIn', label: 'lives in' },
    { id: 'r2', source: 'kong', target: 'neighbor-home', type: 'livesIn', label: 'lives in' },
    { id: 'r3', source: 'baduk', target: 'neighbor-home', type: 'livesIn', label: 'lives in' },
    { id: 'r4', source: 'happy', target: 'park', type: 'livesIn', label: 'lives in' },
    { id: 'r5', source: 'nabi', target: 'cat-food', type: 'eats', label: 'eats' },
    { id: 'r6', source: 'kong', target: 'cat-food', type: 'eats', label: 'eats' },
    { id: 'r7', source: 'baduk', target: 'dog-food', type: 'eats', label: 'eats' },
    { id: 'r8', source: 'happy', target: 'dog-food', type: 'eats', label: 'eats' },
    { id: 'r9', source: 'nabi', target: 'kong', type: 'friendOf', label: 'friend' },
    { id: 'r10', source: 'baduk', target: 'happy', type: 'friendOf', label: 'friend' },
  ],
  metadata: {
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    version: 1,
    nodeCount: 21,
    edgeCount: 27,
  },
};

export const KnowledgeGraphPage: React.FC = () => {
  const [graph, setGraph] = useState<KnowledgeGraph>(sampleGraph);
  const [selectedNode, setSelectedNode] = useState<KnowledgeGraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<KnowledgeGraphEdge | null>(null);
  const [layout, setLayout] = useState<GraphLayoutType>('force');
  const [showDetailPanel, setShowDetailPanel] = useState(false);
  const [viewMode, setViewMode] = useState<'2d' | '3d'>('3d');

  const handleNodeSelect = useCallback((node: KnowledgeGraphNode | null) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    setShowDetailPanel(!!node);
  }, []);

  const handleEdgeSelect = useCallback((edge: KnowledgeGraphEdge | null) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
    setShowDetailPanel(!!edge);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
    setShowDetailPanel(false);
  }, []);

  const handleImport = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const text = await file.text();
        try {
          const importedGraph = JSON.parse(text) as KnowledgeGraph;
          setGraph(importedGraph);
        } catch (err) {
          console.error('Failed to parse graph file:', err);
        }
      }
    };
    input.click();
  }, []);

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="h-14 bg-dark-800 border-b border-dark-700 flex items-center justify-between px-6">
        <div>
          <h1 className="text-lg font-semibold text-white">Knowledge Graph</h1>
          <p className="text-xs text-dark-400">{graph.name}</p>
        </div>
        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-dark-700 rounded-lg p-1">
            <button
              onClick={() => setViewMode('2d')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-all ${
                viewMode === '2d'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'text-dark-400 hover:text-white'
              }`}
            >
              <Grid2X2 className="w-4 h-4" />
              2D
            </button>
            <button
              onClick={() => setViewMode('3d')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-all ${
                viewMode === '3d'
                  ? 'bg-primary-600 text-white shadow-lg'
                  : 'text-dark-400 hover:text-white'
              }`}
            >
              <Box className="w-4 h-4" />
              3D
            </button>
          </div>

          {/* Layout Selector (only for 2D) */}
          {viewMode === '2d' && (
            <select
              value={layout}
              onChange={(e) => setLayout(e.target.value as GraphLayoutType)}
              className="bg-dark-700 border border-dark-600 text-sm text-white rounded-lg px-3 py-1.5 focus:outline-none focus:border-primary-500"
            >
              <option value="force">Force Layout</option>
              <option value="hierarchical">Hierarchical</option>
              <option value="circular">Circular</option>
              <option value="grid">Grid</option>
            </select>
          )}

          <button
            onClick={handleImport}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-dark-700 hover:bg-dark-600 text-white text-sm transition-colors"
          >
            <Upload className="w-4 h-4" />
            Import
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm transition-colors">
            <Plus className="w-4 h-4" />
            Add Node
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={viewMode}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="flex-1"
          >
            {viewMode === '2d' ? (
              <KnowledgeGraphViewer
                graph={graph}
                onNodeSelect={handleNodeSelect}
                onEdgeSelect={handleEdgeSelect}
                layout={layout}
                showMiniMap
                showControls
              />
            ) : (
              <KnowledgeGraph3D
                graph={graph}
                onNodeSelect={handleNodeSelect}
                onEdgeSelect={handleEdgeSelect}
              />
            )}
          </motion.div>
        </AnimatePresence>

        <AnimatePresence>
          {showDetailPanel && (
            <motion.div
              initial={{ x: 300, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 300, opacity: 0 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            >
              <NodeDetailPanel
                node={selectedNode}
                edge={selectedEdge}
                onClose={handleCloseDetail}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default KnowledgeGraphPage;
