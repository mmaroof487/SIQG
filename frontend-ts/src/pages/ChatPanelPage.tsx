import { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, Server, User, Database, ShieldAlert, Sparkles, AlertCircle } from "lucide-react";
import { api } from "../utils/api";

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  error?: boolean;
};

export default function ChatPanelPage() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: 'Connection Established. Argus Intelligence Online. How can I assist you with the cluster telemetry?' }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await api.nlToSql(userMessage.content);
      const sql = response.data.sql;
      
      let explanation = "";
      try {
        const explainRes = await api.explainQuery(sql);
        explanation = explainRes.data.explanation;
      } catch (err) {
        explanation = "Error generating intelligence report.";
      }

      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: explanation,
        sql: sql
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "I'm sorry, I could not generate a safe query for that request or the telemetry service timed out. Check the error logs.",
        error: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-4 animate-in fade-in duration-500 max-w-5xl mx-auto">
      <div className="flex items-center gap-4 py-2 border-b border-surface-high mb-2 pl-2">
        <MessageSquare className="w-6 h-6 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
        <div>
          <h1 className="text-xl font-bold tracking-tight text-on-surface leading-tight">Argus Conversation Matrix</h1>
          <div className="text-xs font-mono text-primary-container flex items-center gap-1"><span className="w-1.5 h-1.5 bg-primary-neon rounded-full animate-pulse"></span> ONLINE</div>
        </div>
      </div>

      <div className="flex-1 bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl flex flex-col overflow-hidden shadow-lg ring-1 ring-white/5 relative">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary-neon/5 blur-[100px] pointer-events-none"></div>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 border ${msg.role === 'user' ? 'bg-surface-high/50 border-surface-high text-on-surface' : 'bg-primary-neon/10 border-primary-neon/30 text-primary-neon shadow-[0_0_10px_rgba(0,255,157,0.1)]'}`}>
                {msg.role === 'user' ? <User className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
              </div>
              <div className={`flex flex-col max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-5 py-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-surface-high text-on-surface rounded-tr-none' : msg.error ? 'bg-error/10 text-error border border-error/20 rounded-tl-none' : 'bg-surface border border-surface-high text-on-surface/90 rounded-tl-none shadow-md'}`}>
                  {msg.error && <AlertCircle className="w-4 h-4 mb-2" />}
                  <div className="leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                </div>
                {msg.sql && (
                  <div className="mt-3 w-full bg-[#111318] border border-surface-high rounded-xl p-4 font-mono text-sm text-[#00fc9b] overflow-x-auto shadow-inner relative group">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-neon to-transparent opacity-30"></div>
                    <pre><code>{msg.sql}</code></pre>
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-full bg-primary-neon/10 border border-primary-neon/30 text-primary-neon flex items-center justify-center shrink-0">
                <Server className="w-5 h-5 animate-pulse" />
              </div>
              <div className="px-5 py-4 bg-surface border border-surface-high rounded-2xl rounded-tl-none flex items-center gap-2">
                <div className="w-2 h-2 bg-primary-neon rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-primary-neon rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-primary-neon rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          )}
          <div ref={endOfMessagesRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-surface-high bg-surface/80 backdrop-blur-md">
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Query the telemetry index..." 
              className="w-full bg-surface border border-primary-container/30 pl-6 pr-16 py-4 rounded-xl outline-none focus:border-primary-neon focus:ring-1 focus:ring-primary-neon/30 transition-all text-on-surface shadow-[inset_0_2px_4px_rgba(0,0,0,0.3)]"
            />
            <button 
              type="submit"
              disabled={isLoading || !input.trim()}
              className="absolute right-3 w-10 h-10 bg-primary-neon hover:bg-primary-container disabled:bg-surface-high disabled:text-on-surface-variant disabled:cursor-not-allowed text-background rounded-lg flex items-center justify-center transition-colors shadow-[0_0_10px_rgba(0,255,157,0.3)]"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
          <div className="text-center mt-3 text-xs font-mono text-on-surface-variant/60 flex items-center justify-center gap-2">
            <Database className="w-3 h-3" /> READ-ONLY BYPASS MODE ACTIVE
          </div>
        </div>
      </div>
    </div>
  );
}
