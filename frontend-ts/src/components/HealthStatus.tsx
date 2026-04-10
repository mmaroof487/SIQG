import React, { useState, useEffect } from "react";
import { api } from "../utils/api";
import { CheckCircle, AlertCircle, Clock, Database, Server, Zap } from "lucide-react";

export default function HealthStatus() {
	const [health, setHealth] = useState<any>(null);
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
			<div className="flex items-center justify-center py-16">
				<div className="text-primary-neon animate-pulse text-lg tracking-widest font-semibold flex items-center gap-3">
					<Zap className="w-5 h-5 animate-pulse" />
					SCANNING SYSTEM TOPOLOGY...
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="bg-error-dim/10 border border-error/30 p-6 rounded-2xl flex items-center gap-3">
				<AlertCircle className="w-6 h-6 text-error flex-shrink-0" />
				<span className="text-error font-mono font-medium">{error}</span>
			</div>
		);
	}

	if (!health) {
		return <div className="text-center py-16 text-on-surface-variant font-mono uppercase tracking-widest">NO HEALTH DATA AVAILABLE</div>;
	}

	const isHealthy = (status: string) => status === "healthy" || status === "ok";

	const StatusCard = ({ title, status, icon: Icon, extraNode }: { title: string, status: string, icon: any, extraNode?: React.ReactNode }) => {
		const healthy = isHealthy(status);
		return (
			<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 relative overflow-hidden group">
				<div className={`absolute top-0 left-0 w-1 h-full ${healthy ? 'bg-primary-neon shadow-[0_0_10px_#00FF9D]' : 'bg-error shadow-[0_0_10px_#ff716c]'}`}></div>
				<div className="flex items-center justify-between mb-4 pl-3">
					<h3 className="font-bold text-on-surface flex items-center gap-2">
						<Icon className="w-5 h-5 text-on-surface-variant" />
						{title}
					</h3>
					{healthy ? (
						<CheckCircle className="w-6 h-6 text-primary-neon drop-shadow-[0_0_5px_#00FF9D]" />
					) : (
						<AlertCircle className="w-6 h-6 text-error drop-shadow-[0_0_5px_#ff716c]" />
					)}
				</div>
				<div className="pl-3 space-y-2">
					<div className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-sm font-bold uppercase tracking-wider ${healthy ? 'bg-primary-neon/10 text-primary-neon border border-primary-neon/30' : 'bg-error/10 text-error border border-error/30'}`}>
						{status}
					</div>
					{extraNode && <div className="mt-3 text-sm text-on-surface-variant font-mono">{extraNode}</div>}
				</div>
			</div>
		);
	};

	return (
		<div className="space-y-6">
			{/* Overall Status */}
			<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-8 rounded-2xl shadow-lg ring-1 ring-white/5">
				<div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
					<div>
						<h2 className="text-2xl font-black text-on-surface mb-2 tracking-tight">System Status Outline</h2>
						<p className="text-on-surface-variant font-medium">Real-time health of all Argus gateway components</p>
					</div>
					<div className="flex flex-col items-end gap-2">
						<div className={`text-2xl font-black uppercase tracking-widest flex items-center gap-3 ${isHealthy(health.status) ? "text-primary-neon" : "text-error"}`}>
							<span className="relative flex h-5 w-5">
								<span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isHealthy(health.status) ? 'bg-primary-neon' : 'bg-error'}`}></span>
								<span className={`relative inline-flex rounded-full h-5 w-5 shadow-[0_0_10px_rgba(0,255,157,1)] ${isHealthy(health.status) ? 'bg-primary-neon' : 'bg-error shadow-[0_0_10px_rgba(255,113,108,1)]'}`}></span>
							</span>
							{health.status}
						</div>
						{health.last_check && (
							<div className="flex items-center gap-1.5 text-xs text-on-surface-variant font-mono">
								<Clock className="w-3.5 h-3.5" />
								{new Date(health.last_check).toLocaleString()}
							</div>
						)}
					</div>
				</div>
			</div>

			<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
				<StatusCard 
					title="PostgreSQL Primary" 
					status={health.postgres_primary} 
					icon={Database} 
					extraNode={health.postgres_primary_latency_ms && `Latency: ${health.postgres_primary_latency_ms}ms`} 
				/>
				<StatusCard 
					title="PostgreSQL Replica" 
					status={health.postgres_replica} 
					icon={Database} 
					extraNode={health.postgres_replica_latency_ms && `Latency: ${health.postgres_replica_latency_ms}ms`} 
				/>
				<StatusCard 
					title="Redis Cache Tier" 
					status={health.redis} 
					icon={Server} 
					extraNode={health.redis_memory_usage_mb !== undefined && `Memory: ${health.redis_memory_usage_mb}MB`} 
				/>
				<StatusCard 
					title="Circuit Breaker" 
					status={health.circuit_breaker_state === "closed" ? "ok" : "tripped"} 
					icon={Zap} 
					extraNode={`State: ${health.circuit_breaker_state?.toUpperCase()}`}
				/>
			</div>

			{/* Additional Data */}
			<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-8 rounded-2xl shadow-lg ring-1 ring-white/5">
				<h3 className="text-lg font-bold text-on-surface mb-6 flex items-center gap-2">
					<span className="w-1.5 h-6 bg-primary-container rounded-full"></span>
					Gateway Telemetry
				</h3>
				<div className="grid grid-cols-2 md:grid-cols-3 gap-8">
					{health.uptime_seconds && (
						<div>
							<div className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">Uptime</div>
							<div className="text-2xl font-mono text-on-surface">{Math.floor(health.uptime_seconds / 86400)}d</div>
						</div>
					)}
					{health.request_count !== undefined && (
						<div>
							<div className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">Total Requests</div>
							<div className="text-2xl font-mono text-on-surface">{health.request_count.toLocaleString()}</div>
						</div>
					)}
					{health.current_connections !== undefined && (
						<div>
							<div className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1">Active Connections</div>
							<div className="text-2xl font-mono text-on-surface">{health.current_connections}</div>
						</div>
					)}
				</div>
			</div>

			{health.last_successful_query_at && (
				<div className="bg-primary-neon/5 border border-primary-neon/20 p-4 rounded-xl flex items-center gap-3">
					<CheckCircle className="w-5 h-5 text-primary-neon" />
					<span className="text-primary-neon/80 font-mono text-sm">Last successful query completed at {new Date(health.last_successful_query_at).toLocaleString()}</span>
				</div>
			)}
		</div>
	);
}
