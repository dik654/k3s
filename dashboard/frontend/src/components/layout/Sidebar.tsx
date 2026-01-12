import { NavLink } from 'react-router-dom';
import clsx from 'clsx';
import {
  LayoutDashboard,
  Server,
  Cpu,
  Database,
  Brain,
  Activity,
  Settings,
  Layers,
} from 'lucide-react';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
}

const navItems: NavItem[] = [
  { to: '/', icon: <LayoutDashboard size={20} />, label: '개요' },
  { to: '/infrastructure', icon: <Server size={20} />, label: '인프라' },
  { to: '/ai-workloads', icon: <Cpu size={20} />, label: 'AI 워크로드' },
  { to: '/agent', icon: <Brain size={20} />, label: 'Agent' },
  { to: '/monitoring', icon: <Activity size={20} />, label: '모니터링' },
  { to: '/storage', icon: <Database size={20} />, label: '스토리지' },
  { to: '/settings', icon: <Settings size={20} />, label: '설정' },
];

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-slate-900 border-r border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center gap-3 px-4 border-b border-slate-800">
        <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
          <Layers size={20} className="text-white" />
        </div>
        <div>
          <h1 className="font-semibold text-white text-sm">K3s Dashboard</h1>
          <p className="text-[10px] text-slate-500">Cluster Management</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600/20 text-blue-400'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              )
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800">
        <div className="text-xs text-slate-500">
          <p>v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
