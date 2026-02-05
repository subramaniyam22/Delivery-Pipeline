'use client';

import { ReactNode } from 'react';
import { Role } from '@/lib/auth';

interface RoleGuardProps {
    children: ReactNode;
    userRole: Role;
    requiredRoles?: Role[];
    fallback?: ReactNode;
}

export default function RoleGuard({
    children,
    userRole,
    requiredRoles,
    fallback = null,
}: RoleGuardProps) {
    // If no required roles specified, allow access
    if (!requiredRoles || requiredRoles.length === 0) {
        return <>{children}</>;
    }

    // Check if user has required role
    if (!requiredRoles.includes(userRole)) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}
