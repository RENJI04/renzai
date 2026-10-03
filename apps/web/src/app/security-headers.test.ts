import { describe, expect, it } from "vitest";
import nextConfig from "../../next.config";

describe("browser security headers", () => {
  it("prevents framing and constrains active content without disabling static caching", async () => {
    expect(nextConfig.poweredByHeader).toBe(false);
    const entries = await nextConfig.headers?.();
    const headers = Object.fromEntries(
      (entries?.[0]?.headers ?? []).map(({ key, value }) => [key, value]),
    );

    expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
    expect(headers["Content-Security-Policy"]).toContain("object-src 'none'");
    expect(headers["X-Frame-Options"]).toBe("DENY");
    expect(headers["X-Content-Type-Options"]).toBe("nosniff");
    expect(headers["Cache-Control"]).toBeUndefined();
  });
});
