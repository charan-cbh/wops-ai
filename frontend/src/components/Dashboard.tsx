import { useEffect, useState } from 'react';
import { ChartBarIcon, TableCellsIcon, ClockIcon, EyeIcon, BeakerIcon, SparklesIcon, ArrowTrendingUpIcon, UsersIcon, CalendarIcon } from '@heroicons/react/24/outline';
import { APIService } from '../services/api';

interface DashboardProps {
  metrics?: any;
  loading?: boolean;
}

interface TableSchema {
  [key: string]: {
    type: string;
    nullable: boolean;
    default: any;
  };
}

interface SampleData {
  table_name: string;
  sample_data: any[];
  columns: string[];
}

export default function Dashboard({ metrics: propMetrics, loading: propLoading }: DashboardProps) {
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [tables, setTables] = useState<string[]>([]);
  const [dashboardMetrics, setDashboardMetrics] = useState<any>(null);
  const [feedbackStats, setFeedbackStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableSchema, setTableSchema] = useState<TableSchema | null>(null);
  const [sampleData, setSampleData] = useState<SampleData | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadAnalyses(),
        loadTables(),
        loadDashboardMetrics(),
        loadFeedbackStats()
      ]);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAnalyses = async () => {
    try {
      const response = await APIService.getAvailableAnalyses();
      setAnalyses(response.analyses || []);
    } catch (error) {
      console.error('Error loading analyses:', error);
    }
  };

  const loadTables = async () => {
    try {
      const response = await APIService.getAvailableTables();
      setTables(response.tables || []);
    } catch (error) {
      console.error('Error loading tables:', error);
    }
  };

  const loadDashboardMetrics = async () => {
    try {
      const response = await APIService.getDashboardMetrics();
      setDashboardMetrics(response);
    } catch (error) {
      console.error('Error loading dashboard metrics:', error);
    }
  };

  const loadFeedbackStats = async () => {
    try {
      const response = await APIService.getFeedbackStats(30);
      setFeedbackStats(response);
    } catch (error) {
      console.error('Error loading feedback stats:', error);
    }
  };

  const handleViewSchema = async (tableName: string) => {
    setSchemaLoading(true);
    setSelectedTable(tableName);
    setError(null);
    try {
      const response = await APIService.getTableSchema(tableName);
      if (response && response.schema) {
        setTableSchema(response.schema);
        setSampleData(null); // Clear sample data when viewing schema
      } else {
        throw new Error('No schema data received');
      }
    } catch (error) {
      console.error('Error loading table schema:', error);
      setError(`Failed to load schema for ${tableName}. Please try again.`);
    } finally {
      setSchemaLoading(false);
    }
  };

  const handleViewSampleData = async (tableName: string) => {
    setSampleLoading(true);
    setSelectedTable(tableName);
    setError(null);
    try {
      const response = await APIService.getTableSample(tableName, 10);
      if (response && response.sample_data) {
        setSampleData(response);
        setTableSchema(null); // Clear schema when viewing sample data
      } else {
        throw new Error('No sample data received');
      }
    } catch (error) {
      console.error('Error loading sample data:', error);
      setError(`Failed to load sample data for ${tableName}. Please try again.`);
    } finally {
      setSampleLoading(false);
    }
  };

  const closeModal = () => {
    setSelectedTable(null);
    setTableSchema(null);
    setSampleData(null);
    setError(null);
  };

  if (loading || propLoading) {
    return (
      <div className="flex items-center justify-center h-full min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-lg border border-white/20">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <ChartBarIcon className="h-6 w-6 text-blue-600" />
              </div>
            </div>
            <div>
              <p className="text-gray-700 font-medium text-lg">Loading Dashboard...</p>
              <p className="text-gray-500 text-sm">Gathering your business intelligence</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Modern Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <div className="flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl shadow-lg">
              <ChartBarIcon className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-700 to-purple-700 bg-clip-text text-transparent">
                Worker Operations Dashboard
              </h1>
              <p className="text-gray-600 flex items-center">
                <SparklesIcon className="h-4 w-4 mr-1 text-blue-500" />
                Real-time insights and analytics for your operations
              </p>
            </div>
          </div>
        </div>

        {/* Modern Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Data Sources</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{tables.length}</p>
                <p className="text-xs text-blue-600 font-medium mt-1">Tables Available</p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                <TableCellsIcon className="h-6 w-6 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Analyses</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{analyses.length}</p>
                <p className="text-xs text-emerald-600 font-medium mt-1">Ready to Use</p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg">
                <ChartBarIcon className="h-6 w-6 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Data Records</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {dashboardMetrics?.metrics ? Object.keys(dashboardMetrics.metrics).length : '0'}
                </p>
                <p className="text-xs text-purple-600 font-medium mt-1">Tracked Metrics</p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <ArrowTrendingUpIcon className="h-6 w-6 text-white" />
              </div>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">User Feedback</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">
                  {feedbackStats?.average_rating ? `${feedbackStats.average_rating}/5` : 'N/A'}
                </p>
                <p className="text-xs text-orange-600 font-medium mt-1">
                  {feedbackStats?.total_ratings ? `${feedbackStats.total_ratings} ratings` : 'No ratings yet'}
                </p>
              </div>
              <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center shadow-lg">
                <UsersIcon className="h-6 w-6 text-white" />
              </div>
            </div>
          </div>
        </div>

        {/* Modern Available Analyses */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center">
              <ChartBarIcon className="h-4 w-4 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Pre-built Analytics</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {analyses.map((analysis, index) => (
              <div key={index} className="group bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 shadow-lg hover:shadow-xl transition-all duration-200 hover:-translate-y-1 cursor-pointer">
                <div className="flex items-start space-x-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-200">
                    <SparklesIcon className="h-6 w-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-900 mb-2 group-hover:text-blue-700 transition-colors">{analysis.name}</h3>
                    <p className="text-sm text-gray-600 mb-4 leading-relaxed">{analysis.description}</p>
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-blue-100 to-purple-100 text-blue-800 border border-blue-200">
                        {analysis.category}
                      </span>
                      <button className="text-blue-600 hover:text-blue-800 font-medium text-sm flex items-center space-x-1 group-hover:translate-x-1 transition-transform duration-200">
                        <span>Run Analysis</span>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Modern Database Tables */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
              <TableCellsIcon className="h-4 w-4 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Data Sources</h2>
          </div>
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200/50">
                <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                  <tr>
                    <th className="px-8 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider border-b border-gray-200/50">
                      Table Name
                    </th>
                    <th className="px-8 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider border-b border-gray-200/50">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-gradient-to-br from-white to-gray-50/30 divide-y divide-gray-200/30">
                  {tables.map((table, index) => (
                    <tr key={index} className="hover:bg-white/60 transition-colors duration-150 group">
                      <td className="px-8 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shadow-sm">
                            <TableCellsIcon className="h-4 w-4 text-white" />
                          </div>
                          <span className="text-sm font-bold text-gray-900 group-hover:text-blue-700 transition-colors">{table}</span>
                        </div>
                      </td>
                      <td className="px-8 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-3">
                          <button 
                            onClick={() => handleViewSchema(table)}
                            disabled={schemaLoading && selectedTable === table}
                            className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-xs font-medium rounded-lg hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-sm hover:shadow-md transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {schemaLoading && selectedTable === table ? (
                              <div className="animate-spin rounded-full h-3 w-3 border border-white border-t-transparent mr-2"></div>
                            ) : (
                              <EyeIcon className="h-3 w-3 mr-2" />
                            )}
                            Schema
                          </button>
                          <button 
                            onClick={() => handleViewSampleData(table)}
                            disabled={sampleLoading && selectedTable === table}
                            className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white text-xs font-medium rounded-lg hover:from-emerald-600 hover:to-emerald-700 transition-all duration-200 shadow-sm hover:shadow-md transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {sampleLoading && selectedTable === table ? (
                              <div className="animate-spin rounded-full h-3 w-3 border border-white border-t-transparent mr-2"></div>
                            ) : (
                              <BeakerIcon className="h-3 w-3 mr-2" />
                            )}
                            Sample
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Modal for Schema and Sample Data */}
        {(tableSchema || sampleData) && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
              <div className="flex items-center justify-between p-6 border-b border-gray-200/50 bg-gradient-to-r from-blue-50 to-purple-50">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                    {tableSchema ? <EyeIcon className="h-4 w-4 text-white" /> : <BeakerIcon className="h-4 w-4 text-white" />}
                  </div>
                  <h3 className="text-xl font-bold text-gray-900">
                    {tableSchema ? 'Table Schema' : 'Sample Data'} - {selectedTable}
                  </h3>
                </div>
                <button
                  onClick={closeModal}
                  className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors"
                >
                  <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="p-6 overflow-auto max-h-[calc(90vh-100px)]">
                {error && (
                  <div className="mb-4 bg-red-50 border border-red-200/50 rounded-xl p-4">
                    <div className="flex items-center space-x-2">
                      <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center">
                        <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <p className="text-red-700 font-medium">{error}</p>
                    </div>
                  </div>
                )}
                
                {tableSchema && (
                  <div className="space-y-4">
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-4 border border-blue-200/50">
                      <h4 className="font-semibold text-gray-800 mb-2">Schema Information</h4>
                      <p className="text-sm text-gray-600">Column definitions and data types for {selectedTable}</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Column Name</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data Type</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nullable</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Default</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {Object.entries(tableSchema).map(([columnName, columnInfo]) => (
                            <tr key={columnName} className="hover:bg-gray-50">
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{columnName}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  {columnInfo.type}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{columnInfo.nullable ? 'Yes' : 'No'}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{columnInfo.default || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                
                {sampleData && (
                  <div className="space-y-4">
                    <div className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl p-4 border border-emerald-200/50">
                      <h4 className="font-semibold text-gray-800 mb-2">Sample Data</h4>
                      <p className="text-sm text-gray-600">Recent records from {selectedTable} ({sampleData.sample_data.length} rows)</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            {sampleData.columns.map((column) => (
                              <th key={column} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {column}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {sampleData.sample_data.map((row, index) => (
                            <tr key={index} className="hover:bg-gray-50">
                              {sampleData.columns.map((column) => (
                                <td key={column} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {row[column] !== null && row[column] !== undefined
                                    ? String(row[column])
                                    : <span className="text-gray-400 italic">—</span>}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}