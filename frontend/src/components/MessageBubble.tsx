import { UserIcon, CpuChipIcon, ChevronDownIcon, ChevronUpIcon, LightBulbIcon, SparklesIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ChartRenderer from './ChartRenderer';
import FeedbackButtons from './FeedbackButtons';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  queryResults?: any;
  insights?: string[];
  sqlQuery?: string;
  charts?: any[];
}

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [showExplanation, setShowExplanation] = useState(false);
  
  // For assistant messages with insights, show insights first
  const hasInsights = !isUser && message.insights && message.insights.length > 0;
  const hasCharts = !isUser && message.charts && message.charts.length > 0;
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-5xl w-full ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Modern Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-4' : 'mr-4'}`}>
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg ${
            isUser 
              ? 'bg-gradient-to-br from-blue-600 to-purple-600 text-white' 
              : 'bg-gradient-to-br from-emerald-500 to-teal-600 text-white'
          }`}>
            {isUser ? (
              <UserIcon className="h-5 w-5" />
            ) : (
              <ChartBarIcon className="h-5 w-5" />
            )}
          </div>
        </div>

        {/* Message Content */}
        <div className="flex-1 space-y-3">
          {isUser ? (
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-2xl px-5 py-3 shadow-lg max-w-md">
              <p className="text-sm leading-relaxed">{message.content}</p>
              <div className="text-xs mt-2 text-blue-100 opacity-75">
                {new Date(message.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Modern Answer Card */}
              {hasInsights && (
                <div className="bg-gradient-to-br from-white to-blue-50/30 border border-blue-200/50 rounded-2xl p-6 shadow-lg backdrop-blur-sm">
                  <div className="flex items-center mb-4">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center mr-3">
                      <SparklesIcon className="h-4 w-4 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-800">Key Insights</h3>
                  </div>
                  <ul className="space-y-3">
                    {message.insights!.map((insight, index) => (
                      <li key={index} className="flex items-start group">
                        <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-full flex items-center justify-center mr-3 mt-0.5 shadow-sm">
                          <span className="text-white text-xs font-bold">{index + 1}</span>
                        </div>
                        <span className="text-gray-800 leading-relaxed font-medium group-hover:text-gray-900 transition-colors">
                          {insight}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Charts Section */}
              {hasCharts && (
                <div className="bg-gradient-to-br from-white to-indigo-50/30 border border-indigo-200/50 rounded-2xl p-6 shadow-lg backdrop-blur-sm">
                  <ChartRenderer charts={message.charts!} />
                </div>
              )}

              {/* Modern Analysis Expandable */}
              {hasInsights ? (
                <div className="bg-white/80 backdrop-blur-sm border border-gray-200/50 rounded-2xl shadow-lg overflow-hidden">
                  <button
                    onClick={() => setShowExplanation(!showExplanation)}
                    className="w-full px-6 py-4 flex items-center justify-center text-left hover:bg-gray-50/80 transition-all duration-200 group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-gradient-to-br from-gray-500 to-gray-600 rounded-lg flex items-center justify-center group-hover:from-blue-500 group-hover:to-purple-600 transition-all duration-200">
                        <CpuChipIcon className="h-4 w-4 text-white" />
                      </div>
                      <span className="text-sm text-gray-700 font-semibold group-hover:text-gray-900">
                        {showExplanation ? "Hide detailed analysis" : "Show detailed analysis"}
                      </span>
                    </div>
                    <div className="ml-auto">
                      {showExplanation ? (
                        <ChevronUpIcon className="h-5 w-5 text-gray-500 group-hover:text-blue-600 transition-colors" />
                      ) : (
                        <ChevronDownIcon className="h-5 w-5 text-gray-500 group-hover:text-blue-600 transition-colors" />
                      )}
                    </div>
                  </button>
                  
                  {showExplanation && (
                    <div className="border-t border-gray-200/50 bg-gradient-to-br from-white to-gray-50/30">
                      <div className="px-6 py-6">
                        <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed">
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-white/80 backdrop-blur-sm border border-gray-200/50 rounded-2xl px-6 py-4 shadow-lg">
                  <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                </div>
              )}
              
              {/* Feedback Buttons for Assistant Messages */}
              <div className="mt-4 pt-3 border-t border-gray-100">
                <FeedbackButtons 
                  messageId={message.id}
                  onFeedbackSubmitted={(rating, comment) => {
                    console.log(`Feedback submitted for message ${message.id}: ${rating}/5`, comment);
                  }}
                />
              </div>
              
              {/* Modern Timestamp */}
              <div className="text-xs text-gray-400 mt-3 flex items-center space-x-1">
                <div className="w-1 h-1 bg-gray-400 rounded-full"></div>
                <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}