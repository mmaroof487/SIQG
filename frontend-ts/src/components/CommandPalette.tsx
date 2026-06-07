import { useEffect, useState } from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import { Search, Database, Home, Shield, Settings, DatabaseBackup, Command as CmdIcon } from 'lucide-react';

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-background/80 backdrop-blur-sm flex items-start justify-center pt-[20vh] animate-in fade-in duration-200" onClick={() => setOpen(false)}>
      <div className="w-full max-w-2xl bg-surface/90 backdrop-blur-xl border border-surface-high rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.5)] overflow-hidden ring-1 ring-white/5 animate-in slide-in-from-top-4 duration-300" onClick={e => e.stopPropagation()}>
        <Command className="w-full" shouldFilter={true}>
          <div className="flex items-center px-4 border-b border-surface-high">
            <Search className="w-5 h-5 text-on-surface-variant" />
            <Command.Input 
              placeholder="Search databases, execute commands..." 
              className="w-full bg-transparent border-0 px-4 py-5 text-on-surface outline-none placeholder-on-surface-variant text-lg" 
              autoFocus
            />
            <div className="flex gap-1 shrink-0">
              <kbd className="bg-surface-high text-on-surface-variant px-2 py-1 rounded text-xs font-mono font-bold tracking-wider">ESC</kbd>
            </div>
          </div>
          <Command.List className="max-h-[60vh] overflow-y-auto p-2">
            <Command.Empty className="py-12 text-center text-sm text-on-surface-variant font-mono">No results found.</Command.Empty>
            
            <Command.Group heading="Navigation" className="text-xs font-bold uppercase tracking-wider text-on-surface-variant px-2 py-3">
              <Command.Item 
                onSelect={() => runCommand(() => navigate('/'))}
                className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer aria-selected:bg-surface-high/50 text-on-surface transition-colors"
              >
                <Home className="w-5 h-5 text-primary-neon" /> Home
              </Command.Item>
              <Command.Item 
                onSelect={() => runCommand(() => navigate('/schema'))}
                className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer aria-selected:bg-surface-high/50 text-on-surface transition-colors"
              >
                <Database className="w-5 h-5 text-primary-neon" /> Schema Explorer
              </Command.Item>
              <Command.Item 
                onSelect={() => runCommand(() => navigate('/connections'))}
                className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer aria-selected:bg-surface-high/50 text-on-surface transition-colors"
              >
                <DatabaseBackup className="w-5 h-5 text-primary-container" /> Connections
              </Command.Item>
              <Command.Item 
                onSelect={() => runCommand(() => navigate('/admin'))}
                className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer aria-selected:bg-surface-high/50 text-on-surface transition-colors"
              >
                <Shield className="w-5 h-5 text-error" /> Governance
              </Command.Item>
              <Command.Item 
                onSelect={() => runCommand(() => navigate('/settings'))}
                className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer aria-selected:bg-surface-high/50 text-on-surface transition-colors"
              >
                <Settings className="w-5 h-5 text-on-surface-variant" /> Settings
              </Command.Item>
            </Command.Group>
            
            <Command.Group heading="Actions" className="text-xs font-bold uppercase tracking-wider text-on-surface-variant px-2 py-3 mt-2 border-t border-surface-high/50">
              <Command.Item 
                onSelect={() => runCommand(() => navigate('/?focus=query'))}
                className="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer aria-selected:bg-surface-high/50 text-on-surface transition-colors"
              >
                <CmdIcon className="w-5 h-5 text-primary-container" /> New Query...
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
