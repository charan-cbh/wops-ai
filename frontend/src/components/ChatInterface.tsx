import { useState, useEffect, useRef } from 'react';
import { PaperAirplaneIcon, CogIcon, ChartBarIcon, SparklesIcon, UserIcon, ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline';
import { APIService, AuthManager } from '../services/api';
import MessageBubble from './MessageBubble';
import QueryResults from './QueryResults';
import AIProviderSelector from './AIProviderSelector';
import AuthModal from './AuthModal';

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

interface AIProvider {
  name: string;
  available_models: string[];
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [providers, setProviders] = useState<Record<string, AIProvider>>({});
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedModel, setSelectedModel] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [sessionInfo, setSessionInfo] = useState<{sessionId: string, userId: string} | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(AuthManager.isAuthenticated());
  const [currentUser, setCurrentUser] = useState(AuthManager.getCurrentUser());
  const [showAuthModal, setShowAuthModal] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadProviders();
    initializeSession();
  }, []);

  const initializeSession = async () => {
    try {
      // Try to get existing session from localStorage
      const storedSessionId = localStorage.getItem('chatSessionId');
      const sessionResponse = await APIService.createOrGetSession(storedSessionId || undefined);
      
      setSessionInfo({
        sessionId: sessionResponse.session_id,
        userId: sessionResponse.user_id
      });
      
      // Store session ID for future use
      localStorage.setItem('chatSessionId', sessionResponse.session_id);
      
      // Load chat history if it's an existing session
      if (!sessionResponse.created) {
        const historyResponse = await APIService.getChatHistory(
          sessionResponse.user_id, 
          sessionResponse.session_id, 
          20
        );
        
        if (historyResponse.history && historyResponse.history.length > 0) {
          const loadedMessages: Message[] = historyResponse.history.map((msg: any) => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            queryResults: msg.query_results,
            insights: msg.insights,
            sqlQuery: msg.sql_query
          }));
          setMessages(loadedMessages);
        } else {
          // Add welcome message for new sessions
          addWelcomeMessage();
        }
      } else {
        // Add welcome message for new sessions
        addWelcomeMessage();
      }
    } catch (error) {
      console.error('Error initializing session:', error);
      // Add welcome message as fallback
      addWelcomeMessage();
    }
  };

  const addWelcomeMessage = () => {
    const welcomeMessage: Message = {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your Worker Operations BI assistant. I can help you analyze data, generate insights, and answer questions about your business metrics. What would you like to explore today?',
      timestamp: new Date().toISOString(),
    };
    setMessages([welcomeMessage]);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadProviders = async () => {
    // Only load providers for admin users
    if (!isAuthenticated || !AuthManager.isAdmin()) {
      return;
    }
    
    try {
      const response = await APIService.getAIProvidersAdmin();
      setProviders(response.providers);
      setSelectedProvider(response.default || 'openai');
      
      // Set default model for the selected provider
      if (response.providers[response.default || 'openai']?.available_models?.length > 0) {
        setSelectedModel(response.providers[response.default || 'openai'].available_models[0]);
      }
    } catch (error) {
      console.error('Error loading providers:', error);
    }
  };

  // Authentication handlers
  const handleLogin = async (email: string, password: string) => {
    await APIService.login(email, password);
    setIsAuthenticated(true);
    setCurrentUser(AuthManager.getCurrentUser());
    loadProviders(); // Reload providers if user is admin
  };

  const handleRegister = async (email: string) => {
    return await APIService.register(email);
  };

  const handleLogout = () => {
    APIService.logout();
    setIsAuthenticated(false);
    setCurrentUser(null);
    setProviders({});
    setMessages([]);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    // Require authentication
    if (!isAuthenticated) {
      setShowAuthModal(true);
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await APIService.sendMessage({
        message: inputMessage,
        conversation_history: messages.map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
        })),
        ai_provider: selectedProvider,
        model: selectedModel,
        session_id: sessionInfo?.sessionId,
      });

      console.log('API Response:', response);

      // Check if we got a valid response
      if (response && response.response) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.response,
          timestamp: new Date().toISOString(),
          queryResults: response.query_results,
          insights: response.insights,
          sqlQuery: response.sql_query,
          charts: response.charts,
        };

        setMessages(prev => [...prev, assistantMessage]);
      } else {
        // Handle case where response is empty or malformed
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'I received an empty response. Please try again.',
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error: any) {
      console.error('Error sending message:', error);
      
      // More detailed error handling
      let errorContent = 'Sorry, I encountered an error processing your request. Please try again.';
      
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Error response:', error.response.data);
        console.error('Error status:', error.response.status);
        
        if (error.response.status === 500) {
          errorContent = `Server error: ${error.response.data?.detail || 'Internal server error'}`;
        } else if (error.response.status === 400) {
          errorContent = `Bad request: ${error.response.data?.detail || 'Invalid request'}`;
        } else {
          errorContent = `Error ${error.response.status}: ${error.response.data?.detail || error.message}`;
        }
      } else if (error.request) {
        // The request was made but no response was received
        console.error('No response received:', error.request);
        errorContent = 'No response from server. Please check your connection and try again.';
      } else {
        // Something happened in setting up the request
        console.error('Request setup error:', error.message);
        errorContent = `Request error: ${error.message}`;
      }
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: errorContent,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleProviderChange = (provider: string, model: string) => {
    setSelectedProvider(provider);
    setSelectedModel(model);
  };

  const quickQuestions = [
    'Show me worker productivity trends',
    'What are the top performing regions?',
    'Analyze scheduling efficiency',
    'Show cost optimization opportunities',
  ];

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Modern Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200/50 p-6 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-4">
          <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl shadow-lg">
            <ChartBarIcon className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-700 to-purple-700 bg-clip-text text-transparent">
              WOPS Intelligence
            </h1>
            <p className="text-sm text-gray-600 flex items-center">
              <SparklesIcon className="h-4 w-4 mr-1 text-blue-500" />
              Your AI-powered business intelligence assistant
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          {isAuthenticated ? (
            <>
              <div className="flex items-center space-x-2 px-3 py-2 bg-green-50 rounded-lg">
                <UserIcon className="h-4 w-4 text-green-600" />
                <span className="text-sm text-green-700 font-medium">
                  {currentUser?.email} ({currentUser?.role})
                </span>
              </div>
              
              {AuthManager.isAdmin() && (
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="p-3 text-gray-500 hover:text-gray-700 rounded-xl hover:bg-white/60 transition-all duration-200 shadow-sm hover:shadow-md"
                >
                  <CogIcon className="h-5 w-5" />
                </button>
              )}
              
              <button
                onClick={handleLogout}
                className="p-3 text-gray-500 hover:text-red-600 rounded-xl hover:bg-red-50 transition-all duration-200 shadow-sm hover:shadow-md"
                title="Logout"
              >
                <ArrowRightOnRectangleIcon className="h-5 w-5" />
              </button>
            </>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 transition-all duration-200 shadow-sm hover:shadow-md"
            >
              Sign In
            </button>
          )}
        </div>
      </div>

      {/* Modern Settings Panel - Admin Only */}
      {showSettings && AuthManager.isAdmin() && (
        <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200/50 p-6 shadow-sm">
          <div className="max-w-4xl mx-auto">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">AI Configuration (Admin)</h3>
            <AIProviderSelector
              providers={providers}
              selectedProvider={selectedProvider}
              selectedModel={selectedModel}
              onProviderChange={handleProviderChange}
            />
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="max-w-6xl mx-auto">
        {messages.map((message) => (
          <div key={message.id} className="space-y-4">
            <MessageBubble message={message} />
            {message.queryResults && (
              <div className="ml-14"> {/* Align with assistant message content */}
                <QueryResults
                  data={message.queryResults}
                  insights={message.insights}
                  sqlQuery={message.sqlQuery}
                  charts={message.charts}
                  showInsights={false} // Don't show insights here as they're already in MessageBubble
                />
              </div>
            )}
          </div>
        ))}
        
          {isLoading && (
            <div className="flex items-center justify-center p-8">
              <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20">
                <div className="flex items-center space-x-3">
                  <div className="relative">
                    <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-200 border-t-blue-600"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <ChartBarIcon className="h-4 w-4 text-blue-600" />
                    </div>
                  </div>
                  <div>
                    <p className="text-gray-700 font-medium">Analyzing your data...</p>
                    <p className="text-gray-500 text-sm">Generating insights with AI</p>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Modern Quick Questions */}
      {messages.length === 1 && (
        <div className="p-6 bg-gradient-to-r from-white/60 to-blue-50/60 backdrop-blur-sm border-t border-gray-200/50">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Popular Analytics Queries</h3>
              <p className="text-gray-600">Start with these commonly requested insights</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {quickQuestions.map((question, index) => (
                <button
                  key={index}
                  onClick={() => setInputMessage(question)}
                  className="group text-left p-4 bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200/50 hover:border-blue-300 hover:bg-white shadow-sm hover:shadow-md text-sm transition-all duration-200 transform hover:-translate-y-1"
                >
                  <div className="flex items-center space-x-2">
                    <ChartBarIcon className="h-5 w-5 text-blue-500 group-hover:text-blue-600" />
                    <span className="font-medium text-gray-800">{question}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modern Input Form */}
      <form onSubmit={handleSendMessage} className="p-6 bg-white/90 backdrop-blur-sm border-t border-gray-200/50 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <div className="relative flex space-x-4">
            <div className="flex-1 relative">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask anything about your worker operations data..."
                className="w-full p-4 pr-12 border border-gray-300/50 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-400 bg-white/80 backdrop-blur-sm shadow-sm text-gray-700 placeholder-gray-400 transition-all duration-200"
                disabled={isLoading}
              />
              <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                <SparklesIcon className="h-5 w-5 text-gray-400" />
              </div>
            </div>
            <button
              type="submit"
              disabled={isLoading || !inputMessage.trim()}
              className="px-6 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-2xl hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center space-x-2"
            >
              <PaperAirplaneIcon className="h-5 w-5" />
              <span className="font-medium">Analyze</span>
            </button>
          </div>
        </div>
      </form>

      {/* Authentication Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onLogin={handleLogin}
        onRegister={handleRegister}
      />
    </div>
  );
}