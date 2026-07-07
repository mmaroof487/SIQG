import React from "react";
import { BadgeDollarSign, ShieldCheck } from "lucide-react";

interface CostAnalysisCardProps {
  status: 'pending' | 'calculated' | 'error' | 'blocked';
  cost?: number;
  rows?: number;
  runtime?: number;
  encryptionStats?: {
    values_encrypted?: number;
    columns_encrypted?: string[];
    values_decrypted?: number;
    columns_decrypted?: string[];
    operation_time_ms?: number;
    algorithm?: string;
    key_version?: number;
  };
}

function StatRow({
  label,
  value,
  valueClass = "text-on-surface",
  title,
  dot,
}: {
  label: React.ReactNode;
  value: React.ReactNode;
  valueClass?: string;
  title?: string;
  dot?: boolean;
}) {
  return (
    <div className="flex justify-between items-center pb-1.5 border-b border-surface-high last:border-b-0 last:pb-0">
      <span className={`text-on-surface-variant flex items-center gap-1.5`} title={title}>
        {dot && <div className="w-1.5 h-1.5 rounded-full bg-primary-neon shadow-[0_0_5px_#00FF9D] shrink-0" />}
        {label}
      </span>
      <span className={`font-bold ${valueClass}`}>{value}</span>
    </div>
  );
}

export default function CostAnalysisCard({ status, cost, rows, runtime, encryptionStats }: CostAnalysisCardProps) {
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

  const hasEncryption = encryptionStats && (encryptionStats.values_encrypted ?? 0) > 0;
  const hasDecryption = encryptionStats && (encryptionStats.values_decrypted ?? 0) > 0;
  const hasCryptoOp = hasEncryption || hasDecryption;

  return (
    <div className={`border rounded-xl p-3 shadow-sm ${
      isError ? 'bg-surface/40 border-surface-high/50 opacity-80' :
      isHighCost ? 'bg-error/5 border-error/30' :
      isMediumCost ? 'bg-warning/5 border-warning/30' :
      'bg-surface/60 border-surface-high'
    }`}>
      {/* Header */}
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
        <div className="space-y-0 font-mono text-xs">
          {rows !== undefined && (
            <StatRow label="Rows Returned" value={rows.toLocaleString()} />
          )}
          <StatRow
            label="Query Runtime"
            value={runtime !== undefined ? `${runtime.toFixed(1)}ms` : '-'}
          />
          <StatRow
            label="Query Cost"
            value={cost !== undefined ? `${cost.toFixed(2)} units` : '-'}
            valueClass={isHighCost ? 'text-error' : isMediumCost ? 'text-warning' : 'text-primary-neon'}
          />

          {/* ── Encryption Section ── */}
          {hasCryptoOp && (
            <>
              {/* Divider */}
              <div className="pt-2 pb-1">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3 h-3 text-primary-neon" />
                  <span className="text-[9px] uppercase tracking-widest text-primary-neon font-bold">Encryption</span>
                </div>
              </div>

              {hasEncryption && (
                <StatRow
                  label="Values Encrypted"
                  value={encryptionStats!.values_encrypted!}
                  valueClass="text-primary-neon"
                  dot
                  title={`Columns: ${(encryptionStats!.columns_encrypted || []).join(', ')}`}
                />
              )}
              {hasDecryption && (
                <StatRow
                  label="Values Decrypted"
                  value={encryptionStats!.values_decrypted!}
                  valueClass="text-primary-neon"
                  dot
                  title={`Columns: ${(encryptionStats!.columns_decrypted || []).join(', ')}`}
                />
              )}
              {(encryptionStats!.operation_time_ms ?? 0) > 0 && (
                <StatRow
                  label={hasEncryption ? "Encrypt Time" : "Decrypt Time"}
                  value={`${encryptionStats!.operation_time_ms!.toFixed(3)}ms`}
                  valueClass="text-on-surface"
                />
              )}
              {encryptionStats!.algorithm && (
                <StatRow
                  label="Algorithm"
                  value={encryptionStats!.algorithm}
                  valueClass="text-on-surface"
                />
              )}
              {encryptionStats!.key_version != null && (
                <StatRow
                  label="Key Version"
                  value={`v${encryptionStats!.key_version}`}
                  valueClass="text-on-surface"
                />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
