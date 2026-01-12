import { Layers, RefreshCw } from 'lucide-react';
import type { Tab } from '@/types';

export interface DashboardHeaderProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  clusterStatus: string | null;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function DashboardHeader({
  tabs,
  activeTab,
  onTabChange,
  clusterStatus,
  onRefresh,
  isRefreshing,
}: DashboardHeaderProps) {
  const isActive = (tabId: string) => activeTab === tabId;

  return (
    <header className="header">
      <h1>
        <div className="logo">
          <Layers size={18} color="white" />
        </div>
        K3s Cluster Dashboard
      </h1>
      <div className="header-right">
        <div className="tab-buttons">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`tab-btn ${isActive(tab.id) ? 'active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="cluster-status">
          <span className={`status-dot ${clusterStatus || 'error'}`}></span>
          <span>{clusterStatus === 'healthy' ? '정상' : '점검 필요'}</span>
        </div>
        <button
          className={`btn-icon ${isRefreshing ? 'spinning' : ''}`}
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw size={16} />
        </button>
      </div>
    </header>
  );
}

export default DashboardHeader;
