import { Shield, Bell, User, LogOut, Layout } from 'lucide-react';
import { useSettings } from '../contexts/SettingsContext';
import { api } from '../utils/api';

export default function Header() {
  const { mode, toggleMode, role, setRole } = useSettings();

  const handleLogout = () => {
    api.logout();
    window.location.reload();
  };

  return (
    <header className="bg-surface/90 backdrop-blur-md border-b border-surface-high sticky top-0 z-50 h-16 flex justify-between items-center px-6 shadow-sm">
      <div className="flex items-center gap-3">
        <img src="/argus-logo.png" alt="Argus Logo" className="w-8 h-8 object-contain drop-shadow-[0_0_8px_rgba(0,255,157,0.5)]" />
        <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary-neon to-primary-container bg-clip-text text-transparent drop-shadow">
          Argus Sentinel
        </span>
      </div>

      <div className="flex items-center gap-6">
        {/* Role Switcher */}
        <div className="flex items-center gap-2 bg-surface-high/50 rounded-lg px-3 py-1.5 border border-surface-high">
          <span className="text-xs text-on-surface-variant font-medium">Viewing as:</span>
          <select 
            className="bg-transparent text-sm text-on-surface font-semibold outline-none cursor-pointer"
            value={role}
            onChange={(e) => setRole(e.target.value as any)}
          >
            <option value="admin">Admin</option>
            <option value="readonly">Readonly</option>
            <option value="guest">Guest</option>
          </select>
        </div>

        {/* Mode Toggle */}
        <button 
          onClick={toggleMode}
          className="flex items-center gap-2 group transition-all"
        >
          <div className={`w-10 h-5 rounded-full relative transition-colors ${mode === 'power' ? 'bg-primary-neon/30 border-primary-neon' : 'bg-surface-high border-on-surface-variant/30'} border`}>
            <div className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 rounded-full transition-transform ${mode === 'power' ? 'translate-x-5 bg-primary-neon' : 'bg-on-surface-variant'} shadow-sm`}></div>
          </div>
          <span className="text-sm font-semibold text-on-surface-variant group-hover:text-primary-neon transition-colors">
            {mode === 'simple' ? 'Simple Mode' : 'Power Mode'}
          </span>
        </button>

        {/* Notifications */}
        <button className="relative text-on-surface-variant hover:text-primary-neon transition-colors p-2 hover:bg-surface-high rounded-lg cursor-pointer">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full animate-pulse shadow-[0_0_8px_rgba(255,85,85,0.8)]"></span>
        </button>

        <div className="w-px h-6 bg-surface-high mx-2"></div>

        {/* User Menu */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 cursor-pointer group">
            <div className="w-8 h-8 rounded-full bg-primary-container/20 border border-primary-container/40 flex items-center justify-center">
              <User className="w-4 h-4 text-primary-container group-hover:text-primary-neon transition-colors" />
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="text-on-surface-variant hover:text-error transition-colors p-2 hover:bg-error/10 rounded-lg cursor-pointer"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
