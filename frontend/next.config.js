/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.NEXT_DIST_DIR || ".next",
  reactStrictMode: false, // Prevents double-mounting effects during SSE connections in dev
};

module.exports = nextConfig;
