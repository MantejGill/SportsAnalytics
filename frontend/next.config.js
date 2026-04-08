/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  swcMinify: true,

  env: {
    NEXT_PUBLIC_APP_NAME: 'Auto-Negotiate',
    NEXT_PUBLIC_APP_VERSION: '1.0.0',
  },

  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: (process.env.BACKEND_URL || 'http://localhost:8100') + '/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
