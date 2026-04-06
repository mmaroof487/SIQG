import React, { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function ResultsTable({ rows, columns, isLoading, error }) {
	const [currentPage, setCurrentPage] = useState(1);
	const itemsPerPage = 10;
	const totalPages = rows ? Math.ceil(rows.length / itemsPerPage) : 0;

	if (isLoading) {
		return (
			<div className="card flex items-center justify-center py-12">
				<div className="text-slate-500">Loading results...</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="card bg-red-50 border border-red-200">
				<div className="text-red-700">{error}</div>
			</div>
		);
	}

	if (!rows || rows.length === 0) {
		return <div className="card text-center py-12 text-slate-500">No results to display</div>;
	}

	const displayColumns = columns || Object.keys(rows[0] || {});
	const startIdx = (currentPage - 1) * itemsPerPage;
	const endIdx = startIdx + itemsPerPage;
	const paginatedRows = rows.slice(startIdx, endIdx);

	const renderValue = (value) => {
		if (value === null || value === undefined) {
			return <span className="text-slate-400 italic">null</span>;
		}
		if (typeof value === "boolean") {
			return <span className={value ? "text-emerald-600 font-medium" : "text-slate-600"}>{value ? "true" : "false"}</span>;
		}
		if (typeof value === "object") {
			return <span className="text-slate-500 text-sm font-mono">{JSON.stringify(value)}</span>;
		}
		// Check if value looks masked (contains ***)
		if (typeof value === "string" && value.includes("***")) {
			return <span className="masked-text">{value}</span>;
		}
		return <span>{String(value)}</span>;
	};

	return (
		<div className="card space-y-4">
			<div className="overflow-x-auto">
				<table className="w-full">
					<thead className="bg-slate-100 border-b border-slate-200">
						<tr>
							{displayColumns.map((col) => (
								<th key={col} className="table-cell font-semibold text-slate-900">
									{col}
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{paginatedRows.map((row, rowIdx) => (
							<tr key={rowIdx} className="border-b border-slate-100 hover:bg-slate-50">
								{displayColumns.map((col) => (
									<td key={`${rowIdx}-${col}`} className="table-cell text-slate-800">
										{renderValue(row[col])}
									</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
			</div>

			{totalPages > 1 && (
				<div className="flex items-center justify-between pt-4 border-t border-slate-200">
					<div className="text-sm text-slate-600">
						Showing {startIdx + 1} to {Math.min(endIdx, rows.length)} of {rows.length} rows
					</div>
					<div className="flex gap-2">
						<button
							onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
							disabled={currentPage === 1}
							className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1">
							<ChevronLeft className="w-4 h-4" />
							Previous
						</button>
						<span className="px-4 py-2 text-slate-600">
							Page {currentPage} of {totalPages}
						</span>
						<button
							onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
							disabled={currentPage === totalPages}
							className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1">
							Next
							<ChevronRight className="w-4 h-4" />
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
