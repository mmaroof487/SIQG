import { useState, useEffect } from "react";
import { api } from "../utils/api";
import { Database, Table as TableIcon, Columns, Key as KeyIcon, Search, RefreshCw, AlertCircle } from "lucide-react";

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
}

interface TableMetadata {
  name: string;
  columns: ColumnMetadata[];
  description?: string;
  rows?: number;
}

interface SchemaMetadata {
  schema: string;
  tables: TableMetadata[];
}

export default function SchemaBrowserPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState<string>("default");
  
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTable, setActiveTable] = useState("users");
  const [isLoading, setIsLoading] = useState(false);
  const [schemaError, setSchemaError] = useState("");
  const [schemas, setSchemas] = useState<SchemaMetadata[]>([]);

  // Local/Primary Mock Database Schema
  const schemaMock: SchemaMetadata[] = [
    {
      schema: "public",
      tables: [
        {
          name: "users",
          columns: [
            { name: "id", type: "uuid", pk: true, nullable: false },
            { name: "email", type: "varchar(255)", pk: false, nullable: false },
            { name: "role", type: "varchar(50)", pk: false, nullable: false },
            { name: "created_at", type: "timestamp", pk: false, nullable: false }
          ],
          rows: 15420,
          description: "Core authentication and user identity table"
        },
        {
          name: "transactions",
          columns: [
            { name: "id", type: "uuid", pk: true, nullable: false },
            { name: "user_id", type: "uuid", pk: false, nullable: false },
            { name: "amount", type: "decimal(12,2)", pk: false, nullable: false },
            { name: "status", type: "varchar(20)", pk: false, nullable: false }
          ],
          rows: 894050,
          description: "Financial ledger events and status"
        },
        {
          name: "audit_logs",
          columns: [
            { name: "trace_id", type: "uuid", pk: true, nullable: false },
            { name: "action", type: "text", pk: false, nullable: false },
            { name: "actor_id", type: "uuid", pk: false, nullable: true },
            { name: "timestamp", type: "timestamp", pk: false, nullable: false }
          ],
          rows: 2450912,
          description: "Immutable gateway security ledger"
        }
      ]
    }
  ];

  useEffect(() => {
    loadConnections();
  }, []);

  useEffect(() => {
    if (selectedConnectionId === "default") {
      setSchemas(schemaMock);
      setActiveTable("users");
      setSchemaError("");
    } else {
      fetchSchema(selectedConnectionId);
    }
  }, [selectedConnectionId]);

  const loadConnections = async () => {
    try {
      const res = await api.getConnections();
      setConnections(res.data.filter((c: Connection) => c.is_active));
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
      const data = res.data;
      setSchemas(data);
      if (data.length > 0 && data[0].tables.length > 0) {
        setActiveTable(data[0].tables[0].name);
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

  return (
    <div className="h-full flex flex-col space-y-6 animate-in fade-in duration-500 pb-16">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-2">
        <div className="flex items-end gap-6">
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
          <select
            value={selectedConnectionId}
            onChange={(e) => setSelectedConnectionId(e.target.value)}
            className="bg-surface/60 border border-surface-high rounded-xl text-xs font-bold text-on-surface px-4 py-2.5 outline-none focus:border-primary-neon/50 transition-colors cursor-pointer min-w-[200px]"
          >
            <option value="default">Argus Primary (default)</option>
            {connections.map(c => (
              <option key={c.id} value={c.id}>{c.display_name}</option>
            ))}
          </select>
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
                  <div key={schema.schema} className="space-y-2">
                    <div className="flex items-center gap-2 text-on-surface-variant font-bold uppercase tracking-wider text-xs mb-2 pl-1">
                      <Database className="w-3.5 h-3.5" /> Schema: {schema.schema}
                    </div>
                    {filteredTables.map(table => (
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
                );
              })
            )}
          </div>
        </div>

        {/* Right Detail Panel */}
        <div className="w-2/3 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl flex flex-col ring-1 ring-white/5 overflow-hidden">
          {isLoading ? (
            <div className="flex-1 flex flex-col space-y-4 p-8 animate-pulse">
              <div className="h-8 bg-surface-high rounded w-1/4"></div>
              <div className="h-4 bg-surface-high rounded w-3/4"></div>
              <div className="h-40 bg-surface-high rounded mt-8"></div>
            </div>
          ) : activeTableObj ? (
            <div className="flex flex-col h-full animate-in fade-in duration-300">
              <div className="p-8 border-b border-surface-high bg-gradient-to-r from-surface-high/10 to-transparent">
                <h2 className="text-2xl font-bold font-mono text-on-surface flex items-center gap-3 mb-2">
                  <span className="w-2 h-8 bg-primary-neon rounded-full shadow-[0_0_8px_#00FF9D]"></span>
                  {activeTableObj.name}
                </h2>
                <p className="text-on-surface-variant">{activeTableObj.description || "External database table topology"}</p>
                {activeTableObj.rows !== undefined && (
                  <div className="mt-6 flex gap-4">
                    <div className="px-4 py-2 bg-surface-high/40 border border-surface-high rounded-xl text-sm font-mono flex items-center gap-3">
                      <span className="text-on-surface-variant uppercase tracking-wider text-xs font-sans font-bold">Est. Rows</span> 
                      <span className="text-primary-neon">{activeTableObj.rows.toLocaleString()}</span>
                    </div>
                  </div>
                )}
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
                              <span className="text-on-surface-variant text-sm flex items-center gap-1">
                                {col.nullable ? "Nullable" : "NOT NULL"}
                              </span>
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
             <div className="flex-1 flex items-center justify-center text-on-surface-variant font-mono uppercase tracking-widest text-sm">Select a table node from catalog</div>
          )}
        </div>
      </div>
    </div>
  );
}
