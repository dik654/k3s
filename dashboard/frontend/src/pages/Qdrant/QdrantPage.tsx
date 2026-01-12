import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Database,
  RefreshCw,
  Plus,
  Trash2,
  Search,
  BookOpen,
  Folder,
  Tag,
  Shield,
  Layers,
  Settings,
  ChevronDown,
  CheckCircle,
  AlertCircle,
  Info,
  Archive,
  Play,
  X,
} from 'lucide-react';

const API_BASE = '/api';

interface Collection {
  name: string;
  vectors_count: number;
  points_count: number;
  status: string;
  config?: {
    params?: {
      vectors?: {
        size?: number;
        distance?: string;
      };
    };
  };
}

interface QdrantInfo {
  version: string;
  collections_count: number;
  total_vectors: number;
}

interface GuideData {
  collection_strategies: {
    title: string;
    description: string;
    strategies: Array<{
      icon: string;
      name: string;
      collections: Array<{
        name: string;
        description: string;
        example: string;
      }>;
      pros: string[];
      cons: string[];
    }>;
  };
  metadata_tagging: {
    title: string;
    description: string;
    required_fields: Array<{
      field: string;
      type: string;
      description: string;
      example: string;
    }>;
    recommended_fields: Array<{
      field: string;
      type: string;
      description: string;
      filter?: boolean;
    }>;
    filter_example: {
      description: string;
      code: string;
    };
  };
  rbac_implementation: {
    title: string;
    description: string;
    approaches: Array<{
      name: string;
      implementation: string;
      description: string;
      code: string;
    }>;
    best_practices: string[];
  };
  chunking_strategies: {
    title: string;
    description: string;
    strategies: Array<{
      type: string;
      chunk_size: string;
      overlap: string;
      method: string;
      tip: string;
    }>;
  };
  search_optimization: {
    title: string;
    tips: Array<{
      category: string;
      items: string[];
    }>;
  };
  maintenance: {
    title: string;
    tasks: Array<{
      task: string;
      frequency: string;
      description: string;
    }>;
    backup_strategy: {
      description: string;
      recommendations: string[];
    };
  };
}

interface QdrantPageProps {
  showToast: (message: string, type?: string) => void;
}

// Vector DB RAG Guide Component
function VectorDBRAGGuide() {
  const [guideData, setGuideData] = useState<GuideData | null>(null);
  const [activeSection, setActiveSection] = useState('collection');
  const [expandedStrategy, setExpandedStrategy] = useState(0);

  useEffect(() => {
    loadGuideData();
  }, []);

  const loadGuideData = async () => {
    try {
      const response = await axios.get('/api/vectordb/rag-guide');
      setGuideData(response.data);
    } catch (error) {
      console.error('Failed to load RAG guide:', error);
    }
  };

  if (!guideData) return null;

  const sections = [
    { key: 'collection', label: '컬렉션 전략', icon: <Folder size={14} /> },
    { key: 'metadata', label: '메타데이터', icon: <Tag size={14} /> },
    { key: 'rbac', label: 'RBAC', icon: <Shield size={14} /> },
    { key: 'chunking', label: '청킹', icon: <Layers size={14} /> },
    { key: 'search', label: '검색 최적화', icon: <Search size={14} /> },
    { key: 'maintenance', label: '유지보수', icon: <Settings size={14} /> }
  ];

  return (
    <div className="rag-guide-card">
      <div className="guide-header">
        <h4><BookOpen size={18} /> Vector DB RAG 관리 가이드</h4>
        <p>효과적인 RAG 시스템 구축을 위한 실무 가이드</p>
      </div>

      <div className="guide-nav">
        {sections.map(section => (
          <button
            key={section.key}
            className={activeSection === section.key ? 'active' : ''}
            onClick={() => setActiveSection(section.key)}
          >
            {section.icon} {section.label}
          </button>
        ))}
      </div>

      <div className="guide-content">
        {/* 컬렉션 전략 */}
        {activeSection === 'collection' && (
          <div className="collection-section">
            <div className="section-header">
              <h5>{guideData.collection_strategies.title}</h5>
              <p>{guideData.collection_strategies.description}</p>
            </div>

            <div className="strategies-accordion">
              {guideData.collection_strategies.strategies.map((strategy, idx) => (
                <div key={idx} className={`strategy-item ${expandedStrategy === idx ? 'expanded' : ''}`}>
                  <div
                    className="strategy-header"
                    onClick={() => setExpandedStrategy(expandedStrategy === idx ? -1 : idx)}
                  >
                    <span className="strategy-icon">{strategy.icon}</span>
                    <span className="strategy-name">{strategy.name}</span>
                    <ChevronDown size={16} className={`chevron ${expandedStrategy === idx ? 'rotated' : ''}`} />
                  </div>

                  {expandedStrategy === idx && (
                    <div className="strategy-content">
                      <div className="collections-grid">
                        {strategy.collections.map((col, cidx) => (
                          <div key={cidx} className="collection-item">
                            <div className="col-name">{col.name}</div>
                            <div className="col-desc">{col.description}</div>
                            <div className="col-example">{col.example}</div>
                          </div>
                        ))}
                      </div>
                      <div className="pros-cons">
                        <div className="pros">
                          <h6><CheckCircle size={12} /> 장점</h6>
                          <ul>
                            {strategy.pros.map((pro, pidx) => (
                              <li key={pidx}>{pro}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="cons">
                          <h6><AlertCircle size={12} /> 단점</h6>
                          <ul>
                            {strategy.cons.map((con, cidx) => (
                              <li key={cidx}>{con}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 메타데이터 태깅 */}
        {activeSection === 'metadata' && (
          <div className="metadata-section">
            <div className="section-header">
              <h5>{guideData.metadata_tagging.title}</h5>
              <p>{guideData.metadata_tagging.description}</p>
            </div>

            <div className="fields-grid">
              <div className="fields-column required">
                <h6>필수 필드</h6>
                {guideData.metadata_tagging.required_fields.map((field, idx) => (
                  <div key={idx} className="field-card">
                    <div className="field-header">
                      <code className="field-name">{field.field}</code>
                      <span className="field-type">{field.type}</span>
                    </div>
                    <div className="field-desc">{field.description}</div>
                    <div className="field-example">예: {field.example}</div>
                  </div>
                ))}
              </div>
              <div className="fields-column recommended">
                <h6>권장 필드</h6>
                {guideData.metadata_tagging.recommended_fields.map((field, idx) => (
                  <div key={idx} className="field-card">
                    <div className="field-header">
                      <code className="field-name">{field.field}</code>
                      <span className="field-type">{field.type}</span>
                      {field.filter && <span className="filter-badge">필터용</span>}
                    </div>
                    <div className="field-desc">{field.description}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="filter-example">
              <h6>{guideData.metadata_tagging.filter_example.description}</h6>
              <pre>{guideData.metadata_tagging.filter_example.code}</pre>
            </div>
          </div>
        )}

        {/* RBAC */}
        {activeSection === 'rbac' && (
          <div className="rbac-section">
            <div className="section-header">
              <h5>{guideData.rbac_implementation.title}</h5>
              <p>{guideData.rbac_implementation.description}</p>
            </div>

            <div className="rbac-approaches">
              {guideData.rbac_implementation.approaches.map((approach, idx) => (
                <div key={idx} className="approach-card">
                  <div className="approach-header">
                    <h6>{approach.name}</h6>
                    <span className="approach-impl">{approach.implementation}</span>
                  </div>
                  <p>{approach.description}</p>
                  <pre className="approach-code">{approach.code}</pre>
                </div>
              ))}
            </div>

            <div className="best-practices">
              <h6><CheckCircle size={14} /> 베스트 프랙티스</h6>
              <ul>
                {guideData.rbac_implementation.best_practices.map((practice, idx) => (
                  <li key={idx}>{practice}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* 청킹 전략 */}
        {activeSection === 'chunking' && (
          <div className="chunking-section">
            <div className="section-header">
              <h5>{guideData.chunking_strategies.title}</h5>
              <p>{guideData.chunking_strategies.description}</p>
            </div>

            <div className="chunking-grid">
              {guideData.chunking_strategies.strategies.map((strategy, idx) => (
                <div key={idx} className="chunking-card">
                  <div className="chunking-type">{strategy.type}</div>
                  <div className="chunking-details">
                    <div className="detail-row">
                      <span className="label">청크 크기</span>
                      <span className="value">{strategy.chunk_size}</span>
                    </div>
                    <div className="detail-row">
                      <span className="label">오버랩</span>
                      <span className="value">{strategy.overlap}</span>
                    </div>
                    <div className="detail-row">
                      <span className="label">분리 방법</span>
                      <span className="value">{strategy.method}</span>
                    </div>
                  </div>
                  <div className="chunking-tip">
                    <Info size={12} /> {strategy.tip}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 검색 최적화 */}
        {activeSection === 'search' && (
          <div className="search-section">
            <div className="section-header">
              <h5>{guideData.search_optimization.title}</h5>
            </div>

            <div className="optimization-grid">
              {guideData.search_optimization.tips.map((tip, idx) => (
                <div key={idx} className="tip-card">
                  <h6>{tip.category}</h6>
                  <ul>
                    {tip.items.map((item, iidx) => (
                      <li key={iidx}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 유지보수 */}
        {activeSection === 'maintenance' && (
          <div className="maintenance-section">
            <div className="section-header">
              <h5>{guideData.maintenance.title}</h5>
            </div>

            <div className="tasks-grid">
              {guideData.maintenance.tasks.map((task, idx) => (
                <div key={idx} className="task-card">
                  <div className="task-header">
                    <span className="task-name">{task.task}</span>
                    <span className="task-frequency">{task.frequency}</span>
                  </div>
                  <p>{task.description}</p>
                </div>
              ))}
            </div>

            <div className="backup-section">
              <h6><Archive size={14} /> {guideData.maintenance.backup_strategy.description}</h6>
              <ul>
                {guideData.maintenance.backup_strategy.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function QdrantPage({ showToast }: QdrantPageProps) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [qdrantInfo, setQdrantInfo] = useState<QdrantInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [showCreateCollection, setShowCreateCollection] = useState(false);
  const [showSearchDemo, setShowSearchDemo] = useState(false);
  const [newCollection, setNewCollection] = useState({
    name: '',
    vector_size: 384,
    distance: 'Cosine'
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{ id: string; score: number; payload: Record<string, unknown> }>>([]);
  const [searching, setSearching] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [collectionsRes, infoRes] = await Promise.all([
        axios.get(`${API_BASE}/qdrant/collections`).catch(() => ({ data: { collections: [] } })),
        axios.get(`${API_BASE}/qdrant/info`).catch(() => ({ data: null })),
      ]);
      setCollections(collectionsRes.data.collections || []);
      setQdrantInfo(infoRes.data);
    } catch (error) {
      console.error('Qdrant fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateCollection = async () => {
    if (!newCollection.name.trim()) {
      showToast('컬렉션 이름을 입력하세요', 'error');
      return;
    }
    try {
      await axios.post(`${API_BASE}/qdrant/collections`, newCollection);
      showToast(`컬렉션 '${newCollection.name}'이 생성되었습니다`);
      setShowCreateCollection(false);
      setNewCollection({ name: '', vector_size: 384, distance: 'Cosine' });
      fetchData();
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      showToast(axiosError.response?.data?.detail || '컬렉션 생성 실패', 'error');
    }
  };

  const handleDeleteCollection = async (name: string) => {
    if (!confirm(`컬렉션 '${name}'을 삭제하시겠습니까?`)) return;
    try {
      await axios.delete(`${API_BASE}/qdrant/collections/${name}`);
      showToast(`컬렉션 '${name}'이 삭제되었습니다`);
      fetchData();
    } catch {
      showToast('컬렉션 삭제 실패', 'error');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() || !selectedCollection) {
      showToast('검색어와 컬렉션을 선택하세요', 'error');
      return;
    }
    setSearching(true);
    try {
      const res = await axios.post(`${API_BASE}/qdrant/search`, {
        collection: selectedCollection,
        query: searchQuery,
        limit: 10
      });
      setSearchResults(res.data.results || []);
      setShowSearchDemo(true);
    } catch {
      showToast('검색 실패', 'error');
    } finally {
      setSearching(false);
    }
  };

  if (loading) {
    return (
      <section className="section">
        <div className="card">
          <div className="loading-container">
            <div className="spinner large"></div>
            <p>Qdrant 정보를 불러오는 중...</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="section">
      <div className="section-header">
        <h2 className="section-title">
          <Database size={24} /> Qdrant Vector Database
        </h2>
        <div className="benchmark-actions">
          <button className="btn btn-outline" onClick={fetchData}>
            <RefreshCw size={16} />
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreateCollection(true)}>
            <Plus size={16} /> 컬렉션 생성
          </button>
        </div>
      </div>

      {/* Qdrant Info */}
      {qdrantInfo && (
        <div className="card" style={{ marginBottom: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', padding: '16px' }}>
            <div className="stat-item">
              <span className="stat-label">버전</span>
              <span className="stat-value">{qdrantInfo.version}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">컬렉션 수</span>
              <span className="stat-value">{qdrantInfo.collections_count}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">총 벡터 수</span>
              <span className="stat-value">{qdrantInfo.total_vectors?.toLocaleString()}</span>
            </div>
          </div>
        </div>
      )}

      {/* Collections Grid */}
      <div className="card">
        <div className="card-header">
          <h3><Folder size={18} /> 컬렉션 목록</h3>
        </div>
        <div style={{ padding: '16px' }}>
          {collections.length === 0 ? (
            <div className="empty-state">
              <Database size={48} color="var(--text-muted)" />
              <p>생성된 컬렉션이 없습니다</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
              {collections.map((collection) => (
                <div
                  key={collection.name}
                  className={`config-card ${selectedCollection === collection.name ? 'selected' : ''}`}
                  onClick={() => setSelectedCollection(collection.name)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="config-card-header">
                    <span className="config-name">{collection.name}</span>
                    <div className="config-card-actions">
                      <button
                        className="config-delete-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteCollection(collection.name);
                        }}
                        title="삭제"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                  <div className="config-card-params">
                    <div className="param-item">
                      <span className="param-label">벡터 수</span>
                      <span className="param-value">{collection.vectors_count?.toLocaleString()}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">포인트 수</span>
                      <span className="param-value">{collection.points_count?.toLocaleString()}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">상태</span>
                      <span className={`param-value ${collection.status === 'green' ? 'success' : ''}`}>
                        {collection.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Search Demo */}
      <div className="card" style={{ marginTop: '16px' }}>
        <div className="card-header">
          <h3><Search size={18} /> 벡터 검색 데모</h3>
        </div>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <select
              value={selectedCollection || ''}
              onChange={(e) => setSelectedCollection(e.target.value)}
              style={{ flex: '0 0 200px' }}
            >
              <option value="">컬렉션 선택</option>
              {collections.map(c => (
                <option key={c.name} value={c.name}>{c.name}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="검색어 입력..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ flex: 1 }}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button className="btn btn-primary" onClick={handleSearch} disabled={searching}>
              {searching ? <div className="spinner" /> : <><Play size={16} /> 검색</>}
            </button>
          </div>

          {searchResults.length > 0 && (
            <div className="results-list">
              <h4>검색 결과 ({searchResults.length}개)</h4>
              {searchResults.map((result, idx) => (
                <div key={idx} className="result-card" style={{ marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>ID: {result.id}</span>
                    <span className="result-metric success">
                      유사도: {(result.score * 100).toFixed(1)}%
                    </span>
                  </div>
                  {result.payload && (
                    <pre style={{ fontSize: '11px', marginTop: '8px', background: 'var(--bg-tertiary)', padding: '8px', borderRadius: '4px', overflow: 'auto' }}>
                      {JSON.stringify(result.payload, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* RAG Guide */}
      <div style={{ marginTop: '16px' }}>
        <VectorDBRAGGuide />
      </div>

      {/* Create Collection Modal */}
      {showCreateCollection && (
        <div className="modal-overlay" onClick={() => setShowCreateCollection(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>새 컬렉션 생성</h3>
              <button className="btn-icon" onClick={() => setShowCreateCollection(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>컬렉션 이름</label>
                <input
                  type="text"
                  value={newCollection.name}
                  onChange={(e) => setNewCollection({ ...newCollection, name: e.target.value })}
                  placeholder="my_collection"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>벡터 크기</label>
                  <input
                    type="number"
                    value={newCollection.vector_size}
                    onChange={(e) => setNewCollection({ ...newCollection, vector_size: parseInt(e.target.value) || 384 })}
                  />
                </div>
                <div className="form-group">
                  <label>거리 메트릭</label>
                  <select
                    value={newCollection.distance}
                    onChange={(e) => setNewCollection({ ...newCollection, distance: e.target.value })}
                  >
                    <option value="Cosine">Cosine</option>
                    <option value="Euclidean">Euclidean</option>
                    <option value="Dot">Dot Product</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setShowCreateCollection(false)}>취소</button>
              <button className="btn btn-primary" onClick={handleCreateCollection}>생성</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default QdrantPage;
