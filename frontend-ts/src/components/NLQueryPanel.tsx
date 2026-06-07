import React, { useState } from "react";
import { api } from "../utils/api";
import { Loader, Send, Sparkles } from "lucide-react";

interface NLQueryPanelProps {
	onSQLGenerated: (data: any) => void;
	onLoading: (isLoading: boolean) => void;
	connectionId?: string;
	initialPrompt?: string;
}

export default function NLQueryPanel({ onSQLGenerated, onLoading, connectionId, initialPrompt }: NLQueryPanelProps) {
	const [question, setQuestion] = useState(initialPrompt || "");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState("");
	const [hasAutoSubmitted, setHasAutoSubmitted] = useState(false);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!question.trim()) return;

		setIsLoading(true);
		setError("");
		onLoading(true);

		try {
			const response = await api.nlToSql(question, "", connectionId === "default" ? undefined : connectionId);

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

	React.useEffect(() => {
		if (initialPrompt && !hasAutoSubmitted) {
			setHasAutoSubmitted(true);
			const fakeEvent = { preventDefault: () => {} } as React.FormEvent;
			handleSubmit(fakeEvent);
		}
	}, [initialPrompt, hasAutoSubmitted]);

	const quickExamples = [
		"Which users joined this week?",
		"Show revenue by month",
		"Find inactive users",
		"Explain this SQL query"
	];

	return (
		<form onSubmit={handleSubmit} className="w-full relative">
			<div className="relative flex items-center w-full group">
				<Sparkles className="absolute left-5 w-6 h-6 text-primary-neon/70" />
				<input
					type="text"
					value={question}
					onChange={(e) => setQuestion(e.target.value)}
					placeholder="Ask your database anything (e.g. Show me users who signed up this week)"
					className="w-full bg-surface-high/40 text-on-surface pl-14 pr-16 py-4 text-lg border border-surface-high rounded-2xl focus:outline-none focus:border-primary-neon/50 focus:bg-surface-high/70 transition-all placeholder-on-surface-variant/50 shadow-inner"
					disabled={isLoading}
				/>
				<button 
					type="submit" 
					disabled={isLoading || !question.trim()} 
					className="absolute right-2.5 disabled:opacity-50 disabled:cursor-not-allowed bg-primary-neon hover:bg-primary-neon/90 text-surface p-2 rounded-xl transition-all"
				>
					{isLoading ? <Loader className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
				</button>
			</div>

			{error && <div className="mt-4 p-4 bg-error-dim/10 border border-error/30 rounded-xl text-error text-sm font-medium">{error}</div>}

		</form>
	);
}
