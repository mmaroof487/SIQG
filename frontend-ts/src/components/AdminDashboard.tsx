import { useState, useEffect, useRef } from 'react';
import { RefreshCw, Trash2, ShieldAlert, Filter, CheckCircle, Database, Download, ChevronDown, Activity, Users, Shield, Clock, AlertTriangle, Network, Search, FileText, Zap, Key } from 'lucide-react';
import apiClient from '../utils/api';

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  
  // Data States
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [slowQueries, setSlowQueries] = useState<any[]>([]);
  const [budget, setBudget] = useState<any>(null);
  const [whitelist, setWhitelist] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [rbacPolicies, setRbacPolicies] = useState<any[]>([]);
  
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState("");

  // Sub-states
  const [ipAddress, setIpAddress] = useState('');
  const [ipAction, setIpAction] = useState('block');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  
  // Export Dropdown
  const [isExportOpen, setIsExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (exportRef.current && !exportRef.current.contains(event.target as Node)) {
        setIsExportOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    setFetchError("");
    try {
      const requests: Promise<any>[] = [];
      
      const fetchAudit = apiClient.get('/admin/audit').then(res => { const d = res.data.items || res.data; setAuditLogs(Array.isArray(d) ? d : []); });
      const fetchSlow = apiClient.get('/admin/slow-queries').then(res => { const d = res.data.items || res.data; setSlowQueries(Array.isArray(d) ? d : []); });
      const fetchBudget = apiClient.get('/admin/budget').then(res => setBudget(res.data));
      const fetchUsers = apiClient.get('/admin/users').then(res => { const d = res.data.users || res.data; setUsers(Array.isArray(d) ? d : []); });
      const fetchPolicies = apiClient.get('/admin/rbac-policies').then(res => { const d = res.data.items || res.data; setRbacPolicies(Array.isArray(d) ? d : []); });
      const fetchWhitelist = apiClient.get('/admin/whitelist').then(res => { const d = res.data.items || res.data; setWhitelist(Array.isArray(d) ? d : []); });

      if (activeTab === 'overview') {
        requests.push(fetchAudit, fetchSlow, fetchBudget, fetchUsers);
      } else if (activeTab === 'security') {
        requests.push(fetchAudit, fetchPolicies);
      } else if (activeTab === 'usage') {
        requests.push(fetchSlow, fetchBudget);
      } else if (activeTab === 'access') {
        requests.push(fetchUsers, fetchWhitelist);
      }

      await Promise.all(requests);
    } catch (err: any) {
      console.error(`Failed to fetch data for ${activeTab}:`, err);
      if (err.response?.status === 403) {
        setFetchError("You do not have administrative privileges to view this section.");
      } else {
        setFetchError("An error occurred while fetching data.");
      }
    }
    setLoading(false);
  };

  const handleExport = async (format: string, type: string) => {
    setIsExportOpen(false);
    try {
      const res = await apiClient.get('/admin/compliance-report', {
        params: { period: '30d', format },
        responseType: 'blob'
      });
      const blob = new Blob([res.data], { type: format === 'csv' ? 'text/csv' : 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${type}-report-30d.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error(`Export failed:`, err);
      alert("Failed to export report.");
    }
  };

  const handleIpRule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.post('/admin/ip-rules', { ip_address: ipAddress, rule_type: ipAction });
      alert(`IP ${ipAddress} ${ipAction}ed successfully.`);
      setIpAddress('');
    } catch (err) {
      console.error(err);
    }
  };

  const removeWhitelist = async (fingerprint: string) => {
    if (!window.confirm('Remove this query from whitelist?')) return;
    try {
      await apiClient.delete(`/admin/whitelist/${fingerprint}`);
      fetchData();
    } catch (err) {
      console.error('Failed to remove whitelist:', err);
    }
  };

  const deleteUser = async (userId: string) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    try {
      await apiClient.delete(`/admin/users/${userId}`);
      fetchData();
    } catch (err) {
      console.error('Failed to delete user:', err);
    }
  };

  const blockedQueriesCount = Array.isArray(auditLogs) ? auditLogs.filter(l => l?.status === 'error').length : 0;
  const policyViolationsCount = Array.isArray(auditLogs) ? auditLogs.filter(l => l?.status === 'denied').length : 0;
  const failedAuthCount = Array.isArray(auditLogs) ? auditLogs.filter(l => l?.query_type === 'auth' && l?.status === 'error').length : 0;

  const topUsers = Array.isArray(auditLogs) ? auditLogs.reduce((acc, log) => {
    const user = log?.user_id || 'anonymous';
    acc[user] = (acc[user] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) : {};
  const sortedTopUsers = Object.entries(topUsers).sort((a, b) => (b[1] as number) - (a[1] as number)).slice(0, 3);

  const filteredLogs = Array.isArray(auditLogs) ? auditLogs.filter(log => {
      if (filterStatus !== 'all' && log?.status !== filterStatus) return false;
      return true;
  }) : [];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
        <div className="flex items-center gap-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-error/20 to-primary-container/5 border border-error/30 flex items-center justify-center shadow-[0_0_20px_rgba(255,113,108,0.15)] backdrop-blur-xl">
            <ShieldAlert className="w-8 h-8 text-error drop-shadow-[0_0_8px_#ff716c]" />
          </div>
          <div>
            <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Security & Governance</h1>
            <p className="text-on-surface-variant font-medium">Monitor usage, investigate risks, and manage access.</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 bg-surface/60 border border-surface-high hover:border-primary-neon/50 text-on-surface rounded-xl transition-colors font-bold uppercase tracking-wider text-xs group"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-primary-neon ${loading ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
            Refresh
          </button>

          <div className="relative" ref={exportRef}>
            <button
              onClick={() => setIsExportOpen(!isExportOpen)}
              className="flex items-center justify-between gap-2 bg-primary-neon/10 hover:bg-primary-neon/20 border border-primary-neon/30 text-primary-neon rounded-xl text-xs font-bold uppercase tracking-wider px-4 py-2.5 transition-all shadow-[0_0_15px_rgba(0,255,157,0.15)]"
            >
              <Download className="w-4 h-4" />
              Export Report
              <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isExportOpen ? 'rotate-180' : ''}`} />
            </button>
            {isExportOpen && (
              <div className="absolute top-full right-0 mt-2 w-48 bg-surface border border-surface-high rounded-xl shadow-2xl z-50 overflow-hidden py-1 animate-in fade-in slide-in-from-top-2">
                <div className="px-3 py-2 text-[10px] font-bold text-on-surface-variant uppercase tracking-wider border-b border-surface-high/50">Report Type</div>
                <button onClick={() => handleExport('csv', 'audit')} className="w-full text-left px-4 py-2 text-xs font-bold text-on-surface hover:bg-surface-high/50 hover:text-primary-neon flex items-center gap-2 transition-colors">
                  <FileText className="w-3.5 h-3.5" /> Audit (CSV)
                </button>
                <button onClick={() => handleExport('json', 'security')} className="w-full text-left px-4 py-2 text-xs font-bold text-on-surface hover:bg-surface-high/50 hover:text-primary-neon flex items-center gap-2 transition-colors">
                  <FileText className="w-3.5 h-3.5" /> Security (JSON)
                </button>
                <button onClick={() => handleExport('csv', 'usage')} className="w-full text-left px-4 py-2 text-xs font-bold text-on-surface hover:bg-surface-high/50 hover:text-primary-neon flex items-center gap-2 transition-colors">
                  <FileText className="w-3.5 h-3.5" /> Usage (CSV)
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex gap-2 overflow-x-auto pb-2 border-b border-surface-high scrollbar-hide">
        {[
          { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
          { id: 'security', label: 'Security', icon: <Shield className="w-4 h-4" /> },
          { id: 'usage', label: 'Usage & Performance', icon: <Clock className="w-4 h-4" /> },
          { id: 'access', label: 'Access Control', icon: <Users className="w-4 h-4" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-3 rounded-t-xl font-bold uppercase tracking-wider text-sm transition-all whitespace-nowrap flex items-center gap-2 ${
              activeTab === tab.id
                ? 'bg-surface-high/50 text-primary-neon border-b-2 border-primary-neon shadow-[inset_0_-2px_8px_rgba(0,255,157,0.1)]'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-high/30 border-b-2 border-transparent'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl shadow-lg ring-1 ring-white/5 overflow-hidden">
        {loading && <div className="h-1 bg-primary-neon/20 overflow-hidden"><div className="h-full bg-primary-neon w-1/3 animate-pulse"></div></div>}
        
        {fetchError && (
          <div className="m-6 p-4 bg-error/10 border border-error/30 text-error rounded-xl flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm font-medium">{fetchError}</span>
          </div>
        )}

        {/* 1. OVERVIEW TAB */}
        {!fetchError && activeTab === 'overview' && (
          <div className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Security Health */}
              <div className="bg-surface-high/20 border border-surface-high rounded-xl p-5 col-span-1 md:col-span-2 lg:col-span-1 flex flex-col justify-between group hover:border-primary-neon/30 transition-colors">
                <div>
                  <div className="flex items-center gap-2 text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-4">
                    <Shield className="w-3.5 h-3.5" /> Security Health
                  </div>
                  <div className="text-5xl font-black text-primary-neon drop-shadow-[0_0_15px_rgba(0,255,157,0.3)]">98<span className="text-2xl text-on-surface-variant/50">/100</span></div>
                </div>
                <div className="mt-6 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-on-surface-variant">Blocked Queries</span>
                    <span className="font-bold text-error">{blockedQueriesCount}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-on-surface-variant">Policy Violations</span>
                    <span className="font-bold text-error">{policyViolationsCount}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-on-surface-variant">Failed Auth</span>
                    <span className="font-bold text-error">{failedAuthCount}</span>
                  </div>
                </div>
              </div>

              {/* Activity Timeline */}
              <div className="bg-surface-high/20 border border-surface-high rounded-xl p-5 col-span-1 md:col-span-2">
                <div className="flex items-center gap-2 text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-4">
                  <Activity className="w-3.5 h-3.5" /> Activity Timeline
                </div>
                <div className="space-y-4">
                  {Array.isArray(auditLogs) && auditLogs.slice(0, 4).map((log: any, idx) => (
                    <div key={idx} className="flex items-center gap-4 relative">
                      {idx !== 3 && <div className="absolute left-[7px] top-6 bottom-0 w-px bg-surface-high"></div>}
                      <div className={`w-4 h-4 rounded-full flex-shrink-0 z-10 border-2 border-surface ${log.status === 'error' ? 'bg-error' : 'bg-primary-neon'}`}></div>
                      <div className="flex-1 flex justify-between items-center bg-surface-high/30 px-3 py-2 rounded-lg border border-surface-high/50">
                        <div className="text-sm font-medium text-on-surface">
                          {log.status === 'error' ? `Blocked ${log.query_type}` : `Allowed ${log.query_type}`}
                        </div>
                        <div className="text-xs font-mono text-on-surface-variant">
                          User: <span className="text-primary-neon">{log.user_id}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {(!Array.isArray(auditLogs) || auditLogs.length === 0) && <div className="text-sm text-on-surface-variant py-4">No recent activity.</div>}
                </div>
              </div>

              {/* Top Users & Budget */}
              <div className="space-y-6 col-span-1 md:col-span-2 lg:col-span-1">
                <div className="bg-surface-high/20 border border-surface-high rounded-xl p-5">
                  <div className="flex items-center gap-2 text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-4">
                    <Users className="w-3.5 h-3.5" /> Top Users Today
                  </div>
                  <div className="space-y-3">
                    {sortedTopUsers.map(([user, count], idx) => (
                      <div key={idx} className="flex justify-between items-center text-sm">
                        <span className="text-on-surface font-medium truncate">{user}</span>
                        <span className="font-mono text-primary-neon text-xs">{count as number} queries</span>
                      </div>
                    ))}
                    {sortedTopUsers.length === 0 && <span className="text-xs text-on-surface-variant">No user activity recorded.</span>}
                  </div>
                </div>

                <div className="bg-surface-high/20 border border-surface-high rounded-xl p-5">
                  <div className="flex items-center gap-2 text-[10px] uppercase font-bold tracking-wider text-on-surface-variant mb-4">
                    <Database className="w-3.5 h-3.5" /> Budget Consumption
                  </div>
                  <div className="mb-2 flex justify-between items-end">
                    <span className="text-2xl font-black text-on-surface">{budget?.current_usage || 0}</span>
                    <span className="text-xs text-on-surface-variant mb-1">/ {budget?.daily_budget || 1000}</span>
                  </div>
                  <div className="h-2 bg-surface-high rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${(budget?.current_usage || 0) > (budget?.daily_budget || 1000) * 0.8 ? 'bg-error' : 'bg-primary-neon'}`} 
                      style={{ width: `${Math.min(((budget?.current_usage || 0) / (budget?.daily_budget || 1000)) * 100, 100)}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 2. SECURITY TAB */}
        {!fetchError && activeTab === 'security' && (
          <div className="p-6 space-y-8">
            {/* Threat Feed & Policies row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Threat Feed (Cards) */}
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface flex items-center gap-2 mb-4 border-b border-surface-high pb-2">
                  <AlertTriangle className="w-4 h-4 text-error" /> Threat Feed
                </h3>
                <div className="space-y-3">
                  {Array.isArray(auditLogs) && auditLogs.filter(l => l?.status === 'error').slice(0, 3).map((log: any, idx) => (
                    <div key={idx} className="bg-error/5 border border-error/20 p-4 rounded-xl flex items-start gap-3">
                      <ShieldAlert className="w-5 h-5 text-error mt-0.5" />
                      <div>
                        <div className="text-sm font-bold text-on-surface">Privilege Escalation Blocked</div>
                        <div className="text-xs text-on-surface-variant mt-1">User <span className="font-mono text-error">{log.user_id}</span> attempted restricted <span className="font-mono">{log.query_type}</span> action.</div>
                      </div>
                    </div>
                  ))}
                  {(!Array.isArray(auditLogs) || auditLogs.filter(l => l?.status === 'error').length === 0) && (
                    <div className="p-6 text-center border border-surface-high border-dashed rounded-xl text-primary-neon/80 text-xs font-mono uppercase tracking-wider">
                      <CheckCircle className="w-5 h-5 mx-auto mb-2 opacity-50" />
                      No threats detected
                    </div>
                  )}
                </div>
              </div>

              {/* IP Rules Form */}
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface flex items-center gap-2 mb-4 border-b border-surface-high pb-2">
                  <Network className="w-4 h-4 text-primary-container" /> IP Rules Configuration
                </h3>
                <div className="bg-surface-high/10 border border-surface-high rounded-xl p-5">
                  <form onSubmit={handleIpRule} className="flex flex-col gap-3">
                    <input type="text" value={ipAddress} onChange={(e) => setIpAddress(e.target.value)} placeholder="IP Address (e.g., 192.168.1.5)" className="bg-surface border border-surface-high text-on-surface px-4 py-2.5 rounded-lg outline-none focus:border-primary-neon/50 transition-colors text-sm" required />
                    <div className="flex gap-3">
                      <select value={ipAction} onChange={(e) => setIpAction(e.target.value)} className="flex-1 bg-surface border border-surface-high text-on-surface px-4 py-2.5 rounded-lg cursor-pointer outline-none focus:border-primary-neon/50 text-sm">
                        <option value="block">Block Access</option>
                        <option value="allow">Whitelist / Allow</option>
                      </select>
                      <button type="submit" className="bg-primary-neon/10 hover:bg-primary-neon/20 text-primary-neon border border-primary-neon/30 px-6 py-2.5 rounded-lg font-bold uppercase tracking-wider transition-colors text-xs">Apply Rule</button>
                    </div>
                  </form>
                  <div className="mt-4 flex gap-2 text-[10px] uppercase font-bold text-on-surface-variant">
                    <span className="px-2 py-1 bg-error/10 text-error rounded border border-error/20">Blocked</span>
                    <span className="px-2 py-1 bg-primary-neon/10 text-primary-neon rounded border border-primary-neon/20">Allowed</span>
                    <span className="px-2 py-1 bg-surface-high text-on-surface rounded border border-surface-high/50">Rate Limited</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Blocked Queries */}
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface flex items-center gap-2 mb-4 border-b border-surface-high pb-2">
                  <Filter className="w-4 h-4 text-on-surface-variant" /> Blocked Queries
                </h3>
                <div className="border border-surface-high rounded-xl overflow-hidden">
                  <table className="w-full text-left">
                    <tbody className="divide-y divide-surface-high/50 bg-surface/30">
                      {Array.isArray(auditLogs) && auditLogs.filter(l => l?.status === 'error').slice(0, 5).map((log: any) => (
                        <tr key={log.trace_id} className="hover:bg-surface-high/30 transition-colors">
                          <td className="p-3">
                            <div className="font-mono text-xs text-primary-container bg-surface-high/50 px-2 py-1 rounded inline-block mb-1">{log.query_type}</div>
                            <div className="text-xs text-on-surface-variant font-mono truncate max-w-xs">{log.trace_id}</div>
                          </td>
                          <td className="p-3 text-right">
                            <span className="px-2 py-1 bg-error/10 text-error border border-error/20 rounded text-[10px] font-bold uppercase tracking-wider">Blocked</span>
                          </td>
                        </tr>
                      ))}
                      {(!Array.isArray(auditLogs) || auditLogs.filter(l => l?.status === 'error').length === 0) && (
                        <tr><td colSpan={2} className="p-4 text-center text-xs text-on-surface-variant font-mono">No blocked queries recorded.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Policies */}
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface flex items-center gap-2 mb-4 border-b border-surface-high pb-2">
                  <ShieldAlert className="w-4 h-4 text-on-surface-variant" /> Policies (RBAC)
                </h3>
                <div className="border border-surface-high rounded-xl overflow-hidden">
                  <table className="w-full text-left">
                    <tbody className="divide-y divide-surface-high/50 bg-surface/30">
                      {Array.isArray(rbacPolicies) && rbacPolicies.map((policy: any) => (
                        <tr key={policy.role} className="hover:bg-surface-high/30 transition-colors">
                          <td className="p-3">
                            <div className="font-bold text-on-surface text-sm">{policy.role}</div>
                            <div className="text-xs text-on-surface-variant mt-1">Limits: {policy.allowed_hours} | Tables: {policy.allowed_tables?.length || 'All'}</div>
                          </td>
                          <td className="p-3 text-right">
                            <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${policy.priority === 'High' ? 'bg-error/10 text-error border border-error/20' : 'bg-surface-high text-on-surface'}`}>
                              {policy.priority} Priority
                            </span>
                          </td>
                        </tr>
                      ))}
                      {(!Array.isArray(rbacPolicies) || rbacPolicies.length === 0) && (
                        <tr><td colSpan={2} className="p-4 text-center text-xs text-on-surface-variant font-mono">No policies loaded.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 3. USAGE & PERFORMANCE TAB */}
        {!fetchError && activeTab === 'usage' && (
          <div className="p-6 space-y-8">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Budget Overview */}
              <div className="lg:col-span-1 space-y-4">
                <div className="bg-surface-high/20 border border-surface-high rounded-xl p-5">
                  <h3 className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-4 flex items-center gap-2">
                    <Database className="w-3.5 h-3.5" /> Budget Forecast
                  </h3>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center border-b border-surface-high/50 pb-2">
                      <span className="text-sm text-on-surface">Consumed</span>
                      <span className="font-mono text-error font-bold">{budget?.current_usage || 0}</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-surface-high/50 pb-2">
                      <span className="text-sm text-on-surface">Remaining</span>
                      <span className="font-mono text-primary-neon font-bold">{budget?.remaining || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-on-surface">Total Quota</span>
                      <span className="font-mono text-on-surface-variant">{budget?.daily_budget || 0}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-surface-high/20 border border-surface-high rounded-xl p-5">
                   <h3 className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-4 flex items-center gap-2">
                    <Zap className="w-3.5 h-3.5" /> Latency & Cache Metrics
                  </h3>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between items-center bg-surface px-3 py-2 rounded border border-surface-high/50">
                      <span className="text-on-surface-variant">P95 Latency</span>
                      <span className="font-mono text-error">~120ms</span>
                    </div>
                    <div className="flex justify-between items-center bg-surface px-3 py-2 rounded border border-surface-high/50">
                      <span className="text-on-surface-variant">Cache Hit Ratio</span>
                      <span className="font-mono text-primary-neon">84.2%</span>
                    </div>
                    <div className="flex justify-between items-center bg-surface px-3 py-2 rounded border border-surface-high/50">
                      <span className="text-on-surface-variant">Queries/hour</span>
                      <span className="font-mono text-on-surface">1,402</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Expensive / Slow Queries */}
              <div className="lg:col-span-2">
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface flex items-center gap-2 mb-4 border-b border-surface-high pb-2">
                  <Clock className="w-4 h-4 text-error" /> Expensive Queries (Top 10)
                </h3>
                <div className="space-y-3">
                  {Array.isArray(slowQueries) && slowQueries.slice(0, 10).map((query: any) => (
                    <div key={query.trace_id} className="bg-surface border border-surface-high rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                      <div>
                        <div className="font-mono text-xs text-on-surface-variant bg-surface-high/50 px-2 py-1 rounded inline-block mb-2">
                          {query.query_fingerprint || query.trace_id}
                        </div>
                        <div className="flex gap-4 text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                          <span>Scanned: <span className="text-on-surface">{query.rows_scanned || 'N/A'}</span></span>
                          <span>Strategy: <span className="text-primary-neon">{query.scan_type || 'Seq Scan'}</span></span>
                        </div>
                      </div>
                      <div className="text-2xl font-black text-error drop-shadow-[0_0_5px_rgba(255,113,108,0.3)]">
                        {query.latency_ms}ms
                      </div>
                    </div>
                  ))}
                  {(!Array.isArray(slowQueries) || slowQueries.length === 0) && <div className="text-center py-12 text-primary-neon/80 font-mono text-sm tracking-wider flex items-center justify-center gap-2"><CheckCircle className="w-4 h-4"/> No expensive queries detected</div>}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 4. ACCESS CONTROL TAB */}
        {!fetchError && activeTab === 'access' && (
          <div className="p-6 space-y-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Users & Roles */}
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface flex items-center gap-2 mb-4 border-b border-surface-high pb-2">
                  <Users className="w-4 h-4 text-primary-container" /> Users & Roles
                </h3>
                <div className="border border-surface-high rounded-xl overflow-hidden">
                  <table className="w-full text-left">
                    <thead className="bg-surface-high/50 border-b border-surface-high">
                      <tr>
                        <th className="p-3 text-xs font-bold text-on-surface-variant uppercase tracking-wider">User</th>
                        <th className="p-3 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Role</th>
                        <th className="p-3 text-right"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-high/50 bg-surface/30">
                      {Array.isArray(users) && users.length > 0 ? users.map((user: any) => (
                        <tr key={user.id} className="hover:bg-surface-high/30 transition-colors">
                          <td className="p-3 font-medium text-sm text-on-surface">{user.username || user.email || user.id}</td>
                          <td className="p-3">
                            <span className="px-2 py-1 bg-primary-container/10 text-primary-container border border-primary-container/20 rounded text-[10px] font-bold uppercase tracking-wider">
                              {user.role || 'user'}
                            </span>
                          </td>
                          <td className="p-3 text-right">
                            <button onClick={() => deleteUser(user.id)} className="p-1.5 rounded-lg text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      )) : (
                        <tr><td colSpan={3} className="p-6 text-center text-xs text-on-surface-variant">No users found</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Query Whitelist */}
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface flex items-center gap-2 mb-4 border-b border-surface-high pb-2">
                  <ShieldAlert className="w-4 h-4 text-primary-neon" /> Query Whitelist
                </h3>
                <div className="space-y-3">
                  {Array.isArray(whitelist) && whitelist.map((item: any) => (
                    <div key={item.query_fingerprint} className="bg-surface border border-surface-high rounded-xl p-4 flex justify-between items-center group hover:border-primary-neon/30 transition-colors">
                      <div>
                        <div className="font-mono text-xs text-primary-neon font-bold mb-1">{item.query_fingerprint}</div>
                        {item.description && <div className="text-[10px] text-on-surface-variant uppercase tracking-wider">{item.description}</div>}
                      </div>
                      <button onClick={() => removeWhitelist(item.query_fingerprint)} className="p-2 rounded-lg text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors opacity-0 group-hover:opacity-100">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                  {(!Array.isArray(whitelist) || whitelist.length === 0) && (
                    <div className="p-6 text-center border border-surface-high border-dashed rounded-xl text-on-surface-variant text-xs font-mono uppercase tracking-wider">
                      No whitelisted queries
                    </div>
                  )}
                </div>
              </div>
            </div>
            
          </div>
        )}
      </div>
    </div>
  );
}
