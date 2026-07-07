import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from "react-router-dom";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import QueryPage from "./pages/QueryPage";
import HealthPage from "./pages/HealthPage";
import AdminPage from "./pages/AdminPage";
import LoginPage from "./pages/LoginPage";
import SchemaBrowserPage from "./pages/SchemaBrowserPage";
import SettingsPage from "./pages/SettingsPage";
import ConnectionsPage from "./pages/ConnectionsPage";
import DashboardPage from "./pages/DashboardPage";
import { SettingsProvider } from "./contexts/SettingsContext";
import { AuthProvider, useAuth } from "./contexts/AuthContext";

import { CommandPalette } from "./components/CommandPalette";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div className="h-screen w-screen flex items-center justify-center bg-surface-low text-primary-neon">Loading...</div>;

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <div className="flex flex-col h-screen bg-surface-low text-on-surface font-sans selection:bg-primary-neon/30">
      <CommandPalette />
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main id="main-content" className="flex-1 overflow-y-auto p-6 max-w-full relative">
          <div className="mx-auto max-w-7xl h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

/**
 * Wraps a route so only users with role=="admin" can access it.
 * Non-admin authenticated users are redirected to /dashboard.
 * Must be used inside RequireAuth (which handles unauthenticated redirects).
 */
function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { role, loading } = useAuth();
  if (loading) return null;
  if (role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <AuthProvider>
      <SettingsProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
            <Route path="/query" element={<RequireAuth><QueryPage /></RequireAuth>} />
            <Route path="/connections" element={<RequireAuth><ConnectionsPage /></RequireAuth>} />
            <Route path="/health" element={<RequireAuth><HealthPage /></RequireAuth>} />
            <Route path="/schema" element={<RequireAuth><SchemaBrowserPage /></RequireAuth>} />
            <Route path="/admin" element={<RequireAuth><RequireAdmin><AdminPage /></RequireAdmin></RequireAuth>} />
            <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />
            
            {/* Catch-all route */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Router>
      </SettingsProvider>
    </AuthProvider>
  );
}

export default App;
