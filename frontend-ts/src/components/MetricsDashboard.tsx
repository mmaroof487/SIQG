import { useState, useEffect } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { api } from "../utils/api";
import { AlertCircle } from "lucide-react";

interface LatencyPoint {
	time: string;
	p50: number;
	p95: number;
	p99: number;
}

export default function MetricsDashboard() {
	const [metrics, setMetrics] = useState<any>(null);
	const [latencyData, setLatencyData] = useState<LatencyPoint[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [anomalyExplanation, setAnomalyExplanation] = useState<string | null>(null);
	const [isExplaining, setIsExplaining] = useState(false);

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
				return newData.slice(-20);
			});

			setError("");
		} catch (err: any) {
			setError("Failed to fetch metrics");
		} finally {
			setLoading(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-12">
				<div className="text-primary-neon animate-pulse text-lg tracking-widest font-semibold flex items-center gap-3">
					<div className="w-5 h-5 border-2 border-primary-neon border-t-transparent rounded-full animate-spin"></div>
					INITIALIZING SYSTEM telemetry...
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="bg-error-dim/10 border border-error/30 p-4 rounded-xl flex items-center gap-3 shadow-[0_0_15px_rgba(255,113,108,0.1)]">
				<AlertCircle className="w-5 h-5 text-error" />
				<span className="text-error font-medium">{error}</span>
			</div>
		);
	}

	if (!metrics) {
		return <div className="text-center py-12 text-on-surface-variant font-mono">NO TELEMETRY AVAILABLE</div>;
	}

	const handleExplainAnomaly = async () => {
		setIsExplaining(true);
		setAnomalyExplanation(null);
		try {
			const res = await api.explainAnomaly(metrics);
			setAnomalyExplanation(res.data.explanation);
		} catch (err) {
			setAnomalyExplanation("Failed to generate anomaly analysis from Argus Intelligence.");
		} finally {
			setIsExplaining(false);
		}
	};

	return (
		<div className="space-y-6">
			{/* Key Metrics */}
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 transition-all hover:ring-primary-neon/20 hover:shadow-[0_0_20px_rgba(0,255,157,0.05)]">
					<div className="text-sm text-on-surface-variant mb-2 tracking-wide font-medium uppercase">Cache Hit Ratio</div>
					<div className="text-4xl font-bold text-primary-neon drop-shadow-[0_0_8px_rgba(0,255,157,0.4)]">
						{metrics.cache_hit_ratio ? `${(metrics.cache_hit_ratio * 100).toFixed(1)}%` : "N/A"}
					</div>
				</div>

				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 transition-all hover:ring-primary-neon/20 hover:shadow-[0_0_20px_rgba(0,255,157,0.05)]">
					<div className="text-sm text-on-surface-variant mb-2 tracking-wide font-medium uppercase">Requests/min</div>
					<div className="text-4xl font-bold text-on-surface drop-shadow-md">
						{metrics.requests_per_minute || 0}
					</div>
				</div>

				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 transition-all hover:ring-error/20 hover:shadow-[0_0_20px_rgba(2ff,113,108,0.05)]">
					<div className="text-sm text-on-surface-variant mb-2 tracking-wide font-medium uppercase">Slow Queries (24h)</div>
					<div className="text-4xl font-bold text-error drop-shadow-[0_0_8px_rgba(255,113,108,0.4)]">
						{metrics.slow_queries_24h || 0}
					</div>
				</div>

				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 transition-all">
					<div className="text-sm text-on-surface-variant mb-2 tracking-wide font-medium uppercase">Circuit Breaker</div>
					<div className={`text-2xl font-bold flex items-center gap-3 ${metrics.circuit_breaker_state === "closed" ? "text-primary-neon" : "text-error"}`}>
						{metrics.circuit_breaker_state === "closed" ? (
							<span className="relative flex h-4 w-4">
								<span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-neon opacity-75"></span>
								<span className="relative inline-flex rounded-full h-4 w-4 bg-primary-neon shadow-[0_0_10px_rgba(0,255,157,1)]"></span>
							</span>
						) : (
							<span className="relative inline-flex rounded-full h-4 w-4 bg-error shadow-[0_0_10px_rgba(255,113,108,1)]"></span>
						)}
						{metrics.circuit_breaker_state?.toUpperCase() || "UNKNOWN"}
					</div>
				</div>
			</div>

			{/* Anomaly Explanation Toggle */}
			<div className="flex justify-end">
				<button 
					onClick={handleExplainAnomaly} 
					disabled={isExplaining}
					className="flex items-center gap-2 px-5 py-2.5 bg-primary-neon/10 hover:bg-primary-neon/20 border border-primary-neon/30 text-primary-neon font-bold uppercase tracking-widest text-sm rounded-xl transition-all shadow-lg"
				>
					{isExplaining ? (
						<><div className="w-4 h-4 border-2 border-primary-neon border-t-transparent rounded-full animate-spin"></div> ANALYZING...</>
					) : (
						<><AlertCircle className="w-4 h-4" /> EXPLAIN ANOMALIES</>
					)}
				</button>
			</div>

			{anomalyExplanation && (
				<div className="bg-surface/80 border border-primary-container/40 p-6 rounded-2xl text-on-surface shadow-[inset_0_0_30px_rgba(0,252,155,0.05)] animate-in fade-in duration-500 mb-6">
					<h3 className="font-bold text-primary-container mb-3 flex items-center gap-2 tracking-wider uppercase text-sm">
						<AlertCircle className="w-4 h-4" /> Argus Sentinel Intelligence Report
					</h3>
					<div className="text-on-surface/90 leading-relaxed font-mono text-sm whitespace-pre-wrap">{anomalyExplanation}</div>
				</div>
			)}

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
				{/* Latency Chart */}
				<div className="lg:col-span-2 bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5">
					<h3 className="text-lg font-bold text-on-surface mb-6 flex items-center gap-2">
						<span className="w-1.5 h-6 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
						Latency Pipeline (ms)
					</h3>
					{latencyData.length > 0 ? (
						<ResponsiveContainer width="100%" height={300}>
							<LineChart data={latencyData}>
								<CartesianGrid strokeDasharray="3 3" stroke="#23262c" />
								<XAxis dataKey="time" stroke="#aaabb0" tick={{fill: '#aaabb0', fontSize: 12}} />
								<YAxis stroke="#aaabb0" tick={{fill: '#aaabb0', fontSize: 12}} />
								<Tooltip 
									contentStyle={{ backgroundColor: '#111318', border: '1px solid #23262c', borderRadius: '8px', color: '#f6f6fc' }}
									itemStyle={{ fontWeight: 'bold' }}
								/>
								<Legend wrapperStyle={{ paddingTop: '20px' }} />
								<Line type="monotone" dataKey="p50" stroke="#00FF9D" name="P50" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
								<Line type="monotone" dataKey="p95" stroke="#a0ffc3" name="P95" strokeWidth={2} dot={false} />
								<Line type="monotone" dataKey="p99" stroke="#ff716c" name="P99" strokeWidth={2} dot={false} />
							</LineChart>
						</ResponsiveContainer>
					) : (
						<div className="text-on-surface-variant text-center py-8">Collecting latency stream...</div>
					)}
				</div>

				{/* Top Tables */}
				{metrics.top_tables && metrics.top_tables.length > 0 && (
					<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5">
						<h3 className="text-lg font-bold text-on-surface mb-6 flex items-center gap-2">
							<span className="w-1.5 h-6 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
							Top Data Sectors
						</h3>
						<div className="space-y-3">
							{metrics.top_tables.map((table: any, idx: number) => (
								<div key={idx} className="flex flex-col gap-1 p-3 bg-surface-high/50 hover:bg-surface-high rounded-xl border border-surface-high transition-colors">
									<div className="flex items-center justify-between">
										<span className="text-on-surface font-semibold">{table.name}</span>
										<span className="text-primary-neon font-mono font-bold">{table.access_count}</span>
									</div>
									<div className="w-full bg-surface rounded-full h-1.5 overflow-hidden">
										<div className="bg-gradient-to-r from-primary-container to-primary-neon h-1.5 rounded-full" style={{ width: `${Math.min((table.access_count / (metrics.top_tables[0]?.access_count || 1)) * 100, 100)}%`}}></div>
									</div>
								</div>
							))}
						</div>
					</div>
				)}
			</div>
			
			{/* Request Distribution */}
			{metrics.request_distribution && (
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5">
					<h3 className="text-lg font-bold text-on-surface mb-6 flex items-center gap-2">
						<span className="w-1.5 h-6 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
						Traffic Distribution Protocol
					</h3>
					<ResponsiveContainer width="100%" height={250}>
						<BarChart data={Object.entries(metrics.request_distribution).map(([name, value]) => ({ name, value }))} margin={{ top: 20 }}>
							<CartesianGrid strokeDasharray="3 3" stroke="#23262c" vertical={false} />
							<XAxis dataKey="name" stroke="#aaabb0" tick={{fill: '#aaabb0', fontSize: 12}} />
							<YAxis stroke="#aaabb0" tick={{fill: '#aaabb0', fontSize: 12}} />
							<Tooltip 
								cursor={{ fill: '#23262c' }}
								contentStyle={{ backgroundColor: '#111318', border: '1px solid #23262c', borderRadius: '8px' }}
							/>
							<Bar dataKey="value" fill="#00fc9b" radius={[4, 4, 0, 0]} barSize={40} />
						</BarChart>
					</ResponsiveContainer>
				</div>
			)}
		</div>
	);
}
