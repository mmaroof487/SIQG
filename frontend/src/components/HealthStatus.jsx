import React, { useState, useEffect } from "react";
import { api } from "../utils/api";
import { CheckCircle, AlertCircle, Clock } from "lucide-react";

export default function HealthStatus() {
	const [health, setHealth] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");

	useEffect(() => {
		fetchHealth();
		const interval = setInterval(fetchHealth, 10000);
		return () => clearInterval(interval);
	}, []);

	const fetchHealth = async () => {
		try {
			const response = await api.checkHealth();
			setHealth(response.data);
			setError("");
		} catch (err) {
			setError("Failed to fetch health status");
		} finally {
			setLoading(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-12">
				<div className="text-slate-500">Checking system health...</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="card bg-red-50 border border-red-200">
				<div className="text-red-700 flex items-center gap-2">
					<AlertCircle className="w-5 h-5" />
					{error}
				</div>
			</div>
		);
	}

	if (!health) {
		return <div className="card text-center py-12 text-slate-500">No health data available</div>;
	}

	const isHealthy = (status) => status === "healthy" || status === "ok";
	const statusIcon = (status) => {
		return isHealthy(status) ? <CheckCircle className="w-5 h-5 text-emerald-600" /> : <AlertCircle className="w-5 h-5 text-red-600" />;
	};

	const statusBadge = (status) => {
		const baseClasses = "inline-flex items-center gap-2 px-3 py-1 rounded-full font-medium";
		if (isHealthy(status)) {
			return `${baseClasses} bg-emerald-100 text-emerald-800`;
		}
		return `${baseClasses} bg-red-100 text-red-800`;
	};

	return (
		<div className="space-y-6">
			{/* Overall Status */}
			<div className="card border-l-4 border-emerald-600">
				<h2 className="text-2xl font-bold text-slate-900 mb-4">System Status</h2>
				<div className={`text-lg font-semibold flex items-center gap-2 mb-4 ${isHealthy(health.status) ? "text-emerald-600" : "text-red-600"}`}>
					<span className={`w-3 h-3 rounded-full ${isHealthy(health.status) ? "bg-emerald-600" : "bg-red-600"} animate-pulse`} />
					{health.status.toUpperCase()}
				</div>
				{health.last_check && (
					<div className="flex items-center gap-2 text-sm text-slate-600">
						<Clock className="w-4 h-4" />
						Last checked: {new Date(health.last_check).toLocaleString()}
					</div>
				)}
			</div>

			{/* Component Status Grid */}
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				{/* PostgreSQL Primary */}
				<div className="card">
					<div className="flex items-center justify-between mb-3">
						<h3 className="font-semibold text-slate-900">PostgreSQL Primary</h3>
						{statusIcon(health.postgres_primary)}
					</div>
					<div className={statusBadge(health.postgres_primary)}>{health.postgres_primary}</div>
					{health.postgres_primary_latency_ms && <div className="text-xs text-slate-600 mt-2">Latency: {health.postgres_primary_latency_ms}ms</div>}
				</div>

				{/* PostgreSQL Replica */}
				<div className="card">
					<div className="flex items-center justify-between mb-3">
						<h3 className="font-semibold text-slate-900">PostgreSQL Replica</h3>
						{statusIcon(health.postgres_replica)}
					</div>
					<div className={statusBadge(health.postgres_replica)}>{health.postgres_replica}</div>
					{health.postgres_replica_latency_ms && <div className="text-xs text-slate-600 mt-2">Latency: {health.postgres_replica_latency_ms}ms</div>}
				</div>

				{/* Redis */}
				<div className="card">
					<div className="flex items-center justify-between mb-3">
						<h3 className="font-semibold text-slate-900">Redis Cache</h3>
						{statusIcon(health.redis)}
					</div>
					<div className={statusBadge(health.redis)}>{health.redis}</div>
					{health.redis_memory_usage_mb !== undefined && <div className="text-xs text-slate-600 mt-2">Memory: {health.redis_memory_usage_mb}MB</div>}
				</div>

				{/* Circuit Breaker */}
				<div className="card">
					<div className="flex items-center justify-between mb-3">
						<h3 className="font-semibold text-slate-900">Circuit Breaker</h3>
						{statusIcon(health.circuit_breaker_state === "closed" ? "ok" : "error")}
					</div>
					<div className={statusBadge(health.circuit_breaker_state === "closed" ? "ok" : "error")}>{health.circuit_breaker_state}</div>
				</div>
			</div>

			{/* Additional Info */}
			<div className="card">
				<h3 className="font-semibold text-slate-900 mb-4">Additional Information</h3>
				<div className="grid grid-cols-2 md:grid-cols-3 gap-4">
					{health.uptime_seconds && (
						<div>
							<div className="text-sm text-slate-600">Uptime</div>
							<div className="text-lg font-semibold text-slate-900">{Math.floor(health.uptime_seconds / 86400)}d</div>
						</div>
					)}
					{health.request_count !== undefined && (
						<div>
							<div className="text-sm text-slate-600">Total Requests</div>
							<div className="text-lg font-semibold text-slate-900">{health.request_count.toLocaleString()}</div>
						</div>
					)}
					{health.current_connections !== undefined && (
						<div>
							<div className="text-sm text-slate-600">Active Connections</div>
							<div className="text-lg font-semibold text-slate-900">{health.current_connections}</div>
						</div>
					)}
				</div>
			</div>

			{/* Last Successful Query */}
			{health.last_successful_query_at && (
				<div className="card bg-emerald-50 border border-emerald-200">
					<div className="flex items-center gap-2 text-emerald-900">
						<CheckCircle className="w-5 h-5" />
						<span>Last successful query: {new Date(health.last_successful_query_at).toLocaleString()}</span>
					</div>
				</div>
			)}
		</div>
	);
}
