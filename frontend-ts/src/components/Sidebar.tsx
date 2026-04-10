import { NavLink } from 'react-router-dom';
import { TerminalSquare, MessageSquare, Activity, Database, Library, Settings as SettingsIcon, Shield } from 'lucide-react';
import clsx from 'clsx';
import { useSettings } from '../contexts/SettingsContext';

export default function Sidebar() {
  const { role } = useSettings();
  
  const navClass = ({ isActive }: { isActive: boolean }) =>
    clsx(
      "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 font-medium whitespace-nowrap overflow-hidden text-sm",
      isActive
        ? "bg-primary-neon/10 text-primary-neon shadow-[0_0_15px_rgba(0,255,157,0.05)] ring-1 ring-primary-neon/30"
        : "text-on-surface hover:bg-surface-high hover:text-primary-container"
    );

  return (
    <aside className="w-64 flex-shrink-0 border-r border-surface-high h-[calc(100vh-4rem)] sticky top-16 flex flex-col bg-surface/40 backdrop-blur-sm p-4 gap-2">
      <div className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 px-4">Workspace</div>
      
      <NavLink to="/" className={navClass}>
        <TerminalSquare className="w-5 h-5 flex-shrink-0" />
        Query Matrix
      </NavLink>
      
      <NavLink to="/chat" className={navClass}>
        <MessageSquare className="w-5 h-5 flex-shrink-0" />
        NL→SQL Chat
      </NavLink>

      <NavLink to="/dashboard" className={navClass}>
        <Activity className="w-5 h-5 flex-shrink-0" />
        Dashboard
      </NavLink>

      <NavLink to="/schema" className={navClass}>
        <Database className="w-5 h-5 flex-shrink-0" />
        Schema Browser
      </NavLink>

      <NavLink to="/library" className={navClass}>
        <Library className="w-5 h-5 flex-shrink-0" />
        Query Library
      </NavLink>

      {role === 'admin' && (
        <>
          <div className="w-full h-px bg-surface-high my-2"></div>
          <div className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 px-4">Governance</div>
          <NavLink to="/admin" className={navClass}>
            <Shield className="w-5 h-5 flex-shrink-0" />
            Admin Console
          </NavLink>
        </>
      )}

      <div className="mt-auto">
        <NavLink to="/settings" className={navClass}>
          <SettingsIcon className="w-5 h-5 flex-shrink-0" />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
