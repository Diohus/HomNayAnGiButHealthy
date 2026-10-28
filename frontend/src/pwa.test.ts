import { describe, expect, it } from "vitest";
import indexHtml from "../index.html?raw";
import manifestSrc from "../public/manifest.webmanifest?raw";
import swSrc from "../public/sw.js?raw";

// Evaluate the real sw.js with a stub `self` and pull out its cache-decision function.
type ShouldCache = (url: string, origin: string) => boolean;
function loadShouldCache(): ShouldCache {
  const self = { addEventListener: () => undefined, location: { origin: "https://app.example" } };
  return new Function("self", "caches", `${swSrc}\nreturn shouldCache;`)(self, {}) as ShouldCache;
}

describe("service worker cache policy", () => {
  const shouldCache = loadShouldCache();
  const O = "https://app.example";

  it("never caches /api (health data)", () => {
    for (const u of ["/api/menu?start=2026-10-21", "/api/me/export", "/api", "/api/chat", `${O}/api/intake?day=x`]) {
      expect(shouldCache(u, O)).toBe(false);
    }
  });

  it("caches the app shell and built assets of the same origin only", () => {
    for (const u of ["/", "/index.html", "/assets/index-abc.js", "/theme-init.js", "/manifest.webmanifest", "/icons/icon-192.png"]) {
      expect(shouldCache(u, O)).toBe(true);
    }
    expect(shouldCache("https://cdn.example/x.js", O)).toBe(false);
    expect(shouldCache("/sw.js", O)).toBe(false);
    expect(shouldCache("/apical.png", O)).toBe(true); // only the /api path segment is excluded
  });

  it("uses a versioned cache and deletes old ones on activate", () => {
    expect(swSrc).toContain('const VERSION = "hnag-__SW_VERSION__"');
    expect(swSrc).toMatch(/caches\.delete/);
  });
});

describe("manifest and index.html", () => {
  it("manifest is valid and points to icons", () => {
    const m = JSON.parse(manifestSrc);
    expect(m.display).toBe("standalone");
    expect(m.start_url).toBe("/");
    expect(m.short_name).toBe("Hôm Nay Ăn Gì");
    const sizes = m.icons.map((i: { sizes: string; purpose: string }) => `${i.sizes}:${i.purpose}`);
    expect(sizes).toEqual(expect.arrayContaining(["192x192:any", "512x512:any", "512x512:maskable"]));
  });

  it("index.html links the manifest and apple-touch-icon", () => {
    expect(indexHtml).toContain('<link rel="manifest" href="/manifest.webmanifest"');
    expect(indexHtml).toContain('rel="apple-touch-icon"');
  });
});
