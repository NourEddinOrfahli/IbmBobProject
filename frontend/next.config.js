/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep the browser on one origin in Replit and local demos. The backend
  // remains private on port 8000 while Next.js proxies browser requests.
  async rewrites() {
    return [
      {
        source: '/backend-api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'apod.nasa.gov',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'www.apod.nasa.gov',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'apod.nasa.gov',
        port: '',
        pathname: '/apod/**',
      },
    ],
  },
};

module.exports = nextConfig;
