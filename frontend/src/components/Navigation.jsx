import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Database, BarChart3, Heart, Settings } from "lucide-react";

export default function Navigation() {
	const location = useLocation();

	const isActive = (path) => {
		return location.pathname === path ? "bg-emerald-600 text-white" : "text-slate-700 hover:bg-slate-100";
	};

	return (
		<nav className="bg-white shadow-md sticky top-0 z-50">
			<div className="container mx-auto px-4">
				<div className="flex items-center justify-between h-16">
					<Link to="/" className="flex items-center gap-2">
						<Database className="w-6 h-6 text-emerald-600" />
						<span className="text-2xl font-bold text-slate-900">Argus</span>
					</Link>

					<div className="flex gap-4">
						<Link to="/" className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${isActive("/")}`}>
							<Database className="w-4 h-4" />
							Query
						</Link>
						<Link to="/dashboard" className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${isActive("/dashboard")}`}>
							<BarChart3 className="w-4 h-4" />
							Metrics
						</Link>
						<Link to="/health" className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${isActive("/health")}`}>
							<Heart className="w-4 h-4" />
							Health
						</Link>
						<Link to="/admin" className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${isActive("/admin")}`}>
							<Settings className="w-4 h-4" />
							Admin
						</Link>
					</div>
				</div>
			</div>
		</nav>
	);
}
