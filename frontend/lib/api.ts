import toast from 'react-hot-toast';
import { getAccessToken, getRefreshToken, clearAuthTokens, setAuthTokens } from './auth';

interface ApiConfig {
    baseUrl: string;
    apiKey: string;
    tenantId: string;
}

interface ApiResponse<T = unknown> {
    data?: T;
    error?: string;
    status: number;
    responseTime: number;
}

interface RequestLog {
    id: string;
    method: string;
    endpoint: string;
    timestamp: Date;
    status?: number;
    responseTime?: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    request?: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    response?: any;
    error?: string;
}

// Configuration management
export const CONFIG_KEY = 'memory-mesh-config';
export const REQUEST_HISTORY_KEY = 'memory-mesh-requests';
export const NAVIGATION_STATE_KEY = 'memory-mesh-nav';

const getDefaultBaseUrl = (): string => {
    if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_API_BASE_URL) {
        return process.env.NEXT_PUBLIC_API_BASE_URL;
    }
    return 'http://localhost:8000';
};

export const defaultConfig: ApiConfig = {
    baseUrl: getDefaultBaseUrl(),
    apiKey: '',
    tenantId: 'demo-tenant'
};

export function getConfig(): ApiConfig {
    if (typeof window === 'undefined') return defaultConfig;

    try {
        const stored = localStorage.getItem(CONFIG_KEY);
        return stored ? { ...defaultConfig, ...JSON.parse(stored) } : defaultConfig;
    } catch {
        return defaultConfig;
    }
}

export function saveConfig(config: Partial<ApiConfig>): void {
    if (typeof window === 'undefined') return;

    const currentConfig = getConfig();
    const newConfig = { ...currentConfig, ...config };
    localStorage.setItem(CONFIG_KEY, JSON.stringify(newConfig));
}

export function clearAllData(): void {
    if (typeof window === 'undefined') return;

    localStorage.removeItem(CONFIG_KEY);
    localStorage.removeItem(REQUEST_HISTORY_KEY);
    localStorage.removeItem(NAVIGATION_STATE_KEY);
    toast.success('All data cleared successfully');
}

// Request history management
export function addToRequestHistory(log: Omit<RequestLog, 'id' | 'timestamp'>): void {
    if (typeof window === 'undefined') return;

    const history = getRequestHistory();
    const newLog: RequestLog = {
        ...log,
        id: Date.now().toString(),
        timestamp: new Date()
    };

    const updatedHistory = [newLog, ...history.slice(0, 99)]; // Keep last 100 requests
    localStorage.setItem(REQUEST_HISTORY_KEY, JSON.stringify(updatedHistory));
}

export function getRequestHistory(): RequestLog[] {
    if (typeof window === 'undefined') return [];

    try {
        const stored = localStorage.getItem(REQUEST_HISTORY_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

export function clearRequestHistory(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(REQUEST_HISTORY_KEY);
}

// Navigation state management
export function getNavigationState(): string {
    if (typeof window === 'undefined') return 'landing';
    return localStorage.getItem(NAVIGATION_STATE_KEY) || 'landing';
}

export function setNavigationState(state: string): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(NAVIGATION_STATE_KEY, state);
}

// API fetch wrapper
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function apiRequest<T = any>(
    endpoint: string,
    options: RequestInit = {},
    includeAuth = true
): Promise<ApiResponse<T>> {
    const config = getConfig();
    const startTime = Date.now();

    const url = `${config.baseUrl}${endpoint}`;
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Add authentication (JWT token preferred, fallback to API key)
    if (includeAuth) {
        const token = getAccessToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        } else if (config.apiKey) {
        headers['x-api-key'] = config.apiKey;
        }
    }

    const requestOptions: RequestInit = {
        ...options,
        headers,
    };

    try {
        const response = await fetch(url, requestOptions);
        const responseTime = Date.now() - startTime;

        let data;
        const contentType = response.headers.get('content-type');

        if (contentType?.includes('application/json')) {
            data = await response.json();
        } else {
            data = await response.text();
        }

        const result: ApiResponse<T> = {
            data,
            status: response.status,
            responseTime,
            error: !response.ok ? data?.error || `HTTP ${response.status}` : undefined
        };

        // Log the request
        addToRequestHistory({
            method: options.method || 'GET',
            endpoint,
            status: response.status,
            responseTime,
            request: options.body ? JSON.parse(options.body as string) : undefined,
            response: data,
            error: result.error
        });

        if (!response.ok) {
            let errorMessage = 'Request failed';

            switch (response.status) {
                case 400:
                    errorMessage = data?.detail || data?.error || 'Invalid request data';
                    break;
                case 401:
                    // For login/register endpoints, show the actual error message
                    if (endpoint.includes('/auth/login') || endpoint.includes('/auth/register')) {
                        errorMessage = data?.detail || data?.error || 'Invalid credentials';
                    } else {
                        errorMessage = 'Invalid API key or unauthorized';
                        // Try to refresh token if we have a refresh token
                        const refreshToken = getRefreshToken();
                        if (refreshToken && endpoint !== '/v1/auth/refresh') {
                            // Attempt token refresh
                            try {
                                const refreshResponse = await fetch(`${config.baseUrl}/v1/auth/refresh`, {
                                    method: 'POST',
                                    headers: { 'Authorization': `Bearer ${refreshToken}` },
                                });
                                if (refreshResponse.ok) {
                                    const refreshData = await refreshResponse.json();
                                    setAuthTokens(refreshData);
                                    // Retry original request
                                    return apiRequest(endpoint, options, includeAuth);
                                }
                            } catch {
                                // Refresh failed, clear tokens
                                clearAuthTokens();
                                if (typeof window !== 'undefined') {
                                    window.location.href = '/login';
                                }
                            }
                        }
                    }
                    break;
                case 404:
                    errorMessage = 'Endpoint not found';
                    break;
                case 429:
                    errorMessage = 'Rate limit exceeded';
                    break;
                case 500:
                    errorMessage = 'Server error occurred';
                    break;
                default:
                    errorMessage = data?.error || `HTTP ${response.status} error`;
            }

            toast.error(errorMessage);
        }

        return result;
    } catch (error) {
        const responseTime = Date.now() - startTime;
        const errorMessage = error instanceof Error ? error.message : 'Network error';

        // Log the failed request
        addToRequestHistory({
            method: options.method || 'GET',
            endpoint,
            responseTime,
            error: errorMessage
        });

        toast.error(`Network error: ${errorMessage}`);

        return {
            status: 0,
            responseTime,
            error: errorMessage
        };
    }
}

// Specific API methods
export const memoryMeshAPI = {
    // Authentication
    login: (email: string, password: string, rememberMe = false) =>
        apiRequest('/v1/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password, remember_me: rememberMe })
        }, false),

    register: (data: {
        email: string;
        username: string;
        password: string;
        full_name?: string;
        tenant_id?: string;
    }) => apiRequest('/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify(data)
    }, false),

    getCurrentUser: () => apiRequest('/v1/auth/me'),

    logout: () => apiRequest('/v1/auth/logout', { method: 'POST' }),

    // OAuth
    oauthInitiate: (provider: 'google' | 'github', redirectUri: string) =>
        apiRequest('/v1/auth/oauth/initiate', {
            method: 'POST',
            body: JSON.stringify({ provider, redirect_uri: redirectUri })
        }, false),

    oauthCallback: (provider: 'google' | 'github', code: string, state: string) =>
        apiRequest('/v1/auth/oauth/callback', {
            method: 'POST',
            body: JSON.stringify({ provider, code, state })
        }, false),

    // Messages
    storeMessage: (data: {
        tenant_id: string;
        conversation_id: string;
        role: 'user' | 'assistant' | 'system';
        content: string;
        metadata?: Record<string, unknown>;
        importance_override?: number;
    }) => apiRequest('/v1/messages', {
        method: 'POST',
        body: JSON.stringify(data)
    }),

    getMessage: (messageId: string) =>
        apiRequest(`/v1/messages/${messageId}`),

    updateMessage: (messageId: string, data: {
        content?: string;
        metadata?: Record<string, unknown>;
        importance_override?: number;
        archived?: boolean;
    }) => apiRequest(`/v1/messages/${messageId}`, {
        method: 'PUT',
        body: JSON.stringify(data)
    }),

    deleteMessage: (messageId: string) =>
        apiRequest(`/v1/messages/${messageId}`, { method: 'DELETE' }),

    // Conversations
    listConversations: (params: {
        tenant_id?: string;
        archived?: boolean;
        page?: number;
        page_size?: number;
    }) => {
        const searchParams = new URLSearchParams();
        if (params.tenant_id) searchParams.append('tenant_id', params.tenant_id);
        if (params.archived !== undefined) searchParams.append('archived', params.archived.toString());
        if (params.page) searchParams.append('page', params.page.toString());
        if (params.page_size) searchParams.append('page_size', params.page_size.toString());
        return apiRequest(`/v1/conversations?${searchParams.toString()}`);
    },

    getConversation: (conversationId: string, tenantId: string) =>
        apiRequest(`/v1/conversations/${conversationId}?tenant_id=${tenantId}`),

    createConversation: (data: {
        conversation_id: string;
        tenant_id: string;
        title?: string;
        metadata?: Record<string, unknown>;
    }) => apiRequest('/v1/conversations', {
        method: 'POST',
        body: JSON.stringify(data)
    }),

    updateConversation: (conversationId: string, data: {
        title?: string;
        metadata?: Record<string, unknown>;
        archived?: boolean;
    }, tenantId: string) => apiRequest(`/v1/conversations/${conversationId}?tenant_id=${tenantId}`, {
        method: 'PUT',
        body: JSON.stringify(data)
    }),

    deleteConversation: (conversationId: string, tenantId: string, deleteMessages = false) =>
        apiRequest(`/v1/conversations/${conversationId}?tenant_id=${tenantId}&delete_messages=${deleteMessages}`, {
            method: 'DELETE'
        }),

    getConversationStats: (conversationId: string, tenantId: string) =>
        apiRequest(`/v1/conversations/${conversationId}/stats?tenant_id=${tenantId}`),

    // Memory search
    searchMemories: (params: {
        query: string;
        tenant_id?: string;
        conversation_id?: string;
        top_k?: number;
        min_importance?: number;
    }) => {
        const config = getConfig();
        const searchParams = new URLSearchParams();

        searchParams.append('query', params.query);
        searchParams.append('tenant_id', params.tenant_id || config.tenantId);

        if (params.conversation_id) {
            searchParams.append('conversation_id', params.conversation_id);
        }
        if (params.top_k !== undefined) {
            searchParams.append('top_k', params.top_k.toString());
        }
        if (params.min_importance !== undefined) {
            searchParams.append('min_importance', params.min_importance.toString());
        }

        return apiRequest(`/v1/memory/search?${searchParams.toString()}`);
    },

    // Analytics
    getUsageStats: (tenantId?: string) => {
        const params = tenantId ? `?tenant_id=${tenantId}` : '';
        return apiRequest(`/v1/analytics/usage${params}`);
    },

    getMessageTrends: (params: { tenant_id?: string; days?: number }) => {
        const searchParams = new URLSearchParams();
        if (params.tenant_id) searchParams.append('tenant_id', params.tenant_id);
        if (params.days) searchParams.append('days', params.days.toString());
        return apiRequest(`/v1/analytics/trends?${searchParams.toString()}`);
    },

    // Admin endpoints
    healthCheck: () => apiRequest('/v1/admin/health', {}, false),

    readinessCheck: () => apiRequest('/v1/admin/readiness', {}, false),

    runRetention: (data: {
        tenant_id: string;
        actions: string[];
        dry_run?: boolean;
    }) => apiRequest('/v1/admin/retention/run', {
        method: 'POST',
        body: JSON.stringify(data)
    })
};

// Sample data for testing
export const sampleData = {
    message: {
        tenant_id: 'demo-tenant',
        conversation_id: 'test-conversation-1',
        role: 'user' as const,
        content: 'I need help understanding how semantic search works with vector embeddings',
        metadata: {
            user_id: 'user-123',
            session_id: 'session-456',
            source: 'web-app'
        }
    },
    search: {
        query: 'vector embeddings',
        top_k: 5
    }
};