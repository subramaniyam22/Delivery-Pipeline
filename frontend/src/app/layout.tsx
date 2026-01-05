import type { Metadata, Viewport } from 'next';
import './globals.css';

// SEO-optimized metadata
export const metadata: Metadata = {
    title: {
        default: 'Delivery Pipeline - Project Management Platform',
        template: '%s | Delivery Pipeline',
    },
    description: 'Enterprise-grade delivery pipeline management platform. Track projects, manage teams, and optimize workflows with AI-powered insights across global regions.',
    keywords: ['project management', 'delivery pipeline', 'team management', 'workflow automation', 'enterprise software'],
    authors: [{ name: 'Delivery Pipeline Team' }],
    creator: 'Delivery Pipeline',
    publisher: 'Delivery Pipeline',
    robots: {
        index: true,
        follow: true,
        googleBot: {
            index: true,
            follow: true,
            'max-video-preview': -1,
            'max-image-preview': 'large',
            'max-snippet': -1,
        },
    },
    openGraph: {
        type: 'website',
        locale: 'en_US',
        url: 'https://delivery-pipeline.com',
        siteName: 'Delivery Pipeline',
        title: 'Delivery Pipeline - Project Management Platform',
        description: 'Enterprise-grade delivery pipeline management platform with AI-powered insights.',
    },
    twitter: {
        card: 'summary_large_image',
        title: 'Delivery Pipeline - Project Management Platform',
        description: 'Enterprise-grade delivery pipeline management platform with AI-powered insights.',
    },
    // InfoSec: Prevent embedding in iframes (clickjacking protection)
    other: {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    },
};

// Viewport configuration
export const viewport: Viewport = {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 5,
    themeColor: '#2563eb',
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" dir="ltr">
            <head>
                {/* Security headers are set in next.config.js */}
                <meta httpEquiv="X-XSS-Protection" content="1; mode=block" />
                <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
                <meta name="referrer" content="strict-origin-when-cross-origin" />
            </head>
            <body>
                {/* WCAG: Skip navigation link for keyboard users */}
                <a href="#main-content" className="skip-link">
                    Skip to main content
                </a>
                {/* Semantic HTML wrapper */}
                <div id="main-content" role="main">
                    {children}
                </div>
            </body>
        </html>
    );
}
