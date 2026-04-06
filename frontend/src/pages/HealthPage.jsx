import React from "react";
import HealthStatus from "../components/HealthStatus";

export default function HealthPage() {
	return (
		<div className="space-y-6">
			<div>
				<h1 className="text-4xl font-bold text-slate-900 mb-2">System Health</h1>
				<p className="text-slate-600">Infrastructure status and connectivity</p>
			</div>
			<HealthStatus />
		</div>
	);
}
