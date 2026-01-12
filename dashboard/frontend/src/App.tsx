import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import {
  Server,
  Activity,
  HardDrive,
  Database,
  BarChart3,
  Settings,
  Layers,
  Workflow,
  Target,
  Image,
  Brain,
  MessageSquare,
  FileText,
  Cpu,
  Box
} from 'lucide-react';

// Import pages
import {
  OverviewPage,
  BenchmarkPage,
  PipelinePage,
  QdrantPage,
  ComfyUIPage,
  Neo4jPage,
  LLMPage,
  AgentPage,
  GoalPage,
  ParserPage,
  GpuPage,
  PodsPage,
  StoragePage,
  ClusterPage,
  BaremetalPage
} from './pages';

// Import CSS
import './index.css';

// Tab configuration
interface TabConfig {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
}

const tabs: TabConfig[] = [
  { id: 'overview', label: 'Overview', icon: <Server size={16} />, path: '/' },
  { id: 'goal', label: 'Goal', icon: <Target size={16} />, path: '/goal' },
  { id: 'pods', label: 'Pods', icon: <Box size={16} />, path: '/pods' },
  { id: 'gpu', label: 'GPU', icon: <Cpu size={16} />, path: '/gpu' },
  { id: 'storage', label: 'Storage', icon: <HardDrive size={16} />, path: '/storage' },
  { id: 'benchmark', label: 'Benchmark', icon: <BarChart3 size={16} />, path: '/benchmark' },
  { id: 'cluster', label: 'Cluster', icon: <Settings size={16} />, path: '/cluster' },
  { id: 'agent', label: 'Agent', icon: <Workflow size={16} />, path: '/agent' },
  { id: 'pipeline', label: 'Pipeline', icon: <Activity size={16} />, path: '/pipeline' },
  { id: 'qdrant', label: 'Qdrant', icon: <Database size={16} />, path: '/qdrant' },
  { id: 'comfyui', label: 'ComfyUI', icon: <Image size={16} />, path: '/comfyui' },
  { id: 'neo4j', label: 'Neo4j', icon: <Brain size={16} />, path: '/neo4j' },
  { id: 'llm', label: 'LLM', icon: <MessageSquare size={16} />, path: '/llm' },
  { id: 'parser', label: 'Parser', icon: <FileText size={16} />, path: '/parser' },
  { id: 'baremetal', label: 'Baremetal', icon: <Server size={16} />, path: '/baremetal' }
];

// Path to tab mapping
const pathToTab: Record<string, string> = {
  '/': 'overview',
  '/overview': 'overview',
  '/goal': 'goal',
  '/pods': 'pods',
  '/gpu': 'gpu',
  '/storage': 'storage',
  '/benchmark': 'benchmark',
  '/cluster': 'cluster',
  '/agent': 'agent',
  '/pipeline': 'pipeline',
  '/qdrant': 'qdrant',
  '/comfyui': 'comfyui',
  '/neo4j': 'neo4j',
  '/llm': 'llm',
  '/parser': 'parser',
  '/baremetal': 'baremetal'
};

// Toast notification component
interface Toast {
  message: string;
  type: 'success' | 'error' | 'info';
}

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<string>(() => pathToTab[location.pathname] || 'overview');
  const [toast, setToast] = useState<Toast | null>(null);

  // Sync tab with URL
  useEffect(() => {
    // /agent/workflow/:id 같은 경로도 agent 탭으로 매핑
    let newTab = pathToTab[location.pathname] || 'overview';
    if (location.pathname.startsWith('/agent')) {
      newTab = 'agent';
    }
    if (newTab !== activeTab) {
      setActiveTab(newTab);
    }
  }, [location.pathname, activeTab]);

  // Handle tab change
  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId);
    const tab = tabs.find(t => t.id === tabId);
    if (tab) {
      navigate(tab.path);
    }
  };

  // Show toast notification
  const showToast = (message: string, type?: string) => {
    const toastType = (type === 'success' || type === 'error' || type === 'info') ? type : 'info';
    setToast({ message, type: toastType });
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1 className="header-title">
            <Layers size={24} />
            K3s Cluster Dashboard
          </h1>
        </div>
        <div className="header-right">
          <span className="version-badge">v2.0 TypeScript</span>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="tab-nav">
        <div className="tab-container">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => handleTabChange(tab.id)}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/goal" element={<GoalPage />} />
          <Route path="/pods" element={<PodsPage />} />
          <Route path="/gpu" element={<GpuPage />} />
          <Route path="/storage" element={<StoragePage showToast={showToast} />} />
          <Route path="/benchmark" element={<BenchmarkPage showToast={showToast} />} />
          <Route path="/cluster" element={<ClusterPage showToast={showToast} />} />
          <Route path="/agent/*" element={<AgentPage />} />
          <Route path="/pipeline" element={<PipelinePage showToast={showToast} />} />
          <Route path="/qdrant" element={<QdrantPage showToast={showToast} />} />
          <Route path="/comfyui" element={<ComfyUIPage showToast={showToast} />} />
          <Route path="/neo4j" element={<Neo4jPage showToast={showToast} />} />
          <Route path="/llm" element={<LLMPage showToast={showToast} />} />
          <Route path="/parser" element={<ParserPage />} />
          <Route path="/baremetal" element={<BaremetalPage />} />
        </Routes>
      </main>

      {/* Toast Notification */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

// App Wrapper with Router
function AppWrapper() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<App />} />
      </Routes>
    </BrowserRouter>
  );
}

export default AppWrapper;
