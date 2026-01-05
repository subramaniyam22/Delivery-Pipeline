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
}

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
        return JSON.parse(userStr);
    } catch {
        return null;
    }
};

export const setCurrentUser = (user: User) => {
    localStorage.setItem('user', JSON.stringify(user));
};

export const isAuthenticated = (): boolean => {
    return !!getToken();
};
