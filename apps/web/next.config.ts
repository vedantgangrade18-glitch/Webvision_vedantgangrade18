import path from "node:path";
import type { NextConfig } from "next";

const API = process.env.API_INTERNAL_URL || "http://localhost:8000";
const MEDIA_ORIGINS = (process.env.MEDIA_ORIGINS || "http://localhost:8000 http://localhost:9000").trim();

// CSP: Razorpay Checkout and Google Identity Services are the only third-party scripts.
const csp = [
  "default-src 'self'",
  // React's dev tooling needs eval(); production builds never do.
  `script-src 'self' 'unsafe-inline'${process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""} https://checkout.razorpay.com https://accounts.google.com`,
  "style-src 'self' 'unsafe-inline' https://accounts.google.com",
  `img-src 'self' data: blob: https: ${MEDIA_ORIGINS}`,
  `media-src 'self' blob: https: ${MEDIA_ORIGINS}`,
  "font-src 'self' data:",
  `connect-src 'self' https://lumberjack.razorpay.com https://accounts.google.com ${MEDIA_ORIGINS}`,
  "frame-src https://api.razorpay.com https://checkout.razorpay.com https://accounts.google.com https://*.tinyfish.ai",
  "worker-src 'self' blob:",
  "base-uri 'self'",
  "form-action 'self' https://api.razorpay.com " + API,
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  // next-intl request config. Wired directly instead of via `next-intl/plugin`, whose
  // message-extraction tooling loads a native SWC addon we don't need.
  turbopack: { resolveAlias: { "next-intl/config": "./i18n/request.ts" } },
  webpack(config) {
    config.resolve.alias["next-intl/config"] = path.resolve(process.cwd(), "i18n/request.ts");
    return config;
  },
  async rewrites() {
    // One origin for the browser: API cookies are first-party and SameSite=Lax works.
    return [
      { source: "/api/v1/:path*", destination: `${API}/api/v1/:path*` },
      { source: "/media/:path*", destination: `${API}/media/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(self), microphone=(self), geolocation=(self)" },
        ],
      },
      { source: "/sw.js", headers: [{ key: "Cache-Control", value: "no-cache" }, { key: "Service-Worker-Allowed", value: "/" }] },
    ];
  },
};

export default nextConfig;
