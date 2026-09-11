import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// CesiumJS runtime files (Workers/Assets/Widgets/ThirdParty) are copied to
// public/cesium by scripts/copy-cesium.mjs (runs on predev/prebuild).
export default defineConfig({
  plugins: [react()],
  define: {
    CESIUM_BASE_URL: JSON.stringify("/cesium/"),
  },
  resolve: {
    alias: {
      cesium: path.resolve(__dirname, "node_modules/cesium"),
    },
  },
  test: {
    environment: "jsdom",
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/media": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
