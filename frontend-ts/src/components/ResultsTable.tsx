import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface ResultsTableProps {
	rows: any[];
	columns: string[];
	isLoading: boolean;
	error: string;
}

export default function ResultsTable({ rows, columns, isLoading, error }: ResultsTableProps) {
	const [currentPage, setCurrentPage] = useState(1);
	const itemsPerPage = 10;
	const totalPages = rows ? Math.ceil(rows.length / itemsPerPage) : 0;

	if (isLoading) {
		return (
			<div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl flex items-center justify-center py-16">
				<div className="text-primary-neon animate-pulse font-mono tracking-widest flex items-center gap-3">
					<div className="w-4 h-4 bg-primary-neon rounded-full animate-bounce"></div>
					EXECUTING QUERY...
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="bg-error-dim/10 border border-error/30 p-6 rounded-2xl text-error font-mono">
				{error}
			</div>
		);
	}

	if (!rows || rows.length === 0) {
		return <div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl text-center py-16 text-on-surface-variant font-mono uppercase tracking-widest">No Results Received</div>;
	}

	const displayColumns = columns || Object.keys(rows[0] || {});
	const startIdx = (currentPage - 1) * itemsPerPage;
	const endIdx = startIdx + itemsPerPage;
	const paginatedRows = rows.slice(startIdx, endIdx);

	const renderValue = (value: any) => {
		if (value === null || value === undefined) {
			return <span className="text-on-surface-variant/50 italic font-mono text-sm">null</span>;
		}
		if (typeof value === "boolean") {
			return <span className={value ? "text-primary-neon font-bold font-mono text-sm" : "text-on-surface-variant font-mono text-sm"}>{value ? "true" : "false"}</span>;
		}
		if (typeof value === "object") {
			return <span className="text-primary font-mono text-sm">{JSON.stringify(value)}</span>;
		}
		if (typeof value === "string" && value.includes("***")) {
			// Masked data
			return <span className="font-mono text-sm bg-surface-high px-2 py-1 rounded text-on-surface-variant tracking-wider">{value}</span>;
		}
		return <span className="text-on-surface">{String(value)}</span>;
	};

	return (
		<div className="bg-surface/60 backdrop-blur-xl border border-surface-high rounded-2xl overflow-hidden shadow-lg">
			<div className="overflow-x-auto">
				<table className="w-full text-left border-collapse">
					<thead>
						<tr className="bg-surface-high/50 border-b border-surface-high">
							{displayColumns.map((col) => (
								<th key={col} className="p-4 text-xs font-bold text-on-surface uppercase tracking-wider whitespace-nowrap">
									{col}
								</th>
							))}
						</tr>
					</thead>
					<tbody className="divide-y divide-surface-high/50">
						{paginatedRows.map((row, rowIdx) => (
							<tr key={rowIdx} className="hover:bg-surface-high/30 transition-colors">
								{displayColumns.map((col) => (
									<td key={`${rowIdx}-${col}`} className="p-4 whitespace-nowrap">
										{renderValue(row[col])}
									</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
			</div>

			{totalPages > 1 && (
				<div className="flex items-center justify-between p-4 bg-surface-high/30 border-t border-surface-high">
					<div className="text-sm font-medium text-on-surface-variant">
						Showing <span className="text-on-surface">{startIdx + 1}</span> to <span className="text-on-surface">{Math.min(endIdx, rows.length)}</span> of <span className="text-on-surface">{rows.length}</span> rows
					</div>
					<div className="flex gap-2">
						<button
							onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
							disabled={currentPage === 1}
							className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high text-on-surface border border-surface-high disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-colors text-sm font-bold uppercase tracking-wide">
							<ChevronLeft className="w-4 h-4" />
							Prev
						</button>
						<div className="hidden sm:flex items-center px-4 font-mono text-sm text-on-surface-variant">
							{currentPage} / {totalPages}
						</div>
						<button
							onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
							disabled={currentPage === totalPages}
							className="px-4 py-2 rounded-lg bg-surface hover:bg-surface-high text-on-surface border border-surface-high disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-colors text-sm font-bold uppercase tracking-wide">
							Next
							<ChevronRight className="w-4 h-4" />
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
