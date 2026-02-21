import type { Metadata, Viewport } from 'next';
import './globals.css';
import { NotificationProvider } from '@/context/NotificationContext';
import QueryProvider from '@/components/QueryProvider';

// SEO-optimized metadata
export const metadata: Metadata = {
    title: {
        default: 'Delivery Automation Intelligence System Yield - Project Management Platform',
        template: '%s | Delivery Automation Intelligence System Yield',
    },
    description: 'Delivery Automation Intelligence System Yield (DAISY): enterprise-grade project delivery orchestration with AI-powered insights across global regions.',
    keywords: ['project management', 'delivery automation', 'team management', 'workflow automation', 'enterprise software'],
    authors: [{ name: 'Delivery Automation Intelligence System Yield Team' }],
    creator: 'Delivery Automation Intelligence System Yield',
    publisher: 'Delivery Automation Intelligence System Yield',
    icons: {
        icon: '/favicon.png',
        shortcut: '/favicon.png',
        apple: '/favicon.png',
    },
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
        siteName: 'Delivery Automation Intelligence System Yield',
        title: 'Delivery Automation Intelligence System Yield - Project Management Platform',
        description: 'Delivery Automation Intelligence System Yield (DAISY) with AI-powered insights.',
    },
    twitter: {
        card: 'summary_large_image',
        title: 'Delivery Automation Intelligence System Yield - Project Management Platform',
        description: 'Delivery Automation Intelligence System Yield (DAISY) with AI-powered insights.',
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
        <html lang="en" dir="ltr" data-scroll-behavior="smooth">
            <head>
                {/* Security headers are set in next.config.js */}
                <meta httpEquiv="X-XSS-Protection" content="1; mode=block" />
                <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
                <meta name="referrer" content="strict-origin-when-cross-origin" />
            </head>
            <body suppressHydrationWarning>
                {/* WCAG: Skip navigation link for keyboard users */}
                <a href="#main-content" className="skip-link">
                    Skip to main content
                </a>
                {/* Semantic HTML wrapper */}
                <div id="main-content" role="main">
                    <QueryProvider>
                        <NotificationProvider>
                            {children}
                        </NotificationProvider>
                    </QueryProvider>
                </div>
            </body>
        </html>
    );
}
