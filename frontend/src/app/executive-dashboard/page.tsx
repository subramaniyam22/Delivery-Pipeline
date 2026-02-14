'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Executive dashboard content has been moved to the main Dashboard page.
 * Redirect so existing links and bookmarks continue to work.
 */
export default function ExecutiveDashboardRedirect() {
    const router = useRouter();
    useEffect(() => {
        router.replace('/dashboard#portfolio-health');
    }, [router]);
    return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh' }}>
            <p style={{ color: '#64748b' }}>Redirecting to Dashboard…</p>
        </div>
    );
}
