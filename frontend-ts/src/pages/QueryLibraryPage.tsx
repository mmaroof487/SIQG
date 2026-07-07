import { useState, useEffect } from "react";
import { BookOpen, Search, Play, Clock, Tag, AlertCircle, Loader2, Database } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "../utils/api";

interface SavedQuery {
  id: string;
  query: string;
  executed_at: string;
  rows_returned: number;
  execution_time_ms: number;
}

export default function QueryLibraryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [queries, setQueries] = useState<SavedQuery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getUserHistory(50, 0);
        // history endpoint returns array of query history rows
        const rows: any[] = res.data?.history || res.data || [];
        setQueries(rows);
      } catch (err: any) {
        setError("Failed to load query history. The gateway may be offline.");
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const filtered = queries.filter((q) =>
    q.query?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleExecute = (sql: string) => {
    // Navigate to query page — future enhancement: pre-fill the query editor
    navigate("/", { state: { prefillQuery: sql } });
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString();
    } catch {
      return isoString;
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6 animate-in fade-in duration-500">
      <div className="flex items-end gap-6 mb-2">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
          <BookOpen className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
        </div>
        <div>
          <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Query History</h1>
          <p className="text-on-surface-variant font-medium">Your recent query executions</p>
        </div>
      </div>

      <div className="flex items-center justify-between pb-4 border-b border-surface-high">
        <div className="relative w-96">
          <Search className="w-4 h-4 text-on-surface-variant absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search your query history..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface border border-surface-high pl-11 pr-4 py-2.5 rounded-xl text-sm outline-none focus:border-primary-neon/50 text-on-surface transition-colors shadow-[inset_0_2px_4px_rgba(0,0,0,0.2)]"
          />
        </div>
        <span className="text-xs font-mono text-on-surface-variant uppercase tracking-widest">
          {loading ? "Loading..." : `${filtered.length} queries`}
        </span>
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-on-surface-variant">
            <Loader2 className="w-8 h-8 animate-spin text-primary-neon" />
            <p className="text-sm font-mono uppercase tracking-widest">Loading query history...</p>
          </div>
        </div>
      )}

      {!loading && error && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-error">
            <AlertCircle className="w-10 h-10 opacity-60" />
            <p className="text-sm font-mono">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-on-surface-variant">
          <div className="text-center font-mono uppercase tracking-widest text-sm space-y-2">
            <BookOpen className="w-12 h-12 mx-auto opacity-20 mb-4" />
            <p>{queries.length === 0 ? "No queries executed yet. Run your first query to build history." : "No queries match your search."}</p>
          </div>
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {filtered.map((query) => (
            <div
              key={query.id}
              className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl p-6 flex flex-col group hover:border-primary-neon/30 transition-all hover:shadow-[0_0_20px_rgba(0,255,157,0.05)] ring-1 ring-white/5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-24 h-24 bg-primary-neon/5 blur-2xl rounded-full transition-opacity opacity-0 group-hover:opacity-100" />

              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-primary-neon shrink-0" />
                  <span className="text-xs font-mono text-primary-neon uppercase tracking-wider">SQL</span>
                </div>
                {query.execution_time_ms != null && (
                  <span className="text-xs font-mono text-on-surface-variant bg-surface-high/50 px-2 py-0.5 rounded border border-surface-high">
                    {Math.round(query.execution_time_ms)}ms
                  </span>
                )}
              </div>

              <pre className="text-on-surface text-xs mb-4 flex-1 line-clamp-5 leading-relaxed font-mono whitespace-pre-wrap break-all">
                {query.query}
              </pre>

              <div className="flex flex-col gap-3 mt-auto">
                {query.rows_returned != null && (
                  <div className="flex items-center gap-1.5">
                    <Tag className="w-3 h-3 text-on-surface-variant" />
                    <span className="text-xs text-on-surface-variant font-mono">
                      {query.rows_returned} row{query.rows_returned !== 1 ? "s" : ""} returned
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between pt-3 border-t border-surface-high/50">
                  <div className="flex items-center gap-1.5 text-xs text-on-surface-variant font-mono">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDate(query.executed_at)}
                  </div>

                  <button
                    onClick={() => handleExecute(query.query)}
                    className="flex items-center gap-1.5 text-background font-bold tracking-wider uppercase text-xs px-4 py-1.5 bg-primary-neon hover:bg-primary-neon/80 rounded-lg transition-colors shadow-[0_0_10px_rgba(0,255,157,0.2)]"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" /> Re-run
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
