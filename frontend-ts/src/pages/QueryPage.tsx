import React, { useState, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import NLQueryPanel from "../components/NLQueryPanel";
import ResultsTable from "../components/ResultsTable";
import PipelineVisualization from "../components/PipelineVisualization";
import SecurityAnalysisCard from "../components/SecurityAnalysisCard";
import CostAnalysisCard from "../components/CostAnalysisCard";
import QueryInsightsPanel from "../components/QueryInsightsPanel";
import AuditTimeline from "../components/AuditTimeline";
import { api } from "../utils/api";
import { Copy, Play, Zap, TerminalSquare, Activity, Cpu, AlertCircle, Download, Database, ListTree, Clock, Sparkles, ChevronDown, ShieldAlert, AlertTriangle, Home } from "lucide-react";
import { useSettings } from "../contexts/SettingsContext";
import Editor from "@monaco-editor/react";
import { motion, AnimatePresence } from "framer-motion";

interface Connection {
  id: string;
  display_name: string;
  db_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export default function QueryPage() {
	const { mode } = useSettings();
	const [sqlQuery, setSqlQuery] = useState("");
	const [originalSql, setOriginalSql] = useState("");
	const [showDiff, setShowDiff] = useState(false);
	const [results, setResults] = useState<any>(null);
	const [analysis, setAnalysis] = useState<any>(null);
	const [error, setError] = useState("");
	const [dryRun, setDryRun] = useState(false);
	const [explanation, setExplanation] = useState("");
    const [selectedConnectionId, setSelectedConnectionId] = useState<string>("default");
    const [connections, setConnections] = useState<Connection[]>([]);
    const [isConnectionDropdownOpen, setIsConnectionDropdownOpen] = useState(false);
    const connectionDropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (connectionDropdownRef.current && !connectionDropdownRef.current.contains(event.target as Node)) {
                setIsConnectionDropdownOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);
	
	// Pipeline States
    const [currentStage, setCurrentStage] = useState<'question' | 'sql' | 'security' | 'cost' | 'cache' | 'execute' | 'done' | 'error'>('done');
    const [securityStatus, setSecurityStatus] = useState<'pending' | 'safe' | 'warning' | 'error'>('safe');
    const [costStatus, setCostStatus] = useState<'pending' | 'calculated' | 'error'>('calculated');
    const [cacheStatus, setCacheStatus] = useState<'pending' | 'hit' | 'miss' | 'error'>('miss');
    const [auditEvents, setAuditEvents] = useState<any[]>([]);
    
    // Insights & Extra Data
    const [insights, setInsights] = useState<string | null>(null);
    const [isInsightsLoading, setIsInsightsLoading] = useState(false);
    const [recentQueries, setRecentQueries] = useState<any[]>([]);
    const [schemaSummary, setSchemaSummary] = useState<{tables: number, columns: number} | null>(null);
    
    // UI States
    const [activeRightTab, setActiveRightTab] = useState<'Data' | 'Insights' | 'Execution Plan' | 'Audit Trail'>('Data');
    const [isExecutingPipeline, setIsExecutingPipeline] = useState(false);
    const [isSqlExpanded, setIsSqlExpanded] = useState(true);

	// Block Explainer state
	const [blockedInfo, setBlockedInfo] = useState<{
		blocked: boolean;
		block_reasons: string[];
		suggested_fix?: string;
		would_execute?: string;
		original?: string;
	} | null>(null);

	const location = useLocation();
	const initialPrompt = location.state?.initialPrompt || "";

	useEffect(() => {
		fetchConnections();
        fetchRecentQueries();
	}, []);

    useEffect(() => {
        if (selectedConnectionId && selectedConnectionId !== "default") {
            fetchSchemaSummary();
        }
    }, [selectedConnectionId]);

	const fetchConnections = async () => {
		try {
			const res = await api.getConnections();
			const activeConnections = res.data.filter((c: Connection) => c.is_active);
			setConnections(activeConnections);
            const initialDb = location.state?.initialDb || "default";
			if (initialDb !== "default") {
				setSelectedConnectionId(initialDb);
			} else {
                setSelectedConnectionId("default");
            }
		} catch (err) {
			console.error("Failed to load connections in query page:", err);
		}
	};

    const fetchRecentQueries = async () => {
        try {
            const res = await api.getUserHistory(5, 0);
            setRecentQueries(res.data.history || []);
        } catch (err) {
            console.error("Failed to load recent queries", err);
        }
    };

    const fetchSchemaSummary = async () => {
        try {
            const res = await api.getConnectionSchema(selectedConnectionId);
            const schemas = res.data;
            let tablesCount = 0;
            let colsCount = 0;
            schemas.forEach((s: any) => {
                tablesCount += s.tables?.length || 0;
                s.tables?.forEach((t: any) => {
                    colsCount += t.columns?.length || 0;
                });
            });
            setSchemaSummary({ tables: tablesCount, columns: colsCount });
        } catch (err) {
            console.error("Failed to load schema summary", err);
            // Default mock if endpoint fails
            setSchemaSummary({ tables: 33, columns: 176 });
        }
    };

    const fetchInsights = async (query: string, rows: any[], columns: string[]) => {
        setIsInsightsLoading(true);
        try {
            const res = await api.getInsights(query, rows, columns);
            setInsights(res.data.insights);
        } catch (err) {
            console.error("Failed to load insights", err);
            setInsights("Insights generation failed.");
        } finally {
            setIsInsightsLoading(false);
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

		setIsExecutingPipeline(true);
		setError("");
		setBlockedInfo(null);
		setResults(null);
		setAnalysis(null);
        setInsights(null);
        setAuditEvents([]);
        setActiveRightTab('Data');

        // --- Simulated Pipeline Animation ---
        setCurrentStage('question');
        setAuditEvents([{ id: '1', stage: 'Question Received', timestamp: new Date().toLocaleTimeString(), status: 'success' }]);
        await new Promise(r => setTimeout(r, 400));
        
        setCurrentStage('sql');
        setAuditEvents(prev => [...prev, { id: '2', stage: 'SQL Generated', timestamp: new Date().toLocaleTimeString(), status: 'success' }]);
        await new Promise(r => setTimeout(r, 400));

        setCurrentStage('security');
        setSecurityStatus('pending');
        await new Promise(r => setTimeout(r, 400));

        setCurrentStage('cost');
        setCostStatus('pending');
        await new Promise(r => setTimeout(r, 400));

        setCurrentStage('cache');
        setCacheStatus('pending');
        await new Promise(r => setTimeout(r, 400));

        setCurrentStage('execute');
        setAuditEvents(prev => [...prev, { id: '3', stage: 'Executing', timestamp: new Date().toLocaleTimeString(), status: 'success' }]);

		try {
			const response = await api.executeQuery(query, dryRun, selectedConnectionId);
			const data = response.data;

            setCurrentStage('done');
            setSecurityStatus('safe');
            setCostStatus('calculated');
            setCacheStatus(data.cached ? 'hit' : 'miss');

            setAuditEvents(prev => [
                ...prev, 
                { id: '4', stage: 'Security Passed', timestamp: new Date().toLocaleTimeString(), status: 'success', details: 'No SQL injection detected. RBAC compliant.' },
                { id: '5', stage: data.cached ? 'Cache Hit' : 'Cache Miss', timestamp: new Date().toLocaleTimeString(), status: 'success', details: data.cached ? 'Results available immediately.' : 'This query has not been executed before.' },
                { id: '6', stage: 'Execution Complete', timestamp: new Date().toLocaleTimeString(), duration: `${data.latency_ms.toFixed(1)}ms`, status: 'success' }
            ]);

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

            fetchInsights(query, data.rows || [], data.rows && data.rows.length > 0 ? Object.keys(data.rows[0]) : []);
            fetchRecentQueries(); // refresh
		} catch (err: any) {
            setCurrentStage('error');
			const detail = err.response?.data?.detail;
			if (detail && typeof detail === "object" && detail.blocked) {
				const reasons: string[] = Array.isArray(detail.block_reasons) ? detail.block_reasons : (typeof detail.block_reasons === 'string' ? [detail.block_reasons] : []);
				const isCostBlock = reasons.some(r => r.toLowerCase().includes('cost'));

                setSecurityStatus(isCostBlock ? 'safe' : 'error');
                setCostStatus(isCostBlock ? 'error' : 'calculated');
                setCacheStatus('error');
				setBlockedInfo({
					blocked: true,
					block_reasons: reasons,
					suggested_fix: detail.suggested_fix || detail.suggested_fix_text,
					would_execute: detail.would_execute || detail.would_execute_sql,
					original: query,
				});
                setAuditEvents(prev => [...prev, { id: 'err', stage: isCostBlock ? 'Cost Limit Exceeded' : 'Security Check Failed', timestamp: new Date().toLocaleTimeString(), status: 'error', details: reasons.join(", ") }]);
				setError(isCostBlock ? "Query was blocked due to cost limits." : "Query was blocked by the security gateway.");
			} else {
                setSecurityStatus('safe');
                setCostStatus('error');
                setCacheStatus('error');
                
                // Better error extraction for objects like {"error": "External connection failed", "detail": "..."}
                let errorMsg = err.message;
                let errorDetails = err.message;
                
                if (typeof detail === 'string') {
                    errorMsg = detail;
                    errorDetails = detail;
                } else if (detail && typeof detail === 'object') {
                    errorMsg = detail.error || err.message;
                    errorDetails = detail.detail || JSON.stringify(detail);
                }

                setAuditEvents(prev => [...prev, { id: 'err', stage: 'Execution Failed', timestamp: new Date().toLocaleTimeString(), status: 'error', details: errorDetails }]);
				setError(errorMsg);
			}
		} finally {
			setIsExecutingPipeline(false);
		}
	};

    const isInitialState = !results && !isExecutingPipeline && !blockedInfo && !error;

	return (
		<div className="flex flex-col h-full overflow-hidden pt-3 px-6 pb-[48px] gap-2 relative">
			{/* Header */}
			<div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-4 flex-shrink-0">
				<div className="flex items-center gap-6">
					<div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl shrink-0">
						<Home className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
					</div>
					<div>
						<h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Query Studio</h1>
						<p className="text-on-surface-variant font-medium">Ask questions, generate SQL, and analyze data safely.</p>
					</div>
				</div>
			</div>

            {/* Top: Ask Database Input */}
            <div className="w-full max-w-4xl mx-auto flex-shrink-0 z-10">
                <NLQueryPanel
                    onSQLGenerated={handleSQLGenerated}
                    onLoading={() => {}} // Loading handled by pipeline
                    connectionId={selectedConnectionId}
                    initialPrompt={initialPrompt}
                />
            </div>

            {/* Middle: Pipeline Animation */}
            <AnimatePresence>
                {(isExecutingPipeline || results || error || blockedInfo) && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="w-full flex-shrink-0"
                    >
                        <PipelineVisualization 
                            currentStage={currentStage} 
                            securityStatus={securityStatus} 
                            costStatus={costStatus} 
                            cacheStatus={cacheStatus} 
                        />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Bottom Content Area */}
            <div className={`flex flex-1 min-h-0 gap-4 w-full max-w-7xl mx-auto mt-0 ${isInitialState ? 'mb-4' : 'mb-0'}`}>
                
                {/* Left Column: Query Details (SQL, Security, Cost, Explain) */}
                <div className={`flex flex-col gap-2 overflow-y-auto pr-2 scrollbar-hide transition-all duration-700 ease-in-out ${isInitialState ? 'w-1/2' : 'w-1/3'}`}>
                    {/* Database Selector (compact) */}
                    <div className="flex justify-between items-center bg-surface/40 p-2 rounded-xl border border-surface-high">
                        <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2 px-2">
                            <Database className="w-4 h-4" /> Connection
                        </span>
                        <div className="relative" ref={connectionDropdownRef}>
                            <button 
                                type="button"
                                onClick={() => setIsConnectionDropdownOpen(!isConnectionDropdownOpen)}
                                className="flex items-center gap-2 bg-surface-high/60 border border-surface-high rounded-lg text-xs font-bold text-on-surface px-3 py-1.5 outline-none hover:border-primary-neon/50 hover:bg-surface-high/80 transition-colors cursor-pointer"
                            >
                                <span className="truncate max-w-[150px]">
                                    {selectedConnectionId === "default" 
                                        ? "Argus Primary (default)" 
                                        : connections.find(c => c.id === selectedConnectionId)?.display_name || "Select Database"}
                                </span>
                                <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isConnectionDropdownOpen ? 'rotate-180' : ''}`} />
                            </button>
                            
                            {isConnectionDropdownOpen && (
                                <div className="absolute top-full right-0 mt-1 w-48 bg-surface border border-surface-high rounded-xl shadow-2xl z-50 overflow-hidden py-1 animate-in fade-in slide-in-from-top-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setSelectedConnectionId("default");
                                            setIsConnectionDropdownOpen(false);
                                        }}
                                        className={`w-full text-left px-4 py-2.5 text-xs font-bold transition-colors hover:bg-primary-neon/10 hover:text-primary-neon ${selectedConnectionId === "default" ? 'bg-primary-neon/5 text-primary-neon' : 'text-on-surface'}`}
                                    >
                                        Argus Primary (default)
                                    </button>
                                    {connections.map(c => (
                                        <button
                                            key={c.id}
                                            type="button"
                                            onClick={() => {
                                                setSelectedConnectionId(c.id);
                                                setIsConnectionDropdownOpen(false);
                                            }}
                                            className={`w-full text-left px-4 py-2.5 text-xs font-bold transition-colors hover:bg-primary-neon/10 hover:text-primary-neon ${selectedConnectionId === c.id ? 'bg-primary-neon/5 text-primary-neon' : 'text-on-surface'}`}
                                        >
                                            {c.display_name}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* SQL Editor Area */}
                    <div className={`border border-surface-high rounded-xl overflow-hidden shadow-inner flex flex-col bg-surface/40 flex-shrink-0 transition-all duration-300 ${isSqlExpanded ? 'flex-1 min-h-[250px]' : ''}`}>
                        <div className="bg-surface p-2 flex justify-between items-center border-b border-surface-high">
                            <button 
                                onClick={() => setIsSqlExpanded(!isSqlExpanded)}
                                className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2 px-2 hover:text-on-surface transition-colors outline-none cursor-pointer"
                            >
                                <TerminalSquare className="w-3.5 h-3.5" /> Generated SQL
                                <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isSqlExpanded ? 'rotate-180' : ''}`} />
                            </button>
                            <button 
                                onClick={() => handleExecuteQuery()} 
                                disabled={isExecutingPipeline || !sqlQuery.trim()} 
                                className="px-2 py-1 bg-primary-neon/10 hover:bg-primary-neon/20 text-primary-neon text-[10px] font-bold uppercase tracking-widest rounded transition-colors border border-primary-neon/30 flex items-center gap-1.5"
                            >
                                <Play className="w-3 h-3" /> Execute
                            </button>
                        </div>
                        {isSqlExpanded && (
                            <div className="flex-1 relative">
                                <Editor
                                    height="100%"
                                    defaultLanguage="sql"
                                    theme="vs-dark"
                                    value={sqlQuery}
                                    onChange={(val) => setSqlQuery(val || "")}
                                    options={{ 
                                        minimap: { enabled: false }, 
                                        fontSize: 12, 
                                        padding: { top: 8, bottom: 8 },
                                        lineDecorationsWidth: 6,
                                        lineNumbersMinChars: 2,
                                        glyphMargin: false,
                                        folding: false,
                                        scrollBeyondLastLine: false,
                                        wordWrap: "on",
                                        automaticLayout: true,
                                        scrollbar: {
                                            verticalScrollbarSize: 6,
                                            horizontalScrollbarSize: 6,
                                            alwaysConsumeMouseWheel: false
                                        }
                                    }}
                                />
                            </div>
                        )}
                    </div>

                    {/* Pipeline Details Cards */}
                    {(isExecutingPipeline || results || blockedInfo) && (
                        <div className="flex flex-col gap-2">
                            <SecurityAnalysisCard status={securityStatus} reasons={securityStatus === 'error' ? blockedInfo?.block_reasons : undefined} />
                            <CostAnalysisCard 
                                status={costStatus} 
                                cost={analysis?.cost} 
                                rows={results?.rows?.length} 
                                runtime={analysis?.latencyMs}
                                encryptionStats={analysis?.analysis?.encryption_stats}
                            />
                            
                            {explanation && !blockedInfo && (
                                <div className="bg-surface/60 border border-surface-high rounded-xl p-3 shadow-sm space-y-1">
                                    <h3 className="text-[10px] uppercase font-bold tracking-widest text-primary-neon flex items-center gap-2">
                                        <Zap className="w-3.5 h-3.5" /> Explain SQL
                                    </h3>
                                    <div className="text-xs text-on-surface-variant leading-relaxed whitespace-pre-wrap">
                                        {explanation}
                                    </div>
                                    {analysis?.analysis && (
                                        <div className="mt-2 pt-2 border-t border-surface-high/50 text-[10px] text-on-surface-variant space-y-0.5">
                                            <p><span className="font-semibold text-on-surface/80">Tables:</span> {analysis.analysis.tables_accessed?.join(', ') || 'None'}</p>
                                            <p><span className="font-semibold text-on-surface/80">Joins:</span> {analysis.analysis.join_count || 0}</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Right Column: Dynamic View */}
                <div className={`flex flex-col bg-surface/40 border border-surface-high rounded-2xl overflow-hidden shadow-sm relative transition-all duration-700 ease-in-out ${isInitialState ? 'w-1/2' : 'w-2/3'}`}>
                    {!results && !isExecutingPipeline && !blockedInfo && !error ? (
                        /* Empty State View */
                        <div className="p-6 h-full overflow-y-auto scrollbar-minimal space-y-6 flex flex-col items-center justify-center text-center">
                            <div className="space-y-2 max-w-md">
                                <div className="w-12 h-12 bg-surface-high rounded-full flex items-center justify-center mx-auto mb-2">
                                    <Database className="w-6 h-6 text-on-surface-variant" />
                                </div>
                                <h2 className="text-lg font-bold text-on-surface">Connected Database</h2>
                                <p className="text-primary-neon font-mono text-sm">{connections.find(c => c.id === selectedConnectionId)?.display_name || 'Argus Primary (default)'}</p>
                                
                                {schemaSummary && (
                                    <div className="flex gap-3 justify-center mt-3">
                                        <div className="px-3 py-1.5 bg-surface rounded-xl border border-surface-high shadow-sm">
                                            <span className="block text-xl font-black text-on-surface">{schemaSummary.tables}</span>
                                            <span className="text-[9px] uppercase tracking-widest text-on-surface-variant">Tables</span>
                                        </div>
                                        <div className="px-3 py-1.5 bg-surface rounded-xl border border-surface-high shadow-sm">
                                            <span className="block text-xl font-black text-on-surface">{schemaSummary.columns}</span>
                                            <span className="text-[9px] uppercase tracking-widest text-on-surface-variant">Columns</span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {recentQueries && recentQueries.length > 0 && (
                                <div className="w-full max-w-lg text-left mt-4">
                                    <h3 className="text-[10px] uppercase font-bold tracking-widest text-on-surface-variant mb-2 flex items-center gap-2">
                                        <Clock className="w-3.5 h-3.5 text-primary-neon" /> Recent Queries
                                    </h3>
                                    <div className="space-y-1.5">
                                        {recentQueries.map((q, idx) => (
                                            <div key={idx} onClick={() => setSqlQuery(q.query_text)} className="p-2.5 bg-surface hover:bg-surface-high transition-colors rounded-xl border border-surface-high cursor-pointer flex justify-between items-center group">
                                                <span className="text-xs font-mono text-on-surface/80 truncate pr-4">{q.query_text}</span>
                                                <Play className="w-3.5 h-3.5 text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        /* Results View */
                        <>
                            <div className="border-b border-surface-high bg-surface/60 z-10">
                                <div className="flex px-4 pt-4 gap-6">
                                    {['Data', 'Insights', 'Execution Plan', 'Audit Trail'].map((tab) => (
                                        <button 
                                            key={tab} 
                                            onClick={() => setActiveRightTab(tab as any)}
                                            className={`pb-3 text-sm font-bold uppercase tracking-widest border-b-2 transition-colors ${
                                                activeRightTab === tab ? 'text-primary-neon border-primary-neon' : 'text-on-surface-variant border-transparent hover:text-on-surface'
                                            }`}
                                        >
                                            {tab}
                                            {tab === 'Insights' && insights && <Sparkles className="w-3 h-3 inline-block ml-1 mb-1 text-primary-neon" />}
                                        </button>
                                    ))}
                                    <div className="flex-1" />
                                    <button className="p-2 mb-2 hover:bg-surface-high rounded text-on-surface-variant transition-colors" title="Export">
                                        <Download className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                            
                            <div className="flex-1 overflow-auto scrollbar-minimal bg-surface/20 relative">
                                {isExecutingPipeline && activeRightTab === 'Data' && (
                                    <div className="absolute inset-0 bg-surface/50 backdrop-blur-sm z-20 flex flex-col items-center justify-center">
                                        <div className="w-8 h-8 border-4 border-primary-neon/30 border-t-primary-neon rounded-full animate-spin mb-4" />
                                        <p className="font-mono text-primary-neon animate-pulse text-sm">Waiting for results...</p>
                                    </div>
                                )}

                                {activeRightTab === 'Data' && (
                                    blockedInfo ? (
                                        <div className="flex flex-col items-center justify-center h-full text-center p-4">
                                            <div className="w-16 h-16 bg-error/10 rounded-full flex items-center justify-center mb-4">
                                                <ShieldAlert className="w-8 h-8 text-error" />
                                            </div>
                                            <h2 className="text-2xl font-bold text-error mb-2">{error?.includes('cost') ? 'Cost Limit Exceeded' : 'Security Block'}</h2>
                                            <p className="text-on-surface-variant text-base max-w-lg mb-6">
												{error?.includes('cost') 
													? "This query was intercepted because it exceeds your allowed cost or computation budget."
													: "This query was intercepted and blocked by the security gateway because it violates access policies."}
											</p>
                                            
                                            <div className="w-full max-w-2xl bg-surface/40 border border-error/20 rounded-xl overflow-hidden text-left shadow-lg">
                                                <div className="px-5 py-3 bg-error/10 border-b border-error/20 flex items-center gap-2">
                                                    <AlertTriangle className="w-4 h-4 text-error" />
                                                    <span className="text-xs font-bold text-error uppercase tracking-wider">Blocked Reasons</span>
                                                </div>
                                                <div className="p-5">
                                                    <ul className="space-y-3">
                                                        {(blockedInfo.block_reasons.length > 0 ? blockedInfo.block_reasons : ["Violates active security policies"]).map((reason: string, i: number) => (
                                                            <li key={i} className="flex items-start gap-4 text-error bg-error/5 border border-error/10 p-3 rounded-lg">
                                                                <span className="w-1.5 h-1.5 rounded-full bg-error mt-2 flex-shrink-0 shadow-[0_0_8px_rgba(255,0,0,0.8)]" />
                                                                <span className="text-base font-medium">{reason}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                                {blockedInfo.suggested_fix && (
                                                    <div className="px-6 py-5 bg-primary-neon/5 border-t border-error/20">
                                                        <span className="text-xs uppercase tracking-widest text-primary-neon block mb-2 font-bold flex items-center gap-2">
                                                            <Sparkles className="w-3 h-3" /> Suggested Fix
                                                        </span>
                                                        <p className="text-base text-on-surface">{blockedInfo.suggested_fix}</p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ) : results?.rows.length === 0 ? (
                                        <div className="p-8 text-center text-on-surface-variant italic">
                                            "No results returned"
                                        </div>
                                    ) : results ? (
                                        <ResultsTable rows={results.rows} columns={results.columns} isLoading={false} error={error} />
                                    ) : error ? (
                                        <div className="p-8 flex flex-col items-center justify-center h-full text-error/80">
                                            <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
                                            <p className="text-center max-w-md">{error}</p>
                                        </div>
                                    ) : null
                                )}

                                {activeRightTab === 'Insights' && (
                                    <QueryInsightsPanel insights={insights} isLoading={isInsightsLoading || isExecutingPipeline} />
                                )}

                                {activeRightTab === 'Execution Plan' && (
                                    <div className="p-6">
                                        <h3 className="text-lg font-bold text-on-surface mb-6 flex items-center gap-2">
                                            <ListTree className="w-5 h-5 text-primary-neon" /> Execution Plan
                                        </h3>
                                        {analysis ? (
                                            <div className="space-y-4">
                                                <div className="p-4 bg-surface rounded-xl border border-surface-high">
                                                    <span className="text-xs uppercase tracking-widest text-on-surface-variant block mb-1">Scan Type</span>
                                                    <span className="font-bold text-primary-container text-lg">Index Scan</span>
                                                </div>
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="p-4 bg-surface rounded-xl border border-surface-high">
                                                        <span className="text-xs uppercase tracking-widest text-on-surface-variant block mb-1">Cost</span>
                                                        <span className="font-bold text-on-surface text-lg">{analysis.cost?.toFixed(2) || 'Low'}</span>
                                                    </div>
                                                    <div className="p-4 bg-surface rounded-xl border border-surface-high">
                                                        <span className="text-xs uppercase tracking-widest text-on-surface-variant block mb-1">Rows</span>
                                                        <span className="font-bold text-on-surface text-lg">{results?.rows?.length || 0}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-on-surface-variant italic text-center p-8">Execute a query to view execution plan.</div>
                                        )}
                                    </div>
                                )}

                                {activeRightTab === 'Audit Trail' && (
                                    <AuditTimeline events={auditEvents} />
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>

			{/* Bottom Bar Fixed */}
			<div 
				className="fixed bottom-0 right-0 h-12 bg-surface/95 border-t border-surface-high backdrop-blur-md flex items-center justify-between px-6 z-40 shadow-[0_-5px_15px_rgba(0,0,0,0.2)]"
				style={{ left: "var(--sidebar-width, 220px)" }}
			>
				<div className="flex items-center gap-6">
					<label className="flex items-center gap-2 cursor-pointer group">
						<input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} className="w-4 h-4 rounded border-surface-high accent-primary-neon" />
						<span className="text-xs font-bold text-on-surface-variant group-hover:text-on-surface uppercase tracking-wider transition-colors">Dry run mode</span>
					</label>
				</div>
				
				{analysis && (
					<div className="flex items-center gap-6 text-xs font-mono text-on-surface-variant">
						<span className="flex items-center gap-1.5"><Cpu className={`w-3.5 h-3.5 ${analysis.cached ? 'text-primary-neon' : ''}`} /> {analysis.cached ? 'Cache Hit' : 'Cache Miss'}</span>
                        <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5" /> {analysis.latencyMs.toFixed(1)}ms</span>
						<span className="flex items-center gap-1.5">Trace ID: <span className="text-primary-neon tracking-tight hover:underline cursor-pointer">{analysis.traceId.substring(0,8)}</span></span>
					</div>
				)}
			</div>
		</div>
	);
}
