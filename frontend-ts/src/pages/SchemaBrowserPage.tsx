import { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ReactFlow, Background, Controls, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { api } from "../utils/api";
import { Database, Table as TableIcon, Columns, Key as KeyIcon, Search, RefreshCw, AlertCircle, Sparkles, Send, Loader2, Bot, User, Link as LinkIcon, Network, Play, Info, ChevronDown, Lightbulb, X, BrainCircuit, Lock, Unlock, Shield } from "lucide-react";

interface Connection {
  id: string;
  display_name: string;
  db_type: string;
  is_active: boolean;
}

interface ColumnMetadata {
  name: string;
  type: string;
  pk: boolean;
  nullable: boolean;
  fk?: string | null;
  is_encrypted?: boolean;
  config_id?: number;
}

interface TableMetadata {
  name: string;
  columns: ColumnMetadata[];
  description?: string;
  rows?: number;
  ai_summary?: string;
  suggested_queries?: { title: string; sql: string }[];
  relationships?: { target: string; type: "1:1" | "1:N" | "N:1" | "N:M"; description: string; inferred?: boolean; confidence?: number }[];
}

interface SchemaStats {
  total_tables: number;
  total_columns: number;
  total_relationships: number;
}

interface SchemaMetadata {
  database_schema: string;
  tables: TableMetadata[];
  stats?: SchemaStats;
}

export default function SchemaBrowserPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { initialPrompt, initialDb } = location.state || {};

  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<string>(initialDb || "default");
  
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTable, setActiveTable] = useState("users");
  const [highlightedColumn, setHighlightedColumn] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [schemaError, setSchemaError] = useState("");
  const [schemas, setSchemas] = useState<SchemaMetadata[]>([]);
  const [isChatDrawerOpen, setIsChatDrawerOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  const [intelligenceReport, setIntelligenceReport] = useState<any>(null);
  const [isIntelligenceLoading, setIsIntelligenceLoading] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [paletteSearch, setPaletteSearch] = useState("");
  const [joinTarget, setJoinTarget] = useState("");
  const [joinPath, setJoinPath] = useState<string[] | null>(null);
  const [modalState, setModalState] = useState<{ isOpen: boolean; title: string; message: string; type: 'info' | 'success' | 'error' | 'loading' }>({ isOpen: false, title: '', message: '', type: 'info' });

  useEffect(() => {
    // BFS Join Path Explorer
    if (!joinTarget || !activeTable || schemas.length === 0) {
      setJoinPath(null);
      return;
    }

    const adjacencyList: Record<string, string[]> = {};
    schemas.forEach(s => {
      s.tables.forEach(t => {
        if (!adjacencyList[t.name]) adjacencyList[t.name] = [];
        t.relationships?.forEach(r => {
          if (!adjacencyList[r.target]) adjacencyList[r.target] = [];
          adjacencyList[t.name].push(r.target);
          adjacencyList[r.target].push(t.name); // undirected graph for joins
        });
      });
    });

    // BFS
    const queue: [string, string[]][] = [[activeTable, [activeTable]]];
    const visited = new Set<string>([activeTable]);

    while (queue.length > 0) {
      const [current, path] = queue.shift()!;
      if (current === joinTarget) {
        setJoinPath(path);
        return;
      }
      
      const neighbors = adjacencyList[current] || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push([neighbor, [...path, neighbor]]);
        }
      }
    }

    setJoinPath([]); // Not found
  }, [joinTarget, activeTable, schemas]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as globalThis.Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Chat State
  const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'ai', content: string }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, isChatLoading]);

  const hasExecutedInitial = useRef(false);

  useEffect(() => {
    if (initialPrompt && !hasExecutedInitial.current && activeTable) {
      hasExecutedInitial.current = true;
      executeChat(initialPrompt);
    }
  }, [initialPrompt, activeTable]);

  const executeChat = async (promptText: string) => {
    if (!promptText.trim() || isChatLoading) return;
    
    const newHistory = [...chatHistory, { role: 'user' as const, content: promptText }];
    setChatHistory(newHistory);
    setIsChatLoading(true);

    try {
      const response = await api.schemaChat(promptText, selectedConnectionId, activeTable, chatHistory);
      setChatHistory([...newHistory, { role: 'ai', content: response.data.answer }]);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || "Error connecting to AI assistant.";
      setChatHistory([...newHistory, { role: 'ai', content: `❌ ${errorMessage}` }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleSendChat = async () => {
    if (!chatInput.trim() || isChatLoading) return;
    const text = chatInput;
    setChatInput("");
    await executeChat(text);
  };

  // No mock database schema. We only show real schemas from connections.

  useEffect(() => {
    loadConnections();
  }, []);

  useEffect(() => {
    if (selectedConnectionId && selectedConnectionId !== "default") {
      fetchSchema(selectedConnectionId);
    } else {
      setSchemas([]);
      setActiveTable('');
    }
  }, [selectedConnectionId]);

  const loadConnections = async () => {
    try {
      const res = await api.getConnections();
      const activeConnections = res.data.filter((c: Connection) => c.is_active);
      setConnections(activeConnections);
      if (activeConnections.length > 0) {
        setSelectedConnectionId(activeConnections[0].id);
      }
    } catch (err) {
      console.error("Failed to load connections in schema page:", err);
    }
  };

  const fetchSchema = async (connectionId: string) => {
    setIsLoading(true);
    setSchemaError("");
    setSchemas([]);
    try {
      const res = await api.getConnectionSchema(connectionId);
      
      // Enrich data with AI insights and stats for the UI
      const enrichedData = res.data.map((schema: any) => {
        let totalCols = 0;
        let totalRels = 0;
        
        const enrichedTables = schema.tables.map((table: any) => {
          totalCols += table.columns.length;
          
          const relationships = table.relationships || [];
          if (relationships.length === 0) {
            table.columns.forEach((col: any) => {
              if (col.fk) {
                const targetTable = col.fk.split('.')[0];
                relationships.push({
                  target: targetTable,
                  type: "N:1",
                  description: `Links to ${targetTable} via ${col.name}`,
                  inferred: col.fk_inferred,
                  confidence: col.fk_confidence
                });
              }
            });
          }
          totalRels += relationships.length;

          return {
            ...table,
            ai_summary: table.ai_summary || `Stores information about ${table.name}. This table contains ${table.columns.length} columns and acts as a core entity in the database topology.`,
            suggested_queries: table.suggested_queries || [
              { title: `View recent ${table.name}`, sql: `SELECT * FROM ${table.name} LIMIT 10;` },
              { title: `Count total ${table.name}`, sql: `SELECT COUNT(*) FROM ${table.name};` }
            ],
            relationships: relationships
          };
        });

        return {
          ...schema,
          stats: schema.stats || {
            total_tables: schema.tables.length,
            total_columns: totalCols,
            total_relationships: totalRels
          },
          tables: enrichedTables
        };
      });

      setSchemas(enrichedData);

      // Fetch intelligence
      setIsIntelligenceLoading(true);
      try {
        const intelligenceRes = await api.getSchemaIntelligence(connectionId, JSON.stringify(enrichedData));
        setIntelligenceReport(intelligenceRes.data);
      } catch (err) {
        console.error("Failed to load schema intelligence:", err);
      } finally {
        setIsIntelligenceLoading(false);
      }

      if (enrichedData.length > 0 && enrichedData[0].tables.length > 0) {
        setActiveTable(enrichedData[0].tables[0].name);
      } else {
        setActiveTable("");
      }
    } catch (err: any) {
      setSchemaError(err.response?.data?.detail || "Could not load schema — check connection status");
    } finally {
      setIsLoading(false);
    }
  };

  // Find active table object across schemas
  let activeTableObj: TableMetadata | undefined;
  for (const s of schemas) {
    const found = s.tables.find(t => t.name === activeTable);
    if (found) {
      activeTableObj = found;
      break;
    }
  }

  // React Flow logic
  const getFlowData = () => {
    if (!activeTableObj || !activeTableObj.relationships || activeTableObj.relationships.length === 0) {
      return { nodes: [], edges: [] };
    }
    
    const nodes: Node[] = [
      {
        id: 'center',
        position: { x: 150, y: 150 },
        data: { label: <div className="font-mono font-bold text-sm tracking-wider">{activeTableObj.name}</div> },
        style: { background: 'rgba(0,255,157,0.1)', border: '1px solid #00FF9D', color: '#00FF9D', borderRadius: '8px', padding: '12px', minWidth: '120px', textAlign: 'center' as const, boxShadow: '0 0 15px rgba(0,255,157,0.2)' }
      }
    ];
    
    const edges: Edge[] = [];
    
    activeTableObj.relationships.forEach((rel, idx) => {
      const yOffset = (idx - (activeTableObj!.relationships!.length - 1) / 2) * 80;
      const xOffset = rel.type.includes('N:1') || rel.type.includes('1:1') ? -200 : 200;
      
      nodes.push({
        id: `rel-${idx}`,
        position: { x: 150 + xOffset, y: 150 + yOffset },
        data: { label: <div className="font-mono text-xs">{rel.target}</div> },
        style: { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#aaa', borderRadius: '8px', padding: '8px', minWidth: '100px', textAlign: 'center' as const }
      });
      
      edges.push({
        id: `edge-${idx}`,
        source: xOffset > 0 ? 'center' : `rel-${idx}`,
        target: xOffset > 0 ? `rel-${idx}` : 'center',
        label: rel.type + (rel.inferred ? ` (${Math.round((rel.confidence || 0) * 100)}%)` : ''),
        style: { 
          stroke: rel.inferred ? '#FFD700' : '#00FF9D', 
          opacity: 0.5, 
          strokeDasharray: rel.inferred ? '5,5' : 'none' 
        },
        labelStyle: { fill: rel.inferred ? '#FFD700' : '#00FF9D', fontSize: 10, fontWeight: 700 },
        labelBgStyle: { fill: '#1E252D', fillOpacity: 1, stroke: rel.inferred ? '#FFD700' : '#00FF9D', strokeOpacity: 0.2, rx: 4, ry: 4 },
        labelBgPadding: [6, 4],
        animated: true,
      });
    });
    
    return { nodes, edges };
  };

  const { nodes: flowNodes, edges: flowEdges } = getFlowData();

  return (
    <div className="h-full flex flex-col space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
        <div className="flex items-center gap-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
            <Database className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
          </div>
          <div>
            <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Schema Browser</h1>
            <p className="text-on-surface-variant font-medium">Database index mapping and topological view</p>
          </div>
        </div>

        {/* Database Connection Selector */}
        <div className="flex flex-col space-y-2">
          <label className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant">Active Database</label>
          <div className="relative" ref={dropdownRef}>
            <button 
              type="button"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center justify-between gap-2 bg-surface/60 border border-surface-high rounded-xl text-xs font-bold text-on-surface px-4 py-2.5 outline-none focus:border-primary-neon/50 hover:bg-surface-high/30 transition-colors cursor-pointer min-w-[200px]"
            >
              <span className="truncate max-w-[150px]">
                {selectedConnectionId === 'default' 
                  ? 'Argus Primary (default)' 
                  : connections.find(c => c.id === selectedConnectionId)?.display_name || 'Select Database'}
              </span>
              <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>
            
            {isDropdownOpen && (
              <div className="absolute top-full right-0 mt-2 w-full min-w-[200px] bg-surface border border-surface-high rounded-xl shadow-2xl z-50 overflow-hidden py-1 animate-in fade-in slide-in-from-top-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedConnectionId('default');
                    setIsDropdownOpen(false);
                  }}
                  className={`w-full text-left px-4 py-2.5 text-xs font-bold transition-colors hover:bg-primary-neon/10 hover:text-primary-neon ${selectedConnectionId === 'default' ? 'bg-primary-neon/5 text-primary-neon' : 'text-on-surface'}`}
                >
                  Argus Primary (default)
                </button>
                {connections.map(c => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => {
                      setSelectedConnectionId(c.id);
                      setIsDropdownOpen(false);
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
      </div>

      {schemaError && (
        <div className="p-4 bg-error/10 border border-error/30 text-error rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">{schemaError}</span>
        </div>
      )}

      <div className="flex gap-6 flex-1 min-h-[500px]">
        {/* Left Tree Panel */}
        <div className="w-[300px] xl:w-[350px] flex-shrink-0 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl flex flex-col overflow-hidden ring-1 ring-white/5 relative z-10">
          {schemas.length > 0 && schemas[0].stats && (
            <div className="p-4 border-b border-surface-high bg-surface-high/10 flex justify-between items-center">
               <div>
                 <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">Tables</div>
                 <div className="text-xl font-mono text-primary-neon">{schemas[0].stats.total_tables}</div>
               </div>
               <div>
                 <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">Columns</div>
                 <div className="text-xl font-mono text-primary-neon">{schemas[0].stats.total_columns}</div>
               </div>
               <div>
                 <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">Relations</div>
                 <div className="text-xl font-mono text-primary-neon">{schemas[0].stats.total_relationships}</div>
               </div>
            </div>
          )}
          <div className="p-4 border-b border-surface-high relative bg-surface-high/20 flex flex-col gap-3">
            <div className="flex gap-2">
              <button
                onClick={() => fetchSchema(selectedConnectionId)}
                disabled={isLoading}
                className="flex-shrink-0 flex items-center justify-center bg-surface border border-surface-high w-10 h-10 rounded-xl text-on-surface hover:border-primary-neon/50 hover:text-primary-neon transition-colors disabled:opacity-50"
                title="Refresh Schema"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-primary-neon' : ''}`} />
              </button>
              <button
                onClick={() => setIsCommandPaletteOpen(true)}
                className="flex-1 flex items-center justify-between bg-surface border border-surface-high px-4 py-2 rounded-xl text-sm outline-none hover:border-primary-neon/50 text-on-surface transition-colors cursor-text group"
              >
                <div className="flex items-center gap-2">
                  <Search className="w-4 h-4 text-on-surface-variant group-hover:text-primary-neon transition-colors" />
                  <span className="text-on-surface-variant group-hover:text-on-surface transition-colors">Search tables...</span>
                </div>
              </button>
            </div>
            
            <button
              onClick={async () => {
                if (!selectedConnectionId || selectedConnectionId === "default") return;
                try {
                  setModalState({ isOpen: true, title: "Scanning Database", message: "Scanning database for sensitive PII... This may take a moment.", type: 'loading' });
                  const res = await api.scanConnection(selectedConnectionId, false, true);
                  setModalState({ isOpen: true, title: "Scan Complete", message: `Detected ${res.data.candidates.length} sensitive columns. ${res.data.applied_count} columns auto-registered (please enable encryption on them below).`, type: 'success' });
                  fetchSchema(selectedConnectionId);
                } catch(e) {
                  console.error(e);
                  setModalState({ isOpen: true, title: "Scan Failed", message: "Scan failed. Please check the network or server logs.", type: 'error' });
                }
              }}
              className="w-full flex items-center justify-center gap-2 bg-primary-neon/10 border border-primary-neon/30 text-primary-neon px-4 py-2 rounded-xl text-sm font-bold hover:bg-primary-neon/20 transition-colors shadow-sm shadow-primary-neon/5"
            >
              <Shield className="w-4 h-4" /> Scan for PII
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 pt-8 space-y-4">
            {isLoading ? (
              <div className="flex flex-col gap-3 py-6 justify-center items-center text-on-surface-variant text-xs">
                <RefreshCw className="w-6 h-6 animate-spin text-primary-neon" />
                <span>Fetching catalog metadata...</span>
              </div>
            ) : schemas.length === 0 && !schemaError ? (
              <div className="text-center py-12 text-on-surface-variant italic text-xs">
                No tables or schemas found in database.
              </div>
            ) : (
              schemas.map(schema => {
                const filteredTables = schema.tables.filter(t => t.name.toLowerCase().includes(searchQuery.toLowerCase()));
                if (filteredTables.length === 0) return null;

                return (
                  <div key={schema.database_schema} className="space-y-2">
                    <div className="flex items-center gap-2 text-on-surface-variant font-bold uppercase tracking-wider text-xs mb-2 pl-1">
                      <Database className="w-3.5 h-3.5" /> Schema: {schema.database_schema}
                    </div>
                    {filteredTables.map(table => (
                      <button 
                        key={table.name}
                        onClick={() => { setActiveTable(table.name); setHighlightedColumn(''); }}
                        className={`w-full flex items-center justify-between p-3 rounded-xl transition-all ${activeTable === table.name ? 'bg-primary-neon/10 border border-primary-neon/30 text-primary-neon shadow-[inset_0_0_10px_rgba(0,255,157,0.05)]' : 'hover:bg-surface-high/50 border border-transparent text-on-surface/80 hover:text-on-surface'}`}
                      >
                        <span className="flex items-center gap-2.5 font-mono text-sm">
                          <TableIcon className="w-4 h-4" /> {table.name}
                        </span>
                        <div className="flex items-center gap-2">
                          {table.relationships && table.relationships.length > 0 && <Network className="w-3.5 h-3.5 text-blue-400 opacity-60" />}
                          {table.columns.some(c => c.config_id && !c.is_encrypted) && <span title="Contains unencrypted sensitive PII"><AlertCircle className="w-3.5 h-3.5 text-orange-500 animate-pulse" /></span>}
                          <span className="text-xs text-on-surface-variant font-mono bg-surface-high/50 px-1.5 py-0.5 rounded" title="Columns">{table.columns.length}</span>
                          {activeTable === table.name && <div className="w-1.5 h-1.5 bg-primary-neon rounded-full shadow-[0_0_5px_#00FF9D]"></div>}
                        </div>
                      </button>
                    ))}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Center Detail Panel */}
        <div className="flex-1 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl flex flex-col ring-1 ring-white/5 overflow-hidden relative z-10 min-w-0">
          {isLoading ? (
            <div className="flex-1 flex flex-col space-y-4 p-8 animate-pulse">
              <div className="h-8 bg-surface-high rounded w-1/4"></div>
              <div className="h-4 bg-surface-high rounded w-3/4"></div>
              <div className="h-40 bg-surface-high rounded mt-8"></div>
            </div>
          ) : activeTableObj ? (
            <div className="flex flex-col h-full animate-in fade-in duration-300">
              <div className="p-8 pb-6 border-b border-surface-high bg-gradient-to-b from-surface-high/10 to-transparent">
                <div className="flex items-start gap-5">
                  <div className="w-14 h-14 rounded-2xl bg-primary-neon/10 border border-primary-neon/30 flex items-center justify-center flex-shrink-0 shadow-[0_0_20px_rgba(0,255,157,0.1)]">
                    <Sparkles className="w-7 h-7 text-primary-neon" />
                  </div>
                  <div className="flex-1 pt-1">
                    <div className="flex items-center justify-between mb-2">
                      <h2 className="text-2xl font-bold font-mono text-on-surface">{activeTableObj.name}</h2>
                      {activeTableObj.rows !== undefined && (
                        <div className="bg-surface-high/40 border border-surface-high rounded-lg px-3 py-1 font-mono text-xs text-primary-neon">
                          ~{activeTableObj.rows.toLocaleString()} rows
                        </div>
                      )}
                    </div>
                    <p className="text-on-surface-variant/80 text-sm font-light leading-relaxed">
                      {activeTableObj.ai_summary}
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-8 flex-1 overflow-y-auto space-y-8 bg-surface/30 relative">
                
                {/* Big Relationship Graph */}
                <div className={`w-full bg-surface-high/10 border border-surface-high rounded-xl overflow-hidden relative group shadow-inner ring-1 ring-white/5 transition-all duration-300 ${flowNodes.length > 0 ? 'h-[300px]' : 'h-[120px]'}`}>
                  <div className="absolute top-4 left-4 z-10 flex items-center gap-2 pointer-events-none">
                    <div className="bg-surface/80 backdrop-blur border border-surface-high rounded-lg px-3 py-1.5 flex items-center gap-2 shadow-lg">
                      <Network className="w-4 h-4 text-primary-neon" />
                      <span className="text-[10px] font-bold text-on-surface uppercase tracking-wider">Relationships Graph</span>
                    </div>
                  </div>
                  {flowNodes.length > 0 ? (
                    <ReactFlow 
                      nodes={flowNodes} 
                      edges={flowEdges} 
                      fitView 
                      className="bg-transparent w-full h-full"
                      style={{ width: '100%', height: '100%' }}
                      proOptions={{ hideAttribution: true }}
                    >
                      <Background color="rgba(255,255,255,0.05)" gap={16} />
                      <Controls className="!bg-surface border-none opacity-0 group-hover:opacity-100 transition-opacity [&>button]:!bg-surface-high [&>button]:!border-surface [&>button]:!fill-on-surface [&>button:hover]:!bg-primary-neon [&>button:hover]:!fill-surface shadow-lg rounded-lg overflow-hidden" />
                    </ReactFlow>
                  ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-on-surface-variant opacity-60 bg-surface/20">
                      <Info className="w-8 h-8 mb-2" />
                      <span className="text-xs font-medium">No relationships detected for this table.</span>
                    </div>
                  )}
                </div>

                {/* Attributes Grid (Collapsible) */}
                <details open id="attributes-details" className="bg-surface-high/5 border border-surface-high/50 rounded-xl group transition-all open:bg-surface-high/10">
                  <summary className="p-4 cursor-pointer flex items-center justify-between outline-none">
                    <h4 className="text-[10px] uppercase font-bold tracking-wider text-on-surface flex items-center gap-2">
                      <Columns className="w-3.5 h-3.5 text-on-surface-variant" /> Data Attributes ({activeTableObj.columns.length})
                    </h4>
                    <div className="text-xs text-primary-neon font-bold group-open:hidden hover:underline">Show Columns</div>
                    <div className="text-xs text-on-surface-variant font-bold hidden group-open:block hover:text-on-surface">Hide Columns</div>
                  </summary>
                  <div className="p-4 pt-0 border-t border-surface-high/50 mt-2">
                    <div className="grid grid-cols-2 xl:grid-cols-3 gap-3 mt-4">
                      {activeTableObj.columns.map(col => {
                        const isSensitive = col.config_id && !col.is_encrypted;
                        return (
                        <div id={`col-${col.name}`} key={col.name} className={`bg-surface border ${highlightedColumn === col.name ? 'border-primary-neon shadow-[0_0_15px_rgba(0,255,157,0.2)]' : isSensitive ? 'border-orange-500/50 shadow-[0_0_10px_rgba(249,115,22,0.15)] bg-orange-500/5' : 'border-surface-high/50'} rounded-xl p-3.5 hover:border-primary-neon/20 transition-all relative overflow-hidden group/col`}>
                          {col.pk && <div className="absolute top-0 left-0 w-1 h-full bg-primary-neon transition-colors"></div>}
                          {col.fk && !col.pk && <div className="absolute top-0 left-0 w-1 h-full bg-blue-400 transition-colors"></div>}
                          {!col.pk && !col.fk && <div className={`absolute top-0 left-0 w-1 h-full transition-colors ${isSensitive ? 'bg-orange-500' : 'bg-surface-high group-hover/col:bg-primary-neon/50'}`}></div>}
                          
                          <div className="flex items-center gap-2 mb-2 pl-2 min-w-0">
                            <span className="font-mono text-sm font-bold text-on-surface truncate flex-1" title={col.name}>
                              {col.name}
                            </span>
                            {col.pk && <span title="Primary Key" className="flex-shrink-0"><KeyIcon className="w-3 h-3 text-primary-neon" /></span>}
                            {col.fk && <span title="Foreign Key" className="flex-shrink-0"><LinkIcon className="w-3 h-3 text-blue-400" /></span>}
                            {isSensitive && <span title="Sensitive PII Detected" className="bg-orange-500/20 text-orange-500 text-[9px] px-1.5 py-0.5 rounded-full uppercase tracking-wider font-sans flex-shrink-0">PII</span>}
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                const newSchemas = [...schemas];
                                const currentSchema = newSchemas.find(s => s.tables.some(t => t.name === activeTable));
                                if (!currentSchema) return;
                                const table = currentSchema.tables.find(t => t.name === activeTable);
                                if (!table) return;
                                const c = table.columns.find(c => c.name === col.name);
                                if (!c) return;

                                try {
                                  if (c.is_encrypted && c.config_id) {
                                    // Delete rule
                                    await api.deleteColumnEncryption(selectedConnectionId, c.config_id);
                                    c.is_encrypted = false;
                                    c.config_id = undefined;
                                  } else {
                                    if (c.config_id) {
                                      // Exists but unencrypted (e.g. from PII scan), delete it first to avoid 409
                                      await api.deleteColumnEncryption(selectedConnectionId, c.config_id);
                                    }
                                    // Add rule
                                    const res = await api.addColumnEncryption(selectedConnectionId, {
                                      schema_name: currentSchema.database_schema,
                                      table_name: table.name,
                                      column_name: col.name,
                                      classification_method: 0,
                                      is_encrypted: true
                                    });
                                    c.is_encrypted = true;
                                    c.config_id = res.data.id;
                                  }
                                  setSchemas(newSchemas);
                                } catch (err) {
                                  console.error("Failed to toggle encryption", err);
                                  setModalState({ isOpen: true, title: "Encryption Error", message: "Failed to toggle encryption. It might already exist or the network failed.", type: 'error' });
                                }
                              }}
                              className={`ml-auto mr-2 p-1 rounded-md transition-colors ${col.is_encrypted ? 'text-primary-neon bg-primary-neon/10 hover:bg-primary-neon/20' : isSensitive ? 'text-orange-500 bg-orange-500/10 hover:bg-orange-500/20 ring-1 ring-orange-500/50' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-high'}`}
                              title={col.is_encrypted ? "Column is encrypted" : isSensitive ? "Click to enable encryption for sensitive PII" : "Click to encrypt column"}
                            >
                              {col.is_encrypted ? <Lock className="w-3.5 h-3.5" /> : <Unlock className={`w-3.5 h-3.5 ${isSensitive ? 'animate-bounce' : ''}`} />}
                            </button>
                          </div>
                          <div className="flex justify-between items-center pl-2 gap-2 min-w-0">
                            <span className="font-mono text-[10px] text-primary-container truncate flex-1" title={col.type}>{col.type}</span>
                            {col.nullable ? 
                              <span className="text-[9px] text-on-surface-variant uppercase tracking-wider font-bold flex-shrink-0">Optional</span> : 
                              <span className="text-[9px] text-error/80 uppercase tracking-wider font-bold flex-shrink-0">Required</span>
                            }
                          </div>
                        </div>
                        );
                      })}
                    </div>
                  </div>
                </details>

                {/* AI Join Recommendations */}
                {activeTableObj.relationships && activeTableObj.relationships.length > 0 && (
                  <div className="pt-4 border-t border-surface-high/50">
                    <h4 className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-4 flex items-center gap-2">
                      <Network className="w-3.5 h-3.5" /> Frequently joined with
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {Array.from(new Set(activeTableObj.relationships.map(r => r.target))).map((target: string) => (
                        <button 
                          key={target}
                          onClick={() => { setActiveTable(target); setHighlightedColumn(null); }}
                          className="bg-surface-high/30 hover:bg-primary-neon/10 border border-surface-high hover:border-primary-neon/50 text-xs font-mono text-on-surface px-3 py-1.5 rounded-lg transition-colors flex items-center gap-2"
                        >
                          <TableIcon className="w-3 h-3 text-primary-neon opacity-70" />
                          {target}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggested Queries */}
                {activeTableObj.suggested_queries && activeTableObj.suggested_queries.length > 0 && (
                  <div className="pt-4">
                    <h4 className="text-[10px] uppercase font-bold tracking-wider text-primary-neon mb-4 flex items-center gap-2 border-b border-primary-neon/20 pb-2">
                      <Play className="w-3.5 h-3.5" /> AI Recommended Queries
                    </h4>
                    <div className="grid gap-3">
                      {activeTableObj.suggested_queries.map((q: any, i: number) => (
                        <div key={i} className="bg-surface-high/20 border border-surface-high rounded-xl p-4 flex flex-col xl:flex-row xl:items-center justify-between gap-4 group hover:border-primary-neon/30 transition-colors">
                          <div className="flex-1 min-w-0">
                            <h5 className="text-sm font-bold text-on-surface mb-1 truncate">{q.title}</h5>
                            <code className="text-xs font-mono text-primary-neon/80 block truncate opacity-70">{q.sql}</code>
                          </div>
                          <button 
                            onClick={() => {
                              navigate('/query', { state: { initialPrompt: q.title } });
                            }}
                            className="bg-surface-high hover:bg-primary-neon hover:text-surface text-on-surface px-4 py-2 rounded-lg text-xs font-bold transition-colors whitespace-nowrap self-start xl:self-auto flex items-center gap-2"
                          >
                            <Play className="w-3 h-3" /> Run in Studio
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Inline Sticky Chat */}
              <div className="p-4 border-t border-surface-high bg-surface-high/10 mt-auto">
                <form 
                  onSubmit={(e) => { 
                    e.preventDefault(); 
                    executeChat(chatInput); 
                    setChatInput(''); 
                    setIsChatDrawerOpen(true); 
                  }}
                  className="flex items-center gap-2 relative"
                >
                  <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                    <Sparkles className="w-4 h-4 text-primary-neon opacity-70" />
                  </div>
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder={`Ask about ${activeTableObj.name}...`}
                    className="flex-1 bg-surface border border-surface-high rounded-xl pl-10 pr-12 py-3 text-sm text-on-surface focus:outline-none focus:border-primary-neon/50 transition-colors shadow-inner"
                    disabled={isChatLoading}
                  />
                  <button
                    type="submit"
                    disabled={!chatInput.trim() || isChatLoading}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-primary-neon hover:bg-primary-neon/10 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 relative">
              <div className="absolute inset-0 bg-gradient-to-b from-primary-neon/5 to-transparent pointer-events-none"></div>
              <Sparkles className="w-12 h-12 text-primary-neon mb-6 opacity-80 shadow-[0_0_30px_rgba(0,255,157,0.3)]" />
              <h2 className="text-3xl font-black text-on-surface mb-3 tracking-tight">Ask about your database</h2>
              <p className="text-on-surface-variant mb-10 max-w-md text-center leading-relaxed">
                I'm your AI Database Architect. I understand the entire schema, relationships, and structure of your selected database.
              </p>
              
              <form 
                onSubmit={(e) => { 
                  e.preventDefault(); 
                  executeChat(chatInput); 
                  setChatInput(''); 
                  setIsChatDrawerOpen(true); 
                }}
                className="w-full max-w-2xl relative shadow-[0_0_40px_rgba(0,0,0,0.3)]"
              >
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                  <Bot className="w-5 h-5 text-primary-neon opacity-80" />
                </div>
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="e.g., How do users relate to orders? What tables store logs?"
                  className="w-full bg-surface-high border border-surface-high hover:border-primary-neon/30 focus:border-primary-neon/50 rounded-2xl pl-12 pr-14 py-4 text-base text-on-surface focus:outline-none transition-all shadow-inner"
                  disabled={isChatLoading}
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || isChatLoading}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-primary-neon text-surface hover:bg-white rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
              
              <div className="flex flex-wrap justify-center gap-3 mt-8 max-w-2xl">
                {["Explain the purpose of this database", "Show me the most important tables", "Which tables have the most foreign keys?"].map((q, i) => (
                  <button 
                    key={i}
                    onClick={() => { executeChat(q); setIsChatDrawerOpen(true); }}
                    className="bg-surface-high/50 hover:bg-primary-neon/10 border border-surface-high hover:border-primary-neon/30 text-xs text-on-surface px-4 py-2 rounded-full transition-colors flex items-center gap-2"
                  >
                    <Search className="w-3 h-3 text-primary-neon opacity-70" /> {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Intelligence Panel */}
        <div className="w-[300px] xl:w-[350px] flex-shrink-0 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl flex flex-col overflow-hidden ring-1 ring-white/5 relative z-10">
          <div className="p-4 border-b border-surface-high bg-surface-high/10 flex items-center gap-3">
            <BrainCircuit className="w-5 h-5 text-primary-neon" />
            <h3 className="font-bold text-on-surface">Database Intelligence</h3>
          </div>
          
          <div className="flex-1 overflow-y-auto p-5 space-y-8">
            {isIntelligenceLoading ? (
              <div className="flex flex-col gap-4 animate-pulse">
                <div className="h-4 bg-surface-high rounded w-1/3"></div>
                <div className="h-16 bg-surface-high/50 rounded w-full"></div>
                <div className="h-4 bg-surface-high rounded w-1/4 mt-4"></div>
                <div className="h-12 bg-surface-high/50 rounded w-full"></div>
              </div>
            ) : intelligenceReport ? (
              <div className="space-y-8 animate-in fade-in duration-500">
                
                {/* Domain & Summary */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-3 flex items-center gap-2">
                    <Lightbulb className="w-3.5 h-3.5 text-primary-neon" /> Business Domain
                  </h4>
                  <div className="text-sm font-bold text-on-surface mb-2">{intelligenceReport.business_domain}</div>
                  <p className="text-xs text-on-surface-variant leading-relaxed">
                    {intelligenceReport.summary}
                  </p>
                </div>

                {/* Core Entities */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-3">Core Entities</h4>
                  <div className="flex flex-wrap gap-2">
                    {intelligenceReport.core_entities?.map((entity: string, i: number) => (
                      <button 
                        key={i}
                        onClick={() => setActiveTable(entity)}
                        className={`text-xs font-mono px-2 py-1 rounded border transition-colors ${activeTable === entity ? 'bg-primary-neon/10 border-primary-neon/50 text-primary-neon' : 'bg-surface-high/30 border-surface-high text-on-surface-variant hover:text-on-surface hover:border-surface-high/80'}`}
                      >
                        {entity}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Network Stats */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-3">Network Graph</h4>
                  <div className="bg-surface-high/20 border border-surface-high rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-on-surface-variant">Detected Relationships</span>
                      <span className="font-mono text-sm font-bold text-primary-neon">{intelligenceReport.relationship_count}</span>
                    </div>
                    <div className="w-full bg-surface-high rounded-full h-1.5 mt-2 overflow-hidden flex">
                      <div className="bg-primary-neon h-full" style={{ width: '60%' }}></div>
                      <div className="bg-yellow-400 h-full" style={{ width: '40%' }}></div>
                    </div>
                    <div className="flex justify-between text-[9px] uppercase font-bold mt-2">
                      <span className="text-primary-neon opacity-80">Declared FKs</span>
                      <span className="text-yellow-400 opacity-80">Inferred Links</span>
                    </div>
                  </div>
                </div>

                {/* Suggested AI Questions */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-3">Analytical Questions</h4>
                  <div className="space-y-2">
                    {intelligenceReport.suggested_questions?.map((q: string, i: number) => (
                      <button
                        key={i}
                        onClick={() => {
                          setIsChatDrawerOpen(true);
                          executeChat(q);
                        }}
                        className="w-full text-left bg-surface-high/30 hover:bg-surface-high/60 border border-surface-high rounded-lg p-3 text-xs text-on-surface transition-colors font-medium flex items-center justify-between group"
                      >
                        <span className="flex-1 pr-2 line-clamp-2 leading-relaxed">{q}</span>
                        <Play className="w-3 h-3 text-primary-neon opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Join Path Explorer */}
                <div>
                  <h4 className="text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-3 flex items-center gap-2">
                    <Network className="w-3.5 h-3.5 text-primary-neon" /> Join Path Explorer
                  </h4>
                  <div className="bg-surface-high/20 border border-surface-high rounded-xl p-3 space-y-3">
                    <select 
                      className="w-full bg-surface border border-surface-high rounded-lg text-xs p-2 text-on-surface focus:outline-none focus:border-primary-neon/50"
                      value={joinTarget}
                      onChange={e => setJoinTarget(e.target.value)}
                    >
                      <option value="">Select target table...</option>
                      {schemas[0]?.tables.map(t => (
                        t.name !== activeTable && <option key={t.name} value={t.name}>{t.name}</option>
                      ))}
                    </select>
                    
                    {joinPath && joinPath.length > 0 && (
                      <div className="pt-2 border-t border-surface-high/50">
                        <div className="text-[10px] uppercase font-bold text-on-surface-variant mb-2">Shortest Path</div>
                        <div className="flex flex-wrap items-center gap-2">
                          {joinPath.map((node, i) => (
                            <div key={i} className="flex items-center gap-2">
                              <span className="text-xs font-mono bg-surface-high/50 px-2 py-1 rounded text-primary-neon">{node}</span>
                              {i < joinPath.length - 1 && <span className="text-on-surface-variant text-[10px]">→</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {joinTarget && (!joinPath || joinPath.length === 0) && (
                      <div className="pt-2 border-t border-surface-high/50 text-xs text-error opacity-80">
                        No relationship path found.
                      </div>
                    )}
                  </div>
                </div>

              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-on-surface-variant text-center opacity-60">
                <Bot className="w-10 h-10 mb-3" />
                <p className="text-xs">Select a database to generate AI intelligence.</p>
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Slide-over Schema Chat Drawer */}
      {isChatDrawerOpen && (
        <>
          <div 
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 transition-opacity"
            onClick={() => setIsChatDrawerOpen(false)}
          ></div>
          <div className="fixed top-0 right-0 h-full w-full max-w-md bg-surface/95 backdrop-blur-2xl border-l border-surface-high shadow-[0_0_50px_rgba(0,0,0,0.5)] z-50 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="p-4 border-b border-surface-high flex justify-between items-center bg-surface-high/20">
              <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary-neon" /> Schema AI
              </h3>
              <button 
                onClick={() => setIsChatDrawerOpen(false)}
                className="text-on-surface-variant hover:text-on-surface hover:bg-surface-high/50 p-2 rounded-lg transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
              </button>
            </div>

            <div className="flex-1 p-4 overflow-y-auto space-y-4 flex flex-col">
              {chatHistory.length === 0 ? (
                <div className="flex-1 flex flex-col justify-center space-y-6">
                  <div className="text-center">
                    <Bot className="w-10 h-10 text-on-surface-variant mx-auto mb-3 opacity-50" />
                    <p className="text-xs text-on-surface-variant leading-relaxed">I'm your AI Database Architect. Ask me anything about <span className="font-mono text-primary-neon">{activeTableObj ? activeTableObj.name : "the database"}</span>.</p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider pl-1 mb-2">Suggested Questions</div>
                    {["How is this table related to others?", "What is the primary key?", "Show me a query to find duplicates"].map((q, i) => (
                      <button 
                        key={i}
                        onClick={() => executeChat(q)}
                        className="w-full text-left bg-surface-high/30 hover:bg-surface-high/60 border border-surface-high rounded-lg p-3 text-xs text-on-surface transition-colors font-medium flex items-center justify-between group"
                      >
                        {q} <Play className="w-3 h-3 text-primary-neon opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                chatHistory.map((msg, i) => (
                  <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`max-w-[90%] p-3 rounded-xl text-sm ${msg.role === 'user' ? 'bg-primary-neon/10 text-primary-neon border border-primary-neon/30 rounded-br-sm' : 'bg-surface-high border border-surface-high rounded-bl-sm text-on-surface'}`}>
                      <div className="flex items-center gap-2 mb-1 opacity-70">
                        {msg.role === 'user' ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
                        <span className="text-[10px] font-bold uppercase tracking-wider">{msg.role}</span>
                      </div>
                      <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                    </div>
                  </div>
                ))
              )}
              {isChatLoading && (
                <div className="flex items-start">
                  <div className="max-w-[90%] p-3 rounded-xl bg-surface-high border border-surface-high rounded-bl-sm text-on-surface flex items-center gap-2 shadow-[0_0_15px_rgba(0,0,0,0.2)]">
                    <Loader2 className="w-4 h-4 animate-spin text-primary-neon" />
                    <span className="text-xs">Analyzing schema...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-surface-high bg-surface-high/10">
              <form 
                onSubmit={(e) => { e.preventDefault(); handleSendChat(); }}
                className="flex items-center gap-2 relative"
              >
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about the schema..."
                  className="flex-1 bg-surface border border-surface-high rounded-xl pl-4 pr-12 py-3 text-sm text-on-surface focus:outline-none focus:border-primary-neon/50 transition-colors shadow-inner"
                  disabled={isChatLoading}
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || isChatLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-primary-neon hover:bg-primary-neon/10 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </div>
        </>
      )}

      {/* Command Palette */}
      {isCommandPaletteOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-start justify-center pt-32 p-4" onClick={() => setIsCommandPaletteOpen(false)}>
          <div className="w-full max-w-2xl bg-surface border border-surface-high rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.5)] overflow-hidden animate-in fade-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
            <div className="flex items-center px-4 py-3 border-b border-surface-high">
              <Search className="w-5 h-5 text-on-surface-variant mr-3" />
              <input 
                autoFocus
                type="text" 
                placeholder="Search tables and columns..." 
                className="flex-1 bg-transparent border-none outline-none text-on-surface placeholder:text-on-surface-variant font-medium"
                value={paletteSearch}
                onChange={e => setPaletteSearch(e.target.value)}
              />
              <button onClick={() => setIsCommandPaletteOpen(false)} className="text-on-surface-variant hover:text-on-surface bg-surface-high/50 p-1.5 rounded-lg transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-2">
              {(() => {
                const results: { type: 'table' | 'column', text: string, table: string, database_schema: string }[] = [];
                if (paletteSearch.trim().length > 0) {
                  const q = paletteSearch.toLowerCase();
                  schemas.forEach(s => {
                    s.tables.forEach(t => {
                      if (t.name.toLowerCase().includes(q)) {
                        results.push({ type: 'table', text: t.name, table: t.name, database_schema: s.database_schema });
                      }
                      t.columns.forEach(c => {
                        if (c.name.toLowerCase().includes(q)) {
                          results.push({ type: 'column', text: `${t.name}.${c.name}`, table: t.name, database_schema: s.database_schema });
                        }
                      });
                    });
                  });
                }
                
                if (paletteSearch.trim().length > 0 && results.length === 0) {
                  return <div className="p-8 text-center text-sm text-on-surface-variant">No results found for "{paletteSearch}"</div>;
                }
                
                if (paletteSearch.trim().length === 0) {
                  return <div className="p-8 text-center text-xs text-on-surface-variant opacity-60">Type to search across all tables and columns...</div>;
                }
                
                return results.slice(0, 50).map((r, i) => (
                  <button 
                    key={i}
                    onClick={() => {
                      setActiveTable(r.table);
                      if (r.type === 'column') {
                        const colName = r.text.split('.')[1];
                        setHighlightedColumn(colName);
                        setTimeout(() => {
                          const detailsEl = document.getElementById('attributes-details') as HTMLDetailsElement;
                          if (detailsEl) detailsEl.open = true;
                          setTimeout(() => {
                            document.getElementById(`col-${colName}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                          }, 100);
                        }, 50);
                      } else {
                        setHighlightedColumn(null);
                      }
                      setIsCommandPaletteOpen(false);
                      setPaletteSearch("");
                    }}
                    className="w-full text-left flex items-center gap-3 p-3 hover:bg-surface-high/50 rounded-xl transition-colors group"
                  >
                    {r.type === 'table' ? (
                      <TableIcon className="w-4 h-4 text-primary-neon opacity-70 group-hover:opacity-100" />
                    ) : (
                      <Columns className="w-4 h-4 text-blue-400 opacity-70 group-hover:opacity-100" />
                    )}
                    <span className="text-sm font-mono text-on-surface flex-1">
                      {r.type === 'column' ? (
                        <>
                          <span className="text-on-surface-variant">{r.table}.</span>
                          <span className="text-on-surface">{r.text.split('.')[1]}</span>
                        </>
                      ) : (
                        r.text
                      )}
                    </span>
                    <span className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider bg-surface-high px-2 py-0.5 rounded">
                      {r.type}
                    </span>
                  </button>
                ));
              })()}
            </div>
          </div>
        </div>
      )}

      {/* Custom Modal */}
      {modalState.isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="bg-surface border border-surface-high rounded-2xl shadow-2xl max-w-md w-full p-6 relative flex flex-col gap-4 animate-in zoom-in-95">
            <div className="flex items-center gap-3">
              {modalState.type === 'loading' && <Loader2 className="w-6 h-6 text-primary-neon animate-spin" />}
              {modalState.type === 'success' && <Sparkles className="w-6 h-6 text-primary-neon" />}
              {modalState.type === 'error' && <AlertCircle className="w-6 h-6 text-error" />}
              {modalState.type === 'info' && <Info className="w-6 h-6 text-blue-400" />}
              <h3 className="text-lg font-bold text-on-surface">{modalState.title}</h3>
            </div>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              {modalState.message}
            </p>
            {modalState.type !== 'loading' && (
              <div className="flex justify-end mt-2">
                <button
                  onClick={() => setModalState(prev => ({ ...prev, isOpen: false }))}
                  className="bg-primary-neon text-surface hover:bg-white px-5 py-2 rounded-xl text-sm font-bold transition-colors"
                >
                  OK
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
