'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '@/components/Navigation';

/**
 * Policies have been consolidated into System Configuration → Decision Policies.
 * This page redirects to avoid duplicate policy UIs.
 */
export default function AdminPoliciesPage() {
    const router = useRouter();

    useEffect(() => {
        router.replace('/configuration?tab=decision_policies');
    }, [router]);

    return (
        <>
            <Navigation />
            <main className="p-6 max-w-2xl">
                <p className="text-sm text-gray-600">
                    Policies are now managed in <strong>System Configuration → Decision Policies</strong>. Redirecting…
                </p>
                <p className="mt-2 text-sm">
                    <a href="/configuration?tab=decision_policies" className="text-indigo-600 hover:underline">
                        Go to Decision Policies
                    </a>
                </p>
            </main>
        </>
    );
}
