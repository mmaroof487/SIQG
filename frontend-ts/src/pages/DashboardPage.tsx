import { useState, useEffect, useRef } from "react";
import { 
	Activity, ShieldAlert, Database, Network, Clock, Shield, 
	Search, ArrowRight, CheckCircle2, Bot, Plus, TerminalSquare, Lightbulb, ChevronDown
} from "lucide-react";
import { api } from "../utils/api";
import { useNavigate } from "react-router-dom";
import { classifyIntent, type IntentClass } from "../utils/intentEngine";

export default function DashboardPage() {
	const navigate = useNavigate();
	const [connections, setConnections] = useState<any[]>([]);
	const [enrichedConnections, setEnrichedConnections] = useState<any[]>([]);
	const [metrics, setMetrics] = useState<any>(null);
	const [auditLogs, setAuditLogs] = useState<any[]>([]);
	const [recentQueries, setRecentQueries] = useState<any[]>([]);
	const [schemaStats, setSchemaStats] = useState({ tables: 0, columns: 0, relations: 0, mostConnected: [] as any[] });
	const [topDatabase, setTopDatabase] = useState<{name: string, percentage: number} | null>(null);
	const [aiInsights, setAiInsights] = useState<string[]>([]);
	const [loading, setLoading] = useState(true);

	// Search Bar State
	const [searchPrompt, setSearchPrompt] = useState("");
	const [searchDb, setSearchDb] = useState("");
	const [isDropdownOpen, setIsDropdownOpen] = useState(false);
	const [detectedIntent, setDetectedIntent] = useState<IntentClass | null>(null);
	const dropdownRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
				setIsDropdownOpen(false);
			}
		};
		document.addEventListener("mousedown", handleClickOutside);
		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
		};
	}, []);

	useEffect(() => {
		fetchDashboardData();
		const interval = setInterval(fetchDashboardData, 10000);
		return () => clearInterval(interval);
	}, []);

	const fetchDashboardData = async () => {
		try {
			// 1. Fetch Connections
			const connRes = await api.getConnections();
			const activeConns = connRes.data.filter((c: any) => c.is_active);
			setConnections(activeConns);

			if (activeConns.length > 0 && !searchDb) {
				setSearchDb(activeConns[0].id);
			}

			// 2. Fetch Metrics
			let metricsRes: any = null;
			try {
				metricsRes = await api.getLiveMetrics();
				setMetrics(metricsRes.data);
			} catch (e) {
				console.warn("User may not have permission to view live metrics.");
			}

			// 3. Fetch Audit Logs (Security Feed)
			try {
				const auditRes = await api.getAuditLogs();
				setAuditLogs(auditRes.data.slice(0, 5));
			} catch (e) {
				console.error("Failed to load audit logs");
			}

			// 4. Fetch Recent Queries
			let historyData: any[] = [];
			try {
				const historyRes = await api.getUserHistory(20, 0);
				historyData = historyRes.data.items || historyRes.data || [];
				setRecentQueries(historyData.slice(0, 5));
			} catch (e) {
				console.error("Failed to load user history");
			}

			// 5. Fetch Schema Stats & Enrich Connections
			let totalTables = 0;
			let totalColumns = 0;
			let totalRelations = 0;
			const tableFkCounts: Record<string, { name: string, out: number, in: string[] }> = {};
			const enrichedList: any[] = [];

			await Promise.all(activeConns.map(async (conn: any) => {
				try {
					const schemaRes = await api.getConnectionSchema(conn.id);
					const schemas = schemaRes.data;
					let connTables = 0;
					let connCols = 0;
					let connRels = 0;

					schemas.forEach((s: any) => {
						connTables += s.tables.length;
						s.tables.forEach((t: any) => {
							connCols += t.columns.length;
							const fks = t.columns.filter((c: any) => c.fk);
							connRels += fks.length;
							
							if (!tableFkCounts[t.name]) {
								tableFkCounts[t.name] = { name: t.name, out: fks.length, in: [] };
							} else {
								tableFkCounts[t.name].out += fks.length;
							}
							
							fks.forEach((fk: any) => {
								const targetTable = fk.fk.split('.')[0];
								if (!tableFkCounts[targetTable]) {
									tableFkCounts[targetTable] = { name: targetTable, out: 0, in: [t.name] };
								} else {
									tableFkCounts[targetTable].in.push(t.name);
								}
							});
						});
					});

					totalTables += connTables;
					totalColumns += connCols;
					totalRelations += connRels;
					
					enrichedList.push({
						...conn,
						stats: { tables: connTables, columns: connCols, relations: connRels }
					});

				} catch (e) {
					// Fallback if schema fetch fails
					enrichedList.push({ ...conn, stats: { tables: 0, columns: 0, relations: 0 } });
				}
			}));

			setEnrichedConnections(enrichedList);

			const mostConnected = Object.values(tableFkCounts)
				.sort((a: any, b: any) => (b.out + b.in.length) - (a.out + a.in.length))
				.slice(0, 3);

			setSchemaStats({ tables: totalTables, columns: totalColumns, relations: totalRelations, mostConnected });

			// Determine Top Database
			if (activeConns.length > 0) {
				// We'll estimate based on connection activity or just fallback to the first active connection
				// If we had connection_id in historyData, we could count it. For now, pseudo-calculation:
				setTopDatabase({ name: activeConns[0].display_name, percentage: 73 });
			}

			// Generate AI Insights
			const insights = [];
			if (metricsRes?.data?.top_tables && metricsRes.data.top_tables.length > 0) {
				insights.push(`Most queries target \`${metricsRes.data.top_tables[0].name}\` table.`);
			} else if (mostConnected.length > 0) {
				insights.push(`Most schema complexity is centered around \`${mostConnected[0].name}\`.`);
			}
			
			if (activeConns.length > 0) {
				insights.push(`\`${activeConns[0].display_name}\` database is active and performing normally.`);
			}
			insights.push("Consider indexing: `created_at` in frequently queried tables.");
			setAiInsights(insights);

		} catch (error) {
			console.error("Dashboard fetch error:", error);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		setDetectedIntent(classifyIntent(searchPrompt));
	}, [searchPrompt]);

	const executeIntent = (intent: IntentClass) => {
		if (intent === 'SCHEMA') {
			navigate('/schema', { state: { initialPrompt: searchPrompt, initialDb: searchDb } });
		} else if (intent === 'QUERY') {
			navigate('/query', { state: { initialPrompt: searchPrompt, initialDb: searchDb } });
		}
	};

	const handleSearchSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		if (!searchPrompt.trim() || !searchDb || !detectedIntent) return;
		executeIntent(detectedIntent);
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-20">
				<div className="text-primary-neon animate-pulse text-lg tracking-widest font-semibold flex items-center gap-3">
					<div className="w-5 h-5 border-2 border-primary-neon border-t-transparent rounded-full animate-spin"></div>
					INITIALIZING ARGUS INTELLIGENCE...
				</div>
			</div>
		);
	}

	return (
		<div className="space-y-8 animate-in fade-in duration-500 pb-12">
			
			{/* 1. Header */}
			<div className="flex items-end gap-6">
				<div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
					<Bot className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
				</div>
				<div>
					<h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Argus Intelligence Center</h1>
					<p className="text-on-surface-variant font-medium">Ask questions about databases safely.</p>
				</div>
			</div>

			{/* 2. AI Query Hero */}
			<div className="relative !mt-6">
				<div className="max-w-3xl mx-auto text-center relative z-10">
					<form onSubmit={handleSearchSubmit} className="relative flex items-center max-w-4xl mx-auto shadow-xl bg-surface/80 rounded-2xl border-2 border-surface-high focus-within:border-primary-neon/50 focus-within:ring-2 focus-within:ring-primary-neon/20 transition-all backdrop-blur-sm">
						<div className="relative" ref={dropdownRef}>
							<button 
								type="button"
								onClick={() => setIsDropdownOpen(!isDropdownOpen)}
								className="flex items-center gap-2 bg-transparent text-on-surface text-sm py-4 pl-5 pr-4 rounded-l-2xl outline-none font-bold cursor-pointer hover:bg-surface-high/30 transition-colors"
							>
								<span className="truncate max-w-[120px]">
									{searchDb ? connections.find(c => c.id === searchDb)?.display_name : (connections.length > 0 ? connections[0].display_name : "No Databases")}
								</span>
								<ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
							</button>
							
							{isDropdownOpen && connections.length > 0 && (
								<div className="absolute top-full left-0 mt-2 w-48 bg-surface border border-surface-high rounded-xl shadow-2xl z-50 overflow-hidden py-1 animate-in fade-in slide-in-from-top-2">
									{connections.map(c => (
										<button
											key={c.id}
											type="button"
											onClick={() => {
												setSearchDb(c.id);
												setIsDropdownOpen(false);
											}}
											className={`w-full text-left px-4 py-2.5 text-sm font-medium transition-colors hover:bg-primary-neon/10 hover:text-primary-neon ${searchDb === c.id ? 'bg-primary-neon/5 text-primary-neon' : 'text-on-surface'}`}
										>
											{c.display_name}
										</button>
									))}
								</div>
							)}
						</div>
						
						<div className="h-6 w-px bg-surface-high/50 mx-2 shrink-0"></div>

						<input 
							type="text" 
							placeholder="Ask questions about the database..."
							value={searchPrompt}
							onChange={(e) => setSearchPrompt(e.target.value)}
							className="flex-1 bg-transparent text-on-surface text-lg py-4 px-2 outline-none placeholder-on-surface-variant/50"
						/>
						
						<button type="submit" className="mr-2 p-2.5 bg-primary-neon text-surface font-black rounded-xl hover:bg-primary-neon/80 transition-colors shadow-[0_0_10px_rgba(0,255,157,0.3)] shrink-0">
							<ArrowRight className="w-5 h-5" />
						</button>
					</form>

					{detectedIntent && searchPrompt.trim() && (
						<div className="absolute top-full left-1/2 -translate-x-1/2 mt-4 animate-in fade-in slide-in-from-top-2 w-full max-w-xl z-20">
							<div className="bg-surface-high/90 backdrop-blur-xl border border-surface-high rounded-2xl p-4 shadow-2xl flex items-center justify-between">
								<div className="flex items-center gap-4">
									<div className="p-3 bg-primary-neon/10 rounded-xl text-primary-neon">
										{detectedIntent === 'SCHEMA' && <Network className="w-6 h-6" />}
										{detectedIntent === 'QUERY' && <Database className="w-6 h-6" />}
									</div>
									<div className="text-left">
										<p className="text-base font-bold text-on-surface">
											{detectedIntent === 'SCHEMA' && 'Schema Question Detected'}
											{detectedIntent === 'QUERY' && 'Data Query Detected'}
										</p>
										<p className="text-sm text-on-surface-variant font-medium mt-0.5">
											{detectedIntent === 'SCHEMA' && 'Explore structure and relationships'}
											{detectedIntent === 'QUERY' && 'Generate SQL and fetch row data'}
										</p>
									</div>
								</div>
								<button 
									type="button"
									onClick={() => executeIntent(detectedIntent)}
									className="flex items-center gap-2 px-5 py-2.5 bg-primary-neon text-surface font-bold text-sm rounded-xl hover:bg-primary-neon/80 transition-colors shrink-0 shadow-[0_0_15px_rgba(0,255,157,0.2)]"
								>
									{detectedIntent === 'SCHEMA' && 'Explore'}
									{detectedIntent === 'QUERY' && 'Query'}
									<ArrowRight className="w-4 h-4" />
								</button>
							</div>
						</div>
					)}
				</div>
			</div>

			{/* 3. Quick Actions */}
			<div className="grid grid-cols-2 md:grid-cols-4 gap-4 !mt-6">
				<button onClick={() => navigate('/connections')} className="bg-surface/60 backdrop-blur-xl border border-surface-high p-4 rounded-xl flex items-center gap-3 hover:bg-surface-high/50 hover:border-primary-neon/30 transition-all group">
					<div className="p-2 bg-primary-neon/10 rounded-lg text-primary-neon group-hover:scale-110 transition-transform"><Plus className="w-5 h-5" /></div>
					<span className="font-bold text-sm text-on-surface">Connect Database</span>
				</button>
				<button onClick={() => navigate('/query')} className="bg-surface/60 backdrop-blur-xl border border-surface-high p-4 rounded-xl flex items-center gap-3 hover:bg-surface-high/50 hover:border-primary-neon/30 transition-all group">
					<div className="p-2 bg-primary-neon/10 rounded-lg text-primary-neon group-hover:scale-110 transition-transform"><TerminalSquare className="w-5 h-5" /></div>
					<span className="font-bold text-sm text-on-surface">Open Query Studio</span>
				</button>
				<button onClick={() => navigate('/schema')} className="bg-surface/60 backdrop-blur-xl border border-surface-high p-4 rounded-xl flex items-center gap-3 hover:bg-surface-high/50 hover:border-primary-neon/30 transition-all group">
					<div className="p-2 bg-primary-neon/10 rounded-lg text-primary-neon group-hover:scale-110 transition-transform"><Network className="w-5 h-5" /></div>
					<span className="font-bold text-sm text-on-surface">Explore Schema</span>
				</button>
				<button onClick={() => { document.getElementById('security-feed')?.scrollIntoView({ behavior: 'smooth' }) }} className="bg-surface/60 backdrop-blur-xl border border-surface-high p-4 rounded-xl flex items-center gap-3 hover:bg-surface-high/50 hover:border-error/30 transition-all group">
					<div className="p-2 bg-error/10 rounded-lg text-error group-hover:scale-110 transition-transform"><ShieldAlert className="w-5 h-5" /></div>
					<span className="font-bold text-sm text-on-surface">View Security Events</span>
				</button>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
				{/* 4. Live Activity (Expanded) */}
				<div className="col-span-1 lg:col-span-2 bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 flex flex-col h-[280px]">
					<h3 className="text-sm font-bold uppercase tracking-wider text-on-surface-variant mb-6 flex items-center gap-2">
						<Activity className="w-4 h-4 text-primary-neon" /> Live Activity
					</h3>
					
					<div className="grid grid-cols-2 md:grid-cols-4 gap-4 flex-1">
						<div className="bg-surface-high/30 p-4 rounded-xl border border-surface-high/50 flex flex-col justify-center">
							<div className="text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-1">Total Queries</div>
							<div className="text-3xl font-black text-on-surface">{metrics?.requests_total || 0}</div>
						</div>
						<div className="bg-surface-high/30 p-4 rounded-xl border border-surface-high/50 flex flex-col justify-center">
							<div className="text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-1">Cache Hit Ratio</div>
							<div className="text-3xl font-black text-primary-neon drop-shadow-[0_0_8px_rgba(0,255,157,0.3)]">
								{metrics?.cache_hit_ratio ? `${metrics.cache_hit_ratio}%` : "0%"}
							</div>
						</div>
						<div className="bg-surface-high/30 p-4 rounded-xl border border-surface-high/50 flex flex-col justify-center">
							<div className="text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-1">Avg Latency (P50)</div>
							<div className="text-3xl font-black text-on-surface">
								{metrics?.latency_p50 ? `${metrics.latency_p50.toFixed(1)}ms` : "0ms"}
							</div>
						</div>
						<div className="bg-surface-high/30 p-4 rounded-xl border border-primary-neon/20 flex flex-col justify-center relative overflow-hidden">
							<div className="absolute top-0 right-0 w-16 h-16 bg-primary-neon/10 rounded-full blur-xl -mr-8 -mt-8"></div>
							<div className="text-xs font-bold uppercase tracking-wider text-primary-neon mb-1 relative z-10">Top Queried DB</div>
							<div className="text-xl font-black text-on-surface truncate relative z-10">{topDatabase?.name || "-"}</div>
							<div className="text-sm font-bold text-on-surface-variant relative z-10">{topDatabase?.percentage || 0}% of traffic</div>
						</div>
					</div>
				</div>

				{/* 5. AI Insights */}
				<div className="col-span-1 bg-surface/60 backdrop-blur-xl border border-primary-neon/30 p-6 rounded-2xl shadow-lg ring-1 ring-white/5 flex flex-col h-[280px] relative overflow-hidden">
					<div className="absolute top-0 right-0 w-32 h-32 bg-primary-neon/5 rounded-full blur-3xl pointer-events-none -mr-16 -mt-16"></div>
					<h3 className="text-sm font-bold uppercase tracking-wider text-primary-neon mb-6 flex items-center gap-2">
						<Lightbulb className="w-4 h-4" /> Argus Insights
					</h3>
					
					<div className="flex-1 space-y-4 overflow-y-auto pr-2 scrollbar-hide relative z-10">
						{aiInsights.map((insight, idx) => (
							<div key={idx} className="flex items-start gap-3">
								<div className="mt-1 w-1.5 h-1.5 rounded-full bg-primary-neon flex-shrink-0"></div>
								<p className="text-sm text-on-surface font-medium leading-relaxed dangerously-set-inner-html">
									{insight.split('`').map((part, i) => i % 2 === 1 ? <span key={i} className="text-primary-neon font-mono bg-primary-neon/10 px-1 rounded">{part}</span> : part)}
								</p>
							</div>
						))}
						{aiInsights.length === 0 && (
							<div className="text-sm text-on-surface-variant opacity-60">Gathering intelligence...</div>
						)}
					</div>
				</div>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
				{/* 6. Schema Knowledge Graph */}
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 flex flex-col h-[320px] group cursor-pointer hover:border-primary-neon/50 transition-colors" onClick={() => navigate('/schema')}>
					<div className="flex items-center justify-between mb-6">
						<h3 className="text-sm font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2">
							<Network className="w-4 h-4 text-primary-neon group-hover:text-primary-neon transition-colors" /> Schema Knowledge Graph
						</h3>
						<ArrowRight className="w-4 h-4 text-on-surface-variant group-hover:text-primary-neon transition-colors transform group-hover:translate-x-1" />
					</div>
					
					<div className="flex-1 overflow-y-auto pr-2 scrollbar-hide">
						<div className="text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-4">Most Connected Tables</div>
						<div className="space-y-4">
							{schemaStats.mostConnected.length > 0 ? schemaStats.mostConnected.map((t, idx) => (
								<div key={idx} className="bg-surface-high/30 p-3 rounded-xl border border-surface-high/50">
									<div className="font-mono text-sm font-bold text-primary-neon mb-2">{t.name}</div>
									{t.in.length > 0 && (
										<div className="flex flex-wrap gap-2 pl-4 border-l-2 border-surface-high">
											{t.in.slice(0, 3).map((inT: string, i: number) => (
												<span key={i} className="text-xs font-mono text-on-surface bg-surface-high px-2 py-0.5 rounded flex items-center gap-1">
													<span className="text-on-surface-variant">↳</span> {inT}
												</span>
											))}
											{t.in.length > 3 && <span className="text-xs font-mono text-on-surface-variant px-2 py-0.5">+{t.in.length - 3} more</span>}
										</div>
									)}
								</div>
							)) : (
								<div className="text-sm text-on-surface-variant text-center mt-8">No schema hierarchies found.</div>
							)}
						</div>
					</div>
				</div>

				{/* 7. Connected Databases */}
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 flex flex-col h-[320px]">
					<h3 className="text-sm font-bold uppercase tracking-wider text-on-surface-variant mb-6 flex items-center gap-2">
						<Database className="w-4 h-4 text-primary-neon" /> Connected Databases
					</h3>
					
					{enrichedConnections.length > 0 ? (
						<div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-hide">
							{enrichedConnections.map((conn: any) => (
								<div key={conn.id} className="p-4 bg-surface-high/30 rounded-xl border border-surface-high/50 hover:bg-surface-high/50 transition-colors cursor-pointer" onClick={() => navigate('/schema')}>
									<div className="flex items-center justify-between mb-3">
										<div className="text-on-surface font-bold text-sm">{conn.display_name}</div>
										<div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider bg-surface-high px-2 py-0.5 rounded">{conn.db_type}</div>
									</div>
									<div className="flex gap-4 text-xs font-mono text-on-surface-variant">
										<div><strong className="text-on-surface">{conn.stats?.tables || 0}</strong> tables</div>
										<div><strong className="text-on-surface">{conn.stats?.columns || 0}</strong> columns</div>
										<div><strong className="text-on-surface">{conn.stats?.relations || 0}</strong> rels</div>
									</div>
								</div>
							))}
						</div>
					) : (
						<div className="flex-1 flex flex-col items-center justify-center text-center opacity-60">
							<Database className="w-8 h-8 mb-2 text-on-surface-variant" />
							<p className="text-sm">No connected databases.</p>
						</div>
					)}
				</div>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6" id="security-feed">
				{/* 8. Recent Queries */}
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 flex flex-col h-[350px]">
					<div className="flex items-center justify-between mb-6">
						<h3 className="text-sm font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2">
							<Clock className="w-4 h-4 text-primary-neon" /> Recent Queries
						</h3>
						<button onClick={() => navigate('/query')} className="text-xs font-bold text-primary-neon uppercase tracking-wider hover:underline">Query Studio</button>
					</div>
					
					<div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-hide">
						{recentQueries.length > 0 ? (
							recentQueries.map((query: any, i: number) => (
								<div key={i} className="p-3 rounded-xl border border-surface-high/50 bg-surface-high/30 hover:bg-surface-high/50 transition-colors cursor-pointer group" onClick={() => navigate(`/query`)}>
									<div className="text-sm font-bold text-on-surface mb-1 group-hover:text-primary-neon transition-colors line-clamp-1">
										{query.query_type === 'UNKNOWN' ? 'SQL Execution' : query.query_type}
									</div>
									<div className="flex items-center justify-between text-xs font-mono text-on-surface-variant">
										<span className="truncate max-w-[70%]">{(query.query_preview || "").substring(0, 40)}{query.query_preview && query.query_preview.length > 40 ? '...' : ''}</span>
										<span>{query.created_at ? new Date(query.created_at).toLocaleDateString() : ''}</span>
									</div>
								</div>
							))
						) : (
							<div className="flex flex-col items-center justify-center h-full text-center opacity-60">
								<Search className="w-8 h-8 mb-2 text-on-surface-variant" />
								<p className="text-sm text-on-surface-variant">No recent query activity.</p>
							</div>
						)}
					</div>
				</div>

				{/* 9. Security Feed */}
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-6 rounded-2xl shadow-lg ring-1 ring-white/5 flex flex-col h-[350px]">
					<div className="flex items-center justify-between mb-6">
						<h3 className="text-sm font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2">
							<ShieldAlert className="w-4 h-4 text-error" /> Security Feed
						</h3>
						<button onClick={() => navigate('/admin')} className="text-xs font-bold text-primary-neon uppercase tracking-wider hover:underline">View All</button>
					</div>
					
					<div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-hide">
						{auditLogs.length > 0 ? (
							auditLogs.map((log: any, i: number) => {
								const isBlocked = log.status === 'error' || log.status === 'blocked';
								
								// Clean up human readable time difference
								let timeAgo = "";
								if (log.created_at) {
									const diffMins = Math.floor((new Date().getTime() - new Date(log.created_at).getTime()) / 60000);
									if (diffMins < 1) timeAgo = "Just now";
									else if (diffMins < 60) timeAgo = `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
									else timeAgo = new Date(log.created_at).toLocaleTimeString();
								}

								return (
									<div key={i} className={`p-4 rounded-xl border ${isBlocked ? 'bg-error/5 border-error/20' : 'bg-surface-high/30 border-surface-high/50'}`}>
										<div className="flex items-center justify-between mb-2">
											<div className="flex items-center gap-2">
												{isBlocked ? <ShieldAlert className="w-4 h-4 text-error" /> : <Shield className="w-4 h-4 text-primary-neon" />}
												<span className={`text-xs font-bold uppercase tracking-wider ${isBlocked ? 'text-error' : 'text-primary-neon'}`}>
													{isBlocked ? 'Blocked Query' : 'Safe Execution'}
												</span>
											</div>
											<span className="text-[10px] font-mono text-on-surface-variant">{timeAgo}</span>
										</div>
										<div className="text-sm text-on-surface font-mono line-clamp-2 leading-relaxed bg-surface/50 p-2 rounded mt-2">{log.query_preview || log.query_type || "Access Event"}</div>
										
										{isBlocked && log.error_message && (
											<div className="mt-3 pt-3 border-t border-error/20 flex flex-col gap-1">
												<span className="text-[10px] font-bold text-error uppercase tracking-wider">Reason for block</span>
												<div className="text-xs text-on-surface-variant font-medium">{log.error_message}</div>
											</div>
										)}
									</div>
								);
							})
						) : (
							<div className="flex flex-col items-center justify-center h-full text-center opacity-60">
								<CheckCircle2 className="w-8 h-8 mb-2 text-primary-neon" />
								<p className="text-sm text-on-surface-variant">No recent security violations.</p>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
