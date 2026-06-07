import React from "react";
import { ShieldAlert, ShieldCheck } from "lucide-react";

interface SecurityAnalysisCardProps {
  status: 'pending' | 'safe' | 'warning' | 'error';
  reasons?: string[];
}

export default function SecurityAnalysisCard({ status, reasons }: SecurityAnalysisCardProps) {
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

  const isSafe = status === 'safe';
  const isWarning = status === 'warning';

  return (
    <div className={`border rounded-xl p-3 shadow-sm ${
      isSafe ? 'bg-primary-neon/5 border-primary-neon/30' :
      isWarning ? 'bg-warning/5 border-warning/30' :
      'bg-error/5 border-error/30'
    }`}>
      <div className="flex items-center gap-2 mb-2">
        {isSafe ? <ShieldCheck className="w-3.5 h-3.5 text-primary-neon" /> : <ShieldAlert className={`w-3.5 h-3.5 ${isWarning ? 'text-warning' : 'text-error'}`} />}
        <h3 className={`text-[10px] uppercase font-bold tracking-widest ${
          isSafe ? 'text-primary-neon' : isWarning ? 'text-warning' : 'text-error'
        }`}>
          {isSafe ? 'Safe' : isWarning ? 'Warning' : 'Blocked'}
        </h3>
      </div>
      
      {reasons && reasons.length > 0 ? (
        <ul className="space-y-0.5">
          {reasons.map((reason, idx) => (
            <li key={idx} className={`text-xs ${
              isSafe ? 'text-primary-neon/80' : isWarning ? 'text-warning/80' : 'text-error/80'
            }`}>
              • {reason}
            </li>
          ))}
        </ul>
      ) : (
        <p className={`text-xs ${isSafe ? 'text-primary-neon/80' : 'text-error/80'}`}>
          {isSafe ? 'No security issues detected.' : 'Security check failed.'}
        </p>
      )}
    </div>
  );
}
