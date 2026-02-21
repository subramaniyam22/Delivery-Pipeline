'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated } from '@/lib/auth';

export default function HomePage() {
    const router = useRouter();

    useEffect(() => {
        // Redirect to login if not authenticated, otherwise to dashboard
        if (isAuthenticated()) {
            router.push('/dashboard');
        } else {
            router.push('/login');
        }
    }, [router]);

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100vh',
            background: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
            color: 'white',
            fontFamily: 'sans-serif'
        }}>
            <div style={{ textAlign: 'center' }}>
                <div style={{ marginBottom: '16px' }}>
                    <img src="/logo.png" alt="DAISY logo" style={{ width: '56px', height: '56px' }} />
                </div>
                <h1 style={{ margin: '0 0 8px 0' }}>Delivery Automation Intelligence System Yield</h1>
                <p style={{ opacity: 0.7 }}>Redirecting...</p>
            </div>
        </div>
    );
}
