import axios from "axios";

// Fallback to localhost if ENV is not set. In Vite we use import.meta.env
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";


const apiClient = axios.create({
	baseURL: API_BASE,
	withCredentials: true,
});



apiClient.interceptors.response.use(
	(response) => response,
	(error) => {
		if (error.response && error.response.status === 401) {
			// Session expired, auto-logout
			localStorage.removeItem("isAuthenticated");
			localStorage.removeItem("role");
			window.location.href = "/login";
		}
		return Promise.reject(error);
	}
);

export const api = {
	getConnections: () => apiClient.get("/connections"),
	createConnection: (payload: any) => apiClient.post("/connections", payload),
	testConnection: (id: string) => apiClient.post(`/connections/${id}/test`, {}),
	deleteConnection: (id: string) => apiClient.delete(`/connections/${id}`),
	hardDeleteConnection: (id: string) => apiClient.delete(`/connections/${id}/hard`),
	getConnectionSchema: (id: string) => apiClient.get(`/connections/${id}/schema`),
	executeQuery: (query: string, dryRun: boolean = false, connectionId?: string | null) => {
		const payload: any = { query, dry_run: dryRun };
		if (connectionId && connectionId !== "default") {
			payload.connection_id = connectionId;
		}
		return apiClient.post("/query/execute", payload);
	},
	getSchemaIntelligence: (id: string, schemaJson: string) => apiClient.post(`/connections/${id}/intelligence`, { schema_json: schemaJson }),
	nlToSql: (question: string, schemaHint: string = "", connectionId?: string) => apiClient.post("/ai/nl-to-sql", { question, schema_hint: schemaHint, connection_id: connectionId }),
	explainQuery: (query: string) => apiClient.post("/ai/explain", { query }),
	getInsights: (query: string, rows: any[], columns: string[]) => apiClient.post("/ai/insights", { query, rows, columns }),
	schemaChat: (question: string, connectionId: string, activeTable?: string, chatHistory: any[] = []) => apiClient.post("/ai/schema-chat", { question, connection_id: connectionId, active_table: activeTable, chat_history: chatHistory }),
	explainAnomaly: (metricsData: any) => apiClient.post("/ai/explain-anomaly", { metrics_data: metricsData }),
	getBudget: () => apiClient.get("/query/budget"),
	getUserHistory: (limit: number = 50, offset: number = 0) => apiClient.get("/query/history", { params: { limit, offset } }),
	getLiveMetrics: () => apiClient.get("/metrics/live"),
	checkHealth: () => axios.get(`${API_BASE.replace('/api/v1', '')}/health`),
	getStatus: () => apiClient.get("/status"),
	getAuditLogs: () => apiClient.get("/admin/audit"),
	getSlowQueries: () => apiClient.get("/admin/slow-queries"),
	getIpRules: () => apiClient.get("/admin/ip-rules"),
	addIpRule: (rule: any) => apiClient.post("/admin/ip-rules", rule),
	removeIpRule: (ip: string) => apiClient.delete(`/admin/ip-rules?ip=${ip}`),
	getComplianceReport: (format: string = 'json', period: string = '30d') => apiClient.get('/admin/compliance-report', { params: { format, period }, responseType: 'blob' }),
	getRbacPolicies: () => apiClient.get("/admin/rbac-policies"),
	login: (username: string, password: string) => apiClient.post("/auth/login", { username, password }),
	register: (username: string, email: string, password: string) => apiClient.post("/auth/register", { username, email, password }),
	logout: () => {
		localStorage.removeItem("isAuthenticated");
		localStorage.removeItem("role");
		return apiClient.post("/auth/logout");
	},
};

export default apiClient;
