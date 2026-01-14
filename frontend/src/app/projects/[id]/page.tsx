'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { projectsAPI, artifactsAPI, workflowAPI, onboardingAPI, projectTasksAPI, remindersAPI, testingAPI, usersAPI, capacityAPI } from '@/lib/api';
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

    // Test Phase State
    const [testScenarios, setTestScenarios] = useState<TestScenario[]>([]);
    const [testExecutions, setTestExecutions] = useState<TestExecution[]>([]);
    const [testResults, setTestResults] = useState<TestResult[]>([]);
    const [defects, setDefects] = useState<Defect[]>([]);
    const [defectSummary, setDefectSummary] = useState<DefectSummary | null>(null);
    const [availableBuilders, setAvailableBuilders] = useState<AvailableBuilder[]>([]);
    
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

    // Role and assignment checks
    const isAdmin = user?.role === 'ADMIN' || user?.role === 'MANAGER';
    const isExecutiveAdmin = user?.role === 'ADMIN';
    
    // Check if current user is assigned to this project
    const isAssignedToProject = user && project && (
        teamAssignments?.consultant?.id === user.id ||
        teamAssignments?.pc?.id === user.id ||
        teamAssignments?.builder?.id === user.id ||
        teamAssignments?.tester?.id === user.id
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

                {/* Onboarding Section - Role-based views */}
                {project.current_stage === 'ONBOARDING' && onboardingData && (
                    <div className="onboarding-section">
                        <div className="section-header">
                            <h2>📋 Onboarding Details</h2>
                            {hasFullEditAccess && completionStatus?.can_auto_advance && (
                                <button className="btn-auto-advance" onClick={handleAutoAdvance} disabled={advancing}>
                                    🚀 Auto-Advance (90%+ Complete)
                                </button>
                            )}
                        </div>

                        {/* ADMIN or Non-Assigned Consultant VIEW - Summary Only */}
                        {(user?.role === 'ADMIN' || (user?.role === 'CONSULTANT' && !isAssignedToProject)) && (
                            <div className="onboarding-summary-view">
                                <div className="summary-card">
                                    <div className="summary-progress">
                                        <div className="progress-ring" style={{ '--progress': completionStatus?.completion_percentage || 0 } as React.CSSProperties}>
                                            <span className="progress-value">{completionStatus?.completion_percentage || 0}%</span>
                                        </div>
                                        <div className="progress-label">
                                            <h4>Onboarding Progress</h4>
                                            <p>{completionStatus?.completed_tasks || 0} of {completionStatus?.total_required_tasks || 0} items complete</p>
                                        </div>
                                    </div>
                                    
                                    <div className="checklist-summary">
                                        <h4>📋 Requirements Checklist</h4>
                                        <div className="checklist-grid">
                                            <div className={`checklist-item ${(onboardingData.contacts_json?.length || 0) > 0 ? 'provided' : 'pending'}`}>
                                                <span className="checklist-icon">{(onboardingData.contacts_json?.length || 0) > 0 ? '✅' : '⏳'}</span>
                                                <span>Client Contacts</span>
                                            </div>
                                            <div className={`checklist-item ${onboardingData.logo_url ? 'provided' : 'pending'}`}>
                                                <span className="checklist-icon">{onboardingData.logo_url ? '✅' : '⏳'}</span>
                                                <span>Company Logo</span>
                                            </div>
                                            <div className={`checklist-item ${(onboardingData.images_json?.length || 0) > 0 ? 'provided' : 'pending'}`}>
                                                <span className="checklist-icon">{(onboardingData.images_json?.length || 0) > 0 ? '✅' : '⏳'}</span>
                                                <span>Website Images</span>
                                            </div>
                                            <div className={`checklist-item ${onboardingData.copy_text || onboardingData.use_custom_copy ? 'provided' : 'pending'}`}>
                                                <span className="checklist-icon">{onboardingData.copy_text || onboardingData.use_custom_copy ? '✅' : '⏳'}</span>
                                                <span>Copy Text</span>
                                            </div>
                                            <div className={`checklist-item ${onboardingData.privacy_policy_url || onboardingData.privacy_policy_text ? 'provided' : 'pending'}`}>
                                                <span className="checklist-icon">{onboardingData.privacy_policy_url || onboardingData.privacy_policy_text ? '✅' : '⏳'}</span>
                                                <span>Privacy Policy</span>
                                            </div>
                                            <div className={`checklist-item ${onboardingData.theme_preference ? 'provided' : 'pending'}`}>
                                                <span className="checklist-icon">{onboardingData.theme_preference ? '✅' : '⏳'}</span>
                                                <span>Theme Preferences</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    {completionStatus && completionStatus.missing_fields.length > 0 && (
                                        <div className="pending-items-summary">
                                            <h4>⏳ Pending Items ({completionStatus.missing_fields.length})</h4>
                                            <ul>
                                                {completionStatus.missing_fields.slice(0, 5).map((field, index) => (
                                                    <li key={index}>{field}</li>
                                                ))}
                                                {completionStatus.missing_fields.length > 5 && (
                                                    <li className="more-items">+{completionStatus.missing_fields.length - 5} more items</li>
                                                )}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* MANAGER VIEW - Read-Only Details */}
                        {user?.role === 'MANAGER' && (
                            <div className="onboarding-readonly-view">
                                {/* Client Contacts - Read Only */}
                                <div className="form-card readonly">
                                    <h3>👥 Client Contacts</h3>
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
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                                
                                {/* Assets - Read Only */}
                                <div className="form-card readonly">
                                    <h3>🖼️ Website Assets</h3>
                                    <div className="readonly-grid">
                                        <div className="readonly-item">
                                            <label>Company Logo</label>
                                            <span>{onboardingData.logo_url || 'Not provided'}</span>
                                        </div>
                                        <div className="readonly-item">
                                            <label>Website Images</label>
                                            <span>{onboardingData.images_json?.length || 0} images provided</span>
                                        </div>
                                    </div>
                                </div>
                                
                                {/* Copy Text - Read Only */}
                                <div className="form-card readonly">
                                    <h3>📝 Copy Text</h3>
                                    <div className="readonly-item">
                                        {onboardingData.use_custom_copy ? (
                                            <span className="badge-info">Custom copy requested from team</span>
                                        ) : onboardingData.copy_text ? (
                                            <p className="copy-preview">{onboardingData.copy_text.substring(0, 200)}...</p>
                                        ) : (
                                            <span className="empty-message">Not provided</span>
                                        )}
                                    </div>
                                </div>
                                
                                {/* WCAG - Read Only */}
                                <div className="form-card readonly">
                                    <h3>♿ Accessibility</h3>
                                    <div className="readonly-item">
                                        <span>{onboardingData.wcag_compliance_required ? `WCAG ${onboardingData.wcag_level} Required` : 'Not required'}</span>
                                    </div>
                                </div>
                                
                                {/* Privacy Policy - Read Only */}
                                <div className="form-card readonly">
                                    <h3>🔒 Privacy Policy</h3>
                                    <div className="readonly-item">
                                        <span>{onboardingData.privacy_policy_url || onboardingData.privacy_policy_text ? 'Provided' : 'Not provided'}</span>
                                    </div>
                                </div>
                                
                                {/* Theme - Read Only */}
                                <div className="form-card readonly">
                                    <h3>🎨 Theme Preferences</h3>
                                    <div className="readonly-item">
                                        <span>{onboardingData.theme_preference || 'Not selected'}</span>
                                    </div>
                                </div>
                                
                                {/* Missing Fields */}
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

                        {/* CONSULTANT VIEW - Full Edit Mode (Only for Assigned Consultant) */}
                        {user?.role === 'CONSULTANT' && isAssignedToProject && (
                            <>
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

                        {/* Missing Fields Alert - Consultant View */}
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
                            </>
                        )}
                    </div>
                )}

                {/* Tasks Section - Auto-updated based on client inputs - Hidden from Executive Admin */}
                {!isExecutiveView && (
                <div className="tasks-section">
                    <div className="section-header">
                        <h2>✅ Tasks ({tasks.length})</h2>
                        <div className="section-header-right">
                            {project.current_stage === 'ONBOARDING' && (
                                <span className="auto-update-badge">🔄 Auto-updates from client inputs</span>
                            )}
                            {hasFullEditAccess && !project.current_stage.includes('ONBOARDING') && (
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
                )}

                {/* Artifacts Section - Hidden from Executive Admin */}
                {!isExecutiveView && (
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
                                ▶️ Executions
                            </button>
                            <button 
                                className={`tab-btn ${activeTestTab === 'defects' ? 'active' : ''}`}
                                onClick={() => setActiveTestTab('defects')}
                            >
                                🐛 Defects {defects.length > 0 && <span className="badge-count">{defects.length}</span>}
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
                                        ▶️ Run New Execution
                                    </button>
                                </div>

                                {testExecutions.length === 0 ? (
                                    <div className="empty-state">
                                        <span className="empty-icon">▶️</span>
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
                                <span>📝 {testScenarios.reduce((acc, s) => acc + (s.test_cases?.length || 0), 0)} test cases</span>
                            </div>
                            <div className="modal-actions">
                                <button className="btn-cancel" onClick={() => setShowRunExecutionModal(false)}>Cancel</button>
                                <button 
                                    className="btn-submit run"
                                    onClick={handleRunExecution}
                                    disabled={testLoading}
                                >
                                    {testLoading ? 'Running...' : '▶️ Start Execution'}
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
                                {user?.role === 'MANAGER' && <><br/><span className="region-note">📍 As a Manager, you can only assign from your region: <strong>{user?.region}</strong></span></>}
                                {user?.role === 'PC' && user?.region === 'INDIA' && <><br/><span className="region-note">📍 As a PC, you can assign Builder and Tester from India region</span></>}
                            </p>
                            
                            {/* Assignment Progress */}
                            <div className="assignment-progress">
                                <div className={`progress-step ${assignmentSequence.consultant_assigned ? 'completed' : assignmentSequence.next_to_assign === 'consultant' ? 'current' : ''}`}>
                                    <span className="step-number">1</span>
                                    <span className="step-label">Consultant</span>
                                </div>
                                <div className="progress-line" />
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
                            {['CONSULTANT', 'PC', 'BUILDER', 'TESTER'].map((role) => {
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
                                                        {!canAssignThisRole ? '🔒 No Permission' : '⏳ Complete previous step'}
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
                                                        {loadingSuggestions && selectedRoleForSuggestion === role ? '⏳' : '🤖'} AI Suggest
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
                                                        <h5>⚠️ Capacity Crunch Detected</h5>
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
                
                /* Admin Summary View */
                .onboarding-summary-view .summary-card {
                    background: white;
                    border-radius: 16px;
                    padding: 2rem;
                    border: 1px solid #e2e8f0;
                }
                
                .summary-progress {
                    display: flex;
                    align-items: center;
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                    padding-bottom: 1.5rem;
                    border-bottom: 1px solid #e2e8f0;
                }
                
                .progress-ring {
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    background: conic-gradient(#22c55e calc(var(--progress) * 1%), #e2e8f0 0);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                }
                
                .progress-ring::before {
                    content: '';
                    position: absolute;
                    width: 80px;
                    height: 80px;
                    background: white;
                    border-radius: 50%;
                }
                
                .progress-ring .progress-value {
                    position: relative;
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: #1e293b;
                }
                
                .progress-label h4 {
                    margin: 0 0 0.25rem;
                    color: #1e293b;
                }
                
                .progress-label p {
                    margin: 0;
                    color: #64748b;
                    font-size: 0.9rem;
                }
                
                .checklist-summary {
                    margin-bottom: 1.5rem;
                }
                
                .checklist-summary h4 {
                    margin: 0 0 1rem;
                    color: #1e293b;
                }
                
                .checklist-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                    gap: 0.75rem;
                }
                
                .checklist-item {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.75rem 1rem;
                    border-radius: 8px;
                    font-size: 0.9rem;
                }
                
                .checklist-item.provided {
                    background: #dcfce7;
                    color: #166534;
                }
                
                .checklist-item.pending {
                    background: #fef3c7;
                    color: #92400e;
                }
                
                .checklist-icon {
                    font-size: 1rem;
                }
                
                .pending-items-summary {
                    background: #fef3c7;
                    border-radius: 12px;
                    padding: 1rem 1.5rem;
                }
                
                .pending-items-summary h4 {
                    margin: 0 0 0.75rem;
                    color: #92400e;
                }
                
                .pending-items-summary ul {
                    margin: 0;
                    padding-left: 1.25rem;
                    color: #92400e;
                }
                
                .pending-items-summary li {
                    margin-bottom: 0.25rem;
                }
                
                .pending-items-summary .more-items {
                    font-style: italic;
                    opacity: 0.8;
                }
                
                /* Manager Read-Only View */
                .onboarding-readonly-view .form-card.readonly {
                    background: #f8fafc;
                }
                
                .readonly-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 1rem;
                }
                
                .readonly-item {
                    padding: 0.75rem 0;
                }
                
                .readonly-item label {
                    display: block;
                    font-size: 0.8rem;
                    color: #64748b;
                    margin-bottom: 0.25rem;
                }
                
                .readonly-item span, .readonly-item p {
                    color: #1e293b;
                }
                
                .copy-preview {
                    background: white;
                    padding: 0.75rem;
                    border-radius: 8px;
                    border: 1px solid #e2e8f0;
                    font-size: 0.9rem;
                    color: #64748b;
                }
                
                .badge-info {
                    display: inline-block;
                    background: #dbeafe;
                    color: #1e40af;
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    font-size: 0.85rem;
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

                /* Test Phase Styles */
                .test-phase-section {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    margin-bottom: var(--space-xl);
                }

                .test-tabs {
                    display: flex;
                    gap: var(--space-sm);
                    margin-bottom: var(--space-lg);
                    border-bottom: 1px solid var(--border-light);
                    padding-bottom: var(--space-md);
                }

                .tab-btn {
                    padding: 10px 20px;
                    background: transparent;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 14px;
                    font-weight: 500;
                    color: var(--text-muted);
                    cursor: pointer;
                    transition: all var(--transition-fast);
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                }

                .tab-btn:hover {
                    background: var(--bg-secondary);
                    color: var(--text-primary);
                }

                .tab-btn.active {
                    background: var(--accent-primary);
                    color: white;
                }

                .badge-count {
                    background: var(--color-error);
                    color: white;
                    font-size: 11px;
                    padding: 2px 6px;
                    border-radius: var(--radius-full);
                    font-weight: 600;
                }

                .test-loading {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: var(--space-sm);
                    padding: var(--space-xl);
                    color: var(--text-muted);
                }

                .spinner.small {
                    width: 20px;
                    height: 20px;
                }

                .content-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-lg);
                }

                .content-header h3 {
                    margin: 0;
                    color: var(--text-primary);
                    font-size: 16px;
                }

                .header-actions {
                    display: flex;
                    gap: var(--space-sm);
                }

                .btn-generate {
                    padding: 8px 16px;
                    background: linear-gradient(135deg, #7c3aed 0%, #9333ea 100%);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                }

                .btn-generate:hover:not(:disabled) {
                    transform: translateY(-1px);
                    box-shadow: var(--shadow-md);
                }

                .btn-run {
                    padding: 8px 16px;
                    background: linear-gradient(135deg, var(--color-success) 0%, #059669 100%);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                }

                .btn-run:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .empty-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: var(--space-2xl);
                    text-align: center;
                }

                .empty-state.success {
                    background: var(--color-success-bg);
                    border-radius: var(--radius-lg);
                }

                .empty-icon {
                    font-size: 48px;
                    margin-bottom: var(--space-md);
                }

                .empty-state p {
                    margin: 0;
                    color: var(--text-primary);
                    font-weight: 500;
                }

                .empty-hint {
                    color: var(--text-muted) !important;
                    font-weight: 400 !important;
                    font-size: 14px;
                    margin-top: var(--space-xs) !important;
                }

                /* Scenarios Grid */
                .scenarios-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: var(--space-md);
                    margin-bottom: var(--space-lg);
                }

                .scenario-card {
                    background: var(--bg-secondary);
                    border: 2px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-md);
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }

                .scenario-card:hover {
                    border-color: var(--accent-primary);
                    box-shadow: var(--shadow-sm);
                }

                .scenario-card.selected {
                    border-color: var(--accent-primary);
                    background: rgba(37, 99, 235, 0.05);
                }

                .scenario-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: var(--space-sm);
                }

                .scenario-header h4 {
                    margin: 0;
                    font-size: 15px;
                    color: var(--text-primary);
                }

                .badge-ai {
                    background: linear-gradient(135deg, #7c3aed 0%, #9333ea 100%);
                    color: white;
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: var(--radius-full);
                }

                .scenario-description {
                    margin: 0;
                    font-size: 13px;
                    color: var(--text-muted);
                    line-height: 1.4;
                }

                .scenario-meta {
                    display: flex;
                    justify-content: space-between;
                    margin-top: var(--space-sm);
                    padding-top: var(--space-sm);
                    border-top: 1px solid var(--border-light);
                    font-size: 12px;
                    color: var(--text-hint);
                }

                /* Scenario Details */
                .scenario-details {
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                }

                .details-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-md);
                }

                .details-header h4 {
                    margin: 0;
                    color: var(--text-primary);
                }

                .btn-add.small {
                    padding: 6px 12px;
                    font-size: 12px;
                }

                .test-cases-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-sm);
                }

                .test-case-item {
                    display: flex;
                    gap: var(--space-md);
                    padding: var(--space-md);
                    background: var(--bg-primary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-md);
                }

                .tc-number {
                    width: 28px;
                    height: 28px;
                    background: var(--accent-primary);
                    color: white;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: 600;
                    flex-shrink: 0;
                }

                .tc-content {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .tc-title {
                    font-weight: 500;
                    color: var(--text-primary);
                }

                .tc-description {
                    font-size: 13px;
                    color: var(--text-muted);
                }

                .tc-expected {
                    font-size: 12px;
                    color: var(--color-info);
                    background: var(--color-info-bg);
                    padding: 4px 8px;
                    border-radius: var(--radius-sm);
                }

                .badge-automated {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                    padding: 4px 8px;
                    border-radius: var(--radius-full);
                    font-size: 11px;
                    font-weight: 600;
                    height: fit-content;
                }

                /* Executions List */
                .executions-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-md);
                }

                .execution-card {
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-md);
                }

                .execution-card.selected {
                    border-color: var(--accent-primary);
                }

                .execution-main {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: var(--space-sm);
                }

                .execution-info h4 {
                    margin: 0 0 var(--space-xs) 0;
                    font-size: 15px;
                    color: var(--text-primary);
                }

                .execution-stats {
                    display: flex;
                    gap: var(--space-md);
                }

                .execution-stats .stat {
                    font-size: 13px;
                }

                .execution-stats .stat.passed {
                    color: var(--color-success);
                }

                .execution-stats .stat.failed {
                    color: var(--color-error);
                }

                .execution-stats .stat.total {
                    color: var(--text-muted);
                }

                .execution-status-badge {
                    padding: 4px 10px;
                    border-radius: var(--radius-full);
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                }

                .execution-status-badge[data-status="completed"] {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                }

                .execution-status-badge[data-status="running"] {
                    background: var(--color-warning-bg);
                    color: var(--color-warning);
                }

                .execution-status-badge[data-status="pending"] {
                    background: var(--bg-tertiary);
                    color: var(--text-muted);
                }

                .execution-status-badge[data-status="failed"] {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                }

                .execution-progress .progress-bar {
                    display: flex;
                    height: 8px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                    overflow: hidden;
                }

                .progress-passed {
                    background: var(--color-success);
                }

                .progress-failed {
                    background: var(--color-error);
                }

                .execution-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-top: var(--space-sm);
                    padding-top: var(--space-sm);
                    border-top: 1px solid var(--border-light);
                }

                .execution-date {
                    font-size: 12px;
                    color: var(--text-hint);
                }

                .btn-view-results {
                    background: transparent;
                    border: none;
                    color: var(--accent-primary);
                    font-size: 13px;
                    font-weight: 500;
                    cursor: pointer;
                }

                .btn-view-results:hover {
                    text-decoration: underline;
                }

                /* Results Panel */
                .results-panel {
                    margin-top: var(--space-lg);
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    overflow: hidden;
                }

                .panel-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: var(--space-md) var(--space-lg);
                    background: var(--bg-tertiary);
                    border-bottom: 1px solid var(--border-light);
                }

                .panel-header h4 {
                    margin: 0;
                    font-size: 14px;
                    color: var(--text-primary);
                }

                .btn-close {
                    width: 28px;
                    height: 28px;
                    background: transparent;
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-muted);
                    font-size: 18px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .btn-close:hover {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                    border-color: var(--color-error);
                }

                .results-list {
                    max-height: 400px;
                    overflow-y: auto;
                }

                .result-item {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    padding: var(--space-md) var(--space-lg);
                    border-bottom: 1px solid var(--border-light);
                }

                .result-item:last-child {
                    border-bottom: none;
                }

                .result-item.passed {
                    background: rgba(34, 197, 94, 0.05);
                }

                .result-item.failed {
                    background: rgba(239, 68, 68, 0.05);
                }

                .result-status-icon {
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: bold;
                    flex-shrink: 0;
                }

                .result-item.passed .result-status-icon {
                    background: var(--color-success);
                    color: white;
                }

                .result-item.failed .result-status-icon {
                    background: var(--color-error);
                    color: white;
                }

                .result-item.skipped .result-status-icon {
                    background: var(--bg-tertiary);
                    color: var(--text-muted);
                }

                .result-item.error .result-status-icon {
                    background: var(--color-warning);
                    color: white;
                }

                .result-content {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }

                .result-title {
                    font-size: 14px;
                    color: var(--text-primary);
                }

                .result-error {
                    font-size: 12px;
                    color: var(--color-error);
                }

                .result-time {
                    font-size: 12px;
                    color: var(--text-hint);
                }

                /* Defects Dashboard */
                .defect-dashboard {
                    display: grid;
                    grid-template-columns: repeat(5, 1fr);
                    gap: var(--space-md);
                    margin-bottom: var(--space-lg);
                }

                .summary-card {
                    background: var(--bg-secondary);
                    border-radius: var(--radius-lg);
                    padding: var(--space-md);
                    text-align: center;
                    border-left: 4px solid transparent;
                }

                .summary-card.total {
                    border-left-color: var(--accent-primary);
                }

                .summary-card.open {
                    border-left-color: var(--color-error);
                }

                .summary-card.in-progress {
                    border-left-color: var(--color-warning);
                }

                .summary-card.fixed {
                    border-left-color: var(--color-info);
                }

                .summary-card.closed {
                    border-left-color: var(--color-success);
                }

                .summary-value {
                    display: block;
                    font-size: 28px;
                    font-weight: 700;
                    color: var(--text-primary);
                }

                .summary-label {
                    display: block;
                    font-size: 12px;
                    color: var(--text-muted);
                    margin-top: 4px;
                }

                .filter-select {
                    padding: 8px 12px;
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    color: var(--text-primary);
                }

                .btn-validate-all {
                    padding: 8px 16px;
                    background: var(--color-success);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                }

                /* Defects List */
                .defects-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-md);
                }

                .defect-card {
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-md);
                }

                .defect-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: var(--space-sm);
                }

                .defect-title-row {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                }

                .severity-badge {
                    color: white;
                    font-size: 10px;
                    padding: 2px 8px;
                    border-radius: var(--radius-full);
                    font-weight: 600;
                    text-transform: uppercase;
                }

                .defect-header h4 {
                    margin: 0;
                    font-size: 15px;
                    color: var(--text-primary);
                }

                .defect-description {
                    margin: 0 0 var(--space-sm) 0;
                    font-size: 13px;
                    color: var(--text-muted);
                }

                .defect-meta {
                    display: flex;
                    gap: var(--space-md);
                    font-size: 12px;
                    color: var(--text-hint);
                    margin-bottom: var(--space-sm);
                }

                .fix-info {
                    background: var(--color-success-bg);
                    padding: var(--space-sm) var(--space-md);
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    color: var(--color-success);
                    margin-bottom: var(--space-sm);
                }

                .defect-actions {
                    display: flex;
                    gap: var(--space-sm);
                    padding-top: var(--space-sm);
                    border-top: 1px solid var(--border-light);
                }

                .btn-action {
                    padding: 6px 12px;
                    border-radius: var(--radius-md);
                    font-size: 12px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }

                .btn-action.reassign {
                    background: var(--color-warning-bg);
                    color: var(--color-warning);
                    border: 1px solid var(--color-warning-border);
                }

                .btn-action.fix {
                    background: var(--color-info-bg);
                    color: var(--color-info);
                    border: 1px solid var(--color-info-border);
                }

                .btn-action.validate {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                    border: 1px solid var(--color-success-border);
                }

                .btn-action:hover {
                    transform: translateY(-1px);
                }

                /* Modal Enhancements */
                .modal-description {
                    margin: 0 0 var(--space-lg) 0;
                    color: var(--text-muted);
                    font-size: 14px;
                    line-height: 1.5;
                }

                .execution-summary {
                    display: flex;
                    gap: var(--space-md);
                    padding: var(--space-md);
                    background: var(--bg-secondary);
                    border-radius: var(--radius-md);
                    margin-top: var(--space-md);
                    font-size: 13px;
                    color: var(--text-secondary);
                }

                .btn-submit.run {
                    background: linear-gradient(135deg, var(--color-success) 0%, #059669 100%);
                }

                /* Team Assignment Styles */
                .team-section {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    margin-bottom: var(--space-xl);
                }

                .team-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: var(--space-md);
                }

                .team-card {
                    background: var(--bg-secondary);
                    border: 2px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    text-align: center;
                    transition: all var(--transition-fast);
                }

                .team-card.assigned {
                    border-color: var(--color-success);
                    background: var(--color-success-bg);
                }

                .team-card.unassigned {
                    border-style: dashed;
                }

                .team-role-icon {
                    font-size: 32px;
                    margin-bottom: var(--space-sm);
                }

                .team-role-label {
                    font-size: 13px;
                    font-weight: 600;
                    color: var(--text-muted);
                    margin-bottom: var(--space-md);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .team-member-info {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .team-member-info .member-name {
                    font-weight: 600;
                    color: var(--text-primary);
                    font-size: 15px;
                }

                .team-member-info .member-email {
                    font-size: 12px;
                    color: var(--text-muted);
                }

                .unassigned-label {
                    color: var(--text-hint);
                    font-style: italic;
                    font-size: 14px;
                }

                .team-empty-message {
                    text-align: center;
                    padding: var(--space-lg);
                    color: var(--text-muted);
                }

                .team-empty-message p {
                    margin: 0 0 var(--space-xs) 0;
                }
                
                .region-badge {
                    background: #dbeafe;
                    color: #1e40af;
                    padding: 0.25rem 0.75rem;
                    border-radius: 12px;
                    font-size: 0.8rem;
                    font-weight: 500;
                }
                
                .region-note {
                    color: #64748b;
                    font-size: 0.85rem;
                }
                
                .assignment-progress {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                    margin: 1rem 0 1.5rem;
                    padding: 1rem;
                    background: #f8fafc;
                    border-radius: 12px;
                }
                
                .progress-step {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 0.25rem;
                }
                
                .progress-step .step-number {
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    background: #e2e8f0;
                    color: #64748b;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 600;
                }
                
                .progress-step .step-label {
                    font-size: 0.75rem;
                    color: #64748b;
                }
                
                .progress-step.completed .step-number {
                    background: #22c55e;
                    color: white;
                }
                
                .progress-step.current .step-number {
                    background: #3b82f6;
                    color: white;
                    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
                }
                
                .progress-line {
                    width: 40px;
                    height: 2px;
                    background: #e2e8f0;
                }
                
                .role-step {
                    font-size: 0.7rem;
                    background: #e2e8f0;
                    color: #64748b;
                    padding: 0.125rem 0.5rem;
                    border-radius: 4px;
                    margin-right: 0.5rem;
                }
                
                .assigned-badge {
                    background: #dcfce7;
                    color: #166534;
                    padding: 0.125rem 0.5rem;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    margin-left: 0.5rem;
                }
                
                .locked-badge {
                    background: #fef3c7;
                    color: #92400e;
                    padding: 0.125rem 0.5rem;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    margin-left: 0.5rem;
                }

                .modal-lg {
                    max-width: 600px;
                }

                .team-form-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: var(--space-md);
                }

                .no-users-hint {
                    display: block;
                    margin-top: var(--space-xs);
                    font-size: 12px;
                    color: var(--color-warning);
                }

                /* Capacity Assignment Styles */
                .modal-xl {
                    max-width: 900px;
                    max-height: 90vh;
                    overflow-y: auto;
                }

                .workload-estimate {
                    background: var(--bg-secondary);
                    border-radius: var(--radius-md);
                    padding: var(--space-md);
                    margin-bottom: var(--space-lg);
                }

                .workload-estimate h4 {
                    margin: 0 0 var(--space-sm) 0;
                    font-size: 14px;
                    color: var(--text-secondary);
                }

                .workload-badges {
                    display: flex;
                    gap: var(--space-sm);
                    flex-wrap: wrap;
                }

                .workload-badge {
                    padding: 4px 10px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                    font-size: 12px;
                    color: var(--text-primary);
                }

                .workload-badge.role {
                    background: var(--color-info-bg);
                    color: var(--color-info);
                }

                .role-assignment-card {
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-md);
                    margin-bottom: var(--space-md);
                    transition: opacity 0.2s, background 0.2s;
                }
                
                .role-assignment-card.disabled {
                    opacity: 0.6;
                    background: #f8f9fa;
                }
                
                .role-assignment-card.assigned {
                    border-color: #22c55e;
                    background: #f0fdf4;
                }

                .role-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-md);
                }

                .role-header h4 {
                    margin: 0;
                    font-size: 15px;
                    color: var(--text-primary);
                }

                .role-header-actions {
                    display: flex;
                    gap: var(--space-sm);
                    align-items: center;
                }

                .btn-ai-suggest {
                    padding: 6px 12px;
                    background: linear-gradient(135deg, #7c3aed 0%, #9333ea 100%);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 12px;
                    cursor: pointer;
                }

                .btn-ai-suggest:disabled {
                    opacity: 0.7;
                }

                .required-hours {
                    font-size: 12px;
                    color: var(--text-muted);
                    background: var(--bg-tertiary);
                    padding: 4px 8px;
                    border-radius: var(--radius-full);
                }

                .ai-suggestions-panel {
                    background: linear-gradient(135deg, rgba(124, 58, 237, 0.05) 0%, rgba(147, 51, 234, 0.05) 100%);
                    border: 1px solid rgba(124, 58, 237, 0.2);
                    border-radius: var(--radius-md);
                    padding: var(--space-md);
                    margin-bottom: var(--space-md);
                }

                .ai-suggestions-panel.crunch {
                    background: var(--color-warning-bg);
                    border-color: var(--color-warning-border);
                }

                .capacity-crunch-alert h5 {
                    margin: 0 0 var(--space-sm) 0;
                    color: var(--color-warning);
                }

                .capacity-crunch-alert p {
                    margin: var(--space-xs) 0;
                    font-size: 13px;
                    color: var(--text-secondary);
                }

                .crunch-actions {
                    display: flex;
                    gap: var(--space-sm);
                    flex-wrap: wrap;
                    margin-top: var(--space-sm);
                }

                .crunch-action {
                    padding: 4px 8px;
                    background: white;
                    border: 1px solid var(--color-warning-border);
                    border-radius: var(--radius-sm);
                    font-size: 11px;
                    color: var(--color-warning);
                }

                .suggestion-summary {
                    margin: 0 0 var(--space-sm) 0;
                    font-size: 13px;
                    color: var(--text-secondary);
                }

                .suggestions-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-sm);
                }

                .suggestion-item {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    padding: var(--space-sm) var(--space-md);
                    background: white;
                    border-radius: var(--radius-md);
                    border: 1px solid var(--border-light);
                }

                .suggestion-main {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                }

                .suggestion-rank {
                    width: 24px;
                    height: 24px;
                    background: var(--accent-primary);
                    color: white;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 11px;
                    font-weight: bold;
                }

                .suggestion-info {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                    min-width: 120px;
                }

                .suggestion-name {
                    font-weight: 600;
                    color: var(--text-primary);
                    font-size: 13px;
                }

                .suggestion-region {
                    font-size: 11px;
                    color: var(--text-muted);
                }

                .suggestion-capacity {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                }

                .capacity-bar-mini {
                    width: 60px;
                    height: 6px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                    overflow: hidden;
                }

                .capacity-fill-mini {
                    height: 100%;
                    border-radius: var(--radius-full);
                    transition: width 0.3s ease;
                }

                .capacity-text {
                    font-size: 11px;
                    color: var(--text-muted);
                    white-space: nowrap;
                }

                .confidence-badge {
                    padding: 2px 6px;
                    background: var(--color-success-bg);
                    color: var(--color-success);
                    border-radius: var(--radius-full);
                    font-size: 10px;
                    font-weight: 600;
                }

                .btn-accept-suggestion {
                    padding: 6px 12px;
                    background: var(--color-success);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-size: 12px;
                    cursor: pointer;
                }

                .btn-accept-suggestion:hover {
                    background: #059669;
                }

                .capacity-user-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--space-sm);
                    max-height: 200px;
                    overflow-y: auto;
                }

                .capacity-user-item {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    padding: var(--space-sm) var(--space-md);
                    background: var(--bg-primary);
                    border: 2px solid var(--border-light);
                    border-radius: var(--radius-md);
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }

                .capacity-user-item:hover {
                    border-color: var(--accent-primary);
                }

                .capacity-user-item.selected {
                    border-color: var(--color-success);
                    background: var(--color-success-bg);
                }

                .capacity-user-item.not-recommended {
                    opacity: 0.7;
                }

                .capacity-user-item .user-info {
                    min-width: 140px;
                }

                .capacity-user-item .user-name {
                    display: block;
                    font-weight: 500;
                    color: var(--text-primary);
                    font-size: 13px;
                }

                .capacity-user-item .user-region {
                    display: block;
                    font-size: 11px;
                    color: var(--text-muted);
                }

                .user-capacity {
                    flex: 1;
                }

                .capacity-bar {
                    width: 100%;
                    height: 8px;
                    background: var(--bg-tertiary);
                    border-radius: var(--radius-full);
                    overflow: hidden;
                    margin-bottom: 4px;
                }

                .capacity-fill {
                    height: 100%;
                    border-radius: var(--radius-full);
                    transition: width 0.3s ease;
                }

                .capacity-details {
                    display: flex;
                    justify-content: space-between;
                    font-size: 11px;
                }

                .hours-available {
                    color: var(--color-success);
                }

                .utilization {
                    color: var(--text-muted);
                }

                .capacity-status {
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    min-width: 70px;
                    text-align: center;
                }

                .recommended-badge {
                    padding: 2px 8px;
                    background: var(--color-success-bg);
                    color: var(--color-success);
                    border-radius: var(--radius-full);
                    font-size: 10px;
                    font-weight: 600;
                }

                .selected-indicator {
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

                /* My Capacity Section */
                .my-capacity-section {
                    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    margin-bottom: var(--space-xl);
                    border: 1px solid #bae6fd;
                }

                .my-capacity-section h2 {
                    margin: 0 0 var(--space-md) 0;
                    color: #0369a1;
                    font-size: 18px;
                }

                .capacity-cards {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: var(--space-md);
                }

                .capacity-card {
                    background: white;
                    border-radius: var(--radius-md);
                    padding: var(--space-md);
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                }

                .capacity-card.available {
                    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
                    border: 1px solid #86efac;
                }

                .capacity-icon {
                    width: 48px;
                    height: 48px;
                    border-radius: 50%;
                    background: #e0f2fe;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                }

                .capacity-card.available .capacity-icon {
                    background: #bbf7d0;
                }

                .capacity-info {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .capacity-label {
                    font-size: 12px;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .capacity-value {
                    font-size: 16px;
                    font-weight: 600;
                    color: var(--text-primary);
                }

                /* Executive Summary Section */
                .executive-summary {
                    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                    margin-bottom: var(--space-xl);
                    border: 1px solid #fbbf24;
                }

                .executive-summary h2 {
                    margin: 0 0 var(--space-md) 0;
                    color: #92400e;
                    font-size: 18px;
                }

                .summary-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: var(--space-md);
                }

                .summary-card {
                    background: white;
                    border-radius: var(--radius-md);
                    padding: var(--space-md);
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                }

                .summary-icon {
                    width: 48px;
                    height: 48px;
                    border-radius: 50%;
                    background: #fef3c7;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                }

                .summary-content {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .summary-label {
                    font-size: 12px;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .summary-value {
                    font-size: 18px;
                    font-weight: 600;
                    color: var(--text-primary);
                }

                .executive-note {
                    margin-top: var(--space-md);
                    padding: var(--space-sm) var(--space-md);
                    background: rgba(255, 255, 255, 0.7);
                    border-radius: var(--radius-md);
                    font-size: 14px;
                    color: #78350f;
                }

                .executive-note p {
                    margin: 0;
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

                    .test-tabs {
                        flex-wrap: wrap;
                    }

                    .defect-dashboard {
                        grid-template-columns: repeat(2, 1fr);
                    }

                    .scenarios-grid {
                        grid-template-columns: 1fr;
                    }

                    .team-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }

                    .team-form-grid {
                        grid-template-columns: 1fr;
                    }

                    .modal-xl {
                        max-width: 100%;
                        margin: var(--space-sm);
                    }

                    .suggestion-main {
                        flex-wrap: wrap;
                    }

                    .capacity-user-item {
                        flex-wrap: wrap;
                    }

                    .capacity-user-item .user-info {
                        min-width: 100%;
                    }

                    .user-capacity {
                        width: 100%;
                    }

                    .capacity-cards {
                        grid-template-columns: 1fr;
                    }

                    .summary-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
        }
      `}</style>
        </div>
    );
}
