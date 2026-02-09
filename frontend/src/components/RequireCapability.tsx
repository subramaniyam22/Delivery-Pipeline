'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useCurrentUser } from '@/lib/useCurrentUser';
import type { Capability } from '@/lib/rbac';
import { getLandingRouteForRole } from '@/lib/nav';

type RequireCapabilityProps = {
  cap: Capability;
  children: React.ReactNode;
};

export default function RequireCapability({ cap, children }: RequireCapabilityProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { capabilities, isLoading, error, role } = useCurrentUser();
  const hasAccess = capabilities.includes(cap);
  const currentPath = `${pathname}${typeof window !== 'undefined' ? window.location.search : ''}`;

  useEffect(() => {
    if (isLoading) return;
    if (error) {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('post_login_redirect', currentPath);
      }
      router.push('/login');
      return;
    }
    if (!hasAccess) {
      const landing = getLandingRouteForRole(role);
      if (landing !== currentPath) {
        router.push(landing);
      }
    }
  }, [isLoading, error, hasAccess, role, router, currentPath]);

  if (isLoading) {
    return (
      <div style={{ padding: '2rem' }}>
        <div style={{ height: 14, width: 220, background: '#e2e8f0', borderRadius: 6, marginBottom: 12 }} />
        <div style={{ height: 10, width: 320, background: '#e2e8f0', borderRadius: 6, marginBottom: 8 }} />
        <div style={{ height: 10, width: 260, background: '#e2e8f0', borderRadius: 6 }} />
      </div>
    );
  }

  if (error || !hasAccess) {
    return (
      <div style={{ padding: '3rem', maxWidth: 640, margin: '0 auto', textAlign: 'center' }}>
        <h1 style={{ fontSize: 24, marginBottom: 8 }}>Access Restricted</h1>
        <p style={{ color: '#64748b', marginBottom: 20 }}>
          You don’t have permission to view this page.
        </p>
        <button
          onClick={() => router.push('/dashboard')}
          style={{
            padding: '10px 18px',
            borderRadius: 8,
            border: '1px solid #2563eb',
            background: '#2563eb',
            color: 'white',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          Go to Dashboard
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
