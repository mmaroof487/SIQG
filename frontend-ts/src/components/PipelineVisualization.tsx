import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Code2, ShieldAlert, BadgeDollarSign, DatabaseZap, Play } from "lucide-react";

interface PipelineVisualizationProps {
  currentStage: string; // 'question' | 'sql' | 'security' | 'cost' | 'cache' | 'execute' | 'done' | 'error'
  securityStatus: 'pending' | 'safe' | 'warning' | 'error';
  costStatus: 'pending' | 'calculated';
  cacheStatus: 'pending' | 'hit' | 'miss';
}

const STAGES = [
  { id: 'question', label: 'Question', icon: Search },
  { id: 'sql', label: 'SQL', icon: Code2 },
  { id: 'security', label: 'Security', icon: ShieldAlert },
  { id: 'cost', label: 'Cost', icon: BadgeDollarSign },
  { id: 'cache', label: 'Cache', icon: DatabaseZap },
  { id: 'execute', label: 'Execute', icon: Play }
];

export default function PipelineVisualization({ currentStage, securityStatus, costStatus, cacheStatus }: PipelineVisualizationProps) {
  const getStageIndex = (stage: string) => {
    if (stage === 'done') return STAGES.length;
    if (stage === 'error') return -1; // Handle error explicitly if needed
    return STAGES.findIndex(s => s.id === stage);
  };

  const currentIndex = getStageIndex(currentStage);

  return (
    <div className="w-full py-4">
      <div className="flex items-center justify-between max-w-4xl mx-auto relative">
        {/* Connecting lines background */}
        <div className="absolute top-6 left-0 right-0 h-0.5 bg-surface-high/50 -z-10" />
        
        {/* Animated progress line */}
        <div 
          className="absolute top-6 left-0 h-0.5 bg-gradient-to-r from-primary-neon to-primary-container transition-all duration-500 ease-in-out -z-10 shadow-[0_0_8px_rgba(0,255,157,0.5)]" 
          style={{ width: `${Math.max(0, currentIndex === STAGES.length ? 100 : (currentIndex / (STAGES.length - 1)) * 100)}%` }}
        />

        {STAGES.map((step, idx) => {
          const isCompleted = currentIndex > idx;
          const isCurrent = currentIndex === idx;
          const isPending = currentIndex < idx;
          const isError = currentStage === 'error' && isCurrent;

          let statusColor = isCompleted ? 'text-primary-neon border-primary-neon bg-primary-neon/10' :
                            isCurrent ? 'text-surface border-primary-neon bg-primary-neon shadow-[0_0_15px_rgba(0,255,157,0.5)]' :
                            isError ? 'text-error border-error bg-error/10' :
                            'text-on-surface-variant border-surface-high bg-surface';

          // Special handling for security stage colors when completed
          if (step.id === 'security' && isCompleted) {
            if (securityStatus === 'warning') statusColor = 'text-warning border-warning bg-warning/10';
            if (securityStatus === 'error') statusColor = 'text-error border-error bg-error/10 shadow-[0_0_15px_rgba(255,82,82,0.3)]';
          }

          const Icon = step.icon;

          return (
            <div key={step.id} className="flex flex-col items-center gap-3 relative group">
              <motion.div 
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: idx * 0.1 }}
                className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${statusColor} ${isCurrent && !isError ? 'animate-pulse' : ''}`}
              >
                <Icon className={`w-5 h-5 ${isCurrent ? 'text-surface' : ''}`} />
              </motion.div>
              
              <div className="flex flex-col items-center">
                <span className={`text-xs font-bold uppercase tracking-wider transition-colors duration-300 ${isCurrent ? 'text-primary-neon' : isCompleted ? 'text-on-surface' : 'text-on-surface-variant'}`}>
                  {step.label}
                </span>
                
                {/* Status sub-label */}
                <div className="h-4 mt-1">
                  <AnimatePresence mode="wait">
                    {step.id === 'security' && securityStatus === 'safe' && isCompleted && (
                      <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-[10px] font-mono text-primary-neon">SAFE</motion.span>
                    )}
                    {step.id === 'security' && securityStatus === 'warning' && isCompleted && (
                      <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-[10px] font-mono text-warning">WARNING</motion.span>
                    )}
                    {step.id === 'security' && securityStatus === 'error' && (
                      <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-[10px] font-mono text-error">BLOCKED</motion.span>
                    )}
                    {step.id === 'cache' && cacheStatus === 'hit' && isCompleted && (
                      <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-[10px] font-mono text-primary-neon">HIT</motion.span>
                    )}
                    {step.id === 'cache' && cacheStatus === 'miss' && isCompleted && (
                      <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-[10px] font-mono text-on-surface-variant">MISS</motion.span>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
