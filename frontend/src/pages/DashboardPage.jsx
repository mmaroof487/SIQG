import React from "react";
import MetricsDashboard from "../components/MetricsDashboard";

export default function DashboardPage() {
	return (
		<div className="space-y-6">
			<div>
				<h1 className="text-4xl font-bold text-slate-900 mb-2">Live Metrics</h1>
				<p className="text-slate-600">Real-time performance and system insights</p>
			</div>
			<MetricsDashboard />
		</div>
	);
}
