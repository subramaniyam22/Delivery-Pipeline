export type Role = 'ADMIN' | 'MANAGER' | 'SALES' | 'CONSULTANT' | 'PC' | 'BUILDER' | 'TESTER';

export const capabilities = [
  'view_dashboard',
  'view_projects',
  'create_projects',
  'edit_projects',
  'view_clients',
  'edit_clients',
  'view_operations',
  'view_quality',
  'view_sentiments',
  'view_capacity',
  'view_forecast',
  'manage_users',
  'configure_system',
  'approve_hitl',
  'assign_tasks',
  'perform_build',
  'perform_test',
  'view_reports',
  'view_audit_logs',
] as const;

export type Capability = (typeof capabilities)[number];

export const roleToCapabilities: Record<Role, Capability[]> = {
  ADMIN: [...capabilities],
  MANAGER: [
    ...capabilities,
  ],
  SALES: [
    'create_projects',
    'view_clients',
    'edit_clients',
    'view_projects',
    'view_sentiments',
    'view_reports',
  ],
  CONSULTANT: [
    'create_projects',
    'view_projects',
    'view_clients',
    'view_sentiments',
  ],
  PC: [
    'view_projects',
    'assign_tasks',
    'view_capacity',
    'view_operations',
    'view_quality',
    'approve_hitl',
  ],
  BUILDER: [
    'perform_build',
    'view_projects',
    'view_quality',
  ],
  TESTER: [
    'perform_test',
    'view_projects',
    'view_quality',
  ],
};

type UserLike = { role?: Role | string | null } | null | undefined;

export const getCapabilities = (role?: Role | string | null): Capability[] => {
  if (!role) return [];
  const normalized = role as Role;
  return roleToCapabilities[normalized] || [];
};

export const hasCapability = (user: UserLike, capability: Capability): boolean => {
  const role = user?.role ?? undefined;
  return getCapabilities(role).includes(capability);
};

export const hasAnyCapability = (user: UserLike, caps: Capability[]): boolean => {
  const role = user?.role ?? undefined;
  const userCaps = getCapabilities(role);
  return caps.some((cap) => userCaps.includes(cap));
};

export enum Stage {
    SALES = 'SALES',
    ONBOARDING = 'ONBOARDING',
    ASSIGNMENT = 'ASSIGNMENT',
    BUILD = 'BUILD',
    TEST = 'TEST',
    DEFECT_VALIDATION = 'DEFECT_VALIDATION',
    COMPLETE = 'COMPLETE',
}


export const hasRole = (userRole: Role, requiredRole: Role): boolean => {
    // Admin and Manager have access to everything
    if (userRole === 'ADMIN' || userRole === 'MANAGER') {
        return true;
    }
    return userRole === requiredRole;
};

export const hasAnyRole = (userRole: Role, requiredRoles: Role[]): boolean => {
    // Admin and Manager have access to everything
    if (userRole === 'ADMIN' || userRole === 'MANAGER') {
        return true;
    }
    return requiredRoles.includes(userRole);
};

export const canAccessStage = (userRole: Role, stage: Stage): boolean => {
    // Admin and Manager can access all stages
    if (userRole === 'ADMIN' || userRole === 'MANAGER') {
        return true;
    }

    // Role-specific stage access
    switch (userRole) {
        case 'CONSULTANT':
            return stage === Stage.ONBOARDING;
        case 'PC':
            return stage === Stage.ASSIGNMENT;
        case 'BUILDER':
            return stage === Stage.BUILD;
        case 'TESTER':
            return stage === Stage.TEST;
        default:
            return false;
    }
};

export const canCreateProject = (userRole: Role): boolean => {
    return userRole === 'SALES';
};

export const canManageUsers = (userRole: Role): boolean => {
    return userRole === 'ADMIN' || userRole === 'MANAGER';
};

export const canManageConfig = (userRole: Role): boolean => {
    return userRole === 'ADMIN' || userRole === 'MANAGER';
};

export const canApproveWorkflow = (userRole: Role): boolean => {
    return userRole === 'ADMIN' || userRole === 'MANAGER';
};

export const canCreateTasks = (userRole: Role): boolean => {
    return hasAnyRole(userRole, ['PC', 'ADMIN', 'MANAGER']);
};

export const canCreateDefects = (userRole: Role): boolean => {
    return hasAnyRole(userRole, ['TESTER', 'ADMIN', 'MANAGER']);
};
