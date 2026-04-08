import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from 'recharts';
import {
  TrashIcon,
  PlusIcon,
  DownloadIcon,
  RefreshIcon,
} from '@heroicons/react/solid';

const AdminDashboard = ({ token }) => {
  const [activeTab, setActiveTab] = useState('audit');
  const [auditLogs, setAuditLogs] = useState([]);
  const [slowQueries, setSlowQueries] = useState([]);
  const [budget, setBudget] = useState(null);
  const [whitelist, setWhitelist] = useState([]);
  const [ipRules, setIpRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newIpAddress, setNewIpAddress] = useState('');
  const [ipRuleType, setIpRuleType] = useState('allow');

  const apiBase = 'http://localhost:8000/api/v1';

  useEffect(() => {
    if (activeTab === 'audit') fetchAuditLogs();
    if (activeTab === 'slow') fetchSlowQueries();
    if (activeTab === 'budget') fetchBudget();
    if (activeTab === 'whitelist') fetchWhitelist();
    if (activeTab === 'ip') fetchIpRules();
  }, [activeTab]);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/admin/audit?limit=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setAuditLogs(data);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    }
    setLoading(false);
  };

  const fetchSlowQueries = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/admin/slow-queries?limit=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setSlowQueries(data.items || []);
    } catch (err) {
      console.error('Failed to fetch slow queries:', err);
    }
    setLoading(false);
  };

  const fetchBudget = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/admin/budget`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setBudget(data);
    } catch (err) {
      console.error('Failed to fetch budget:', err);
    }
    setLoading(false);
  };

  const fetchWhitelist = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/admin/whitelist`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setWhitelist(data.items || []);
    } catch (err) {
      console.error('Failed to fetch whitelist:', err);
    }
    setLoading(false);
  };

  const fetchIpRules = async () => {
    setLoading(true);
    try {
      // Placeholder - would need actual endpoint
      setIpRules([]);
    } catch (err) {
      console.error('Failed to fetch IP rules:', err);
    }
    setLoading(false);
  };

  const removeWhitelist = async (fingerprint) => {
    if (!window.confirm('Remove this query from whitelist?')) return;
    try {
      await fetch(`${apiBase}/admin/whitelist/${fingerprint}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchWhitelist();
    } catch (err) {
      console.error('Failed to remove whitelist:', err);
    }
  };

  const addIpRule = async () => {
    if (!newIpAddress) return;
    try {
      await fetch(`${apiBase}/admin/ip-rules`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ip_address: newIpAddress,
          rule_type: ipRuleType,
          description: `${ipRuleType} rule`,
        }),
      });
      setNewIpAddress('');
      fetchIpRules();
    } catch (err) {
      console.error('Failed to add IP rule:', err);
    }
  };

  const exportCompliance = async () => {
    try {
      const res = await fetch(`${apiBase}/admin/compliance-report?period=30d&format=json`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `compliance-report-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
    } catch (err) {
      console.error('Failed to export compliance report:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <button
            onClick={() => setActiveTab(activeTab)} // Force refresh
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
          >
            <RefreshIcon className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-8 border-b border-gray-700">
          {[
            { id: 'audit', label: '📋 Audit Logs' },
            { id: 'slow', label: '⚡ Slow Queries' },
            { id: 'budget', label: '💰 Budget Usage' },
            { id: 'whitelist', label: '✅ Query Whitelist' },
            { id: 'ip', label: '🚫 IP Rules' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-medium transition ${
                activeTab === tab.id
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading && <div className="text-center py-8">Loading...</div>}

        {!loading && (
          <>
            {/* Audit Logs Tab */}
            {activeTab === 'audit' && (
              <div className="bg-gray-800 rounded-lg p-6">
                <h2 className="text-xl font-bold mb-4">Audit Logs</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-4 py-2 text-left">Trace ID</th>
                        <th className="px-4 py-2 text-left">User</th>
                        <th className="px-4 py-2 text-left">Query Type</th>
                        <th className="px-4 py-2 text-left">Status</th>
                        <th className="px-4 py-2 text-left">Latency</th>
                        <th className="px-4 py-2 text-left">Cached</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log) => (
                        <tr key={log.trace_id} className="border-t border-gray-700">
                          <td className="px-4 py-2 font-mono text-xs">
                            {log.trace_id.substring(0, 12)}...
                          </td>
                          <td className="px-4 py-2">{log.user_id}</td>
                          <td className="px-4 py-2">{log.query_type}</td>
                          <td className="px-4 py-2">
                            <span
                              className={`px-2 py-1 rounded text-xs ${
                                log.status === 'success'
                                  ? 'bg-green-900 text-green-300'
                                  : 'bg-red-900 text-red-300'
                              }`}
                            >
                              {log.status}
                            </span>
                          </td>
                          <td className="px-4 py-2">{log.latency_ms.toFixed(2)}ms</td>
                          <td className="px-4 py-2">
                            {log.cached ? '✓' : '✗'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Slow Queries Tab */}
            {activeTab === 'slow' && (
              <div className="bg-gray-800 rounded-lg p-6">
                <h2 className="text-xl font-bold mb-4">Slow Queries</h2>
                <div className="space-y-4">
                  {slowQueries.map((query) => (
                    <div key={query.trace_id} className="bg-gray-700 rounded p-4 border-l-4 border-red-500">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-mono text-sm text-gray-300">
                            {query.query_fingerprint}
                          </div>
                          <div className="text-lg font-bold text-red-400 mt-2">
                            {query.latency_ms}ms
                          </div>
                        </div>
                        <div className="text-right text-sm">
                          <div className="text-gray-400">
                            Rows: {query.rows_scanned}
                          </div>
                          <div className="text-gray-400">
                            Scan: {query.scan_type}
                          </div>
                        </div>
                      </div>
                      {query.recommended_index && (
                        <div className="mt-3 bg-gray-600 rounded p-2 font-mono text-xs">
                          {query.recommended_index}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Budget Tab */}
            {activeTab === 'budget' && budget && (
              <div className="bg-gray-800 rounded-lg p-6 space-y-6">
                <h2 className="text-xl font-bold mb-4">Budget Usage</h2>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-700 rounded p-4">
                    <div className="text-gray-400 text-sm">Daily Limit</div>
                    <div className="text-3xl font-bold text-blue-400">
                      {budget.daily_budget}
                    </div>
                  </div>
                  <div className="bg-gray-700 rounded p-4">
                    <div className="text-gray-400 text-sm">Used</div>
                    <div className="text-3xl font-bold text-yellow-400">
                      {budget.current_usage}
                    </div>
                  </div>
                  <div className="bg-gray-700 rounded p-4">
                    <div className="text-gray-400 text-sm">Remaining</div>
                    <div className="text-3xl font-bold text-green-400">
                      {budget.remaining}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Whitelist Tab */}
            {activeTab === 'whitelist' && (
              <div className="bg-gray-800 rounded-lg p-6">
                <h2 className="text-xl font-bold mb-4">Query Whitelist</h2>
                <div className="space-y-3">
                  {whitelist.map((item) => (
                    <div key={item.query_fingerprint} className="flex items-center justify-between bg-gray-700 rounded p-3">
                      <div>
                        <div className="font-mono text-sm text-gray-300">
                          {item.query_fingerprint}
                        </div>
                        {item.description && (
                          <div className="text-xs text-gray-400 mt-1">
                            {item.description}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => removeWhitelist(item.query_fingerprint)}
                        className="bg-red-600 hover:bg-red-700 p-2 rounded transition"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* IP Rules Tab */}
            {activeTab === 'ip' && (
              <div className="bg-gray-800 rounded-lg p-6 space-y-6">
                <h2 className="text-xl font-bold mb-4">IP Rules</h2>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="IP address"
                    value={newIpAddress}
                    onChange={(e) => setNewIpAddress(e.target.value)}
                    className="flex-1 bg-gray-700 text-white rounded px-3 py-2"
                  />
                  <select
                    value={ipRuleType}
                    onChange={(e) => setIpRuleType(e.target.value)}
                    className="bg-gray-700 text-white rounded px-3 py-2"
                  >
                    <option value="allow">Allow</option>
                    <option value="block">Block</option>
                  </select>
                  <button
                    onClick={addIpRule}
                    className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded flex items-center gap-2 transition"
                  >
                    <PlusIcon className="h-4 w-4" />
                    Add
                  </button>
                </div>
                <div className="space-y-2">
                  {ipRules.map((rule) => (
                    <div key={rule.ip_address} className="flex items-center justify-between bg-gray-700 rounded p-3">
                      <div>
                        <div className="font-bold">{rule.ip_address}</div>
                        <div className="text-sm text-gray-400">{rule.rule_type}</div>
                      </div>
                      <button
                        onClick={() => console.log('Delete', rule.ip_address)}
                        className="bg-red-600 hover:bg-red-700 p-2 rounded transition"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Export Compliance Button */}
        <div className="mt-8 flex justify-center">
          <button
            onClick={exportCompliance}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-6 py-3 rounded-lg font-medium transition"
          >
            <DownloadIcon className="h-5 w-5" />
            Export 30-Day Compliance Report
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
