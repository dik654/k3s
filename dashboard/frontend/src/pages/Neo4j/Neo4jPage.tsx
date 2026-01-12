import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Database,
  RefreshCw,
  Play,
  GitBranch,
  Layers,
  Workflow,
  Info,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Eye,
  X,
} from 'lucide-react';
import MermaidChart from '@/MermaidChart';
import { KnowledgeGraphViewer, KnowledgeGraph3D, NodeDetailPanel } from '@/components/knowledge';

const API_BASE = '/api';

interface SchemaData {
  rdbms_schema: {
    tables: Array<{ name: string; columns: string[] }>;
    sql_example: string;
  };
  graph_schema: {
    nodes: Array<{ label: string; properties: string[]; color: string }>;
    relationships: Array<{ from: string; type: string; to: string }>;
    cypher_example: string;
  };
  comparison: Record<string, { rdbms: string; graph: string }>;
}

interface GraphNode {
  id: string;
  label: string;
  name: string;
  x: number;
  y: number;
  properties: Record<string, unknown>;
}

interface GraphEdge {
  from: string;
  to: string;
  type: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface RagData {
  traditional_rag: {
    flow: string[];
    limitations: string[];
  };
  graph_enhanced_rag: {
    flow: Array<{ step: string; description: string }>;
    advantages: string[];
  };
  example: {
    query: string;
    graph_context: {
      traversal: string[];
      related_info: string[];
    };
    enhanced_answer: string;
  };
}

interface IndexData {
  types: Array<{
    name: string;
    description: string;
    use_case: string;
    syntax: string;
  }>;
}

interface Neo4jPageProps {
  showToast: (message: string, type?: string) => void;
}

const nodeColors: Record<string, string> = {
  'Person': '#4ecdc4',
  'Department': '#45b7d1',
  'Project': '#96ceb4',
  'Technology': '#ffeaa7',
  'Company': '#dfe6e9'
};

export function Neo4jPage({ showToast }: Neo4jPageProps) {
  const [activeTab, setActiveTab] = useState<'schema' | 'query' | 'rag' | 'index' | 'graph3d'>('schema');
  const [schemaData, setSchemaData] = useState<SchemaData | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [ragData, setRagData] = useState<RagData | null>(null);
  const [indexData, setIndexData] = useState<IndexData | null>(null);
  const [cypherQuery, setCypherQuery] = useState('MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 10');
  const [queryResult, setQueryResult] = useState<{ results?: unknown[]; error?: string; mode?: string; note?: string } | null>(null);
  const [isQuerying, setIsQuerying] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [view3D, setView3D] = useState(false);

  const loadOntologyData = useCallback(async () => {
    try {
      const [schema, graph, rag, index] = await Promise.all([
        axios.get('/api/ontology/schema').catch(() => ({ data: null })),
        axios.get('/api/ontology/graph-data').catch(() => ({ data: null })),
        axios.get('/api/ontology/rag-integration').catch(() => ({ data: null })),
        axios.get('/api/ontology/index-types').catch(() => ({ data: null }))
      ]);
      setSchemaData(schema.data);
      setGraphData(graph.data);
      setRagData(rag.data);
      setIndexData(index.data);
    } catch (error) {
      console.error('Failed to load ontology data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOntologyData();
  }, [loadOntologyData]);

  const executeQuery = async () => {
    setIsQuerying(true);
    try {
      const response = await axios.post('/api/ontology/query', { query: cypherQuery });
      setQueryResult(response.data);
    } catch (error: unknown) {
      const err = error as { message?: string };
      setQueryResult({ error: err.message || 'Query failed' });
    }
    setIsQuerying(false);
  };

  const exampleQueries = [
    { label: '모든 노드', query: 'MATCH (n) RETURN n LIMIT 10' },
    { label: '모든 관계', query: 'MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 10' },
    { label: '최단 경로', query: 'MATCH path = shortestPath((a)-[*]-(b)) RETURN path' },
    { label: '노드 수', query: 'MATCH (n) RETURN count(n) as count' }
  ];

  if (loading) {
    return (
      <section className="section">
        <div className="card">
          <div className="loading-container">
            <div className="spinner large"></div>
            <p>Neo4j 정보를 불러오는 중...</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">
          <GitBranch size={24} /> Neo4j 그래프 데이터베이스
        </h2>
        <div className="benchmark-actions">
          <button className="btn btn-outline" onClick={loadOntologyData}>
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <div className="ontology-live-demo-card">
        <div className="demo-header">
          <h4><GitBranch size={18} /> Ontology (Neo4j) 라이브 데모</h4>
          <p>그래프 데이터베이스로 개념과 관계를 표현하고 탐색합니다</p>
        </div>

        <div className="demo-tabs">
          <button
            className={activeTab === 'schema' ? 'active' : ''}
            onClick={() => setActiveTab('schema')}
          >
            <Database size={14} /> 스키마 비교
          </button>
          <button
            className={activeTab === 'query' ? 'active' : ''}
            onClick={() => setActiveTab('query')}
          >
            <Play size={14} /> Cypher 실행
          </button>
          <button
            className={activeTab === 'rag' ? 'active' : ''}
            onClick={() => setActiveTab('rag')}
          >
            <Workflow size={14} /> RAG 통합
          </button>
          <button
            className={activeTab === 'index' ? 'active' : ''}
            onClick={() => setActiveTab('index')}
          >
            <Layers size={14} /> 인덱스
          </button>
          <button
            className={activeTab === 'graph3d' ? 'active' : ''}
            onClick={() => setActiveTab('graph3d')}
          >
            <Eye size={14} /> 3D 시각화
          </button>
        </div>

        <div className="demo-content">
          {/* 스키마 비교 탭 */}
          {activeTab === 'schema' && schemaData && (
            <div className="schema-comparison">
              <div className="comparison-intro">
                <Info size={16} />
                <span>온톨로지(그래프 스키마)는 기존 RDBMS 스키마와 유사하지만, 관계를 1급 시민으로 취급합니다</span>
              </div>

              <div className="schema-grid">
                {/* RDBMS 스키마 */}
                <div className="schema-section rdbms">
                  <h5>🗄️ RDBMS 스키마</h5>
                  <div className="tables-list">
                    {schemaData.rdbms_schema.tables.map((table, idx) => (
                      <div key={idx} className="table-card">
                        <div className="table-name">{table.name}</div>
                        <div className="table-columns">
                          {table.columns.map((col, cidx) => (
                            <span key={cidx} className={col.includes('PK') ? 'pk' : col.includes('FK') ? 'fk' : ''}>
                              {col}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="query-example">
                    <h6>SQL 쿼리 예시</h6>
                    <pre>{schemaData.rdbms_schema.sql_example}</pre>
                  </div>
                </div>

                {/* Graph 스키마 */}
                <div className="schema-section graph">
                  <h5>🕸️ Graph 스키마 (온톨로지)</h5>

                  <div className="ontology-mermaid-chart">
                    <h6>그래프 구조 시각화</h6>
                    <MermaidChart
                      chart={`graph LR
    subgraph Nodes["노드 (Entities)"]
        P[("👤 Person<br/>name, email, role")]
        D[("📁 Department<br/>name, budget")]
        PR[("📋 Project<br/>name, status")]
        T[("💻 Technology<br/>name, type")]
    end

    subgraph Relationships["관계"]
        P -->|WORKS_IN| D
        P -->|MANAGES| PR
        P -->|KNOWS| T
        PR -->|USES| T
        D -->|OWNS| PR
    end

    style P fill:#4ecdc4,stroke:#333,stroke-width:2px
    style D fill:#45b7d1,stroke:#333,stroke-width:2px
    style PR fill:#96ceb4,stroke:#333,stroke-width:2px
    style T fill:#ffeaa7,stroke:#333,stroke-width:2px`}
                      className="ontology-graph-mermaid"
                    />
                  </div>

                  <div className="nodes-list">
                    <h6>노드 (Node Labels)</h6>
                    {schemaData.graph_schema.nodes.map((node, idx) => (
                      <div key={idx} className="node-card" style={{ borderLeftColor: node.color }}>
                        <div className="node-label" style={{ backgroundColor: node.color }}>{node.label}</div>
                        <div className="node-properties">
                          {node.properties.map((prop, pidx) => (
                            <span key={pidx}>{prop}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="relations-list">
                    <h6>관계 (Relationships)</h6>
                    {schemaData.graph_schema.relationships.map((rel, idx) => (
                      <div key={idx} className="relation-card">
                        <span className="rel-from">{rel.from}</span>
                        <span className="rel-arrow">-[:{rel.type}]-&gt;</span>
                        <span className="rel-to">{rel.to}</span>
                      </div>
                    ))}
                  </div>
                  <div className="query-example">
                    <h6>Cypher 쿼리 예시</h6>
                    <pre>{schemaData.graph_schema.cypher_example}</pre>
                  </div>
                </div>
              </div>

              {/* 비교 표 */}
              <div className="comparison-table">
                <h5>RDBMS vs Graph 비교</h5>
                <table>
                  <thead>
                    <tr>
                      <th>항목</th>
                      <th>RDBMS</th>
                      <th>Graph DB</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(schemaData.comparison).map(([key, value]) => (
                      <tr key={key}>
                        <td>{key.replace(/_/g, ' ')}</td>
                        <td className="rdbms-cell">{value.rdbms}</td>
                        <td className="graph-cell">{value.graph}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Cypher 쿼리 실행 탭 */}
          {activeTab === 'query' && (
            <div className="cypher-query-section">
              <div className="query-panel">
                <div className="query-input-section">
                  <h5>Cypher 쿼리 실행</h5>
                  <div className="example-queries">
                    {exampleQueries.map((eq, idx) => (
                      <button key={idx} onClick={() => setCypherQuery(eq.query)}>
                        {eq.label}
                      </button>
                    ))}
                  </div>
                  <textarea
                    value={cypherQuery}
                    onChange={(e) => setCypherQuery(e.target.value)}
                    placeholder="Cypher 쿼리를 입력하세요..."
                    rows={4}
                  />
                  <button className="execute-btn" onClick={executeQuery} disabled={isQuerying}>
                    {isQuerying ? <Loader2 size={14} className="spinning" /> : <Play size={14} />}
                    {isQuerying ? '실행 중...' : '쿼리 실행'}
                  </button>
                </div>

                {queryResult && (
                  <div className="query-result">
                    <div className="result-header">
                      <h5>실행 결과</h5>
                      {queryResult.mode && (
                        <span className={`mode-badge ${queryResult.mode}`}>
                          {queryResult.mode === 'live' ? '🟢 Live' : '🟡 Simulation'}
                        </span>
                      )}
                    </div>
                    {queryResult.error ? (
                      <div className="result-error">{queryResult.error}</div>
                    ) : (
                      <pre className="result-json">{JSON.stringify(queryResult.results, null, 2)}</pre>
                    )}
                    {queryResult.note && (
                      <div className="result-note"><Info size={14} /> {queryResult.note}</div>
                    )}
                  </div>
                )}
              </div>

              {/* 그래프 시각화 */}
              {graphData && (
                <div className="graph-visualization">
                  <h5>그래프 시각화</h5>
                  <svg viewBox="0 0 800 400" className="graph-svg">
                    {/* 엣지 그리기 */}
                    {graphData.edges.map((edge, idx) => {
                      const fromNode = graphData.nodes.find(n => n.id === edge.from);
                      const toNode = graphData.nodes.find(n => n.id === edge.to);
                      if (!fromNode || !toNode) return null;

                      const midX = (fromNode.x + toNode.x) / 2;
                      const midY = (fromNode.y + toNode.y) / 2;

                      return (
                        <g key={idx}>
                          <line
                            x1={fromNode.x}
                            y1={fromNode.y}
                            x2={toNode.x}
                            y2={toNode.y}
                            className="graph-edge"
                          />
                          <text x={midX} y={midY - 5} className="edge-label">{edge.type}</text>
                        </g>
                      );
                    })}

                    {/* 노드 그리기 */}
                    {graphData.nodes.map((node, idx) => (
                      <g
                        key={idx}
                        className={`graph-node ${selectedNode?.id === node.id ? 'selected' : ''}`}
                        onClick={() => setSelectedNode(node)}
                        style={{ cursor: 'pointer' }}
                      >
                        <circle
                          cx={node.x}
                          cy={node.y}
                          r={30}
                          fill={nodeColors[node.label] || '#ddd'}
                        />
                        <text x={node.x} y={node.y - 40} className="node-label-text">{node.label}</text>
                        <text x={node.x} y={node.y + 5} className="node-name-text">{node.name}</text>
                      </g>
                    ))}
                  </svg>

                  {selectedNode && (
                    <div className="node-details">
                      <h6>선택된 노드</h6>
                      <div className="node-info">
                        <span className="node-type" style={{ backgroundColor: nodeColors[selectedNode.label] }}>
                          {selectedNode.label}
                        </span>
                        <span className="node-name">{selectedNode.name}</span>
                      </div>
                      <div className="node-props">
                        {Object.entries(selectedNode.properties).map(([key, value]) => (
                          <div key={key}><strong>{key}:</strong> {String(value)}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* RAG 통합 탭 */}
          {activeTab === 'rag' && ragData && (
            <div className="rag-integration-section">
              <div className="rag-comparison">
                {/* Traditional RAG */}
                <div className="rag-flow traditional">
                  <h5>📚 Traditional RAG</h5>
                  <div className="flow-diagram">
                    {ragData.traditional_rag.flow.map((step, idx) => (
                      <span key={idx}>
                        <div className="flow-step">{step}</div>
                        {idx < ragData.traditional_rag.flow.length - 1 && (
                          <div className="flow-arrow">→</div>
                        )}
                      </span>
                    ))}
                  </div>
                  <div className="limitations">
                    <h6>한계점</h6>
                    <ul>
                      {ragData.traditional_rag.limitations.map((lim, idx) => (
                        <li key={idx}><AlertTriangle size={12} /> {lim}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Graph Enhanced RAG */}
                <div className="rag-flow enhanced">
                  <h5>🕸️ Graph-Enhanced RAG</h5>
                  <div className="flow-diagram vertical">
                    {ragData.graph_enhanced_rag.flow.map((step, idx) => (
                      <div key={idx} className="flow-step-detailed">
                        <div className="step-number">{idx + 1}</div>
                        <div className="step-content">
                          <div className="step-name">{step.step}</div>
                          <div className="step-desc">{step.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="advantages">
                    <h6>장점</h6>
                    <ul>
                      {ragData.graph_enhanced_rag.advantages.map((adv, idx) => (
                        <li key={idx}><CheckCircle size={12} /> {adv}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* 실제 예제 */}
              <div className="rag-example">
                <h5>실제 동작 예시</h5>
                <div className="example-query">
                  <strong>질문:</strong> {ragData.example.query}
                </div>
                <div className="graph-context">
                  <h6>🕸️ 그래프 컨텍스트</h6>
                  <div className="traversal-path">
                    {ragData.example.graph_context.traversal.map((path, idx) => (
                      <div key={idx} className="path-step">
                        <code>{path}</code>
                      </div>
                    ))}
                  </div>
                  <div className="related-info">
                    {ragData.example.graph_context.related_info.map((info, idx) => (
                      <span key={idx} className="info-tag">{info}</span>
                    ))}
                  </div>
                </div>
                <div className="enhanced-answer">
                  <h6>📝 향상된 응답</h6>
                  <p>{ragData.example.enhanced_answer}</p>
                </div>
              </div>
            </div>
          )}

          {/* 인덱스 탭 */}
          {activeTab === 'index' && indexData && (
            <div className="index-section">
              <h5>Neo4j 인덱스 타입</h5>
              <div className="index-grid">
                {indexData.types.map((idx_type, idx) => (
                  <div key={idx} className="index-card">
                    <h6>{idx_type.name}</h6>
                    <p>{idx_type.description}</p>
                    <div className="use-case">
                      <strong>사용 사례:</strong> {idx_type.use_case}
                    </div>
                    <pre className="syntax">{idx_type.syntax}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 3D 시각화 탭 */}
          {activeTab === 'graph3d' && graphData && (
            <div className="graph3d-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h5>3D 지식 그래프</h5>
                <button
                  className={`btn ${view3D ? 'btn-primary' : 'btn-outline'}`}
                  onClick={() => setView3D(!view3D)}
                >
                  <Eye size={14} /> {view3D ? '3D 활성화됨' : '2D 뷰'}
                </button>
              </div>
              <div style={{ height: '500px', background: 'var(--bg-tertiary)', borderRadius: '8px', overflow: 'hidden' }}>
                {view3D ? (
                  <KnowledgeGraph3D
                    graph={{
                      id: 'neo4j-graph',
                      name: 'Neo4j Knowledge Graph',
                      description: 'Interactive knowledge graph from Neo4j',
                      nodes: graphData.nodes.map(n => ({
                        id: n.id,
                        label: n.name,
                        type: n.label,
                        properties: n.properties
                      })),
                      edges: graphData.edges.map((e, i) => ({
                        id: `edge-${i}`,
                        source: e.from,
                        target: e.to,
                        type: e.type,
                        label: e.type
                      })),
                      metadata: {
                        createdAt: new Date().toISOString(),
                        updatedAt: new Date().toISOString(),
                        version: 1,
                        nodeCount: graphData.nodes.length,
                        edgeCount: graphData.edges.length
                      }
                    }}
                  />
                ) : (
                  <KnowledgeGraphViewer
                    graph={{
                      id: 'neo4j-graph',
                      name: 'Neo4j Knowledge Graph',
                      description: 'Interactive knowledge graph from Neo4j',
                      nodes: graphData.nodes.map(n => ({
                        id: n.id,
                        label: n.name,
                        type: n.label,
                        properties: n.properties
                      })),
                      edges: graphData.edges.map((e, i) => ({
                        id: `edge-${i}`,
                        source: e.from,
                        target: e.to,
                        type: e.type,
                        label: e.type
                      })),
                      metadata: {
                        createdAt: new Date().toISOString(),
                        updatedAt: new Date().toISOString(),
                        version: 1,
                        nodeCount: graphData.nodes.length,
                        edgeCount: graphData.edges.length
                      }
                    }}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default Neo4jPage;
