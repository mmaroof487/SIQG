import { useState, useEffect } from "react";
import { 
  Settings2, User, Wallet, History, AlertCircle, Key, Activity, 
  ArrowRight, CheckCircle, ShieldAlert, LogOut, Database, 
  Zap, BarChart2, Shield, Clock 
} from "lucide-react";
import { api } from "../utils/api";
import { useAuth } from "../contexts/AuthContext";
import { Link } from "react-router-dom";

export default function SettingsPage() {
  const { role, logout } = useAuth();
  const username = role === 'admin' ? 'Administrator' : 'User';
  const [budget, setBudget] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getBudget().catch(() => ({ data: null })),
      api.getUserHistory(10, 0).catch(() => ({ data: [] }))
    ]).then(([budgetRes, historyRes]) => {
      if (budgetRes?.data) setBudget(budgetRes.data);
      if (historyRes?.data?.history) {
        setHistory(historyRes.data.history);
      } else if (Array.isArray(historyRes?.data)) {
        setHistory(historyRes.data);
      }
    }).finally(() => setLoading(false));
  }, []);

  const queriesToday = history.length; // Approximate from recent history
  const budgetUsedPercent = budget && budget.daily_budget > 0 
    ? Math.min(100, Math.round((budget.current_usage / budget.daily_budget) * 100)) 
    : 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-6xl mx-auto pb-12">
      {/* --- TOP: Profile Header --- */}
      <div className="relative overflow-hidden bg-surface/60 backdrop-blur-xl border border-surface-high p-8 rounded-3xl shadow-lg ring-1 ring-white/5 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary-neon/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>
        <div className="flex items-center gap-6 relative z-10">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border-2 border-primary-neon/30 flex items-center justify-center shadow-[0_0_30px_rgba(0,255,157,0.15)] backdrop-blur-xl shrink-0">
            <User className="w-10 h-10 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
          </div>
          <div>
            <h1 className="text-3xl font-black text-on-surface mb-2 tracking-tight">{username}</h1>
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1 bg-surface-high rounded-full text-[10px] font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-1.5">
                <ShieldAlert className="w-3 h-3" /> {role || 'Member'}
              </span>
              <span className="px-3 py-1 bg-primary-neon/10 border border-primary-neon/20 rounded-full text-[10px] font-bold uppercase tracking-wider text-primary-neon flex items-center gap-1.5">
                <Zap className="w-3 h-3" /> Default Tier
              </span>
              <span className="text-on-surface-variant/50 text-xs font-medium ml-2">Active</span>
            </div>
          </div>
        </div>
        <div className="relative z-10 flex flex-wrap gap-3">
          <button className="px-4 py-2 bg-surface-high hover:bg-surface-high/80 text-on-surface font-bold tracking-wider uppercase text-xs rounded-xl transition-all border border-surface-high flex items-center gap-2">
            <Settings2 className="w-3.5 h-3.5" /> Edit Profile
          </button>
          <button 
            onClick={() => {
              api.logout().finally(() => {
                logout();
              });
            }}
            className="px-4 py-2 bg-error/10 hover:bg-error/20 text-error font-bold tracking-wider uppercase text-xs rounded-xl transition-all border border-error/20 flex items-center gap-2"
          >
            <LogOut className="w-3.5 h-3.5" /> Logout
          </button>
        </div>
      </div>

      {/* --- ROW 2: KPI Cards --- */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-5 rounded-2xl shadow-sm flex flex-col justify-between group">
          <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 flex items-center justify-between">
            <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5" /> Recent Queries</span>
          </div>
          <div className="text-3xl font-black text-on-surface">{loading ? "..." : queriesToday}</div>
        </div>
        
        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-5 rounded-2xl shadow-sm flex flex-col justify-between group">
          <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 flex items-center justify-between">
            <span className="flex items-center gap-1.5"><Wallet className="w-3.5 h-3.5" /> Budget Used</span>
          </div>
          <div className="text-3xl font-black text-primary-neon">{loading ? "..." : `${budgetUsedPercent}%`}</div>
        </div>

        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-5 rounded-2xl shadow-sm flex flex-col justify-between group">
          <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 flex items-center justify-between">
            <span className="flex items-center gap-1.5"><Key className="w-3.5 h-3.5" /> API Keys</span>
          </div>
          <div className="text-xl font-black text-on-surface-variant opacity-50">Coming Soon</div>
        </div>

        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high p-5 rounded-2xl shadow-sm flex flex-col justify-between group">
          <div className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-3 flex items-center justify-between">
            <span className="flex items-center gap-1.5"><Database className="w-3.5 h-3.5" /> Connected DBs</span>
          </div>
          <div className="text-xl font-black text-on-surface-variant opacity-50">View Connections</div>
        </div>
      </div>

      {/* --- ROW 3: Budget & API Keys --- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Budget Usage */}
        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-3xl p-6 shadow-lg relative overflow-hidden">
          <div className="flex items-center gap-3 mb-6 relative z-10">
            <div className="p-2 bg-primary-neon/10 rounded-lg">
              <Wallet className="w-5 h-5 text-primary-neon" />
            </div>
            <h2 className="text-lg font-bold text-on-surface">Daily Budget</h2>
          </div>
          
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-8 bg-surface-high rounded w-1/2"></div>
              <div className="h-2 bg-surface-high rounded w-full"></div>
            </div>
          ) : budget ? (
            <div className="relative z-10 space-y-6">
              <div>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-3xl font-black text-primary-neon">{budgetUsedPercent}%</span>
                  <span className="text-sm font-medium text-on-surface-variant">Used</span>
                </div>
                <div className="w-full bg-surface-high/50 rounded-full h-3 overflow-hidden flex">
                  <div className="bg-primary-neon h-full rounded-full transition-all duration-1000" style={{ width: `${budgetUsedPercent}%` }}></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-surface-high/20 p-4 rounded-xl border border-surface-high/50 flex flex-col justify-between">
                  <span className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Used</span>
                  <span className="text-xl font-bold text-on-surface">{budget.current_usage.toLocaleString()}</span>
                </div>
                <div className="bg-surface-high/20 p-4 rounded-xl border border-surface-high/50 flex flex-col justify-between">
                  <span className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Remaining</span>
                  <span className="text-xl font-bold text-on-surface">{budget.remaining.toLocaleString()}</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs font-medium text-on-surface-variant px-1">
                <span>Limit: {budget.daily_budget.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <div className="text-error text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" /> Unavailable
            </div>
          )}
        </div>

        {/* Right: API Keys */}
        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-3xl p-6 shadow-lg">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-container/10 rounded-lg">
                <Key className="w-5 h-5 text-primary-container" />
              </div>
              <h2 className="text-lg font-bold text-on-surface">Active API Keys</h2>
            </div>
          </div>
          
          <div className="space-y-3">
            <div className="text-center text-on-surface-variant py-8 border border-dashed border-surface-high rounded-xl bg-surface-high/10">
              <p className="font-medium text-sm">API Key Management coming in v1.1</p>
            </div>
          </div>
        </div>
      </div>

      {/* --- ROW 4: Insights & Security --- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Personal Insights */}
        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-3xl p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-surface-high rounded-lg">
              <BarChart2 className="w-5 h-5 text-on-surface" />
            </div>
            <h2 className="text-lg font-bold text-on-surface">Personal Insights</h2>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
             <div className="text-center text-on-surface-variant py-8 border border-dashed border-surface-high rounded-xl bg-surface-high/10 col-span-2">
                <p className="font-medium text-sm">Analytics Engine currently inactive</p>
             </div>
          </div>
        </div>

        {/* Right: Security */}
        <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-3xl p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-surface-high rounded-lg">
              <Shield className="w-5 h-5 text-on-surface" />
            </div>
            <h2 className="text-lg font-bold text-on-surface">Security & Access</h2>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-start justify-between pb-4 border-b border-surface-high/50">
              <div>
                <div className="text-sm font-bold text-on-surface mb-0.5">Two-Factor Authentication</div>
                <div className="text-xs text-on-surface-variant font-medium">Coming in v1.1</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* --- ROW 5: Recent Activity --- */}
      <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-3xl p-6 shadow-lg flex flex-col">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-surface-high rounded-lg">
              <Clock className="w-5 h-5 text-on-surface" />
            </div>
            <h2 className="text-lg font-bold text-on-surface">Recent Queries</h2>
          </div>
          <Link to="/library" className="text-xs font-bold uppercase tracking-wider text-primary-neon hover:text-primary-neon/80 flex items-center gap-1 transition-colors">
            View Full History <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="space-y-2">
          {loading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => (
                <div key={i} className="h-12 bg-surface-high/50 rounded-xl animate-pulse"></div>
              ))}
            </div>
          ) : history.length > 0 ? (
            history.slice(0, 5).map((log: any) => (
              <div key={log.id} className="bg-surface-high/20 border border-surface-high p-3 rounded-xl flex items-center justify-between hover:bg-surface-high/40 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="shrink-0">
                    <CheckCircle className="w-4 h-4 text-primary-neon" />
                  </div>
                  <div>
                    <div className="text-sm font-mono font-bold text-on-surface truncate max-w-xs">{log.query}</div>
                    <div className="text-[10px] text-on-surface-variant font-medium">
                      {log.rows_returned} rows returned
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono text-on-surface-variant font-medium mb-0.5">{log.execution_time_ms ? log.execution_time_ms.toFixed(1) : 0}ms</div>
                  <div className="text-[10px] text-on-surface-variant/60">{new Date(log.executed_at).toLocaleTimeString()}</div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center text-on-surface-variant py-8 border border-dashed border-surface-high rounded-xl bg-surface-high/10">
              <p className="font-medium text-sm">No recent queries.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
