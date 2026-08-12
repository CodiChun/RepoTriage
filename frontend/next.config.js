/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    const backendUrl =
      process.env.BACKEND_INTERNAL_URL || "http://backend:8000";
    return [
      { source: "/issues/:path*", destination: `${backendUrl}/issues/:path*` },
      { source: "/triage", destination: `${backendUrl}/triage` },
      { source: "/webhook/:path*", destination: `${backendUrl}/webhook/:path*` },
    ];
  },
};

module.exports = nextConfig;
