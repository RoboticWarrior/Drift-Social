import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies API and media requests to the Flask process so the
// browser only ever talks to one origin (no CORS, cookies work normally).
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:5000" },
      "/media": { target: "http://127.0.0.1:5000" },
    },
  },
  build: {
    outDir: "dist",
  },
});
