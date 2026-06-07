import React from "react";
import { CheckCircle2, Clock } from "lucide-react";

interface AuditEvent {
  id: string;
  stage: string;
  timestamp: string;
  duration?: string;
  status: 'success' | 'warning' | 'error';
  details?: string;
}

interface AuditTimelineProps {
  events: AuditEvent[];
}

export default function AuditTimeline({ events }: AuditTimelineProps) {
  if (!events || events.length === 0) {
    return (
      <div className="p-8 text-center text-on-surface-variant italic">
        Execute a query to see the audit trail.
      </div>
    );
  }

  return (
    <div className="p-6 bg-surface/40 h-full overflow-y-auto">
      <div className="flex items-center gap-2 mb-8">
        <div className="p-2 bg-primary-neon/10 rounded-lg border border-primary-neon/30">
          <Clock className="w-5 h-5 text-primary-neon" />
        </div>
        <h3 className="text-lg font-bold text-on-surface">Audit Trail</h3>
      </div>
      
      <div className="relative pl-4 border-l-2 border-surface-high space-y-8">
        {events.map((event, idx) => (
          <div key={event.id} className="relative">
            {/* Timeline dot */}
            <div className={`absolute -left-[21px] top-1 w-3 h-3 rounded-full border-2 bg-surface ${
              event.status === 'success' ? 'border-primary-neon' :
              event.status === 'warning' ? 'border-warning' :
              'border-error'
            }`} />
            
            <div className="flex flex-col">
              <div className="flex items-center gap-3">
                <span className={`text-sm font-bold uppercase tracking-wider ${
                  event.status === 'success' ? 'text-primary-neon' :
                  event.status === 'warning' ? 'text-warning' :
                  'text-error'
                }`}>
                  {event.stage}
                </span>
                <span className="text-xs font-mono text-on-surface-variant/50">{event.timestamp}</span>
              </div>
              
              {event.details && (
                <p className="mt-1 text-sm text-on-surface-variant">{event.details}</p>
              )}
              
              {event.duration && (
                <span className="mt-2 text-[10px] uppercase font-mono tracking-widest text-on-surface-variant/70 bg-surface-high/30 inline-block self-start px-2 py-0.5 rounded border border-surface-high">
                  {event.duration}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
