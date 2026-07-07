import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../utils/api';

interface AuthContextType {
  isAuthenticated: boolean;
  role: string | null;
  loading: boolean;
  login: (auth: boolean, role: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  role: null,
  loading: true,
  login: () => {},
  logout: () => {}
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    api.getMe()
      .then((res: any) => {
        setIsAuthenticated(true);
        setRole(res.data.role || 'admin'); // Fallback role if not provided
      })
      .catch(() => {
        setIsAuthenticated(false);
        setRole(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = (auth: boolean, role: string) => {
    setIsAuthenticated(auth);
    setRole(role);
  };

  const logout = () => {
    setIsAuthenticated(false);
    setRole(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, role, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
