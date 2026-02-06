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

// Create axios instance with cookie support
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,  // Enable sending cookies with requests
    timeout: 120000,  // 120 second timeout for Render cold starts
});

// Add request interceptor to send token in Authorization header
api.interceptors.request.use((config) => {
    // Check if we are in a browser environment
    if (typeof window !== 'undefined') {
        // First try to get token from localStorage (most reliable for JS)
        let token: string | null | undefined = localStorage.getItem('access_token');

        // If not in localStorage, attempt to get from cookie (only works if NOT httponly)
        if (!token) {
            token = document.cookie
                .split('; ')
                .find(row => row.startsWith('access_token='))
                ?.split('=')[1];
        }

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});

// Response interceptor to handle 401
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Clear any legacy localStorage data and redirect to login
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
    logout: () =>
        api.post('/auth/logout'),
    forgotPassword: (email: string) =>
        api.post('/auth/forgot-password', { email }),
    resetPassword: (token: string, newPassword: string) =>
        api.post('/auth/reset-password', { token, new_password: newPassword }),
};

export const healthAPI = {
    ping: () => api.get('/health'),
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
    getUsersByRole: (role: string) => api.get(`/users/by-role/${role}`),
};

export const projectsAPI = {
    list: () => api.get('/projects'),
    get: (id: string) => api.get(`/projects/${id}`),
    create: (data: any) => api.post('/projects', data),
    update: (id: string, data: any) => api.put(`/projects/${id}`, data),
    getPhaseSummary: (id: string) => api.get(`/projects/${id}/phase-summary`),
    updateOnboarding: (id: string, data: any) =>
        api.post(`/projects/${id}/onboarding/update`, data),
    publishAssignment: (id: string) =>
        api.post(`/projects/${id}/assignment/publish`),
    getChatLogs: (id: string) => api.get(`/api/ai/chat-logs/${id}`),
    sendConsultantMessage: (data: { project_id: string; message: string }) =>
        api.post('/api/ai/chat/send', data),
    toggleAI: (data: { project_id: string; enabled: boolean }) =>
        api.post('/api/ai/toggle-ai', data),
    getAIStatus: (id: string) => api.get(`/api/ai/status/${id}`),
    updateBuildStatus: (id: string, data: any) =>
        api.post(`/projects/${id}/build/status`, data),
    updateTestStatus: (id: string, data: any) =>
        api.post(`/projects/${id}/test/status`, data),
    closeProject: (id: string) => api.post(`/projects/${id}/complete/close`),
    // Team Assignment
    assignTeam: (id: string, data: any) => api.post(`/projects/${id}/team/assign`, data),
    getTeam: (id: string) => api.get(`/projects/${id}/team`),
    getAvailableUsersByRole: (role: string) => api.get(`/projects/available-users/${role}`),
    reviewOnboarding: (id: string, action: string, notes?: string) =>
        api.post(`/projects/${id}/onboarding/review`, { action, notes }),
    toggleHITL: (id: string, enabled: boolean) =>
        api.post(`/projects/${id}/hitl-toggle?enabled=${enabled}`),
    pause: (id: string, reason: string) => api.post(`/projects/${id}/pause`, { reason }),
    archive: (id: string, reason: string) => api.post(`/projects/${id}/archive`, { reason }),
    delete: (id: string) => api.delete(`/projects/${id}`),
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
    delete: (artifactId: string) => api.delete(`/projects/artifacts/${artifactId}`),
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

export const notificationsAPI = {
    list: (skip = 0, limit = 50) => api.get(`/notifications?skip=${skip}&limit=${limit}`),
    markRead: (id: string) => api.put(`/notifications/${id}/read`),
    markAllRead: () => api.put('/notifications/read-all'),
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
    toggleAutoReminder: (projectId: string, enabled: boolean, intervalHours?: number) =>
        api.post(`/projects/${projectId}/toggle-auto-reminder`, null, {
            params: { enabled, ...(intervalHours && { interval_hours: intervalHours }) }
        }),
    sendReminder: (projectId: string, data: { recipient_email: string; recipient_name: string; message: string }) =>
        api.post(`/projects/${projectId}/send-reminder`, data),
    sendManualReminder: (projectId: string) =>
        api.post(`/projects/${projectId}/onboarding-data/remind`),
};

// Client API (no auth required)
export const clientAPI = {
    getOnboardingForm: (token: string) =>
        api.get(`/projects/client-onboarding/${token}`),
    updateOnboardingForm: (token: string, data: any) =>
        api.put(`/projects/client-onboarding/${token}`, data),
    submitOnboardingForm: (token: string, data: any) =>
        api.post(`/projects/client-onboarding/${token}/submit`, data),
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
    deleteImage: (token: string, index: number) =>
        api.delete(`/projects/client-onboarding/${token}/image`, { params: { index } }),
    deleteLogo: (token: string) =>
        api.delete(`/projects/client-onboarding/${token}/logo`),
    consultAI: (message: string, context?: any) =>
        api.post('/api/ai/consult', { message, context }),
    getChatLogs: (projectId: string) => api.get(`/api/ai/chat-logs/${projectId}`),
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

// Test Phase Sub-Agents APIs
export const testingAPI = {
    // Test Scenarios
    getScenarios: (projectId: string) =>
        api.get(`/testing/projects/${projectId}/scenarios`),
    createScenario: (projectId: string, data: any) =>
        api.post(`/testing/projects/${projectId}/scenarios`, data),
    generateScenario: (projectId: string, scenarioName: string) =>
        api.post(`/testing/projects/${projectId}/scenarios/generate?scenario_name=${encodeURIComponent(scenarioName)}`),

    // Test Cases
    getTestCases: (scenarioId: string) =>
        api.get(`/testing/scenarios/${scenarioId}/cases`),
    createTestCase: (scenarioId: string, data: any) =>
        api.post(`/testing/scenarios/${scenarioId}/cases`, data),

    // Test Executions
    getExecutions: (projectId: string) =>
        api.get(`/testing/projects/${projectId}/executions`),
    runExecution: (projectId: string, executionName: string) =>
        api.post(`/testing/projects/${projectId}/executions?execution_name=${encodeURIComponent(executionName)}`),
    getResults: (executionId: string, statusFilter?: string) =>
        api.get(`/testing/executions/${executionId}/results`, { params: statusFilter ? { status_filter: statusFilter } : {} }),

    // Defect Management
    getDefects: (projectId: string, statusFilter?: string) =>
        api.get(`/testing/projects/${projectId}/defects`, { params: statusFilter ? { status_filter: statusFilter } : {} }),
    getDefectSummary: (projectId: string) =>
        api.get(`/testing/projects/${projectId}/defects/summary`),
    reassignDefect: (defectId: string, data: { new_assignee_id: string; reason?: string }) =>
        api.post(`/testing/defects/${defectId}/reassign`, data),
    markDefectFixed: (defectId: string, data: { fix_description: string }) =>
        api.post(`/testing/defects/${defectId}/fix`, data),
    validateDefect: (defectId: string) =>
        api.post(`/testing/defects/${defectId}/validate`),
    validateAllDefects: (projectId: string) =>
        api.post(`/testing/projects/${projectId}/defects/validate-all`),

    // Builder Availability
    getAvailableBuilders: (projectId?: string) =>
        api.get('/testing/available-builders', { params: projectId ? { project_id: projectId } : {} }),
    setUserAvailability: (userId: string, data: any) =>
        api.post(`/testing/users/${userId}/availability`, data),
    getUserAvailability: (userId: string) =>
        api.get(`/testing/users/${userId}/availability`),
};

// Capacity Management API
export const capacityAPI = {
    // Configs
    getConfigs: () => api.get('/capacity/configs'),
    updateConfig: (configId: string, data: any) => api.put(`/capacity/configs/${configId}`, data),

    // User Capacity
    getUserCapacity: (userId: string, weeks?: number) =>
        api.get(`/capacity/users/${userId}/summary`, { params: weeks ? { weeks } : {} }),
    getAvailableUsers: (role: string, minHours?: number) =>
        api.get(`/capacity/available-users/${role}`, { params: minHours ? { min_hours: minHours } : {} }),
    getTeamOverview: () => api.get('/capacity/team-overview'),

    // Allocations
    allocateCapacity: (data: { user_id: string; project_id: string; date: string; hours: number }) =>
        api.post('/capacity/allocate', data),

    // AI Suggestions
    getSuggestions: (projectId: string, role: string) =>
        api.get(`/capacity/suggestions/${projectId}/${role}`),
    recordFeedback: (suggestionId: string, data: { was_accepted: boolean; feedback_notes?: string; actual_outcome?: string }) =>
        api.post(`/capacity/suggestions/${suggestionId}/feedback`, data),

    // Manual Input
    recordManualInput: (data: any) => api.post('/capacity/manual-input', data),

    // Project Workload
    getProjectWorkload: (projectId: string) => api.get(`/capacity/projects/${projectId}/workload`),
};

// Configuration API (Admin/Manager)
export const configurationAPI = {
    getTemplates: () => api.get('/templates'),
    createTemplate: (data: any) => api.post('/templates', data),
    deleteTemplate: (id: string) => api.delete(`/templates/${id}`),
    uploadBulkTemplates: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/templates/bulk', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
    togglePublish: (id: string, publish: boolean) =>
        api.post(`/templates/${id}/publish`, null, { params: { publish } }),

    // SLA Configuration
    getSLAConfigs: () => api.get('/sla/configurations'),
    updateSLAConfig: (stage: string, data: any) =>
        api.put(`/sla/configurations/${stage}`, data),
};
