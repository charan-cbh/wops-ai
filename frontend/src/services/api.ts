import axios from 'axios';

// Use direct backend URL for reliable connection
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // Increased to 2 minutes for AI processing
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management with SSR support
export class AuthManager {
  static isBrowser(): boolean {
    return typeof window !== 'undefined';
  }

  static setTokens(accessToken: string, refreshToken: string) {
    if (!this.isBrowser()) return;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  static getAccessToken(): string | null {
    if (!this.isBrowser()) return null;
    return localStorage.getItem('access_token');
  }

  static getRefreshToken(): string | null {
    if (!this.isBrowser()) return null;
    return localStorage.getItem('refresh_token');
  }

  static removeTokens() {
    if (!this.isBrowser()) return;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('current_user');
  }

  static isAuthenticated(): boolean {
    if (!this.isBrowser()) return false;
    return !!this.getAccessToken();
  }

  static setCurrentUser(user: any) {
    if (!this.isBrowser()) return;
    localStorage.setItem('current_user', JSON.stringify(user));
  }

  static getCurrentUser() {
    if (!this.isBrowser()) return null;
    const user = localStorage.getItem('current_user');
    return user ? JSON.parse(user) : null;
  }

  static isAdmin(): boolean {
    if (!this.isBrowser()) return false;
    const user = this.getCurrentUser();
    return user?.role === 'admin';
  }
}

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = AuthManager.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      AuthManager.removeTokens();
      window.location.reload(); // Force re-authentication
    }
    return Promise.reject(error);
  }
);

export interface ChatMessage {
  role: string;
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  conversation_history?: ChatMessage[];
  context?: any;
  ai_provider?: string;
  model?: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  query_results?: any;
  insights?: string[];
  sql_query?: string;
  charts?: any[];
  ai_provider: string;
  model: string;
  success: boolean;
  session_info?: {
    user_id: string;
    session_id: string;
    message_id: string;
  };
}

export interface SessionInfo {
  session_id: string;
  user_id: string;
  created: boolean;
}

export interface FeedbackRequest {
  message_id: string;
  rating: number; // 1-5
  comment?: string;
}

export const APIService = {
  // Chat endpoints
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await api.post('/api/v1/chat', request);
    return response.data;
  },

  // Dashboard endpoints
  async getDashboardMetrics() {
    const response = await api.get('/api/v1/dashboard/metrics');
    return response.data;
  },

  async getAvailableAnalyses() {
    const response = await api.get('/api/v1/analyses');
    return response.data;
  },

  // AI Provider endpoints
  async getAIProviders() {
    const response = await api.get('/api/v1/providers');
    return response.data;
  },

  // Database endpoints
  async getAvailableTables() {
    const response = await api.get('/api/v1/tables');
    return response.data;
  },

  async getTableSchema(tableName: string) {
    const response = await api.get(`/api/v1/tables/${tableName}/schema`);
    return response.data;
  },

  async getTableSample(tableName: string, limit: number = 10) {
    const response = await api.get(`/api/v1/tables/${tableName}/sample`, {
      params: { limit },
    });
    return response.data;
  },

  // File upload endpoints
  async uploadFile(file: File, context?: any) {
    const formData = new FormData();
    formData.append('file', file);
    if (context) {
      formData.append('context', JSON.stringify(context));
    }

    const response = await api.post('/api/v1/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Session management endpoints
  async createOrGetSession(sessionId?: string): Promise<SessionInfo> {
    const response = await api.post('/api/v1/session', { session_id: sessionId });
    return response.data;
  },

  async getUserSessions(userId: string) {
    const response = await api.get(`/api/v1/sessions/${userId}`);
    return response.data;
  },

  async getChatHistory(userId: string, sessionId: string, limit: number = 50) {
    const response = await api.get(`/api/v1/history/${userId}/${sessionId}`, {
      params: { limit },
    });
    return response.data;
  },

  // Feedback endpoints
  async submitFeedback(feedback: FeedbackRequest) {
    const response = await api.post('/api/v1/feedback', feedback);
    return response.data;
  },

  async getFeedbackStats(days: number = 30) {
    const response = await api.get('/api/v1/feedback/stats', {
      params: { days },
    });
    return response.data;
  },

  // Weekly Digest endpoints - DISABLED
  // User requested to remove weekly digest functionality
  // async getWeeklyDigest(weeksBack: number = 1) {
  //   const response = await api.get('/api/v1/digest/weekly', {
  //     params: { weeks_back: weeksBack },
  //   });
  //   return response.data;
  // },

  // async getDigestPreview() {
  //   const response = await api.get('/api/v1/digest/preview');
  //   return response.data;
  // },


  // Authentication endpoints
  async login(email: string, password: string) {
    const response = await api.post('/api/v1/auth/login', {
      email,
      password,
    });
    
    const { access_token, refresh_token, user } = response.data;
    AuthManager.setTokens(access_token, refresh_token);
    AuthManager.setCurrentUser(user);
    
    return response.data;
  },

  async register(email: string) {
    const response = await api.post('/api/v1/auth/register', {
      email,
      role: 'user',
      usage_plan: 'free',
    });
    
    return response.data;
  },

  async setPassword(email: string, password: string, verificationToken: string) {
    const response = await api.post('/api/v1/auth/set-password', {
      email,
      password,
      verification_token: verificationToken,
    });
    
    const { access_token, refresh_token, user } = response.data;
    AuthManager.setTokens(access_token, refresh_token);
    AuthManager.setCurrentUser(user);
    
    return response.data;
  },

  async verifyEmail(email: string, token: string) {
    const response = await api.get('/api/v1/auth/verify-email', {
      params: { email, token },
    });
    return response.data;
  },

  async requestPasswordReset(email: string) {
    const response = await api.post('/api/v1/auth/request-password-reset', {
      email,
    });
    return response.data;
  },

  async confirmPasswordReset(email: string, token: string, newPassword: string) {
    const response = await api.post('/api/v1/auth/confirm-password-reset', {
      email,
      token,
      new_password: newPassword,
    });
    
    const { access_token, refresh_token, user } = response.data;
    AuthManager.setTokens(access_token, refresh_token);
    AuthManager.setCurrentUser(user);
    
    return response.data;
  },

  logout() {
    AuthManager.removeTokens();
  },

  async getCurrentUser() {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },

  async getUsers(page: number = 1, limit: number = 50) {
    const response = await api.get('/api/v1/auth/users', {
      params: { page, limit },
    });
    return response.data;
  },

  // AI Providers (admin only now)
  async getAIProvidersAdmin() {
    const response = await api.get('/api/v1/auth/providers');
    return response.data;
  },

  // Health check
  async healthCheck() {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;