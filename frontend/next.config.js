const { withSentryConfig } = require('@sentry/nextjs');

/** @type {import('next').NextConfig} */
const nextConfig = {
    // Security headers (CSP removed temporarily for Render compatibility)
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
                    // CSP removed - was blocking API calls on Render
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

const sentryOptions = {
    org: process.env.SENTRY_ORG || '',
    project: process.env.SENTRY_PROJECT || '',
    silent: !process.env.CI,
};
module.exports = withSentryConfig(nextConfig, sentryOptions);
