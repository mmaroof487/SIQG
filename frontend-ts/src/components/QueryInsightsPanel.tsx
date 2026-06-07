import React from "react";
import { Sparkles, Loader } from "lucide-react";

interface QueryInsightsPanelProps {
  insights: string | null;
  isLoading: boolean;
}

export default function QueryInsightsPanel({ insights, isLoading }: QueryInsightsPanelProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-on-surface-variant space-y-4">
        <Loader className="w-8 h-8 animate-spin text-primary-neon" />
        <p className="text-sm font-mono animate-pulse">Generating AI insights...</p>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="p-8 text-center text-on-surface-variant italic">
        Execute a query to see AI insights.
      </div>
    );
  }

  return (
    <div className="p-6 bg-surface/40 h-full overflow-y-auto">
      <div className="flex items-center gap-2 mb-6">
        <div className="p-2 bg-primary-neon/10 rounded-lg border border-primary-neon/30">
          <Sparkles className="w-5 h-5 text-primary-neon" />
        </div>
        <h3 className="text-lg font-bold text-on-surface">AI Insights</h3>
      </div>
      
      <div className="prose prose-invert prose-p:text-on-surface-variant prose-li:text-on-surface-variant max-w-none prose-strong:text-on-surface">
        {insights.split('\n').map((paragraph, index) => {
          if (paragraph.startsWith('- ')) {
            return (
              <ul key={index} className="list-disc pl-5 mb-2 text-sm leading-relaxed">
                <li className="mb-1">{paragraph.substring(2)}</li>
              </ul>
            );
          }
          return paragraph ? <p key={index} className="text-sm leading-relaxed mb-4">{paragraph}</p> : null;
        })}
      </div>
    </div>
  );
}
