import React, { useState, useEffect } from "react";
import { api } from "../utils/api";
import { CheckCircle, AlertCircle, Clock, Database, Server, Zap, Activity, Cpu, HardDrive, Network, AlertTriangle, TrendingUp, BarChart2, Check, ExternalLink } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from "recharts";



export default function HealthStatus() {
	const [health, setHealth] = useState<any>(null);
	const [budget, setBudget] = useState<any>(null);
	const [slowQueries, setSlowQueries] = useState<any[]>([]);
	const [auditLogs, setAuditLogs] = useState<any[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");


	useEffect(() => {
		fetchData();
		const interval = setInterval(() => {
      fetchData();
    }, 10000);
		return () => clearInterval(interval);
	}, []);

	const fetchData = async () => {
		try {
			const [healthRes, budgetRes, slowRes, auditRes] = await Promise.allSettled([
				api.checkHealth(),
				api.getBudget(),
				api.getSlowQueries(),
				api.getAuditLogs()
			]);

			if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data);
			if (budgetRes.status === 'fulfilled') setBudget(budgetRes.value.data);
			if (slowRes.status === 'fulfilled') setSlowQueries(Array.isArray(slowRes.value.data?.items) ? slowRes.value.data.items : Array.isArray(slowRes.value.data) ? slowRes.value.data : []);
			if (auditRes.status === 'fulfilled') setAuditLogs(Array.isArray(auditRes.value.data) ? auditRes.value.data : []);

			setError("");
		} catch (err) {
			setError("Failed to fetch observability data");
		} finally {
			setLoading(false);
		}
	};

	if (loading && !health) {
		return (
			<div className="flex items-center justify-center py-24">
				<div className="text-primary-neon animate-pulse text-lg tracking-widest font-semibold flex items-center gap-3">
					<Activity className="w-5 h-5 animate-pulse" />
					ESTABLISHING OBSERVABILITY LINK...
				</div>
			</div>
		);
	}

	if (error && !health) {
		return (
			<div className="bg-error-dim/10 border border-error/30 p-6 rounded-2xl flex items-center gap-3">
				<AlertCircle className="w-6 h-6 text-error flex-shrink-0" />
				<span className="text-error font-mono font-medium">{error}</span>
			</div>
		);
	}

	const isHealthy = (status: string) => status === "healthy" || status === "ok";

	const formatUptime = (seconds: number) => {
		if (!seconds) return "---";
		const days = Math.floor(seconds / 86400);
		const hrs = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
		return `${days}d ${hrs}h ${mins}m`;
	};

  const MetricBlock = ({ title, value, icon: Icon, valueClass = "text-on-surface", subtext }: any) => (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">
        <Icon className="w-3.5 h-3.5" /> {title}
      </div>
      <div className={`text-3xl font-black ${valueClass}`}>{value}</div>
      {subtext && <div className="text-xs text-on-surface-variant/70 font-medium">{subtext}</div>}
    </div>
  );

	return (
		<div className="space-y-6">
			{/* 1. Global System Pulse */}
      <div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-3xl shadow-lg ring-1 ring-white/5 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary-neon/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>
        <div className="flex flex-col md:flex-row items-center justify-between gap-8 relative z-10">
          <div className="flex items-center gap-6">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 shadow-[0_0_20px_rgba(0,255,157,0.15)] ${health && isHealthy(health.status) ? 'bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30' : 'bg-gradient-to-br from-error/20 to-error-dim/5 border border-error/30'}`}>
              <Activity className={`w-8 h-8 ${health && isHealthy(health.status) ? 'text-primary-neon drop-shadow-[0_0_8px_#00FF9D]' : 'text-error drop-shadow-[0_0_8px_#FF4C4C]'}`} />
            </div>
            <div>
              <h2 className="text-2xl font-black text-on-surface tracking-tight mb-1">Gateway Pulse</h2>
              <div className="flex items-center gap-2">
                <span className={`flex items-center gap-1 text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${health && isHealthy(health.status) ? 'bg-primary-neon/10 text-primary-neon border-primary-neon/20' : 'bg-error/10 text-error border-error/20'}`}>
                  {health && isHealthy(health.status) ? <><Check className="w-3 h-3" /> All Systems Nominal</> : <><AlertTriangle className="w-3 h-3" /> System Degraded</>}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center justify-end gap-10 lg:gap-16">
            <MetricBlock title="Uptime" value={health?.uptime_seconds ? formatUptime(health.uptime_seconds) : "---"} icon={Clock} />
            <MetricBlock title="Active Conns" value={health?.current_connections ?? "---"} icon={Network} />
            <MetricBlock title="Circuit Breaker" value={health?.circuit_breaker_state?.toUpperCase() ?? "---"} icon={Zap} valueClass={health?.circuit_breaker_state === 'closed' ? 'text-primary-neon' : 'text-error'} subtext="Security Gateway" />
          </div>
        </div>      </div>

      {/* 2. Cache Analytics */}
      <div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-3xl shadow-lg ring-1 ring-white/5">
        <h3 className="font-bold text-on-surface mb-6 flex items-center gap-2">
          <Database className="w-5 h-5 text-on-surface-variant" /> Cache Analytics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-surface-high/20 p-4 rounded-2xl border border-surface-high/50">
            <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Cache Hit Rate</div>
            <div className="text-2xl font-black text-primary-neon">{health?.metrics?.cache_hit_ratio ?? 0}%</div>
          </div>
          <div className="bg-surface-high/20 p-4 rounded-2xl border border-surface-high/50">
            <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Cache Miss Rate</div>
            <div className="text-2xl font-black text-on-surface">{health?.metrics?.cache_miss_ratio ?? 0}%</div>
          </div>
          <div className="bg-surface-high/20 p-4 rounded-2xl border border-surface-high/50">
            <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Entries Cached</div>
            <div className="text-2xl font-black text-on-surface">{health?.metrics?.entries_cached ?? 0}</div>
          </div>
          <div className="bg-surface-high/20 p-4 rounded-2xl border border-surface-high/50">
            <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Entries Invalidated</div>
            <div className="text-2xl font-black text-error">{health?.metrics?.entries_invalidated ?? 0}</div>
          </div>
          <div className="bg-surface-high/20 p-4 rounded-2xl border border-surface-high/50">
            <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Avg Invalidation</div>
            <div className="text-2xl font-black text-on-surface">{health?.metrics?.avg_invalidation_ms ?? 0}ms</div>
          </div>
        </div>
      </div>

			{/* 3. Anomalies & Threat Events */}
			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
				{/* Performance Anomalies (Slow Queries) */}
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-3xl shadow-lg ring-1 ring-white/5 flex flex-col">
					<h3 className="font-bold text-on-surface mb-6 flex items-center gap-2">
						<Clock className="w-5 h-5 text-on-surface-variant" /> Performance Anomalies (APM)
					</h3>
					<div className="space-y-3 flex-1">
						{slowQueries && slowQueries.length > 0 ? (
							slowQueries.slice(0, 8).map((q: any, i: number) => (
								<div key={i} className="flex justify-between items-center p-4 bg-surface-high/20 rounded-xl border border-surface-high/50 hover:bg-surface-high/40 transition-colors group">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded bg-surface-high text-on-surface text-[10px] font-bold uppercase tracking-widest font-mono">TRACE ID</span>
                      <span className="text-[10px] text-on-surface-variant font-mono">{q.trace_id || "N/A"}</span>
                    </div>
									  <code className="text-xs text-on-surface font-mono truncate block group-hover:text-primary-neon transition-colors">{q.query || q.statement}</code>
                  </div>
									<div className="text-right ml-4 shrink-0">
                    <div className="text-error text-lg font-black font-mono tracking-tight">{q.duration_ms || q.execution_time || q.latency_ms}ms</div>
                  </div>
								</div>
							))
						) : (
							<div className="h-full flex flex-col items-center justify-center p-8 text-center border border-dashed border-surface-high rounded-xl bg-surface-high/10">
								<CheckCircle className="w-8 h-8 text-primary-neon/50 mb-3" />
                <span className="text-on-surface font-medium text-sm">No Performance Anomalies</span>
                <span className="text-on-surface-variant text-xs mt-1">All queries completing within SLA.</span>
							</div>
						)}
					</div>
				</div>

				{/* System Events & Errors (Audit Logs) */}
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-3xl shadow-lg ring-1 ring-white/5 flex flex-col">
					<h3 className="font-bold text-on-surface mb-6 flex items-center gap-2">
						<AlertTriangle className="w-5 h-5 text-on-surface-variant" /> System Event Log
					</h3>
					<div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar">
						{auditLogs && auditLogs.length > 0 ? (
							auditLogs.slice(0, 8).map((log: any, i: number) => {
                const isError = log.status === 'error' || log.action?.includes('error') || log.event_type?.includes('error');
                return (
								<div key={i} className="flex justify-between items-start p-4 bg-surface-high/20 rounded-xl border border-surface-high/50">
									<div className="flex gap-4">
                    <div className="mt-0.5 shrink-0">
                      {isError ? <AlertCircle className="w-4 h-4 text-error" /> : <Activity className="w-4 h-4 text-primary-neon" />}
                    </div>
                    <div className="flex flex-col gap-1 min-w-0">
                      <span className={`text-xs font-bold uppercase tracking-wider ${isError ? 'text-error' : 'text-on-surface'}`}>
                        {log.action || log.event_type || log.query_type || 'System Event'}
                      </span>
                      <span className="text-xs text-on-surface-variant/80 truncate block">
                        {log.details || (log.payload ? JSON.stringify(log.payload) : 'Execution recorded via secure gateway')}
                      </span>
                    </div>
                  </div>
									<span className="text-[10px] text-on-surface-variant/50 font-mono whitespace-nowrap ml-4 mt-0.5">
										{new Date(log.timestamp || log.created_at).toLocaleTimeString()}
									</span>
								</div>
							)})
						) : (
							<div className="h-full flex flex-col items-center justify-center p-8 text-center border border-dashed border-surface-high rounded-xl bg-surface-high/10">
                <CheckCircle className="w-8 h-8 text-primary-neon/50 mb-3" />
                <span className="text-on-surface font-medium text-sm">System Nominal</span>
                <span className="text-on-surface-variant text-xs mt-1">No anomalous events recorded.</span>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
