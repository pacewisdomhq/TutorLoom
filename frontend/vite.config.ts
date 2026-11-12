// SPDX-FileCopyrightText: 2026 Pace Wisdom Solutions Pvt. Ltd.
// SPDX-License-Identifier: Apache-2.0

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
    },
  },
  server: {
    // strictPort:false lets Vite fall back to the next free port if 5173 is taken.
    port: 5173,
    strictPort: false,
    // Allow *.localhost subdomains for local tenant testing (e.g. org1.localhost:5173)
    allowedHosts: true,
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          // Split heavy vendor libs into separate chunks so browsers can
          // cache them independently.
          groups: [
            { name: "vendor-react", test: /node_modules[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/ },
            { name: "vendor-icons", test: /node_modules[\\/]lucide-react[\\/]/ },
            { name: "vendor-pdf", test: /node_modules[\\/](jspdf|html2canvas)[\\/]/ },
          ],
        },
      },
    },
  },
});
