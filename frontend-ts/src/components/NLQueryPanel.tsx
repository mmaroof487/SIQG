import React, { useState } from "react";
import { api } from "../utils/api";
import { Loader, Send, Sparkles } from "lucide-react";

interface NLQueryPanelProps {
	onSQLGenerated: (data: any) => void;
	onLoading: (isLoading: boolean) => void;
}

export default function NLQueryPanel({ onSQLGenerated, onLoading }: NLQueryPanelProps) {
	const [question, setQuestion] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState("");

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!question.trim()) return;

		setIsLoading(true);
		setError("");
		onLoading(true);

		try {
			const response = await api.nlToSql(question);

			if (response.data.status === "success") {
				onSQLGenerated({
					sql: response.data.generated_sql,
					explanation: response.data.explanation,
					question: question,
				});
			} else {
				setError(response.data.message || "Failed to generate SQL");
			}
		} catch (err: any) {
			setError(err.response?.data?.detail || "Error generating SQL");
		} finally {
			setIsLoading(false);
			onLoading(false);
		}
	};

	return (
		<form onSubmit={handleSubmit} className="w-full space-y-6 bg-surface/60 backdrop-blur-xl border border-surface-high p-6 flex flex-col rounded-2xl shadow-[0_0_30px_rgba(0,0,0,0.5)]">
			<div className="space-y-4 relative">
				<label className="flex items-center gap-2 text-sm font-bold text-on-surface tracking-wide uppercase">
					<Sparkles className="text-primary-neon w-4 h-4" />
					Argus Intelligence Matrix
				</label>
				<div className="flex gap-4 relative">
					<div className="relative flex-1 group">
						<div className="absolute -inset-0.5 bg-gradient-to-r from-primary-neon to-primary-container rounded-xl blur opacity-25 group-focus-within:opacity-50 transition duration-500"></div>
						<input
							type="text"
							value={question}
							onChange={(e) => setQuestion(e.target.value)}
							placeholder="e.g., Show me the top 5 users by creation date"
							className="relative w-full bg-surface-high/80 text-on-surface px-5 py-4 border border-surface-high rounded-xl focus:outline-none focus:ring-1 focus:ring-primary-neon placeholder-on-surface-variant/50 shadow-inner"
							disabled={isLoading}
						/>
					</div>
					<button 
						type="submit" 
						disabled={isLoading || !question.trim()} 
						className="relative disabled:opacity-50 disabled:cursor-not-allowed group overflow-hidden bg-primary-neon/10 hover:bg-primary-neon/20 px-8 rounded-xl font-bold text-primary-neon transition-all border border-primary-neon/50 uppercase tracking-widest shadow-[0_0_15px_rgba(0,255,157,0.15)] flex items-center gap-3"
					>
						{isLoading ? <Loader className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />}
						Generate
					</button>
				</div>
			</div>

			{error && <div className="p-4 bg-error-dim/10 border border-error/30 rounded-xl text-error text-sm font-medium">{error}</div>}

			<div className="flex items-center gap-3 text-xs text-on-surface-variant font-medium bg-surface/50 p-3 rounded-lg border border-surface-high/50">
				<span className="px-2 py-1 bg-surface-high rounded text-primary-neon font-bold">Try:</span>
				<span>Show me users created yesterday</span>
				<span className="w-1 h-1 bg-surface-high rounded-full"></span>
				<span>Count active users by role</span>
				<span className="w-1 h-1 bg-surface-high rounded-full"></span>
				<span>Find slowest queries</span>
			</div>
		</form>
	);
}
