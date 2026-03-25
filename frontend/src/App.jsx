import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000/api/v1";

export default function App() {
	const [status, setStatus] = useState(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		checkStatus();
		const interval = setInterval(checkStatus, 5000);
		return () => clearInterval(interval);
	}, []);

	async function checkStatus() {
		try {
			const response = await axios.get(`${API_BASE}/status`);
			setStatus(response.data);

			// Update status dots
			document.getElementById("gateway-status").className = "status-dot";
			document.getElementById("redis-status").className = `status-dot ${response.data.redis === "healthy" ? "" : "error"}`;
		} catch (error) {
			console.error("Status check failed:", error);
			document.getElementById("gateway-status").className = "status-dot error";
		}
		setLoading(false);
	}

	if (loading) {
		return <div className="loading">Checking gateway status...</div>;
	}

	return (
		<div style={{ padding: "20px" }}>
			<h2>📊 Gateway Status</h2>
			{status ? (
				<div>
					<p>
						<strong>Status:</strong> {status.status}
					</p>
					<p>
						<strong>Redis:</strong> {status.redis}
					</p>
				</div>
			) : (
				<p style={{ color: "#f44336" }}>Failed to connect to gateway</p>
			)}

			<h2 style={{ marginTop: "30px" }}>🚀 Features Coming Soon</h2>
			<ul>
				<li>SQL Query Editor with Monaco</li>
				<li>Query History</li>
				<li>Live Metrics Dashboard</li>
				<li>Schema Browser</li>
				<li>Query Analysis & Recommendations</li>
			</ul>
		</div>
	);
}
