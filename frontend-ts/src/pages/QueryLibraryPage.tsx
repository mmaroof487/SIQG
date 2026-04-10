import { useState } from "react";
import { BookOpen, Search, Play, Star, Clock, Tag } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function QueryLibraryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const navigate = useNavigate();

  const queries = [
    { id: 1, title: "High-Value Transaction Anomalies", description: "Detects active user accounts with transaction volume exceeding 500% of their 30-day moving average.", tags: ["security", "finance"], savedAt: "2 hours ago", isStarred: true },
    { id: 2, title: "Daily Active Users (DAU) by Region", description: "Aggregates unique logins partitioned by geographic region codes over the past 24 hour window.", tags: ["analytics"], savedAt: "1 day ago", isStarred: false },
    { id: 3, title: "Stale Sessions Cleanup", description: "Identifies and computes TTLs for user sessions that have registered no heartbeat in 48 hours.", tags: ["maintenance"], savedAt: "1 week ago", isStarred: true },
    { id: 4, title: "Revenue Churn Predictor", description: "Cross-referencing payment failures with prior high-engagement metrics to find risk profiles.", tags: ["forecast", "finance"], savedAt: "2 weeks ago", isStarred: false },
  ];

  const filteredQueries = queries.filter(q => q.title.toLowerCase().includes(searchQuery.toLowerCase()) || q.description.toLowerCase().includes(searchQuery.toLowerCase()));

  const handleExecute = (title: string) => {
    // In a real app, we would pass the query ID to the context/state, but here we'll just navigate
    navigate("/");
  };

  return (
    <div className="h-full flex flex-col space-y-6 animate-in fade-in duration-500">
      <div className="flex items-end gap-6 mb-2">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
          <BookOpen className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
        </div>
        <div>
          <h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Query Library</h1>
          <p className="text-on-surface-variant font-medium">Stored structural configurations and analytic macros</p>
        </div>
      </div>

      <div className="flex items-center justify-between pb-4 border-b border-surface-high">
        <div className="relative w-96">
          <Search className="w-4 h-4 text-on-surface-variant absolute left-4 top-1/2 -translate-y-1/2" />
          <input 
            type="text" 
            placeholder="Search saved macros..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface border border-surface-high pl-11 pr-4 py-2.5 rounded-xl text-sm outline-none focus:border-primary-neon/50 text-on-surface transition-colors shadow-[inset_0_2px_4px_rgba(0,0,0,0.2)]"
          />
        </div>
        <div className="flex gap-2">
           <button className="px-4 py-2 text-sm font-bold uppercase tracking-wider bg-surface-high/50 text-on-surface hover:text-primary-neon rounded-lg transition-colors border border-surface-high hover:border-primary-neon/30">
              Filter by Tags
           </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredQueries.map(query => (
          <div key={query.id} className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl p-6 flex flex-col group hover:border-primary-neon/30 transition-all hover:shadow-[0_0_20px_rgba(0,255,157,0.05)] ring-1 ring-white/5 relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-24 h-24 bg-primary-neon/5 blur-2xl rounded-full transition-opacity opacity-0 group-hover:opacity-100`}></div>
            <div className="flex justify-between items-start mb-4">
               <h3 className="font-bold text-lg text-on-surface leading-tight pr-8">{query.title}</h3>
               <button className="text-on-surface-variant hover:text-primary-container transition-colors shrink-0">
                 <Star className={`w-5 h-5 ${query.isStarred ? 'fill-primary-container text-primary-container' : ''}`} />
               </button>
            </div>
            
            <p className="text-on-surface-variant text-sm mb-6 flex-1 line-clamp-3 leading-relaxed">
              {query.description}
            </p>
            
            <div className="flex flex-col gap-4 mt-auto">
              <div className="flex flex-wrap gap-2">
                 {query.tags.map(tag => (
                   <span key={tag} className="px-2 py-0.5 bg-surface-high/50 border border-surface-high rounded text-xs font-mono text-primary-neon uppercase flex items-center gap-1">
                     <Tag className="w-3 h-3" /> {tag}
                   </span>
                 ))}
              </div>
              
              <div className="flex items-center justify-between pt-4 border-t border-surface-high/50">
                 <div className="flex items-center gap-1.5 text-xs text-on-surface-variant font-mono">
                   <Clock className="w-3.5 h-3.5" />
                   {query.savedAt}
                 </div>
                 
                 <button 
                  onClick={() => handleExecute(query.title)}
                  className="flex items-center gap-1.5 text-background font-bold tracking-wider uppercase text-xs px-4 py-1.5 bg-primary-neon hover:bg-primary-neon/80 rounded-lg transition-colors shadow-[0_0_10px_rgba(0,255,157,0.2)]"
                 >
                   <Play className="w-3.5 h-3.5 fill-current" /> Execute
                 </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {filteredQueries.length === 0 && (
         <div className="flex-1 flex items-center justify-center text-on-surface-variant">
           <div className="text-center font-mono uppercase tracking-widest text-sm space-y-2">
             <BookOpen className="w-12 h-12 mx-auto opacity-20 mb-4" />
             <p>No query macros found matching signature</p>
           </div>
         </div>
      )}
    </div>
  );
}
