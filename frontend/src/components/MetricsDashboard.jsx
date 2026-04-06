import React, { useState, useEffect } from "react";
import { LineChart, Line, BarChart, Bar, GaugeChart, Gauge, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { api } from "../utils/api";
import { AlertCircle, Zap } from "lucide-react";

export default function MetricsDashboard() {
	const [metrics, setMetrics] = useState(null);
	const [latencyData, setLatencyData] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");

	useEffect(() => {
		fetchMetrics();
		const interval = setInterval(fetchMetrics, 5000);
		return () => clearInterval(interval);
	}, []);

	const fetchMetrics = async () => {
		try {
			const response = await api.getLiveMetrics();
			const data = response.data;

			setMetrics(data);

			// Add to latency chart
			setLatencyData((prev) => {
				const newData = [
					...prev,
					{
						time: new Date().toLocaleTimeString(),
						p50: data.latency?.p50 || 0,
						p95: data.latency?.p95 || 0,
						p99: data.latency?.p99 || 0,
					},
				];
				return newData.slice(-20); // Keep last 20 data points
			});

			setError("");
		} catch (err) {
			setError("Failed to fetch metrics");
		} finally {
			setLoading(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-12">
				<div className="text-slate-500">Loading metrics...</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="card bg-red-50 border border-red-200 flex items-center gap-2">
				<AlertCircle className="w-5 h-5 text-red-600" />
				<span className="text-red-700">{error}</span>
			</div>
		);
	}

	if (!metrics) {
		return <div className="card text-center py-12 text-slate-500">No metrics available</div>;
	}

	return (
		<div className="space-y-6">
			{/* Latency Chart */}
			<div className="card">
				<h3 className="text-lg font-semibold text-slate-900 mb-4">Latency (ms)</h3>
				{latencyData.length > 0 ? (
					<ResponsiveContainer width="100%" height={300}>
						<LineChart data={latencyData}>
							<CartesianGrid strokeDasharray="3 3" />
							<XAxis dataKey="time" />
							<YAxis />
							<Tooltip />
							<Legend />
							<Line type="monotone" dataKey="p50" stroke="#10b981" name="P50" strokeWidth={2} />
							<Line type="monotone" dataKey="p95" stroke="#f59e0b" name="P95" strokeWidth={2} />
							<Line type="monotone" dataKey="p99" stroke="#ef4444" name="P99" strokeWidth={2} />
						</LineChart>
					</ResponsiveContainer>
				) : (
					<div className="text-slate-500 text-center py-8">Collecting latency data...</div>
				)}
			</div>

			{/* Key Metrics */}
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				{/* Cache Hit Ratio */}
				<div className="card">
					<div className="text-sm text-slate-600 mb-2">Cache Hit Ratio</div>
					<div className="text-3xl font-bold text-emerald-600">{metrics.cache_hit_ratio ? `${(metrics.cache_hit_ratio * 100).toFixed(1)}%` : "N/A"}</div>
				</div>

				{/* Requests/min */}
				<div className="card">
					<div className="text-sm text-slate-600 mb-2">Requests/min</div>
					<div className="text-3xl font-bold text-slate-900">{metrics.requests_per_minute || 0}</div>
				</div>

				{/* Slow Queries */}
				<div className="card">
					<div className="text-sm text-slate-600 mb-2">Slow Queries (24h)</div>
					<div className="text-3xl font-bold text-amber-600">{metrics.slow_queries_24h || 0}</div>
				</div>

				{/* Circuit Breaker */}
				<div className="card">
					<div className="text-sm text-slate-600 mb-2">Circuit Breaker</div>
					<div className={`text-lg font-semibold flex items-center gap-2 ${metrics.circuit_breaker_state === "closed" ? "text-emerald-600" : "text-red-600"}`}>
						<span className={`w-3 h-3 rounded-full ${metrics.circuit_breaker_state === "closed" ? "bg-emerald-600" : "bg-red-600"}`} />
						{metrics.circuit_breaker_state || "Unknown"}
					</div>
				</div>
			</div>

			{/* Request Distribution */}
			{metrics.request_distribution && (
				<div className="card">
					<h3 className="text-lg font-semibold text-slate-900 mb-4">Request Distribution</h3>
					<ResponsiveContainer width="100%" height={300}>
						<BarChart data={Object.entries(metrics.request_distribution).map(([name, value]) => ({ name, value }))}>
							<CartesianGrid strokeDasharray="3 3" />
							<XAxis dataKey="name" />
							<YAxis />
							<Tooltip />
							<Bar dataKey="value" fill="#10b981" />
						</BarChart>
					</ResponsiveContainer>
				</div>
			)}

			{/* Top Tables */}
			{metrics.top_tables && metrics.top_tables.length > 0 && (
				<div className="card">
					<h3 className="text-lg font-semibold text-slate-900 mb-4">Top Tables by Access</h3>
					<div className="space-y-2">
						{metrics.top_tables.map((table, idx) => (
							<div key={idx} className="flex items-center justify-between p-2 bg-slate-50 rounded">
								<span className="text-slate-700">{table.name}</span>
								<span className="font-semibold text-slate-900">{table.access_count} accesses</span>
							</div>
						))}
					</div>
				</div>
			)}
		</div>
	);
}
