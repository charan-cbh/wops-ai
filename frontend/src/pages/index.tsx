import { useState, useEffect } from 'react';
import Head from 'next/head';
import ChatInterface from '../components/ChatInterface';
import Sidebar from '../components/Sidebar';
import Dashboard from '../components/Dashboard';
// import WeeklyDigest from '../components/WeeklyDigest'; // REMOVED - Weekly digest functionality disabled
import { APIService } from '../services/api';

export default function Home() {
  const [currentView, setCurrentView] = useState<'chat' | 'dashboard'>('chat');
  const [dashboardMetrics, setDashboardMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardMetrics();
  }, []);

  const loadDashboardMetrics = async () => {
    try {
      const metrics = await APIService.getDashboardMetrics();
      setDashboardMetrics(metrics);
    } catch (error) {
      console.error('Error loading dashboard metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Worker Operations BI Chatbot</title>
        <meta name="description" content="Business Intelligence Chatbot for Worker Operations" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="flex h-screen bg-gray-50">
        <Sidebar
          currentView={currentView}
          onViewChange={setCurrentView}
          dashboardMetrics={dashboardMetrics}
        />
        
        <main className="flex-1 overflow-hidden">
          {currentView === 'chat' ? (
            <ChatInterface />
          ) : (
            <Dashboard metrics={dashboardMetrics} loading={loading} />
          )}
        </main>
      </div>
    </>
  );
}