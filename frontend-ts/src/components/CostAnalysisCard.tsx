import React from "react";
import { BadgeDollarSign } from "lucide-react";

interface CostAnalysisCardProps {
  status: 'pending' | 'calculated' | 'error' | 'blocked';
  cost?: number;
  rows?: number;
  runtime?: number;
}

export default function CostAnalysisCard({ status, cost, rows, runtime }: CostAnalysisCardProps) {
  if (status === 'pending') {
    return (
      <div className="bg-surface/60 border border-surface-high rounded-xl p-3 shadow-sm animate-pulse">
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-3.5 h-3.5 rounded-full border-2 border-primary-neon/50 border-t-primary-neon animate-spin" />
          <div className="h-3 w-20 bg-surface-high rounded" />
        </div>
        <div className="h-2.5 w-40 bg-surface-high/50 rounded mt-2" />
      </div>
    );
  }

  const isError = status === 'error' || status === 'blocked';
  const isHighCost = !isError && cost !== undefined && cost > 500;
  const isMediumCost = !isError && cost !== undefined && cost > 100 && cost <= 500;

  return (
    <div className={`border rounded-xl p-3 shadow-sm ${
      isError ? 'bg-surface/40 border-surface-high/50 opacity-80' :
      isHighCost ? 'bg-error/5 border-error/30' :
      isMediumCost ? 'bg-warning/5 border-warning/30' :
      'bg-surface/60 border-surface-high'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <BadgeDollarSign className={`w-3.5 h-3.5 ${isError ? 'text-on-surface-variant/50' : isHighCost ? 'text-error' : isMediumCost ? 'text-warning' : 'text-on-surface-variant'}`} />
          <h3 className="text-[10px] uppercase font-bold tracking-widest text-on-surface-variant">
            Cost Analysis
          </h3>
        </div>
        
        {!isError && cost !== undefined && (
          <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded border ${
            isHighCost ? 'bg-error/10 text-error border-error/30' :
            isMediumCost ? 'bg-warning/10 text-warning border-warning/30' :
            'bg-surface-high/50 text-on-surface-variant border-surface-high'
          }`}>
            {isHighCost ? 'High' : isMediumCost ? 'Medium' : 'Low'}
          </span>
        )}
        {isError && (
          <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded border bg-surface-high/30 text-on-surface-variant/50 border-surface-high/50">
            N/A
          </span>
        )}
      </div>

      {!isError && (
        <div className="space-y-2 font-mono text-xs">
          <div className="flex justify-between items-center pb-1.5 border-b border-surface-high">
            <span className="text-on-surface-variant">Estimated Rows</span>
            <span className="text-on-surface">{rows !== undefined ? rows.toLocaleString() : '-'}</span>
          </div>
          <div className="flex justify-between items-center pb-1.5 border-b border-surface-high">
            <span className="text-on-surface-variant">Expected Runtime</span>
            <span className="text-on-surface">{runtime !== undefined ? `${runtime.toFixed(1)}ms` : '-'}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-on-surface-variant">Query Cost</span>
            <span className={isHighCost ? 'text-error font-bold' : isMediumCost ? 'text-warning font-bold' : 'text-primary-neon font-bold'}>
              {cost !== undefined ? `${cost.toFixed(2)} units` : '-'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
