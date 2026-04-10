import { useState } from "react";
import { Database, Table as TableIcon, Columns, Key as KeyIcon, Search } from "lucide-react";

export default function SchemaBrowserPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTable, setActiveTable] = useState("users");

  const schemaMock = [
    {
      name: "public",
      tables: [
        {
          name: "users",
          columns: [
            { name: "id", type: "uuid", pk: true },
            { name: "email", type: "varchar(255)", pk: false },
            { name: "role", type: "varchar(50)", pk: false },
            { name: "created_at", type: "timestamp", pk: false }
          ],
          rows: 15420,
          description: "Core authentication and user identity table"
        },
        {
          name: "transactions",
          columns: [
            { name: "id", type: "uuid", pk: true },
            { name: "user_id", type: "uuid", pk: false },
            { name: "amount", type: "decimal(12,2)", pk: false },
            { name: "status", type: "varchar(20)", pk: false }
          ],
          rows: 894050,
          description: "Financial ledger events and status"
        },
        {
          name: "audit_logs",
          columns: [
            { name: "trace_id", type: "uuid", pk: true },
            { name: "action", type: "text", pk: false },
            { name: "actor_id", type: "uuid", pk: false },
            { name: "timestamp", type: "timestamp", pk: false }
          ],
          rows: 2450912,
          description: "Immutable gateway security ledger"
        }
      ]
    }
  ];

  const activeTableObj = schemaMock[0].tables.find(t => t.name === activeTable);

  return (
    <div className="h-full flex flex-col space-y-6 animate-in fade-in duration-500">
      <div className="flex items-end gap-6 mb-2">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
          <Database className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
        </div>
        <div>
          <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Schema Browser</h1>
          <p className="text-on-surface-variant font-medium">Database index mapping and topological view</p>
        </div>
      </div>

      <div className="flex gap-6 flex-1 min-h-[500px]">
        {/* Left Tree Panel */}
        <div className="w-1/3 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl flex flex-col overflow-hidden ring-1 ring-white/5">
          <div className="p-4 border-b border-surface-high relative bg-surface-high/20">
            <Search className="w-4 h-4 text-on-surface-variant absolute left-7 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search tables..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface border border-surface-high pl-10 pr-4 py-2 rounded-xl text-sm outline-none focus:border-primary-neon/50 text-on-surface transition-colors"
            />
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {schemaMock.map(schema => (
              <div key={schema.name} className="space-y-2">
                <div className="flex items-center gap-2 text-on-surface-variant font-bold uppercase tracking-wider text-xs mb-2 pl-1">
                  <Database className="w-3.5 h-3.5" /> Schema: {schema.name}
                </div>
                {schema.tables.filter(t => t.name.includes(searchQuery.toLowerCase())).map(table => (
                  <button 
                    key={table.name}
                    onClick={() => setActiveTable(table.name)}
                    className={`w-full flex items-center justify-between p-3 rounded-xl transition-all ${activeTable === table.name ? 'bg-primary-neon/10 border border-primary-neon/30 text-primary-neon shadow-[inset_0_0_10px_rgba(0,255,157,0.05)]' : 'hover:bg-surface-high/50 border border-transparent text-on-surface/80 hover:text-on-surface'}`}
                  >
                    <span className="flex items-center gap-2.5 font-mono text-sm">
                      <TableIcon className="w-4 h-4" /> {table.name}
                    </span>
                    {activeTable === table.name && <div className="w-1.5 h-1.5 bg-primary-neon rounded-full shadow-[0_0_5px_#00FF9D]"></div>}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Right Detail Panel */}
        <div className="w-2/3 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl flex flex-col ring-1 ring-white/5 overflow-hidden">
          {activeTableObj ? (
            <div className="flex flex-col h-full animate-in fade-in duration-300">
              <div className="p-8 border-b border-surface-high bg-gradient-to-r from-surface-high/10 to-transparent">
                <h2 className="text-2xl font-bold font-mono text-on-surface flex items-center gap-3 mb-2">
                  <span className="w-2 h-8 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
                  {activeTableObj.name}
                </h2>
                <p className="text-on-surface-variant">{activeTableObj.description}</p>
                <div className="mt-6 flex gap-4">
                  <div className="px-4 py-2 bg-surface-high/40 border border-surface-high rounded-xl text-sm font-mono flex items-center gap-3">
                    <span className="text-on-surface-variant uppercase tracking-wider text-xs font-sans font-bold">Est. Rows</span> 
                    <span className="text-primary-neon">{activeTableObj.rows.toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <div className="p-8 flex-1 overflow-y-auto">
                <h3 className="text-sm font-bold uppercase tracking-wider text-on-surface-variant flex items-center gap-2 mb-4">
                  <Columns className="w-4 h-4" /> Columns Topology
                </h3>
                <div className="border border-surface-high rounded-xl overflow-hidden">
                  <table className="w-full text-left">
                    <thead className="bg-surface-high/50 border-b border-surface-high">
                      <tr>
                        <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Field Vector</th>
                        <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Type Mapping</th>
                        <th className="p-4 text-xs font-bold text-on-surface-variant uppercase tracking-wider">Constraints</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-high/50 bg-surface/30">
                      {activeTableObj.columns.map(col => (
                        <tr key={col.name} className="hover:bg-surface-high/30 transition-colors">
                          <td className="p-4 font-mono font-bold text-sm text-on-surface flex items-center gap-2">
                            {col.pk && <KeyIcon className="w-3.5 h-3.5 text-primary-neon" />}
                            {col.name}
                          </td>
                          <td className="p-4 font-mono text-xs text-primary-container">{col.type}</td>
                          <td className="p-4">
                            {col.pk ? (
                              <span className="px-2 py-1 bg-primary-neon/10 text-primary-neon border border-primary-neon/20 rounded text-xs font-bold uppercase tracking-wider">Primary Key</span>
                            ) : (
                              <span className="text-on-surface-variant text-sm">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
             <div className="flex-1 flex items-center justify-center text-on-surface-variant font-mono uppercase tracking-widest text-sm">Select a node from topology</div>
          )}
        </div>
      </div>
    </div>
  );
}
