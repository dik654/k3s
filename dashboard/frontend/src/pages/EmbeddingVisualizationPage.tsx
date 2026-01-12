import React, { useState, useCallback } from 'react';
import { Upload, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { EmbeddingVisualization, NodeDetailPanel } from '@/components/knowledge';
import type {
  KnowledgeGraph,
  KnowledgeGraphNode,
  KnowledgeGraphEdge,
} from '@/types';

// Sample data for embedding visualization demo
const sampleEmbeddingGraph: KnowledgeGraph = {
  id: 'embedding-graph',
  name: 'Embedding Similarity Graph',
  description: 'Visualization of embedding vectors using t-SNE style clustering',
  nodes: [
    // Person cluster
    { id: 'alice', label: 'Alice Johnson', type: 'person', properties: { role: 'CEO', department: 'Executive' } },
    { id: 'bob', label: 'Bob Smith', type: 'person', properties: { role: 'CTO', department: 'Engineering' } },
    { id: 'charlie', label: 'Charlie Brown', type: 'person', properties: { role: 'Developer', department: 'Engineering' } },
    { id: 'diana', label: 'Diana Ross', type: 'person', properties: { role: 'Designer', department: 'Design' } },
    // Company cluster
    { id: 'acme', label: 'Acme Corp', type: 'company', properties: { industry: 'Technology', founded: 2015 } },
    { id: 'startup', label: 'StartupXYZ', type: 'company', properties: { industry: 'AI', founded: 2020 } },
    // Concept cluster
    { id: 'ai-project', label: 'AI Assistant Project', type: 'concept', properties: { status: 'In Progress' } },
    { id: 'ml-tech', label: 'Machine Learning', type: 'concept', properties: { category: 'Technology' } },
    // Location cluster
    { id: 'nyc', label: 'New York City', type: 'location', properties: { country: 'USA', region: 'East Coast' } },
    { id: 'sf', label: 'San Francisco', type: 'location', properties: { country: 'USA', region: 'West Coast' } },
    { id: 'la', label: 'Los Angeles', type: 'location', properties: { country: 'USA', region: 'West Coast' } },
  ],
  edges: [
    // Same-type connections
    { id: 'p1', source: 'alice', target: 'bob', type: 'manages', label: 'manages' },
    { id: 'p2', source: 'bob', target: 'charlie', type: 'manages', label: 'manages' },
    { id: 'p3', source: 'alice', target: 'diana', type: 'knows', label: 'knows' },
    { id: 'c1', source: 'acme', target: 'startup', type: 'invests', label: 'invested in', weight: 3 },
    { id: 'con1', source: 'ai-project', target: 'ml-tech', type: 'uses', label: 'uses' },
    { id: 'l1', source: 'sf', target: 'la', type: 'nearBy', label: 'near' },
    // Cross-type connections
    { id: 'pc1', source: 'alice', target: 'acme', type: 'worksAt', label: 'CEO of' },
    { id: 'pc2', source: 'bob', target: 'acme', type: 'worksAt', label: 'CTO of' },
    { id: 'pc3', source: 'charlie', target: 'acme', type: 'worksAt', label: 'works at' },
    { id: 'pc4', source: 'diana', target: 'startup', type: 'worksAt', label: 'works at' },
    { id: 'cc1', source: 'acme', target: 'ai-project', type: 'develops', label: 'develops' },
    { id: 'cl1', source: 'acme', target: 'nyc', type: 'locatedIn', label: 'HQ in' },
    { id: 'cl2', source: 'startup', target: 'sf', type: 'locatedIn', label: 'based in' },
  ],
  metadata: {
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    version: 1,
    nodeCount: 11,
    edgeCount: 13,
  },
};

export const EmbeddingVisualizationPage: React.FC = () => {
  const [graph, setGraph] = useState<KnowledgeGraph>(sampleEmbeddingGraph);
  const [selectedNode, setSelectedNode] = useState<KnowledgeGraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<KnowledgeGraphEdge | null>(null);
  const [showDetailPanel, setShowDetailPanel] = useState(false);

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
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary-400" />
            <h1 className="text-lg font-semibold text-white">Embedding Visualization</h1>
          </div>
          <p className="text-xs text-dark-400">t-SNE style clustering by similarity</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-dark-700 rounded-lg px-3 py-1.5 text-xs text-dark-300">
            <span className="text-primary-400 font-medium">Same type</span> = Similar embedding = Close together
          </div>
          <button
            onClick={handleImport}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-dark-700 hover:bg-dark-600 text-white text-sm transition-colors"
          >
            <Upload className="w-4 h-4" />
            Import
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden relative">
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, ease: 'easeInOut' }}
          className="flex-1"
        >
          <EmbeddingVisualization
            graph={graph}
            onNodeSelect={handleNodeSelect}
            onEdgeSelect={handleEdgeSelect}
            showMiniMap
            showControls
          />
        </motion.div>

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

export default EmbeddingVisualizationPage;
