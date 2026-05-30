import { useState, useEffect } from "react";
import { api } from "../utils/api";
import { 
  Database, Plus, Trash2, Key, 
  RefreshCw, CheckCircle, XCircle, ChevronDown, ChevronUp, AlertCircle 
} from "lucide-react";

interface ColumnEncryptionConfig {
  id: number;
  connection_id: string;
  table_name: string;
  column_name: string;
  created_at: string;
}

interface Connection {
  id: string;
  display_name: string;
  db_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  column_encryption_configs?: ColumnEncryptionConfig[];
}

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Add Form State
  const [showAddForm, setShowAddForm] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [dbType, setDbType] = useState("postgres");
  const [connStr, setConnStr] = useState("");

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
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load connections.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim() || !connStr.trim()) {
      setError("Please fill out all required fields.");
      return;
    }
    setError("");
    setSuccess("");
    try {
      await api.createConnection({
        display_name: displayName.trim(),
        db_type: dbType,
        conn_str: connStr.trim()
      });
      setSuccess("Connection registered successfully!");
      setDisplayName("");
      setConnStr("");
      setShowAddForm(false);
      fetchConnections();
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
    if (!window.confirm("Are you sure you want to delete this connection? The configurations will be deactivated.")) {
      return;
    }
    setError("");
    setSuccess("");
    try {
      await api.deleteConnection(id);
      setSuccess("Connection soft-deleted successfully.");
      fetchConnections();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete connection.");
    }
  };

  const toggleConfigs = (id: string) => {
    setExpandedConfigs(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-16">
      {/* Header section */}
      <div className="flex items-end justify-between gap-6 mb-4">
        <div className="flex items-end gap-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
            <Database className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
          </div>
          <div>
            <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Database Connections</h1>
            <p className="text-on-surface-variant font-medium">Register and manage secure routes to external databases</p>
          </div>
        </div>

        <button
          onClick={() => {
            setShowAddForm(!showAddForm);
            setError("");
            setSuccess("");
          }}
          className="px-4 py-2.5 bg-primary-neon/10 hover:bg-primary-neon/20 text-primary-neon text-xs font-bold uppercase tracking-widest rounded-xl transition-all border border-primary-neon/30 flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> {showAddForm ? "View Connections" : "Add Connection"}
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

      {/* Main panel */}
      {showAddForm ? (
        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl p-8 max-w-2xl mx-auto shadow-sm ring-1 ring-white/5">
          <h2 className="text-xl font-bold text-on-surface mb-6 flex items-center gap-2">
            <Plus className="w-5 h-5 text-primary-neon" /> Add Database Connection
          </h2>
          <form onSubmit={handleAddConnection} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs uppercase font-bold tracking-wider text-on-surface-variant">Display Name</label>
              <input 
                type="text" 
                placeholder="e.g. Analytics Replica" 
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                className="w-full bg-surface border border-surface-high px-4 py-3 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface transition-colors"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs uppercase font-bold tracking-wider text-on-surface-variant">Database Engine</label>
              <select
                value={dbType}
                onChange={(e) => setDbType(e.target.value)}
                className="w-full bg-surface border border-surface-high px-4 py-3 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface transition-colors"
              >
                <option value="postgres">PostgreSQL</option>
                <option value="mysql">MySQL (Beta)</option>
                <option value="sqlite">SQLite</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs uppercase font-bold tracking-wider text-on-surface-variant flex items-center justify-between">
                <span>Connection URI</span>
                <span className="text-[10px] text-error flex items-center gap-1"><Key className="w-3 h-3" /> Encrypted at rest</span>
              </label>
              <input 
                type="password" 
                placeholder="e.g. postgresql://user:password@host:5432/dbname" 
                value={connStr}
                onChange={(e) => setConnStr(e.target.value)}
                required
                className="w-full bg-surface border border-surface-high px-4 py-3 rounded-xl outline-none focus:border-primary-neon/50 text-on-surface font-mono transition-colors"
              />
              <p className="text-[10px] text-on-surface-variant italic">
                Connection details are encrypted using AES-256-GCM. Plaintext is decrypted only in memory during execution.
              </p>
            </div>

            <div className="flex gap-4 pt-2 justify-end">
              <button 
                type="button" 
                onClick={() => setShowAddForm(false)} 
                className="px-5 py-2.5 bg-surface hover:bg-surface-high border border-surface-high text-on-surface rounded-xl transition-colors font-semibold text-sm"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="px-6 py-2.5 bg-primary-neon text-surface hover:bg-primary-neon/90 rounded-xl transition-colors font-bold text-sm shadow-[0_0_15px_rgba(0,255,157,0.25)]"
              >
                Register connection
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="bg-surface/40 border border-surface-high rounded-2xl overflow-hidden shadow-sm backdrop-blur-xl">
          {isLoading ? (
            <div className="p-12 text-center text-on-surface-variant flex flex-col items-center justify-center gap-3">
              <RefreshCw className="w-8 h-8 text-primary-neon animate-spin" />
              <span>Loading registered databases...</span>
            </div>
          ) : connections.length === 0 ? (
            <div className="p-16 text-center space-y-4">
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
            <div className="divide-y divide-surface-high">
              {connections.map((conn) => {
                const testState = testStates[conn.id];
                const isExpanded = !!expandedConfigs[conn.id];
                
                return (
                  <div key={conn.id} className="p-6 space-y-4 hover:bg-surface/10 transition-colors">
                    <div className="flex items-center justify-between gap-4">
                      {/* Left: Info */}
                      <div className="flex items-center gap-4">
                        <div className={`p-3 rounded-xl border ${conn.is_active ? 'bg-primary-neon/10 border-primary-neon/20 text-primary-neon' : 'bg-surface-high border-surface-high text-on-surface-variant'}`}>
                          <Database className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="font-bold text-on-surface text-lg flex items-center gap-2">
                            {conn.display_name}
                            {!conn.is_active && (
                              <span className="text-[10px] bg-surface-high border border-surface-high px-2 py-0.5 rounded uppercase font-black tracking-widest text-on-surface-variant">Inactive</span>
                            )}
                          </h3>
                          <div className="flex gap-4 text-xs text-on-surface-variant font-mono mt-1">
                            <span>Engine: {conn.db_type}</span>
                            <span>ID: {conn.id.substring(0, 8)}</span>
                            <span>Added: {new Date(conn.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>

                      {/* Right: Actions */}
                      <div className="flex items-center gap-3">
                        {/* Test connection badge */}
                        {testState && (
                          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold ${
                            testState.loading ? 'bg-surface border-surface-high text-on-surface-variant animate-pulse' :
                            testState.ok ? 'bg-primary-neon/10 border-primary-neon/20 text-primary-neon' :
                            'bg-error/10 border-error/20 text-error'
                          }`}>
                            {testState.loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> :
                             testState.ok ? <CheckCircle className="w-3.5 h-3.5" /> :
                             <XCircle className="w-3.5 h-3.5" />}
                            <span>
                              {testState.loading ? "Testing..." :
                               testState.ok ? "Connected" :
                               testState.error ? `Failed: ${testState.error.substring(0,25)}...` : "Failed"}
                            </span>
                          </div>
                        )}

                        <button
                          onClick={() => handleTestConnection(conn.id)}
                          disabled={testState?.loading}
                          className="px-3.5 py-1.5 hover:bg-surface-high rounded-xl text-xs font-bold text-on-surface transition-colors border border-surface-high flex items-center gap-1.5"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${testState?.loading ? 'animate-spin' : ''}`} /> Test
                        </button>

                        <button
                          onClick={() => toggleConfigs(conn.id)}
                          className="px-3 py-1.5 hover:bg-surface-high rounded-xl text-xs font-bold text-on-surface-variant hover:text-on-surface transition-colors border border-surface-high flex items-center gap-1"
                        >
                          Rules ({conn.column_encryption_configs?.length || 0})
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>

                        <button
                          onClick={() => handleDeleteConnection(conn.id)}
                          className="p-2.5 text-on-surface-variant hover:text-error hover:bg-error/10 rounded-xl transition-all border border-transparent hover:border-error/20"
                          title="Delete Connection"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Expandable encryption rules */}
                    {isExpanded && (
                      <div className="bg-surface/30 border border-surface-high rounded-xl p-4 ml-14 animate-in slide-in-from-top-2 duration-300">
                        <div className="flex items-center gap-2 mb-3">
                          <Key className="w-4 h-4 text-primary-neon" />
                          <h4 className="text-xs uppercase font-bold tracking-wider text-on-surface">Active Encryption Rules</h4>
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
                                  <th className="pb-2">Encryption Algorithm</th>
                                  <th className="pb-2">Created</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-surface-high/30">
                                {conn.column_encryption_configs.map((config) => (
                                  <tr key={config.id} className="text-on-surface/90">
                                    <td className="py-2">{config.table_name}</td>
                                    <td className="py-2 text-primary-neon">{config.column_name}</td>
                                    <td className="py-2 text-primary-container">AES-256-GCM</td>
                                    <td className="py-2 text-[10px] text-on-surface-variant">{new Date(config.created_at).toLocaleString()}</td>
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
        </div>
      )}
    </div>
  );
}
