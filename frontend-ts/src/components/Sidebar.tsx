import { NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Home, Database, Map, ShieldAlert, User, LayoutDashboard, LineChart } from 'lucide-react';
import clsx from 'clsx';
import { useSettings } from '../contexts/SettingsContext';
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import { api } from '../utils/api';

function SidebarLink({ to, icon: Icon, label, badge, alert, isCollapsed, hoveredPath, setHoveredPath, ...props }: any) {
  const isActive = window.location.pathname.startsWith(to);
  
  return (
    <NavLink 
      to={to} 
      onMouseEnter={() => setHoveredPath(to)}
      onMouseLeave={() => setHoveredPath(null)}
      className={clsx(
        "relative w-full h-12 shrink-0 flex items-center px-6 transition-colors duration-300 font-medium whitespace-nowrap text-sm group",
        isActive
          ? "text-primary-neon"
          : "text-on-surface hover:text-primary-container",
        isCollapsed ? "justify-center" : "gap-3"
      )}
      title={isCollapsed ? label + (badge ? ` (${badge})` : '') + (alert ? ' (Alerts)' : '') : ""}
      {...props}
    >
      <AnimatePresence>
        {hoveredPath === to && (
          <div className="absolute inset-0 pointer-events-none z-0">
            <motion.div
              layoutId="sidebar-hover-bg"
              className="absolute inset-0 bg-surface-high/50 border-y border-surface-high/50"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
            />
          </div>
        )}
      </AnimatePresence>

      <div className="relative z-10 flex items-center w-full">
        <motion.div 
          className="relative"
          animate={{ x: isCollapsed ? 6 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <Icon className="w-5 h-5 flex-shrink-0" />
          {isCollapsed && alert && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-error rounded-full border-2 border-surface"></span>}
        </motion.div>
        
        <AnimatePresence initial={false}>
          {!isCollapsed && (
            <motion.div
              initial={{ width: 0, opacity: 0, marginLeft: 0 }}
              animate={{ width: "auto", opacity: 1, marginLeft: 12 }}
              exit={{ width: 0, opacity: 0, marginLeft: 0 }}
              transition={{ duration: 0.3 }}
              className="flex flex-1 items-center justify-between overflow-hidden"
            >
              <span>{label}</span>
              {badge && (
                <span className="px-2 py-0.5 rounded-md bg-surface-high text-[10px] font-bold text-on-surface-variant">
                  {badge}
                </span>
              )}
              {alert && (
                <span className="w-2 h-2 rounded-full bg-error shadow-[0_0_8px_rgba(255,82,82,0.6)]"></span>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </NavLink>
  );
}

export default function Sidebar() {
  const { role } = useSettings();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [hoveredPath, setHoveredPath] = useState<string | null>(null);
  const [connectionsCount, setConnectionsCount] = useState<number | null>(null);
  
  useEffect(() => {
    const fetchCount = () => {
      api.getConnections().then(res => {
        const active = res.data.filter((c: any) => c.is_active);
        setConnectionsCount(active.length);
      }).catch(() => {});
    };
    
    fetchCount();
    window.addEventListener('connectionsUpdated', fetchCount);
    return () => window.removeEventListener('connectionsUpdated', fetchCount);
  }, []);

  const linkProps = { isCollapsed, hoveredPath, setHoveredPath };

  return (
    <motion.aside 
      initial={false}
      animate={{ width: isCollapsed ? 80 : 220 }}
      onUpdate={(latest) => {
        if (latest.width) {
          document.documentElement.style.setProperty('--sidebar-width', `${latest.width}px`);
        }
      }}
      className="flex-shrink-0 border-r border-surface-high h-[calc(100vh-4rem)] sticky top-16 flex flex-col bg-surface/40 backdrop-blur-sm py-4 gap-2 z-40 relative"
    >
      <LayoutGroup id="sidebar-hover-group">
      <div className="flex flex-col relative z-10">
        <SidebarLink to="/dashboard" icon={LayoutDashboard} label="Dashboard" {...linkProps} />
        <SidebarLink to="/query" icon={Home} label="Query Studio" {...linkProps} />
        <SidebarLink 
          to="/connections" 
          icon={Database} 
          label="Connections" 
          badge={connectionsCount !== null ? connectionsCount.toString() : undefined} 
          {...linkProps} 
        />
        <SidebarLink to="/schema" icon={Map} label="Schema Explorer" {...linkProps} />

        {role === 'admin' && (
          <>
            <div className="w-full h-px bg-surface-high my-2"></div>
            {!isCollapsed && <div className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 px-6 truncate">Governance</div>}
            
            <SidebarLink to="/admin" icon={ShieldAlert} label="Security Center" alert {...linkProps} />
            <SidebarLink to="/health" icon={LineChart} label="Observability" {...linkProps} />
          </>
        )}
      </div>

      <div className="mt-auto flex flex-col relative z-10">
        <div className="w-full h-px bg-surface-high"></div>
        <SidebarLink to="/settings" icon={User} label="Account" {...linkProps} />
      </div>

      {/* Organic Bulge Toggle */}
      <div className="absolute top-0 right-0 w-4 h-full flex items-center justify-center z-50">
        <div className="absolute right-0 top-1/2 -translate-y-1/2 w-[48px] h-[140px] pointer-events-none translate-x-[24px]">
          <svg width="48" height="140" viewBox="-24 0 48 140" fill="none" xmlns="http://www.w3.org/2000/svg" className="absolute top-0 left-0 w-full h-full">
            {/* Fill Shape */}
            <motion.path
              d={isCollapsed 
                  ? "M5 0 V140 H0 C0 100 -20 100 -20 70 C-20 40 0 40 0 0 H5 Z" 
                  : "M-5 0 V140 H0 C0 100 20 100 20 70 C20 40 0 40 0 0 H-5 Z"
                }
              className="fill-[#0c0c0e]" // Match bg-surface roughly
              transition={{ duration: 0.3, ease: "easeInOut" }}
            />
            {/* Border Stroke */}
            <motion.path
              d={isCollapsed 
                  ? "M0 0 C0 40 -20 40 -20 70 C-20 100 0 100 0 140" 
                  : "M0 0 C0 40 20 40 20 70 C20 100 0 100 0 140"
                }
              className="stroke-surface-high"
              strokeWidth="1"
              fill="none"
              transition={{ duration: 0.3, ease: "easeInOut" }}
            />
          </svg>
        </div>
        <div
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="absolute right-0 translate-x-2 top-1/2 -translate-y-1/2 p-1 cursor-pointer transition-colors duration-300 flex items-center justify-center z-[9999] text-on-surface-variant hover:text-primary-neon"
        >
          <motion.svg
            className="w-3.5 h-3.5 text-on-surface"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            animate={{ rotate: isCollapsed ? 180 : 0 }}
            transition={{
              rotate: { duration: 0.3 }
            }}
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </motion.svg>
        </div>
        </div>
      </LayoutGroup>
    </motion.aside>
  );
}
