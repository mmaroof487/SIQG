import { useState, useEffect } from "react";
import NLQueryPanel from "../components/NLQueryPanel";
import ResultsTable from "../components/ResultsTable";
import { api } from "../utils/api";
import { Copy, Play, Zap, TerminalSquare, Activity, ShieldCheck, Cpu, AlertCircle, Download } from "lucide-react";
import { useSettings } from "../contexts/SettingsContext";
import Editor from "@monaco-editor/react";

interface Connection {
  id: string;
  display_name: string;
  db_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

function BlockExplainerCard({ info }: { info: { blocked: boolean; block_reasons: string[]; suggested_fix?: string; would_execute?: string; original?: string } }) {
  return (
    <div className="bg-error/10 border border-error/30 rounded-2xl p-6 space-y-4 shadow-sm animate-in shake duration-300">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-error/20 text-error rounded-xl border border-error/30">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-bold text-error text-lg">Query Rejection Explainer</h3>
          <span className="text-[10px] bg-error/20 text-error px-2 py-0.5 rounded border border-error/30 uppercase font-black tracking-widest mt-1 inline-block">Security Gate Violation</span>
        </div>
      </div>
      
      <div className="space-y-2">
        <p className="text-xs uppercase font-bold tracking-wider text-on-surface-variant">Reason(s) for Block:</p>
        <ul className="list-disc pl-5 text-sm text-on-surface/90 space-y-1">
          {info.block_reasons.map((reason, idx) => (
            <li key={idx} className="font-medium text-error">{reason}</li>
          ))}
        </ul>
      </div>

      {info.suggested_fix && (
        <div className="p-4 bg-surface/60 border border-surface-high rounded-xl space-y-1">
          <p className="text-xs uppercase font-bold tracking-wider text-primary-neon">Suggested Fix:</p>
          <p className="text-sm text-on-surface-variant font-medium">{info.suggested_fix}</p>
        </div>
      )}

      {info.would_execute && (
        <div className="space-y-2">
          <p className="text-xs uppercase font-bold tracking-wider text-on-surface-variant">Query Sanitization Comparison:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <span className="text-[10px] uppercase font-mono tracking-widest text-on-surface-variant/50">Submitted Query</span>
              <pre className="bg-surface p-3 rounded-xl border border-surface-high text-xs text-error overflow-auto font-mono max-h-40 whitespace-pre-wrap">{info.original}</pre>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] uppercase font-mono tracking-widest text-on-surface-variant/50">Proposed Sanitized Execution</span>
              <pre className="bg-surface p-3 rounded-xl border border-surface-high text-xs text-primary-neon overflow-auto font-mono max-h-40 whitespace-pre-wrap">{info.would_execute}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function QueryPage() {
	const { mode } = useSettings();
	const [sqlQuery, setSqlQuery] = useState("SELECT * FROM users LIMIT 10;");
	const [originalSql, setOriginalSql] = useState("");
	const [showDiff, setShowDiff] = useState(false);
	const [results, setResults] = useState<any>(null);
	const [analysis, setAnalysis] = useState<any>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState("");
	const [dryRun, setDryRun] = useState(false);
	const [explanation, setExplanation] = useState("");

	// Connections state
	const [connections, setConnections] = useState<Connection[]>([]);
	const [selectedConnectionId, setSelectedConnectionId] = useState<string>("default");

	// Block Explainer state
	const [blockedInfo, setBlockedInfo] = useState<{
		blocked: boolean;
		block_reasons: string[];
		suggested_fix?: string;
		would_execute?: string;
		original?: string;
	} | null>(null);

	useEffect(() => {
		fetchConnections();
	}, []);

	const fetchConnections = async () => {
		try {
			const res = await api.getConnections();
			setConnections(res.data.filter((c: Connection) => c.is_active));
		} catch (err) {
			console.error("Failed to load connections in query page:", err);
		}
	};

	const handleSQLGenerated = (data: any) => {
		setSqlQuery(data.sql);
		setOriginalSql(data.sql);
		setExplanation(data.explanation || "");
		handleExecuteQuery(data.sql);
	};

	const handleExecuteQuery = async (query = sqlQuery) => {
		if (!query.trim()) return;

		setIsLoading(true);
		setError("");
		setBlockedInfo(null);
		setResults(null);
		setAnalysis(null);

		try {
			const response = await api.executeQuery(query, dryRun, selectedConnectionId);
			const data = response.data;

			setResults({
				rows: data.rows || [],
				columns: data.rows && data.rows.length > 0 ? Object.keys(data.rows[0]) : [],
			});

			setAnalysis({
				traceId: data.trace_id,
				queryType: data.query_type,
				latencyMs: data.latency_ms,
				cost: data.cost,
				cached: data.cached,
				slow: data.slow,
				analysis: data.analysis,
			});
		} catch (err: any) {
			const detail = err.response?.data?.detail;
			if (detail && typeof detail === "object" && detail.blocked) {
				setBlockedInfo({
					blocked: true,
					block_reasons: detail.block_reasons || [],
					suggested_fix: detail.suggested_fix || detail.suggested_fix_text,
					would_execute: detail.would_execute || detail.would_execute_sql,
					original: query,
				});
				setError("Query was blocked by the security gateway.");
			} else {
				setError(typeof detail === "string" ? detail : (err.message || "Query execution failed"));
			}
		} finally {
			setIsLoading(false);
		}
	};

	const copyToClipboard = (text: string) => {
		navigator.clipboard.writeText(text);
	};

	return (
		<div className="flex gap-6 h-full">
			{/* Main Content Area */}
			<div className="flex-1 flex flex-col space-y-6 min-w-0 pb-16">
				
				{/* Top Section */}
				<div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl p-6 shadow-sm">
					<NLQueryPanel onSQLGenerated={handleSQLGenerated} onLoading={setIsLoading} />
					
					{(mode === 'power' || sqlQuery) && (
						<div className="mt-4 border border-surface-high rounded-xl overflow-hidden shadow-inner">
							<div className="bg-surface p-2 flex justify-between items-center border-b border-surface-high">
								<div className="flex gap-4 items-center">
									<span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2 px-2">
										<TerminalSquare className="w-4 h-4" /> SQL Editor
									</span>
									{originalSql && sqlQuery !== originalSql && (
										<span className="text-[10px] bg-error/20 text-error px-2 py-0.5 rounded border border-error/30 uppercase font-black tracking-widest">Tampered</span>
									)}

									{/* Database Selector Dropdown */}
									<select
										value={selectedConnectionId}
										onChange={(e) => setSelectedConnectionId(e.target.value)}
										className="bg-surface-high/60 border border-surface-high rounded-lg text-xs font-bold text-on-surface px-3 py-1.5 outline-none focus:border-primary-neon/50 transition-colors cursor-pointer"
									>
										<option value="default">Argus Primary (default)</option>
										{connections.map(c => (
											<option key={c.id} value={c.id}>{c.display_name}</option>
										))}
									</select>
								</div>
								
								<button 
									onClick={() => handleExecuteQuery()} 
									disabled={isLoading || !sqlQuery.trim()} 
									className="px-4 py-1.5 bg-primary-neon/10 hover:bg-primary-neon/20 text-primary-neon text-xs font-bold uppercase tracking-widest rounded transition-colors border border-primary-neon/30 flex items-center gap-2"
								>
									<Play className="w-3 h-3" /> {dryRun ? 'Dry Run' : 'Execute'}
								</button>
							</div>
							<div className="h-48 relative">
								<Editor
									height="100%"
									defaultLanguage="sql"
									theme="vs-dark"
									value={sqlQuery}
									onChange={(val) => setSqlQuery(val || "")}
									options={{ minimap: { enabled: false }, fontSize: 13, padding: { top: 12 } }}
								/>
							</div>
						</div>
					)}
					<div className="flex items-center gap-4 mt-4 text-sm">
						{sqlQuery && (
							<button onClick={async () => {
								try {
									const res = await api.explainQuery(sqlQuery);
									setExplanation(res.data.explanation);
								} catch {}
							}} className="text-primary-neon hover:text-primary-container transition-colors font-semibold flex items-center gap-1.5 text-xs uppercase tracking-wider">
								<Zap className="w-4 h-4" /> Explain this SQL
							</button>
						)}
					</div>
				</div>

				{/* Block Explainer Section */}
				{blockedInfo && (
					<BlockExplainerCard info={blockedInfo} />
				)}

				{/* General Error Alert */}
				{error && !blockedInfo && (
					<div className="p-4 bg-error/10 border border-error/30 text-error rounded-xl flex items-center gap-3">
						<AlertCircle className="w-5 h-5 flex-shrink-0" />
						<span className="text-sm font-medium">{error}</span>
					</div>
				)}

				{/* Middle Section: Results */}
				{results && (
					<div className="flex flex-col flex-1 bg-surface/40 border border-surface-high rounded-2xl overflow-hidden shadow-sm">
						<div className="p-4 border-b border-surface-high flex justify-between items-center bg-surface/60">
							<div className="flex flex-col">
								<h3 className="font-bold text-on-surface">Execution Results</h3>
								<div className="text-xs font-mono text-on-surface-variant mt-0.5 opacity-80 flex items-center gap-2">
									<span>{results.rows.length} rows · {analysis?.latencyMs.toFixed(1)}ms · {analysis?.cached ? 'cached' : 'live'}</span>
									<span className="h-3 w-px bg-surface-high"></span>
									<span className="text-primary-neon font-semibold uppercase tracking-wider text-[10px] bg-primary-neon/10 border border-primary-neon/20 px-2 py-0.5 rounded">
										Results from: {selectedConnectionId === "default" ? "Argus Primary (default)" : (connections.find(c => c.id === selectedConnectionId)?.display_name || "External DB")}
									</span>
								</div>
							</div>
							<div className="flex gap-2">
								<button className="p-2 hover:bg-surface-high rounded text-on-surface-variant transition-colors" title="Export JSON">
									<Download className="w-4 h-4" />
								</button>
							</div>
						</div>
						
						{results.rows.length === 0 ? (
							<div className="p-8 text-center text-on-surface-variant italic border-t border-surface-high">No results found</div>
						) : (
							<div className="overflow-auto bg-surface/20">
								<ResultsTable rows={results.rows} columns={results.columns} isLoading={isLoading} error={error} />
							</div>
						)}
					</div>
				)}

				{/* Bottom Bar Fixed */}
				<div className="fixed bottom-0 left-64 right-0 h-12 bg-surface/95 border-t border-surface-high backdrop-blur-md flex items-center justify-between px-6 z-40">
					<div className="flex items-center gap-6">
						<label className="flex items-center gap-2 cursor-pointer group">
							<input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} className="w-4 h-4 rounded border-surface-high accent-primary-neon" />
							<span className="text-xs font-bold text-on-surface-variant group-hover:text-on-surface uppercase tracking-wider transition-colors">Dry run mode</span>
						</label>
						{dryRun && (
							<span className="text-xs font-mono text-primary-neon px-2 py-0.5 bg-primary-neon/10 rounded-md border border-primary-neon/30">Would cost {analysis?.cost?.toFixed(2) || '?'} units · Not executed</span>
						)}
					</div>
					
					{analysis && (
						<div className="flex items-center gap-4 text-xs font-mono text-on-surface-variant">
							<span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5" /> {analysis.cached ? 'Hit' : 'Miss'}</span>
							<span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5" /> Trace: <span className="text-primary-neon tracking-tight hover:underline cursor-pointer">{analysis.traceId.substring(0,8)}</span></span>
						</div>
					)}
				</div>
			</div>

			{/* Right Panel (Collapsible / Power Mode) */}
			{(mode === 'power' || analysis || explanation) && (
				<div className="w-80 flex-shrink-0 flex flex-col gap-4 overflow-y-auto pb-16">
					
					{/* Analysis Panel */}
					{analysis && (
						<div className="bg-surface/60 border border-surface-high rounded-xl p-4 shadow-sm">
							<h3 className="text-xs uppercase font-bold tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
								<Activity className="w-4 h-4 text-primary-neon" /> Analysis
							</h3>
							<div className="space-y-3 font-mono text-xs">
								<div className="flex justify-between items-center pb-2 border-b border-surface-high">
									<span className="text-on-surface-variant">Scan Type</span>
									<span className="text-primary-container font-semibold badge bg-primary-container/10 px-2 py-0.5 rounded border border-primary-container/30">Index Scan</span>
								</div>
								<div className="flex justify-between items-center pb-2 border-b border-surface-high">
									<span className="text-on-surface-variant">Execution Time</span>
									<span className="text-on-surface">{analysis.latencyMs.toFixed(2)}ms</span>
								</div>
								<div className="flex justify-between items-center">
									<span className="text-on-surface-variant">Total Cost</span>
									<span className="text-primary-neon">{analysis.cost?.toFixed(2) || 'N/A'} units</span>
								</div>
							</div>
						</div>
					)}

					{/* Complexity & Suggestions */}
					{analysis?.analysis && (
						<div className="bg-surface/60 border border-surface-high rounded-xl p-4 shadow-sm space-y-4">
							<div className="flex items-center justify-between">
								<span className="text-xs uppercase font-bold tracking-widest text-on-surface-variant">Complexity</span>
								<span className={`text-xs font-black uppercase px-2 py-0.5 rounded border ${
									analysis.analysis.join_count > 2 ? 'bg-error/10 text-error border-error/30' : 'bg-primary-neon/10 text-primary-neon border-primary-neon/30'
								}`}>
									{analysis.analysis.join_count > 2 ? 'High' : 'Low'}
								</span>
							</div>
							<div className="text-xs text-on-surface-variant space-y-1">
								<p>• Tables: {analysis.analysis.tables_accessed?.join(', ')}</p>
								<p>• Joins: {analysis.analysis.join_count}</p>
							</div>

							{analysis.slow && (
								<div className="mt-4 pt-4 border-t border-surface-high">
									<span className="text-xs uppercase font-bold tracking-widest text-error mb-2 block">Index Suggestion</span>
									<div className="relative group">
										<div className="bg-surface-high/50 font-mono text-[10px] p-2 rounded text-on-surface/80 border border-surface-high whitespace-pre-wrap overflow-hidden">
											CREATE INDEX idx_perf ON table(col);
										</div>
										<button onClick={() => copyToClipboard('CREATE INDEX idx_perf ON table(col);')} className="absolute top-1 right-1 p-1 bg-surface hover:bg-surface-high rounded border border-surface-high text-on-surface opacity-0 group-hover:opacity-100 transition-opacity">
											<Copy className="w-3 h-3" />
										</button>
									</div>
								</div>
							)}
						</div>
					)}

					{/* Query Diff Panel */}
					{originalSql && sqlQuery !== originalSql && (
						<div className="bg-error/5 border border-error/20 rounded-xl p-4 shadow-sm">
							<div className="flex justify-between items-center mb-2">
								<h3 className="text-xs uppercase font-bold tracking-widest text-error flex items-center gap-2">
									<TerminalSquare className="w-4 h-4" /> Query Diff
								</h3>
								<button onClick={() => setShowDiff(!showDiff)} className="text-[10px] font-bold uppercase hover:underline text-error">Toggle View</button>
							</div>
							{showDiff ? (
								<div className="space-y-2 mt-3">
									<div className="font-mono text-[10px] p-2 bg-surface-high/30 rounded border border-surface-high">
										<div className="text-on-surface-variant/50 uppercase tracking-widest mb-1 border-b border-surface-high pb-1">Original</div>
										<span className="text-error mb-2 block">{originalSql}</span>
										<div className="text-on-surface-variant/50 uppercase tracking-widest mb-1 mt-2 border-b border-surface-high pb-1">Executed</div>
										<span className="text-primary-neon block">{sqlQuery}</span>
									</div>
								</div>
							) : (
								<p className="text-xs text-error/80 italic">Query was manually altered from AI suggestion.</p>
							)}
						</div>
					)}

					{/* Pipeline Trace Timeline */}
					{analysis && (
						<div className="bg-surface/60 border border-surface-high rounded-xl p-4 shadow-sm">
							<h3 className="text-xs uppercase font-bold tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
								<ShieldCheck className="w-4 h-4 text-primary-container" /> Pipeline Trace
							</h3>
							<div className="relative border-l border-surface-high ml-2 space-y-4">
								{['Auth', 'Rate Limit', 'Injection Scan', analysis.cached ? 'Cache Hit' : 'Execute', 'Observe'].map((step, idx) => (
									<div key={idx} className="relative pl-4">
										<div className="absolute -left-[5px] top-1 w-2 h-2 rounded-full bg-primary-neon ring-2 ring-surface"></div>
										<div className="text-xs font-semibold text-on-surface">{step}</div>
										<div className="text-[10px] text-on-surface-variant font-mono">Pass · {Math.random().toFixed(1)}ms</div>
									</div>
								))}
							</div>
						</div>
					)}

				</div>
			)}
		</div>
	);
}
