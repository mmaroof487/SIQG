import { useState, useEffect } from "react";
import { Settings2, User, Wallet, History, AlertCircle, Key, Activity, ArrowRight, CheckCircle, ShieldAlert, LogOut } from "lucide-react";
import { api } from "../utils/api";

export default function SettingsPage() {
  const [budget, setBudget] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getBudget().catch(() => ({ data: null })),
      api.getUserHistory(10, 0).catch(() => ({ data: [] }))
    ]).then(([budgetRes, historyRes]) => {
      if (budgetRes?.data) setBudget(budgetRes.data);
      if (historyRes?.data) setHistory(historyRes.data);
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto">
      {/* Header Profile Area */}
      <div className="relative overflow-hidden bg-surface/60 backdrop-blur-xl border border-surface-high p-8 rounded-3xl shadow-lg ring-1 ring-white/5 flex items-center justify-between">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary-neon/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>
        <div className="flex items-center gap-6 relative z-10">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border-2 border-primary-neon/30 flex items-center justify-center shadow-[0_0_30px_rgba(0,255,157,0.15)] backdrop-blur-xl">
            <User className="w-10 h-10 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
          </div>
          <div>
            <h1 className="text-3xl font-black text-on-surface mb-1 tracking-tight">Data Scientist Profile</h1>
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 bg-surface-high rounded-full text-xs font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5" /> Researcher
              </span>
              <span className="text-on-surface-variant/50 text-sm">Member since 2024</span>
            </div>
          </div>
        </div>
        <div className="relative z-10 flex gap-3">
          <button className="px-6 py-2.5 bg-surface-high hover:bg-surface-high/80 text-on-surface font-bold tracking-wider uppercase text-sm rounded-xl transition-all border border-surface-high flex items-center gap-2">
            <Settings2 className="w-4 h-4" /> Edit Profile
          </button>
          <button 
            onClick={() => {
              api.logout();
              window.location.reload();
            }}
            className="px-6 py-2.5 bg-error/10 hover:bg-error/20 text-error font-bold tracking-wider uppercase text-sm rounded-xl transition-all border border-error/20 flex items-center gap-2"
          >
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Budget & Keys */}
        <div className="space-y-8">
          {/* Budget Widget */}
          <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-3xl p-6 shadow-lg relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-primary-neon/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="flex items-center gap-3 mb-6 relative z-10">
              <div className="p-2 bg-primary-neon/10 rounded-lg">
                <Wallet className="w-5 h-5 text-primary-neon" />
              </div>
              <h2 className="text-lg font-bold text-on-surface">Compute Budget</h2>
            </div>
            
            {loading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-8 bg-surface-high rounded w-1/2"></div>
                <div className="h-2 bg-surface-high rounded w-full"></div>
              </div>
            ) : budget ? (
              <div className="relative z-10 space-y-5">
                <div>
                  <div className="flex justify-between items-end mb-1">
                    <span className="text-sm font-medium text-on-surface-variant">Remaining Capacity</span>
                    <span className="text-2xl font-black text-primary-neon">{budget.remaining.toLocaleString()}</span>
                  </div>
                  <div className="w-full bg-surface-high/50 rounded-full h-2 overflow-hidden flex">
                    <div className="bg-primary-neon h-full rounded-full transition-all duration-1000" style={{ width: `${Math.min(100, (budget.current_usage / budget.daily_budget) * 100)}%` }}></div>
                  </div>
                </div>
                <div className="flex justify-between text-xs font-mono text-on-surface-variant bg-surface-high/20 p-3 rounded-xl border border-surface-high/50">
                  <div className="flex flex-col">
                    <span className="uppercase tracking-wider opacity-60 mb-0.5">Used</span>
                    <span className="text-on-surface font-bold text-sm">{budget.current_usage.toLocaleString()}</span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="uppercase tracking-wider opacity-60 mb-0.5">Limit</span>
                    <span className="text-on-surface font-bold text-sm">{budget.daily_budget.toLocaleString()}</span>
                  </div>
                </div>
                <div className="text-xs text-center text-on-surface-variant/60">
                  Resets {new Date(budget.resets_at).toLocaleDateString()}
                </div>
              </div>
            ) : (
              <div className="text-error text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> Unavailable
              </div>
            )}
          </div>

          {/* API Keys Widget */}
          <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-3xl p-6 shadow-lg">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary-container/10 rounded-lg">
                  <Key className="w-5 h-5 text-primary-container" />
                </div>
                <h2 className="text-lg font-bold text-on-surface">API Access</h2>
              </div>
            </div>
            <p className="text-sm text-on-surface-variant mb-6">Create programmatic access keys to query Argus via REST API.</p>
            
            <div className="space-y-3 mb-6">
              <div className="bg-surface-high/20 border border-surface-high p-3 rounded-xl flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-primary-neon"></div>
                  <div>
                    <div className="text-sm font-bold text-on-surface">Production Analytics</div>
                    <div className="text-xs text-on-surface-variant font-mono">sk_prod_...8f92</div>
                  </div>
                </div>
                <span className="text-xs font-medium text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity">Active</span>
              </div>
            </div>

            <button className="w-full py-3 bg-primary-container/10 hover:bg-primary-container/20 text-primary-container font-bold tracking-wider uppercase text-xs rounded-xl transition-all border border-primary-container/20">
              Generate New Key
            </button>
          </div>
        </div>

        {/* Right Column: Query History */}
        <div className="lg:col-span-2 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-3xl p-6 shadow-lg flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-surface-high rounded-lg">
                <Activity className="w-5 h-5 text-on-surface" />
              </div>
              <h2 className="text-lg font-bold text-on-surface">Recent Activity</h2>
            </div>
            <button className="text-xs font-bold uppercase tracking-wider text-primary-neon hover:text-primary-neon/80 flex items-center gap-1 transition-colors">
              View All <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto pr-2 -mr-2 space-y-3">
            {loading ? (
              <div className="space-y-3">
                {[1,2,3,4].map(i => (
                  <div key={i} className="h-16 bg-surface-high/50 rounded-xl animate-pulse"></div>
                ))}
              </div>
            ) : history.length > 0 ? (
              history.map((log: any) => (
                <div key={log.trace_id} className="bg-surface-high/20 border border-surface-high p-4 rounded-xl flex items-center gap-4 hover:bg-surface-high/40 transition-colors">
                  <div className="shrink-0">
                    {log.status === 'success' ? (
                      <div className="w-10 h-10 rounded-full bg-primary-neon/10 flex items-center justify-center border border-primary-neon/20">
                        <CheckCircle className="w-4 h-4 text-primary-neon" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-error/10 flex items-center justify-center border border-error/20">
                        <ShieldAlert className="w-4 h-4 text-error" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono font-bold text-on-surface-variant uppercase tracking-wider">{log.query_type}</span>
                      <span className="text-xs text-on-surface-variant/60">{new Date(log.created_at).toLocaleTimeString()}</span>
                    </div>
                    <div className="text-sm text-on-surface font-medium truncate" title={log.query_preview}>
                      {log.query_preview || <span className="opacity-50 italic">No query body</span>}
                    </div>
                  </div>
                  <div className="shrink-0 text-right hidden sm:block">
                    <div className="text-xs font-mono text-primary-container font-bold mb-1">{log.latency_ms?.toFixed(1)}ms</div>
                    <div className="text-xs text-on-surface-variant font-medium">{log.cost ? `Cost: ${log.cost}` : 'No cost'}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-on-surface-variant py-12">
                <History className="w-12 h-12 mb-4 opacity-20" />
                <p className="font-medium">No recent query activity.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
