import { useState } from "react";
import MetricsDashboard from "../components/MetricsDashboard";
import HealthStatus from "../components/HealthStatus";
import { Activity, Shield } from "lucide-react";

export default function DashboardPage() {
	const [activeTab, setActiveTab] = useState<"metrics" | "health">("metrics");

	return (
		<div className="space-y-6 animate-in fade-in duration-500">
			<div className="flex items-end gap-6 mb-2">
				<div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
					{activeTab === "metrics" ? (
						<Activity className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
					) : (
						<Shield className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
					)}
				</div>
				<div>
					<h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">Observability Dashboard</h1>
					<p className="text-on-surface-variant font-medium">Real-time performance, telemetry, and system node health</p>
				</div>
			</div>

			{/* Tabs */}
			<div className="flex gap-4 border-b border-surface-high pb-px relative">
				<button 
					onClick={() => setActiveTab("metrics")}
					className={`pb-3 px-2 text-sm font-bold uppercase tracking-wider transition-colors relative ${activeTab === "metrics" ? "text-primary-neon" : "text-on-surface-variant hover:text-on-surface"}`}
				>
					<span className="flex items-center gap-2">
						<Activity className="w-4 h-4" /> Live Metrics
					</span>
					{activeTab === "metrics" && (
						<div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary-neon shadow-[0_0_8px_#00FF9D]"></div>
					)}
				</button>
				<button 
					onClick={() => setActiveTab("health")}
					className={`pb-3 px-2 text-sm font-bold uppercase tracking-wider transition-colors relative ${activeTab === "health" ? "text-primary-neon" : "text-on-surface-variant hover:text-on-surface"}`}
				>
					<span className="flex items-center gap-2">
						<Shield className="w-4 h-4" /> System Health
					</span>
					{activeTab === "health" && (
						<div className="absolute bottom-0 left-0 w-full h-0.5 bg-primary-neon shadow-[0_0_8px_#00FF9D]"></div>
					)}
				</button>
			</div>
			
			<div className="pt-2">
				{activeTab === "metrics" ? <MetricsDashboard /> : <HealthStatus />}
			</div>
		</div>
	);
}
