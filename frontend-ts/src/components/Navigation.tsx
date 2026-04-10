import { NavLink } from 'react-router-dom';
import { Shield, Activity, TerminalSquare, Settings, LogOut } from 'lucide-react';
import clsx from 'clsx';
import { api } from '../utils/api';

export default function Navigation() {
  const handleLogout = () => {
    api.logout();
    window.location.reload();
  };

  const navClass = ({ isActive }: { isActive: boolean }) =>
    clsx(
      "flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-300 font-medium",
      isActive
        ? "bg-primary-neon/10 text-primary-neon shadow-[0_0_15px_rgba(0,255,157,0.1)] ring-1 ring-primary-neon/30"
        : "text-on-surface hover:bg-surface-high hover:text-primary-container"
    );

  return (
    <nav className="bg-surface/60 backdrop-blur-md border-b border-surface-high sticky top-0 z-50">
      <div className="container mx-auto px-4 max-w-7xl h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_rgba(0,255,157,0.5)]" />
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary-neon to-primary-container bg-clip-text text-transparent drop-shadow">
            Argus / SIQG
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <NavLink to="/" className={navClass}>
            <TerminalSquare className="w-4 h-4" />
            Query
          </NavLink>
          <NavLink to="/dashboard" className={navClass}>
            <Activity className="w-4 h-4" />
            Metrics
          </NavLink>
          <NavLink to="/health" className={navClass}>
            <Shield className="w-4 h-4" />
            Health
          </NavLink>
          <NavLink to="/admin" className={navClass}>
            <Settings className="w-4 h-4" />
            Admin
          </NavLink>
        </div>

        <button 
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 text-on-surface-variant hover:text-error hover:bg-error/10 rounded-lg transition-colors border border-transparent hover:border-error/30"
        >
          <LogOut className="w-4 h-4" />
          <span className="text-sm font-medium">Logout</span>
        </button>
      </div>
    </nav>
  );
}
