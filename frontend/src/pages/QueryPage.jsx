import React, { useState } from "react";
import NLQueryPanel from "../components/NLQueryPanel";
import ResultsTable from "../components/ResultsTable";
import { api } from "../utils/api";
import { Copy, Play, Zap } from "lucide-react";

export default function QueryPage() {
	const [sqlQuery, setSqlQuery] = useState("SELECT * FROM users LIMIT 10;");
	const [results, setResults] = useState(null);
	const [analysis, setAnalysis] = useState(null);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState("");
	const [dryRun, setDryRun] = useState(false);
	const [explanation, setExplanation] = useState("");

	const handleSQLGenerated = (data) => {
		setSqlQuery(data.sql);
		setExplanation(data.explanation || "");
		// Auto-execute the generated SQL
		handleExecuteQuery(data.sql);
	};

	const handleExecuteQuery = async (query = sqlQuery) => {
		if (!query.trim()) return;

		setIsLoading(true);
		setError("");
		setResults(null);
		setAnalysis(null);

		try {
			const response = await api.executeQuery(query, dryRun);
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
		} catch (err) {
			setError(err.response?.data?.detail || "Query execution failed");
		} finally {
			setIsLoading(false);
		}
	};

	const handleExplainQuery = async () => {
		if (!sqlQuery.trim()) return;

		try {
			const response = await api.explainQuery(sqlQuery);
			setExplanation(response.data.explanation);
		} catch (err) {
			setError("Failed to generate explanation");
		}
	};

	const copyToClipboard = () => {
		navigator.clipboard.writeText(sqlQuery);
	};

	return (
		<div className="space-y-6">
			<div>
				<h1 className="text-4xl font-bold text-slate-900 mb-2">Query Argus</h1>
				<p className="text-slate-600">Ask in English or write SQL — Argus handles the rest</p>
			</div>

			{/* NL Query Panel */}
			<div className="card">
				<NLQueryPanel onSQLGenerated={handleSQLGenerated} onLoading={setIsLoading} />
			</div>

			{/* SQL Editor Panel */}
			<div className="card space-y-4">
				<div className="flex items-center justify-between">
					<h2 className="text-lg font-semibold text-slate-900">SQL Query</h2>
					<div className="flex gap-2">
						<button onClick={copyToClipboard} className="btn-secondary flex items-center gap-2">
							<Copy className="w-4 h-4" />
							Copy
						</button>
					</div>
				</div>

				<textarea
					value={sqlQuery}
					onChange={(e) => setSqlQuery(e.target.value)}
					placeholder="SELECT * FROM users LIMIT 10"
					className="w-full h-32 p-4 border border-slate-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
				/>

				<div className="flex items-center gap-4">
					<button onClick={() => handleExecuteQuery()} disabled={isLoading || !sqlQuery.trim()} className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
						<Play className="w-4 h-4" />
						Execute
					</button>

					<button onClick={handleExplainQuery} className="btn-secondary flex items-center gap-2">
						<Zap className="w-4 h-4" />
						Explain
					</button>

					<label className="flex items-center gap-2 cursor-pointer">
						<input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} className="w-4 h-4 rounded border-slate-300" />
						<span className="text-sm text-slate-700">Dry run (preview only)</span>
					</label>
				</div>
			</div>

			{/* Explanation */}
			{explanation && (
				<div className="card bg-blue-50 border border-blue-200">
					<h3 className="font-semibold text-slate-900 mb-2">Explanation</h3>
					<p className="text-slate-700 leading-relaxed">{explanation}</p>
				</div>
			)}

			{/* Results */}
			{results && (
				<div className="space-y-4">
					<div className="card bg-slate-50">
						<div className="grid grid-cols-2 md:grid-cols-5 gap-4">
							<div>
								<div className="text-sm text-slate-600">Status</div>
								<div className="text-2xl font-bold text-emerald-600">{analysis.slow ? "⚠️ Slow" : "✅ OK"}</div>
							</div>
							<div>
								<div className="text-sm text-slate-600">Latency</div>
								<div className="text-2xl font-bold text-slate-900">{analysis.latencyMs.toFixed(1)}ms</div>
							</div>
							<div>
								<div className="text-sm text-slate-600">Cost</div>
								<div className="text-2xl font-bold text-slate-900">{analysis.cost?.toFixed(2) || "N/A"}</div>
							</div>
							<div>
								<div className="text-sm text-slate-600">Rows</div>
								<div className="text-2xl font-bold text-slate-900">{results.rows.length}</div>
							</div>
							<div>
								<div className="text-sm text-slate-600">Source</div>
								<div className="text-lg font-bold text-slate-900">{analysis.cached ? "💾 Cache" : "🔍 DB"}</div>
							</div>
						</div>
					</div>

					<ResultsTable rows={results.rows} columns={results.columns} isLoading={isLoading} error={error} />

					{/* Analysis */}
					{analysis.analysis && (
						<div className="card space-y-4">
							<h3 className="font-semibold text-slate-900">Query Analysis</h3>
							<div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
								{analysis.analysis.scan_type && (
									<div>
										<div className="text-slate-600">Scan Type</div>
										<div className="font-medium text-slate-900">{analysis.analysis.scan_type}</div>
									</div>
								)}
								{analysis.analysis.rows_processed !== undefined && (
									<div>
										<div className="text-slate-600">Rows Processed</div>
										<div className="font-medium text-slate-900">{analysis.analysis.rows_processed}</div>
									</div>
								)}
								{analysis.analysis.execution_time_ms !== undefined && (
									<div>
										<div className="text-slate-600">Execution Time</div>
										<div className="font-medium text-slate-900">{analysis.analysis.execution_time_ms.toFixed(2)}ms</div>
									</div>
								)}
								{analysis.analysis.complexity && (
									<div>
										<div className="text-slate-600">Complexity</div>
										<div className="font-medium text-slate-900">{analysis.analysis.complexity}</div>
									</div>
								)}
							</div>

							{analysis.analysis.index_suggestions && analysis.analysis.index_suggestions.length > 0 && (
								<div className="mt-4 p-4 bg-amber-50 rounded-lg">
									<h4 className="font-semibold text-amber-900 mb-2">📊 Index Suggestions</h4>
									<ul className="space-y-2 text-sm">
										{analysis.analysis.index_suggestions.map((suggestion, idx) => (
											<li key={idx} className="text-amber-800">
												• {suggestion}
											</li>
										))}
									</ul>
								</div>
							)}
						</div>
					)}
				</div>
			)}

			{error && (
				<div className="card bg-red-50 border border-red-200">
					<div className="text-red-700 font-medium">Error</div>
					<div className="text-red-600 text-sm mt-2">{error}</div>
				</div>
			)}
		</div>
	);
}
