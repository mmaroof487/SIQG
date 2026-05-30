import axios from "axios";

// Fallback to localhost if ENV is not set. In Vite we use import.meta.env
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

const getToken = (): string | null => localStorage.getItem("token");

const apiClient = axios.create({
	baseURL: API_BASE,
});

import CryptoJS from 'crypto-js';

apiClient.interceptors.request.use((config) => {
	const token = getToken();
	if (token && config.headers) {
		config.headers.Authorization = `Bearer ${token}`;
	}

	// HMAC Request Signing (Tier 6 Feature)
	if (config.headers) {
		const timestamp = (Date.now() / 1000).toString(); // Using float-compatible timestamp for <30s check
		const method = config.method ? config.method.toUpperCase() : 'GET';
		
		// Map path to what FastAPI receives (e.g. /api/v1/query/execute)
		const baseUrlObj = new URL(config.baseURL || 'http://localhost:8000/api/v1');
		// Remove leading slash from config.url to avoid double slashes
		const rawPath = config.url ? (config.url.startsWith('/') ? config.url.substring(1) : config.url) : '';
		const path = baseUrlObj.pathname.endsWith('/') ? `${baseUrlObj.pathname}${rawPath}` : `${baseUrlObj.pathname}/${rawPath}`;
		
		const bodyStr = config.data ? JSON.stringify(config.data) : "";
		const message = `${timestamp}:${method}:${path}:${bodyStr}`;
		
		// Use dummy secret key matching the backend bypass behavior from .env
		const SECRET_KEY = "12345678901234567890123456789012";
		const signature = CryptoJS.HmacSHA256(message, SECRET_KEY).toString(CryptoJS.enc.Hex);

		config.headers['X-Timestamp'] = timestamp;
		config.headers['X-Signature'] = signature;
	}

	return config;
});

export const api = {
	getConnections: () => apiClient.get("/connections"),
	createConnection: (payload: any) => apiClient.post("/connections", payload),
	testConnection: (id: string) => apiClient.post(`/connections/${id}/test`),
	deleteConnection: (id: string) => apiClient.delete(`/connections/${id}`),
	getConnectionSchema: (id: string) => apiClient.get(`/connections/${id}/schema`),
	executeQuery: (query: string, dryRun: boolean = false, connectionId?: string | null) => {
		const payload: any = { query, dry_run: dryRun };
		if (connectionId && connectionId !== "default") {
			payload.connection_id = connectionId;
		}
		return apiClient.post("/query/execute", payload);
	},
	nlToSql: (question: string, schemaHint: string = "") => apiClient.post("/ai/nl-to-sql", { question, schema_hint: schemaHint }),
	explainQuery: (query: string) => apiClient.post("/ai/explain", { query }),
	explainAnomaly: (metricsData: any) => apiClient.post("/ai/explain-anomaly", { metrics_data: metricsData }),
	getLiveMetrics: () => apiClient.get("/metrics/live"),
	checkHealth: () => axios.get(`${API_BASE.replace('/api/v1', '')}/health`),
	getStatus: () => apiClient.get("/status"),
	getAuditLogs: () => apiClient.get("/admin/audit-log"),
	getSlowQueries: () => apiClient.get("/admin/slow-queries"),
	getIpRules: () => apiClient.get("/admin/ip-rules"),
	addIpRule: (rule: any) => apiClient.post("/admin/ip-rules", rule),
	removeIpRule: (ip: string) => apiClient.delete(`/admin/ip-rules?ip=${ip}`),
	getComplianceReport: (format: string = 'json', period: string = '30d') => apiClient.get('/admin/compliance-report', { params: { format, period }, responseType: 'blob' }),
	getRbacPolicies: () => apiClient.get("/admin/rbac-policies"),
	login: (username: string, password: string) => apiClient.post("/auth/login", { username, password }),
	register: (username: string, email: string, password: string) => apiClient.post("/auth/register", { username, email, password }),
	logout: () => {
		localStorage.removeItem("token");
	},
};

export default apiClient;
