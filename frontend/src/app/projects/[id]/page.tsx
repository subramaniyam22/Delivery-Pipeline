'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { projectsAPI, artifactsAPI, workflowAPI, onboardingAPI, projectTasksAPI, remindersAPI } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import Navigation from '@/components/Navigation';

interface Contact {
    name: string;
    email: string;
    role?: string;
    is_primary: boolean;
}

interface OnboardingData {
    id: string;
    project_id: string;
    client_access_token: string | null;
    contacts_json: Contact[];
    logo_url: string | null;
    logo_file_path: string | null;
    images_json: any[];
    copy_text: string | null;
    use_custom_copy: boolean;
    custom_copy_base_price: number;
    custom_copy_word_count: number;
    custom_copy_final_price: number | null;
    wcag_compliance_required: boolean;
    wcag_level: string;
    privacy_policy_url: string | null;
    privacy_policy_text: string | null;
    theme_preference: string | null;
    selected_template_id: string | null;
    theme_colors_json: Record<string, string>;
    custom_fields_json: Array<{ field_name: string; field_value: string; field_type: string }>;
    completion_percentage: number;
    reminder_count: number;
    auto_reminder_enabled: boolean;
    next_reminder_at: string | null;
}

interface Template {
    id: string;
    name: string;
    description: string;
    colors: { primary: string; secondary: string; accent: string };
    features: string[];
}

interface PricingTier {
    words: number;
    price: number;
    description: string;
}

interface ProjectTask {
    id: string;
    project_id: string;
    stage: string;
    title: string;
    description: string | null;
    is_predefined: boolean;
    is_required: boolean;
    is_auto_completed: boolean;
    linked_field: string | null;
    status: string;
    assignee_user_id: string | null;
    due_date: string | null;
    completed_at: string | null;
    order_index: number;
}

interface CompletionStatus {
    completion_percentage: number;
    task_completion_percentage: number;
    can_auto_advance: boolean;
    missing_fields: string[];
    completed_tasks: number;
    total_required_tasks: number;
    client_form_url: string | null;
}

const STAGES = [
    { key: 'ONBOARDING', label: 'Onboarding', icon: '📋' },
    { key: 'ASSIGNMENT', label: 'Assignment', icon: '📤' },
    { key: 'BUILD', label: 'Build', icon: '🔨' },
    { key: 'TEST', label: 'Test', icon: '🧪' },
    { key: 'DEFECT_VALIDATION', label: 'Defect Validation', icon: '🔍' },
    { key: 'COMPLETE', label: 'Complete', icon: '✅' },
];

const THEME_OPTIONS = [
    { value: 'light', label: 'Light Theme' },
    { value: 'dark', label: 'Dark Theme' },
    { value: 'custom', label: 'Custom Colors' },
];

const WCAG_LEVELS = [
    { value: 'A', label: 'Level A (Minimum)' },
    { value: 'AA', label: 'Level AA (Standard)' },
    { value: 'AAA', label: 'Level AAA (Enhanced)' },
];

export default function ProjectDetailPage() {
    const router = useRouter();
    const params = useParams();
    const projectId = params.id as string;

    const [project, setProject] = useState<any>(null);
    const [artifacts, setArtifacts] = useState<any[]>([]);
    const [user, setUser] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [advancing, setAdvancing] = useState(false);

    // Onboarding state
    const [onboardingData, setOnboardingData] = useState<OnboardingData | null>(null);
    const [tasks, setTasks] = useState<ProjectTask[]>([]);
    const [completionStatus, setCompletionStatus] = useState<CompletionStatus | null>(null);
    const [templates, setTemplates] = useState<Template[]>([]);
    const [pricingTiers, setPricingTiers] = useState<PricingTier[]>([]);

    // Modal states
    const [showContactModal, setShowContactModal] = useState(false);
    const [showTaskModal, setShowTaskModal] = useState(false);
    const [showReminderModal, setShowReminderModal] = useState(false);
    const [showCustomFieldModal, setShowCustomFieldModal] = useState(false);

    // Form states
    const [newContact, setNewContact] = useState<Contact>({ name: '', email: '', role: '', is_primary: false });
    const [newTask, setNewTask] = useState({ title: '', description: '', stage: 'ONBOARDING', is_required: true });
    const [reminderData, setReminderData] = useState({ recipient_email: '', recipient_name: '', message: '' });
    const [newCustomField, setNewCustomField] = useState({ field_name: '', field_value: '', field_type: 'text' });

    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const isAdmin = user?.role === 'ADMIN' || user?.role === 'MANAGER';

    useEffect(() => {
        const currentUser = getCurrentUser();
        if (!currentUser) {
            router.push('/login');
            return;
        }
        setUser(currentUser);
        loadAllData();
    }, [projectId]);

    const loadAllData = async () => {
        try {
            const [projectRes, artifactsRes] = await Promise.all([
                projectsAPI.get(projectId),
                artifactsAPI.list(projectId),
            ]);

            setProject(projectRes.data);
            setArtifacts(artifactsRes.data);

            // Load onboarding data if in onboarding stage
            if (projectRes.data.current_stage === 'ONBOARDING') {
                await loadOnboardingData();
            }

            // Load tasks for current stage
            await loadTasks(projectRes.data.current_stage);
        } catch (error) {
            console.error('Failed to load project data:', error);
            setError('Failed to load project data');
        } finally {
            setLoading(false);
        }
    };

    const loadOnboardingData = async () => {
        try {
            const [dataRes, completionRes, templatesRes, pricingRes] = await Promise.all([
                onboardingAPI.getData(projectId),
                onboardingAPI.getCompletion(projectId),
                onboardingAPI.getTemplates(),
                onboardingAPI.getCopyPricing(),
            ]);
            setOnboardingData(dataRes.data);
            setCompletionStatus(completionRes.data);
            setTemplates(templatesRes.data.templates || []);
            setPricingTiers(pricingRes.data.pricing_tiers || []);
        } catch (error) {
            console.error('Failed to load onboarding data:', error);
        }
    };

    const loadTasks = async (stage: string) => {
        try {
            const res = await projectTasksAPI.list(projectId, stage);
            setTasks(res.data);
        } catch (error) {
            console.error('Failed to load tasks:', error);
        }
    };

    const saveOnboardingData = async (updates: Partial<OnboardingData>) => {
        if (!onboardingData) return;
        setSaving(true);
        setError('');

        try {
            const payload: any = {};

            if (updates.contacts_json !== undefined) {
                payload.contacts = updates.contacts_json;
            }
            if (updates.logo_url !== undefined) {
                payload.logo_url = updates.logo_url;
            }
            if (updates.images_json !== undefined) {
                payload.images = updates.images_json;
            }
            if (updates.copy_text !== undefined) {
                payload.copy_text = updates.copy_text;
            }
            if (updates.use_custom_copy !== undefined) {
                payload.use_custom_copy = updates.use_custom_copy;
            }
            if (updates.wcag_compliance_required !== undefined) {
                payload.wcag_compliance_required = updates.wcag_compliance_required;
            }
            if (updates.wcag_level !== undefined) {
                payload.wcag_level = updates.wcag_level;
            }
            if (updates.privacy_policy_url !== undefined) {
                payload.privacy_policy_url = updates.privacy_policy_url;
            }
            if (updates.privacy_policy_text !== undefined) {
                payload.privacy_policy_text = updates.privacy_policy_text;
            }
            if (updates.theme_preference !== undefined) {
                payload.theme_preference = updates.theme_preference;
            }
            if (updates.theme_colors_json !== undefined) {
                payload.theme_colors = updates.theme_colors_json;
            }
            if (updates.custom_fields_json !== undefined) {
                payload.custom_fields = updates.custom_fields_json;
            }

            const res = await onboardingAPI.updateData(projectId, payload);
            setOnboardingData(res.data);
            setSuccess('Changes saved successfully');
            setTimeout(() => setSuccess(''), 3000);

            // Reload completion status
            const completionRes = await onboardingAPI.getCompletion(projectId);
            setCompletionStatus(completionRes.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save changes');
        } finally {
            setSaving(false);
        }
    };

    const handleAdvanceWorkflow = async () => {
        setAdvancing(true);
        setError('');

        try {
            await workflowAPI.advance(projectId, 'Advancing workflow');
            setSuccess('Workflow advanced successfully');
            await loadAllData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to advance workflow');
        } finally {
            setAdvancing(false);
        }
    };

    const handleAutoAdvance = async () => {
        setAdvancing(true);
        setError('');

        try {
            const res = await onboardingAPI.checkAutoAdvance(projectId);
            if (res.data.advanced) {
                setSuccess('Project automatically advanced to Assignment stage!');
                await loadAllData();
            } else {
                setError(res.data.reason || 'Cannot auto-advance yet');
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to check auto-advance');
        } finally {
            setAdvancing(false);
        }
    };

    const handleSendBack = async () => {
        if (!project) return;
        setAdvancing(true);
        setError('');

        try {
            const stageIndex = STAGES.findIndex(s => s.key === project.current_stage);
            if (stageIndex > 0) {
                const previousStage = STAGES[stageIndex - 1].key;
                await workflowAPI.sendBack(projectId, previousStage, 'Sent back for revisions');
                setSuccess('Project sent back successfully');
                await loadAllData();
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to send back');
        } finally {
            setAdvancing(false);
        }
    };

    const addContact = async () => {
        if (!onboardingData || !newContact.name || !newContact.email) return;

        const updatedContacts = [...(onboardingData.contacts_json || []), newContact];
        await saveOnboardingData({ contacts_json: updatedContacts });
        setNewContact({ name: '', email: '', role: '', is_primary: false });
        setShowContactModal(false);
    };

    const removeContact = async (index: number) => {
        if (!onboardingData) return;
        const updatedContacts = onboardingData.contacts_json.filter((_, i) => i !== index);
        await saveOnboardingData({ contacts_json: updatedContacts });
    };

    const addCustomField = async () => {
        if (!onboardingData || !newCustomField.field_name) return;

        const updatedFields = [...(onboardingData.custom_fields_json || []), newCustomField];
        await saveOnboardingData({ custom_fields_json: updatedFields });
        setNewCustomField({ field_name: '', field_value: '', field_type: 'text' });
        setShowCustomFieldModal(false);
    };

    const updateCustomField = async (index: number, value: string) => {
        if (!onboardingData) return;
        const updatedFields = [...onboardingData.custom_fields_json];
        updatedFields[index].field_value = value;
        await saveOnboardingData({ custom_fields_json: updatedFields });
    };

    const removeCustomField = async (index: number) => {
        if (!onboardingData) return;
        const updatedFields = onboardingData.custom_fields_json.filter((_, i) => i !== index);
        await saveOnboardingData({ custom_fields_json: updatedFields });
    };

    const createTask = async () => {
        if (!newTask.title) return;

        try {
            await projectTasksAPI.create(projectId, {
                ...newTask,
                order_index: tasks.length,
            });
            await loadTasks(project?.current_stage || 'ONBOARDING');
            setNewTask({ title: '', description: '', stage: project?.current_stage || 'ONBOARDING', is_required: true });
            setShowTaskModal(false);
            setSuccess('Task created successfully');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create task');
        }
    };

    const updateTaskStatus = async (taskId: string, status: string) => {
        try {
            await projectTasksAPI.update(projectId, taskId, { status });
            await loadTasks(project?.current_stage || 'ONBOARDING');

            // Reload completion status
            const completionRes = await onboardingAPI.getCompletion(projectId);
            setCompletionStatus(completionRes.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update task');
        }
    };

    const sendReminder = async () => {
        if (!reminderData.recipient_email || !reminderData.message) return;

        try {
            await remindersAPI.send(projectId, {
                ...reminderData,
                reminder_type: 'onboarding_incomplete',
            });
            setSuccess('Reminder sent successfully');
            setReminderData({ recipient_email: '', recipient_name: '', message: '' });
            setShowReminderModal(false);

            // Reload onboarding data to update reminder count
            await loadOnboardingData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to send reminder');
        }
    };

    const getStageIndex = (stage: string) => STAGES.findIndex(s => s.key === stage);

    if (loading) {
        return (
            <div className="page-wrapper">
                <Navigation />
                <div className="loading-screen">
                    <div className="spinner" />
                    <p>Loading project...</p>
                </div>
                <style jsx>{`
                    .loading-screen {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 60vh;
                        gap: var(--space-md);
                    }
                    .loading-screen p {
                        color: var(--text-muted);
                    }
                `}</style>
            </div>
        );
    }

    if (!project || !user) return null;

    return (
        <div className="page-wrapper">
            <Navigation />
            <main className="project-detail">
                {/* Back Button */}
                <button className="btn-back" onClick={() => router.push('/projects')}>
                    ← Back to Projects
                </button>

                {/* Project Header */}
                <header className="project-header">
                    <div className="header-info">
            <h1>{project.title}</h1>
                        <div className="project-meta">
                            <span><strong>Client:</strong> {project.client_name}</span>
                            <span className={`priority priority-${project.priority.toLowerCase()}`}>
                                {project.priority}
                            </span>
                            <span className="status">{project.status}</span>
                        </div>
                    </div>
                    {completionStatus && (
                        <div className="completion-badge">
                            <div className="completion-ring">
                                <svg viewBox="0 0 36 36">
                                    <path className="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                    <path
                                        className="ring-fill"
                                        strokeDasharray={`${completionStatus.completion_percentage}, 100`}
                                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                    />
                                </svg>
                                <span className="ring-value">{completionStatus.completion_percentage}%</span>
                            </div>
                            <span className="completion-label">Complete</span>
                        </div>
                    )}
                </header>

                {/* Stage Timeline */}
                <div className="stage-timeline">
                    {STAGES.map((stage, index) => {
                        const currentIndex = getStageIndex(project.current_stage);
                        const isComplete = index < currentIndex;
                        const isCurrent = index === currentIndex;
                        return (
                            <div
                                key={stage.key}
                                className={`stage-item ${isComplete ? 'complete' : ''} ${isCurrent ? 'current' : ''}`}
                            >
                                <div className="stage-icon">{isComplete ? '✓' : index + 1}</div>
                                <span className="stage-label">{stage.label}</span>
                            </div>
                        );
                    })}
                </div>

                {/* Alerts */}
                {error && <div className="alert alert-error">{error}</div>}
                {success && <div className="alert alert-success">{success}</div>}

                {/* Onboarding Section */}
                {project.current_stage === 'ONBOARDING' && onboardingData && (
                    <div className="onboarding-section">
                        <div className="section-header">
                            <h2>📋 Onboarding Details</h2>
                            {completionStatus?.can_auto_advance && (
                                <button className="btn-auto-advance" onClick={handleAutoAdvance} disabled={advancing}>
                                    🚀 Auto-Advance (90%+ Complete)
                                </button>
                            )}
                        </div>

                        {/* Client Contacts */}
                        <div className="form-card">
                            <div className="card-header">
                                <h3>👥 Client Contacts</h3>
                                <button className="btn-add" onClick={() => setShowContactModal(true)}>+ Add Contact</button>
                            </div>
                            <div className="contacts-list">
                                {onboardingData.contacts_json?.length === 0 ? (
                                    <p className="empty-message">No contacts added yet</p>
                                ) : (
                                    onboardingData.contacts_json?.map((contact, index) => (
                                        <div key={index} className="contact-item">
                                            <div className="contact-info">
                                                <span className="contact-name">{contact.name}</span>
                                                <span className="contact-email">{contact.email}</span>
                                                {contact.role && <span className="contact-role">{contact.role}</span>}
                                                {contact.is_primary && <span className="badge-primary">Primary</span>}
                                            </div>
                                            <button className="btn-remove" onClick={() => removeContact(index)}>×</button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Assets Section */}
                        <div className="form-card">
                            <h3>🖼️ Website Assets</h3>
                            <div className="form-grid">
                                <div className="form-group">
                                    <label>Company Logo URL</label>
                                    <input
                                        type="url"
                                        value={onboardingData.logo_url || ''}
                                        onChange={(e) => saveOnboardingData({ logo_url: e.target.value })}
                                        placeholder="https://example.com/logo.png"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Website Images (comma-separated URLs)</label>
                                    <input
                                        type="text"
                                        value={onboardingData.images_json?.join(', ') || ''}
                                        onChange={(e) => saveOnboardingData({
                                            images_json: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                                        })}
                                        placeholder="https://example.com/hero.jpg, https://example.com/about.jpg"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Copy Text Section */}
                        <div className="form-card">
                            <h3>📝 Copy Text</h3>
                            <div className="form-group">
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={onboardingData.use_custom_copy}
                                        onChange={(e) => saveOnboardingData({ use_custom_copy: e.target.checked })}
                                    />
                                    Request custom copy from our team
                                </label>
                            </div>
                            {!onboardingData.use_custom_copy && (
                                <div className="form-group">
                                    <label>Client-provided Copy Text</label>
                                    <textarea
                                        value={onboardingData.copy_text || ''}
                                        onChange={(e) => saveOnboardingData({ copy_text: e.target.value })}
                                        placeholder="Enter website copy text here..."
                                        rows={4}
                                    />
                                </div>
                            )}
                        </div>

                        {/* WCAG Compliance */}
                        <div className="form-card">
                            <h3>♿ Accessibility (WCAG)</h3>
                            <div className="form-grid">
                                <div className="form-group">
                                    <label className="checkbox-label">
                                        <input
                                            type="checkbox"
                                            checked={onboardingData.wcag_compliance_required}
                                            onChange={(e) => saveOnboardingData({ wcag_compliance_required: e.target.checked })}
                                        />
                                        WCAG Compliance Required
                                    </label>
                                </div>
                                {onboardingData.wcag_compliance_required && (
                                    <div className="form-group">
                                        <label>Compliance Level</label>
                                        <select
                                            value={onboardingData.wcag_level}
                                            onChange={(e) => saveOnboardingData({ wcag_level: e.target.value })}
                                        >
                                            {WCAG_LEVELS.map(level => (
                                                <option key={level.value} value={level.value}>{level.label}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Privacy Policy */}
                        <div className="form-card">
                            <h3>🔒 Privacy Policy</h3>
                            <div className="form-grid">
                                <div className="form-group">
                                    <label>Privacy Policy URL</label>
                                    <input
                                        type="url"
                                        value={onboardingData.privacy_policy_url || ''}
                                        onChange={(e) => saveOnboardingData({ privacy_policy_url: e.target.value })}
                                        placeholder="https://example.com/privacy"
                                    />
                                </div>
                                <div className="form-group full-width">
                                    <label>Or paste Privacy Policy Text</label>
                                    <textarea
                                        value={onboardingData.privacy_policy_text || ''}
                                        onChange={(e) => saveOnboardingData({ privacy_policy_text: e.target.value })}
                                        placeholder="Paste privacy policy content here..."
                                        rows={3}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Theme Preferences */}
                        <div className="form-card">
                            <h3>🎨 Theme Preferences</h3>
                            <div className="form-grid">
                                <div className="form-group">
                                    <label>Theme Style</label>
                                    <select
                                        value={onboardingData.theme_preference || ''}
                                        onChange={(e) => saveOnboardingData({ theme_preference: e.target.value })}
                                    >
                                        <option value="">Select theme...</option>
                                        {THEME_OPTIONS.map(opt => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                                {onboardingData.theme_preference === 'custom' && (
                                    <>
                                        <div className="form-group">
                                            <label>Primary Color</label>
                                            <input
                                                type="color"
                                                value={onboardingData.theme_colors_json?.primary || '#2563eb'}
                                                onChange={(e) => saveOnboardingData({
                                                    theme_colors_json: { ...onboardingData.theme_colors_json, primary: e.target.value }
                                                })}
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label>Secondary Color</label>
                                            <input
                                                type="color"
                                                value={onboardingData.theme_colors_json?.secondary || '#7c3aed'}
                                                onChange={(e) => saveOnboardingData({
                                                    theme_colors_json: { ...onboardingData.theme_colors_json, secondary: e.target.value }
                                                })}
                                            />
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Custom Fields */}
                        <div className="form-card">
                            <div className="card-header">
                                <h3>📋 Additional Fields</h3>
                                <button className="btn-add" onClick={() => setShowCustomFieldModal(true)}>+ Add Field</button>
                            </div>
                            <div className="custom-fields-list">
                                {onboardingData.custom_fields_json?.length === 0 ? (
                                    <p className="empty-message">No custom fields added</p>
                                ) : (
                                    onboardingData.custom_fields_json?.map((field, index) => (
                                        <div key={index} className="custom-field-item">
                                            <label>{field.field_name}</label>
                                            {field.field_type === 'textarea' ? (
                                                <textarea
                                                    value={field.field_value}
                                                    onChange={(e) => updateCustomField(index, e.target.value)}
                                                    rows={2}
                                                />
                                            ) : (
                                                <input
                                                    type={field.field_type}
                                                    value={field.field_value}
                                                    onChange={(e) => updateCustomField(index, e.target.value)}
                                                />
                                            )}
                                            <button className="btn-remove" onClick={() => removeCustomField(index)}>×</button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Missing Fields Alert */}
                        {completionStatus && completionStatus.missing_fields.length > 0 && (
                            <div className="missing-fields-alert">
                                <h4>⚠️ Missing Information</h4>
                                <ul>
                                    {completionStatus.missing_fields.map((field, index) => (
                                        <li key={index}>{field}</li>
                    ))}
                </ul>
            </div>
                        )}
                    </div>
                )}

                {/* Tasks Section - Auto-updated based on client inputs */}
                <div className="tasks-section">
                    <div className="section-header">
                        <h2>✅ Tasks ({tasks.length})</h2>
                        <div className="section-header-right">
                            {project.current_stage === 'ONBOARDING' && (
                                <span className="auto-update-badge">🔄 Auto-updates from client inputs</span>
                            )}
                            {isAdmin && !project.current_stage.includes('ONBOARDING') && (
                                <button className="btn-add" onClick={() => setShowTaskModal(true)}>+ Add Task</button>
                            )}
                        </div>
                    </div>
                    <div className="tasks-list">
                        {tasks.map((task) => (
                            <div key={task.id} className={`task-item ${task.status === 'DONE' ? 'completed' : ''} ${task.is_auto_completed ? 'auto-completed' : ''}`}>
                                <div className="task-status-indicator">
                                    {task.status === 'DONE' ? (
                                        <span className="status-done">✓</span>
                                    ) : (
                                        <span className="status-pending">○</span>
                                    )}
                                </div>
                                <div className="task-content">
                                    <span className="task-title">{task.title}</span>
                                    {task.description && <span className="task-description">{task.description}</span>}
                                    <div className="task-meta">
                                        {task.is_auto_completed && <span className="badge-auto">Auto-completed</span>}
                                        {task.linked_field && <span className="badge-linked">Linked: {task.linked_field}</span>}
                                        {task.is_required && <span className="badge-required">Required</span>}
                                    </div>
                                </div>
                                <div className="task-status-badge">
                                    {task.status === 'DONE' ? (
                                        <span className="status-badge done">Complete</span>
                                    ) : (
                                        <span className="status-badge pending">Pending</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                    {completionStatus && (
                        <div className="task-progress">
                            <div className="progress-bar">
                                <div
                                    className="progress-fill"
                                    style={{ width: `${completionStatus.task_completion_percentage}%` }}
                                />
                            </div>
                            <span className="progress-text">
                                {completionStatus.completed_tasks} of {completionStatus.total_required_tasks} tasks complete
                            </span>
                        </div>
                    )}
                </div>

                {/* Artifacts Section */}
                <div className="artifacts-section">
                    <h2>📎 Artifacts ({artifacts.length})</h2>
                    {artifacts.length === 0 ? (
                        <p className="empty-message">No artifacts uploaded yet</p>
                    ) : (
                        <ul className="artifacts-list">
                            {artifacts.map((artifact) => (
                                <li key={artifact.id} className="artifact-item">
                                    <span className="artifact-name">{artifact.filename}</span>
                                    <span className="artifact-stage">{artifact.stage}</span>
                                    <span className="artifact-type">{artifact.type}</span>
                            </li>
                        ))}
                    </ul>
                    )}
                </div>

                {/* Admin Actions */}
                {isAdmin && (
                    <div className="admin-actions">
                        <h3>Admin Actions</h3>
                        
                        {/* Client Form Link */}
                        {project.current_stage === 'ONBOARDING' && completionStatus?.client_form_url && (
                            <div className="client-form-section">
                                <h4>📤 Client Onboarding Form</h4>
                                <p>Share this link with the client to collect onboarding information:</p>
                                <div className="form-link-box">
                                    <input 
                                        type="text" 
                                        readOnly 
                                        value={`${window.location.origin}${completionStatus.client_form_url}`}
                                        onClick={(e) => (e.target as HTMLInputElement).select()}
                                    />
                                    <button 
                                        className="btn-copy"
                                        onClick={() => {
                                            navigator.clipboard.writeText(`${window.location.origin}${completionStatus.client_form_url}`);
                                            setSuccess('Link copied to clipboard!');
                                            setTimeout(() => setSuccess(''), 3000);
                                        }}
                                    >
                                        📋 Copy
                                    </button>
                                </div>
                                
                                {/* Auto Reminder Toggle */}
                                <div className="auto-reminder-toggle">
                                    <label>
                                        <input
                                            type="checkbox"
                                            checked={onboardingData?.auto_reminder_enabled ?? true}
                                            onChange={async (e) => {
                                                try {
                                                    await onboardingAPI.toggleAutoReminder(projectId, e.target.checked);
                                                    await loadOnboardingData();
                                                    setSuccess(`Auto-reminders ${e.target.checked ? 'enabled' : 'disabled'}`);
                                                } catch (err) {
                                                    setError('Failed to update reminder settings');
                                                }
                                            }}
                                        />
                                        Send auto-reminder every 24 hours for missing information
                                    </label>
                                    {onboardingData?.next_reminder_at && onboardingData.auto_reminder_enabled && (
                                        <p className="next-reminder">Next reminder: {new Date(onboardingData.next_reminder_at).toLocaleString()}</p>
                                    )}
                                </div>
                            </div>
                        )}
                        
                        <div className="actions-row">
                            <button
                                className="btn-advance"
                                onClick={handleAdvanceWorkflow}
                                disabled={advancing || project.current_stage === 'COMPLETE'}
                            >
                                {advancing ? 'Processing...' : '➡️ Advance Workflow'}
                            </button>
                            <button
                                className="btn-send-back"
                                onClick={handleSendBack}
                                disabled={advancing || project.current_stage === 'ONBOARDING'}
                            >
                                ⬅️ Send Back
                            </button>
                            {project.current_stage === 'ONBOARDING' && (
                                <button
                                    className="btn-reminder"
                                    onClick={() => setShowReminderModal(true)}
                                >
                                    📧 Send Manual Reminder
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {/* Contact Modal */}
                {showContactModal && (
                    <div className="modal-overlay" onClick={() => setShowContactModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Add Contact</h2>
                            <div className="form-group">
                                <label>Name *</label>
                                <input
                                    type="text"
                                    value={newContact.name}
                                    onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label>Email *</label>
                                <input
                                    type="email"
                                    value={newContact.email}
                                    onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label>Role</label>
                                <input
                                    type="text"
                                    value={newContact.role}
                                    onChange={(e) => setNewContact({ ...newContact, role: e.target.value })}
                                    placeholder="e.g., Project Manager"
                                />
                            </div>
                            <div className="form-group">
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={newContact.is_primary}
                                        onChange={(e) => setNewContact({ ...newContact, is_primary: e.target.checked })}
                                    />
                                    Primary Contact
                                </label>
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowContactModal(false)}>Cancel</button>
                                <button className="btn-submit" onClick={addContact}>Add Contact</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Task Modal */}
                {showTaskModal && (
                    <div className="modal-overlay" onClick={() => setShowTaskModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Add Task</h2>
                            <div className="form-group">
                                <label>Title *</label>
                                <input
                                    type="text"
                                    value={newTask.title}
                                    onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label>Description</label>
                                <textarea
                                    value={newTask.description}
                                    onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                                    rows={3}
                                />
                            </div>
                            <div className="form-group">
                                <label>Stage</label>
                                <select
                                    value={newTask.stage}
                                    onChange={(e) => setNewTask({ ...newTask, stage: e.target.value })}
                                >
                                    {STAGES.map(stage => (
                                        <option key={stage.key} value={stage.key}>{stage.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={newTask.is_required}
                                        onChange={(e) => setNewTask({ ...newTask, is_required: e.target.checked })}
                                    />
                                    Required Task
                                </label>
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowTaskModal(false)}>Cancel</button>
                                <button className="btn-submit" onClick={createTask}>Add Task</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Reminder Modal */}
                {showReminderModal && (
                    <div className="modal-overlay" onClick={() => setShowReminderModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Send Reminder</h2>
                            <div className="form-group">
                                <label>Recipient Email *</label>
                                <input
                                    type="email"
                                    value={reminderData.recipient_email}
                                    onChange={(e) => setReminderData({ ...reminderData, recipient_email: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label>Recipient Name</label>
                                <input
                                    type="text"
                                    value={reminderData.recipient_name}
                                    onChange={(e) => setReminderData({ ...reminderData, recipient_name: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label>Message *</label>
                                <textarea
                                    value={reminderData.message}
                                    onChange={(e) => setReminderData({ ...reminderData, message: e.target.value })}
                                    rows={4}
                                    placeholder="Please provide the required onboarding details..."
                                />
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowReminderModal(false)}>Cancel</button>
                                <button className="btn-submit" onClick={sendReminder}>Send Reminder</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Custom Field Modal */}
                {showCustomFieldModal && (
                    <div className="modal-overlay" onClick={() => setShowCustomFieldModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Add Custom Field</h2>
                            <div className="form-group">
                                <label>Field Name *</label>
                                <input
                                    type="text"
                                    value={newCustomField.field_name}
                                    onChange={(e) => setNewCustomField({ ...newCustomField, field_name: e.target.value })}
                                    placeholder="e.g., Brand Guidelines URL"
                                />
                            </div>
                            <div className="form-group">
                                <label>Field Type</label>
                                <select
                                    value={newCustomField.field_type}
                                    onChange={(e) => setNewCustomField({ ...newCustomField, field_type: e.target.value })}
                                >
                                    <option value="text">Text</option>
                                    <option value="url">URL</option>
                                    <option value="textarea">Long Text</option>
                                    <option value="date">Date</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Initial Value</label>
                                <input
                                    type="text"
                                    value={newCustomField.field_value}
                                    onChange={(e) => setNewCustomField({ ...newCustomField, field_value: e.target.value })}
                                />
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowCustomFieldModal(false)}>Cancel</button>
                                <button className="btn-submit" onClick={addCustomField}>Add Field</button>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            <style jsx>{`
                .project-detail {
          max-width: 1200px;
          margin: 0 auto;
                    padding: var(--space-xl) var(--space-lg);
                }

                .btn-back {
                    display: inline-flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: var(--space-sm) var(--space-md);
                    background: var(--accent-primary);
                    color: white;
                    border-radius: var(--radius-md);
                    font-size: 14px;
                    font-weight: 500;
                    margin-bottom: var(--space-lg);
                }

                .btn-back:hover {
                    background: var(--accent-primary-hover);
                }

                .project-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: var(--space-xl);
                    padding: var(--space-lg);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                }

                .header-info h1 {
                    margin-bottom: var(--space-sm);
                    color: var(--text-primary);
                }

                .project-meta {
                    display: flex;
                    gap: var(--space-md);
                    align-items: center;
                    flex-wrap: wrap;
                }

                .project-meta span {
                    color: var(--text-secondary);
                    font-size: 14px;
                }

                .priority {
                    padding: 4px 10px;
                    border-radius: var(--radius-full);
                    font-size: 12px;
                    font-weight: 600;
                }

                .priority-high, .priority-critical {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                }

                .priority-medium {
                    background: var(--color-warning-bg);
                    color: var(--color-warning);
                }

                .priority-low {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                }

                .status {
                    padding: 4px 10px;
                    background: var(--color-info-bg);
                    color: var(--color-info);
                    border-radius: var(--radius-full);
                    font-size: 12px;
                    font-weight: 600;
                }

                .completion-badge {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: var(--space-xs);
                }

                .completion-ring {
                    position: relative;
                    width: 64px;
                    height: 64px;
                }

                .completion-ring svg {
                    transform: rotate(-90deg);
                }

                .ring-bg {
                    fill: none;
                    stroke: var(--border-light);
                    stroke-width: 3;
                }

                .ring-fill {
                    fill: none;
                    stroke: var(--color-success);
                    stroke-width: 3;
                    stroke-linecap: round;
                }

                .ring-value {
                    position: absolute;
                    inset: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                    font-weight: 700;
                    color: var(--text-primary);
                }

                .completion-label {
                    font-size: 12px;
                    color: var(--text-muted);
                }

                .stage-timeline {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: var(--space-xl);
                    padding: var(--space-lg);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                }

                .stage-item {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: var(--space-sm);
                    flex: 1;
                }

                .stage-icon {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--bg-tertiary);
                    color: var(--text-muted);
                    font-weight: 600;
                    font-size: 14px;
                    border: 2px solid var(--border-light);
                }

                .stage-item.current .stage-icon {
                    background: var(--accent-primary);
          color: white;
                    border-color: var(--accent-primary);
                }

                .stage-item.complete .stage-icon {
                    background: var(--color-success);
                    color: white;
                    border-color: var(--color-success);
                }

                .stage-label {
                    font-size: 12px;
                    color: var(--text-muted);
                    text-align: center;
                }

                .stage-item.current .stage-label {
                    color: var(--accent-primary);
                    font-weight: 600;
                }

                .alert {
                    padding: var(--space-md);
                    border-radius: var(--radius-md);
                    margin-bottom: var(--space-md);
                    font-size: 14px;
                }

                .alert-error {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                    border: 1px solid var(--color-error-border);
                }

                .alert-success {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                    border: 1px solid var(--color-success-border);
                }

                .section-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-lg);
                }

                .section-header h2 {
                    margin: 0;
                    color: var(--text-primary);
                }

                .onboarding-section, .tasks-section, .artifacts-section, .admin-actions {
                    margin-bottom: var(--space-xl);
                }

                .form-card {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    margin-bottom: var(--space-md);
                }

                .form-card h3 {
                    margin: 0 0 var(--space-md) 0;
                    font-size: 16px;
                    color: var(--text-primary);
                }

                .card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-md);
                }

                .card-header h3 {
                    margin: 0;
                }

                .form-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: var(--space-md);
                }

                .form-group {
                    margin-bottom: var(--space-md);
                }

                .form-group.full-width {
                    grid-column: span 2;
                }

                .form-group label {
                    display: block;
                    font-size: 13px;
                    font-weight: 600;
                    color: var(--text-secondary);
                    margin-bottom: var(--space-xs);
                }

                .form-group input, .form-group select, .form-group textarea {
                    width: 100%;
                    padding: 10px 12px;
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-primary);
                    font-size: 14px;
                }

                .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
                    outline: none;
                    border-color: var(--accent-primary);
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
                }

                .checkbox-label {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    cursor: pointer;
                }

                .checkbox-label input[type="checkbox"] {
                    width: auto;
                }

                .btn-add, .btn-auto-advance, .btn-advance, .btn-send-back, .btn-reminder {
                    padding: 8px 16px;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }

                .btn-add {
                    background: var(--color-info-bg);
                    color: var(--color-info);
                    border: 1px solid var(--color-info-border);
                }

                .btn-add:hover {
                    background: var(--color-info);
                    color: white;
                }

                .btn-auto-advance {
                    background: linear-gradient(135deg, var(--color-success) 0%, #059669 100%);
                    color: white;
          border: none;
                }

                .btn-auto-advance:hover:not(:disabled) {
                    transform: translateY(-1px);
                    box-shadow: var(--shadow-md);
                }

                .contacts-list, .tasks-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-sm);
                }

                .contact-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: var(--space-sm) var(--space-md);
                    background: var(--bg-secondary);
                    border-radius: var(--radius-md);
                }

                .contact-info {
                    display: flex;
                    gap: var(--space-md);
                    align-items: center;
                }

                .contact-name {
                    font-weight: 600;
                    color: var(--text-primary);
                }

                .contact-email {
                    color: var(--text-muted);
                    font-size: 13px;
                }

                .contact-role {
                    color: var(--text-hint);
                    font-size: 12px;
                }

                .badge-primary, .badge-predefined, .badge-required, .badge-auto, .badge-linked {
                    padding: 2px 8px;
                    border-radius: var(--radius-full);
                    font-size: 10px;
                    font-weight: 600;
                }

                .badge-primary {
                    background: var(--accent-primary);
                    color: white;
                }

                .badge-predefined {
                    background: var(--color-info-bg);
                    color: var(--color-info);
                }

                .badge-required {
                    background: var(--color-warning-bg);
                    color: var(--color-warning);
                }

                .badge-auto {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                }

                .badge-linked {
                    background: var(--bg-tertiary);
                    color: var(--text-muted);
                }

                .btn-remove {
                    width: 28px;
                    height: 28px;
                    border-radius: 50%;
                    background: var(--color-error-bg);
                    color: var(--color-error);
                    border: none;
          cursor: pointer;
                    font-size: 18px;
                    line-height: 1;
                }

                .btn-remove:hover {
                    background: var(--color-error);
                    color: white;
                }

                .empty-message {
                    color: var(--text-hint);
                    font-style: italic;
                    padding: var(--space-md);
                    text-align: center;
                }

                .section-header-right {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                }

                .auto-update-badge {
                    font-size: 12px;
                    color: var(--color-info);
                    background: var(--color-info-bg);
                    padding: 4px 10px;
                    border-radius: var(--radius-full);
                }

                .task-item {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    padding: var(--space-md);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                }

                .task-item.completed {
                    background: var(--color-success-bg);
                    border-color: var(--color-success-border);
                }

                .task-item.auto-completed {
                    border-left: 3px solid var(--color-success);
                }

                .task-status-indicator {
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .status-done {
                    width: 24px;
                    height: 24px;
                    background: var(--color-success);
                    color: white;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                }

                .status-pending {
                    width: 24px;
                    height: 24px;
                    border: 2px solid var(--border-medium);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: var(--text-hint);
                    font-size: 10px;
                }

                .task-status-badge .status-badge {
                    padding: 4px 10px;
                    border-radius: var(--radius-full);
                    font-size: 11px;
                    font-weight: 600;
                }

                .status-badge.done {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                }

                .status-badge.pending {
                    background: var(--bg-tertiary);
                    color: var(--text-muted);
                }

                .task-checkbox input {
                    width: 20px;
                    height: 20px;
                    cursor: pointer;
                }

                .task-content {
                    flex: 1;
                }

                .task-title {
                    display: block;
                    font-weight: 500;
                    color: var(--text-primary);
                }

                .task-item.completed .task-title {
                    text-decoration: line-through;
                    color: var(--text-muted);
                }

                .task-description {
                    display: block;
                    font-size: 13px;
                    color: var(--text-muted);
                    margin-top: 2px;
                }

                .task-meta {
                    display: flex;
                    gap: var(--space-sm);
                    margin-top: var(--space-xs);
                }

                .task-status-select {
                    padding: 6px 12px;
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    font-size: 12px;
                    color: var(--text-primary);
                }

                .task-progress {
                    margin-top: var(--space-md);
                }

                .progress-bar {
                    height: 8px;
                    background: var(--border-light);
                    border-radius: var(--radius-full);
                    overflow: hidden;
                }

                .progress-fill {
                    height: 100%;
                    background: var(--color-success);
                    border-radius: var(--radius-full);
                    transition: width 0.3s ease;
                }

                .progress-text {
                    display: block;
                    margin-top: var(--space-xs);
                    font-size: 12px;
                    color: var(--text-muted);
                    text-align: right;
                }

                .missing-fields-alert {
                    background: var(--color-warning-bg);
                    border: 1px solid var(--color-warning-border);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    margin-top: var(--space-md);
                }

                .missing-fields-alert h4 {
                    margin: 0 0 var(--space-sm) 0;
                    color: var(--color-warning);
                }

                .missing-fields-alert ul {
                    margin: 0;
                    padding-left: var(--space-lg);
                    color: var(--text-secondary);
                }

                .artifacts-list {
                    list-style: none;
                    margin: 0;
                    padding: 0;
                }

                .artifact-item {
                    display: flex;
                    gap: var(--space-md);
                    padding: var(--space-md);
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                    margin-bottom: var(--space-sm);
                }

                .artifact-name {
                    flex: 1;
                    font-weight: 500;
                    color: var(--text-primary);
                }

                .artifact-stage, .artifact-type {
                    font-size: 12px;
                    padding: 4px 8px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                    color: var(--text-muted);
                }

                .admin-actions {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                }

                .admin-actions h3 {
                    margin: 0 0 var(--space-md) 0;
                    color: var(--text-secondary);
                }

                .actions-row {
                    display: flex;
                    gap: var(--space-md);
                    flex-wrap: wrap;
                }

                .btn-advance {
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    color: white;
                    border: none;
                }

                .btn-send-back {
                    background: var(--color-warning-bg);
                    color: var(--color-warning);
                    border: 1px solid var(--color-warning-border);
                }

                .btn-reminder {
                    background: var(--color-info-bg);
                    color: var(--color-info);
                    border: 1px solid var(--color-info-border);
                }

                .btn-advance:disabled, .btn-send-back:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                /* Client Form Section */
                .client-form-section {
                    background: var(--bg-secondary);
                    border-radius: var(--radius-md);
                    padding: var(--space-lg);
                    margin-bottom: var(--space-lg);
                }

                .client-form-section h4 {
                    margin: 0 0 var(--space-sm) 0;
                    color: var(--text-primary);
                }

                .client-form-section > p {
                    margin: 0 0 var(--space-md) 0;
                    font-size: 14px;
                    color: var(--text-muted);
                }

                .form-link-box {
                    display: flex;
                    gap: var(--space-sm);
                }

                .form-link-box input {
                    flex: 1;
                    padding: 10px 12px;
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    color: var(--text-primary);
                }

                .btn-copy {
                    padding: 10px 16px;
                    background: var(--accent-primary);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 500;
                    cursor: pointer;
                    white-space: nowrap;
                }

                .btn-copy:hover {
                    background: var(--accent-primary-hover);
                }

                .auto-reminder-toggle {
                    margin-top: var(--space-md);
                    padding-top: var(--space-md);
                    border-top: 1px solid var(--border-light);
                }

                .auto-reminder-toggle label {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    font-size: 14px;
                    cursor: pointer;
                }

                .auto-reminder-toggle input {
                    width: 18px;
                    height: 18px;
                }

                .next-reminder {
                    margin: var(--space-sm) 0 0 0;
                    font-size: 12px;
                    color: var(--text-hint);
                }

                /* Modal Styles */
                .modal-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(4px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                }

                .modal {
                    background: var(--bg-primary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-xl);
                    padding: var(--space-xl);
                    width: 100%;
                    max-width: 480px;
                    box-shadow: var(--shadow-lg);
                }

                .modal h2 {
                    margin: 0 0 var(--space-lg) 0;
                    color: var(--text-primary);
                }

                .modal-actions {
                    display: flex;
                    gap: var(--space-md);
                    justify-content: flex-end;
                    margin-top: var(--space-lg);
                }

                .btn-cancel {
                    padding: 10px var(--space-lg);
                    background: var(--bg-tertiary);
                    color: var(--text-secondary);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    font-size: 14px;
                }

                .btn-submit {
                    padding: 10px var(--space-lg);
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 14px;
                    font-weight: 600;
                }

                .custom-fields-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-md);
                }

                .custom-field-item {
                    display: flex;
                    gap: var(--space-sm);
                    align-items: center;
                }

                .custom-field-item label {
                    min-width: 150px;
                    font-size: 13px;
                    font-weight: 500;
                    color: var(--text-secondary);
                }

                .custom-field-item input, .custom-field-item textarea {
                    flex: 1;
                    padding: 8px 12px;
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-primary);
                    font-size: 14px;
                }

                @media (max-width: 768px) {
                    .project-header {
                        flex-direction: column;
                        gap: var(--space-md);
                    }

                    .form-grid {
                        grid-template-columns: 1fr;
                    }

                    .form-group.full-width {
                        grid-column: span 1;
                    }

                    .stage-timeline {
                        flex-wrap: wrap;
                        gap: var(--space-sm);
                    }

                    .contact-info {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: var(--space-xs);
                    }
        }
      `}</style>
        </div>
    );
}
