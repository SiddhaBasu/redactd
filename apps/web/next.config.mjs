/** @type {import('next').NextConfig} */
const ortWasm = new URL("./node_modules/gliner/node_modules/onnxruntime-web/dist/ort.min.mjs", import.meta.url).pathname;

const nextConfig = {
  // Cross-origin isolation enables multi-threaded WASM (SharedArrayBuffer) for the in-browser models.
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
        { key: "Cross-Origin-Embedder-Policy", value: "require-corp" },
        { key: "Referrer-Policy", value: "no-referrer" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
        { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
      ],
    }];
  },
  webpack(config, { isServer }) {
    // gliner.js imports onnxruntime-web/webgpu and /webgl subpaths that its pinned ORT version doesn't export.
    config.resolve.alias = { ...config.resolve.alias, sharp$: false, "onnxruntime-node$": false,
      "onnxruntime-web/webgpu$": ortWasm, "onnxruntime-web/webgl$": ortWasm };
    if (!isServer) config.resolve.fallback = { ...config.resolve.fallback, fs: false, path: false, url: false, crypto: false };
    return config;
  },
};
export default nextConfig;
