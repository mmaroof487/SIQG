/** @type {import('tailwindcss').Config} */
export default {
	content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
	theme: {
		extend: {
			colors: {
				slate: {
					50: "#f8fafc",
					100: "#f1f5f9",
					200: "#e2e8f0",
					300: "#cbd5e1",
					400: "#94a3b8",
					500: "#64748b",
					600: "#475569",
					700: "#334155",
					800: "#1e293b",
					900: "#0f172a",
				},
				emerald: {
					50: "#f0fdf4",
					500: "#10b981",
					600: "#059669",
				},
				red: {
					50: "#fef2f2",
					500: "#ef4444",
					600: "#dc2626",
				},
			},
		},
	},
	plugins: [],
};
