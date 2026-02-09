export interface User {
    id: string;
    name: string;
    email: string;
    role: Role;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export enum Role {
    ADMIN = 'ADMIN',
    MANAGER = 'MANAGER',
    CONSULTANT = 'CONSULTANT',
    PC = 'PC',
    BUILDER = 'BUILDER',
    TESTER = 'TESTER',
    SALES = 'SALES',
}

const DEV_ROLE_KEY = 'dev_role_override';
const DEV_ROLE_BACKUP_KEY = 'dev_role_original_user';

const isDev = () => process.env.NODE_ENV !== 'production';

export const login = async (email: string, password: string): Promise<string> => {
    const { authAPI, usersAPI } = await import('./api');

    // Step 1: Authenticate and get token
    const response = await authAPI.login(email, password);
    const token = response.data.access_token;

    // Store token immediately
    localStorage.setItem('access_token', token);

    // Decode token to get email for immediate user storage
    const payload = JSON.parse(atob(token.split('.')[1]));

    // Store minimal user immediately to ensure redirect works
    localStorage.setItem('user', JSON.stringify({
        email: payload.sub,
        role: 'ADMIN' // Default, will be updated
    }));

    // Step 2: Fetch complete user data (async, non-blocking for redirect)
    try {
        const userResponse = await usersAPI.me();
        const currentUser = userResponse.data;
        localStorage.setItem('user', JSON.stringify(currentUser));
        console.log('User data loaded:', currentUser.email, 'Role:', currentUser.role);
    } catch (error) {
        console.error('Failed to fetch user data:', error);
    }

    return token;
};

export const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    localStorage.removeItem(DEV_ROLE_KEY);
    localStorage.removeItem(DEV_ROLE_BACKUP_KEY);
    window.location.href = '/login';
};

export const getToken = (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
};

export const setToken = (token: string) => {
    localStorage.setItem('access_token', token);
};

export const getCurrentUser = (): User | null => {
    if (typeof window === 'undefined') return null;
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    try {
        const user = JSON.parse(userStr);
        return applyDevRoleOverride(user);
    } catch {
        return null;
    }
};

export const setCurrentUser = (user: User) => {
    localStorage.setItem('user', JSON.stringify(user));
};

export const getDevRoleOverride = (): Role | null => {
    if (typeof window === 'undefined' || !isDev()) return null;
    const value = localStorage.getItem(DEV_ROLE_KEY);
    if (!value) return null;
    if (Object.values(Role).includes(value as Role)) {
        return value as Role;
    }
    return null;
};

export const setDevRoleOverride = (role: Role | null) => {
    if (typeof window === 'undefined' || !isDev()) return;
    const userStr = localStorage.getItem('user');
    if (role) {
        if (userStr && !localStorage.getItem(DEV_ROLE_BACKUP_KEY)) {
            localStorage.setItem(DEV_ROLE_BACKUP_KEY, userStr);
        }
        localStorage.setItem(DEV_ROLE_KEY, role);
        if (userStr) {
            try {
                const user = JSON.parse(userStr);
                localStorage.setItem('user', JSON.stringify({ ...user, role }));
            } catch {
                // ignore parse errors
            }
        }
        return;
    }

    localStorage.removeItem(DEV_ROLE_KEY);
    const backup = localStorage.getItem(DEV_ROLE_BACKUP_KEY);
    if (backup) {
        localStorage.setItem('user', backup);
        localStorage.removeItem(DEV_ROLE_BACKUP_KEY);
    }
};

export const applyDevRoleOverride = (user: User | null): User | null => {
    if (!user) return null;
    const devRole = getDevRoleOverride();
    if (!devRole) return user;
    return { ...user, role: devRole };
};

export const isAuthenticated = (): boolean => {
    return !!getToken();
};
