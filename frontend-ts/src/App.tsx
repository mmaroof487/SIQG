import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from "react-router-dom";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import QueryPage from "./pages/QueryPage";
import DashboardPage from "./pages/DashboardPage";
import HealthPage from "./pages/HealthPage";
import AdminPage from "./pages/AdminPage";
import LoginPage from "./pages/LoginPage";
import ChatPanelPage from "./pages/ChatPanelPage";
import SchemaBrowserPage from "./pages/SchemaBrowserPage";
import QueryLibraryPage from "./pages/QueryLibraryPage";
import SettingsPage from "./pages/SettingsPage";
import { SettingsProvider } from "./contexts/SettingsContext";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("token");
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <div className="flex flex-col min-h-screen bg-surface-low text-on-surface font-sans selection:bg-primary-neon/30">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 max-w-full">
          <div className="mx-auto max-w-7xl h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <SettingsProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          
          <Route path="/" element={<RequireAuth><QueryPage /></RequireAuth>} />
          <Route path="/chat" element={<RequireAuth><ChatPanelPage /></RequireAuth>} />
          <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
          <Route path="/health" element={<RequireAuth><HealthPage /></RequireAuth>} />
          <Route path="/schema" element={<RequireAuth><SchemaBrowserPage /></RequireAuth>} />
          <Route path="/library" element={<RequireAuth><QueryLibraryPage /></RequireAuth>} />
          <Route path="/admin" element={<RequireAuth><AdminPage /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />
        </Routes>
      </Router>
    </SettingsProvider>
  );
}

export default App;
