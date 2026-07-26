import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    manifest: true,

    outDir: "static",

    emptyOutDir: true,

    sourcemap: true,

    rollupOptions: {
      input: {
        page: resolve(__dirname, "assets/js/page.js"),
        main: resolve(__dirname, "assets/scss/main.scss"),
      },
    },
  },
});