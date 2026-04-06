import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000/api/v1";

// Get auth token from localStorage
const getToken = () => localStorage.getItem("token");

// Create axios instance with auth header
const apiClient = axios.create({
	baseURL: API_BASE,
});

apiClient.interceptors.request.use((config) => {
	const token = getToken();
	if (token) {
		config.headers.Authorization = `Bearer ${token}`;
	}
	return config;
});

export const api = {
	// Query endpoints
	executeQuery: (query, dryRun = false) => apiClient.post("/query/execute", { query, dry_run: dryRun }),

	// AI endpoints
	nlToSql: (question, schemaHint = "") => apiClient.post("/ai/nl-to-sql", { question, schema_hint: schemaHint }),

	explainQuery: (query) => apiClient.post("/ai/explain", { query }),

	// Metrics endpoints
	getLiveMetrics: () => apiClient.get("/metrics/live"),

	// Health endpoints
	checkHealth: () => apiClient.get("/health"),

	getStatus: () => apiClient.get("/status"),

	// Auth endpoints
	login: (username, password) => apiClient.post("/auth/login", { username, password }),

	register: (username, email, password) => apiClient.post("/auth/register", { username, email, password }),

	logout: () => {
		localStorage.removeItem("token");
	},
};

export default apiClient;
