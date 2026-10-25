import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id))
            return "react";
          if (id.includes("node_modules/recharts/")) return "charts";
          if (/node_modules\/(d3-[^/]+|victory-vendor|internmap)\//.test(id))
            return "chart-math";
        },
      },
    },
  },
});
