import axios from 'axios';

// Determine API URL based on environment
// In production (Render), use the deployed backend URL
// In development, use localhost
const getApiUrl = () => {
    // If env var is set, use it
    if (process.env.NEXT_PUBLIC_API_URL) {
        return process.env.NEXT_PUBLIC_API_URL;
    }
    // In browser, check if we're on Render
    if (typeof window !== 'undefined') {
        const hostname = window.location.hostname;
        if (hostname.includes('onrender.com')) {
            // Production: use the Render backend
            return 'https://delivery-backend-vvbf.onrender.com';
        }
    }
    // Default: localhost for development
    return 'http://localhost:8000';
};

const API_BASE_URL = getApiUrl();

// Create axios instance
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor to add token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor to handle 401
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Clear token and redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default api;

// API methods
export const authAPI = {
    login: (email: string, password: string) =>
        api.post('/auth/login', { email, password }),
    forgotPassword: (email: string) =>
        api.post('/auth/forgot-password', { email }),
    resetPassword: (token: string, newPassword: string) =>
        api.post('/auth/reset-password', { token, new_password: newPassword }),
};

export const usersAPI = {
    me: () => api.get('/users/me'),
    list: () => api.get('/users'),
    listArchived: () => api.get('/users/archived'),
    get: (id: string) => api.get(`/users/${id}`),
    create: (data: any) => api.post('/users', data),
    update: (id: string, data: any) => api.put(`/users/${id}`, data),
    archive: (id: string) => api.delete(`/users/${id}`),
    reactivate: (id: string) => api.post(`/users/${id}/reactivate`),
    seedAdmin: () => api.post('/users/seed'),
};

export const projectsAPI = {
    list: () => api.get('/projects'),
    get: (id: string) => api.get(`/projects/${id}`),
    create: (data: any) => api.post('/projects', data),
    update: (id: string, data: any) => api.put(`/projects/${id}`, data),
    updateOnboarding: (id: string, data: any) =>
        api.post(`/projects/${id}/onboarding/update`, data),
    publishAssignment: (id: string) =>
        api.post(`/projects/${id}/assignment/publish`),
    updateBuildStatus: (id: string, data: any) =>
        api.post(`/projects/${id}/build/status`, data),
    updateTestStatus: (id: string, data: any) =>
        api.post(`/projects/${id}/test/status`, data),
    closeProject: (id: string) => api.post(`/projects/${id}/complete/close`),
};

export const workflowAPI = {
    advance: (projectId: string, notes?: string) =>
        api.post(`/projects/${projectId}/advance`, { notes }),
    approveBuild: (projectId: string, notes?: string) =>
        api.post(`/projects/${projectId}/human/approve-build`, { notes }),
    sendBack: (projectId: string, targetStage: string, reason: string) =>
        api.post(`/projects/${projectId}/human/send-back`, {
            target_stage: targetStage,
            reason,
        }),
};

export const artifactsAPI = {
    list: (projectId: string) => api.get(`/projects/${projectId}/artifacts`),
    upload: (projectId: string, formData: FormData) =>
        api.post(`/projects/${projectId}/artifacts/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        }),
    delete: (artifactId: string) => api.delete(`/artifacts/${artifactId}`),
};

export const tasksAPI = {
    list: (projectId: string) => api.get(`/projects/${projectId}/tasks`),
    create: (projectId: string, data: any) =>
        api.post(`/projects/${projectId}/tasks`, data),
    update: (taskId: string, data: any) => api.put(`/tasks/${taskId}`, data),
    delete: (taskId: string) => api.delete(`/tasks/${taskId}`),
};

export const defectsAPI = {
    list: (projectId: string) => api.get(`/projects/${projectId}/defects`),
    createDraft: (projectId: string, data: any) =>
        api.post(`/projects/${projectId}/defects/create-draft`, data),
    validate: (projectId: string, defectId: string, data: any) =>
        api.post(`/projects/${projectId}/defects/validate?defect_id=${defectId}`, data),
    update: (defectId: string, data: any) =>
        api.put(`/defects/${defectId}`, data),
};

export const configAPI = {
    list: () => api.get('/admin/config'),
    get: (key: string) => api.get(`/admin/config/${key}`),
    update: (key: string, valueJson: any) =>
        api.put(`/admin/config/${key}`, { value_json: valueJson }),
};

export const onboardingAPI = {
    getData: (projectId: string) =>
        api.get(`/projects/${projectId}/onboarding-data`),
    updateData: (projectId: string, data: any) =>
        api.put(`/projects/${projectId}/onboarding-data`, data),
    getCompletion: (projectId: string) =>
        api.get(`/projects/${projectId}/onboarding-data/completion`),
    checkAutoAdvance: (projectId: string) =>
        api.post(`/projects/${projectId}/check-auto-advance`),
    getTemplates: () => api.get('/projects/templates'),
    getCopyPricing: () => api.get('/projects/copy-pricing'),
    toggleAutoReminder: (projectId: string, enabled: boolean) =>
        api.post(`/projects/${projectId}/toggle-auto-reminder`, null, { params: { enabled } }),
};

// Client API (no auth required)
export const clientAPI = {
    getOnboardingForm: (token: string) =>
        api.get(`/projects/client-onboarding/${token}`),
    updateOnboardingForm: (token: string, data: any) =>
        api.put(`/projects/client-onboarding/${token}`, data),
    uploadLogo: (token: string, file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post(`/projects/client-onboarding/${token}/upload-logo`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
    uploadImage: (token: string, file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post(`/projects/client-onboarding/${token}/upload-image`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
};

export const projectTasksAPI = {
    list: (projectId: string, stage?: string) =>
        api.get(`/projects/${projectId}/project-tasks`, { params: stage ? { stage } : {} }),
    create: (projectId: string, data: any) =>
        api.post(`/projects/${projectId}/project-tasks`, data),
    update: (projectId: string, taskId: string, data: any) =>
        api.put(`/projects/${projectId}/project-tasks/${taskId}`, data),
    delete: (projectId: string, taskId: string) =>
        api.delete(`/projects/${projectId}/project-tasks/${taskId}`),
};

export const remindersAPI = {
    list: (projectId: string) => api.get(`/projects/${projectId}/reminders`),
    send: (projectId: string, data: any) =>
        api.post(`/projects/${projectId}/send-reminder`, data),
};
