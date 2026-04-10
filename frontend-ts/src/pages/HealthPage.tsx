import HealthStatus from "../components/HealthStatus";
import { Shield } from "lucide-react";

export default function HealthPage() {
	return (
		<div className="space-y-8 animate-in fade-in duration-500">
			<div className="flex items-end gap-6 mb-4">
				<div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-neon/20 to-primary-container/5 border border-primary-neon/30 flex items-center justify-center shadow-[0_0_20px_rgba(0,255,157,0.15)] backdrop-blur-xl">
					<Shield className="w-8 h-8 text-primary-neon drop-shadow-[0_0_8px_#00FF9D]" />
				</div>
				<div>
					<h1 className="text-4xl font-black text-on-surface mb-2 tracking-tight">System Health</h1>
					<p className="text-on-surface-variant font-medium">Gateway infrastructure status and nodal connectivity check</p>
				</div>
			</div>
			
			<HealthStatus />
		</div>
	);
}
