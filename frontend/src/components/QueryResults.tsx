import { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon, TableCellsIcon, CodeBracketIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import DataVisualization from './DataVisualization';

interface QueryResultsProps {
  data: any[];
  insights?: string[];
  sqlQuery?: string;
  showInsights?: boolean; // New prop to control insights display
  charts?: any[]; // Chart data for visualization
}

export default function QueryResults({ data, insights, sqlQuery, showInsights = true, charts }: QueryResultsProps) {
  const [showData, setShowData] = useState(false);
  const [showSQL, setShowSQL] = useState(false);

  if (!data || data.length === 0) {
    return null;
  }

  const columns = Object.keys(data[0] || {});
  const displayData = data.slice(0, 100); // Limit display for performance

  return (
    <div className="mt-6 space-y-6">
      {/* Modern Insights Card */}
      {showInsights && insights && insights.length > 0 && (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200/50 rounded-2xl p-6 shadow-lg">
          <div className="flex items-center mb-4">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center mr-3">
              <DocumentTextIcon className="h-4 w-4 text-white" />
            </div>
            <h4 className="text-lg font-semibold text-blue-900">Key Insights</h4>
          </div>
          <ul className="space-y-3">
            {insights.map((insight, index) => (
              <li key={index} className="flex items-start group">
                <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mr-3 mt-0.5">
                  <span className="text-white text-xs font-bold">{index + 1}</span>
                </div>
                <span className="text-blue-800 font-medium leading-relaxed group-hover:text-blue-900 transition-colors">
                  {insight}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Modern SQL Query Card */}
      {sqlQuery && (
        <div className="bg-white/80 backdrop-blur-sm border border-gray-200/50 rounded-2xl shadow-lg overflow-hidden">
          <button
            onClick={() => setShowSQL(!showSQL)}
            className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50/80 transition-all duration-200 group"
          >
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center group-hover:from-emerald-600 group-hover:to-teal-700 transition-all duration-200">
                <CodeBracketIcon className="h-4 w-4 text-white" />
              </div>
              <span className="font-semibold text-gray-700 group-hover:text-gray-900">SQL Query</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full font-medium">Generated</span>
              {showSQL ? (
                <ChevronUpIcon className="h-5 w-5 text-gray-500 group-hover:text-emerald-600 transition-colors" />
              ) : (
                <ChevronDownIcon className="h-5 w-5 text-gray-500 group-hover:text-emerald-600 transition-colors" />
              )}
            </div>
          </button>
          
          {showSQL && (
            <div className="border-t border-gray-200/50">
              <SyntaxHighlighter
                language="sql"
                style={oneDark}
                customStyle={{
                  margin: 0,
                  borderRadius: '0 0 1rem 1rem',
                  fontSize: '0.875rem',
                  background: 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)',
                }}
              >
                {sqlQuery}
              </SyntaxHighlighter>
            </div>
          )}
        </div>
      )}

      {/* Modern Data Table Card */}
      <div className="bg-white/80 backdrop-blur-sm border border-gray-200/50 rounded-2xl shadow-lg overflow-hidden">
        <button
          onClick={() => setShowData(!showData)}
          className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50/80 transition-all duration-200 group"
        >
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center group-hover:from-purple-600 group-hover:to-pink-700 transition-all duration-200">
              <TableCellsIcon className="h-4 w-4 text-white" />
            </div>
            <span className="font-semibold text-gray-700 group-hover:text-gray-900">
              Data Results
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full font-medium">{data.length} rows</span>
            {showData ? (
              <ChevronUpIcon className="h-5 w-5 text-gray-500 group-hover:text-purple-600 transition-colors" />
            ) : (
              <ChevronDownIcon className="h-5 w-5 text-gray-500 group-hover:text-purple-600 transition-colors" />
            )}
          </div>
        </button>
        
        {showData && (
          <div className="border-t border-gray-200/50 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200/50">
              <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                <tr>
                  {columns.map((column) => (
                    <th
                      key={column}
                      className="px-6 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider border-b border-gray-200/50"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-gradient-to-br from-white to-gray-50/30 divide-y divide-gray-200/30">
                {displayData.map((row, index) => (
                  <tr key={index} className="hover:bg-white/60 transition-colors duration-150">
                    {columns.map((column) => (
                      <td
                        key={column}
                        className="px-6 py-3 whitespace-nowrap text-sm text-gray-800 font-medium"
                      >
                        {row[column] !== null && row[column] !== undefined
                          ? String(row[column])
                          : <span className="text-gray-400 italic">—</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            
            {data.length > 100 && (
              <div className="px-6 py-4 bg-gradient-to-r from-purple-50 to-pink-50 border-t border-purple-200/50 text-sm text-purple-700 font-medium text-center">
                📊 Showing first 100 rows of {data.length} total rows
              </div>
            )}
          </div>
        )}
      </div>

      {/* Data Visualization Charts */}
      {charts && charts.length > 0 && (
        <DataVisualization charts={charts} insights={insights} />
      )}
    </div>
  );
}