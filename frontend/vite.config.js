import { defineConfig } from "vite";
import { resolve } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: resolve(__dirname, "src"),
  build: {
    outDir: resolve(__dirname, "../static/dist"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "src/main.js"),
      },
      output: {
        // Deterministic filenames so Flask templates can reference them statically
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
  },
  css: {
    // Inline source maps in dev mode only
    devSourcemap: true,
  },
});
