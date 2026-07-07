import { Search, ChevronDown } from 'lucide-react';
import { useEffect, useState, useRef } from 'react';
import { useSettings } from '../contexts/SettingsContext';
import { api } from '../utils/api';

type HealthStatus = 'checking' | 'healthy' | 'degraded' | 'down';

export default function Header() {
  const { mode, toggleMode, role, setRole } = useSettings();
  const [isRoleDropdownOpen, setIsRoleDropdownOpen] = useState(false);
  const roleDropdownRef = useRef<HTMLDivElement>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus>('checking');

  // Poll actual /health endpoint every 30s
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await api.checkHealth();
        const status = res.data?.status;
        if (status === 'ok') setHealthStatus('healthy');
        else if (status === 'degraded') setHealthStatus('degraded');
        else setHealthStatus('down');
      } catch {
        setHealthStatus('down');
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (roleDropdownRef.current && !roleDropdownRef.current.contains(event.target as Node)) {
        setIsRoleDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const healthConfig: Record<HealthStatus, { dot: string; text: string; label: string }> = {
    checking: { dot: 'bg-yellow-400 animate-pulse', text: 'text-yellow-400', label: 'Checking...' },
    healthy:  { dot: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]', text: 'text-emerald-400', label: 'System Healthy' },
    degraded: { dot: 'bg-yellow-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]', text: 'text-yellow-400', label: 'Degraded' },
    down:     { dot: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]',     text: 'text-red-400',   label: 'System Down' },
  };

  const hc = healthConfig[healthStatus];

  return (
    <header className="bg-surface/90 backdrop-blur-md border-b border-surface-high sticky top-0 z-50 h-16 flex justify-between items-center px-6 shadow-sm">
      {/* Left */}
      <div className="flex items-center gap-3 flex-1">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="Argus Logo" className="w-8 h-8 object-contain drop-shadow-[0_0_8px_rgba(0,255,157,0.5)]" />
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary-neon to-primary-container bg-clip-text text-transparent drop-shadow">
            Argus
          </span>
        </div>
      </div>

      {/* Center - Command Palette */}
      <div className="flex-1 flex justify-center max-w-2xl w-full px-4 hidden md:flex">
        <button
          onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true, ctrlKey: true, bubbles: true }))}
          className="w-full max-w-md bg-surface-high/50 hover:bg-surface-high transition-colors border border-surface-high rounded-lg px-4 py-2 flex items-center justify-between group cursor-text"
        >
          <div className="flex items-center gap-2 text-on-surface-variant group-hover:text-primary-neon transition-colors">
            <Search className="w-4 h-4" />
            <span className="text-sm">Ask Argus...</span>
          </div>
          <div className="flex items-center gap-1 opacity-70">
            <kbd className="bg-surface border border-surface-high rounded px-1.5 py-0.5 text-xs font-medium font-sans text-on-surface-variant">⌘</kbd>
            <kbd className="bg-surface border border-surface-high rounded px-1.5 py-0.5 text-xs font-medium font-sans text-on-surface-variant">K</kbd>
          </div>
        </button>
      </div>

      {/* Right - Controls */}
      <div className="flex items-center gap-4 flex-1 justify-end shrink-0">
        {/* Real System Health Badge */}
        <div className={`hidden lg:flex shrink-0 whitespace-nowrap items-center gap-2 text-xs font-medium mr-2 border border-surface-high bg-surface-high/20 px-3 py-1.5 rounded-full`}>
          <div className={`w-2 h-2 rounded-full shrink-0 ${hc.dot}`}></div>
          <span className={hc.text}>{hc.label}</span>
        </div>

        {/* Role Switcher */}
        <div className="flex shrink-0 whitespace-nowrap items-center gap-2 bg-surface-high/50 rounded-lg px-3 py-1.5 border border-surface-high relative" ref={roleDropdownRef}>
          <span className="text-xs text-on-surface-variant font-medium hidden xl:block">Viewing as:</span>
          <button
            type="button"
            onClick={() => setIsRoleDropdownOpen(!isRoleDropdownOpen)}
            className="flex items-center gap-1 bg-transparent text-sm text-on-surface font-semibold outline-none cursor-pointer hover:text-primary-neon transition-colors"
          >
            <span className="capitalize">{role}</span>
            <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isRoleDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {isRoleDropdownOpen && (
            <div className="absolute top-full right-0 mt-2 w-32 bg-surface border border-surface-high rounded-xl shadow-2xl z-50 overflow-hidden py-1 animate-in fade-in slide-in-from-top-2">
              {['admin', 'readonly', 'guest'].map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => {
                    setRole(r as any);
                    setIsRoleDropdownOpen(false);
                  }}
                  className={`w-full text-left px-4 py-2 text-sm font-medium transition-colors hover:bg-primary-neon/10 hover:text-primary-neon capitalize ${role === r ? 'bg-primary-neon/5 text-primary-neon' : 'text-on-surface'}`}
                >
                  {r}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Mode Toggle */}
        <button
          onClick={toggleMode}
          className="flex shrink-0 whitespace-nowrap items-center gap-2 group transition-all"
        >
          <div className={`shrink-0 w-10 h-5 rounded-full relative transition-colors ${mode === 'power' ? 'bg-primary-neon/30 border-primary-neon' : 'bg-surface-high border-on-surface-variant/30'} border`}>
            <div className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 rounded-full transition-transform ${mode === 'power' ? 'translate-x-5 bg-primary-neon' : 'bg-on-surface-variant'} shadow-sm`}></div>
          </div>
          <span className="text-sm font-semibold text-on-surface-variant group-hover:text-primary-neon transition-colors hidden sm:block">
            {mode === 'simple' ? 'Simple Mode' : 'Power Mode'}
          </span>
        </button>
      </div>
    </header>
  );
}
