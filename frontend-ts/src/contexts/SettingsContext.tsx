import { createContext, useContext, useState, ReactNode } from 'react';

type Mode = 'simple' | 'power';
type Role = 'admin' | 'readonly' | 'guest';

interface SettingsContextType {
  mode: Mode;
  toggleMode: () => void;
  role: Role;
  setRole: (role: Role) => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>('simple');
  const [role, setRole] = useState<Role>('admin');

  const toggleMode = () => {
    setMode(prev => prev === 'simple' ? 'power' : 'simple');
  };

  return (
    <SettingsContext.Provider value={{ mode, toggleMode, role, setRole }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
