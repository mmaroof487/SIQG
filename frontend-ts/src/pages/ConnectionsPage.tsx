import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../utils/api";
import { 
  Database, Plus, Trash2, Key, 
  RefreshCw, CheckCircle, XCircle, AlertCircle,
  Server, LayoutTemplate, Network, Activity, Search, Shield, Zap, Sparkles, Clock, Compass
} from "lucide-react";

interface ColumnEncryptionConfig {
  id: number;
  connection_id: string;
  table_name: string;
  column_name: string;
  created_at: string;
}

export interface Connection {
  id: string;
  display_name: string;
  db_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  column_encryption_configs: ColumnEncryptionConfig[];
}

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Add Form State
  const [showAddForm, setShowAddForm] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [displayName, setDisplayName] = useState("");
  const [dbType, setDbType] = useState("postgres");
  const [connStr, setConnStr] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("");
  const [dbName, setDbName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const getBuiltConnStr = () => {
    if (dbType === "sqlite") return connStr;
    return `${dbType === "postgres" ? "postgresql" : "mysql"}://${encodeURIComponent(username)}:${encodeURIComponent(password)}@${host}:${port}/${dbName}`;
  };

  // Testing connection states map (connectionId -> { ok, error, loading })
  const [testStates, setTestStates] = useState<Record<string, { ok?: boolean; error?: string; loading?: boolean }>>({});
  
  // Expanded encryption rules map (connectionId -> boolean)
  const [expandedConfigs, setExpandedConfigs] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetchConnections();
  }, []);

  const fetchConnections = async () => {
    setIsLoading(true);
    setError("");
    try {
      const res = await api.getConnections();
      setConnections(res.data);
      window.dispatchEvent(new Event('connectionsUpdated'));
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load connections.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (wizardStep < 5) return;
    
    const finalConnStr = getBuiltConnStr();
    setError("");
    setSuccess("");
    try {
      await api.createConnection({
        display_name: displayName.trim(),
        db_type: dbType,
        conn_str: finalConnStr.trim()
      });
      // Move to success / discovery step instead of closing
      setWizardStep(6);
      fetchConnections(); // Refresh data in background
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create connection.");
    }
  };

  const handleTestConnection = async (id: string) => {
    setTestStates(prev => ({ ...prev, [id]: { loading: true } }));
    try {
      const res = await api.testConnection(id);
      if (res.data.ok) {
        setTestStates(prev => ({ ...prev, [id]: { ok: true, loading: false } }));
        // Connection is healthy
      } else {
        setTestStates(prev => ({ ...prev, [id]: { ok: false, error: res.data.error || "Connection failed", loading: false } }));
      }
    } catch (err: any) {
      setTestStates(prev => ({ 
        ...prev, 
        [id]: { ok: false, error: err.response?.data?.detail || "Network error during test", loading: false } 
      }));
    }
  };

  const handleDeleteConnection = async (id: string) => {
    if (!window.confirm("Are you sure you want to deactivate this connection?")) {
      return;
    }
    setError("");
    setSuccess("");
    try {
      await api.deleteConnection(id);
      setSuccess("Connection deactivated successfully.");
      fetchConnections();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to deactivate connection.");
    }
  };

  const handleHardDeleteConnection = async (id: string) => {
    if (!window.confirm("Are you sure you want to completely remove this connection? This action cannot be undone.")) {
      return;
    }
    setError("");
    setSuccess("");
    try {
      await api.hardDeleteConnection(id);
      setSuccess("Connection permanently removed.");
      fetchConnections();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to remove connection.");
    }
  };

  const toggleConfigs = (id: string) => {
    setExpandedConfigs(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const healthyCount = connections.filter(c => c.is_active).length;
  const offlineCount = connections.filter(c => !c.is_active).length;

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-16">
      {/* Top Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div className="flex items-end gap-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
            <Network className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
          </div>
          <div>
            <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Connected Databases</h1>
            <div className="flex items-center gap-4 text-sm font-medium">
              <span className="flex items-center gap-1.5 text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-md border border-emerald-400/20">
                <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)] animate-pulse"></div>
                {healthyCount} Healthy
              </span>
              <span className="flex items-center gap-1.5 text-rose-400 bg-rose-400/10 px-2 py-0.5 rounded-md border border-rose-400/20">
                <div className="w-2 h-2 rounded-full bg-rose-400"></div>
                {offlineCount} Offline / Degraded
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={() => {
            setShowAddForm(!showAddForm);
            setError("");
            setSuccess("");
            setWizardStep(1);
          }}
          className="px-5 py-3 bg-primary-neon/10 hover:bg-primary-neon/20 text-primary-neon text-sm font-bold uppercase tracking-widest rounded-xl transition-all border border-primary-neon/30 flex items-center gap-2"
        >
          {showAddForm ? <XCircle className="w-4 h-4" /> : <Plus className="w-4 h-4" />} 
          {showAddForm ? "Cancel Wizard" : "Add Connection"}
        </button>
      </div>

      {/* Message Banners */}
      {error && (
        <div className="p-4 bg-error/10 border border-error/30 text-error rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 bg-primary-neon/10 border border-primary-neon/30 text-primary-neon rounded-xl flex items-center gap-3 animate-pulse">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">{success}</span>
        </div>
      )}

      {showAddForm ? (
        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl p-8 max-w-2xl mx-auto shadow-sm ring-1 ring-white/5">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-on-surface flex items-center gap-2">
              {wizardStep === 6 || wizardStep === 7 ? (
                <><Sparkles className="w-5 h-5 text-primary-neon" /> Discovery</>
              ) : (
                <><Plus className="w-5 h-5 text-primary-neon" /> Connection Wizard</>
              )}
            </h2>
            <div className="flex gap-1.5">
              {[1, 2, 3, 4, 5, 6].map(step => (
                <div key={step} className={`h-2 rounded-full transition-all ${wizardStep === step ? 'w-8 bg-primary-neon shadow-[0_0_8px_#00FF9D]' : wizardStep > step ? 'w-4 bg-primary-neon/50' : 'w-2 bg-surface-high'}`} />
              ))}
            </div>
          </div>
          
          <form onSubmit={handleAddConnection} className="space-y-6 min-h-[250px] relative">
            {wizardStep === 1 && (
              <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                <label className="text-sm font-bold text-on-surface">Step 1: Choose Database</label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { id: 'postgres', label: 'PostgreSQL', icon: Database },
                    { id: 'mysql', label: 'MySQL', icon: Database },
                    { id: 'sqlite', label: 'SQLite', icon: Database },
                  ].map(engine => (
                    <button
                      key={engine.id}
                      type="button"
                      onClick={() => { setDbType(engine.id); setWizardStep(2); }}
                      className={`p-6 rounded-xl border flex flex-col items-center gap-3 transition-all ${dbType === engine.id ? 'bg-primary-neon/10 border-primary-neon/50 text-primary-neon shadow-[inset_0_0_20px_rgba(0,255,157,0.1)]' : 'bg-surface border-surface-high text-on-surface-variant hover:bg-surface-high/50 hover:text-on-surface'}`}
                    >
                      <engine.icon className="w-8 h-8" />
                      <span className="font-bold text-sm">{engine.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {wizardStep === 2 && (
              <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                <label className="text-sm font-bold text-on-surface">Step 2: Database Name</label>
                <p className="text-xs text-on-surface-variant">Enter a friendly name for this connection.</p>
                <input 
                  type="text" 
                  placeholder="e.g. AthletIQ Production" 
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  autoFocus
                  required
                  className="w-full bg-surface border border-surface-high px-4 py-4 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface transition-colors text-lg"
                />
              </div>
            )}

            {wizardStep === 3 && (
              <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                <label className="text-sm font-bold text-on-surface">Step 3: Connection Details</label>
                <p className="text-xs text-on-surface-variant">Provide the database credentials and host.</p>
                
                {dbType === "sqlite" ? (
                  <div className="relative">
                    <Key className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-on-surface-variant" />
                    <input 
                      type="text" 
                      placeholder="sqlite:///path/to/db.sqlite" 
                      value={connStr}
                      onChange={(e) => setConnStr(e.target.value)}
                      autoFocus
                      required
                      className="w-full bg-surface border border-surface-high pl-12 pr-4 py-4 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface font-mono transition-colors"
                    />
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-on-surface-variant">Host</label>
                        <input type="text" placeholder="localhost" value={host} onChange={(e) => setHost(e.target.value)} className="w-full bg-surface border border-surface-high px-4 py-3 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface font-mono" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-on-surface-variant">Port</label>
                        <input type="text" placeholder={dbType === "postgres" ? "5432" : "3306"} value={port} onChange={(e) => setPort(e.target.value)} className="w-full bg-surface border border-surface-high px-4 py-3 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface font-mono" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-on-surface-variant">Database Name</label>
                      <input type="text" placeholder="dbname" value={dbName} onChange={(e) => setDbName(e.target.value)} className="w-full bg-surface border border-surface-high px-4 py-3 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface font-mono" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-on-surface-variant">Username</label>
                        <input type="text" placeholder="user" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full bg-surface border border-surface-high px-4 py-3 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface font-mono" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-bold text-on-surface-variant">Password</label>
                        <input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full bg-surface border border-surface-high px-4 py-3 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface font-mono" />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {wizardStep === 4 && (
              <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                <label className="text-sm font-bold text-on-surface">Step 4: Encryption Rules</label>
                <p className="text-xs text-on-surface-variant">How should Argus handle credentials?</p>
                
                <div className="p-6 bg-primary-neon/5 border border-primary-neon/30 rounded-xl space-y-2 relative overflow-hidden group hover:border-primary-neon/50 transition-colors">
                  <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Key className="w-24 h-24 text-primary-neon" />
                  </div>
                  <h4 className="font-bold text-primary-neon flex items-center gap-2">
                    <Key className="w-5 h-5" /> Default Policy: AES-256-GCM
                  </h4>
                  <p className="text-sm text-on-surface-variant relative z-10 w-4/5">
                    Connection credentials will be automatically encrypted at rest using AES-256-GCM. 
                    They are only decrypted in-memory by the query execution engine at runtime.
                  </p>
                  <div className="pt-2">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-primary-neon/20 text-primary-neon text-xs font-bold uppercase tracking-wider rounded">
                      <Shield className="w-3 h-3" /> Policy Enforced
                    </span>
                  </div>
                </div>
              </div>
            )}

            {wizardStep === 5 && (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <label className="text-sm font-bold text-on-surface">Step 5: Review & Test</label>
                <div className="p-6 bg-surface border border-surface-high rounded-xl space-y-4">
                  <div className="flex justify-between items-center pb-4 border-b border-surface-high">
                    <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Engine</span>
                    <span className="text-sm font-bold text-primary-neon flex items-center gap-2">
                      <Database className="w-4 h-4" /> {dbType}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pb-4 border-b border-surface-high">
                    <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Database Name</span>
                    <span className="text-sm font-bold text-on-surface">{displayName}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">URI</span>
                    <span className="text-sm font-mono text-on-surface-variant">••••••••••••••••••••</span>
                  </div>
                </div>
              </div>
            )}

            {wizardStep === 6 && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-500 flex flex-col items-center justify-center text-center py-8">
                <div className="w-20 h-20 rounded-full bg-primary-neon/20 border border-primary-neon/50 flex items-center justify-center mb-2 shadow-[0_0_30px_rgba(0,255,157,0.3)]">
                  <Sparkles className="w-10 h-10 text-primary-neon animate-pulse" />
                </div>
                <h3 className="text-2xl font-black text-on-surface">Database Analyzed!</h3>
                
                <div className="grid grid-cols-3 gap-4 w-full mt-4">
                  <div className="p-4 bg-surface border border-surface-high rounded-xl">
                    <LayoutTemplate className="w-5 h-5 text-primary-neon mx-auto mb-2" />
                    <div className="text-2xl font-bold text-on-surface">--</div>
                    <div className="text-xs text-on-surface-variant uppercase tracking-wider font-bold">Tables Found</div>
                  </div>
                  <div className="p-4 bg-surface border border-surface-high rounded-xl">
                    <Server className="w-5 h-5 text-primary-container mx-auto mb-2" />
                    <div className="text-2xl font-bold text-on-surface">--</div>
                    <div className="text-xs text-on-surface-variant uppercase tracking-wider font-bold">Columns Found</div>
                  </div>
                  <div className="p-4 bg-surface border border-surface-high rounded-xl">
                    <Network className="w-5 h-5 text-secondary-teal mx-auto mb-2" />
                    <div className="text-2xl font-bold text-on-surface">--</div>
                    <div className="text-xs text-on-surface-variant uppercase tracking-wider font-bold">Relationships</div>
                  </div>
                </div>
              </div>
            )}

            <div className="flex justify-between pt-6 border-t border-surface-high/50">
              {wizardStep < 6 && (
                <button 
                  type="button" 
                  onClick={() => {
                    if (wizardStep === 1) {
                      setShowAddForm(false);
                    } else {
                      setWizardStep(s => s - 1);
                    }
                  }} 
                  className="px-5 py-2.5 bg-surface hover:bg-surface-high border border-surface-high text-on-surface rounded-xl transition-colors font-semibold text-sm"
                >
                  {wizardStep === 1 ? 'Cancel' : 'Back'}
                </button>
              )}
              
              {wizardStep < 5 ? (
                <button 
                  type="button" 
                  onClick={() => {
                    if (wizardStep === 2 && !displayName.trim()) return setError("Please enter the database name");
                    if (wizardStep === 3) {
                      if (dbType === "sqlite" && !connStr.trim()) return setError("Please enter a connection string");
                      if (dbType !== "sqlite" && (!host.trim() || !port.trim() || !dbName.trim() || !username.trim())) {
                        return setError("Please fill out all connection details");
                      }
                    }
                    setError("");
                    setWizardStep(s => s + 1);
                  }}
                  className="px-6 py-2.5 bg-on-surface text-surface hover:bg-on-surface/90 rounded-xl transition-colors font-bold text-sm ml-auto"
                >
                  Next Step
                </button>
              ) : wizardStep === 5 ? (
                <button 
                  type="submit" 
                  className="px-6 py-2.5 bg-primary-neon text-surface hover:bg-primary-neon/90 rounded-xl transition-colors font-bold text-sm shadow-[0_0_15px_rgba(0,255,157,0.25)] flex items-center gap-2 ml-auto"
                >
                  <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                  Connect Database
                </button>
              ) : (
                <button 
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="w-full px-6 py-3 bg-on-surface text-surface hover:bg-on-surface/90 rounded-xl transition-colors font-bold text-sm shadow-md"
                >
                  Done
                </button>
              )}
            </div>
          </form>
        </div>
      ) : (
        <>
          {isLoading ? (
            <div className="p-12 text-center text-on-surface-variant flex flex-col items-center justify-center gap-3">
              <RefreshCw className="w-8 h-8 text-primary-neon animate-spin" />
              <span>Loading databases...</span>
            </div>
          ) : connections.length === 0 ? (
            <div className="bg-surface/40 border border-surface-high rounded-2xl overflow-hidden shadow-sm backdrop-blur-xl p-16 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-surface-high flex items-center justify-center mx-auto text-on-surface-variant">
                <Database className="w-6 h-6" />
              </div>
              <div className="max-w-xs mx-auto">
                <h3 className="font-bold text-on-surface text-lg">No connections yet</h3>
                <p className="text-sm text-on-surface-variant mt-1">Add your first database connection to start query routing.</p>
              </div>
              <button
                onClick={() => setShowAddForm(true)}
                className="px-4 py-2 bg-primary-neon text-surface font-bold text-xs uppercase tracking-widest rounded-xl transition-colors"
              >
                Add connection
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {connections.map((conn) => {
                const testState = testStates[conn.id];
                const isExpanded = !!expandedConfigs[conn.id];
                const isHealthy = conn.is_active;
                
                return (
                  <div key={conn.id} className="group relative bg-surface/40 border border-surface-high rounded-2xl flex flex-col hover:border-primary-neon/50 transition-all duration-300 hover:shadow-[0_8px_30px_rgba(0,0,0,0.12)] hover:-translate-y-1 overflow-visible">
                    
                    {/* Card Header */}
                    <div className="p-5 border-b border-surface-high">
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-surface-high flex items-center justify-center border border-surface-high">
                            <Database className="w-5 h-5 text-on-surface-variant" />
                          </div>
                          <div>
                            <h3 className="font-bold text-on-surface text-base leading-none mb-1">{conn.display_name}</h3>
                            <span className="text-[10px] text-on-surface-variant font-mono uppercase">{conn.db_type}</span>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          {/* Status Badge */}
                          <div className={`px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 border ${
                            isHealthy ? "bg-emerald-400/10 text-emerald-400 border-emerald-400/20" :
                            "bg-rose-400/10 text-rose-400 border-rose-400/20"
                          }`}>
                            <div className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.8)]' : 'bg-rose-400'}`} />
                            {isHealthy ? "Active" : "Inactive"}
                          </div>
                          
                          {/* Delete Button */}
                          {isHealthy ? (
                            <button
                              onClick={() => handleDeleteConnection(conn.id)}
                              className="p-1.5 text-on-surface-variant hover:text-amber-400 hover:bg-amber-400/10 rounded-lg transition-all"
                              title="Deactivate Connection"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleHardDeleteConnection(conn.id)}
                              className="p-1.5 text-on-surface-variant hover:text-rose-400 hover:bg-rose-400/10 rounded-lg transition-all"
                              title="Permanently Remove Connection"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Activity Section */}
                    <div className="px-5 py-3 bg-surface/20 flex justify-between items-center text-xs border-b border-surface-high">
                      <div className="flex items-center gap-2 text-on-surface-variant">
                        <Activity className="w-3.5 h-3.5" />
                        <span className="font-medium text-on-surface">Updated: <span className="font-mono text-primary-neon">{new Date(conn.updated_at).toLocaleDateString()}</span></span>
                      </div>
                      <div className="flex items-center gap-1 text-on-surface-variant opacity-80">
                        <Clock className="w-3 h-3" />
                        Added {new Date(conn.created_at).toLocaleDateString()}
                      </div>
                    </div>

                    {/* Quick Actions (Bottom) */}
                    <div className="p-3 grid grid-cols-2 gap-2 mt-auto">
                      <Link 
                        to={`/query?db=${conn.id}`}
                        className="flex items-center justify-center gap-1.5 px-2 py-1.5 bg-primary-neon/10 hover:bg-primary-neon/20 text-primary-neon rounded-lg text-[11px] font-bold transition-colors border border-primary-neon/20"
                      >
                        <Search className="w-3 h-3" /> Query Studio
                      </Link>
                      
                      <Link 
                        to={`/schema?db=${conn.id}`}
                        className="flex items-center justify-center gap-1.5 px-2 py-1.5 bg-surface hover:bg-surface-high text-on-surface rounded-lg text-[11px] font-bold transition-colors border border-surface-high"
                      >
                        <Compass className="w-3 h-3" /> Explore Schema
                      </Link>
                      
                      <button 
                        onClick={() => handleTestConnection(conn.id)}
                        className="flex items-center justify-center gap-1.5 px-2 py-1.5 bg-surface hover:bg-surface-high text-on-surface rounded-lg text-[11px] font-bold transition-colors border border-surface-high"
                      >
                        <RefreshCw className={`w-3 h-3 ${testState?.loading ? 'animate-spin text-primary-neon' : ''}`} /> 
                        {testState?.loading ? "Testing..." : "Test Connection"}
                      </button>
                      
                      <button 
                        onClick={() => toggleConfigs(conn.id)}
                        className="flex items-center justify-center gap-1.5 px-2 py-1.5 bg-surface hover:bg-surface-high text-on-surface rounded-lg text-[11px] font-bold transition-colors border border-surface-high"
                      >
                        <Shield className="w-3 h-3" /> Security Policies
                      </button>
                    </div>

                    {/* Expandable encryption rules (Policies) */}
                    {isExpanded && (
                      <div className="m-4 mt-0 bg-surface/60 border border-surface-high rounded-xl p-4 animate-in slide-in-from-top-2 duration-300">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-primary-neon" />
                            <h4 className="text-xs uppercase font-bold tracking-wider text-on-surface">Security Policies</h4>
                          </div>
                        </div>
                        
                        {!conn.column_encryption_configs || conn.column_encryption_configs.length === 0 ? (
                          <p className="text-xs text-on-surface-variant italic">No columns configured for encryption. Queries will be stored in plaintext.</p>
                        ) : (
                          <div className="overflow-x-auto">
                            <table className="w-full text-left text-xs font-mono">
                              <thead>
                                <tr className="border-b border-surface-high text-on-surface-variant font-sans font-bold">
                                  <th className="pb-2">Table</th>
                                  <th className="pb-2">Column</th>
                                  <th className="pb-2 text-right">Policy</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-surface-high/30">
                                {conn.column_encryption_configs.map((config) => (
                                  <tr key={config.id} className="text-on-surface/90">
                                    <td className="py-2">{config.table_name}</td>
                                    <td className="py-2 text-primary-neon">{config.column_name}</td>
                                    <td className="py-2 text-right text-primary-container">AES-256</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Bottom Section: Activity Feed Mock */}
          {!isLoading && connections.length > 0 && (
            <div className="mt-12">
              <h3 className="text-lg font-bold text-on-surface mb-4">Recent Activity</h3>
              <div className="bg-surface/40 border border-surface-high rounded-2xl overflow-hidden shadow-sm backdrop-blur-xl">
                <div className="divide-y divide-surface-high">
                  <div className="p-4 flex items-center gap-4 hover:bg-surface/50 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-primary-neon/10 border border-primary-neon/30 flex items-center justify-center flex-shrink-0">
                      <Sparkles className="w-4 h-4 text-primary-neon" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-on-surface">Schema Discovery Completed</p>
                      <p className="text-xs text-on-surface-variant">Argus discovered 3 new tables in <strong>AthletIQ Production</strong></p>
                    </div>
                    <div className="text-xs text-on-surface-variant font-mono">2 mins ago</div>
                  </div>
                  <div className="p-4 flex items-center gap-4 hover:bg-surface/50 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-emerald-400/10 border border-emerald-400/30 flex items-center justify-center flex-shrink-0">
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-on-surface">Health Check Passed</p>
                      <p className="text-xs text-on-surface-variant">Automated connection test succeeded for <strong>User DB</strong></p>
                    </div>
                    <div className="text-xs text-on-surface-variant font-mono">1 hr ago</div>
                  </div>
                  <div className="p-4 flex items-center gap-4 hover:bg-surface/50 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-rose-400/10 border border-rose-400/30 flex items-center justify-center flex-shrink-0">
                      <XCircle className="w-4 h-4 text-rose-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-on-surface">Connection Failed</p>
                      <p className="text-xs text-on-surface-variant">Failed to reach <strong>Legacy Archive</strong>. Reason: Timeout.</p>
                    </div>
                    <div className="text-xs text-on-surface-variant font-mono">3 hrs ago</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
