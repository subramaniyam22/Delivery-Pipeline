import { Role } from './auth';

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
    if (userRole === Role.ADMIN || userRole === Role.MANAGER) {
        return true;
    }
    return userRole === requiredRole;
};

export const hasAnyRole = (userRole: Role, requiredRoles: Role[]): boolean => {
    // Admin and Manager have access to everything
    if (userRole === Role.ADMIN || userRole === Role.MANAGER) {
        return true;
    }
    return requiredRoles.includes(userRole);
};

export const canAccessStage = (userRole: Role, stage: Stage): boolean => {
    // Admin and Manager can access all stages
    if (userRole === Role.ADMIN || userRole === Role.MANAGER) {
        return true;
    }

    // Role-specific stage access
    switch (userRole) {
        case Role.CONSULTANT:
            return stage === Stage.ONBOARDING;
        case Role.PC:
            return stage === Stage.ASSIGNMENT;
        case Role.BUILDER:
            return stage === Stage.BUILD;
        case Role.TESTER:
            return stage === Stage.TEST;
        default:
            return false;
    }
};

export const canCreateProject = (userRole: Role): boolean => {
    return userRole === Role.SALES;
};

export const canManageUsers = (userRole: Role): boolean => {
    return userRole === Role.ADMIN || userRole === Role.MANAGER;
};

export const canManageConfig = (userRole: Role): boolean => {
    return userRole === Role.ADMIN || userRole === Role.MANAGER;
};

export const canApproveWorkflow = (userRole: Role): boolean => {
    return userRole === Role.ADMIN || userRole === Role.MANAGER;
};

export const canCreateTasks = (userRole: Role): boolean => {
    return hasAnyRole(userRole, [Role.PC, Role.ADMIN, Role.MANAGER]);
};

export const canCreateDefects = (userRole: Role): boolean => {
    return hasAnyRole(userRole, [Role.TESTER, Role.ADMIN, Role.MANAGER]);
};
