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
    // Admin and Manager have access to everything
    if (userRole === Role.ADMIN || userRole === Role.MANAGER) {
        return <>{children}</>;
    }

    // Check if user has required role
    if (requiredRoles && !requiredRoles.includes(userRole)) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}
