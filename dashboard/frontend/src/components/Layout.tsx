import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  Workflow,
  Settings,
  PlusCircle,
  Brain,
  Share2,
  Sparkles,
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { path: '/workflows', label: 'Workflows', icon: Workflow },
  { path: '/knowledge', label: 'Knowledge Graph', icon: Share2 },
  { path: '/embeddings', label: 'Embeddings', icon: Sparkles },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Layout() {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-dark-900">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-800 border-r border-dark-700 flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center gap-2 px-4 border-b border-dark-700">
          <Brain className="w-8 h-8 text-primary-500" />
          <span className="text-lg font-semibold text-white">AI Workflow</span>
        </div>

        {/* New Workflow Button */}
        <div className="p-4">
          <Link
            to="/workflows/new"
            className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
          >
            <PlusCircle className="w-5 h-5" />
            New Workflow
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            const Icon = item.icon;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg mb-1 transition-colors',
                  isActive
                    ? 'bg-dark-700 text-white'
                    : 'text-dark-300 hover:bg-dark-700 hover:text-white'
                )}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-dark-700">
          <div className="text-xs text-dark-400">
            AI Workflow Builder v1.0.0
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
