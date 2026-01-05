/** @type {import('next').NextConfig} */
const nextConfig = {
    // Output standalone for cloud deployment (Render, Vercel, etc.)
    output: 'standalone',
    
    // InfoSec: Security headers
    async headers() {
        return [
            {
                source: '/:path*',
                headers: [
                    // Prevent clickjacking
                    {
                        key: 'X-Frame-Options',
                        value: 'DENY',
                    },
                    // Prevent MIME sniffing
                    {
                        key: 'X-Content-Type-Options',
                        value: 'nosniff',
                    },
                    // XSS protection
                    {
                        key: 'X-XSS-Protection',
                        value: '1; mode=block',
                    },
                    // Referrer policy
                    {
                        key: 'Referrer-Policy',
                        value: 'strict-origin-when-cross-origin',
                    },
                    // Permissions policy (restrict dangerous features)
                    {
                        key: 'Permissions-Policy',
                        value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()',
                    },
                    // Strict Transport Security (for production)
                    {
                        key: 'Strict-Transport-Security',
                        value: 'max-age=31536000; includeSubDomains',
                    },
                    // Content Security Policy - allow Render URLs
                    {
                        key: 'Content-Security-Policy',
                        value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://*.onrender.com http://localhost:* http://backend:*; frame-ancestors 'none';",
                    },
                ],
            },
        ];
    },
    // SEO: Enable compression
    compress: true,
    // SEO: Optimize images
    images: {
        formats: ['image/avif', 'image/webp'],
        minimumCacheTTL: 60,
        remotePatterns: [
            {
                protocol: 'https',
                hostname: 'flagcdn.com',
                pathname: '/**',
            },
        ],
    },
    // InfoSec: Disable powered by header
    poweredByHeader: false,
    // Performance: Enable React strict mode
    reactStrictMode: true,
};

module.exports = nextConfig;
