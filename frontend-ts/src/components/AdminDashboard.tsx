import { useState, useEffect } from 'react';
import { RefreshCw, Trash2, ShieldAlert, Filter, CheckCircle, Database, Download } from 'lucide-react';
import apiClient from '../utils/api';

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('audit');
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [slowQueries, setSlowQueries] = useState<any[]>([]);
  const [budget, setBudget] = useState<any>(null);
  const [whitelist, setWhitelist] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [ipAddress, setIpAddress] = useState('');
  const [ipAction, setIpAction] = useState('block');

  // Filters for Audit Log
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterUser] = useState<string>('');

  // Phase C: Advanced Policies & Compliance Export States
  const [rbacPolicies, setRbacPolicies] = useState<any[]>([]);
  const [compliancePeriod, setCompliancePeriod] = useState('30d');

  const [fetchError, setFetchError] = useState("");

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    setFetchError("");
    try {
      if (activeTab === 'audit') {
        const res = await apiClient.get('/admin/audit');
        setAuditLogs(Array.isArray(res.data) ? res.data : []);
      } else if (activeTab === 'slow') {
        const res = await apiClient.get('/admin/slow-queries');
        setSlowQueries(res.data.items || res.data || []);
      } else if (activeTab === 'budget') {
        const res = await apiClient.get('/admin/budget');
        setBudget(res.data);
      } else if (activeTab === 'whitelist') {
        const res = await apiClient.get('/admin/whitelist');
        setWhitelist(res.data.items || res.data || []);
      } else if (activeTab === 'users') {
        const res = await apiClient.get('/admin/users');
        setUsers(res.data.users || res.data || []);
      } else if (activeTab === 'policies') {
        const res = await apiClient.get('/admin/rbac-policies');
        setRbacPolicies(Array.isArray(res.data) ? res.data : []);
      }
    } catch (err: any) {
      console.error(`Failed to fetch data for ${activeTab}:`, err);
      if (err.response?.status === 403) {
        setFetchError("You do not have administrative privileges to view this section. If your role was recently updated, please log out and log back in to refresh your access token.");
      } else {
        setFetchError("An error occurred while fetching data.");
      }
    }
    setLoading(false);
  };

  const handleExport = async (format: string) => {
    try {
      const res = await apiClient.get('/admin/compliance-report', {
        params: { period: compliancePeriod, format },
        responseType: 'blob'
      });
      const blob = new Blob([res.data], { type: format === 'csv' ? 'text/csv' : 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `compliance-report-${compliancePeriod}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error(`Export failed:`, err);
      alert("Failed to export compliance report.");
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

  const filteredLogs = auditLogs.filter(log => {
      if (filterStatus !== 'all' && log.status !== filterStatus) return false;
      if (filterUser && !String(log.user_id).toLowerCase().includes(filterUser.toLowerCase())) return false;
      return true;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-end gap-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-error/20 to-primary-container/5 border border-error/30 flex items-center justify-center shadow-[0_0_20px_rgba(255,113,108,0.15)] backdrop-blur-xl">
            <ShieldAlert className="w-8 h-8 text-error drop-shadow-[0_0_8px_#ff716c]" />
          </div>
          <div>
            <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Admin Console</h1>
            <p className="text-on-surface-variant font-medium">Gateway compliance, user security, and resource limits</p>
          </div>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 bg-surface-high border border-surface-high hover:border-primary-neon/50 text-on-surface rounded-xl transition-colors font-bold uppercase tracking-wider text-sm group"
        >
          <RefreshCw className={`h-4 w-4 text-primary-neon ${loading ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
          Refresh
        </button>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-2 border-b border-surface-high scrollbar-hide">
        {[
          { id: 'audit', label: 'Audit Logs' },
          { id: 'slow', label: 'Slow Queries' },
          { id: 'budget', label: 'Budget Usage' },
          { id: 'whitelist', label: 'Query Whitelist' },
          { id: 'ip_rules', label: 'IP Rules' },
          { id: 'users', label: 'User Management' },
          { id: 'policies', label: 'Security Policies' },
          { id: 'compliance', label: 'Compliance Export' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-5 py-2.5 rounded-t-xl font-bold uppercase tracking-wider text-sm transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-surface-high/50 text-primary-neon border-b-2 border-primary-neon shadow-[inset_0_-2px_8px_rgba(0,255,157,0.1)]'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-high/30'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl shadow-lg ring-1 ring-white/5 overflow-hidden">
        {loading && <div className="h-1 bg-primary-neon/20 overflow-hidden"><div className="h-full bg-primary-neon w-1/3 animate-pulse"></div></div>}
        
        {fetchError && (
          <div className="m-6 p-4 bg-error/10 border border-error/30 text-error rounded-xl flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm font-medium">{fetchError}</span>
          </div>
        )}

        {/* Audit Logs (Security Center) */}
        {!fetchError && activeTab === 'audit' && (
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="text-xl font-bold text-on-surface flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
                  Security Overview
                </h2>
                <p className="text-sm text-on-surface-variant mt-1">Argus has automatically prevented dangerous actions and policy violations today.</p>
              </div>
              <div className="flex items-center gap-4 bg-surface-high/50 px-4 py-2 rounded-xl border border-surface-high text-sm">
                <Filter className="w-4 h-4 text-primary-neon" />
                <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="bg-transparent text-on-surface outline-none cursor-pointer">
                  <option value="all">All Events</option>
                  <option value="error">Blocked Actions</option>
                  <option value="success">Allowed Actions</option>
                </select>
              </div>
            </div>

            {/* Narrative Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredLogs.filter(l => l.status === 'error').slice(0, 2).map((log: any, idx) => (
                <div key={`story-${idx}`} className="bg-error/5 border border-error/20 p-5 rounded-xl relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-error/10 rounded-full blur-3xl -mr-16 -mt-16"></div>
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-error/20 rounded-xl">
                      <ShieldAlert className="w-6 h-6 text-error" />
                    </div>
                    <div>
                      <h3 className="font-bold text-on-surface text-lg">Blocked Dangerous Query</h3>
                      <p className="text-sm text-on-surface-variant mt-1">
                        User <span className="font-mono text-error font-bold">{log.user_id}</span> attempted an unauthorized <span className="uppercase text-xs font-bold tracking-wider">{log.query_type}</span> operation. Argus intercepted and dropped the request.
                      </p>
                      <div className="mt-3 flex items-center gap-4 text-xs font-mono text-on-surface-variant">
                        <span>Trace: {log.trace_id?.substring(0,8)}</span>
                        <span>Time: {new Date().toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 border border-surface-high rounded-xl overflow-hidden">
              <div className="bg-surface-high/50 px-4 py-3 border-b border-surface-high flex justify-between items-center">
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface-variant">Full Event Ledger</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-surface/30 border-b border-surface-high">
                    <tr>
                      <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Trace ID</th>
                      <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">User</th>
                      <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Action</th>
                      <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-high/50 bg-surface/50">
                    {filteredLogs.map((log: any) => (
                      <tr key={log.trace_id} className="hover:bg-surface-high/30 transition-colors">
                        <td className="p-4 font-mono text-xs text-on-surface/80">{log.trace_id?.substring(0, 12)}...</td>
                        <td className="p-4 text-on-surface text-sm font-medium">{log.user_id}</td>
                        <td className="p-4"><span className="px-2 py-1 bg-surface-high rounded text-xs font-mono text-primary-container">{log.query_type}</span></td>
                        <td className="p-4">
                          <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider ${log.status === 'success' ? 'bg-primary-neon/10 text-primary-neon border border-primary-neon/20' : 'bg-error/10 text-error border border-error/20'}`}>
                            {log.status === 'success' ? 'Allowed' : 'Blocked'}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {filteredLogs.length === 0 && (
                      <tr><td colSpan={4} className="text-center py-8 text-on-surface-variant font-mono uppercase text-sm">No events found matching criteria</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Slow Queries */}
        {!fetchError && activeTab === 'slow' && (
          <div className="p-6">
            <h2 className="text-xl font-bold text-on-surface mb-6 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-error rounded-full shadow-[0_0_8px_#ff716c]"></span>
              Performance Degradation Events
            </h2>
            <div className="space-y-4">
              {slowQueries.map((query: any) => (
                <div key={query.trace_id} className="bg-error/5 border border-error/20 rounded-xl p-5 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-error"></div>
                  <div className="flex flex-col md:flex-row justify-between items-start gap-4">
                    <div>
                      <div className="text-xs font-bold text-error uppercase tracking-widest mb-1">Fingerprint Hash</div>
                      <div className="font-mono text-sm text-on-surface/80 bg-surface px-3 py-1.5 rounded-lg border border-surface-high inline-block">
                        {query.query_fingerprint || query.trace_id}
                      </div>
                      <div className="text-3xl font-black text-error drop-shadow-[0_0_5px_rgba(255,113,108,0.5)] mt-4 flex items-center gap-2">
                        {query.latency_ms}ms <span className="text-sm text-error/60 font-medium tracking-normal">(Execution Delay)</span>
                      </div>
                    </div>
                    <div className="text-right flex flex-col md:items-end gap-2 text-sm w-full md:w-auto">
                      <div className="bg-surface px-3 py-2 rounded-lg border border-surface-high font-mono text-on-surface-variant flex items-center justify-between md:justify-end gap-4 w-full">
                        <span className="uppercase text-xs font-bold">Rows Scanned</span>
                        <span className="text-on-surface font-bold text-lg">{query.rows_scanned || 'N/A'}</span>
                      </div>
                      <div className="bg-surface px-3 py-2 rounded-lg border border-surface-high font-mono text-on-surface-variant flex items-center justify-between md:justify-end gap-4 w-full">
                        <span className="uppercase text-xs font-bold">Strategy</span>
                        <span className="text-primary-neon font-bold">{query.scan_type || 'Seq Scan'}</span>
                      </div>
                    </div>
                  </div>
                  {query.recommended_index && (
                    <div className="mt-5 bg-primary-neon/10 border border-primary-neon/30 p-4 rounded-xl font-mono text-sm">
                      <div className="flex items-center gap-2 text-primary-neon font-bold uppercase tracking-wider text-xs mb-2">
                        <Database className="w-4 h-4" /> AI Index Recommendation
                      </div>
                      <div className="text-on-surface break-all">{query.recommended_index}</div>
                    </div>
                  )}
                </div>
              ))}
              {slowQueries.length === 0 && <div className="text-center py-12 text-primary-neon/80 font-mono text-sm tracking-wider flex items-center justify-center gap-2"><CheckCircle className="w-4 h-4"/> No slow queries detected in the past 24 hours</div>}
            </div>
          </div>
        )}

        {/* Budget */}
        {!fetchError && activeTab === 'budget' && (
          <div className="p-6">
            <h2 className="text-xl font-bold text-on-surface mb-6 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-primary-container rounded-full"></span>
              Resource Quotas
            </h2>
            {budget ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-surface-high/30 border border-surface-high rounded-xl p-6 text-center">
                  <div className="text-on-surface-variant font-bold uppercase tracking-wider text-sm mb-2">Daily Threshold</div>
                  <div className="text-4xl font-black text-primary-container">{budget.daily_budget || 1000}</div>
                </div>
                <div className="bg-surface-high/30 border border-surface-high rounded-xl p-6 text-center">
                  <div className="text-on-surface-variant font-bold uppercase tracking-wider text-sm mb-2">Consumed</div>
                  <div className="text-4xl font-black text-error drop-shadow-[0_0_8px_rgba(255,113,108,0.3)]">{budget.current_usage || 0}</div>
                </div>
                <div className="bg-surface-high/30 border border-surface-high rounded-xl p-6 text-center">
                  <div className="text-on-surface-variant font-bold uppercase tracking-wider text-sm mb-2">Remaining</div>
                  <div className="text-4xl font-black text-primary-neon drop-shadow-[0_0_8px_rgba(0,255,157,0.3)]">{budget.remaining || 1000}</div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-on-surface-variant font-mono text-sm">Loading budget telemetry...</div>
            )}
          </div>
        )}

        {/* IP Rules */}
        {!fetchError && activeTab === 'ip_rules' && (
          <div className="p-6">
            <h2 className="text-xl font-bold text-on-surface mb-6 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-error rounded-full shadow-[0_0_8px_#ff716c]"></span>
              IP Firewall Configuration
            </h2>
            <form onSubmit={handleIpRule} className="bg-surface-high/20 border border-surface-high rounded-xl p-6 flex flex-col md:flex-row gap-4 mb-6">
              <input type="text" value={ipAddress} onChange={(e) => setIpAddress(e.target.value)} placeholder="IP Address (e.g., 192.168.1.5)" className="flex-1 bg-surface border border-surface-high text-on-surface px-4 py-2 rounded-lg outline-none focus:border-primary-neon/50 transition-colors" required />
              <select value={ipAction} onChange={(e) => setIpAction(e.target.value)} className="bg-surface border border-surface-high text-on-surface px-4 py-2 rounded-lg cursor-pointer outline-none focus:border-primary-neon/50">
                <option value="block">Block (24h)</option>
                <option value="allow">Whitelist</option>
              </select>
              <button type="submit" className="bg-primary-neon hover:bg-primary-neon/80 text-background px-6 py-2 rounded-lg font-bold uppercase tracking-wider transition-colors shadow-[0_0_10px_rgba(0,255,157,0.3)]">Apply Rule</button>
            </form>
            <div className="text-sm text-on-surface-variant font-medium">New firewall rules sync across gateway nodes within ~2,000ms.</div>
          </div>
        )}

        {/* User Management */}
        {!fetchError && activeTab === 'users' && (
          <div className="p-6">
            <h2 className="text-xl font-bold text-on-surface mb-6 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-primary-container rounded-full"></span>
              User & Access Scoping
            </h2>
            <div className="overflow-x-auto rounded-xl border border-surface-high">
              <table className="w-full text-left">
                <thead className="bg-surface-high/50 border-b border-surface-high">
                  <tr>
                    <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">User ID</th>
                    <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Role</th>
                    <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Created</th>
                    <th className="p-4 text-center text-xs font-bold text-on-surface-variant uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-high/50 bg-surface/50">
                  {users.length > 0 ? users.map((user: any) => (
                    <tr key={user.id} className="hover:bg-surface-high/30 transition-colors">
                      <td className="p-4 text-on-surface text-sm font-medium">{user.username || user.email || user.id}</td>
                      <td className="p-4">
                        <span className="px-2.5 py-1 bg-primary-container/10 text-primary-container border border-primary-container/20 rounded-md text-xs font-bold uppercase tracking-wider">
                          {user.role || 'user'}
                        </span>
                      </td>
                      <td className="p-4 text-sm font-mono text-on-surface-variant">{new Date(user.created_at || Date.now()).toLocaleDateString()}</td>
                      <td className="p-4 text-center">
                        <button onClick={() => deleteUser(user.id)} className="p-2 rounded-lg text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors" title="Revoke Access">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={4} className="p-8 text-center text-on-surface-variant">
                        <div className="font-mono text-sm uppercase tracking-wider mb-2">No Users Found</div>
                        <p className="text-xs opacity-70">If the users endpoint isn't fully scaffolded natively, user accounts are managed at the DB layer presently.</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Whitelist */}
        {!fetchError && activeTab === 'whitelist' && (
          <div className="p-6">
            <h2 className="text-xl font-bold text-on-surface mb-6 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
              Sanctioned Query Fingerprints
            </h2>
            <div className="space-y-3">
              {whitelist.map((item: any) => (
                <div key={item.query_fingerprint} className="flex justify-between items-center bg-surface-high/20 hover:bg-surface-high/40 transition-colors border border-surface-high rounded-xl p-4">
                  <div>
                    <div className="font-mono text-sm text-primary-neon font-bold mb-1">{item.query_fingerprint}</div>
                    {item.description && <div className="text-xs text-on-surface-variant uppercase tracking-wider">{item.description}</div>}
                  </div>
                  <button
                    onClick={() => removeWhitelist(item.query_fingerprint)}
                    className="p-2 rounded-lg text-on-surface-variant hover:text-error hover:bg-error/10 border border-transparent hover:border-error/20 transition-colors"
                    title="Revoke Approval"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              ))}
              {whitelist.length === 0 && <div className="text-center py-12 text-on-surface-variant font-mono text-sm uppercase tracking-wider">No Pre-approved Queries configured</div>}
            </div>
          </div>
        )}

        {/* Security Policies Tab */}
        {!fetchError && activeTab === 'policies' && (
          <div className="p-6">
            <h2 className="text-xl font-bold text-on-surface mb-6 flex items-center gap-2">
              <span className="w-1.5 h-6 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
              Active Role-Based Access Control Policies (RBAC)
            </h2>
            <div className="overflow-x-auto rounded-xl border border-surface-high">
              <table className="w-full text-left">
                <thead className="bg-surface-high/50 border-b border-surface-high">
                  <tr>
                    <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Role</th>
                    <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Allowed Tables</th>
                    <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Allowed Hours</th>
                    <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Priority</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-high/50 bg-surface/50">
                  {rbacPolicies.map((policy: any) => (
                    <tr key={policy.role} className="hover:bg-surface-high/30 transition-colors">
                      <td className="p-4 font-mono text-sm font-bold text-primary-neon">{policy.role}</td>
                      <td className="p-4 text-sm font-mono text-on-surface">
                        {policy.allowed_tables?.join(", ") || "*"}
                      </td>
                      <td className="p-4 text-sm font-mono text-on-surface font-semibold">
                        {policy.allowed_hours} ({policy.timezone})
                      </td>
                      <td className="p-4 text-sm">
                        <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider ${
                          policy.priority === 'High' 
                            ? 'bg-error/10 text-error border border-error/20 shadow-[0_0_10px_rgba(255,113,108,0.1)]' 
                            : 'bg-primary-container/10 text-primary-container border border-primary-container/20'
                        }`}>
                          {policy.priority}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {rbacPolicies.length === 0 && (
                    <tr>
                      <td colSpan={4} className="text-center py-8 text-on-surface-variant font-mono uppercase text-sm">
                        No security policies loaded
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Compliance Export Tab */}
        {!fetchError && activeTab === 'compliance' && (
          <div className="p-6 space-y-6">
            <h2 className="text-xl font-bold text-on-surface flex items-center gap-2">
              <span className="w-1.5 h-6 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
              Compliance Ledger Export
            </h2>
            <p className="text-sm text-on-surface-variant">
              Download standard compliance audits, query performance summaries, and IP rules for offline storage or reporting.
            </p>

            <div className="bg-surface-high/20 border border-surface-high rounded-xl p-6 space-y-6 max-w-xl">
              <div className="space-y-3">
                <label className="text-xs uppercase font-bold tracking-wider text-on-surface-variant block">Report Period</label>
                <div className="flex gap-4">
                  {['30d', '60d', '90d'].map((period) => (
                    <label 
                      key={period} 
                      className={`flex-1 flex items-center justify-center p-3 rounded-xl border text-sm font-bold uppercase tracking-wider cursor-pointer transition-all ${
                        compliancePeriod === period 
                          ? 'bg-primary-neon/10 border-primary-neon text-primary-neon shadow-[0_0_10px_rgba(0,255,157,0.1)]' 
                          : 'bg-surface border-surface-high text-on-surface-variant hover:text-on-surface'
                      }`}
                    >
                      <input 
                        type="radio" 
                        name="period" 
                        value={period} 
                        checked={compliancePeriod === period}
                        onChange={() => setCompliancePeriod(period)}
                        className="sr-only"
                      />
                      {period}
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-4 pt-2">
                <button 
                  onClick={() => handleExport('csv')} 
                  className="flex-1 px-5 py-3 bg-surface hover:bg-surface-high border border-surface-high text-on-surface rounded-xl font-bold uppercase tracking-wider text-xs transition-colors flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4 text-primary-neon" /> Export CSV
                </button>
                <button 
                  onClick={() => handleExport('json')} 
                  className="flex-1 px-5 py-3 bg-primary-neon text-background hover:bg-primary-neon/90 rounded-xl font-bold uppercase tracking-wider text-xs transition-colors shadow-[0_0_15px_rgba(0,255,157,0.2)] flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" /> Export JSON
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
