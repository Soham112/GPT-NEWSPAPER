/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow external images if needed
  images: {
    domains: ['www.google.com'],
  },
}

module.exports = nextConfig

