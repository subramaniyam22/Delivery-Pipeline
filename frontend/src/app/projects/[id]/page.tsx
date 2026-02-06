'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { projectsAPI, artifactsAPI, workflowAPI, onboardingAPI, projectTasksAPI, remindersAPI, testingAPI, usersAPI, capacityAPI } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import Navigation from '@/components/Navigation';
import './project-details.css';

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
    wcag_confirmed: boolean;
    privacy_policy_url: string | null;
    privacy_policy_text: string | null;
    theme_preference: string | null;
    selected_template_id: string | null;
    theme_colors_json: Record<string, string>;
    custom_fields_json: Array<{ field_name: string; field_value: string; field_type: string }>;
    requirements_json?: Record<string, any>;
    completion_percentage: number;
    reminder_count: number;
    auto_reminder_enabled: boolean;
    next_reminder_at: string | null;
    reminder_interval_hours?: number;
    submitted_at?: string | null;
    missing_fields_eta_json?: Record<string, string> | null;
    updated_at?: string;
    review_status?: string;
    ai_review_notes?: string | null;
    consultant_review_notes?: string | null;
}

interface Template {
    id: string;
    name: string;
    description: string;
    preview_url?: string;
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

// Test Phase Interfaces
interface TestScenario {
    id: string;
    project_id: string;
    name: string;
    description: string | null;
    script_content: string | null;
    is_generated: boolean;
    created_at: string;
    updated_at: string;
    test_cases: TestCase[];
}

interface TestCase {
    id: string;
    scenario_id: string;
    title: string;
    description: string | null;
    steps: string | null;
    expected_result: string | null;
    is_automated: boolean;
    created_at: string;
}

interface TestExecution {
    id: string;
    project_id: string;
    execution_name: string;
    status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
    started_at: string | null;
    completed_at: string | null;
    total_tests: number;
    passed_tests: number;
    failed_tests: number;
    created_at: string;
}

interface TestResult {
    id: string;
    execution_id: string;
    test_case_id: string;
    test_case_title: string;
    status: 'PASSED' | 'FAILED' | 'SKIPPED' | 'ERROR';
    error_message: string | null;
    execution_time_ms: number;
    created_at: string;
}

interface Defect {
    id: string;
    project_id: string;
    title: string;
    description: string | null;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    status: 'OPEN' | 'IN_PROGRESS' | 'FIXED' | 'VERIFIED' | 'CLOSED' | 'REOPENED';
    assigned_to_user_id: string | null;
    assigned_to_user_name: string | null;
    test_result_id: string | null;
    fix_description: string | null;
    created_at: string;
    updated_at: string;
}

interface DefectSummary {
    total: number;
    by_status: Record<string, number>;
    by_severity: Record<string, number>;
}

interface PhaseSummary {
    stage: string;
    total_tasks: number;
    completed_tasks: number;
    pending_tasks: number;
    completion_percentage: number;
}

interface ProjectHealthSummary {
    status: string;
    days_in_stage: number;
    sla_days: number;
    warning_threshold_days: number;
    critical_threshold_days: number;
    remaining_days: number;
}

interface AvailableBuilder {
    id: string;
    name: string;
    email: string;
    region: string;
    is_available: boolean;
    current_workload: number;
}

interface TeamMember {
    id: string;
    name: string;
    email: string;
    role: string;
}

interface TeamAssignments {
    pc?: TeamMember;
    consultant?: TeamMember;
    builder?: TeamMember;
    tester?: TeamMember;
}

interface AvailableUser {
    id: string;
    name: string;
    email: string;
    region: string | null;
}

interface UserCapacity {
    user_id: string;
    user_name: string;
    role: string;
    region: string | null;
    total_hours: number;
    allocated_hours: number;
    remaining_hours: number;
    utilization_percentage: number;
    capacity_status: string;
    is_recommended: boolean;
    assignment_score?: number;
}

interface AISuggestion {
    id: string;
    rank: number;
    user_id: string;
    user_name: string;
    region: string | null;
    suggestion_text: string;
    confidence_score: number;
    remaining_hours: number;
    utilization_percentage: number;
    capacity_status: string;
    assignment_score: number;
}

interface CapacityCrunchSuggestion {
    type: string;
    severity: string;
    shortage_hours: number;
    suggestions: string[];
    recommended_actions: { type: string; description: string }[];
    available_users: { user_id: string; user_name: string; remaining_hours: number }[];
}

interface SuggestionsResponse {
    project_id: string;
    role: string;
    required_hours: number;
    capacity_crunch: boolean;
    suggestions: (AISuggestion | CapacityCrunchSuggestion)[];
    available_users_count: number;
    total_available_hours: number;
}

const ChatLogsModal = ({ logs, onClose }: { logs: any[], onClose: () => void }) => {
    return (
        <div className="modal-overlay" onClick={onClose} style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', zIndex: 2000,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
            <div className="modal-content" onClick={e => e.stopPropagation()} style={{
                background: 'white', padding: '24px', borderRadius: '12px',
                width: '600px', maxHeight: '80vh', display: 'flex', flexDirection: 'column'
            }}>
                <h3 style={{ margin: 0 }}>Client Chat History</h3>
                <div style={{ flex: 1, overflowY: 'auto', marginTop: '16px', background: '#f8fafc', padding: '16px', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {logs.length === 0 ? <p style={{ color: '#64748b', textAlign: 'center' }}>No chat history found.</p> : logs.map(log => (
                        <div key={log.id} style={{
                            alignSelf: log.sender === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '80%'
                        }}>
                            <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '2px', textAlign: log.sender === 'user' ? 'right' : 'left' }}>
                                {log.sender === 'user' ? 'Client' : log.sender === 'consultant' ? 'Consultant' : 'AI Assistant'} • {new Date(log.created_at).toLocaleString()}
                            </div>
                            <div style={{
                                background: log.sender === 'user' ? '#3b82f6' : 'white',
                                color: log.sender === 'user' ? 'white' : '#1e293b',
                                padding: '8px 12px',
                                borderRadius: '8px',
                                border: log.sender === 'user' ? 'none' : '1px solid #e2e8f0',
                                whiteSpace: 'pre-wrap',
                                fontSize: '14px',
                                boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                            }}>
                                {log.message}
                            </div>
                        </div>
                    ))}
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
                    <button onClick={onClose} style={{ background: '#e2e8f0', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: 500 }}>Close</button>
                </div>
            </div>
        </div>
    );
};

const STAGES = [
    { key: 'ONBOARDING', label: 'Onboarding', icon: '📋' },
    { key: 'ASSIGNMENT', label: 'Assignment', icon: '📥' },
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

const ConsultantChatModal = ({ projectId, onClose }: { projectId: string; onClose: () => void }) => {
    const [logs, setLogs] = useState<any[]>([]);
    const [input, setInput] = useState('');
    const [aiEnabled, setAiEnabled] = useState(true);
    const [sending, setSending] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    const loadData = async () => {
        try {
            const [logsRes, statusRes] = await Promise.all([
                projectsAPI.getChatLogs(projectId),
                projectsAPI.getAIStatus(projectId)
            ]);
            setLogs(logsRes.data);
            setAiEnabled(statusRes.data.ai_enabled);
        } catch (err) {
            console.error('Failed to load chat data', err);
        }
    };

    const setupWebSocket = () => {
        // Construct WS URL
        // In local dev: ws://localhost:8000/api/ai/ws/chat/{id}
        // In prod: wss://delivery-backend-vvbf.onrender.com/api/ai/ws/chat/{id}

        let baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        if (baseUrl.startsWith('http')) {
            baseUrl = baseUrl.replace(/^http/, 'ws');
        }

        const wsUrl = `${baseUrl}/api/ai/ws/chat/${projectId}`;
        console.log('Connecting to WS:', wsUrl);

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WS Connected');
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                setLogs(prev => {
                    // Avoid duplicates
                    if (prev.find(l => l.id === message.id)) return prev;
                    return [...prev, message];
                });
                // Scroll on new message
                setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
            } catch (e) {
                console.error('WS Message Parse Error', e);
            }
        };

        ws.onclose = () => {
            console.log('WS Disconnected');
            // Optional: Reconnect logic could go here
        };

        return ws;
    };

    useEffect(() => {
        loadData();
        const ws = setupWebSocket();

        return () => {
            if (ws) ws.close();
        };
    }, [projectId]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const handleSend = async () => {
        if (!input.trim()) return;
        setSending(true);
        try {
            await projectsAPI.sendConsultantMessage({ project_id: projectId, message: input });
            setInput('');
            // await loadData(); // Handled by WebSocket
        } catch (err) {
            console.error('Failed to send message', err);
        } finally {
            setSending(false);
        }
    };

    const handleToggleAI = async () => {
        try {
            await projectsAPI.toggleAI({ project_id: projectId, enabled: !aiEnabled });
            setAiEnabled(!aiEnabled);
        } catch (err) {
            console.error('Failed to toggle AI', err);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose} style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', zIndex: 2000,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
            <div className="modal-content" onClick={e => e.stopPropagation()} style={{
                background: 'white', padding: '0', borderRadius: '12px', overflow: 'hidden',
                width: '600px', height: '80vh', display: 'flex', flexDirection: 'column',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
            }}>
                <div style={{
                    padding: '16px 24px', borderBottom: '1px solid #e2e8f0',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    background: '#f8fafc'
                }}>
                    <div>
                        <h3 style={{ margin: 0, fontSize: '18px' }}>Client Chat</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', marginTop: '4px' }}>
                            <span style={{
                                width: '8px', height: '8px', borderRadius: '50%',
                                background: aiEnabled ? '#10b981' : '#cbd5e1'
                            }} />
                            {aiEnabled ? 'AI Assistant Active' : 'AI Paused (Human Mode)'}
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <button
                            onClick={handleToggleAI}
                            style={{
                                fontSize: '12px', padding: '6px 12px', borderRadius: '6px',
                                border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer',
                                color: aiEnabled ? '#dc2626' : '#10b981', fontWeight: 500
                            }}
                        >
                            {aiEnabled ? '⏸ Pause AI' : '▶ Resume AI'}
                        </button>
                        <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#64748b' }}>×</button>
                    </div>
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: '24px', background: '#f1f5f9', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {logs.length === 0 ? (
                        <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '40px' }}>
                            <p>No messages yet.</p>
                        </div>
                    ) : logs.map(log => {
                        const isMe = log.sender === 'consultant';
                        const isUser = log.sender === 'user';
                        return (
                            <div key={log.id} style={{
                                alignSelf: isMe ? 'flex-end' : 'flex-start',
                                maxWidth: '80%',
                                display: 'flex', flexDirection: 'column', alignItems: isMe ? 'flex-end' : 'flex-start'
                            }}>
                                <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px', marginLeft: '4px' }}>
                                    {isUser ? 'Client' : isMe ? 'You' : 'AI Assistant'} • {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                                <div style={{
                                    background: isMe ? '#3b82f6' : isUser ? 'white' : '#e2e8f0',
                                    color: isMe ? 'white' : '#1e293b',
                                    padding: '10px 16px',
                                    borderRadius: '12px',
                                    borderTopLeftRadius: !isMe ? '2px' : '12px',
                                    borderTopRightRadius: isMe ? '2px' : '12px',
                                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                                    whiteSpace: 'pre-wrap',
                                    fontSize: '14px',
                                    border: isUser ? '1px solid #e2e8f0' : 'none'
                                }}>
                                    {log.message}
                                </div>
                            </div>
                        );
                    })}
                    <div ref={bottomRef} />
                </div>
                <div style={{ padding: '16px 24px', background: 'white', borderTop: '1px solid #e2e8f0' }}>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <input
                            type="text"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                            placeholder="Type a message..."
                            disabled={sending}
                            style={{
                                flex: 1, padding: '10px 16px', borderRadius: '8px',
                                border: '1px solid #cbd5e1', outline: 'none', fontSize: '14px'
                            }}
                        />
                        <button
                            onClick={handleSend}
                            disabled={sending || !input.trim()}
                            style={{
                                background: '#3b82f6', color: 'white', border: 'none',
                                padding: '10px 20px', borderRadius: '8px', cursor: 'pointer',
                                fontWeight: 500, opacity: sending || !input.trim() ? 0.7 : 1
                            }}
                        >
                            Send
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

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
    const [previewImage, setPreviewImage] = useState<string | null>(null);

    // Form states
    const [newContact, setNewContact] = useState<Contact>({ name: '', email: '', role: '', is_primary: false });
    const [newTask, setNewTask] = useState({ title: '', description: '', stage: 'ONBOARDING', is_required: true });
    const [reminderData, setReminderData] = useState({ recipient_email: '', recipient_name: '', message: '' });
    const [newCustomField, setNewCustomField] = useState({ field_name: '', field_value: '', field_type: 'text' });

    // Email trigger and reminder state
    const [selectedEmailContacts, setSelectedEmailContacts] = useState<number[]>([]);
    const [reminderInterval, setReminderInterval] = useState<number>(24);
    const [showEmailModal, setShowEmailModal] = useState(false);
    const [sendingEmail, setSendingEmail] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [artifactNotes, setArtifactNotes] = useState('');

    // Test Phase State
    const [testScenarios, setTestScenarios] = useState<TestScenario[]>([]);
    const [testExecutions, setTestExecutions] = useState<TestExecution[]>([]);
    const [testResults, setTestResults] = useState<TestResult[]>([]);
    const [defects, setDefects] = useState<Defect[]>([]);
    const [defectSummary, setDefectSummary] = useState<DefectSummary | null>(null);
    const [availableBuilders, setAvailableBuilders] = useState<AvailableBuilder[]>([]);
    const [phaseSummaries, setPhaseSummaries] = useState<PhaseSummary[]>([]);
    const [healthSummary, setHealthSummary] = useState<ProjectHealthSummary | null>(null);
    const [showUpdateNotice, setShowUpdateNotice] = useState(false);

    // Test Phase UI State
    const [activeTestTab, setActiveTestTab] = useState<'scenarios' | 'executions' | 'defects'>('scenarios');
    const [selectedScenario, setSelectedScenario] = useState<TestScenario | null>(null);
    const [selectedExecution, setSelectedExecution] = useState<TestExecution | null>(null);
    const [selectedDefect, setSelectedDefect] = useState<Defect | null>(null);
    const [defectStatusFilter, setDefectStatusFilter] = useState<string>('');
    const [testLoading, setTestLoading] = useState(false);

    // Test Phase Modals
    const [showCreateScenarioModal, setShowCreateScenarioModal] = useState(false);
    const [showCreateTestCaseModal, setShowCreateTestCaseModal] = useState(false);
    const [showRunExecutionModal, setShowRunExecutionModal] = useState(false);
    const [showReassignDefectModal, setShowReassignDefectModal] = useState(false);
    const [showFixDefectModal, setShowFixDefectModal] = useState(false);

    // Test Phase Forms
    const [newScenario, setNewScenario] = useState({ name: '', description: '' });
    const [newTestCase, setNewTestCase] = useState({ title: '', description: '', steps: '', expected_result: '' });
    const [executionName, setExecutionName] = useState('');
    const [reassignData, setReassignData] = useState({ new_assignee_id: '', reason: '' });
    const [fixDescription, setFixDescription] = useState('');

    // Team Assignment State
    const [teamAssignments, setTeamAssignments] = useState<TeamAssignments>({});
    const [teamPermissions, setTeamPermissions] = useState<any>({});
    const [assignmentSequence, setAssignmentSequence] = useState<any>({});
    const [availablePCs, setAvailablePCs] = useState<AvailableUser[]>([]);
    const [availableConsultants, setAvailableConsultants] = useState<AvailableUser[]>([]);
    const [availableBuilders2, setAvailableBuilders2] = useState<AvailableUser[]>([]);
    const [availableTesters, setAvailableTesters] = useState<AvailableUser[]>([]);
    const [showTeamModal, setShowTeamModal] = useState(false);
    const [teamFormData, setTeamFormData] = useState({
        pc_user_id: '',
        consultant_user_id: '',
        builder_user_id: '',
        tester_user_id: ''
    });
    const [assigningTeam, setAssigningTeam] = useState(false);

    // Capacity State
    const [capacityByRole, setCapacityByRole] = useState<Record<string, UserCapacity[]>>({});
    const [aiSuggestions, setAiSuggestions] = useState<Record<string, SuggestionsResponse>>({});
    const [selectedRoleForSuggestion, setSelectedRoleForSuggestion] = useState<string>('');
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const [projectWorkload, setProjectWorkload] = useState<any>(null);

    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [myCapacity, setMyCapacity] = useState<any>(null);

    const [showCustomInterval, setShowCustomInterval] = useState(false);

    // Chat Logs State
    const [showChatLogs, setShowChatLogs] = useState(false);
    const [chatLogs, setChatLogs] = useState<any[]>([]);




    const handleViewChatLogs = async () => {
        try {
            const res = await projectsAPI.getChatLogs(projectId);
            setChatLogs(res.data);
            setShowChatLogs(true);
        } catch (err) {
            console.error('Failed to load chat logs:', err);
            setError('Failed to load chat logs');
        }
    };

    // Role and assignment checks
    const isAdmin = user?.role === 'ADMIN' || user?.role === 'MANAGER';
    const isExecutiveAdmin = user?.role === 'ADMIN';

    // Check if current user is assigned to this project (check both teamAssignments and project direct fields)
    const isAssignedToProject = user && project && (
        teamAssignments?.consultant?.id === user.id ||
        teamAssignments?.pc?.id === user.id ||
        teamAssignments?.builder?.id === user.id ||
        teamAssignments?.tester?.id === user.id ||
        // Also check project's direct assignment fields (before team data loads)
        (project as any).consultant_user_id === user.id ||
        (project as any).pc_user_id === user.id ||
        (project as any).builder_user_id === user.id ||
        (project as any).tester_user_id === user.id
    );

    // Check if user owns/manages this project
    const isProjectOwner = user?.role === 'CONSULTANT' && isAssignedToProject;
    const isProjectManager = user?.role === 'MANAGER';

    // View mode: Full edit, read-only details, or executive summary
    const hasFullEditAccess = isProjectOwner || (user?.role === 'PC' && isAssignedToProject);
    const hasDetailedViewAccess = isProjectManager || hasFullEditAccess || (user?.role === 'BUILDER' && isAssignedToProject) || (user?.role === 'TESTER' && isAssignedToProject);
    const isExecutiveView = isExecutiveAdmin;

    useEffect(() => {
        const currentUser = getCurrentUser();
        if (!currentUser) {
            router.push('/login');
            return;
        }
        setUser(currentUser);
        loadAllData();
    }, [projectId]);

    useEffect(() => {
        if (!onboardingData?.updated_at || !user?.role) return;
        if (user.role !== 'CONSULTANT' || !isAssignedToProject) return;
        const key = `onboarding_seen_${projectId}`;
        const lastSeen = localStorage.getItem(key);
        const updatedAt = new Date(onboardingData.updated_at);
        if (!lastSeen || updatedAt > new Date(lastSeen)) {
            setShowUpdateNotice(true);
        }
    }, [onboardingData?.updated_at, user?.role, isAssignedToProject, projectId]);

    const loadAllData = async () => {
        try {
            const [projectRes, artifactsRes] = await Promise.all([
                projectsAPI.get(projectId),
                artifactsAPI.list(projectId),
            ]);

            setProject(projectRes.data);
            setArtifacts(artifactsRes.data);

            const currentUser = getCurrentUser();
            if (currentUser?.role && ['ADMIN', 'MANAGER'].includes(currentUser.role)) {
                const phaseRes = await projectsAPI.getPhaseSummary(projectId);
                setPhaseSummaries(phaseRes.data?.phase_summaries || []);
                setHealthSummary(phaseRes.data?.health || null);
            }

            // Load onboarding data for requirements visibility across stages
            const onboardingRes = await loadOnboardingData();
            if (onboardingRes && onboardingRes.reminder_interval_hours) {
                setReminderInterval(onboardingRes.reminder_interval_hours);
                setShowCustomInterval(![6, 12, 24].includes(onboardingRes.reminder_interval_hours));
            }

            // Load test phase data if in TEST or DEFECT_VALIDATION stage
            if (projectRes.data.current_stage === 'TEST' || projectRes.data.current_stage === 'DEFECT_VALIDATION') {
                await loadTestPhaseData();
            }

            // Load tasks for current stage
            await loadTasks(projectRes.data.current_stage);

            // Load team assignments (don't block if it fails)
            loadTeamData().catch(err => console.error('Team data load error:', err));
        } catch (error) {
            console.error('Failed to load project data:', error);
            setError('Failed to load project data');
        } finally {
            setLoading(false);
        }


    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.length) return;
        const file = e.target.files[0];
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('stage', project?.current_stage || 'ONBOARDING');
            formData.append('artifact_type', 'DOCUMENT'); // Default type
            if (artifactNotes) {
                formData.append('notes', artifactNotes);
            }
            await artifactsAPI.upload(projectId, formData);
            setSuccess('Artifact uploaded successfully');
            setArtifactNotes('');
            // Refresh artifacts list
            const res = await artifactsAPI.list(projectId);
            setArtifacts(res.data);
        } catch (err) {
            console.error('Upload failed:', err);
            setError('Failed to upload artifact');
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteArtifact = async (artifactId: string) => {
        if (!confirm('Are you sure you want to delete this artifact?')) return;
        try {
            await artifactsAPI.delete(artifactId);
            setSuccess('Artifact deleted');
            // Refresh list
            const res = await artifactsAPI.list(projectId);
            setArtifacts(res.data);
        } catch (err) {
            console.error('Failed to delete artifact:', err);
            setError('Failed to delete artifact');
        }
    };

    const loadTestPhaseData = async () => {
        setTestLoading(true);
        try {
            const [scenariosRes, executionsRes, defectsRes, summaryRes, buildersRes] = await Promise.all([
                testingAPI.getScenarios(projectId),
                testingAPI.getExecutions(projectId),
                testingAPI.getDefects(projectId),
                testingAPI.getDefectSummary(projectId),
                testingAPI.getAvailableBuilders(projectId),
            ]);

            setTestScenarios(scenariosRes.data || []);
            setTestExecutions(executionsRes.data || []);
            setDefects(defectsRes.data || []);
            setDefectSummary(summaryRes.data);
            setAvailableBuilders(buildersRes.data || []);
        } catch (err) {
            console.error('Failed to load test phase data:', err);
        } finally {
            setTestLoading(false);
        }
    };

    const loadTestResults = async (executionId: string) => {
        try {
            const res = await testingAPI.getResults(executionId);
            setTestResults(res.data || []);
        } catch (err) {
            console.error('Failed to load test results:', err);
        }
    };

    const loadDefects = async (statusFilter?: string) => {
        try {
            const res = await testingAPI.getDefects(projectId, statusFilter);
            setDefects(res.data || []);
        } catch (err) {
            console.error('Failed to load defects:', err);
        }
    };

    const loadTeamData = async () => {
        try {
            // Load team assignments (only for Admin, Manager, PC)
            const storedUser = getCurrentUser();
            const allowedToViewTeam = storedUser?.role && ['ADMIN', 'MANAGER', 'PC'].includes(storedUser.role);
            let teamData: any = { team: {}, permissions: {}, assignment_sequence: {} };
            if (allowedToViewTeam) {
                const teamRes = await projectsAPI.getTeam(projectId).catch(e => {
                    console.error('Error loading team:', e);
                    return { data: { team: {}, permissions: {}, assignment_sequence: {} } };
                });
                teamData = teamRes.data || { team: {}, permissions: {}, assignment_sequence: {} };
                setTeamAssignments(teamData?.team || teamData || {});
                setTeamPermissions(teamData?.permissions || {});
                setAssignmentSequence(teamData?.assignment_sequence || {});
            }

            // Load available users by role with capacity info
            const [pcsRes, consultantsRes, buildersRes, testersRes] = await Promise.all([
                capacityAPI.getAvailableUsers('PC').catch(e => {
                    console.error('Error loading PCs:', e);
                    return { data: [] };
                }),
                capacityAPI.getAvailableUsers('CONSULTANT').catch(e => {
                    console.error('Error loading Consultants:', e);
                    return { data: [] };
                }),
                capacityAPI.getAvailableUsers('BUILDER').catch(e => {
                    console.error('Error loading Builders:', e);
                    return { data: [] };
                }),
                capacityAPI.getAvailableUsers('TESTER').catch(e => {
                    console.error('Error loading Testers:', e);
                    return { data: [] };
                }),
            ]);

            // Store capacity data by role
            setCapacityByRole({
                PC: pcsRes.data || [],
                CONSULTANT: consultantsRes.data || [],
                BUILDER: buildersRes.data || [],
                TESTER: testersRes.data || []
            });

            // Also set basic available users for backwards compatibility
            setAvailablePCs((pcsRes.data || []).map((u: UserCapacity) => ({ id: u.user_id, name: u.user_name, email: '', region: u.region })));
            setAvailableConsultants((consultantsRes.data || []).map((u: UserCapacity) => ({ id: u.user_id, name: u.user_name, email: '', region: u.region })));
            setAvailableBuilders2((buildersRes.data || []).map((u: UserCapacity) => ({ id: u.user_id, name: u.user_name, email: '', region: u.region })));
            setAvailableTesters((testersRes.data || []).map((u: UserCapacity) => ({ id: u.user_id, name: u.user_name, email: '', region: u.region })));

            // Pre-fill form with current assignments
            setTeamFormData({
                pc_user_id: teamData?.team?.pc?.id || teamData?.pc?.id || '',
                consultant_user_id: teamData?.team?.consultant?.id || teamData?.consultant?.id || '',
                builder_user_id: teamData?.team?.builder?.id || teamData?.builder?.id || '',
                tester_user_id: teamData?.team?.tester?.id || teamData?.tester?.id || ''
            });

            // Load project workload estimate
            const workloadRes = await capacityAPI.getProjectWorkload(projectId).catch(e => {
                console.error('Error loading workload:', e);
                return { data: null };
            });
            setProjectWorkload(workloadRes.data);
        } catch (err) {
            console.error('Failed to load team data:', err);
        }
    };

    const loadAiSuggestions = async (role: string) => {
        setLoadingSuggestions(true);
        setSelectedRoleForSuggestion(role);
        try {
            const res = await capacityAPI.getSuggestions(projectId, role);
            setAiSuggestions(prev => ({ ...prev, [role]: res.data }));
        } catch (err) {
            console.error('Error loading AI suggestions:', err);
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const getCapacityStatusColor = (status: string) => {
        switch (status) {
            case 'LOW': return 'var(--color-success)';
            case 'MODERATE': return 'var(--color-info)';
            case 'HIGH': return 'var(--color-warning)';
            case 'CRITICAL': return 'var(--color-error)';
            default: return 'var(--text-muted)';
        }
    };

    const getBackendBaseUrl = () => {
        // 1. Priority: Environment variable
        if (process.env.NEXT_PUBLIC_API_URL) {
            return process.env.NEXT_PUBLIC_API_URL;
        }

        // 2. Browser detection
        if (typeof window !== 'undefined') {
            const hostname = window.location.hostname;

            // Handle Render deployments
            if (hostname.includes('onrender.com')) {
                // First try to derive the backend from the frontend URL if it follows a pattern
                // frontend: delivery-frontend-60cf.onrender.com
                // backend: delivery-backend-vvbf.onrender.com (wait, the user has vvbf)

                // If the user's console showed vvbf and it's 404ing, maybe they have another one?
                // Actually, I'll keep vvbf as default but add a way to override it via hostname
                if (hostname.includes('delivery-frontend-60cf')) {
                    return 'https://delivery-backend-vvbf.onrender.com';
                }

                return 'https://delivery-backend-vvbf.onrender.com';
            }
        }

        return 'http://localhost:8000';
    };

    const getAssetUrl = (path?: string | null) => {
        if (!path) return '';
        if (path.startsWith('http')) return path;

        const baseUrl = getBackendBaseUrl();
        // Remove leading ./ or / if present to normalize
        let cleanPath = path.replace(/\\/g, '/').replace(/^\.?\//, '');

        // If the path already has 'uploads/' at the start, don't duplicate it
        if (cleanPath.startsWith('uploads/')) {
            return `${baseUrl}/${cleanPath}`;
        }
        return `${baseUrl}/uploads/${cleanPath}`;
    };
    const getImageItems = () => {
        const images = onboardingData?.images_json || [];
        return images.map((img: any, index: number) => {
            if (typeof img === 'string') {
                return { key: `${img}-${index}`, name: img, url: getAssetUrl(img) };
            }
            const path = img.url || img.file_path || img.path || '';
            const name = img.filename || img.name || path.split('/').pop() || `image-${index + 1}`;
            return { key: `${name}-${index}`, name, url: getAssetUrl(path) };
        });
    };

    const getTemplateLabel = () => {
        if (onboardingData?.selected_template_id) {
            const selected = templates.find(t => t.id === onboardingData.selected_template_id);
            return selected?.name || onboardingData.selected_template_id;
        }
        if (onboardingData?.theme_preference) {
            return onboardingData.theme_preference.charAt(0).toUpperCase() + onboardingData.theme_preference.slice(1);
        }
        return 'Not selected';
    };

    const getCopySummary = () => {
        if (!onboardingData) return 'Not provided';
        if (onboardingData.use_custom_copy) {
            const price = onboardingData.custom_copy_final_price;
            const words = onboardingData.custom_copy_word_count;
            const priceLabel = price ? ` - $${price}` : '';
            const wordLabel = words ? ` (${words} words)` : '';
            return `Custom copy requested${priceLabel}${wordLabel}`;
        }
        return onboardingData.copy_text || 'Not provided';
    };

    const getRequirementsChecklistItems = () => {
        const req = onboardingData?.requirements_json || {};
        const hasValue = (val: any) => {
            if (val === null || val === undefined) return false;
            if (typeof val === 'string') return val.trim().length > 0;
            if (Array.isArray(val)) return val.length > 0;
            if (typeof val === 'boolean') return val === true;
            return true;
        };

        return [
            { label: 'Project Summary', filled: hasValue(req.project_summary) },
            { label: 'Project Notes', filled: hasValue(req.project_notes) },
            { label: 'Phase', filled: hasValue(req.phase_number) },
            { label: 'Template Mode', filled: hasValue(req.template_mode) },
            { label: 'Template References', filled: req.template_mode === 'NEW' ? hasValue(req.template_references) : hasValue(onboardingData?.selected_template_id) },
            {
                label: 'Brand Guidelines',
                filled: req.brand_guidelines_available === true ? hasValue(req.brand_guidelines_details) : req.brand_guidelines_available === false
            },
            { label: 'Color Selection', filled: hasValue(req.color_selection) },
            { label: 'Font Selection', filled: hasValue(req.font_selection) },
            {
                label: 'Custom Graphics',
                filled: req.custom_graphic_notes_enabled === true ? hasValue(req.custom_graphic_notes) : req.custom_graphic_notes_enabled === false
            },
            { label: 'Navigation', filled: hasValue(req.navigation_notes) },
            { label: 'Stock Images', filled: hasValue(req.stock_images_reference) },
            { label: 'Floor Plans', filled: hasValue(req.floor_plan_images) },
            { label: 'Sitemap', filled: hasValue(req.sitemap) },
            { label: 'Virtual Tours', filled: hasValue(req.virtual_tours) },
            { label: 'POI Categories', filled: hasValue(req.poi_categories) },
            {
                label: 'Specials',
                filled: req.specials_enabled === true ? hasValue(req.specials_details) : req.specials_enabled === false
            },
            { label: 'Copy Scope', filled: hasValue(req.copy_scope_notes) },
            { label: 'Pages', filled: hasValue(req.pages) },
            { label: 'Domain Type', filled: hasValue(req.domain_type) },
            { label: 'Vanity Domains', filled: hasValue(req.vanity_domains) },
            { label: 'Call Tracking', filled: hasValue(req.call_tracking_plan) },
        ];
    };

    const getAllOnboardingItems = () => {
        if (!onboardingData) return [];
        const req = getRequirementsChecklistItems();

        // Essential Items (matching Client Onboarding logic)
        const essentialItems = [
            { label: 'Primary Contact', filled: (onboardingData.contacts_json?.length || 0) > 0 },
            { label: 'Company Logo', filled: !!(onboardingData.logo_url || onboardingData.logo_file_path) },
            { label: 'Website Images', filled: (onboardingData.images_json?.length || 0) > 0 },
            { label: 'Copy Text', filled: !!(onboardingData.copy_text || onboardingData.use_custom_copy) },
            { label: 'WCAG Requirements', filled: !!onboardingData.wcag_confirmed },
            { label: 'Privacy Policy', filled: !!(onboardingData.privacy_policy_url || onboardingData.privacy_policy_text) },
            { label: 'Theme / Template', filled: !!(onboardingData.selected_template_id) }
        ];

        return [...essentialItems, ...req];
    };

    const renderReadonlyOnboardingDetails = () => {
        const requirements = onboardingData?.requirements_json || {};

        const readonlyCardStyle: React.CSSProperties = {
            padding: 'var(--space-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-light)',
            marginBottom: 'var(--space-lg)',
        };
        const fieldStyle: React.CSSProperties = {
            background: 'var(--bg-card)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-md)',
            boxShadow: 'var(--shadow-sm)',
        };

        const handleDownload = async (e: React.MouseEvent, url: string, filename: string) => {
            e.preventDefault();
            e.stopPropagation();
            try {
                const response = await fetch(url);
                const blob = await response.blob();
                const blobUrl = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = blobUrl;
                link.download = filename || 'download';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(blobUrl);
            } catch (error) {
                console.error('Download failed:', error);
                window.open(url, '_blank');
            }
        };

        const renderField = (label: string, value: string | undefined) => {
            if (!value) return (
                <div className="readonly-item">
                    <label>{label}</label>
                    <span className="empty">Not provided</span>
                </div>
            );

            // SPECIAL HANDLING: Navigation Details (Comma or Newline separated)
            if (label === 'Navigation Details') {
                const items = value.split(/,|\n|- /).map(s => s.trim()).filter(s => s.length > 0 && s !== '-');
                if (items.length > 1) {
                    return (
                        <div className="readonly-item">
                            <label>{label}</label>
                            <div className="value-list">
                                {items.map((item, i) => (
                                    <div key={i} className="list-item">• {item}</div>
                                ))}
                            </div>
                        </div>
                    );
                }
            }

            return (
                <div className="readonly-item">
                    <label>{label}</label>
                    <span className="value-text">{value}</span>
                </div>
            );
        };

        const renderBoolField = (label: string, value: boolean | undefined) => (
            <div className="readonly-item">
                <label>{label}</label>
                <span>{value === true ? 'Yes' : value === false ? 'No' : 'Not provided'}</span>
            </div>
        );

        return (
            <div className="form-card readonly-section requirements-panel" style={readonlyCardStyle}>
                <div className="section-badge">
                    <span className="badge-readonly">👀 Read-only (Client fills via form)</span>
                </div>

                {/* Sales & Project Context */}
                {(project?.pmc_name || project?.location || project?.client_email_ids || project?.sales_user_id) && (
                    <div className="readonly-group project-context-group" style={{ marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid #e2e8f0' }}>
                        <h4 style={{ color: '#0ea5e9', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            🏢 Project Requirements
                        </h4>
                        <div className="requirements-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
                            {/* Manager if assigned */}
                            {project.manager_chk && (
                                <div className="readonly-item">
                                    <label>Assigned Manager</label>
                                    <span className="value-text">{project.manager_chk.name}</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Phase 1: Project Basics */}
                <div className="readonly-group">
                    <h4>1. Project Basics</h4>
                    <div className="requirements-grid">
                        {renderField('Project Summary', requirements.project_summary)}
                        {renderField('Project Notes', requirements.project_notes)}
                        {renderField('Phase', requirements.phase_number)}
                    </div>
                </div>

                {/* Phase 2: Brand & Visual Assets */}
                <div className="readonly-group">
                    <h4>2. Brand & Visual Assets</h4>

                    {/* Logo & Images */}
                    <div className="readonly-field" style={{ ...fieldStyle, marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>Company Logo</label>
                        {(onboardingData?.logo_url || onboardingData?.logo_file_path) ? (
                            <div className="logo-preview-card">
                                <img
                                    src={getAssetUrl(onboardingData?.logo_url || onboardingData?.logo_file_path)}
                                    alt="Company logo"
                                    className="logo-thumbnail"
                                    onClick={() => setPreviewImage(getAssetUrl(onboardingData?.logo_url || onboardingData?.logo_file_path))}
                                    title="Click to preview"
                                />
                                <div className="logo-actions">
                                    <button
                                        className="btn-download"
                                        onClick={(e) => handleDownload(e, getAssetUrl(onboardingData?.logo_url || onboardingData?.logo_file_path), 'logo.png')}
                                    >⬇ Download</button>
                                </div>
                            </div>
                        ) : <span className="empty">Not provided</span>}
                    </div>

                    {user?.role !== 'ADMIN' && (
                        <div className="readonly-field" style={{ ...fieldStyle, marginBottom: '16px' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>Website Images</label>
                            {getImageItems().length ? (
                                <div className="images-grid">
                                    {getImageItems().map((img) => (
                                        <div key={img.key} className="image-card">
                                            <div className="image-preview">
                                                <img src={img.url} alt={img.name} onClick={() => setPreviewImage(img.url)} />
                                            </div>
                                            <div className="image-info">
                                                <span className="image-name">{img.name}</span>
                                                <button
                                                    className="link-download"
                                                    onClick={(e) => handleDownload(e, img.url, img.name)}
                                                >⬇</button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : <span className="empty">Not provided</span>}
                        </div>
                    )}

                    {/* Copy Text */}
                    <div className="readonly-field full-width" style={{ ...fieldStyle, marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>Copy Text</label>
                        <span className={onboardingData?.copy_text || onboardingData?.use_custom_copy ? 'filled' : 'empty'}>
                            {getCopySummary()}
                        </span>
                    </div>

                    {/* Theme */}
                    <div className="readonly-field full-width" style={fieldStyle}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>Theme & Template</label>
                        <div className="theme-display-container" style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
                            {requirements.template_mode !== 'NEW' && onboardingData?.selected_template_id && (
                                <div className="theme-preview">
                                    {templates.find(t => t.id === onboardingData?.selected_template_id)?.preview_url ? (
                                        <img
                                            src={templates.find(t => t.id === onboardingData?.selected_template_id)?.preview_url}
                                            alt="Theme Preview"
                                            onClick={() => setPreviewImage(templates.find(t => t.id === onboardingData?.selected_template_id)?.preview_url || '')}
                                            style={{ cursor: 'pointer' }}
                                        />
                                    ) : <div className="theme-preview-placeholder">Preview Not Available</div>}
                                </div>
                            )}
                            <div className="theme-info">
                                <div className="info-row" style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
                                    <label style={{ fontWeight: 600, color: '#64748b', fontSize: '0.85rem', textTransform: 'uppercase' }}>Template Direction</label>
                                    <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#0f172a' }}>
                                        {requirements.template_mode === 'NEW' ? 'New Custom Design' : 'Clone from Validated Template'}
                                    </div>
                                </div>

                                {requirements.template_mode === 'NEW' ? (
                                    <div className="info-row" style={{ marginTop: '8px' }}>
                                        <label style={{ fontWeight: 600, color: '#64748b', fontSize: '0.85rem' }}>Selected Package / Details:</label>
                                        <span className={requirements.template_references ? 'filled' : 'empty'} style={{ whiteSpace: 'pre-wrap' }}>
                                            {(() => {
                                                let text = requirements.template_references || 'None';

                                                // Feature check for existing data
                                                if (text && !text.includes('Includes:')) {
                                                    if (text.includes('Essential')) text += '\nIncludes: Custom Homepage + 5 Inner Pages';
                                                    else if (text.includes('Professional')) text += '\nIncludes: Custom Homepage + 10 Inner Pages';
                                                    else if (text.includes('Enterprise')) text += '\nIncludes: Fully Custom UI/UX + Branding';
                                                }
                                                return text;
                                            })()}
                                        </span>
                                    </div>
                                ) : (
                                    <div className="info-row" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                        <label style={{ fontWeight: 600, color: '#64748b', fontSize: '0.85rem', textTransform: 'uppercase' }}>Selected Template</label>
                                        <div className="template-display" style={{ fontSize: '1.1rem', fontWeight: 600, color: '#0f172a' }}>
                                            {templates.find(t => t.id === onboardingData?.theme_preference || t.name === onboardingData?.theme_preference)?.name || onboardingData?.theme_preference || 'None'}
                                        </div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                                            (Client Preference)
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Phase 1: Project Basics */}

                {/* Phase 3: Design Preferences */}
                <div className="readonly-group">
                    <h4>3. Design Preferences</h4>
                    <div className="requirements-grid">
                        {renderBoolField('Brand Guidelines', requirements.brand_guidelines_available)}
                        {requirements.brand_guidelines_available === true && renderField('Guidelines Details', requirements.brand_guidelines_details)}

                        {renderField('Color Selection', requirements.color_selection)}
                        {['Color codes', 'Other'].includes(requirements.color_selection) && requirements.color_notes && renderField('Color Notes', requirements.color_notes)}

                        {renderField('Font Selection', requirements.font_selection)}
                        {requirements.font_selection === 'Other' && requirements.font_notes && renderField('Font Notes', requirements.font_notes)}

                        {renderBoolField('Custom Graphic Notes', requirements.custom_graphic_notes_enabled)}
                        {requirements.custom_graphic_notes_enabled === true && renderField('Graphic Details', requirements.custom_graphic_notes)}

                        {renderField('Navigation', requirements.navigation_notes_option)}
                        {requirements.navigation_notes_option === 'Custom' && renderField('Navigation names', requirements.navigation_notes)}
                    </div>
                </div>

                {/* Phase 4: Property Content */}
                <div className="readonly-group">
                    <h4>4. Property Content</h4>
                    <div className="requirements-grid">
                        {renderField('Stock Images Ref', requirements.stock_images_reference)}
                        {renderField('Floor Plan Images', requirements.floor_plan_images)}
                        {renderField('Sitemap', requirements.sitemap)}
                        {renderField('Virtual Tours', requirements.virtual_tours)}
                        {renderField('POI Categories', requirements.poi_categories)}
                        {renderBoolField('Specials Enabled', requirements.specials_enabled)}
                        {requirements.specials_enabled === true && renderField('Specials Details', requirements.specials_details)}
                        {requirements.copy_scope_notes && renderField('Copy Scope Notes', requirements.copy_scope_notes)}
                    </div>
                </div>

                {/* Phase 5: Compliance & Legal */}
                <div className="readonly-group">
                    <h4>5. Compliance & Legal</h4>

                    {/* WCAG */}
                    <div className="readonly-field" style={{ ...fieldStyle, marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>WCAG Accessibility</label>
                        <span className={onboardingData?.wcag_compliance_required ? 'filled' : 'empty'}>
                            {onboardingData?.wcag_compliance_required
                                ? `Required - Level ${onboardingData?.wcag_level || 'AA'}`
                                : 'Not required'}
                        </span>
                    </div>

                    {/* Privacy Policy */}
                    <div className="readonly-field full-width" style={fieldStyle}>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>Privacy Policy</label>
                        {onboardingData?.privacy_policy_text ? (
                            <textarea
                                className="privacy-policy-text"
                                readOnly
                                value={onboardingData.privacy_policy_text}
                            />
                        ) : onboardingData?.privacy_policy_url ? (
                            <div className="privacy-link-container">
                                <span className="filled">URL Provided: </span>
                                <a href={onboardingData.privacy_policy_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                    {onboardingData.privacy_policy_url}
                                </a>
                            </div>
                        ) : <span className="empty">Not provided</span>}
                    </div>
                </div>

                {/* Phase 6: Website Fundamentals */}
                <div className="readonly-group">
                    <h4>6. Website Fundamentals</h4>
                    <div className="requirements-grid">
                        {renderField('Pages', requirements.pages)}
                        {renderField('Domain Type', requirements.domain_type)}
                        {renderField('Vanity Domains', requirements.vanity_domains)}
                        {renderField('Call Tracking', requirements.call_tracking_plan)}
                    </div>
                </div>
            </div >
        );
    };

    const handleAcceptSuggestion = async (suggestion: AISuggestion, role: string) => {
        // Update the form with the suggested user
        const roleKey = role.toLowerCase() + '_user_id';
        setTeamFormData(prev => ({ ...prev, [roleKey]: suggestion.user_id }));

        // Record feedback
        try {
            await capacityAPI.recordFeedback(suggestion.id, {
                was_accepted: true,
                actual_outcome: 'accepted_suggestion'
            });
            setSuccess(`${suggestion.user_name} selected as ${role}`);
        } catch (err) {
            console.error('Error recording feedback:', err);
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
            return dataRes.data;
        } catch (error) {
            console.error('Failed to load onboarding data:', error);
            return null;
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
        setSelectedEmailContacts([]);
    };

    const removeContact = async (index: number) => {
        if (!onboardingData) return;
        const updatedContacts = onboardingData.contacts_json.filter((_, i) => i !== index);
        await saveOnboardingData({ contacts_json: updatedContacts });
        setSelectedEmailContacts([]);
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

    // Test Phase Handlers
    const handleCreateScenario = async () => {
        if (!newScenario.name.trim()) return;

        try {
            await testingAPI.createScenario(projectId, newScenario);
            setSuccess('Test scenario created successfully');
            setNewScenario({ name: '', description: '' });
            setShowCreateScenarioModal(false);
            await loadTestPhaseData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create test scenario');
        }
    };

    const handleGenerateScenario = async (scenarioName: string) => {
        try {
            setTestLoading(true);
            await testingAPI.generateScenario(projectId, scenarioName);
            setSuccess('Test scenario generated with AI-based test cases');
            await loadTestPhaseData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to generate test scenario');
        } finally {
            setTestLoading(false);
        }
    };

    const handleCreateTestCase = async () => {
        if (!selectedScenario || !newTestCase.title.trim()) return;

        try {
            await testingAPI.createTestCase(selectedScenario.id, newTestCase);
            setSuccess('Test case created successfully');
            setNewTestCase({ title: '', description: '', steps: '', expected_result: '' });
            setShowCreateTestCaseModal(false);
            await loadTestPhaseData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create test case');
        }
    };

    const handleRunExecution = async () => {
        if (!executionName.trim()) return;

        try {
            setTestLoading(true);
            await testingAPI.runExecution(projectId, executionName);
            setSuccess('Test execution started. Results will be available shortly.');
            setExecutionName('');
            setShowRunExecutionModal(false);
            await loadTestPhaseData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to run test execution');
        } finally {
            setTestLoading(false);
        }
    };

    const handleViewExecutionResults = async (execution: TestExecution) => {
        setSelectedExecution(execution);
        await loadTestResults(execution.id);
    };

    const handleReassignDefect = async () => {
        if (!selectedDefect || !reassignData.new_assignee_id) return;

        try {
            await testingAPI.reassignDefect(selectedDefect.id, reassignData);
            setSuccess('Defect reassigned successfully');
            setReassignData({ new_assignee_id: '', reason: '' });
            setShowReassignDefectModal(false);
            setSelectedDefect(null);
            await loadTestPhaseData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to reassign defect');
        }
    };

    const handleMarkDefectFixed = async () => {
        if (!selectedDefect || !fixDescription.trim()) return;

        try {
            await testingAPI.markDefectFixed(selectedDefect.id, { fix_description: fixDescription });
            setSuccess('Defect marked as fixed');
            setFixDescription('');
            setShowFixDefectModal(false);
            setSelectedDefect(null);
            await loadTestPhaseData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to mark defect as fixed');
        }
    };

    const handleValidateDefect = async (defectId: string) => {
        try {
            await testingAPI.validateDefect(defectId);
            setSuccess('Defect validated and closed');
            await loadTestPhaseData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to validate defect');
        }
    };

    const handleValidateAllDefects = async () => {
        try {
            setTestLoading(true);
            await testingAPI.validateAllDefects(projectId);
            setSuccess('All fixed defects have been validated');
            await loadTestPhaseData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to validate defects');
        } finally {
            setTestLoading(false);
        }
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'CRITICAL': return 'var(--color-error)';
            case 'HIGH': return '#dc2626';
            case 'MEDIUM': return 'var(--color-warning)';
            case 'LOW': return 'var(--color-info)';
            default: return 'var(--text-muted)';
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'OPEN': return 'var(--color-error)';
            case 'IN_PROGRESS': return 'var(--color-warning)';
            case 'FIXED': return 'var(--color-info)';
            case 'VERIFIED':
            case 'CLOSED': return 'var(--color-success)';
            case 'REOPENED': return '#dc2626';
            default: return 'var(--text-muted)';
        }
    };

    const handleAssignTeam = async () => {
        setAssigningTeam(true);
        setError('');

        try {
            const assignmentData: any = {};
            if (teamFormData.pc_user_id) assignmentData.pc_user_id = teamFormData.pc_user_id;
            if (teamFormData.consultant_user_id) assignmentData.consultant_user_id = teamFormData.consultant_user_id;
            if (teamFormData.builder_user_id) assignmentData.builder_user_id = teamFormData.builder_user_id;
            if (teamFormData.tester_user_id) assignmentData.tester_user_id = teamFormData.tester_user_id;

            await projectsAPI.assignTeam(projectId, assignmentData);
            setSuccess('Team assigned successfully');
            setShowTeamModal(false);
            await loadTeamData();
            await loadAllData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to assign team');
        } finally {
            setAssigningTeam(false);
        }
    };

    // Team visibility: Only Admin, Manager, and PC can see team assignments
    const canViewTeam = user?.role === 'ADMIN' || user?.role === 'MANAGER' || user?.role === 'PC';

    // Assignment permissions based on role
    const canAssignConsultant = user?.role === 'ADMIN' || user?.role === 'MANAGER';
    const canAssignPC = user?.role === 'ADMIN' || user?.role === 'MANAGER';
    const canAssignBuilder = user?.role === 'ADMIN' || user?.role === 'MANAGER' || (user?.role === 'PC' && user?.region === 'INDIA');
    const canAssignTester = user?.role === 'ADMIN' || user?.role === 'MANAGER' || (user?.role === 'PC' && user?.region === 'INDIA');
    const canAssignTeam = canAssignConsultant || canAssignPC || canAssignBuilder || canAssignTester;

    if (loading) {
        return (
            <div className="page-wrapper">
                <Navigation />
                <div className="loading-screen">
                    <div className="spinner" />
                    <p>Loading project...</p>
                </div>

            </div>
        );
    }

    if (!project || !user) return null;

    console.log('Current User Role:', user.role);
    console.log('Is Admin?', user.role === 'ADMIN');

    return (
        <div className="page-wrapper">
            <Navigation />
            <main className="project-detail">
                {/* Back Button */}
                <button className="btn-back" onClick={() => router.push('/projects')}>
                    ← Back to Projects
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

                    {/* Draft Actions */}
                    {project.status === 'DRAFT' && (
                        <div className="header-actions" style={{ marginLeft: 'auto', marginRight: '24px', display: 'flex', gap: '12px' }}>
                            <button
                                onClick={() => router.push(`/projects/create?edit=${projectId}`)}
                                style={{
                                    background: 'white',
                                    color: '#475569',
                                    border: '1px solid #cbd5e1',
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    cursor: 'pointer',
                                    fontWeight: 500
                                }}
                            >
                                <span>✏️</span> Edit Project
                            </button>
                            <button
                                onClick={async () => {
                                    if (!confirm('Move project to Onboarding stage? This will activate the project.')) return;
                                    try {
                                        setLoading(true);
                                        await projectsAPI.update(projectId, { status: 'ACTIVE', current_stage: 'ONBOARDING' });
                                        await loadAllData();
                                    } catch (e) {
                                        console.error(e);
                                        alert('Failed to activate project');
                                        setLoading(false);
                                    }
                                }}
                                style={{
                                    background: '#10b981',
                                    color: 'white',
                                    border: 'none',
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    cursor: 'pointer',
                                    fontWeight: 500,
                                    boxShadow: '0 2px 4px rgba(16, 185, 129, 0.2)'
                                }}
                            >
                                <span>🚀</span> Move to Onboarding
                            </button>
                        </div>
                    )}

                    {isProjectOwner && project.status !== 'DRAFT' && (
                        <div className="header-actions" style={{ marginLeft: 'auto', marginRight: '24px' }}>
                            <button
                                onClick={handleViewChatLogs}
                                style={{
                                    background: '#3b82f6',
                                    color: 'white',
                                    border: 'none',
                                    padding: '8px 16px',
                                    borderRadius: '8px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    cursor: 'pointer',
                                    fontWeight: 500,
                                    boxShadow: '0 2px 4px rgba(59, 130, 246, 0.2)'
                                }}
                            >
                                <span>💬</span> View Client Chat
                            </button>
                        </div>
                    )}
                    {project && (
                        <div className="completion-badge">
                            <div className="completion-ring">
                                <svg viewBox="0 0 36 36">
                                    <path className="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                    <path
                                        className="ring-fill"
                                        strokeDasharray={`${project.completion_percentage || 0}, 100`}
                                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                    />
                                </svg>
                                <span className="ring-value">{project.completion_percentage || 0}%</span>
                            </div>
                            <span className="completion-label">Complete</span>
                        </div>
                    )}
                </header>

                {/* Sales Information Section - Only show for SALES stage */}
                {project.current_stage === 'SALES' && (
                    <div className="sales-info-section" style={{
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        padding: '24px',
                        borderRadius: '12px',
                        marginBottom: '24px',
                        color: 'white',
                        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
                    }}>
                        <h2 style={{ margin: '0 0 20px 0', fontSize: '20px', fontWeight: 600 }}>
                            🤝 Sales Handover Information
                        </h2>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
                            <div style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '16px', borderRadius: '8px' }}>
                                <div style={{ fontSize: '12px', opacity: 0.9, marginBottom: '4px' }}>PMC Name</div>
                                <div style={{ fontSize: '16px', fontWeight: 500 }}>{project.pmc_name || 'Not specified'}</div>
                            </div>
                            <div style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '16px', borderRadius: '8px' }}>
                                <div style={{ fontSize: '12px', opacity: 0.9, marginBottom: '4px' }}>Location</div>
                                <div style={{ fontSize: '16px', fontWeight: 500 }}>{project.location || 'Not specified'}</div>
                            </div>
                            <div style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '16px', borderRadius: '8px' }}>
                                <div style={{ fontSize: '12px', opacity: 0.9, marginBottom: '4px' }}>Client Email IDs</div>
                                <div style={{ fontSize: '14px', fontWeight: 500, wordBreak: 'break-word' }}>
                                    {project.client_email_ids || 'Not specified'}
                                </div>
                            </div>
                            <div style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '16px', borderRadius: '8px' }}>
                                <div style={{ fontSize: '12px', opacity: 0.9, marginBottom: '4px' }}>Project Type</div>
                                <div style={{ fontSize: '16px', fontWeight: 500 }}>
                                    {project.project_type || 'Full Website'}
                                </div>
                            </div>
                            {project.description && (
                                <div style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '16px', borderRadius: '8px', gridColumn: '1 / -1' }}>
                                    <div style={{ fontSize: '12px', opacity: 0.9, marginBottom: '4px' }}>Description</div>
                                    <div style={{ fontSize: '14px', lineHeight: '1.6' }}>{project.description}</div>
                                </div>
                            )}
                        </div>
                        {/* Manager info removed as per request */}
                    </div>
                )}

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
                {showUpdateNotice && onboardingData?.updated_at && (
                    <div className="alert alert-info">
                        <div className="alert-content">
                            <strong>Client updates received.</strong>
                            <span>Updated on {new Date(onboardingData.updated_at).toLocaleString()}</span>
                        </div>
                        <button
                            className="btn-dismiss"
                            onClick={() => {
                                localStorage.setItem(`onboarding_seen_${projectId}`, onboardingData.updated_at || new Date().toISOString());
                                setShowUpdateNotice(false);
                            }}
                        >
                            Mark as read
                        </button>
                    </div>
                )}

                {/* My Capacity on this Project - Visible to all assigned team members */}
                {isAssignedToProject && (
                    <div className="my-capacity-section">
                        <h2>📊 My Capacity on this Project</h2>
                        <div className="capacity-cards">
                            <div className="capacity-card">
                                <div className="capacity-icon">🎯</div>
                                <div className="capacity-info">
                                    <span className="capacity-label">This Project</span>
                                    <span className="capacity-value">{projectWorkload?.by_role?.[user?.role] || 0}h estimated</span>
                                </div>
                            </div>
                            <div className="capacity-card">
                                <div className="capacity-icon">📋</div>
                                <div className="capacity-info">
                                    <span className="capacity-label">Other Projects</span>
                                    <span className="capacity-value">
                                        {capacityByRole[user?.role || '']?.find((c: any) => c.user_id === user?.id)?.allocated_hours || 0}h allocated
                                    </span>
                                </div>
                            </div>
                            <div className="capacity-card available">
                                <div className="capacity-icon">✅</div>
                                <div className="capacity-info">
                                    <span className="capacity-label">Available</span>
                                    <span className="capacity-value">
                                        {capacityByRole[user?.role || '']?.find((c: any) => c.user_id === user?.id)?.remaining_hours?.toFixed(1) || 0}h remaining
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Consultant Onboarding Actions (New 2-Step Logic) */}
                {user?.role === 'CONSULTANT' && isAssignedToProject && project.current_stage === 'ONBOARDING' && onboardingData && (
                    <div className="consultant-actions-section">
                        <h2>Client Onboarding</h2>
                        <div className="onboarding-actions-container">

                            {/* Step 1: Add Clients (Contacts) */}
                            <div className="onboarding-step-card">
                                <span className="step-label">Step 1</span>
                                <div className="step-header">
                                    <h3>Add Clients</h3>
                                </div>
                                <div className="step-content">
                                    <div className="contacts-list-compact">
                                        {onboardingData.contacts_json?.length === 0 ? (
                                            <p className="empty-message">No contacts added yet.</p>
                                        ) : (
                                            onboardingData.contacts_json?.map((contact: any, index: number) => (
                                                <div key={index} className="contact-item-compact">
                                                    <div className="contact-info">
                                                        <span className="contact-name">{contact.name}</span>
                                                        <span className="contact-email-sm">{contact.email}</span>
                                                    </div>
                                                    <button className="btn-icon-remove" onClick={() => removeContact(index)}>×</button>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                    <button className="btn-add-sm full-width" onClick={() => setShowContactModal(true)}>+ Add Contact</button>
                                </div>
                            </div>

                            {/* Step 2: Invite Client */}
                            <div className={`onboarding-step-card ${onboardingData.contacts_json?.length > 0 ? 'active' : ''}`}>
                                <span className="step-label">Step 2</span>
                                <div className="step-header">
                                    <h3>Invite Client</h3>
                                </div>
                                <div className="step-content">
                                    <div className="invite-section">
                                        {/* Copy Link */}
                                        <div className="invite-share-box">
                                            {completionStatus?.client_form_url ? (
                                                <button
                                                    className="btn-copy-link full-width"
                                                    onClick={() => {
                                                        navigator.clipboard.writeText(`${window.location.origin}${completionStatus.client_form_url}`);
                                                        setSuccess('Link copied!');
                                                        setTimeout(() => setSuccess(''), 2000);
                                                    }}
                                                >
                                                    🔗 Copy Onboarding Link
                                                </button>
                                            ) : <p>Link not ready</p>}
                                        </div>

                                        {/* Auto Reminder Toggle */}
                                        {/* Auto Reminder Toggle & Settings */}
                                        <div className="auto-reminder-section" style={{ marginTop: '16px', padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                                            <div className="flex-between" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                                <div>
                                                    <span style={{ fontWeight: 600, fontSize: '14px', color: '#334155' }}>Auto-Reminders</span>
                                                    <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>Automatically nudge client every {reminderInterval} hours</p>
                                                </div>
                                                <div className="toggle-wrapper" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                    <span style={{ fontSize: '12px', fontWeight: 500, color: onboardingData.auto_reminder_enabled ? '#10b981' : '#94a3b8' }}>
                                                        {onboardingData.auto_reminder_enabled ? 'Enabled' : 'Disabled'}
                                                    </span>
                                                    <label className="switch">
                                                        <input
                                                            type="checkbox"
                                                            checked={onboardingData.auto_reminder_enabled}
                                                            onChange={(e) => {
                                                                onboardingAPI.toggleAutoReminder(projectId, e.target.checked, reminderInterval)
                                                                    .then(() => loadOnboardingData())
                                                                    .catch(() => setError('Failed to update'));
                                                            }}
                                                        />
                                                        <span className="slider round"></span>
                                                    </label>
                                                </div>
                                            </div>

                                            {onboardingData.auto_reminder_enabled && (
                                                <div className="interval-selector" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                                    <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Reminder Frequency</label>
                                                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                                        {[6, 12, 24].map(hours => (
                                                            <button
                                                                key={hours}
                                                                className={`btn-chip ${reminderInterval === hours && !showCustomInterval ? 'active' : ''}`}
                                                                onClick={() => {
                                                                    setReminderInterval(hours);
                                                                    setShowCustomInterval(false);
                                                                    onboardingAPI.toggleAutoReminder(projectId, true, hours)
                                                                        .then(() => loadOnboardingData());
                                                                }}
                                                                style={{
                                                                    padding: '6px 12px', borderRadius: '16px', border: '1px solid',
                                                                    borderColor: reminderInterval === hours && !showCustomInterval ? '#2563eb' : '#cbd5e1',
                                                                    background: reminderInterval === hours && !showCustomInterval ? '#eff6ff' : 'white',
                                                                    color: reminderInterval === hours && !showCustomInterval ? '#1e40af' : '#64748b',
                                                                    fontSize: '12px', cursor: 'pointer'
                                                                }}
                                                            >
                                                                Every {hours}h
                                                            </button>
                                                        ))}
                                                        <button
                                                            className={`btn-chip ${showCustomInterval ? 'active' : ''}`}
                                                            onClick={() => setShowCustomInterval(true)}
                                                            style={{
                                                                padding: '6px 12px', borderRadius: '16px', border: '1px solid',
                                                                borderColor: showCustomInterval ? '#2563eb' : '#cbd5e1',
                                                                background: showCustomInterval ? '#eff6ff' : 'white',
                                                                color: showCustomInterval ? '#1e40af' : '#64748b',
                                                                fontSize: '12px', cursor: 'pointer'
                                                            }}
                                                        >
                                                            Custom
                                                        </button>
                                                    </div>

                                                    {showCustomInterval && (
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                                                            <input
                                                                type="number"
                                                                min="1"
                                                                value={reminderInterval}
                                                                onChange={(e) => setReminderInterval(parseInt(e.target.value) || 24)}
                                                                onBlur={() => onboardingAPI.toggleAutoReminder(projectId, true, reminderInterval).then(() => loadOnboardingData())}
                                                                style={{ width: '80px', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                                                            />
                                                            <span style={{ fontSize: '13px', color: '#64748b' }}>hours</span>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>

                                        {/* Send Reminder - Only if Auto-Reminder is OFF */}
                                        {!onboardingData.auto_reminder_enabled && (
                                            <button
                                                className="btn-send-email-sm"
                                                disabled={sendingEmail || !onboardingData.contacts_json?.length}
                                                onClick={async () => {
                                                    setSendingEmail(true);
                                                    try {
                                                        const primary = onboardingData.contacts_json?.find((c: any) => c.is_primary) || onboardingData.contacts_json?.[0];
                                                        if (primary) {
                                                            await onboardingAPI.sendReminder(projectId, {
                                                                recipient_email: primary.email,
                                                                recipient_name: primary.name,
                                                                message: `Please complete the onboarding form.`
                                                            });
                                                            setSuccess('Reminder sent!');
                                                        } else {
                                                            setError('No contacts to send to');
                                                        }
                                                    } catch { setError('Failed to send'); }
                                                    finally { setSendingEmail(false); }
                                                }}
                                            >
                                                {sendingEmail ? 'Sending...' : '📧 Send Manual Reminder'}
                                            </button>
                                        )}
                                        {onboardingData.auto_reminder_enabled && (
                                            <p className="description-text sm">Manual reminders disabled when auto-reminders are on.</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Phase Summary - Admin/Manager */}
                {user?.role && ['ADMIN', 'MANAGER'].includes(user.role) && phaseSummaries.length > 0 && (
                    <div className="phase-summary-section">
                        <div className="section-header">
                            <h2>📌 Phase Task Summary</h2>
                            {healthSummary && (
                                <span className={`health-pill health-${healthSummary.status?.toLowerCase()}`}>
                                    {healthSummary.status.replace('_', ' ')}
                                </span>
                            )}
                        </div>
                        {healthSummary && (
                            <div className="health-details">
                                <div>Days in stage: {healthSummary.days_in_stage}</div>
                                <div>SLA days: {healthSummary.sla_days}</div>
                                <div>Remaining: {healthSummary.remaining_days} days</div>
                            </div>
                        )}
                        <div className="phase-table">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Phase</th>
                                        <th>Completed</th>
                                        <th>Pending</th>
                                        <th>Total</th>
                                        <th>Completion</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {phaseSummaries.map((phase) => (
                                        <tr key={phase.stage}>
                                            <td className="cell-title">{phase.stage.replace('_', ' ')}</td>
                                            <td>{phase.completed_tasks}</td>
                                            <td>{phase.pending_tasks}</td>
                                            <td>{phase.total_tasks}</td>
                                            <td>{phase.completion_percentage}%</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Executive Summary for Admin */}
                {isExecutiveView && (
                    <div className="executive-summary">
                        <h2>📈 Executive Summary</h2>
                        <div className="summary-grid">
                            <div className="summary-card">
                                <span className="summary-icon">📊</span>
                                <div className="summary-content">
                                    <span className="summary-label">Progress</span>
                                    <span className="summary-value">{completionStatus?.completion_percentage || 0}%</span>
                                </div>
                            </div>
                            <div className="summary-card">
                                <span className="summary-icon">📋</span>
                                <div className="summary-content">
                                    <span className="summary-label">Tasks</span>
                                    <span className="summary-value">{completionStatus?.completed_tasks || 0}/{completionStatus?.total_required_tasks || 0}</span>
                                </div>
                            </div>
                            <div className="summary-card">
                                <span className="summary-icon">🎯</span>
                                <div className="summary-content">
                                    <span className="summary-label">Stage</span>
                                    <span className="summary-value">{project.current_stage?.replace('_', ' ')}</span>
                                </div>
                            </div>
                            <div className="summary-card">
                                <span className="summary-icon">⚡</span>
                                <div className="summary-content">
                                    <span className="summary-label">Status</span>
                                    <span className="summary-value">{project.status}</span>
                                </div>
                            </div>
                        </div>
                        <div className="executive-note">
                            <p>💡 As an executive, you see the high-level overview. Detailed operational data is managed by Consultants and Managers.</p>
                        </div>
                    </div>
                )}

                {/* Team Assignment Section - Only visible to Admin, Manager, and PC */}
                {canViewTeam && (
                    <div className="team-section">
                        <div className="section-header">
                            <h2>👥 Team Assignment</h2>
                            {canAssignTeam && (
                                <button className="btn-add" onClick={() => setShowTeamModal(true)}>
                                    ✏️ Manage Team
                                </button>
                            )}
                            {user?.role === 'MANAGER' && user?.region && (
                                <span className="region-badge">Region: {user.region}</span>
                            )}
                        </div>
                        <div className="team-grid">
                            {project.require_manual_review && (
                                <div className={`team-card ${teamAssignments.consultant ? 'assigned' : 'unassigned'}`}>
                                    <div className="team-role-icon">💼</div>
                                    <div className="team-role-label">Consultant</div>
                                    {teamAssignments.consultant ? (
                                        <div className="team-member-info">
                                            <span className="member-name">{teamAssignments.consultant.name}</span>
                                            <span className="member-email">{teamAssignments.consultant.email}</span>
                                        </div>
                                    ) : (
                                        <div className="unassigned-label">Not assigned</div>
                                    )}
                                </div>
                            )}
                            <div className={`team-card ${teamAssignments.pc ? 'assigned' : 'unassigned'}`}>
                                <div className="team-role-icon">🎯</div>
                                <div className="team-role-label">Project Coordinator (PC)</div>
                                {teamAssignments.pc ? (
                                    <div className="team-member-info">
                                        <span className="member-name">{teamAssignments.pc.name}</span>
                                        <span className="member-email">{teamAssignments.pc.email}</span>
                                    </div>
                                ) : (
                                    <div className="unassigned-label">Not assigned</div>
                                )}
                            </div>
                            <div className={`team-card ${teamAssignments.builder ? 'assigned' : 'unassigned'}`}>
                                <div className="team-role-icon">🔨</div>
                                <div className="team-role-label">Builder</div>
                                {teamAssignments.builder ? (
                                    <div className="team-member-info">
                                        <span className="member-name">{teamAssignments.builder.name}</span>
                                        <span className="member-email">{teamAssignments.builder.email}</span>
                                    </div>
                                ) : (
                                    <div className="unassigned-label">Not assigned</div>
                                )}
                            </div>
                            <div className={`team-card ${teamAssignments.tester ? 'assigned' : 'unassigned'}`}>
                                <div className="team-role-icon">🧪</div>
                                <div className="team-role-label">Tester</div>
                                {teamAssignments.tester ? (
                                    <div className="team-member-info">
                                        <span className="member-name">{teamAssignments.tester.name}</span>
                                        <span className="member-email">{teamAssignments.tester.email}</span>
                                    </div>
                                ) : (
                                    <div className="unassigned-label">Not assigned</div>
                                )}
                            </div>
                        </div>
                        {!teamAssignments.pc && !teamAssignments.consultant && !teamAssignments.builder && !teamAssignments.tester && (
                            <div className="team-empty-message">
                                <p>No team members assigned yet.</p>
                                {canAssignTeam && <p>Click "Manage Team" to assign team members to this project.</p>}
                            </div>
                        )}
                    </div>
                )}



                {/* Onboarding Section - Unified View for All Roles */}
                {project.current_stage === 'ONBOARDING' && project.current_stage !== 'SALES' && onboardingData && (
                    <div className="onboarding-section">
                        {console.log('Project Page Debug - User Role:', user?.role, 'Is Admin:', isAdmin, 'Matches:', ['ADMIN', 'MANAGER'].includes(user?.role || ''))}
                        <div className="section-header">
                            <h2>📋 {['ADMIN', 'MANAGER'].includes(user?.role || '') ? 'Project Requirement Progress' : 'Project Onboarding Details'}  <span style={{ fontSize: '10px', color: '#ccc' }}>(v2.1)</span></h2>
                            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                                {(isAdmin || user?.role === 'MANAGER') && (
                                    <div className={`hitl-banner ${project.require_manual_review ? 'hitl-on' : 'hitl-off'}`} style={{
                                        display: 'flex', alignItems: 'center', gap: '16px', padding: '12px 20px',
                                        borderRadius: '12px', border: '1px solid',
                                        background: project.require_manual_review ? '#fef2f2' : '#f0fdf4',
                                        borderColor: project.require_manual_review ? '#fecaca' : '#bbf7d0',
                                        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                                        flex: 1
                                    }}>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                                <span style={{ fontSize: '18px' }}>{project.require_manual_review ? '👤' : '🤖'}</span>
                                                <span style={{ fontWeight: 700, fontSize: '14px', color: project.require_manual_review ? '#991b1b' : '#166534' }}>
                                                    {project.require_manual_review ? 'Manual Review Enabled (HITL)' : 'Onboarder AI Agent Active'}
                                                </span>
                                            </div>
                                            <p style={{ margin: 0, fontSize: '12px', color: project.require_manual_review ? '#b91c1c' : '#15803d', lineHeight: '1.4' }}>
                                                {project.require_manual_review
                                                    ? 'A Consultant must manually review and approve all client data before the project advances.'
                                                    : 'The AI Agent automatically sends reminders every 24hrs and will advance the project once all data is verified.'}
                                            </p>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '16px', borderLeft: '1px solid', borderColor: project.require_manual_review ? '#fecaca' : '#bbf7d0' }}>
                                            <span style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Toggle Mode:</span>
                                            <label className="switch">
                                                <input
                                                    type="checkbox"
                                                    checked={project.require_manual_review}
                                                    onChange={async (e) => {
                                                        try {
                                                            await projectsAPI.toggleHITL(projectId, e.target.checked);
                                                            setSuccess(`Mode switched to ${e.target.checked ? 'Manual Review' : 'AI Agent'}`);
                                                            await loadAllData();
                                                        } catch (err) {
                                                            setError('Failed to toggle review mode');
                                                        }
                                                    }}
                                                />
                                                <span className="slider round"></span>
                                            </label>
                                        </div>
                                    </div>
                                )}
                                {project.require_manual_review && (user?.role === 'CONSULTANT' || user?.role === 'PC' || user?.role === 'ADMIN' || user?.role === 'MANAGER') && (
                                    <button
                                        className="btn-send-reminder-now"
                                        onClick={async () => {
                                            try {
                                                await onboardingAPI.sendManualReminder(projectId as string);
                                                setSuccess('Manual reminder sent to client');
                                                setTimeout(() => setSuccess(''), 3000);
                                            } catch (err) {
                                                console.error('Failed to send reminder', err);
                                                setError('Failed to send reminder');
                                            }
                                        }}
                                        style={{
                                            padding: '8px 16px', background: '#3b82f6', color: 'white', border: 'none',
                                        }}
                                    >
                                        🔔 Send Reminder Now
                                    </button>
                                )}



                            </div>
                        </div>

                        {/* Project Information Summary (Shared by Sales) */}
                        <div className="project-summary-box" style={{ background: '#f8fafc', padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0', marginBottom: '24px' }}>
                            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 600, color: '#1e293b' }}>Project Information Summary</h3>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
                                <div className="summary-field">
                                    <label style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Client Name</label>
                                    <div style={{ fontSize: '14px', fontWeight: 500 }}>{project.client_name || '—'}</div>
                                </div>
                                <div className="summary-field">
                                    <label style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>PMC Name</label>
                                    <div style={{ fontSize: '14px', fontWeight: 500 }}>{project.pmc_name || '—'}</div>
                                </div>
                                <div className="summary-field">
                                    <label style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Location</label>
                                    <div style={{ fontSize: '14px', fontWeight: 500 }}>{project.location || '—'}</div>
                                </div>
                                <div className="summary-field" style={{ minWidth: 0 }}>
                                    <label style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Client Emails</label>
                                    <div style={{ fontSize: '14px', fontWeight: 500, wordBreak: 'break-all' }}>{project.client_email_ids || '—'}</div>
                                </div>
                                <div className="summary-field">
                                    <label style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Priority</label>
                                    <div style={{ fontSize: '14px', fontWeight: 500 }}>{project.priority}</div>
                                </div>
                                {project.sales_rep && (
                                    <div className="summary-field" style={{ minWidth: 0 }}>
                                        <label style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Sales Rep</label>
                                        <div style={{ fontSize: '14px', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={project.sales_rep.name}>{project.sales_rep.name}</div>
                                    </div>
                                )}
                                {project.description && (
                                    <div className="summary-field" style={{ gridColumn: '1 / -1' }}>
                                        <label style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Description</label>
                                        <div style={{ fontSize: '14px', lineHeight: '1.5' }}>{project.description}</div>
                                    </div>
                                )}
                                <div className="summary-field">
                                    <label style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Client Notification</label>
                                    <div style={{ fontSize: '14px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        {onboardingData?.review_status === 'NEEDS_CHANGES' ? (
                                            <><span style={{ color: '#ef4444' }}>❌</span> Failed (Missing Info)</>
                                        ) : onboardingData?.review_status === 'PENDING' || onboardingData?.review_status === 'APPROVED' ? (
                                            <><span style={{ color: '#10b981' }}>✅</span> Sent</>
                                        ) : (
                                            <><span style={{ color: '#f59e0b' }}>⏳</span> Pending</>
                                        )}

                                        {/* Manual Resend Button */}
                                        {(onboardingData?.review_status === 'PENDING' || onboardingData?.review_status === 'APPROVED') && (
                                            <button
                                                onClick={async () => {
                                                    try {
                                                        const btn = document.getElementById('resend-btn');
                                                        if (btn) btn.innerText = 'Sending...';
                                                        const response = await onboardingAPI.sendManualReminder(projectId);
                                                        // Show actual message from backend
                                                        console.log(response.data.message || 'Notification resent successfully!');
                                                    } catch (err: any) {
                                                        const errMsg = err.response?.data?.detail || err.response?.data?.message || err.message;
                                                        alert('Failed to resend notification. ' + errMsg);
                                                        console.error(err);
                                                    } finally {
                                                        const btn = document.getElementById('resend-btn');
                                                        if (btn) btn.innerText = '↺ Resend';
                                                    }
                                                }}
                                                id="resend-btn"
                                                style={{
                                                    fontSize: '11px', padding: '2px 8px', borderRadius: '4px',
                                                    border: '1px solid #cbd5e1', background: 'white', cursor: 'pointer',
                                                    color: '#64748b'
                                                }}
                                                title="Resend email notification"
                                            >
                                                ↺ Resend
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Onboarder Agent Analysis - Moved to Top */}


                        {/* Requirements Summary Dashboard - Visible to Everyone */}
                        <div className="summary-card">
                            <div className="summary-header-row">
                                <h3>Onboarding Checklist</h3>
                                <div className="linear-progress-wrapper">
                                    <div className="progress-text">
                                        <span className="progress-label">{getAllOnboardingItems().filter(i => i.filled).length} of {getAllOnboardingItems().length} Items Provided</span>
                                        <span className="progress-percent">({Math.round((getAllOnboardingItems().filter(i => i.filled).length / getAllOnboardingItems().length) * 100) || 0}%)</span>
                                    </div>
                                    <div className="progress-bar-bg">
                                        <div className="progress-bar-fill" style={{ width: `${Math.round((getAllOnboardingItems().filter(i => i.filled).length / getAllOnboardingItems().length) * 100) || 0}%` }}></div>
                                    </div>
                                </div>
                            </div>

                            <div className="checklist-compact-grid">
                                {/* Essential Items */}
                                <div className={`checklist-compact-item ${onboardingData.contacts_json?.some((c: any) => c.is_primary) ? 'provided' : 'pending'}`}>
                                    <span className="checklist-compact-icon">{onboardingData.contacts_json?.some((c: any) => c.is_primary) ? '✅' : '❌'}</span>
                                    <span className="checklist-label">Primary Contact</span>
                                </div>

                                <div className={`checklist-compact-item ${onboardingData.logo_url || onboardingData.logo_file_path ? 'provided' : 'pending'}`}>
                                    <span className="checklist-compact-icon">{onboardingData.logo_url || onboardingData.logo_file_path ? '✅' : '❌'}</span>
                                    <span className="checklist-label">Company Logo</span>
                                </div>

                                <div className={`checklist-compact-item ${(onboardingData.images_json?.length || 0) > 0 ? 'provided' : 'pending'}`}>
                                    <span className="checklist-compact-icon">{(onboardingData.images_json?.length || 0) > 0 ? '✅' : '❌'}</span>
                                    <span className="checklist-label">Website Images</span>
                                </div>

                                <div className={`checklist-compact-item ${onboardingData.copy_text || onboardingData.use_custom_copy ? 'provided' : 'pending'}`}>
                                    <span className="checklist-compact-icon">{onboardingData.copy_text || onboardingData.use_custom_copy ? '✅' : '❌'}</span>
                                    <span className="checklist-label">Copy Text</span>
                                </div>

                                <div className={`checklist-compact-item ${onboardingData.wcag_confirmed ? 'provided' : 'pending'}`}>
                                    <span className="checklist-compact-icon">{onboardingData.wcag_confirmed ? '✅' : '❌'}</span>
                                    <span className="checklist-label">WCAG Requirements</span>
                                </div>

                                <div className={`checklist-compact-item ${onboardingData.privacy_policy_url || onboardingData.privacy_policy_text ? 'provided' : 'pending'}`}>
                                    <span className="checklist-compact-icon">{onboardingData.privacy_policy_url || onboardingData.privacy_policy_text ? '✅' : '❌'}</span>
                                    <span className="checklist-label">Privacy Policy</span>
                                </div>

                                <div className={`checklist-compact-item ${onboardingData.theme_preference || onboardingData.selected_template_id ? 'provided' : 'pending'}`}>
                                    <span className="checklist-compact-icon">{onboardingData.theme_preference || onboardingData.selected_template_id ? '✅' : '❌'}</span>
                                    <span className="checklist-label">Theme / Template</span>
                                </div>

                                {/* Detailed Requirements */}
                                {getRequirementsChecklistItems().map((item) => (
                                    <div key={item.label} className={`checklist-compact-item ${item.filled ? 'provided' : 'pending'}`}>
                                        <span className="checklist-compact-icon">{item.filled ? '✅' : '❌'}</span>
                                        <span className="checklist-label">{item.label}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Read-Only Details for Managers/Admins/Others */}
                        {(user?.role !== 'CONSULTANT' || !isAssignedToProject) && user?.role !== 'ADMIN' && (
                            <div className="onboarding-readonly-view">
                                {renderReadonlyOnboardingDetails()}
                            </div>
                        )}

                        {/* Restored Details for Consultant (Edit View is done via actions, this is reference) */}
                        {user?.role === 'CONSULTANT' && isAssignedToProject && (
                            <div className="restored-details-section">
                                <h3>Onboarding Details</h3>
                                {renderReadonlyOnboardingDetails()}
                            </div>
                        )}

                    </div>
                )}

                {project.current_stage !== 'ONBOARDING' && project.current_stage !== 'SALES' && onboardingData && hasDetailedViewAccess && !isExecutiveView && user?.role !== 'ADMIN' && (
                    <div className="requirements-section">
                        <div className="section-header">
                            <h2>📋 {user?.role === 'ADMIN' ? 'Project Requirement Progress' : 'Project Onboarding Details'}</h2>
                        </div>
                        {renderReadonlyOnboardingDetails()}
                    </div>
                )}

                {/* Artifacts Section */}
                {!isExecutiveView && (
                    <div className="artifacts-section">
                        <div className="artifacts-header">
                            <h2>📎 Artifacts ({artifacts.length})</h2>
                        </div>

                        {/* Upload Area */}
                        {hasFullEditAccess && (
                            <div className="artifact-upload-form">
                                <label className="artifact-upload-area">
                                    <input
                                        type="file"
                                        style={{ display: 'none' }}
                                        onChange={handleFileUpload}
                                        disabled={uploading}
                                    />
                                    <span className="upload-icon">☁️</span>
                                    <span className="upload-text">
                                        {uploading ? 'Uploading...' : 'Click to upload project files'}
                                    </span>
                                    <span className="upload-hint">Supported: PDF, DOCX, ZIP, IMAGES</span>
                                </label>
                                <div className="artifact-notes">
                                    <label>Notes (optional):</label>
                                    <textarea
                                        placeholder="Add description..."
                                        value={artifactNotes}
                                        onChange={(e) => setArtifactNotes(e.target.value)}
                                        rows={2}
                                    />
                                </div>
                            </div>
                        )}


                        <div className="artifact-list">
                            {artifacts.length === 0 ? (
                                <p className="empty-message">No artifacts uploaded yet.</p>
                            ) : (
                                artifacts.map((artifact: any) => (
                                    <div key={artifact.id} className="artifact-card">
                                        <div className="artifact-icon">📄</div>
                                        <div className="artifact-info">
                                            <a
                                                href={artifact.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="artifact-name"
                                                download
                                            >
                                                {artifact.filename}
                                            </a>
                                            <span className="artifact-date">Uploaded on {new Date(artifact.created_at).toLocaleDateString()}</span>
                                            {artifact.notes && <p className="artifact-notes-text">{artifact.notes}</p>}
                                        </div>
                                        {(user?.role === 'ADMIN' || user?.role === 'MANAGER' || user?.id === artifact.uploaded_by_user_id) && (
                                            <button
                                                className="btn-delete-artifact"
                                                onClick={() => handleDeleteArtifact(artifact.id)}
                                                title="Delete Artifact"
                                            >
                                                🗑️
                                            </button>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {/* Test Phase Section - Visible in TEST and DEFECT_VALIDATION stages - Hidden from Executive */}
                {!isExecutiveView && (project.current_stage === 'TEST' || project.current_stage === 'DEFECT_VALIDATION') && (
                    <div className="test-phase-section">
                        <div className="section-header">
                            <h2>🧪 Test & Quality Assurance</h2>
                        </div>

                        {/* Test Phase Tabs */}
                        <div className="test-tabs">
                            <button
                                className={`tab-btn ${activeTestTab === 'scenarios' ? 'active' : ''}`}
                                onClick={() => setActiveTestTab('scenarios')}
                            >
                                📋 Test Scenarios
                            </button>
                            <button
                                className={`tab-btn ${activeTestTab === 'executions' ? 'active' : ''}`}
                                onClick={() => setActiveTestTab('executions')}
                            >
                                ▶️ Executions
                            </button>
                            <button
                                className={`tab-btn ${activeTestTab === 'defects' ? 'active' : ''}`}
                                onClick={() => setActiveTestTab('defects')}
                            >
                                ðŸ› Defects {defects.length > 0 && <span className="badge-count">{defects.length}</span>}
                            </button>
                        </div>

                        {testLoading && (
                            <div className="test-loading">
                                <div className="spinner small" />
                                <span>Loading...</span>
                            </div>
                        )}

                        {/* Test Scenarios Tab */}
                        {activeTestTab === 'scenarios' && !testLoading && (
                            <div className="test-scenarios-content">
                                <div className="content-header">
                                    <h3>Test Scenarios ({testScenarios.length})</h3>
                                    <div className="header-actions">
                                        <button
                                            className="btn-add"
                                            onClick={() => setShowCreateScenarioModal(true)}
                                        >
                                            + Create Scenario
                                        </button>
                                        {isAdmin && (
                                            <button
                                                className="btn-generate"
                                                onClick={() => handleGenerateScenario('Auto-Generated Scenarios')}
                                                disabled={testLoading}
                                            >
                                                🤖 Generate with AI
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {testScenarios.length === 0 ? (
                                    <div className="empty-state">
                                        <span className="empty-icon">📋</span>
                                        <p>No test scenarios created yet</p>
                                        <p className="empty-hint">Create test scenarios to define what needs to be tested</p>
                                    </div>
                                ) : (
                                    <div className="scenarios-grid">
                                        {testScenarios.map((scenario) => (
                                            <div
                                                key={scenario.id}
                                                className={`scenario-card ${selectedScenario?.id === scenario.id ? 'selected' : ''}`}
                                                onClick={() => setSelectedScenario(scenario)}
                                            >
                                                <div className="scenario-header">
                                                    <h4>{scenario.name}</h4>
                                                    {scenario.is_generated && (
                                                        <span className="badge-ai">🤖 AI</span>
                                                    )}
                                                </div>
                                                {scenario.description && (
                                                    <p className="scenario-description">{scenario.description}</p>
                                                )}
                                                <div className="scenario-meta">
                                                    <span className="test-case-count">
                                                        {scenario.test_cases?.length || 0} test cases
                                                    </span>
                                                    <span className="scenario-date">
                                                        {new Date(scenario.created_at).toLocaleDateString()}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Selected Scenario Details */}
                                {selectedScenario && (
                                    <div className="scenario-details">
                                        <div className="details-header">
                                            <h4>📋 {selectedScenario.name} - Test Cases</h4>
                                            <button
                                                className="btn-add small"
                                                onClick={() => setShowCreateTestCaseModal(true)}
                                            >
                                                + Add Test Case
                                            </button>
                                        </div>

                                        {selectedScenario.test_cases?.length === 0 ? (
                                            <p className="empty-message">No test cases in this scenario</p>
                                        ) : (
                                            <div className="test-cases-list">
                                                {selectedScenario.test_cases?.map((tc, index) => (
                                                    <div key={tc.id} className="test-case-item">
                                                        <div className="tc-number">{index + 1}</div>
                                                        <div className="tc-content">
                                                            <span className="tc-title">{tc.title}</span>
                                                            {tc.description && (
                                                                <span className="tc-description">{tc.description}</span>
                                                            )}
                                                            {tc.expected_result && (
                                                                <span className="tc-expected">
                                                                    <strong>Expected:</strong> {tc.expected_result}
                                                                </span>
                                                            )}
                                                        </div>
                                                        {tc.is_automated && (
                                                            <span className="badge-automated">⚡ Auto</span>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Test Executions Tab */}
                        {activeTestTab === 'executions' && !testLoading && (
                            <div className="test-executions-content">
                                <div className="content-header">
                                    <h3>Test Executions ({testExecutions.length})</h3>
                                    <button
                                        className="btn-run"
                                        onClick={() => setShowRunExecutionModal(true)}
                                        disabled={testScenarios.length === 0}
                                    >
                                        ▶️ Run New Execution
                                    </button>
                                </div>

                                {testExecutions.length === 0 ? (
                                    <div className="empty-state">
                                        <span className="empty-icon">▶️</span>
                                        <p>No test executions yet</p>
                                        <p className="empty-hint">Run an execution to test your scenarios</p>
                                    </div>
                                ) : (
                                    <div className="executions-list">
                                        {testExecutions.map((execution) => (
                                            <div
                                                key={execution.id}
                                                className={`execution-card ${selectedExecution?.id === execution.id ? 'selected' : ''}`}
                                            >
                                                <div className="execution-main">
                                                    <div className="execution-info">
                                                        <h4>{execution.execution_name}</h4>
                                                        <div className="execution-stats">
                                                            <span className="stat passed">✓ {execution.passed_tests} passed</span>
                                                            <span className="stat failed">✗ {execution.failed_tests} failed</span>
                                                            <span className="stat total">📊 {execution.total_tests} total</span>
                                                        </div>
                                                    </div>
                                                    <div className="execution-status-badge" data-status={execution.status.toLowerCase()}>
                                                        {execution.status}
                                                    </div>
                                                </div>
                                                <div className="execution-progress">
                                                    <div className="progress-bar">
                                                        <div
                                                            className="progress-passed"
                                                            style={{ width: `${(execution.passed_tests / execution.total_tests) * 100}%` }}
                                                        />
                                                        <div
                                                            className="progress-failed"
                                                            style={{ width: `${(execution.failed_tests / execution.total_tests) * 100}%` }}
                                                        />
                                                    </div>
                                                </div>
                                                <div className="execution-footer">
                                                    <span className="execution-date">
                                                        {execution.started_at
                                                            ? new Date(execution.started_at).toLocaleString()
                                                            : 'Not started'}
                                                    </span>
                                                    <button
                                                        className="btn-view-results"
                                                        onClick={() => handleViewExecutionResults(execution)}
                                                    >
                                                        View Results →
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Execution Results Panel */}
                                {selectedExecution && (
                                    <div className="results-panel">
                                        <div className="panel-header">
                                            <h4>📊 Results: {selectedExecution.execution_name}</h4>
                                            <button
                                                className="btn-close"
                                                onClick={() => {
                                                    setSelectedExecution(null);
                                                    setTestResults([]);
                                                }}
                                            >
                                                ×
                                            </button>
                                        </div>
                                        <div className="results-list">
                                            {testResults.length === 0 ? (
                                                <p className="empty-message">No results available</p>
                                            ) : (
                                                testResults.map((result) => (
                                                    <div
                                                        key={result.id}
                                                        className={`result-item ${result.status.toLowerCase()}`}
                                                    >
                                                        <div className="result-status-icon">
                                                            {result.status === 'PASSED' && '✓'}
                                                            {result.status === 'FAILED' && '✗'}
                                                            {result.status === 'SKIPPED' && '○'}
                                                            {result.status === 'ERROR' && '!'}
                                                        </div>
                                                        <div className="result-content">
                                                            <span className="result-title">{result.test_case_title}</span>
                                                            {result.error_message && (
                                                                <span className="result-error">{result.error_message}</span>
                                                            )}
                                                        </div>
                                                        <span className="result-time">{result.execution_time_ms}ms</span>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Defects Tab */}
                        {activeTestTab === 'defects' && !testLoading && (
                            <div className="defects-content">
                                {/* Defect Summary Dashboard */}
                                {defectSummary && (
                                    <div className="defect-dashboard">
                                        <div className="summary-card total">
                                            <span className="summary-value">{defectSummary.total}</span>
                                            <span className="summary-label">Total Defects</span>
                                        </div>
                                        <div className="summary-card open">
                                            <span className="summary-value">{defectSummary.by_status?.OPEN || 0}</span>
                                            <span className="summary-label">Open</span>
                                        </div>
                                        <div className="summary-card in-progress">
                                            <span className="summary-value">{defectSummary.by_status?.IN_PROGRESS || 0}</span>
                                            <span className="summary-label">In Progress</span>
                                        </div>
                                        <div className="summary-card fixed">
                                            <span className="summary-value">{defectSummary.by_status?.FIXED || 0}</span>
                                            <span className="summary-label">Fixed</span>
                                        </div>
                                        <div className="summary-card closed">
                                            <span className="summary-value">
                                                {(defectSummary.by_status?.VERIFIED || 0) + (defectSummary.by_status?.CLOSED || 0)}
                                            </span>
                                            <span className="summary-label">Closed</span>
                                        </div>
                                    </div>
                                )}

                                <div className="content-header">
                                    <h3>Defect List</h3>
                                    <div className="header-actions">
                                        <select
                                            className="filter-select"
                                            value={defectStatusFilter}
                                            onChange={(e) => {
                                                setDefectStatusFilter(e.target.value);
                                                loadDefects(e.target.value);
                                            }}
                                        >
                                            <option value="">All Status</option>
                                            <option value="OPEN">Open</option>
                                            <option value="IN_PROGRESS">In Progress</option>
                                            <option value="FIXED">Fixed</option>
                                            <option value="VERIFIED">Verified</option>
                                            <option value="CLOSED">Closed</option>
                                        </select>
                                        {isAdmin && defects.some(d => d.status === 'FIXED') && (
                                            <button
                                                className="btn-validate-all"
                                                onClick={handleValidateAllDefects}
                                            >
                                                ✓ Validate All Fixed
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {defects.length === 0 ? (
                                    <div className="empty-state success">
                                        <span className="empty-icon">🎉</span>
                                        <p>No defects found</p>
                                        <p className="empty-hint">Great! Your project has no recorded defects</p>
                                    </div>
                                ) : (
                                    <div className="defects-list">
                                        {defects.map((defect) => (
                                            <div key={defect.id} className="defect-card">
                                                <div className="defect-header">
                                                    <div className="defect-title-row">
                                                        <span
                                                            className="severity-badge"
                                                            style={{ backgroundColor: getSeverityColor(defect.severity) }}
                                                        >
                                                            {defect.severity}
                                                        </span>
                                                        <h4>{defect.title}</h4>
                                                    </div>
                                                    <span
                                                        className="status-badge"
                                                        style={{ color: getStatusColor(defect.status) }}
                                                    >
                                                        {defect.status}
                                                    </span>
                                                </div>
                                                {defect.description && (
                                                    <p className="defect-description">{defect.description}</p>
                                                )}
                                                <div className="defect-meta">
                                                    <span className="assigned-to">
                                                        👤 {defect.assigned_to_user_name || 'Unassigned'}
                                                    </span>
                                                    <span className="defect-date">
                                                        {new Date(defect.created_at).toLocaleDateString()}
                                                    </span>
                                                </div>
                                                {defect.fix_description && (
                                                    <div className="fix-info">
                                                        <strong>Fix:</strong> {defect.fix_description}
                                                    </div>
                                                )}
                                                <div className="defect-actions">
                                                    {(defect.status === 'OPEN' || defect.status === 'IN_PROGRESS') && (
                                                        <>
                                                            <button
                                                                className="btn-action reassign"
                                                                onClick={() => {
                                                                    setSelectedDefect(defect);
                                                                    setShowReassignDefectModal(true);
                                                                }}
                                                            >
                                                                🔄 Reassign
                                                            </button>
                                                            <button
                                                                className="btn-action fix"
                                                                onClick={() => {
                                                                    setSelectedDefect(defect);
                                                                    setShowFixDefectModal(true);
                                                                }}
                                                            >
                                                                🔧 Mark Fixed
                                                            </button>
                                                        </>
                                                    )}
                                                    {defect.status === 'FIXED' && isAdmin && (
                                                        <button
                                                            className="btn-action validate"
                                                            onClick={() => handleValidateDefect(defect.id)}
                                                        >
                                                            ✓ Validate Fix
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Admin Actions - Only for Consultant on their assigned projects */}
                {hasFullEditAccess && !isExecutiveAdmin && (
                    <div className="admin-actions">
                        <h3>Project Actions</h3>

                        <div className="actions-row">
                            <button
                                className="btn-advance"
                                onClick={handleAdvanceWorkflow}
                                disabled={advancing || project.current_stage === 'COMPLETE'}
                            >
                                {advancing ? 'Processing...' : '➡️ Advance Workflow'}
                            </button>
                            <button
                                className="btn-send-back"
                                onClick={handleSendBack}
                                disabled={advancing || project.current_stage === 'ONBOARDING'}
                            >
                                ⬅️ Send Back
                            </button>
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

                {/* Create Test Scenario Modal */}
                {showCreateScenarioModal && (
                    <div className="modal-overlay" onClick={() => setShowCreateScenarioModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Create Test Scenario</h2>
                            <div className="form-group">
                                <label>Scenario Name *</label>
                                <input
                                    type="text"
                                    value={newScenario.name}
                                    onChange={(e) => setNewScenario({ ...newScenario, name: e.target.value })}
                                    placeholder="e.g., User Authentication Tests"
                                />
                            </div>
                            <div className="form-group">
                                <label>Description</label>
                                <textarea
                                    value={newScenario.description}
                                    onChange={(e) => setNewScenario({ ...newScenario, description: e.target.value })}
                                    placeholder="Describe what this scenario covers..."
                                    rows={3}
                                />
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowCreateScenarioModal(false)}>Cancel</button>
                                <button className="btn-submit" onClick={handleCreateScenario}>Create Scenario</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Create Test Case Modal */}
                {showCreateTestCaseModal && selectedScenario && (
                    <div className="modal-overlay" onClick={() => setShowCreateTestCaseModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Add Test Case to {selectedScenario.name}</h2>
                            <div className="form-group">
                                <label>Test Case Title *</label>
                                <input
                                    type="text"
                                    value={newTestCase.title}
                                    onChange={(e) => setNewTestCase({ ...newTestCase, title: e.target.value })}
                                    placeholder="e.g., Verify login with valid credentials"
                                />
                            </div>
                            <div className="form-group">
                                <label>Description</label>
                                <textarea
                                    value={newTestCase.description}
                                    onChange={(e) => setNewTestCase({ ...newTestCase, description: e.target.value })}
                                    placeholder="Describe the test case..."
                                    rows={2}
                                />
                            </div>
                            <div className="form-group">
                                <label>Test Steps</label>
                                <textarea
                                    value={newTestCase.steps}
                                    onChange={(e) => setNewTestCase({ ...newTestCase, steps: e.target.value })}
                                    placeholder="1. Navigate to login page&#10;2. Enter username&#10;3. Enter password&#10;4. Click login"
                                    rows={4}
                                />
                            </div>
                            <div className="form-group">
                                <label>Expected Result *</label>
                                <input
                                    type="text"
                                    value={newTestCase.expected_result}
                                    onChange={(e) => setNewTestCase({ ...newTestCase, expected_result: e.target.value })}
                                    placeholder="e.g., User should be redirected to dashboard"
                                />
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowCreateTestCaseModal(false)}>Cancel</button>
                                <button className="btn-submit" onClick={handleCreateTestCase}>Add Test Case</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Run Test Execution Modal */}
                {showRunExecutionModal && (
                    <div className="modal-overlay" onClick={() => setShowRunExecutionModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Run Test Execution</h2>
                            <p className="modal-description">
                                This will execute all test cases in your scenarios using the QA Automation Agent.
                                Failed tests will automatically create defects.
                            </p>
                            <div className="form-group">
                                <label>Execution Name *</label>
                                <input
                                    type="text"
                                    value={executionName}
                                    onChange={(e) => setExecutionName(e.target.value)}
                                    placeholder={`Test Run - ${new Date().toLocaleDateString()}`}
                                />
                            </div>
                            <div className="execution-summary">
                                <span>📋 {testScenarios.length} scenarios</span>
                                <span>📝 {testScenarios.reduce((acc, s) => acc + (s.test_cases?.length || 0), 0)} test cases</span>
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowRunExecutionModal(false)}>Cancel</button>
                                <button
                                    className="btn-submit run"
                                    onClick={handleRunExecution}
                                    disabled={testLoading}
                                >
                                    {testLoading ? 'Running...' : '▶️ Start Execution'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Reassign Defect Modal */}
                {showReassignDefectModal && selectedDefect && (
                    <div className="modal-overlay" onClick={() => setShowReassignDefectModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Reassign Defect</h2>
                            <p className="modal-description">
                                Reassign "{selectedDefect.title}" to another available builder.
                            </p>
                            <div className="form-group">
                                <label>Assign To *</label>
                                <select
                                    value={reassignData.new_assignee_id}
                                    onChange={(e) => setReassignData({ ...reassignData, new_assignee_id: e.target.value })}
                                >
                                    <option value="">Select a builder...</option>
                                    {availableBuilders.map((builder) => (
                                        <option
                                            key={builder.id}
                                            value={builder.id}
                                            disabled={!builder.is_available}
                                        >
                                            {builder.name} ({builder.region})
                                            {!builder.is_available ? ' - Unavailable' : ` - ${builder.current_workload} tasks`}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Reason for Reassignment</label>
                                <textarea
                                    value={reassignData.reason}
                                    onChange={(e) => setReassignData({ ...reassignData, reason: e.target.value })}
                                    placeholder="e.g., Original assignee is on leave"
                                    rows={2}
                                />
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => {
                                    setShowReassignDefectModal(false);
                                    setSelectedDefect(null);
                                }}>Cancel</button>
                                <button className="btn-submit" onClick={handleReassignDefect}>Reassign</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Mark Defect Fixed Modal */}
                {showFixDefectModal && selectedDefect && (
                    <div className="modal-overlay" onClick={() => setShowFixDefectModal(false)}>
                        <div className="modal" onClick={(e) => e.stopPropagation()}>
                            <h2>Mark Defect as Fixed</h2>
                            <p className="modal-description">
                                Provide details about how "{selectedDefect.title}" was fixed.
                            </p>
                            <div className="form-group">
                                <label>Fix Description *</label>
                                <textarea
                                    value={fixDescription}
                                    onChange={(e) => setFixDescription(e.target.value)}
                                    placeholder="Describe the fix that was applied..."
                                    rows={4}
                                />
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => {
                                    setShowFixDefectModal(false);
                                    setSelectedDefect(null);
                                    setFixDescription('');
                                }}>Cancel</button>
                                <button className="btn-submit" onClick={handleMarkDefectFixed}>Mark as Fixed</button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Team Assignment Modal */}
                {showTeamModal && (
                    <div className="modal-overlay" onClick={() => setShowTeamModal(false)}>
                        <div className="modal modal-xl" onClick={(e) => e.stopPropagation()}>
                            <h2>👥 Assign Team Members</h2>
                            <p className="modal-description">
                                Assign team members in sequence: Consultant → PC → Builder → Tester
                                {user?.role === 'MANAGER' && <><br /><span className="region-note">📝 As a Manager, you can only assign from your region: <strong>{user?.region}</strong></span></>}
                                {user?.role === 'PC' && user?.region === 'INDIA' && <><br /><span className="region-note">📝 As a PC, you can assign Builder and Tester from India region</span></>}
                            </p>

                            {/* Assignment Progress */}
                            <div className="assignment-progress">
                                {project.require_manual_review && (
                                    <>
                                        <div className={`progress-step ${assignmentSequence.consultant_assigned ? 'completed' : assignmentSequence.next_to_assign === 'consultant' ? 'current' : ''}`}>
                                            <span className="step-number">1</span>
                                            <span className="step-label">Consultant</span>
                                        </div>
                                        <div className="progress-line" />
                                    </>
                                )}
                                <div className={`progress-step ${assignmentSequence.pc_assigned ? 'completed' : assignmentSequence.next_to_assign === 'pc' ? 'current' : ''}`}>
                                    <span className="step-number">2</span>
                                    <span className="step-label">PC</span>
                                </div>
                                <div className="progress-line" />
                                <div className={`progress-step ${assignmentSequence.builder_assigned ? 'completed' : assignmentSequence.next_to_assign === 'builder' ? 'current' : ''}`}>
                                    <span className="step-number">3</span>
                                    <span className="step-label">Builder</span>
                                </div>
                                <div className="progress-line" />
                                <div className={`progress-step ${assignmentSequence.tester_assigned ? 'completed' : assignmentSequence.next_to_assign === 'tester' ? 'current' : ''}`}>
                                    <span className="step-number">4</span>
                                    <span className="step-label">Tester</span>
                                </div>
                            </div>

                            {/* Project Workload Estimate */}
                            {projectWorkload && (
                                <div className="workload-estimate">
                                    <h4>📊 Estimated Project Workload</h4>
                                    <div className="workload-badges">
                                        <span className="workload-badge">Total: {projectWorkload.total_hours}h</span>
                                        {Object.entries(projectWorkload.by_role || {}).map(([role, hours]) => (
                                            <span key={role} className="workload-badge role">{role}: {hours as number}h</span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Role Selection Cards - Order: CONSULTANT, PC, BUILDER, TESTER */}
                            {['CONSULTANT', 'PC', 'BUILDER', 'TESTER'].filter(role => role !== 'CONSULTANT' || project.require_manual_review).map((role) => {
                                // Permission check
                                const canAssignThisRole =
                                    (role === 'CONSULTANT' && canAssignConsultant) ||
                                    (role === 'PC' && canAssignPC) ||
                                    (role === 'BUILDER' && canAssignBuilder) ||
                                    (role === 'TESTER' && canAssignTester);

                                // Sequential check
                                const isSequenceAllowed =
                                    (role === 'CONSULTANT') ||
                                    (role === 'PC' && (assignmentSequence.consultant_assigned || teamFormData.consultant_user_id)) ||
                                    (role === 'BUILDER' && (assignmentSequence.pc_assigned || teamFormData.pc_user_id)) ||
                                    (role === 'TESTER' && (assignmentSequence.builder_assigned || teamFormData.builder_user_id));

                                const isDisabled = !canAssignThisRole || !isSequenceAllowed;
                                const isAlreadyAssigned =
                                    (role === 'CONSULTANT' && assignmentSequence.consultant_assigned) ||
                                    (role === 'PC' && assignmentSequence.pc_assigned) ||
                                    (role === 'BUILDER' && assignmentSequence.builder_assigned) ||
                                    (role === 'TESTER' && assignmentSequence.tester_assigned);
                                const capacityList = capacityByRole[role] || [];
                                const suggestions = aiSuggestions[role];
                                const roleIcon = role === 'PC' ? '🎯' : role === 'CONSULTANT' ? '💼' : role === 'BUILDER' ? '🔨' : '🧪';
                                const roleKey = role.toLowerCase() + '_user_id';
                                const selectedValue = teamFormData[roleKey as keyof typeof teamFormData];
                                const requiredHours = projectWorkload?.by_role?.[role] || 0;
                                const stepNumber = role === 'CONSULTANT' ? 1 : role === 'PC' ? 2 : role === 'BUILDER' ? 3 : 4;

                                return (
                                    <div key={role} className={`role-assignment-card ${isDisabled ? 'disabled' : ''} ${isAlreadyAssigned ? 'assigned' : ''}`}>
                                        <div className="role-header">
                                            <h4>
                                                <span className="role-step">Step {stepNumber}</span>
                                                {roleIcon} {role}
                                                {isAlreadyAssigned && <span className="assigned-badge">✓ Assigned</span>}
                                                {isDisabled && !isAlreadyAssigned && (
                                                    <span className="locked-badge">
                                                        {!canAssignThisRole ? '🔒 No Permission' : 'â³ Complete previous step'}
                                                    </span>
                                                )}
                                            </h4>
                                            <div className="role-header-actions">
                                                {!isDisabled && (
                                                    <button
                                                        className="btn-ai-suggest"
                                                        onClick={() => loadAiSuggestions(role)}
                                                        disabled={loadingSuggestions && selectedRoleForSuggestion === role}
                                                    >
                                                        {loadingSuggestions && selectedRoleForSuggestion === role ? 'â³' : '🤖'} AI Suggest
                                                    </button>
                                                )}
                                                {requiredHours > 0 && (
                                                    <span className="required-hours">Required: {requiredHours}h</span>
                                                )}
                                            </div>
                                        </div>

                                        {/* AI Suggestions Panel */}
                                        {suggestions && (
                                            <div className={`ai-suggestions-panel ${suggestions.capacity_crunch ? 'crunch' : ''}`}>
                                                {suggestions.capacity_crunch ? (
                                                    <div className="capacity-crunch-alert">
                                                        <h5>⚠️ Capacity Crunch Detected</h5>
                                                        {(suggestions.suggestions[0] as CapacityCrunchSuggestion)?.suggestions?.map((s, i) => (
                                                            <p key={i}>{s}</p>
                                                        ))}
                                                        <div className="crunch-actions">
                                                            {(suggestions.suggestions[0] as CapacityCrunchSuggestion)?.recommended_actions?.map((action, i) => (
                                                                <span key={i} className="crunch-action">{action.description}</span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <>
                                                        <p className="suggestion-summary">
                                                            {suggestions.available_users_count} {role}s available with {suggestions.total_available_hours.toFixed(1)}h total capacity
                                                        </p>
                                                        <div className="suggestions-list">
                                                            {(suggestions.suggestions as AISuggestion[]).slice(0, 3).map((s) => (
                                                                <div key={s.id} className="suggestion-item">
                                                                    <div className="suggestion-main">
                                                                        <span className="suggestion-rank">#{s.rank}</span>
                                                                        <div className="suggestion-info">
                                                                            <span className="suggestion-name">{s.user_name}</span>
                                                                            <span className="suggestion-region">{s.region || 'No region'}</span>
                                                                        </div>
                                                                        <div className="suggestion-capacity">
                                                                            <span className="capacity-bar-mini">
                                                                                <span
                                                                                    className="capacity-fill-mini"
                                                                                    style={{
                                                                                        width: `${s.utilization_percentage}%`,
                                                                                        backgroundColor: getCapacityStatusColor(s.capacity_status)
                                                                                    }}
                                                                                />
                                                                            </span>
                                                                            <span className="capacity-text">{s.remaining_hours.toFixed(1)}h free</span>
                                                                        </div>
                                                                        <span className="confidence-badge">{(s.confidence_score * 100).toFixed(0)}% match</span>
                                                                    </div>
                                                                    <button
                                                                        className="btn-accept-suggestion"
                                                                        onClick={() => handleAcceptSuggestion(s, role)}
                                                                    >
                                                                        ✓ Select
                                                                    </button>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                        )}

                                        {/* User Selection with Capacity */}
                                        <div className="capacity-user-list">
                                            {capacityList.length === 0 ? (
                                                <p className="no-users-hint">No {role}s available. Create users with {role} role first.</p>
                                            ) : (
                                                capacityList.map((user) => (
                                                    <div
                                                        key={user.user_id}
                                                        className={`capacity-user-item ${selectedValue === user.user_id ? 'selected' : ''} ${!user.is_recommended ? 'not-recommended' : ''}`}
                                                        onClick={() => setTeamFormData({ ...teamFormData, [roleKey]: user.user_id })}
                                                    >
                                                        <div className="user-info">
                                                            <span className="user-name">{user.user_name}</span>
                                                            <span className="user-region">{user.region || 'No region'}</span>
                                                        </div>
                                                        <div className="user-capacity">
                                                            <div className="capacity-bar">
                                                                <div
                                                                    className="capacity-fill"
                                                                    style={{
                                                                        width: `${user.utilization_percentage}%`,
                                                                        backgroundColor: getCapacityStatusColor(user.capacity_status)
                                                                    }}
                                                                />
                                                            </div>
                                                            <div className="capacity-details">
                                                                <span className="hours-available">{user.remaining_hours.toFixed(1)}h available</span>
                                                                <span className="utilization">{user.utilization_percentage}% used</span>
                                                            </div>
                                                        </div>
                                                        <div className="capacity-status" style={{ color: getCapacityStatusColor(user.capacity_status) }}>
                                                            {user.capacity_status}
                                                        </div>
                                                        {user.is_recommended && <span className="recommended-badge">✓ Recommended</span>}
                                                        {selectedValue === user.user_id && <span className="selected-indicator">✓</span>}
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </div>
                                );
                            })}

                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowTeamModal(false)}>Cancel</button>
                                <button
                                    className="btn-submit"
                                    onClick={handleAssignTeam}
                                    disabled={assigningTeam}
                                >
                                    {assigningTeam ? 'Saving...' : 'Save Assignments'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            {/* Styles moved to project-details.css */}
            {/* Lightbox Modal */}
            {previewImage && (
                <div className="lightbox-overlay" onClick={() => setPreviewImage(null)}>
                    <div className="lightbox-content" onClick={e => e.stopPropagation()}>
                        <button className="lightbox-close" onClick={() => setPreviewImage(null)}>×</button>
                        <img src={previewImage} alt="Full size preview" />
                    </div>
                </div>
            )}

            {showChatLogs && <ConsultantChatModal projectId={projectId as string} onClose={() => setShowChatLogs(false)} />}

            <style jsx global>{`
                .requirements-grid {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }
                .readonly-group {
                    margin-bottom: 24px;
                }
            `}</style>


        </div>
    );
}
