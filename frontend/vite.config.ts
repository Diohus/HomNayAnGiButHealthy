import react from "@vitejs/plugin-react";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";

// P4: give dist/sw.js a per-build cache version (hash of the built index.html, which names the hashed assets),
// so a new deploy installs a new cache and the old one is deleted on activate.
function swVersion(): Plugin {
  return {
    name: "sw-version",
    apply: "build",
    closeBundle() {
      const dist = resolve(__dirname, "dist");
      const version = createHash("sha256").update(readFileSync(resolve(dist, "index.html"))).digest("hex").slice(0, 12);
      const sw = resolve(dist, "sw.js");
      writeFileSync(sw, readFileSync(sw, "utf8").replace("__SW_VERSION__", version));
    },
  };
}

export default defineConfig({
  plugins: [react(), swVersion()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
