import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navigation from "./components/Navigation";
import QueryPage from "./pages/QueryPage";
import DashboardPage from "./pages/DashboardPage";
import HealthPage from "./pages/HealthPage";
import AdminPage from "./pages/AdminPage";
import "./index.css";

function App() {
	const token = localStorage.getItem("token");

	return (
		<Router>
			<div className="min-h-screen bg-slate-50">
				<Navigation />
				<main className="container mx-auto px-4 py-8">
					<Routes>
						<Route path="/" element={<QueryPage />} />
						<Route path="/dashboard" element={<DashboardPage />} />
						<Route path="/health" element={<HealthPage />} />
						<Route path="/admin" element={<AdminPage token={token} />} />
					</Routes>
				</main>
			</div>
		</Router>
	);
}

export default App;
