/**
 * GraphGuard API Client
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchJSON<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== 'undefined' ? sessionStorage.getItem("auth_token") : null;
  const headers = {
    "Content-Type": "application/json",
    ...(options?.headers || {}),
  };
  
  if (token) {
    (headers as any)["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers,
    ...options,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error [${res.status}]: ${errorText || res.statusText}`);
  }

  return res.json();
}

export const api = {
  // Dashboard
  getDashboardSummary: () => fetchJSON<any>("/dashboard/summary"),

  // Accounts
  getAccounts: (params?: { risk_level?: string; search?: string; page?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.risk_level) query.append("risk_level", params.risk_level);
    if (params?.search) query.append("search", params.search);
    if (params?.page) query.append("page", String(params.page));
    if (params?.limit) query.append("limit", String(params.limit));
    return fetchJSON<any[]>(`/accounts?${query.toString()}`);
  },

  getAccountDetail: (accountId: string) => fetchJSON<any>(`/accounts/${accountId}`),

  getAccountTransactions: (accountId: string, limit: number = 50) =>
    fetchJSON<any[]>(`/accounts/${accountId}/transactions?limit=${limit}`),

  getAccountRisk: (accountId: string) => fetchJSON<any>(`/accounts/${accountId}/risk`),

  getAccountGraph: (accountId: string, depth: number = 1, limit: number = 50) =>
    fetchJSON<any>(`/accounts/${accountId}/graph?depth=${depth}&limit=${limit}`),

  // Transactions
  getTransactions: (params?: { account_id?: string; page?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.account_id) query.append("account_id", params.account_id);
    if (params?.page) query.append("page", String(params.page));
    if (params?.limit) query.append("limit", String(params.limit));
    return fetchJSON<any[]>(`/transactions?${query.toString()}`);
  },

  // Alerts
  getAlerts: (params?: { status?: string; severity?: string; page?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.severity) query.append("severity", params.severity);
    if (params?.page) query.append("page", String(params.page));
    if (params?.limit) query.append("limit", String(params.limit));
    return fetchJSON<any[]>(`/alerts?${query.toString()}`);
  },

  updateAlertStatus: (alertId: string, status: string) =>
    fetchJSON<any>(`/alerts/${alertId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  // EWS
  getEWSSignals: (params?: { account_id?: string; signal_code?: string; page?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.account_id) query.append("account_id", params.account_id);
    if (params?.signal_code) query.append("signal_code", params.signal_code);
    if (params?.page) query.append("page", String(params.page));
    if (params?.limit) query.append("limit", String(params.limit));
    return fetchJSON<any[]>(`/ews?${query.toString()}`);
  },

  // Graph
  searchGraph: (params?: { account_id?: string; risk_level?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.account_id) query.append("account_id", params.account_id);
    if (params?.risk_level) query.append("risk_level", params.risk_level);
    if (params?.limit) query.append("limit", String(params.limit));
    return fetchJSON<any>(`/graph/search?${query.toString()}`);
  },
};
