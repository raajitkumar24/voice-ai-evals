import {defineConfig} from "vitest/config";
import path from "node:path";

export default defineConfig({
  esbuild: {jsx: "automatic"},
  resolve: {alias: {"@": path.resolve(__dirname, ".")}},
  test: {
    environment: "jsdom",
    include: [path.resolve(__dirname, "**/*.test.{ts,tsx}")],
    setupFiles: [path.resolve(__dirname, "vitest.setup.ts")],
  },
});
