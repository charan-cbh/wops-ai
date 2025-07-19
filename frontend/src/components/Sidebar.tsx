import { ChatBubbleLeftRightIcon, ChartBarIcon, DocumentTextIcon, CogIcon } from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

interface SidebarProps {
  currentView: 'chat' | 'dashboard';
  onViewChange: (view: 'chat' | 'dashboard') => void;
  dashboardMetrics?: any;
}

export default function Sidebar({ currentView, onViewChange, dashboardMetrics }: SidebarProps) {
  const menuItems = [
    {
      id: 'chat' as const,
      name: 'Chat',
      icon: ChatBubbleLeftRightIcon,
      description: 'Ask questions about your data',
    },
    {
      id: 'dashboard' as const,
      name: 'Dashboard',
      icon: ChartBarIcon,
      description: 'View key metrics and insights',
    },
  ];

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo/Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <ChartBarIcon className="h-5 w-5 text-white" />
          </div>
          <div className="ml-3">
            <h1 className="text-lg font-semibold text-gray-900">WOPS AI</h1>
            <p className="text-sm text-gray-500">BI Assistant</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onViewChange(item.id)}
            className={clsx(
              'w-full flex items-center px-4 py-3 text-left rounded-lg transition-colors',
              currentView === item.id
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            )}
          >
            <item.icon className="h-5 w-5 mr-3" />
            <div>
              <div className="font-medium">{item.name}</div>
              <div className="text-sm text-gray-500">{item.description}</div>
            </div>
          </button>
        ))}
      </nav>

      {/* Status/Info */}
      <div className="p-4 border-t border-gray-200">
        <div className="bg-gray-50 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">System Status</span>
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          </div>
          
          {dashboardMetrics && (
            <div className="space-y-1">
              <div className="text-xs text-gray-500">
                Tables: {dashboardMetrics.available_tables?.length || 0}
              </div>
              <div className="text-xs text-gray-500">
                Last updated: {dashboardMetrics.last_updated 
                  ? new Date(dashboardMetrics.last_updated).toLocaleTimeString()
                  : 'Never'
                }
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}