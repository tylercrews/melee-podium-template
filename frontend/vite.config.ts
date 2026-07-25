import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/melee-podium-template/",
  plugins: [react()],
  server: {
    proxy: {
      "/melee-podium-template/char_assets": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
        rewrite: (path) =>
          path.replace(/^\/melee-podium-template\/char_assets/, "/char_assets"),
      },
      "/melee-podium-template/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
        rewrite: (path) =>
          path.replace(/^\/melee-podium-template\/api/, "/api"),
      },
    },
  },
});
