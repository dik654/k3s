import React from 'react';
import { Search, Brain, Database, Download, Upload, GitBranch, Shuffle } from 'lucide-react';
import { useNodeDefinitionsStore } from '@/stores/nodeDefinitionsStore';

const categoryIcons: Record<string, React.ComponentType<any>> = {
  ai: Brain,
  knowledge: Database,
  input: Download,
  output: Upload,
  control: GitBranch,
  transform: Shuffle,
};

export function NodePanel() {
  const {
    categories,
    searchQuery,
    selectedCategory,
    setSearchQuery,
    setSelectedCategory,
    getFilteredNodes,
  } = useNodeDefinitionsStore();

  const filteredNodes = getFilteredNodes();

  const handleDragStart = (event: React.DragEvent, node: any) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(node));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div style={{
      width: 256,
      background: '#1e293b',
      borderRight: '1px solid #334155',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Search */}
      <div style={{ padding: 12, borderBottom: '1px solid #334155' }}>
        <div style={{ position: 'relative' }}>
          <Search
            size={14}
            style={{
              position: 'absolute',
              left: 10,
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#94a3b8'
            }}
          />
          <input
            type="text"
            placeholder="노드 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              paddingLeft: 32,
              paddingRight: 12,
              paddingTop: 8,
              paddingBottom: 8,
              background: '#334155',
              border: '1px solid #475569',
              borderRadius: 6,
              fontSize: 12,
              color: '#fff'
            }}
          />
        </div>
      </div>

      {/* Categories */}
      <div style={{ padding: 8, borderBottom: '1px solid #334155' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          <button
            onClick={() => setSelectedCategory(null)}
            style={{
              padding: '4px 8px',
              borderRadius: 4,
              fontSize: 11,
              border: 'none',
              cursor: 'pointer',
              background: selectedCategory === null ? '#3b82f6' : '#334155',
              color: selectedCategory === null ? '#fff' : '#94a3b8'
            }}
          >
            전체
          </button>
          {categories.map((category) => {
            const Icon = categoryIcons[category.id] || Brain;
            return (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                style={{
                  padding: '4px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  background: selectedCategory === category.id ? '#3b82f6' : '#334155',
                  color: selectedCategory === category.id ? '#fff' : '#94a3b8'
                }}
              >
                <Icon size={12} />
                {category.name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Node List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {filteredNodes.map((node) => (
            <div
              key={node.type}
              draggable
              onDragStart={(e) => handleDragStart(e, node)}
              style={{
                padding: 12,
                background: '#334155',
                borderRadius: 8,
                cursor: 'grab'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: node.color
                  }}
                >
                  {React.createElement(categoryIcons[node.category] || Brain, {
                    size: 16,
                    color: '#fff',
                  })}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#fff' }}>
                    {node.name}
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {node.description}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredNodes.length === 0 && (
          <div style={{ textAlign: 'center', color: '#94a3b8', fontSize: 13, padding: 32 }}>
            노드를 찾을 수 없습니다
          </div>
        )}
      </div>
    </div>
  );
}

export default NodePanel;
