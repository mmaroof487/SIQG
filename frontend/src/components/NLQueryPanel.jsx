import React, { useState } from "react";
import { api } from "../utils/api";
import { Loader, Send } from "lucide-react";

export default function NLQueryPanel({ onSQLGenerated, onLoading }) {
	const [question, setQuestion] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState("");

	const handleSubmit = async (e) => {
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
		} catch (err) {
			setError(err.response?.data?.detail || "Error generating SQL");
		} finally {
			setIsLoading(false);
			onLoading(false);
		}
	};

	return (
		<form onSubmit={handleSubmit} className="w-full space-y-4">
			<div className="space-y-2">
				<label className="block text-sm font-medium text-slate-700">Ask in plain English</label>
				<div className="flex gap-2">
					<input
						type="text"
						value={question}
						onChange={(e) => setQuestion(e.target.value)}
						placeholder="e.g., Show me the top 5 users by creation date"
						className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
						disabled={isLoading}
					/>
					<button type="submit" disabled={isLoading || !question.trim()} className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
						{isLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
						Generate
					</button>
				</div>
			</div>

			{error && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}

			<div className="text-sm text-slate-500">💡 Examples: Show me users created yesterday, Count active users by role, Find slowest queries</div>
		</form>
	);
}
