'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { configurationAPI, configAPI, API_BASE_URL } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import { Dialog } from '@/components/ui/dialog';
import PageHeader from '@/components/PageHeader';

type ConfigTab = 'template_registry' | 'sla' | 'thresholds' | 'preview_strategy' | 'hitl_gates' | 'learning';
type TemplateDetailSubTab = 'overview' | 'preview' | 'validation' | 'versions' | 'blueprint' | 'performance' | 'evolution';

interface TemplateRegistry {
    id: string;
    name: string;
    repo_url?: string | null;
    default_branch?: string | null;
    description?: string | null;
    intent?: string | null;
    features_json?: string[];
    preview_url?: string | null;
    preview_status?: string | null;
    preview_last_generated_at?: string | null;
    preview_error?: string | null;
    preview_thumbnail_url?: string | null;
    source_type?: 'ai' | 'git' | string;
    is_active: boolean;
    is_published: boolean;
    category?: string | null;
    style?: string | null;
    feature_tags_json?: string[];
    status?: string;
    is_default?: boolean;
    is_recommended?: boolean;
    repo_path?: string | null;
    pages_json?: Array<{ slug?: string; title?: string; sections?: unknown[] }>;
    required_inputs_json?: unknown[];
    optional_inputs_json?: unknown[];
    default_config_json?: Record<string, unknown>;
    rules_json?: unknown[];
    validation_results_json?: Record<string, unknown>;
    validation_status?: string | null;
    validation_last_run_at?: string | null;
    validation_hash?: string | null;
    version?: number;
    changelog?: string | null;
    parent_template_id?: string | null;
    performance_metrics_json?: Record<string, unknown> | null;
    is_deprecated?: boolean;
    blueprint_json?: Record<string, unknown> | null;
    blueprint_schema_version?: number | null;
    blueprint_quality_json?: Record<string, unknown> | null;
    blueprint_hash?: string | null;
    blueprint_status?: string | null;
    blueprint_last_run_id?: string | null;
    blueprint_updated_at?: string | null;
    meta_json?: Record<string, unknown> | null;
}

/** Normalize API error detail (string, array of {msg}, or object) to a single string so it's safe to render in JSX. */
function formatApiErrorDetail(detail: unknown): string {
    if (detail == null) return '';
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((x: { msg?: string; message?: string }) => x?.msg ?? x?.message ?? JSON.stringify(x)).join('. ');
    if (typeof detail === 'object') return (detail as { msg?: string; message?: string }).msg ?? (detail as { message?: string }).message ?? JSON.stringify(detail);
    return String(detail);
}

function EvolutionTab({ templateId }: { templateId: string }) {
    const [proposals, setProposals] = useState<Array<{ id: string; proposal_json: any; status: string; created_at: string | null; rejection_reason?: string }>>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [evolving, setEvolving] = useState<string | null>(null);
    useEffect(() => {
        configurationAPI.getEvolutionProposals(templateId)
            .then((r: any) => { setProposals(r.data?.proposals || []); setError(''); })
            .catch((e: any) => { setError(e.response?.data?.detail || 'Failed to load'); setProposals([]); })
            .finally(() => setLoading(false));
    }, [templateId]);
    const handlePropose = () => {
        setLoading(true);
        configurationAPI.proposeEvolution(templateId)
            .then(() => configurationAPI.getEvolutionProposals(templateId))
            .then((r: any) => setProposals(r.data?.proposals || []))
            .catch((e: any) => setError(e.response?.data?.detail || 'Propose failed'))
            .finally(() => setLoading(false));
    };
    const handleEvolve = (proposalId: string, approve: boolean, rejectionReason?: string) => {
        setEvolving(proposalId);
        configurationAPI.evolveTemplate(templateId, { proposal_id: proposalId, approve, rejection_reason: rejectionReason })
            .then(() => configurationAPI.getEvolutionProposals(templateId))
            .then((r: any) => setProposals(r.data?.proposals || []))
            .catch((e: any) => setError(e.response?.data?.detail || 'Action failed'))
            .finally(() => setEvolving(null));
    };
    if (loading && proposals.length === 0) return <div style={{ padding: 16 }}>Loading proposals…</div>;
    return (
        <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', fontSize: '13px' }}>
            <p style={{ margin: '0 0 12px', color: '#64748b' }}>Propose evolution suggests template improvements based on usage and quality metrics. After you approve a proposal, changes can be applied to the template. This runs after templates are in use and complements the create → preview → validate → publish flow.</p>
            {error && <p style={{ color: '#dc2626', marginBottom: 12 }}>{error}</p>}
            <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
                <button type="button" onClick={handlePropose} disabled={loading} style={{ padding: '6px 12px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '6px', cursor: loading ? 'not-allowed' : 'pointer' }}>Propose evolution</button>
            </div>
            <h4 style={{ margin: '0 0 8px' }}>Proposals</h4>
            {proposals.length === 0 ? <p style={{ margin: 0, color: '#64748b' }}>No proposals. Click &quot;Propose evolution&quot; to generate one (rate limit: 1 per week).</p> : (
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {proposals.map((p) => (
                        <li key={p.id} style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 12, marginBottom: 8 }}>
                            <div><strong>Status:</strong> {p.status} · {p.created_at ? new Date(p.created_at).toLocaleString() : ''}</div>
                            {p.proposal_json?.change_summary && <div style={{ marginTop: 6 }}>{p.proposal_json.change_summary}</div>}
                            {p.rejection_reason && <div style={{ marginTop: 4, color: '#64748b' }}>Rejection: {p.rejection_reason}</div>}
                            {p.status === 'pending' && (
                                <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                                    <button type="button" onClick={() => handleEvolve(p.id, true)} disabled={!!evolving} style={{ padding: '4px 10px', background: '#10b981', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Approve</button>
                                    <button type="button" onClick={() => handleEvolve(p.id, false, 'Rejected by user')} disabled={!!evolving} style={{ padding: '4px 10px', background: '#ef4444', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Reject</button>
                                </div>
                            )}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

function LearningProposalsPanel() {
    const [proposals, setProposals] = useState<Array<{ policy_key: string; current_value: any; suggested_value: any; rationale: string }>>([]);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState('');
    useEffect(() => {
        configAPI.getLearningProposals()
            .then((r: any) => { setProposals(r.data?.proposals || []); setError(''); })
            .catch(() => { setProposals([]); })
            .finally(() => setLoading(false));
    }, []);
    const handleRun = () => {
        setRunning(true);
        configAPI.runTemplateMetrics()
            .then(() => configAPI.runLearningProposals())
            .then((r: any) => setProposals(r.data?.proposals || []))
            .catch((e: any) => setError(e.response?.data?.detail || 'Run failed'))
            .finally(() => setRunning(false));
    };
    const handleApply = (index: number) => {
        configAPI.applyLearningProposal(index)
            .then(() => configAPI.getLearningProposals())
            .then((r: any) => setProposals(r.data?.proposals || []))
            .catch((e: any) => setError(e.response?.data?.detail || 'Apply failed'));
    };
    if (loading && proposals.length === 0) return <div style={{ padding: 16 }}>Loading…</div>;
    return (
        <div>
            {error && <p style={{ color: '#dc2626', marginBottom: 12 }}>{error}</p>}
            <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
                <button type="button" onClick={handleRun} disabled={running} style={{ padding: '8px 16px', background: '#2563eb', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>{running ? 'Running…' : 'Run template metrics & learning'}</button>
            </div>
            <h4 style={{ margin: '0 0 8px' }}>Proposals</h4>
            {proposals.length === 0 ? <p style={{ margin: 0, color: '#64748b' }}>No proposals. Click &quot;Run template metrics &amp; learning&quot; to compute.</p> : (
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {proposals.map((p, i) => (
                        <li key={i} style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 12, marginBottom: 8 }}>
                            <div><strong>{p.policy_key}</strong></div>
                            <div style={{ marginTop: 4 }}>Current: {String(p.current_value)} → Suggested: {String(p.suggested_value)}</div>
                            <div style={{ marginTop: 4, color: '#64748b', fontSize: 12 }}>{p.rationale}</div>
                            <button type="button" onClick={() => handleApply(i)} style={{ marginTop: 8, padding: '4px 10px', background: '#10b981', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Apply</button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

interface SLAConfig {
    id: string;
    stage: string;
    default_days: number;
    warning_threshold_days: number;
    critical_threshold_days: number;
    description: string | null;
    is_active: boolean;
}

export default function ConfigurationPage() {
    const router = useRouter();
    const [user, setUser] = useState<any>(null);
    const [templates, setTemplates] = useState<TemplateRegistry[]>([]);
    const [defaultTemplateId, setDefaultTemplateId] = useState('');
    const [slaDrafts, setSlaDrafts] = useState<SLAConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [infoBannerDismissed, setInfoBannerDismissed] = useState(false);
    const [globalStageGates, setGlobalStageGates] = useState({
        onboarding: false,
        assignment: false,
        build: false,
        test: false,
        defect_validation: false,
        complete: false,
    });
    const [savingGates, setSavingGates] = useState(false);
    const [savingSla, setSavingSla] = useState(false);
    const [globalThresholds, setGlobalThresholds] = useState({
        build_pass_score: 98,
        qa_pass_score: 98,
        axe_max_critical: 0,
        lighthouse_min: {
            performance: 0.5,
            accessibility: 0.8,
            seo: 0.8,
            best_practices: 0.8,
        },
    });
    const [savingThresholds, setSavingThresholds] = useState(false);
    const [previewStrategy, setPreviewStrategy] = useState('zip_only');
    const [savingPreview, setSavingPreview] = useState(false);
    const [savingDefaultTemplate, setSavingDefaultTemplate] = useState(false);
    const [configVersions, setConfigVersions] = useState<Record<string, number | null>>({
        default_template_id: null,
        global_stage_gates_json: null,
        global_thresholds_json: null,
        preview_strategy: null,
    });
    const [showAddForm, setShowAddForm] = useState(false);
    const [templateSource, setTemplateSource] = useState<'ai' | 'git'>('ai');
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [previewModalOpen, setPreviewModalOpen] = useState(false);
    const [previewTemplate, setPreviewTemplate] = useState<TemplateRegistry | null>(null);
    const [previewPolling, setPreviewPolling] = useState(false);
    const [blueprintJobPolling, setBlueprintJobPolling] = useState(false);
    const [blueprintStatusData, setBlueprintStatusData] = useState<{ blueprint_status?: string; latest_run?: { run_id: string; status: string; error_message?: string }; blueprint_preview?: { pages_count: number } } | null>(null);
    const [workerHealthy, setWorkerHealthy] = useState<boolean | null>(null);
    const [blueprintRunDetails, setBlueprintRunDetails] = useState<Record<string, unknown> | null>(null);
    const [validationJobPolling, setValidationJobPolling] = useState(false);

    const [newTemplate, setNewTemplate] = useState({
        name: '',
        repo_url: '',
        default_branch: 'main',
        description: '',
        intent: '',
        features_input: '',
    });
    const [activeConfigTab, setActiveConfigTab] = useState<ConfigTab>('template_registry');
    const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
    const [templateDetailSubTab, setTemplateDetailSubTab] = useState<TemplateDetailSubTab>('overview');
    const [selectedStructurePageIndex, setSelectedStructurePageIndex] = useState<number | null>(0);
    const [validationToast, setValidationToast] = useState<string | null>(null);
    const [copyValidationLoading, setCopyValidationLoading] = useState(false);
    const [seoValidationLoading, setSeoValidationLoading] = useState(false);
    const [imageUploadSectionKey, setImageUploadSectionKey] = useState('exterior');
    const [imageUploading, setImageUploading] = useState(false);
    const [fixBlueprintModalOpen, setFixBlueprintModalOpen] = useState(false);
    const [fixBlueprintLoading, setFixBlueprintLoading] = useState(false);
    const [fixBlueprintSuggestions, setFixBlueprintSuggestions] = useState<{ plain_language_summary: string; technical_details?: string | null; code_snippets?: Array<{ title: string; code: string }>; interim_actions?: string[] } | null>(null);
    const [fixBlueprintShowTechnical, setFixBlueprintShowTechnical] = useState(false);
    const [previewViewport, setPreviewViewport] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');

    useEffect(() => {
        configurationAPI.getSystemHealth().then((r: any) => {
            const d = r.data;
            setWorkerHealthy(d?.worker_healthy !== false);
        }).catch(() => setWorkerHealthy(false));
    }, []);

    useEffect(() => {
        if (!selectedTemplateId || templateDetailSubTab !== 'blueprint') return;
        configurationAPI.getTemplateBlueprintStatus(selectedTemplateId)
            .then((r: any) => setBlueprintStatusData(r.data))
            .catch(() => setBlueprintStatusData(null));
    }, [selectedTemplateId, templateDetailSubTab]);

    useEffect(() => {
        setSelectedStructurePageIndex(0);
    }, [selectedTemplateId]);

    const [showCreateWizard, setShowCreateWizard] = useState(false);
    const [templateListFilters, setTemplateListFilters] = useState<{ q?: string; status?: string; category?: string; style?: string; tag?: string }>({});
    const [wizardStep, setWizardStep] = useState(1);
    const [wizardForm, setWizardForm] = useState<{
        source: 'ai' | 'git'; name: string; description: string; category: string; style: string; feature_tags: string; intent: string;
        repo_url: string; repo_branch: string; repo_path: string; preset: string;
        industry: string; image_prompts: Record<string, string>; validate_responsiveness: boolean;
    }>({
        source: 'ai', name: '', description: '', category: '', style: '', feature_tags: '', intent: '',
        repo_url: '', repo_branch: 'main', repo_path: '', preset: '',
        industry: 'real_estate',
        image_prompts: { exterior: '', interior: '', lifestyle: '', people: '', neighborhood: '' },
        validate_responsiveness: true,
    });

    type SectionKey = 'templates_default' | 'sla_config' | 'thresholds' | 'preview_strategy' | 'hitl_gates';
    type SectionState = {
        initialValue: any;
        currentValue: any;
        isDirty: boolean;
        validationErrors?: string[];
        initialized: boolean;
    };
    const [sectionState, setSectionState] = useState<Record<SectionKey, SectionState>>({
        templates_default: { initialValue: null, currentValue: null, isDirty: false, initialized: false },
        sla_config: { initialValue: null, currentValue: null, isDirty: false, initialized: false },
        thresholds: { initialValue: null, currentValue: null, isDirty: false, initialized: false },
        preview_strategy: { initialValue: null, currentValue: null, isDirty: false, initialized: false },
        hitl_gates: { initialValue: null, currentValue: null, isDirty: false, initialized: false },
    });

    const isDeepEqual = (a: any, b: any) => JSON.stringify(a) === JSON.stringify(b);

    const setSectionInitial = (section: SectionKey, initialValue: any, currentValue?: any) => {
        setSectionState(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                initialValue,
                currentValue: typeof currentValue === 'undefined' ? initialValue : currentValue,
                isDirty: false,
                initialized: true,
            },
        }));
    };

    const setSectionCurrent = (section: SectionKey, currentValue: any) => {
        setSectionState(prev => {
            if (!prev[section].initialized) return prev;
            const isDirty = !isDeepEqual(currentValue, prev[section].initialValue);
            return {
                ...prev,
                [section]: {
                    ...prev[section],
                    currentValue,
                    isDirty,
                    validationErrors: [],
                },
            };
        });
    };

    const markDirty = (section: SectionKey) => {
        setSectionState(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                isDirty: true,
                initialized: true,
            },
        }));
    };

    const resetSection = (section: SectionKey) => {
        const initialValue = sectionState[section]?.initialValue;
        if (section === 'templates_default') setDefaultTemplateId(initialValue || '');
        if (section === 'sla_config') setSlaDrafts(initialValue || []);
        if (section === 'thresholds') setGlobalThresholds(initialValue || globalThresholds);
        if (section === 'preview_strategy') setPreviewStrategy(initialValue || 'zip_only');
        if (section === 'hitl_gates') {
            setGlobalStageGates(
                initialValue || {
                    onboarding: false,
                    assignment: false,
                    build: false,
                    test: false,
                    defect_validation: false,
                    complete: false,
                }
            );
        }
        setSectionState(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                currentValue: initialValue,
                isDirty: false,
                initialized: true,
            },
        }));
    };

    const getDirtySections = () => {
        return (Object.keys(sectionState) as SectionKey[]).filter((key) => sectionState[key]?.isDirty);
    };

    const renderDirtyDot = (section: SectionKey) => {
        if (!sectionState[section]?.isDirty) return null;
        return (
            <span
                title="Unsaved changes"
                aria-label="Unsaved changes"
                style={{ width: '8px', height: '8px', borderRadius: '999px', background: '#f59e0b', display: 'inline-block' }}
            />
        );
    };

    const getSectionError = (section: SectionKey) => {
        const errors = sectionState[section]?.validationErrors || [];
        return errors.length > 0 ? errors[0] : '';
    };

    const renderStatusChip = (section: SectionKey) => {
        const error = getSectionError(section);
        const isSaving =
            (section === 'preview_strategy' && savingPreview) ||
            (section === 'templates_default' && savingDefaultTemplate) ||
            (section === 'sla_config' && savingSla) ||
            (section === 'thresholds' && savingThresholds) ||
            (section === 'hitl_gates' && savingGates);
        if (error) {
            return (
                <button
                    type="button"
                    onClick={() => window.alert(error)}
                    style={{
                        padding: '2px 8px',
                        borderRadius: '999px',
                        border: '1px solid #fecaca',
                        background: '#fee2e2',
                        color: '#991b1b',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer',
                    }}
                    title="Click to view error"
                >
                    Error
                </button>
            );
        }
        if (isSaving) {
            return (
                <span
                    style={{
                        padding: '2px 8px',
                        borderRadius: '999px',
                        border: '1px solid #bfdbfe',
                        background: '#eff6ff',
                        color: '#1d4ed8',
                        fontSize: '11px',
                        fontWeight: 600,
                    }}
                >
                    Saving...
                </span>
            );
        }
        if (sectionState[section]?.initialized && !sectionState[section]?.isDirty) {
            return (
                <span
                    style={{
                        padding: '2px 8px',
                        borderRadius: '999px',
                        border: '1px solid #bbf7d0',
                        background: '#ecfdf5',
                        color: '#047857',
                        fontSize: '11px',
                        fontWeight: 600,
                    }}
                >
                    Saved
                </span>
            );
        }
        return null;
    };

    const sectionLabels: Record<SectionKey, string> = {
        templates_default: 'Templates',
        sla_config: 'SLA',
        thresholds: 'Thresholds',
        preview_strategy: 'Preview Strategy',
        hitl_gates: 'HITL Gates',
    };

    const handleDiscardAll = () => {
        getDirtySections().forEach((section) => resetSection(section));
    };

    const setValidationErrors = (section: SectionKey, errors: string[]) => {
        setSectionState(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                validationErrors: errors,
            },
        }));
    };

    const validatePreviewStrategy = () => {
        const allowed = ['zip_only', 'serve_static_preview'];
        if (!allowed.includes(previewStrategy)) {
            return `Preview strategy must be one of: ${allowed.join(', ')}`;
        }
        return '';
    };

    const validateDefaultTemplate = () => {
        if (!defaultTemplateId) return '';
        const exists = templates.some(t => t.id === defaultTemplateId);
        if (!exists) return 'Default template must exist in the registry.';
        return '';
    };

    const validateSla = () => {
        const invalid = slaDrafts.find(
            item =>
                Number.isNaN(item.default_days) ||
                Number.isNaN(item.warning_threshold_days) ||
                Number.isNaN(item.critical_threshold_days) ||
                item.default_days < 0 ||
                item.warning_threshold_days < 0 ||
                item.critical_threshold_days < 0
        );
        if (invalid) {
            return `SLA values must be non-negative for stage ${invalid.stage}.`;
        }
        return '';
    };

    const validateThresholds = () => {
        const values = [
            globalThresholds.build_pass_score,
            globalThresholds.qa_pass_score,
            globalThresholds.axe_max_critical,
            globalThresholds.lighthouse_min.performance,
            globalThresholds.lighthouse_min.accessibility,
            globalThresholds.lighthouse_min.seo,
            globalThresholds.lighthouse_min.best_practices,
        ];
        if (values.some(v => Number.isNaN(v))) return 'Threshold values must be numbers.';
        if (
            globalThresholds.build_pass_score < 0 ||
            globalThresholds.qa_pass_score < 0 ||
            globalThresholds.axe_max_critical < 0
        ) {
            return 'Threshold values must be non-negative.';
        }
        return '';
    };

    const validateGates = () => '';

    const conflictMessage = 'Config was changed by another user. Reload to continue.';

    const isConflictError = (err: any) => err?.response?.status === 409;

    const savePreviewStrategy = async () => {
        if (!canEditPreviewStrategy) throw new Error('Only Admin can change this setting.');
        const response = await configAPI.update('preview_strategy', previewStrategy, configVersions.preview_strategy);
        if (typeof response.data?.config_version === 'number') {
            setConfigVersions(prev => ({ ...prev, preview_strategy: response.data.config_version }));
        }
        setSectionInitial('preview_strategy', previewStrategy);
    };

    const saveDefaultTemplate = async (value?: string) => {
        if (!canEditTemplates) throw new Error('Only Admin can change this setting.');
        const nextValue = typeof value === 'string' ? value : defaultTemplateId;
        setSavingDefaultTemplate(true);
        try {
            const response = await configAPI.update('default_template_id', nextValue, configVersions.default_template_id);
            if (typeof response.data?.config_version === 'number') {
                setConfigVersions(prev => ({ ...prev, default_template_id: response.data.config_version }));
            }
            setSectionInitial('templates_default', nextValue);
        } finally {
            setSavingDefaultTemplate(false);
        }
    };

    const saveSlaConfigs = async () => {
        if (!canEditSla) throw new Error('Only Admin can change this setting.');
        await Promise.all(
            slaDrafts.map(config =>
                configurationAPI.updateSLAConfig(config.stage, {
                    default_days: config.default_days,
                    warning_threshold_days: config.warning_threshold_days,
                    critical_threshold_days: config.critical_threshold_days,
                    description: config.description,
                    is_active: config.is_active,
                })
            )
        );
        setSectionInitial('sla_config', slaDrafts);
    };

    const saveThresholds = async () => {
        if (!canEditThresholds) throw new Error('Only Admin can change this setting.');
        const response = await configAPI.update('global_thresholds_json', globalThresholds, configVersions.global_thresholds_json);
        if (typeof response.data?.config_version === 'number') {
            setConfigVersions(prev => ({ ...prev, global_thresholds_json: response.data.config_version }));
        }
        setSectionInitial('thresholds', globalThresholds);
    };

    const saveGates = async () => {
        if (!canEditGates) throw new Error('Only Admin can change this setting.');
        const response = await configAPI.update('global_stage_gates_json', globalStageGates, configVersions.global_stage_gates_json);
        if (typeof response.data?.config_version === 'number') {
            setConfigVersions(prev => ({ ...prev, global_stage_gates_json: response.data.config_version }));
        }
        setSectionInitial('hitl_gates', globalStageGates);
    };

    const handleSaveAll = async () => {
        setError('');
        setSuccess('');
        const dirty = getDirtySections();
        const ordered: SectionKey[] = [
            'preview_strategy',
            'templates_default',
            'sla_config',
            'thresholds',
            'hitl_gates',
        ];
        for (const section of ordered) {
            if (!dirty.includes(section)) continue;
            let validationError = '';
            if (section === 'preview_strategy') validationError = validatePreviewStrategy();
            if (section === 'templates_default') validationError = validateDefaultTemplate();
            if (section === 'sla_config') validationError = validateSla();
            if (section === 'thresholds') validationError = validateThresholds();
            if (section === 'hitl_gates') validationError = validateGates();
            if (validationError) {
                setValidationErrors(section, [validationError]);
                setError(`Failed to save ${sectionLabels[section]}: ${validationError}`);
                return;
            }
            try {
                if (section === 'preview_strategy') await savePreviewStrategy();
                if (section === 'templates_default') await saveDefaultTemplate();
                if (section === 'sla_config') await saveSlaConfigs();
                if (section === 'thresholds') await saveThresholds();
                if (section === 'hitl_gates') await saveGates();
            } catch (err: any) {
                if (isConflictError(err)) {
                    setValidationErrors(section, [conflictMessage]);
                    setError(conflictMessage);
                    return;
                }
                const message = err.response?.data?.detail || err.message || 'Unknown error';
                setValidationErrors(section, [message]);
                setError(`Failed to save ${sectionLabels[section]}: ${message}`);
                return;
            }
        }
        if (dirty.length > 0) {
            setSuccess('Saved configuration');
        }
    };
    const isAdmin = user?.role === 'ADMIN';
    const isManager = user?.role === 'MANAGER';
    const canEditTemplates = isAdmin;
    const canEditSla = isAdmin || isManager;
    const canEditThresholds = isAdmin;
    const canEditPreviewStrategy = isAdmin;
    const canEditGates = isAdmin || isManager;

    useEffect(() => {
        const currentUser = getCurrentUser();
        if (!currentUser || !['ADMIN', 'MANAGER'].includes(currentUser.role)) {
            router.push('/projects');
            return;
        }
        setUser(currentUser);
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        setError('');
        try {
            const results = await Promise.allSettled([
                configurationAPI.getTemplates(),
                configurationAPI.getSLAConfigs(),
            ]);
            const templatesRes = results[0].status === 'fulfilled' ? results[0].value : null;
            const slaRes = results[1].status === 'fulfilled' ? results[1].value : null;
            const templatesData = templatesRes ? templatesRes.data : [];
            const slaData = slaRes ? slaRes.data : [];
            if (templatesRes) {
                const list = Array.isArray(templatesData) ? templatesData : [];
                const byId = new Map(list.map((t: TemplateRegistry) => [t.id, t]));
                setTemplates(Array.from(byId.values()));
            }
            if (slaRes) setSlaDrafts(slaData);
            if (!templatesRes || !slaRes) {
                setError('Some configuration data failed to load');
            }
            let defaultTemplateValue = defaultTemplateId || '';
            let gatesValue = globalStageGates;
            let thresholdsValue = globalThresholds;
            let previewValue = previewStrategy;
            try {
                const configRes = await configAPI.get('default_template_id');
                if (configRes.data?.value_json) {
                    defaultTemplateValue = configRes.data.value_json;
                    setDefaultTemplateId(defaultTemplateValue);
                }
                if (typeof configRes.data?.config_version === 'number') {
                    setConfigVersions(prev => ({ ...prev, default_template_id: configRes.data.config_version }));
                }
            } catch {
                // ignore missing config
            }
            try {
                const gatesRes = await configAPI.get('global_stage_gates_json');
                if (gatesRes.data?.value_json) {
                    gatesValue = {
                        onboarding: !!gatesRes.data.value_json.onboarding,
                        assignment: !!gatesRes.data.value_json.assignment,
                        build: !!gatesRes.data.value_json.build,
                        test: !!gatesRes.data.value_json.test,
                        defect_validation: !!gatesRes.data.value_json.defect_validation,
                        complete: !!gatesRes.data.value_json.complete,
                    };
                }
                if (typeof gatesRes.data?.config_version === 'number') {
                    setConfigVersions(prev => ({ ...prev, global_stage_gates_json: gatesRes.data.config_version }));
                }
            } catch {
                // ignore missing config
            }
            try {
                const thresholdsRes = await configAPI.get('global_thresholds_json');
                if (thresholdsRes.data?.value_json) {
                    const value = thresholdsRes.data.value_json;
                    thresholdsValue = {
                        build_pass_score: Number(value.build_pass_score ?? 98),
                        qa_pass_score: Number(value.qa_pass_score ?? 98),
                        axe_max_critical: Number(value.axe_max_critical ?? 0),
                        lighthouse_min: {
                            performance: Number(value.lighthouse_min?.performance ?? 0.5),
                            accessibility: Number(value.lighthouse_min?.accessibility ?? 0.8),
                            seo: Number(value.lighthouse_min?.seo ?? 0.8),
                            best_practices: Number(value.lighthouse_min?.best_practices ?? 0.8),
                        },
                    };
                }
                if (typeof thresholdsRes.data?.config_version === 'number') {
                    setConfigVersions(prev => ({ ...prev, global_thresholds_json: thresholdsRes.data.config_version }));
                }
            } catch {
                // ignore missing config
            }
            try {
                const previewRes = await configAPI.get('preview_strategy');
                if (previewRes.data?.value_json) {
                    previewValue = String(previewRes.data.value_json);
                }
                if (typeof previewRes.data?.config_version === 'number') {
                    setConfigVersions(prev => ({ ...prev, preview_strategy: previewRes.data.config_version }));
                }
            } catch {
                // ignore missing config
            }
            setGlobalStageGates(gatesValue);
            setGlobalThresholds(thresholdsValue);
            setPreviewStrategy(previewValue);
            setSectionInitial('templates_default', defaultTemplateValue);
            setSectionInitial('sla_config', slaData);
            setSectionInitial('hitl_gates', gatesValue);
            setSectionInitial('thresholds', thresholdsValue);
            setSectionInitial('preview_strategy', previewValue);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        setSectionCurrent('templates_default', defaultTemplateId);
    }, [defaultTemplateId]);

    useEffect(() => {
        setSectionCurrent('sla_config', slaDrafts);
    }, [slaDrafts]);

    useEffect(() => {
        setSectionCurrent('thresholds', globalThresholds);
    }, [globalThresholds]);

    useEffect(() => {
        setSectionCurrent('preview_strategy', previewStrategy);
    }, [previewStrategy]);

    useEffect(() => {
        setSectionCurrent('hitl_gates', globalStageGates);
    }, [globalStageGates]);

    const handleAddTemplate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canEditTemplates) {
            setError('Only Admin can change this setting.');
            return;
        }
        setError('');
        setSuccess('');
        try {
            const features = newTemplate.features_input
                .split(',')
                .map(item => item.trim())
                .filter(Boolean);
            const payload: any = {
                name: newTemplate.name,
                description: newTemplate.description || null,
                intent: newTemplate.intent || null,
                features_json: features,
                source_type: templateSource,
            };
            if (templateSource === 'git') {
                payload.repo_url = newTemplate.repo_url;
                payload.default_branch = newTemplate.default_branch || 'main';
            }
            await configurationAPI.createTemplate(payload);
            setSuccess('Template added');
            setShowAddForm(false);
            setNewTemplate({ name: '', repo_url: '', default_branch: 'main', description: '', intent: '', features_input: '' });
            setTemplateSource('ai');
            setShowAdvanced(false);
            loadData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create template');
        }
    };

    const getTemplatePreviewUrl = (template: TemplateRegistry) => {
        const derivedSource = template.source_type || (template.repo_url ? 'git' : 'ai');
        if (template.preview_url) return template.preview_url;
        if (derivedSource === 'ai') return '';
        if (!template.repo_url) return '';
        const cleanedRepo = template.repo_url.replace(/\/$/, '');
        const branch = template.default_branch || 'main';
        if (cleanedRepo.includes('github.com') && !cleanedRepo.includes('/tree/')) {
            return `${cleanedRepo}/tree/${branch}`;
        }
        return cleanedRepo;
    };

    /** Use proxy URL for embedded preview and open-in-tab so in-preview navigation works (avoids 403 on S3 presigned). */
    const getPreviewIframeUrl = (template: TemplateRegistry) => {
        if ((template.preview_status || '') !== 'ready' || !template.id) return template.preview_url || '';
        const base = `${API_BASE_URL}/api/templates/${template.id}/preview/`;
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('access_token');
            if (token) return `${base}?access_token=${encodeURIComponent(token)}`;
        }
        return base;
    };

    const getPreviewStatusLabel = (template: TemplateRegistry) => {
        const derivedSource = template.source_type || (template.repo_url ? 'git' : 'ai');
        if (derivedSource === 'git' && !template.preview_url && template.repo_url) {
            return 'Ready';
        }
        const status = template.preview_status || 'not_generated';
        if (status === 'generating') return 'Generating';
        if (status === 'ready') return 'Ready';
        if (status === 'failed') return 'Failed';
        return 'Not generated';
    };

    const getPreviewStatusStyle = (status: string) => {
        if (status === 'Ready') return { background: '#ecfdf5', color: '#10b981' };
        if (status === 'Generating') return { background: '#eff6ff', color: '#2563eb' };
        if (status === 'Failed') return { background: '#fee2e2', color: '#ef4444' };
        return { background: '#f1f5f9', color: '#475569' };
    };

    const getPreviewModeLabel = () => {
        return previewStrategy === 'serve_static_preview' ? 'Static Preview' : 'Live Preview';
    };

    const updateTemplateInState = (updated: TemplateRegistry) => {
        setTemplates(prev => prev.map(t => (t.id === updated.id ? updated : t)));
        if (previewTemplate?.id === updated.id) {
            setPreviewTemplate(updated);
        }
    };

    function OverviewDescriptionEditor({ template, onSaved }: { template: TemplateRegistry; onSaved: (t: TemplateRegistry) => void }) {
        const [draft, setDraft] = useState(template.description || '');
        const [saving, setSaving] = useState(false);
        useEffect(() => {
            setDraft(template.description || '');
        }, [template.id, template.description]);
        const handleBlur = async () => {
            const trimmed = (draft || '').trim() || null;
            if (trimmed === (template.description || '').trim() || (trimmed === '' && !template.description)) return;
            setSaving(true);
            try {
                const res = await configurationAPI.updateTemplate(template.id, { description: trimmed });
                onSaved(res.data as TemplateRegistry);
            } catch {
                // error surfaced by parent
            } finally {
                setSaving(false);
            }
        };
        return (
            <div>
                <textarea
                    value={draft}
                    onChange={e => setDraft(e.target.value)}
                    onBlur={handleBlur}
                    placeholder="Short description for list and overview (saves when you leave the field)"
                    rows={2}
                    style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px', resize: 'vertical' }}
                />
                {saving && <span style={{ fontSize: '12px', color: '#64748b', marginLeft: '8px' }}>Saving…</span>}
            </div>
        );
    }

    const selectedTemplate = selectedTemplateId ? templates.find(t => t.id === selectedTemplateId) ?? null : null;
    const canPublishTemplate = (t: TemplateRegistry) =>
        (t.preview_status === 'ready') && ((t.validation_status || '') === 'passed') && ((t.status === 'validated') || (t.status === 'draft'));
    const filteredTemplates = React.useMemo(() => {
        let list = templates;
        const { q, status, category, style, tag } = templateListFilters;
        if (q?.trim()) {
            const lower = q.trim().toLowerCase();
            list = list.filter(t =>
                (t.name || '').toLowerCase().includes(lower) ||
                (t.description || '').toLowerCase().includes(lower)
            );
        }
        if (status) list = list.filter(t => (t.status || '') === status);
        if (category) list = list.filter(t => (t.category || '') === category);
        if (style) list = list.filter(t => (t.style || '') === style);
        if (tag) list = list.filter(t => (t.feature_tags_json || t.features_json || []).some((f: string) => (f || '').toLowerCase().includes(tag.toLowerCase())));
        return list;
    }, [templates, templateListFilters]);

    const handleDuplicateTemplate = async (t: TemplateRegistry) => {
        if (!canEditTemplates) return;
        try {
            const res = await configurationAPI.duplicateTemplate(t.id);
            setTemplates(prev => [res.data as TemplateRegistry, ...prev]);
            setSuccess('Template duplicated');
            setSelectedTemplateId((res.data as TemplateRegistry).id);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to duplicate');
        }
    };
    const handleValidateTemplate = async (t: TemplateRegistry) => {
        if (!canEditTemplates) return;
        try {
            const res = await configurationAPI.validateTemplate(t.id);
            const updated = await configurationAPI.getTemplate(t.id);
            updateTemplateInState(updated.data as TemplateRegistry);
            const passed = (res.data as { passed?: boolean }).passed;
            setValidationToast(passed ? 'Validation passed' : 'Validation completed (see results)');
            setTemplateDetailSubTab('validation');
        } catch (err: any) {
            setError(formatApiErrorDetail(err.response?.data?.detail) || 'Validation failed');
        }
    };
    const handlePublishTemplate = async (t: TemplateRegistry) => {
        if (!canEditTemplates || !canPublishTemplate(t)) return;
        try {
            const body = (t.status || '') !== 'validated' ? { admin_override: true } : undefined;
            await configurationAPI.publishTemplate(t.id, body);
            setSuccess('Template published');
            loadData();
        } catch (err: any) {
            setError(formatApiErrorDetail(err.response?.data?.detail) || 'Publish failed');
        }
    };
    const handleArchiveTemplate = async (t: TemplateRegistry) => {
        if (!canEditTemplates) return;
        if (!window.confirm(`Archive "${t.name}"? It will be hidden from clients.`)) return;
        try {
            await configurationAPI.archiveTemplate(t.id);
            setSuccess('Template archived');
            if (selectedTemplateId === t.id) setSelectedTemplateId(null);
            loadData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Archive failed');
        }
    };
    const handleSetDefaultTemplateFromCard = async (t: TemplateRegistry) => {
        try {
            await configurationAPI.setDefaultTemplate(t.id);
            setDefaultTemplateId(t.id);
            await saveDefaultTemplate(t.id);
            setSuccess('Default template set');
            loadData();
        } catch (err: any) {
            setError(formatApiErrorDetail(err.response?.data?.detail) || 'Set default failed');
        }
    };
    const handleSetRecommendedTemplate = async (t: TemplateRegistry, value: boolean) => {
        try {
            await configurationAPI.setRecommendedTemplate(t.id, value);
            updateTemplateInState({ ...t, is_recommended: value });
            setSuccess(value ? 'Marked as recommended' : 'Unmarked as recommended');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Update failed');
        }
    };

    const pollTemplatePreview = async (templateId: string) => {
        setPreviewPolling(true);
        const start = Date.now();
        let done = false;
        while (!done && Date.now() - start < 60000) {
            await new Promise(res => setTimeout(res, 2000));
            try {
                const response = await configurationAPI.getTemplate(templateId);
                const updated = response.data as TemplateRegistry;
                updateTemplateInState(updated);
                const status = updated.preview_status;
                if (status === 'ready' || status === 'failed') {
                    done = true;
                }
            } catch {
                done = true;
            }
        }
        setPreviewPolling(false);
    };

    const handleGeneratePreview = async (template: TemplateRegistry) => {
        if (!canEditTemplates) {
            setError('Only Admin can change this setting.');
            return;
        }
        const derivedSource = template.source_type || (template.repo_url ? 'git' : 'ai');
        if (derivedSource === 'git') {
            setError('Preview generation is for AI templates only.');
            return;
        }
        if (!template.blueprint_json) {
            setError('Generate blueprint first.');
            return;
        }
        setTemplateDetailSubTab('preview');
        try {
            await configurationAPI.generateTemplatePreview(template.id, { force: template.preview_status === 'ready' });
            updateTemplateInState({ ...template, preview_status: 'generating', preview_error: null });
            setSuccess('Preview generation started');
            pollTemplatePreview(template.id);
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            const msg = typeof detail === 'string' ? detail : (Array.isArray(detail) ? detail.map((d: any) => d.msg || d).join(', ') : 'Failed to start preview generation');
            if (err.response?.status === 409) setSuccess('Preview already up-to-date');
            else setError(msg);
        }
    };

    const handleOpenPreview = (template: TemplateRegistry) => {
        setPreviewTemplate(template);
        setPreviewModalOpen(true);
        if (template.preview_status === 'generating') {
            pollTemplatePreview(template.id);
        }
    };

    const pollBlueprintStatus = async (templateId: string) => {
        setBlueprintJobPolling(true);
        const start = Date.now();
        let done = false;
        while (!done && Date.now() - start < 120000) {
            await new Promise(r => setTimeout(r, 3000));
            try {
                const res = await configurationAPI.getTemplateBlueprintStatus(templateId);
                const d = res.data as { blueprint_status?: string; latest_run?: { run_id: string; status: string; error_message?: string } };
                setBlueprintStatusData(d);
                const status = d?.latest_run?.status ?? d?.blueprint_status;
                if (status === 'ready' || status === 'failed') {
                    done = true;
                    const updated = await configurationAPI.getTemplate(templateId);
                    updateTemplateInState(updated.data as TemplateRegistry);
                    setSuccess(status === 'ready' ? 'Blueprint generation finished' : 'Blueprint generation failed');
                }
            } catch {
                done = true;
            }
        }
        setBlueprintJobPolling(false);
    };

    const pollBlueprintJob = async (templateId: string) => {
        setBlueprintJobPolling(true);
        const start = Date.now();
        let done = false;
        while (!done && Date.now() - start < 120000) {
            await new Promise(r => setTimeout(r, 3000));
            try {
                const res = await configurationAPI.getTemplateBlueprintJob(templateId);
                const d = res.data as { status?: string };
                const finished = d.status === 'ready' || d.status === 'success' || d.status === 'failed';
                if (finished) {
                    done = true;
                    const updated = await configurationAPI.getTemplate(templateId);
                    updateTemplateInState(updated.data as TemplateRegistry);
                    setSuccess(d.status === 'failed' ? 'Blueprint generation failed' : 'Blueprint generation finished');
                }
                const statusRes = await configurationAPI.getTemplateBlueprintStatus(templateId);
                setBlueprintStatusData(statusRes.data as { blueprint_status?: string; latest_run?: { run_id: string; status: string; error_message?: string } });
            } catch {
                done = true;
            }
        }
        setBlueprintJobPolling(false);
    };

    const handleGenerateBlueprint = async (template: TemplateRegistry, regenerate = false) => {
        if (!canEditTemplates) {
            setError('Only Admin can change this.');
            return;
        }
        try {
            await configurationAPI.generateBlueprint(template.id, { regenerate, max_iterations: 3 });
            setSuccess(regenerate ? 'Blueprint regeneration started' : 'Blueprint generation started');
            setBlueprintStatusData({ blueprint_status: 'queued', latest_run: { run_id: '', status: 'queued' } });
            pollBlueprintJob(template.id);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start blueprint generation');
        }
    };

    const pollValidationJob = async (templateId: string) => {
        setValidationJobPolling(true);
        const start = Date.now();
        let done = false;
        while (!done && Date.now() - start < 120000) {
            await new Promise(r => setTimeout(r, 2500));
            try {
                const res = await configurationAPI.getTemplateValidationJob(templateId);
                const d = res.data as { status?: string };
                if (d.status === 'success' || d.status === 'failed') {
                    done = true;
                    const updated = await configurationAPI.getTemplate(templateId);
                    updateTemplateInState(updated.data as TemplateRegistry);
                    setValidationToast(d.status === 'success' ? 'Validation finished' : 'Validation failed');
                    setTemplateDetailSubTab('validation');
                }
            } catch {
                done = true;
            }
        }
        setValidationJobPolling(false);
    };

    const handleRunValidation = async (template: TemplateRegistry, force = false) => {
        if (!canEditTemplates) {
            setError('Only Admin can run validation.');
            return;
        }
        try {
            await configurationAPI.validateTemplate(template.id, { force });
            setSuccess('Validation started');
            pollValidationJob(template.id);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start validation');
        }
    };

    const handleValidateCopy = async (template: TemplateRegistry) => {
        if (!canEditTemplates) return;
        setCopyValidationLoading(true);
        setError('');
        try {
            await configurationAPI.validateTemplateCopy(template.id);
            const res = await configurationAPI.getTemplate(template.id);
            updateTemplateInState(res.data as TemplateRegistry);
            setSuccess('Copy validation complete');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Copy validation failed');
        } finally {
            setCopyValidationLoading(false);
        }
    };

    const handleValidateSeo = async (template: TemplateRegistry) => {
        if (!canEditTemplates) return;
        setSeoValidationLoading(true);
        setError('');
        try {
            await configurationAPI.validateTemplateSeo(template.id);
            const res = await configurationAPI.getTemplate(template.id);
            updateTemplateInState(res.data as TemplateRegistry);
            setSuccess('SEO validation complete');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'SEO validation failed');
        } finally {
            setSeoValidationLoading(false);
        }
    };

    const handleUploadTemplateImage = async (template: TemplateRegistry, file: File, sectionKey: string) => {
        if (!canEditTemplates || !file?.type?.startsWith('image/')) return;
        setImageUploading(true);
        setError('');
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('section_key', sectionKey);
            await configurationAPI.uploadTemplateImage(template.id, formData);
            const res = await configurationAPI.getTemplate(template.id);
            updateTemplateInState(res.data as TemplateRegistry);
            setSuccess('Image uploaded');
        } catch (err: any) {
            setError(formatApiErrorDetail(err.response?.data?.detail) || 'Image upload failed');
        } finally {
            setImageUploading(false);
        }
    };

    const handleUploadTemplateImages = async (template: TemplateRegistry, files: File[], sectionKey: string) => {
        if (!canEditTemplates || !files?.length) return;
        const valid = files.filter(f => f?.type?.startsWith('image/'));
        if (!valid.length) return;
        setImageUploading(true);
        setError('');
        try {
            const formData = new FormData();
            valid.forEach(f => formData.append('files', f));
            formData.append('section_key', sectionKey);
            await configurationAPI.uploadTemplateImagesBatch(template.id, formData);
            const res = await configurationAPI.getTemplate(template.id);
            updateTemplateInState(res.data as TemplateRegistry);
            setSuccess(valid.length > 1 ? `${valid.length} images uploaded` : 'Image uploaded');
        } catch (err: any) {
            setError(formatApiErrorDetail(err.response?.data?.detail) || 'Image upload failed');
        } finally {
            setImageUploading(false);
        }
    };

    const handleReorderTemplateImages = async (template: TemplateRegistry, fromCategory: string, fromIndex: number, toCategory: string, toIndex: number) => {
        if (!canEditTemplates) return;
        const meta = (template.meta_json as Record<string, unknown>) || {};
        const images: Record<string, string[]> = {};
        Object.entries(meta.images as Record<string, unknown> || {}).forEach(([k, v]) => {
            images[k] = Array.isArray(v) ? [...(v as string[])] : v ? [String(v)] : [];
        });
        const fromList = images[fromCategory];
        if (!fromList || fromIndex < 0 || fromIndex >= fromList.length) return;
        const [movedUrl] = fromList.splice(fromIndex, 1);
        if (fromCategory === toCategory) {
            if (toIndex < 0 || toIndex > fromList.length) return;
            fromList.splice(toIndex, 0, movedUrl);
            images[fromCategory] = fromList;
        } else {
            if (!images[toCategory]) images[toCategory] = [];
            const toList = images[toCategory];
            const insertAt = Math.max(0, Math.min(toIndex, toList.length));
            toList.splice(insertAt, 0, movedUrl);
            images[fromCategory] = fromList.length ? fromList : [];
            images[toCategory] = toList;
        }
        try {
            const res = await configurationAPI.updateTemplate(template.id, { meta_json: { ...meta, images } });
            updateTemplateInState(res.data as TemplateRegistry);
            setSuccess(fromCategory === toCategory ? 'Image order updated' : 'Image moved to category');
        } catch (err: any) {
            setError(formatApiErrorDetail(err.response?.data?.detail) || 'Failed to update');
        }
    };

    const handleTogglePublish = async (template: TemplateRegistry) => {
        try {
            if (!canEditTemplates) {
                setError('Only Admin can change this setting.');
                return;
            }
            await configurationAPI.updateTemplate(template.id, { is_published: !template.is_published });
            setSuccess(`Template ${template.is_published ? 'unpublished' : 'published'}`);
            loadData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update publish status');
        }
    };

    const handleDeleteTemplate = async (template: TemplateRegistry) => {
        const confirmed = window.confirm(`Delete template "${template.name}"? This cannot be undone.`);
        if (!confirmed) return;
        try {
            if (!canEditTemplates) {
                setError('Only Admin can change this setting.');
                return;
            }
            await configurationAPI.deleteTemplate(template.id);
            setSuccess('Template deleted');
            loadData();
        } catch (err: any) {
            const d = err.response?.data?.detail;
            let msg = 'Failed to delete template';
            if (typeof d === 'string') msg = d;
            else if (Array.isArray(d)) msg = d.map((x: any) => x?.msg ?? x).join(' ');
            else if (d && typeof d === 'object' && d.message) msg = d.message;
            if (d && typeof d === 'object' && d.project_titles?.length) msg += ` Projects: ${d.project_titles.join(', ')}`;
            setError(msg);
            if (err.response?.status === 409 && d && typeof d === 'object' && d.references && !d.project_titles?.length) {
                try {
                    const { data } = await configurationAPI.getTemplateReferences(template.id);
                    const projectList = (data.projects?.length)
                        ? `\n\nProjects using this template: ${data.projects.map((p: { title: string }) => p.title).join(', ')}`
                        : '';
                    const full = (data.summary || '') + projectList;
                    if (full.trim()) window.alert(`Cannot delete: ${full}`);
                } catch (_) { /* ignore */ }
            }
        }
    };

    const handleSlaChange = (stage: string, updates: Partial<SLAConfig>) => {
        if (!canEditSla) return;
        setSlaDrafts(prev =>
            prev.map(item => (item.stage === stage ? { ...item, ...updates } : item))
        );
    };

    const handleSaveSlaConfigs = async () => {
        setError('');
        setSuccess('');
        if (!canEditSla) {
            setError('Only Admin can change this setting.');
            return;
        }
        setSavingSla(true);
        try {
            await saveSlaConfigs();
            setSuccess('SLA configurations updated');
            setValidationErrors('sla_config', []);
            loadData();
        } catch (err: any) {
            const message = isConflictError(err)
                ? conflictMessage
                : (err.response?.data?.detail || 'Failed to update SLA configuration');
            setError(message);
            setValidationErrors('sla_config', [message]);
        } finally {
            setSavingSla(false);
        }
    };

    const handleSaveGlobalGates = async () => {
        setError('');
        setSuccess('');
        if (!canEditGates) {
            setError('Only Admin can change this setting.');
            return;
        }
        setSavingGates(true);
        try {
            await saveGates();
            setSuccess('Global HITL gates updated');
            setValidationErrors('hitl_gates', []);
        } catch (err: any) {
            const message = isConflictError(err)
                ? conflictMessage
                : (err.response?.data?.detail || 'Failed to update global HITL gates');
            setError(message);
            setValidationErrors('hitl_gates', [message]);
        } finally {
            setSavingGates(false);
        }
    };

    const handleSaveThresholds = async () => {
        setError('');
        setSuccess('');
        if (!canEditThresholds) {
            setError('Only Admin can change this setting.');
            return;
        }
        setSavingThresholds(true);
        try {
            await saveThresholds();
            setSuccess('Global thresholds updated');
            setValidationErrors('thresholds', []);
        } catch (err: any) {
            const message = isConflictError(err)
                ? conflictMessage
                : (err.response?.data?.detail || 'Failed to update global thresholds');
            setError(message);
            setValidationErrors('thresholds', [message]);
        } finally {
            setSavingThresholds(false);
        }
    };

    const handleSavePreviewStrategy = async () => {
        setError('');
        setSuccess('');
        if (!canEditPreviewStrategy) {
            setError('Only Admin can change this setting.');
            return;
        }
        setSavingPreview(true);
        try {
            await savePreviewStrategy();
            setSuccess('Preview strategy updated');
            setValidationErrors('preview_strategy', []);
        } catch (err: any) {
            const message = isConflictError(err)
                ? conflictMessage
                : (err.response?.data?.detail || 'Failed to update preview strategy');
            setError(message);
            setValidationErrors('preview_strategy', [message]);
        } finally {
            setSavingPreview(false);
        }
    };

    if (!user) return <div className="loading-screen">Loading...</div>;

    return (
        <RequireCapability cap="configure_system">
        <div className="page-wrapper">
            <Navigation />
            <main className="container" style={{ padding: '2rem var(--space-lg)', maxWidth: '1600px', width: '100%', margin: '0 auto' }}>
                <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <PageHeader
                        title="System Configuration"
                        purpose="Manage templates and SLA settings"
                        affects="Changes apply to new projects created after saving (unless stated otherwise)."
                        variant="page"
                    />
                </header>
                {!infoBannerDismissed && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1d4ed8', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', fontSize: '13px' }}>
                        <span>Client feedback in Sentiments can be used to refine templates, SLAs, and quality thresholds.</span>
                        <button type="button" onClick={() => setInfoBannerDismissed(true)} aria-label="Close" style={{ flexShrink: 0, padding: '4px 8px', border: '1px solid #1d4ed8', background: 'white', color: '#1d4ed8', cursor: 'pointer', borderRadius: '6px', fontSize: '12px', fontWeight: 600 }}>Close</button>
                    </div>
                )}

                {error && (
                    <div className="alert alert-error" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                        <span>{typeof error === 'string' ? error : formatApiErrorDetail(error)}</span>
                        <button type="button" onClick={() => setError('')} aria-label="Close" style={{ flexShrink: 0, padding: '4px 8px', border: '1px solid currentColor', background: 'transparent', color: 'inherit', cursor: 'pointer', borderRadius: '6px', fontSize: '12px', fontWeight: 600 }}>Close</button>
                    </div>
                )}
                {success && (
                    <div className="alert alert-success" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                        <span>{success}</span>
                        <button type="button" onClick={() => setSuccess('')} aria-label="Close" style={{ flexShrink: 0, padding: '4px 8px', border: '1px solid currentColor', background: 'transparent', color: 'inherit', cursor: 'pointer', borderRadius: '6px', fontSize: '12px', fontWeight: 600 }}>Close</button>
                    </div>
                )}

                <div style={{ display: 'flex', gap: '4px', marginBottom: '16px', flexWrap: 'wrap' }}>
                    {(['template_registry', 'sla', 'thresholds', 'preview_strategy', 'hitl_gates', 'learning'] as ConfigTab[]).map((tab) => (
                        <button
                            key={tab}
                            type="button"
                            onClick={() => setActiveConfigTab(tab)}
                            style={{
                                padding: '10px 16px',
                                borderRadius: '8px',
                                border: '1px solid #e2e8f0',
                                background: activeConfigTab === tab ? '#2563eb' : 'white',
                                color: activeConfigTab === tab ? 'white' : '#475569',
                                fontWeight: 600,
                                fontSize: '13px',
                                cursor: 'pointer',
                            }}
                        >
                            {tab === 'template_registry' && 'Template Registry'}
                            {tab === 'sla' && 'SLA Settings'}
                            {tab === 'thresholds' && 'Quality Thresholds'}
                            {tab === 'preview_strategy' && 'Preview Strategy'}
                            {tab === 'hitl_gates' && 'HITL Gates'}
                            {tab === 'learning' && 'Learning Proposals'}
                        </button>
                    ))}
                </div>

                {activeConfigTab === 'template_registry' && (
                <section style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <PageHeader
                                title="Template Registry"
                                purpose="Manage reusable templates and default selections for new projects."
                                affects="Affects which template is used when creating new projects."
                                variant="section"
                            />
                            {renderDirtyDot('templates_default')}
                            {renderStatusChip('templates_default')}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <label style={{ fontSize: '13px', color: '#64748b' }}>Preset Category</label>
                            <select
                                value={templateListFilters.category || ''}
                                onChange={(e) => setTemplateListFilters(f => ({ ...f, category: e.target.value || undefined }))}
                                style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                            >
                                <option value="">All</option>
                                <option value="Residential Modern">Residential Modern</option>
                                <option value="Corporate Trust">Corporate Trust</option>
                                <option value="Luxury Lifestyle">Luxury Lifestyle</option>
                            </select>
                            <label style={{ fontSize: '13px', color: '#64748b', marginLeft: '8px' }}>Default</label>
                            <select
                                value={defaultTemplateId}
                                onChange={(e) => { const id = e.target.value; setDefaultTemplateId(id); saveDefaultTemplate(id); }}
                                disabled={!canEditTemplates}
                                style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                            >
                                <option value="">Select default</option>
                                {templates.filter(t => t.is_published).map((t) => (
                                    <option key={t.id} value={t.id}>{t.name}</option>
                                ))}
                            </select>
                            <button
                                type="button"
                                onClick={() => setShowCreateWizard(true)}
                                disabled={!canEditTemplates}
                                style={{ padding: '8px 16px', background: '#2563eb', color: 'white', borderRadius: '6px', border: 'none', cursor: canEditTemplates ? 'pointer' : 'not-allowed', fontSize: '13px' }}
                            >
                                Create Template
                            </button>
                        </div>
                    </div>
                    {!canEditTemplates && (
                        <p style={{ marginTop: 0, marginBottom: '8px', color: '#64748b', fontSize: '12px' }}>Only Admin can change templates.</p>
                    )}
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 320px) 1fr', gap: '24px', minHeight: '480px' }}>
                        <div style={{ borderRight: '1px solid #e2e8f0', paddingRight: '16px' }}>
                            <div style={{ marginBottom: '12px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                <input
                                    type="text"
                                    placeholder="Search..."
                                    value={templateListFilters.q || ''}
                                    onChange={(e) => setTemplateListFilters(f => ({ ...f, q: e.target.value || undefined }))}
                                    style={{ flex: 1, minWidth: '100px', padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                                />
                                <select
                                    value={templateListFilters.status || ''}
                                    onChange={(e) => setTemplateListFilters(f => ({ ...f, status: e.target.value || undefined }))}
                                    style={{ padding: '6px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '12px' }}
                                >
                                    <option value="">All statuses</option>
                                    <option value="draft">draft</option>
                                    <option value="preview_ready">preview_ready</option>
                                    <option value="validated">validated</option>
                                    <option value="published">published</option>
                                    <option value="archived">archived</option>
                                </select>
                            </div>
                            {loading ? (
                                <div style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>Loading...</div>
                            ) : filteredTemplates.length === 0 ? (
                                <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', background: '#f8fafc', borderRadius: '8px' }}>No templates. Create one to get started.</div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    {filteredTemplates.map((t) => (
                                        <div
                                            key={t.id}
                                            onClick={() => setSelectedTemplateId(t.id)}
                                            style={{
                                                padding: '12px',
                                                borderRadius: '8px',
                                                border: '1px solid',
                                                borderColor: selectedTemplateId === t.id ? '#2563eb' : '#e2e8f0',
                                                background: selectedTemplateId === t.id ? '#eff6ff' : 'white',
                                                cursor: 'pointer',
                                            }}
                                        >
                                            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                                                {t.preview_thumbnail_url ? (
                                                    <img src={t.preview_thumbnail_url} alt="" style={{ width: '56px', height: '40px', borderRadius: '6px', objectFit: 'cover' }} />
                                                ) : (
                                                    <div style={{ width: '56px', height: '40px', borderRadius: '6px', background: '#e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', color: '#64748b' }}>{t.name?.slice(0, 2).toUpperCase()}</div>
                                                )}
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    <div style={{ fontWeight: 600, fontSize: '13px' }}>{t.name}</div>
                                                    <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '10px', background: t.status === 'published' ? '#ecfdf5' : t.status === 'draft' ? '#f1f5f9' : '#eff6ff', color: t.status === 'published' ? '#047857' : '#475569' }}>{t.status || 'draft'}</span>
                                                    {t.preview_status === 'ready' && <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '10px', background: '#dcfce7', color: '#166534', marginLeft: '4px' }}>Preview</span>}
                                                    <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                                        {(t.feature_tags_json || t.features_json || []).slice(0, 3).map((tag: string) => (
                                                            <span key={tag} style={{ fontSize: '10px', color: '#64748b' }}>{tag}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div style={{ minWidth: 0 }}>
                            {!selectedTemplate ? (
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8', fontSize: '14px' }}>Select a template</div>
                            ) : (
                                <>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                                        {(['overview', 'blueprint', 'preview', 'validation', 'versions', 'performance', 'evolution'] as TemplateDetailSubTab[]).map((sub) => (
                                            <button key={sub} type="button" onClick={() => setTemplateDetailSubTab(sub)} style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #e2e8f0', background: templateDetailSubTab === sub ? '#2563eb' : 'white', color: templateDetailSubTab === sub ? 'white' : '#475569', fontSize: '12px', cursor: 'pointer' }}>{sub === 'blueprint' ? 'Blueprint' : sub === 'performance' ? 'Performance' : sub === 'evolution' ? 'Evolution' : sub.charAt(0).toUpperCase() + sub.slice(1)}</button>
                                        ))}
                                    </div>
                                    <div style={{ marginBottom: '12px' }}>
                                        <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '6px', fontWeight: 600 }}>Workflow</div>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                                            <button type="button" onClick={() => handleValidateTemplate(selectedTemplate)} disabled={!canEditTemplates} title="Run validation" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '6px 10px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '12px', color: '#475569', cursor: canEditTemplates ? 'pointer' : 'not-allowed' }}>
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 6L9 17l-5-5"/></svg>
                                            Validate
                                            </button>
                                            <button type="button" onClick={() => { setTemplateDetailSubTab('preview'); handleGeneratePreview(selectedTemplate); }} disabled={!canEditTemplates || selectedTemplate.source_type === 'git' || !selectedTemplate.blueprint_json || selectedTemplate.preview_status === 'generating' || previewPolling} title={!selectedTemplate.blueprint_json ? 'Generate blueprint first' : 'Build preview and switch to Preview tab'} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '6px 10px', border: '1px solid #2563eb', color: '#2563eb', borderRadius: '6px', fontSize: '12px', cursor: (canEditTemplates && selectedTemplate.source_type !== 'git' && selectedTemplate.blueprint_json && selectedTemplate.preview_status !== 'generating' && !previewPolling) ? 'pointer' : 'not-allowed' }}>
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 3l14 9-14 9V3z"/></svg>
                                            Generate Preview
                                            </button>
                                            <button type="button" onClick={() => handleOpenPreview(selectedTemplate)} title="Open preview in new window" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '6px 10px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '12px', color: '#475569', cursor: 'pointer' }}>
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M21 3l-7 7-4-4"/></svg>
                                            Open Preview
                                            </button>
                                            <button type="button" onClick={() => handlePublishTemplate(selectedTemplate)} disabled={!canEditTemplates || !canPublishTemplate(selectedTemplate)} title={!canPublishTemplate(selectedTemplate) ? 'Requires ready preview and passed validation' : 'Publish template'} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', padding: '6px 10px', background: canPublishTemplate(selectedTemplate) ? '#10b981' : '#e2e8f0', color: canPublishTemplate(selectedTemplate) ? 'white' : '#94a3b8', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: canEditTemplates && canPublishTemplate(selectedTemplate) ? 'pointer' : 'not-allowed' }}>
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
                                            Publish
                                            </button>
                                            {!canPublishTemplate(selectedTemplate) && canEditTemplates && (
                                                <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: '4px' }}>{selectedTemplate.preview_status !== 'ready' ? 'Generate preview first' : (selectedTemplate.validation_status || 'not_run') !== 'passed' ? 'Run validation first' : ''}</span>
                                            )}
                                        </div>
                                        <div style={{ fontSize: '11px', color: '#64748b', marginTop: '10px', marginBottom: '6px', fontWeight: 600 }}>Settings</div>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                                            <button type="button" onClick={() => handleSetDefaultTemplateFromCard(selectedTemplate)} disabled={!canEditTemplates || !selectedTemplate.is_published} title="Use as default for new projects" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '5px 9px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '11px', color: '#475569', cursor: canEditTemplates && selectedTemplate.is_published ? 'pointer' : 'not-allowed' }}>
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15 9 22 9 17 14 18 22 12 18 6 22 7 14 2 9 9 9"/></svg>
                                            Default
                                            </button>
                                            <button type="button" onClick={() => handleSetRecommendedTemplate(selectedTemplate, !selectedTemplate.is_recommended)} disabled={!canEditTemplates} title="Mark as recommended" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '5px 9px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '11px', color: '#475569', cursor: canEditTemplates ? 'pointer' : 'not-allowed' }}>
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3"/></svg>
                                            {selectedTemplate.is_recommended ? 'Unrecommend' : 'Recommend'}
                                            </button>
                                            <button type="button" onClick={() => handleDuplicateTemplate(selectedTemplate)} disabled={!canEditTemplates} title="Duplicate template" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '5px 9px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '11px', color: '#475569', cursor: canEditTemplates ? 'pointer' : 'not-allowed' }}>
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                                            Duplicate
                                            </button>
                                            <button type="button" onClick={() => handleArchiveTemplate(selectedTemplate)} disabled={!canEditTemplates} title="Archive template" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '5px 9px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '11px', color: '#475569', cursor: canEditTemplates ? 'pointer' : 'not-allowed' }}>
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 8v13H3V8M1 3h22v5H1zM10 12h4"/></svg>
                                            Archive
                                            </button>
                                            <button type="button" onClick={() => handleDeleteTemplate(selectedTemplate)} disabled={!canEditTemplates} title="Delete template" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '5px 9px', border: '1px solid #fecaca', color: '#dc2626', borderRadius: '6px', fontSize: '11px', cursor: canEditTemplates ? 'pointer' : 'not-allowed' }}>
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/><path d="M10 11v6M14 11v6"/></svg>
                                            Delete
                                            </button>
                                        </div>
                                    </div>
                                    {templateDetailSubTab === 'overview' && (
                                        <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px' }}>
                                            <h4 style={{ margin: '0 0 8px' }}>{selectedTemplate.name}</h4>
                                            {canEditTemplates ? (
                                                <div style={{ marginBottom: '8px' }}>
                                                    <label style={{ fontSize: '12px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Description</label>
                                                    <OverviewDescriptionEditor key={selectedTemplate.id} template={selectedTemplate} onSaved={updateTemplateInState} />
                                                </div>
                                            ) : (
                                                <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>{selectedTemplate.description || 'No description'}</p>
                                            )}
                                            <p style={{ margin: '8px 0 0', fontSize: '12px', color: '#94a3b8' }}>Status: {selectedTemplate.status || 'draft'} · Preview: {getPreviewStatusLabel(selectedTemplate)} · Validation: {(selectedTemplate.validation_status || 'not_run').replace('_', ' ')}{selectedTemplate.validation_last_run_at ? ` (${new Date(selectedTemplate.validation_last_run_at).toLocaleString()})` : ''}</p>
                                            <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                                {!selectedTemplate.blueprint_json ? (
                                                    <button type="button" onClick={() => { setTemplateDetailSubTab('blueprint'); handleGenerateBlueprint(selectedTemplate, false); }} disabled={!canEditTemplates || blueprintJobPolling} style={{ padding: '6px 12px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: canEditTemplates && !blueprintJobPolling ? 'pointer' : 'not-allowed' }}>Generate Blueprint</button>
                                                ) : (selectedTemplate.blueprint_quality_json as Record<string, unknown> | undefined)?.status === 'fail' ? (
                                                    <button type="button" onClick={() => { setTemplateDetailSubTab('blueprint'); handleGenerateBlueprint(selectedTemplate, true); }} disabled={!canEditTemplates || blueprintJobPolling} style={{ padding: '6px 12px', border: '1px solid #f59e0b', color: '#f59e0b', borderRadius: '6px', fontSize: '12px', cursor: canEditTemplates && !blueprintJobPolling ? 'pointer' : 'not-allowed' }}>Iterate / Regenerate Blueprint</button>
                                                ) : (selectedTemplate.blueprint_quality_json as Record<string, unknown> | undefined)?.status === 'pass' ? (
                                                    <span style={{ background: '#10b981', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '12px' }}>Validated</span>
                                                ) : null}
                                            </div>
                                        </div>
                                    )}
                                    {templateDetailSubTab === 'blueprint' && (
                                        <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', fontSize: '13px' }}>
                                            {workerHealthy === false && (
                                                <div style={{ padding: '12px', background: '#fef3c7', borderRadius: '8px', color: '#92400e', marginBottom: '12px' }}>Worker not running. Blueprint jobs will not execute.</div>
                                            )}
                                            {(() => {
                                                const bp = selectedTemplate.blueprint_json as Record<string, unknown> | undefined;
                                                const quality = selectedTemplate.blueprint_quality_json as Record<string, unknown> | undefined;
                                                const scorecard = quality?.scorecard as Record<string, number> | undefined;
                                                const hardChecks = quality?.hard_checks as Record<string, boolean> | undefined;
                                                const issues = (quality?.issues as Array<{ severity?: string; path?: string; message?: string; fix_hint?: string }>) || [];
                                                const status = quality?.status as string | undefined;
                                                const jobRunning = blueprintJobPolling;
                                                const hasBlueprint = !!bp;
                                                const runStatus = blueprintStatusData?.latest_run?.status ?? blueprintStatusData?.blueprint_status ?? (hasBlueprint ? 'ready' : 'idle');
                                                const statusBadge = runStatus === 'ready' ? 'Ready' : runStatus === 'failed' ? 'Failed' : runStatus === 'queued' ? 'Queued' : runStatus === 'generating' ? 'Generating' : runStatus === 'validating' ? 'Validating' : 'Idle';
                                                const isInProgress = runStatus === 'queued' || runStatus === 'generating' || runStatus === 'validating';
                                                const errorMessage = blueprintStatusData?.latest_run?.error_message;
                                                const latestRunId = blueprintStatusData?.latest_run?.run_id;
                                                return (
                                                    <>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                                                            <span style={{ padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: 500, background: runStatus === 'ready' ? '#dcfce7' : runStatus === 'failed' ? '#fee2e2' : isInProgress ? '#fef3c7' : '#f1f5f9', color: runStatus === 'ready' ? '#166534' : runStatus === 'failed' ? '#991b1b' : isInProgress ? '#92400e' : '#475569' }}>{statusBadge}</span>
                                                            <button type="button" onClick={() => handleGenerateBlueprint(selectedTemplate, !!hasBlueprint)} disabled={!canEditTemplates || jobRunning} style={{ padding: '8px 16px', background: jobRunning ? '#94a3b8' : '#2563eb', color: 'white', border: 'none', borderRadius: '6px', fontSize: '13px', cursor: canEditTemplates && !jobRunning ? 'pointer' : 'not-allowed' }}>{jobRunning ? 'Running…' : hasBlueprint ? 'Regenerate Blueprint' : 'Generate Blueprint'}</button>
                                                            {selectedTemplate.blueprint_hash && <code style={{ fontSize: '11px', background: '#e2e8f0', padding: '2px 6px', borderRadius: '4px' }}>{String(selectedTemplate.blueprint_hash).slice(0, 12)}…</code>}
                                                            {status === 'pass' && <span style={{ background: '#10b981', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px' }}>Validated</span>}
                                                            {status === 'fail' && <span style={{ background: '#f59e0b', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px' }}>Below threshold</span>}
                                                        </div>
                                                        {isInProgress && <p style={{ margin: '0 0 12px', color: '#64748b' }}>This can take up to 60 seconds.</p>}
                                                        {runStatus === 'failed' && errorMessage && (
                                                            <div style={{ marginBottom: '12px', padding: '12px', background: '#fee2e2', borderRadius: '8px', color: '#991b1b' }}>
                                                                {errorMessage}
                                                                {latestRunId && canEditTemplates && (
                                                                    <button type="button" onClick={() => configurationAPI.getBlueprintRunDetails(latestRunId).then((r: any) => setBlueprintRunDetails(r.data)).catch(() => setBlueprintRunDetails(null))} style={{ marginLeft: '12px', padding: '4px 10px', border: '1px solid #991b1b', borderRadius: '6px', background: 'transparent', color: '#991b1b', cursor: 'pointer', fontSize: '12px' }}>View details</button>
                                                                )}
                                                            </div>
                                                        )}
                                                        {blueprintRunDetails && (
                                                            <div style={{ marginBottom: '12px', padding: '12px', background: '#f1f5f9', borderRadius: '8px', maxHeight: '300px', overflow: 'auto' }}>
                                                                <pre style={{ margin: 0, fontSize: '11px', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{JSON.stringify(blueprintRunDetails, null, 2)}</pre>
                                                                <button type="button" onClick={() => setBlueprintRunDetails(null)} style={{ marginTop: '8px', padding: '4px 8px', fontSize: '12px', cursor: 'pointer' }}>Close</button>
                                                            </div>
                                                        )}
                                                        {!hasBlueprint && !jobRunning && <p style={{ margin: 0, color: '#64748b' }}>No blueprint yet. Click Generate Blueprint to create one.</p>}
                                                        {hasBlueprint && bp && (
                                                            <>
                                                                <div style={{ marginBottom: '16px' }}>
                                                                    <h5 style={{ margin: '0 0 8px' }}>Summary</h5>
                                                                    <ul style={{ margin: 0, paddingLeft: '20px', color: '#475569' }}>
                                                                        {bp.pages && Array.isArray(bp.pages) ? <li>Pages: {(bp.pages as unknown[]).length}</li> : null}
                                                                        {bp.tokens && typeof bp.tokens === 'object' ? <li>Tokens: colors, typography, spacing</li> : null}
                                                                        {bp.navigation && typeof bp.navigation === 'object' ? <li>Navigation: {(bp.navigation as Record<string, unknown>).items && Array.isArray((bp.navigation as Record<string, unknown>).items) ? ((bp.navigation as Record<string, unknown>).items as unknown[]).length : 0} items</li> : null}
                                                                    </ul>
                                                                </div>
                                                                {(() => {
                                                                    const pages = (bp?.pages as Array<{ slug?: string; title?: string; seo?: { meta_title?: string; meta_description?: string; h1?: string }; sections?: unknown[] }>) ?? selectedTemplate.pages_json ?? [];
                                                                    const pageList = Array.isArray(pages) ? pages : [];
                                                                    const selectedPage = selectedStructurePageIndex != null && pageList[selectedStructurePageIndex] ? pageList[selectedStructurePageIndex] : pageList[0] ?? null;
                                                                    return (
                                                                        <div style={{ marginBottom: '16px', padding: '16px', border: '1px solid #e2e8f0', borderRadius: '8px', background: 'white' }}>
                                                                            <h5 style={{ margin: '0 0 12px' }}>Pages (click to view)</h5>
                                                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
                                                                                {pageList.map((p, idx) => (
                                                                                    <button key={idx} type="button" onClick={() => setSelectedStructurePageIndex(idx)} style={{ padding: '8px 14px', borderRadius: '8px', border: '1px solid', borderColor: selectedStructurePageIndex === idx ? '#2563eb' : '#e2e8f0', background: selectedStructurePageIndex === idx ? '#eff6ff' : 'white', color: selectedStructurePageIndex === idx ? '#1d4ed8' : '#475569', fontWeight: 500, cursor: 'pointer', fontSize: '13px' }}>
                                                                                        {(p as { title?: string }).title || (p as { slug?: string }).slug || `Page ${idx + 1}`}
                                                                                    </button>
                                                                                ))}
                                                                            </div>
                                                                            {selectedPage && (
                                                                                <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', marginBottom: '16px', background: '#f8fafc' }}>
                                                                                    <h6 style={{ margin: '0 0 12px', fontSize: '14px' }}>SEO (page content)</h6>
                                                                                    <dl style={{ margin: 0, display: 'grid', gap: '8px', fontSize: '12px' }}>
                                                                                        <div><dt style={{ color: '#64748b', marginBottom: '2px' }}>Meta title</dt><dd style={{ margin: 0 }}>{(selectedPage as { seo?: { meta_title?: string } }).seo?.meta_title || '—'}</dd></div>
                                                                                        <div><dt style={{ color: '#64748b', marginBottom: '2px' }}>Meta description</dt><dd style={{ margin: 0 }}>{(selectedPage as { seo?: { meta_description?: string } }).seo?.meta_description || '—'}</dd></div>
                                                                                        <div><dt style={{ color: '#64748b', marginBottom: '2px' }}>H1</dt><dd style={{ margin: 0 }}>{(selectedPage as { seo?: { h1?: string } }).seo?.h1 || '—'}</dd></div>
                                                                                    </dl>
                                                                                    <h6 style={{ margin: '12px 0 8px', fontSize: '14px' }}>Sections</h6>
                                                                                    <ul style={{ margin: 0, paddingLeft: '20px' }}>{((selectedPage as { sections?: unknown[] }).sections || []).map((s: any, i: number) => <li key={i}>{s?.type ?? s ?? `Section ${i + 1}`}</li>)}</ul>
                                                                                </div>
                                                                            )}
                                                                            <h5 style={{ margin: '0 0 8px' }}>Template images</h5>
                                                                            <p style={{ margin: '0 0 12px', color: '#64748b', fontSize: '12px' }}>Upload images per category. You can add many per category; the preview uses them by the blueprint&apos;s section <code style={{ fontSize: '11px', background: '#f1f5f9', padding: '1px 4px' }}>image_prompt_category</code>. Choose a category below, then choose files (multiple allowed).</p>
                                                                            {(() => {
                                                                                const bpPages = selectedTemplate.blueprint_json as { pages?: Array<{ slug?: string; title?: string; sections?: Array<{ type?: string; variant?: string; image_prompt_category?: string }> }> } | undefined;
                                                                                const sectionCategoryRows: Array<{ page: string; sectionType: string; variant?: string; category: string }> = [];
                                                                                if (bpPages?.pages) {
                                                                                    for (const page of bpPages.pages) {
                                                                                        const pageLabel = (page.title || page.slug || '') || 'Page';
                                                                                        for (const sec of page.sections || []) {
                                                                                            const cat = (sec.image_prompt_category || '').trim();
                                                                                            if (cat) sectionCategoryRows.push({ page: pageLabel, sectionType: sec.type || 'section', variant: sec.variant, category: cat });
                                                                                        }
                                                                                    }
                                                                                }
                                                                                return sectionCategoryRows.length > 0 ? (
                                                                                    <div style={{ marginBottom: '12px', padding: '10px 12px', background: '#f1f5f9', borderRadius: '8px', fontSize: '12px' }}>
                                                                                        <div style={{ fontWeight: 600, marginBottom: '6px', color: '#475569' }}>How sections use these images</div>
                                                                                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                                                                                            <thead><tr style={{ borderBottom: '1px solid #e2e8f0' }}><th style={{ textAlign: 'left', padding: '4px 8px 4px 0' }}>Page</th><th style={{ textAlign: 'left', padding: '4px 8px' }}>Section</th><th style={{ textAlign: 'left', padding: '4px 8px' }}>Image category</th></tr></thead>
                                                                                            <tbody>
                                                                                                {sectionCategoryRows.map((row, i) => (
                                                                                                    <tr key={i} style={{ borderBottom: '1px solid #e2e8f0' }}>
                                                                                                        <td style={{ padding: '4px 8px 4px 0' }}>{row.page}</td>
                                                                                                        <td style={{ padding: '4px 8px' }}>{row.sectionType}{row.variant ? ` (${row.variant})` : ''}</td>
                                                                                                        <td style={{ padding: '4px 8px' }}><strong>{row.category}</strong></td>
                                                                                                    </tr>
                                                                                                ))}
                                                                                            </tbody>
                                                                                        </table>
                                                                                    </div>
                                                                                ) : (
                                                                                    <p style={{ margin: '0 0 12px', fontSize: '12px', color: '#94a3b8' }}>Blueprint sections can specify <code>image_prompt_category</code>. Upload images for those categories below.</p>
                                                                                );
                                                                            })()}
                                                                            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                                                                                <select value={imageUploadSectionKey} onChange={e => setImageUploadSectionKey(e.target.value)} style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1' }}>
                                                                                    {['exterior', 'interior', 'lifestyle', 'people', 'neighborhood'].map(k => <option key={k} value={k}>{k.charAt(0).toUpperCase() + k.slice(1)}</option>)}
                                                                                </select>
                                                                                <input type="file" accept="image/*" multiple onChange={e => { const files = e.target.files; if (files?.length) handleUploadTemplateImages(selectedTemplate, Array.from(files), imageUploadSectionKey); e.target.value = ''; }} disabled={!canEditTemplates || imageUploading} style={{ fontSize: '12px' }} />
                                                                                {imageUploading && <span style={{ color: '#64748b', fontSize: '12px' }}>Uploading…</span>}
                                                                            </div>
                                                                            {(() => {
                                                                                const metaImages = (selectedTemplate.meta_json as Record<string, unknown>)?.images;
                                                                                if (!metaImages || typeof metaImages !== 'object') return null;
                                                                                const entries = Object.entries(metaImages as Record<string, unknown>).filter(([, v]) => v !== undefined && v !== null);
                                                                                if (entries.length === 0) return null;
                                                                                return (
                                                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                                                                        {entries.map(([key, urls]) => {
                                                                                            const list = Array.isArray(urls) ? urls as string[] : [urls as string];
                                                                                            const valid = list.filter((u): u is string => typeof u === 'string' && u.length > 0);
                                                                                            if (valid.length === 0) return null;
                                                                                            return (
                                                                                                <div key={key} style={{ marginBottom: '4px' }}>
                                                                                                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>{key} ({valid.length} image{valid.length !== 1 ? 's' : ''}){canEditTemplates ? ' — drag to reorder or drop on another category' : ''}</div>
                                                                                                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                                                                                        {valid.slice(0, 20).map((url, i) => (
                                                                                                            <div key={i} draggable={canEditTemplates} onDragStart={(e) => { e.dataTransfer.setData('application/json', JSON.stringify({ category: key, index: i })); e.dataTransfer.effectAllowed = 'move'; }} onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; }} onDrop={(e) => { e.preventDefault(); try { const d = JSON.parse(e.dataTransfer.getData('application/json') || '{}'); if (d.category != null && typeof d.index === 'number' && (d.category !== key || d.index !== i)) handleReorderTemplateImages(selectedTemplate, d.category, d.index, key, i); } catch { /* ignore */ } }} style={{ display: 'block', cursor: canEditTemplates ? 'grab' : 'default' }}>
                                                                                                                <a href={url} target="_blank" rel="noreferrer" style={{ display: 'block' }}>
                                                                                                                    <img src={url} alt="" style={{ width: '80px', height: '56px', objectFit: 'cover', borderRadius: '6px', border: '1px solid #e2e8f0' }} draggable={false} />
                                                                                                                </a>
                                                                                                            </div>
                                                                                                        ))}
                                                                                                        {valid.length > 20 && <span style={{ fontSize: '11px', color: '#64748b', alignSelf: 'center' }}>+{valid.length - 20} more</span>}
                                                                                                    </div>
                                                                                                </div>
                                                                                            );
                                                                                        })}
                                                                                    </div>
                                                                                );
                                                                            })()}
                                                                            {!pageList.length && <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '11px' }}>{JSON.stringify(selectedTemplate.pages_json || [], null, 2)}</pre>}
                                                                        </div>
                                                                    );
                                                                })()}
                                                            </>
                                                        )}
                                                        {(scorecard || hardChecks) && (
                                                            <div style={{ marginBottom: '16px' }}>
                                                                <h5 style={{ margin: '0 0 8px' }}>Scorecard</h5>
                                                                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '8px' }}>
                                                                    {scorecard && Object.entries(scorecard).map(([k, v]) => <span key={k} style={{ background: '#e2e8f0', padding: '4px 8px', borderRadius: '4px' }}>{k}: {Number(v)}</span>)}
                                                                </div>
                                                                {hardChecks && <div style={{ fontSize: '12px', color: '#64748b' }}>Hard checks: {Object.entries(hardChecks).map(([k, v]) => `${k}=${v}`).join(', ')}</div>}
                                                            </div>
                                                        )}
                                                        {issues.length > 0 && (
                                                            <div>
                                                                <h5 style={{ margin: '0 0 8px' }}>Issues</h5>
                                                                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                                                                    {issues.slice(0, 20).map((i, idx) => <li key={idx} style={{ color: i.severity === 'blocker' ? '#dc2626' : i.severity === 'major' ? '#ea580c' : '#64748b' }}>{i.path}: {i.message}{i.fix_hint ? ` (${i.fix_hint})` : ''}</li>)}
                                                                </ul>
                                                                {issues.length > 20 && <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>…and {issues.length - 20} more</p>}
                                                            </div>
                                                        )}
                                                    </>
                                                );
                                            })()}
                                        </div>
                                    )}
                                    {templateDetailSubTab === 'preview' && (
                                        <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                                                {selectedTemplate.preview_thumbnail_url ? (
                                                    <img src={selectedTemplate.preview_thumbnail_url} alt="Preview thumbnail" style={{ width: '120px', height: '80px', borderRadius: '8px', objectFit: 'cover' }} />
                                                ) : (
                                                    <div style={{ width: '120px', height: '80px', borderRadius: '8px', background: '#e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', color: '#64748b' }}>No thumbnail</div>
                                                )}
                                                <div>
                                                    <span style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '4px', background: selectedTemplate.preview_status === 'ready' ? '#dcfce7' : selectedTemplate.preview_status === 'failed' ? '#fee2e2' : '#fef3c7', color: selectedTemplate.preview_status === 'ready' ? '#166534' : selectedTemplate.preview_status === 'failed' ? '#991b1b' : '#92400e' }}>
                                                        {getPreviewStatusLabel(selectedTemplate)}
                                                    </span>
                                                    {selectedTemplate.preview_status === 'ready' && (selectedTemplate.preview_url || getPreviewIframeUrl(selectedTemplate)) && (
                                                        <a href={getPreviewIframeUrl(selectedTemplate) || selectedTemplate.preview_url!} target="_blank" rel="noreferrer" style={{ display: 'block', marginTop: '6px', fontSize: '13px', color: '#2563eb' }}>Open preview in new tab</a>
                                                    )}
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => handleGeneratePreview(selectedTemplate)}
                                                    disabled={!canEditTemplates || selectedTemplate.source_type === 'git' || !selectedTemplate.blueprint_json || selectedTemplate.preview_status === 'generating' || previewPolling}
                                                    title={!selectedTemplate.blueprint_json ? 'Generate blueprint first' : selectedTemplate.preview_status === 'generating' || previewPolling ? 'Generating…' : ''}
                                                    style={{ padding: '8px 16px', background: (selectedTemplate.preview_status === 'ready' ? '#e0f2fe' : '#2563eb'), color: (selectedTemplate.preview_status === 'ready' ? '#0369a1' : 'white'), border: '1px solid ' + (selectedTemplate.preview_status === 'ready' ? '#0ea5e9' : '#2563eb'), borderRadius: '6px', fontSize: '13px', cursor: (canEditTemplates && selectedTemplate.source_type !== 'git' && selectedTemplate.blueprint_json && selectedTemplate.preview_status !== 'generating' && !previewPolling) ? 'pointer' : 'not-allowed' }}
                                                >
                                                    {selectedTemplate.preview_status === 'generating' || previewPolling ? 'Generating…' : selectedTemplate.preview_status === 'ready' ? 'Regenerate Preview' : 'Generate Preview'}
                                                </button>
                                            </div>
                                            {selectedTemplate.preview_status === 'failed' && selectedTemplate.preview_error && (
                                                <div style={{ padding: '12px', background: '#fee2e2', borderRadius: '8px', color: '#991b1b', fontSize: '13px', marginBottom: '12px' }}>{selectedTemplate.preview_error}</div>
                                            )}
                                            {!selectedTemplate.blueprint_json && (
                                                <p style={{ margin: 0, color: '#64748b', fontSize: '13px' }}>Generate a blueprint first in the Blueprint tab, then generate the preview.</p>
                                            )}
                                            {selectedTemplate.preview_status === 'ready' && (selectedTemplate.preview_url || getPreviewIframeUrl(selectedTemplate)) ? (
                                                <>
                                                    <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
                                                        <span style={{ fontSize: '12px', color: '#64748b', alignSelf: 'center' }}>Viewport:</span>
                                                        {(['desktop', 'tablet', 'mobile'] as const).map(v => (
                                                            <button key={v} type="button" onClick={() => setPreviewViewport(v)} style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid', fontSize: '12px', cursor: 'pointer', background: previewViewport === v ? '#2563eb' : 'white', color: previewViewport === v ? 'white' : '#475569', borderColor: previewViewport === v ? '#2563eb' : '#e2e8f0' }}>{v.charAt(0).toUpperCase() + v.slice(1)}</button>
                                                        ))}
                                                    </div>
                                                    <div style={{ maxWidth: previewViewport === 'desktop' ? '100%' : previewViewport === 'tablet' ? '768px' : '375px', margin: '0 auto', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden', boxShadow: previewViewport !== 'desktop' ? '0 4px 12px rgba(0,0,0,0.1)' : 'none' }}>
                                                        <iframe title="Preview" src={getPreviewIframeUrl(selectedTemplate) || selectedTemplate.preview_url!} style={{ width: '100%', height: previewViewport === 'mobile' ? '600px' : '400px', border: 'none', display: 'block' }} />
                                                    </div>
                                                </>
                                            ) : selectedTemplate.blueprint_json && selectedTemplate.preview_status !== 'failed' && (
                                                <p style={{ margin: 0, color: '#64748b' }}>Status: {getPreviewStatusLabel(selectedTemplate)}. Click Generate Preview to build the static site.</p>
                                            )}
                                        </div>
                                    )}
                                    {templateDetailSubTab === 'validation' && (
                                        <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', fontSize: '13px' }}>
                                            {validationToast && (
                                                <div role="alert" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '16px', padding: '12px 16px', background: '#dbeafe', border: '1px solid #93c5fd', borderRadius: '8px', color: '#1e40af', fontSize: '13px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
                                                    <span>{validationToast}</span>
                                                    <button type="button" onClick={() => setValidationToast(null)} aria-label="Close message" style={{ flexShrink: 0, padding: '6px 10px', border: '1px solid #1e40af', background: 'white', color: '#1e40af', cursor: 'pointer', borderRadius: '6px', fontSize: '12px', fontWeight: 600 }} title="Close">Close</button>
                                                </div>
                                            )}
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                                                <button type="button" onClick={() => handleRunValidation(selectedTemplate, selectedTemplate.validation_status === 'passed')} disabled={!canEditTemplates || validationJobPolling || selectedTemplate.preview_status !== 'ready'} title={selectedTemplate.preview_status !== 'ready' ? 'Generate preview first' : ''} style={{ padding: '8px 16px', background: validationJobPolling ? '#94a3b8' : '#2563eb', color: 'white', border: 'none', borderRadius: '6px', fontSize: '13px', cursor: (canEditTemplates && !validationJobPolling && selectedTemplate.preview_status === 'ready') ? 'pointer' : 'not-allowed' }}>{validationJobPolling ? 'Running…' : 'Run Validation'}</button>
                                                <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', background: (selectedTemplate.validation_status || '') === 'passed' ? '#dcfce7' : (selectedTemplate.validation_status || '') === 'failed' ? '#fee2e2' : (selectedTemplate.validation_status || '') === 'running' ? '#fef3c7' : '#f1f5f9', color: (selectedTemplate.validation_status || '') === 'passed' ? '#166534' : (selectedTemplate.validation_status || '') === 'failed' ? '#991b1b' : '#475569' }}>{(selectedTemplate.validation_status || 'not_run').replace('_', ' ')}</span>
                                                {selectedTemplate.validation_last_run_at && <span style={{ color: '#64748b', fontSize: '12px' }}>Last run: {new Date(selectedTemplate.validation_last_run_at).toLocaleString()}</span>}
                                            </div>
                                            <p style={{ margin: '0 0 16px', color: '#64748b', fontSize: '12px' }}>Run Validation includes responsiveness (Lighthouse mobile viewport). Generate preview first.</p>
                                            {selectedTemplate.preview_status !== 'ready' && <p style={{ margin: 0, color: '#64748b' }}>Generate preview first, then run validation.</p>}
                                            {selectedTemplate.blueprint_json && (
                                                <>
                                                    <h5 style={{ margin: '16px 0 8px' }}>Copy &amp; SEO</h5>
                                                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
                                                        <button type="button" onClick={() => handleValidateCopy(selectedTemplate)} disabled={!canEditTemplates || copyValidationLoading} style={{ padding: '6px 12px', border: '1px solid #2563eb', color: '#2563eb', borderRadius: '6px', fontSize: '12px', cursor: canEditTemplates && !copyValidationLoading ? 'pointer' : 'not-allowed' }}>{copyValidationLoading ? 'Running…' : 'Validate copy'}</button>
                                                        <button type="button" onClick={() => handleValidateSeo(selectedTemplate)} disabled={!canEditTemplates || seoValidationLoading} style={{ padding: '6px 12px', border: '1px solid #059669', color: '#059669', borderRadius: '6px', fontSize: '12px', cursor: canEditTemplates && !seoValidationLoading ? 'pointer' : 'not-allowed' }}>{seoValidationLoading ? 'Running…' : 'Validate SEO'}</button>
                                                    </div>
                                                    {(() => {
                                                        const meta = selectedTemplate.meta_json as Record<string, { passed?: boolean; score?: number; summary?: string }> | undefined;
                                                        const copyVal = meta?.copy_validation;
                                                        const seoVal = meta?.seo_validation;
                                                        return (
                                                            <>
                                                                {copyVal && (
                                                                    <div style={{ marginBottom: '12px', padding: '12px', background: '#f1f5f9', borderRadius: '8px' }}>
                                                                        <strong>Copy validation</strong>
                                                                        <div style={{ fontSize: '12px', marginTop: '4px' }}>{copyVal.passed ? 'Passed' : 'Issues found'} · Score: {copyVal.score ?? '—'}</div>
                                                                        {copyVal.summary && <div style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>{copyVal.summary}</div>}
                                                                    </div>
                                                                )}
                                                                {seoVal && (
                                                                    <div style={{ marginBottom: '12px', padding: '12px', background: '#f1f5f9', borderRadius: '8px' }}>
                                                                        <strong>SEO validation</strong>
                                                                        <div style={{ fontSize: '12px', marginTop: '4px' }}>{seoVal.passed ? 'Passed' : 'Issues found'} · Score: {seoVal.score ?? '—'}</div>
                                                                        {seoVal.summary && <div style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>{seoVal.summary}</div>}
                                                                    </div>
                                                                )}
                                                            </>
                                                        );
                                                    })()}
                                                </>
                                            )}
                                            {(() => {
                                                const vr = selectedTemplate.validation_results_json as Record<string, unknown> | undefined;
                                                if (!vr || Object.keys(vr).length === 0) return <p style={{ margin: 0, color: '#64748b' }}>No validation results yet.</p>;
                                                const lh = vr.lighthouse as Record<string, unknown> | undefined;
                                                const axe = vr.axe as Record<string, unknown> | undefined;
                                                const content = vr.content as Record<string, unknown> | undefined;
                                                const failed = (vr.failed_reasons as string[]) || [];
                                                return (
                                                    <>
                                                        {lh && !lh.error && (lh.scores as Record<string, number>) && (
                                                            <div style={{ marginBottom: '12px' }}>
                                                                <h5 style={{ margin: '0 0 6px' }}>Lighthouse</h5>
                                                                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                                                    {Object.entries(lh.scores as Record<string, number>).map(([k, v]) => (
                                                                        <span key={k} style={{ background: '#e2e8f0', padding: '4px 8px', borderRadius: '4px' }}>{k}: {typeof v === 'number' ? Math.round(v * 100) : v}</span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {axe && !axe.error && (
                                                            <div style={{ marginBottom: '12px' }}>
                                                                <h5 style={{ margin: '0 0 6px' }}>Axe</h5>
                                                                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                                                    {['critical', 'serious', 'moderate', 'minor'].map(imp => (
                                                                        <span key={imp} style={{ background: '#e2e8f0', padding: '4px 8px', borderRadius: '4px' }}>{imp}: {Number((axe as Record<string, number>)[imp] ?? 0)}</span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {content && !content.error && (
                                                            <div style={{ marginBottom: '12px' }}>
                                                                <h5 style={{ margin: '0 0 6px' }}>Content</h5>
                                                                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                                                    {['has_home', 'has_cta', 'has_contact_or_lead', 'has_viewport_meta'].map(k => (
                                                                        <span key={k} style={{ background: (content as Record<string, boolean>)[k] ? '#dcfce7' : '#fee2e2', padding: '4px 8px', borderRadius: '4px' }}>{k}: {(content as Record<string, boolean>)[k] ? 'yes' : 'no'}</span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {failed.length > 0 && (
                                                            <div style={{ marginBottom: '12px' }}>
                                                                <h5 style={{ margin: '0 0 6px' }}>Failed reasons</h5>
                                                                <ul style={{ margin: 0, paddingLeft: '20px', color: '#991b1b' }}>{failed.map((r, i) => <li key={i}>{r}</li>)}</ul>
                                                                <button type="button" onClick={() => { setFixBlueprintModalOpen(true); setFixBlueprintSuggestions(null); setFixBlueprintShowTechnical(false); setFixBlueprintLoading(true); configurationAPI.getFixBlueprintSuggestions(selectedTemplate.id).then(r => { setFixBlueprintSuggestions(r.data); setFixBlueprintLoading(false); }).catch(() => { setFixBlueprintSuggestions({ plain_language_summary: 'Could not load suggestions. Please check the failed reasons above and share them with your technical team.', technical_details: null, code_snippets: [], interim_actions: [] }); setFixBlueprintLoading(false); }); }} style={{ marginTop: '8px', padding: '6px 12px', border: '1px solid #2563eb', color: '#2563eb', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}>Fix Blueprint</button>
                                                            </div>
                                                        )}
                                                        <details style={{ marginTop: '12px' }}>
                                                            <summary style={{ cursor: 'pointer', color: '#64748b' }}>Raw results</summary>
                                                            <pre style={{ margin: '8px 0 0', whiteSpace: 'pre-wrap', fontSize: '11px' }}>{JSON.stringify(vr, null, 2)}</pre>
                                                        </details>
                                                    </>
                                                );
                                            })()}
                                        </div>
                                    )}
                                    {templateDetailSubTab === 'versions' && (
                                        <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', fontSize: '13px' }}>Version: {selectedTemplate.version ?? 1}. Changelog: {selectedTemplate.changelog || '—'}</div>
                                    )}
                                    {templateDetailSubTab === 'performance' && (
                                        <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', fontSize: '13px' }}>
                                            <h4 style={{ margin: '0 0 12px' }}>Performance metrics</h4>
                                            {selectedTemplate.performance_metrics_json && typeof selectedTemplate.performance_metrics_json === 'object' && Object.keys(selectedTemplate.performance_metrics_json).length > 0 ? (
                                                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                                                    {Object.entries(selectedTemplate.performance_metrics_json).map(([k, v]) => (
                                                        <li key={k}><strong>{k}</strong>: {String(v)}</li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <p style={{ margin: 0, color: '#64748b' }}>No metrics yet. This tab shows usage and quality data (e.g. usage count, average sentiment) once &quot;Template metrics&quot; has been run in Admin config to aggregate from projects using this template.</p>
                                            )}
                                        </div>
                                    )}
                                    {templateDetailSubTab === 'evolution' && (
                                        <EvolutionTab templateId={selectedTemplate.id} />
                                    )}
                                </>
                            )}
                        </div>
                    </div>

                    <div style={{ overflowX: 'auto', display: 'none' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                            <thead>
                                <tr style={{ background: '#f8fafc', color: '#64748b', textAlign: 'left' }}>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>Preview</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>Template</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>Type</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>Preview Status</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0', textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr><td colSpan={5} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>Loading templates...</td></tr>
                                ) : templates.length === 0 ? (
                                    <tr><td colSpan={5} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>No templates found.</td></tr>
                                ) : (
                                    templates.map(t => (
                                        <tr key={t.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                            <td style={{ padding: '12px 16px' }}>
                                                <div style={{ display: 'grid', gap: '6px', justifyItems: 'start' }}>
                                                    {t.preview_thumbnail_url ? (
                                                        <img src={t.preview_thumbnail_url} alt={`${t.name} thumbnail`} style={{ width: '48px', height: '48px', borderRadius: '8px', objectFit: 'cover' }} />
                                                    ) : (
                                                        <div style={{ width: '48px', height: '48px', borderRadius: '8px', background: '#e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', color: '#64748b' }}>
                                                            {t.name?.slice(0, 2).toUpperCase()}
                                                        </div>
                                                    )}
                                                    <div style={{ fontSize: '11px', color: '#64748b' }}>
                                                        Preview mode: {getPreviewModeLabel()}
                                                    </div>
                                                </div>
                                            </td>
                                            <td style={{ padding: '12px 16px' }}>
                                                <div style={{ fontWeight: 600 }}>{t.name}</div>
                                                <div style={{ fontSize: '12px', color: '#64748b' }}>{t.description || 'No description yet'}</div>
                                                <div style={{ fontSize: '11px', color: '#94a3b8' }}>ID: {t.id}</div>
                                                {(t.features_json && t.features_json.length > 0) && (
                                                    <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                                        {t.features_json.slice(0, 4).map((feature) => (
                                                            <span key={feature} style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '10px', background: '#f1f5f9', color: '#475569' }}>
                                                                {feature}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                                {t.repo_url && (
                                                    <div style={{ marginTop: '6px', fontSize: '12px' }}>
                                                        <a href={t.repo_url} target="_blank" rel="noreferrer" style={{ color: '#2563eb' }}>Repo</a>
                                                        {t.default_branch && <span style={{ color: '#94a3b8', marginLeft: '6px' }}>({t.default_branch})</span>}
                                                    </div>
                                                )}
                                            </td>
                                            <td style={{ padding: '12px 16px' }}>
                                                <span style={{ fontSize: '12px', background: (t.source_type === 'git' || (!t.source_type && t.repo_url)) ? '#fef3c7' : '#eff6ff', color: (t.source_type === 'git' || (!t.source_type && t.repo_url)) ? '#92400e' : '#2563eb', padding: '4px 8px', borderRadius: '12px', fontWeight: 600 }}>
                                                    {(t.source_type === 'git' || (!t.source_type && t.repo_url)) ? 'Git Template' : 'AI Generated'}
                                                </span>
                                            </td>
                                            <td style={{ padding: '12px 16px' }}>
                                                <span style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '12px', fontWeight: 600, ...getPreviewStatusStyle(getPreviewStatusLabel(t)) }}>
                                                    {getPreviewStatusLabel(t)}
                                                </span>
                                                <div style={{ marginTop: '6px' }}>
                                                    {t.is_published ? (
                                                        <span style={{ fontSize: '11px', background: '#ecfdf5', color: '#10b981', padding: '2px 6px', borderRadius: '10px', fontWeight: 600 }}>Published</span>
                                                    ) : (
                                                        <span style={{ fontSize: '11px', background: '#fef3c7', color: '#92400e', padding: '2px 6px', borderRadius: '10px', fontWeight: 600 }}>Unpublished</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                                                <div style={{ display: 'inline-flex', gap: '8px', flexWrap: 'nowrap', justifyContent: 'flex-end' }}>
                                                    <button
                                                        onClick={() => handleOpenPreview(t)}
                                                        title="Preview"
                                                        aria-label="Preview"
                                                        style={{ width: '28px', height: '28px', background: 'transparent', border: '1px solid #2563eb', color: '#2563eb', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' }}
                                                    >
                                                        👁️
                                                    </button>
                                                    <button
                                                        disabled
                                                        title="Use template (coming soon)"
                                                        aria-label="Use template"
                                                        style={{ width: '28px', height: '28px', background: '#f1f5f9', border: '1px solid #e2e8f0', color: '#94a3b8', borderRadius: '6px', cursor: 'not-allowed', fontSize: '14px' }}
                                                    >
                                                        📌
                                                    </button>
                                                    <button
                                                        onClick={() => handleTogglePublish(t)}
                                                        title={t.is_published ? 'Unpublish' : 'Publish'}
                                                        aria-label={t.is_published ? 'Unpublish' : 'Publish'}
                                                        disabled={!canEditTemplates}
                                                        style={{
                                                            width: '28px',
                                                            height: '28px',
                                                            background: 'transparent',
                                                            border: '1px solid #0ea5e9',
                                                            color: '#0ea5e9',
                                                            borderRadius: '6px',
                                                            cursor: canEditTemplates ? 'pointer' : 'not-allowed',
                                                            fontSize: '14px',
                                                            opacity: canEditTemplates ? 1 : 0.5,
                                                        }}
                                                    >
                                                        {t.is_published ? '🚫' : '📣'}
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteTemplate(t)}
                                                        title="Delete"
                                                        aria-label="Delete"
                                                        disabled={!canEditTemplates}
                                                        style={{
                                                            width: '28px',
                                                            height: '28px',
                                                            background: 'transparent',
                                                            border: '1px solid #ef4444',
                                                            color: '#ef4444',
                                                            borderRadius: '6px',
                                                            cursor: canEditTemplates ? 'pointer' : 'not-allowed',
                                                            fontSize: '14px',
                                                            opacity: canEditTemplates ? 1 : 0.5,
                                                        }}
                                                    >
                                                        🗑️
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>
                )}

                {showCreateWizard && (
                <Dialog
                    open={showCreateWizard}
                    onOpenChange={(open) => { if (!open) { setShowCreateWizard(false); setWizardStep(1); setWizardForm({ source: 'ai', name: '', description: '', category: '', style: '', feature_tags: '', intent: '', repo_url: '', repo_branch: 'main', repo_path: '', preset: '', industry: 'real_estate', image_prompts: { exterior: '', interior: '', lifestyle: '', people: '', neighborhood: '' }, validate_responsiveness: true }); } }}
                    title="Create Template"
                >
                    <div style={{ padding: '16px', minWidth: '400px' }}>
                        {wizardStep === 1 && (
                            <div>
                                <p style={{ marginBottom: '12px', fontSize: '13px' }}>Source</p>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    <button type="button" onClick={() => setWizardForm(f => ({ ...f, source: 'ai' }))} style={{ padding: '10px 16px', border: '1px solid', borderColor: wizardForm.source === 'ai' ? '#2563eb' : '#e2e8f0', background: wizardForm.source === 'ai' ? '#eff6ff' : 'white', borderRadius: '8px', cursor: 'pointer' }}>AI Generated</button>
                                    <button type="button" onClick={() => setWizardForm(f => ({ ...f, source: 'git' }))} style={{ padding: '10px 16px', border: '1px solid', borderColor: wizardForm.source === 'git' ? '#2563eb' : '#e2e8f0', background: wizardForm.source === 'git' ? '#eff6ff' : 'white', borderRadius: '8px', cursor: 'pointer' }}>Git Repository</button>
                                </div>
                            </div>
                        )}
                        {wizardStep === 2 && (
                            <div style={{ display: 'grid', gap: '12px' }}>
                                <label style={{ fontSize: '13px' }}>Name <input type="text" value={wizardForm.name} onChange={e => setWizardForm(f => ({ ...f, name: e.target.value }))} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} required /></label>
                                <label style={{ fontSize: '13px' }}>Description <textarea value={wizardForm.description} onChange={e => setWizardForm(f => ({ ...f, description: e.target.value }))} rows={2} placeholder="Short description shown in template list and overview" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', resize: 'vertical' }} /></label>
                                <label style={{ fontSize: '13px' }}>Category <input type="text" value={wizardForm.category} onChange={e => setWizardForm(f => ({ ...f, category: e.target.value }))} placeholder="e.g. Residential" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} /></label>
                                <label style={{ fontSize: '13px' }}>Style <input type="text" value={wizardForm.style} onChange={e => setWizardForm(f => ({ ...f, style: e.target.value }))} placeholder="e.g. Modern" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} /></label>
                                <label style={{ fontSize: '13px' }}>Industry
                                    <select value={wizardForm.industry} onChange={e => setWizardForm(f => ({ ...f, industry: e.target.value }))} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}>
                                        <option value="real_estate">Real Estate</option>
                                        <option value="property_management">Property Management</option>
                                    </select>
                                </label>
                                <label style={{ fontSize: '13px' }}>Feature tags (comma-separated) <input type="text" value={wizardForm.feature_tags} onChange={e => setWizardForm(f => ({ ...f, feature_tags: e.target.value }))} placeholder="gallery, contact, map" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} /></label>
                                <div style={{ marginTop: '8px', padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                                    <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '4px', color: '#475569' }}>Image prompts (optional)</div>
                                    <p style={{ margin: '0 0 10px', fontSize: '11px', color: '#64748b', lineHeight: 1.4 }}>Short text descriptions used to guide AI when generating or selecting images for this template (e.g. &quot;Modern glass-fronted building with landscaped entrance&quot; for Exterior). Leave blank to skip. They help previews and client sites look consistent and professional.</p>
                                    {(['exterior', 'interior', 'lifestyle', 'people', 'neighborhood'] as const).map(k => (
                                        <label key={k} style={{ display: 'block', fontSize: '12px', marginBottom: '6px' }}>
                                            {k.charAt(0).toUpperCase() + k.slice(1)} <input type="text" value={wizardForm.image_prompts[k] || ''} onChange={e => setWizardForm(f => ({ ...f, image_prompts: { ...f.image_prompts, [k]: e.target.value } }))} placeholder={`e.g. ${k} imagery`} style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #cbd5e1', marginTop: '2px' }} />
                                        </label>
                                    ))}
                                </div>
                            </div>
                        )}
                        {wizardStep === 3 && (
                            <div style={{ display: 'grid', gap: '12px' }}>
                                {wizardForm.source === 'ai' ? (
                                    <label style={{ fontSize: '13px' }}>Template intent <textarea value={wizardForm.intent} onChange={e => setWizardForm(f => ({ ...f, intent: e.target.value }))} rows={3} placeholder="e.g. Modern property listing with gallery, enquiry form" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} /></label>
                                ) : (
                                    <>
                                        <label style={{ fontSize: '13px' }}>Repo URL <input type="text" value={wizardForm.repo_url} onChange={e => setWizardForm(f => ({ ...f, repo_url: e.target.value }))} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} /></label>
                                        <label style={{ fontSize: '13px' }}>Branch <input type="text" value={wizardForm.repo_branch} onChange={e => setWizardForm(f => ({ ...f, repo_branch: e.target.value }))} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} /></label>
                                        <label style={{ fontSize: '13px' }}>Repo path <input type="text" value={wizardForm.repo_path} onChange={e => setWizardForm(f => ({ ...f, repo_path: e.target.value }))} placeholder="optional" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} /></label>
                                    </>
                                )}
                            </div>
                        )}
                        {wizardStep === 4 && (
                            <div>
                                <p style={{ marginBottom: '12px', fontSize: '13px' }}>Preset Category <span style={{ color: '#dc2626' }}>*</span></p>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                                    {['Residential Modern', 'Corporate Trust', 'Luxury Lifestyle'].map(p => (
                                        <button key={p} type="button" onClick={() => setWizardForm(f => ({ ...f, preset: p }))} style={{ padding: '10px', border: '1px solid', borderColor: wizardForm.preset === p ? '#2563eb' : '#e2e8f0', background: wizardForm.preset === p ? '#eff6ff' : 'white', borderRadius: '8px', cursor: 'pointer', textAlign: 'left' }}>{p}</button>
                                    ))}
                                </div>
                                {!wizardForm.preset && <p style={{ margin: '0 0 12px', fontSize: '12px', color: '#dc2626' }}>Select a Preset Category to continue.</p>}
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={wizardForm.validate_responsiveness} onChange={e => setWizardForm(f => ({ ...f, validate_responsiveness: e.target.checked }))} />
                                    Validate responsiveness after creating (run viewport/mobile check when template is ready)
                                </label>
                            </div>
                        )}
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
                            <button type="button" onClick={() => setWizardStep(s => Math.max(1, s - 1))} style={{ padding: '8px 16px', border: '1px solid #e2e8f0', borderRadius: '6px', background: 'white', cursor: 'pointer' }}>Back</button>
                            {wizardStep < 4 ? (
                                <button type="button" onClick={() => setWizardStep(s => s + 1)} style={{ padding: '8px 16px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>Next</button>
                            ) : (
                                <button
                                    type="button"
                                    disabled={wizardStep === 4 && !wizardForm.preset}
                                    onClick={async () => {
                                        const tags = wizardForm.feature_tags.split(',').map(x => x.trim()).filter(Boolean);
                                        const presetPayload: Record<string, unknown> = {};
                                        if (wizardForm.preset === 'Residential Modern') {
                                            presetPayload.pages_json = [{ slug: 'home', title: 'Home', sections: ['hero', 'cta'] }, { slug: 'contact', title: 'Contact', sections: ['form'] }];
                                            presetPayload.required_inputs_json = ['logo', 'images', 'copy_text'];
                                            presetPayload.optional_inputs_json = ['floor_plans'];
                                            presetPayload.default_config_json = { colors: { primary: '#2563eb', secondary: '#1e40af', accent: '#3b82f6' } };
                                            presetPayload.rules_json = [];
                                        } else if (wizardForm.preset === 'Corporate Trust') {
                                            presetPayload.pages_json = [{ slug: 'home', title: 'Home', sections: ['hero', 'cta'] }, { slug: 'about', title: 'About', sections: [] }, { slug: 'contact', title: 'Contact', sections: ['form'] }];
                                            presetPayload.required_inputs_json = ['logo', 'copy_text'];
                                            presetPayload.optional_inputs_json = ['images'];
                                            presetPayload.default_config_json = { colors: { primary: '#0f766e', secondary: '#134e4a', accent: '#2dd4bf' } };
                                            presetPayload.rules_json = [];
                                        } else if (wizardForm.preset === 'Luxury Lifestyle') {
                                            presetPayload.pages_json = [{ slug: 'home', title: 'Home', sections: ['hero', 'gallery', 'cta'] }, { slug: 'contact', title: 'Contact', sections: ['form'] }];
                                            presetPayload.required_inputs_json = ['logo', 'images', 'copy_text'];
                                            presetPayload.optional_inputs_json = ['floor_plans', 'virtual_tours'];
                                            presetPayload.default_config_json = { colors: { primary: '#78350f', secondary: '#92400e', accent: '#f59e0b' } };
                                            presetPayload.rules_json = [];
                                        }
                                        const payload: any = { name: wizardForm.name, description: (wizardForm.description || '').trim() || null, intent: wizardForm.intent || null, source_type: wizardForm.source, feature_tags_json: tags.length ? tags : undefined, category: wizardForm.preset || wizardForm.category || null, style: wizardForm.style || null, ...presetPayload };
                                        const imagePromptsFiltered: Record<string, string> = {};
                                        Object.entries(wizardForm.image_prompts || {}).forEach(([k, v]) => { if (v && String(v).trim()) imagePromptsFiltered[k] = String(v).trim(); });
                                        payload.meta_json = { industry: wizardForm.industry || 'real_estate', image_prompts: Object.keys(imagePromptsFiltered).length ? imagePromptsFiltered : undefined };
                                        if (wizardForm.source === 'git') {
                                            payload.repo_url = wizardForm.repo_url;
                                            payload.default_branch = wizardForm.repo_branch;
                                            payload.repo_path = wizardForm.repo_path || null;
                                        }
                                        try {
                                            await configurationAPI.createTemplate(payload);
                                            setSuccess('Template created. Generate blueprint for homepage (hero + 3–5 features + CTA) and 5+ internal pages with SEO content.');
                                            setShowCreateWizard(false);
                                            setWizardStep(1);
                                            setWizardForm({ source: 'ai', name: '', description: '', category: '', style: '', feature_tags: '', intent: '', repo_url: '', repo_branch: 'main', repo_path: '', preset: '', industry: 'real_estate', image_prompts: { exterior: '', interior: '', lifestyle: '', people: '', neighborhood: '' }, validate_responsiveness: true });
                                            loadData();
                                        } catch (err: any) {
                                            setError(err.response?.data?.detail || 'Failed to create template');
                                        }
                                    }}
                                    style={{ padding: '8px 16px', background: '#10b981', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
                                >
                                    Create
                                </button>
                            )}
                        </div>
                    </div>
                </Dialog>
                )}

                <Dialog open={fixBlueprintModalOpen} onOpenChange={setFixBlueprintModalOpen} title="Fix Blueprint – Suggestions">
                    <div style={{ padding: '16px', maxWidth: '560px' }}>
                        {fixBlueprintLoading && (
                            <p style={{ margin: 0, color: '#64748b' }}>Getting AI suggestions…</p>
                        )}
                        {!fixBlueprintLoading && fixBlueprintSuggestions && (
                            <>
                                <p style={{ margin: '0 0 16px', fontSize: '14px', lineHeight: 1.5 }}>{fixBlueprintSuggestions.plain_language_summary}</p>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', fontSize: '13px', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={fixBlueprintShowTechnical} onChange={e => setFixBlueprintShowTechnical(e.target.checked)} />
                                    Show technical details
                                </label>
                                {fixBlueprintShowTechnical && fixBlueprintSuggestions.technical_details && (
                                    <div style={{ marginBottom: '12px', padding: '12px', background: '#f1f5f9', borderRadius: '8px', fontSize: '12px', whiteSpace: 'pre-wrap' }}>{fixBlueprintSuggestions.technical_details}</div>
                                )}
                                {(fixBlueprintSuggestions.code_snippets?.length ?? 0) > 0 && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '8px', color: '#475569' }}>Suggested commands / code</div>
                                        {fixBlueprintSuggestions.code_snippets!.map((s, i) => (
                                            <div key={i} style={{ marginBottom: '8px', padding: '12px', background: '#1e293b', color: '#e2e8f0', borderRadius: '8px', fontFamily: 'monospace', fontSize: '12px', overflow: 'auto' }}>
                                                <div style={{ marginBottom: '4px', color: '#94a3b8' }}>{s.title}</div>
                                                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{s.code}</pre>
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {(fixBlueprintSuggestions.interim_actions?.length ?? 0) > 0 && (
                                    <div style={{ marginBottom: '12px' }}>
                                        <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '6px', color: '#475569' }}>In the meantime</div>
                                        <ul style={{ margin: 0, paddingLeft: '20px' }}>{fixBlueprintSuggestions.interim_actions!.map((a, i) => <li key={i} style={{ marginBottom: '4px' }}>{a}</li>)}</ul>
                                    </div>
                                )}
                                <button type="button" onClick={() => { setTemplateDetailSubTab('blueprint'); setFixBlueprintModalOpen(false); }} style={{ marginTop: '8px', padding: '8px 16px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '6px', fontSize: '13px', cursor: 'pointer' }}>Go to Blueprint</button>
                            </>
                        )}
                    </div>
                </Dialog>

                <Dialog
                    open={previewModalOpen}
                    onOpenChange={(open) => {
                        setPreviewModalOpen(open);
                        if (!open) {
                            setPreviewTemplate(null);
                        }
                    }}
                    title={previewTemplate ? `Preview: ${previewTemplate.name}` : 'Template Preview'}
                >
                    {!previewTemplate ? (
                        <div style={{ padding: '16px' }}>No template selected.</div>
                    ) : (
                        <div style={{ display: 'grid', gap: '12px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ fontSize: '12px', color: '#64748b' }}>Status</div>
                                    <span style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '12px', fontWeight: 600, ...getPreviewStatusStyle(getPreviewStatusLabel(previewTemplate)) }}>
                                        {getPreviewStatusLabel(previewTemplate)}
                                    </span>
                                    <div style={{ marginTop: '6px', fontSize: '11px', color: '#64748b' }}>
                                        Preview mode: {getPreviewModeLabel()}
                                    </div>
                                </div>
                                <div style={{ fontSize: '12px', color: '#64748b' }}>
                                    Last generated: {previewTemplate.preview_last_generated_at ? new Date(previewTemplate.preview_last_generated_at).toLocaleString() : '—'}
                                </div>
                            </div>

                            {previewTemplate.preview_status === 'failed' && (
                                <div style={{ padding: '12px', background: '#fee2e2', borderRadius: '8px', color: '#991b1b' }}>
                                    {previewTemplate.preview_error || 'Preview generation failed.'}
                                </div>
                            )}

                            <div style={{ display: 'flex', gap: '8px' }}>
                                {(() => {
                                    const isGitTemplate = previewTemplate.source_type === 'git' || (!previewTemplate.source_type && !!previewTemplate.repo_url);
                                    return (
                                        <>
                                {previewTemplate.preview_status === 'generating' || previewPolling ? (
                                    <button disabled style={{ padding: '8px 16px', background: '#e2e8f0', color: '#475569', border: 'none', borderRadius: '6px' }}>
                                        Generating...
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => handleGeneratePreview(previewTemplate)}
                                        disabled={isGitTemplate || !canEditTemplates || !previewTemplate.blueprint_json}
                                        title={!previewTemplate.blueprint_json ? 'Generate blueprint first' : ''}
                                        style={{
                                            padding: '8px 16px',
                                            background: '#2563eb',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: (isGitTemplate || !canEditTemplates || !previewTemplate.blueprint_json) ? 'not-allowed' : 'pointer',
                                            opacity: isGitTemplate || !canEditTemplates ? 0.6 : 1,
                                        }}
                                    >
                                        {previewTemplate.preview_status === 'ready' ? 'Regenerate Preview' : 'Generate Preview'}
                                    </button>
                                )}
                                {(getPreviewIframeUrl(previewTemplate) || getTemplatePreviewUrl(previewTemplate)) && (
                                    <a
                                        href={getPreviewIframeUrl(previewTemplate) || getTemplatePreviewUrl(previewTemplate)!}
                                        target="_blank"
                                        rel="noreferrer"
                                        style={{ padding: '8px 16px', border: '1px solid #2563eb', color: '#2563eb', borderRadius: '6px', fontSize: '12px', textDecoration: 'none' }}
                                    >
                                        Open Preview
                                    </a>
                                )}
                                        </>
                                    );
                                })()}
                            </div>

                            {previewTemplate.preview_status === 'generating' && previewPolling && (
                                <div style={{ fontSize: '12px', color: '#64748b' }}>Generating preview… polling for updates.</div>
                            )}

                            {previewTemplate.preview_status === 'ready' && (getPreviewIframeUrl(previewTemplate) || previewTemplate.preview_url) && (
                                <iframe
                                    title="Template Preview"
                                    src={getPreviewIframeUrl(previewTemplate) || previewTemplate.preview_url!}
                                    style={{ width: '100%', height: '420px', border: '1px solid #e2e8f0', borderRadius: '8px' }}
                                />
                            )}
                        </div>
                    )}
                </Dialog>

                {activeConfigTab === 'sla' && (
                <section style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginTop: '24px' }}>
                    <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <PageHeader
                            title="SLA Configuration"
                            purpose="Define target durations and warning thresholds by stage."
                            affects="Affects alerts, escalations, and delivery performance reporting."
                            variant="section"
                        />
                        {renderDirtyDot('sla_config')}
                        {renderStatusChip('sla_config')}
                    </div>
                    {!canEditSla && (
                        <p style={{ marginTop: 0, marginBottom: '16px', color: '#64748b', fontSize: '12px' }}>
                            Only Admin can change this setting.
                        </p>
                    )}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                        {slaDrafts.map(config => (
                            <div key={config.stage} style={{ background: '#f8fafc', borderRadius: '12px', padding: '16px', border: '1px solid #e2e8f0' }}>
                                <h3 style={{ fontSize: '14px', fontWeight: 600, textTransform: 'capitalize', marginBottom: '8px' }}>
                                    {config.stage.replace(/_/g, ' ')}
                                </h3>
                                <div style={{ display: 'grid', gap: '8px' }}>
                                    <label style={{ fontSize: '12px', color: '#64748b' }}>
                                        Default Days
                                        <input
                                            type="number"
                                            value={config.default_days}
                                            onChange={(e) => handleSlaChange(config.stage, { default_days: Number(e.target.value) })}
                                            disabled={!canEditSla}
                                            style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditSla ? 1 : 0.6 }}
                                        />
                                    </label>
                                    <label style={{ fontSize: '12px', color: '#64748b' }}>
                                        Warning Days
                                        <input
                                            type="number"
                                            value={config.warning_threshold_days}
                                            onChange={(e) => handleSlaChange(config.stage, { warning_threshold_days: Number(e.target.value) })}
                                            disabled={!canEditSla}
                                            style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditSla ? 1 : 0.6 }}
                                        />
                                    </label>
                                    <label style={{ fontSize: '12px', color: '#64748b' }}>
                                        Critical Days
                                        <input
                                            type="number"
                                            value={config.critical_threshold_days}
                                            onChange={(e) => handleSlaChange(config.stage, { critical_threshold_days: Number(e.target.value) })}
                                            disabled={!canEditSla}
                                            style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditSla ? 1 : 0.6 }}
                                        />
                                    </label>
                                </div>
                            </div>
                        ))}
                    </div>
                    <div style={{ marginTop: '16px' }}>
                        <button
                            onClick={handleSaveSlaConfigs}
                            disabled={savingSla || !canEditSla}
                            style={{ padding: '8px 24px', background: '#2563eb', color: 'white', borderRadius: '6px', border: 'none', cursor: canEditSla ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: '13px', opacity: savingSla || !canEditSla ? 0.7 : 1 }}
                        >
                            {savingSla ? 'Saving...' : 'Save SLA'}
                        </button>
                    </div>
                </section>
                )}

                {activeConfigTab === 'thresholds' && (
                <section style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginTop: '24px' }}>
                    <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <PageHeader
                            title="Global Thresholds"
                            purpose="Configure pass scores and Lighthouse thresholds used across stages."
                            affects="Affects pass/fail gating and rework triggers."
                            variant="section"
                        />
                        {renderDirtyDot('thresholds')}
                        {renderStatusChip('thresholds')}
                    </div>
                    {!canEditThresholds && (
                        <p style={{ marginTop: 0, marginBottom: '12px', color: '#64748b', fontSize: '12px' }}>
                            Only Admin can change this setting.
                        </p>
                    )}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '16px' }}>
                        <label style={{ fontSize: '12px', color: '#64748b' }}>
                            Build Pass Score
                            <input
                                type="number"
                                value={globalThresholds.build_pass_score}
                                onChange={(e) => setGlobalThresholds(prev => ({ ...prev, build_pass_score: Number(e.target.value) }))}
                                disabled={!canEditThresholds}
                                style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditThresholds ? 1 : 0.6 }}
                            />
                        </label>
                        <label style={{ fontSize: '12px', color: '#64748b' }}>
                            QA Pass Score
                            <input
                                type="number"
                                value={globalThresholds.qa_pass_score}
                                onChange={(e) => setGlobalThresholds(prev => ({ ...prev, qa_pass_score: Number(e.target.value) }))}
                                disabled={!canEditThresholds}
                                style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditThresholds ? 1 : 0.6 }}
                            />
                        </label>
                        <label style={{ fontSize: '12px', color: '#64748b' }}>
                            Axe Max Critical
                            <input
                                type="number"
                                value={globalThresholds.axe_max_critical}
                                onChange={(e) => setGlobalThresholds(prev => ({ ...prev, axe_max_critical: Number(e.target.value) }))}
                                disabled={!canEditThresholds}
                                style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditThresholds ? 1 : 0.6 }}
                            />
                        </label>
                    </div>
                    <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '16px' }}>
                        <label style={{ fontSize: '12px', color: '#64748b' }}>
                            Lighthouse Performance
                            <input
                                type="number"
                                step="0.1"
                                value={globalThresholds.lighthouse_min.performance}
                                onChange={(e) =>
                                    setGlobalThresholds(prev => ({
                                        ...prev,
                                        lighthouse_min: { ...prev.lighthouse_min, performance: Number(e.target.value) },
                                    }))
                                }
                                disabled={!canEditThresholds}
                                style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditThresholds ? 1 : 0.6 }}
                            />
                        </label>
                        <label style={{ fontSize: '12px', color: '#64748b' }}>
                            Lighthouse Accessibility
                            <input
                                type="number"
                                step="0.1"
                                value={globalThresholds.lighthouse_min.accessibility}
                                onChange={(e) =>
                                    setGlobalThresholds(prev => ({
                                        ...prev,
                                        lighthouse_min: { ...prev.lighthouse_min, accessibility: Number(e.target.value) },
                                    }))
                                }
                                disabled={!canEditThresholds}
                                style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditThresholds ? 1 : 0.6 }}
                            />
                        </label>
                        <label style={{ fontSize: '12px', color: '#64748b' }}>
                            Lighthouse SEO
                            <input
                                type="number"
                                step="0.1"
                                value={globalThresholds.lighthouse_min.seo}
                                onChange={(e) =>
                                    setGlobalThresholds(prev => ({
                                        ...prev,
                                        lighthouse_min: { ...prev.lighthouse_min, seo: Number(e.target.value) },
                                    }))
                                }
                                disabled={!canEditThresholds}
                                style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditThresholds ? 1 : 0.6 }}
                            />
                        </label>
                        <label style={{ fontSize: '12px', color: '#64748b' }}>
                            Lighthouse Best Practices
                            <input
                                type="number"
                                step="0.1"
                                value={globalThresholds.lighthouse_min.best_practices}
                                onChange={(e) =>
                                    setGlobalThresholds(prev => ({
                                        ...prev,
                                        lighthouse_min: { ...prev.lighthouse_min, best_practices: Number(e.target.value) },
                                    }))
                                }
                                disabled={!canEditThresholds}
                                style={{ width: '100%', padding: '6px', borderRadius: '4px', border: '1px solid #cbd5e1', opacity: canEditThresholds ? 1 : 0.6 }}
                            />
                        </label>
                    </div>
                    <div style={{ marginTop: '16px' }}>
                        <button
                            onClick={handleSaveThresholds}
                            disabled={savingThresholds || !canEditThresholds}
                            style={{ padding: '8px 24px', background: '#2563eb', color: 'white', borderRadius: '6px', border: 'none', cursor: canEditThresholds ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: '13px', opacity: savingThresholds || !canEditThresholds ? 0.7 : 1 }}
                        >
                            {savingThresholds ? 'Saving...' : 'Save Thresholds'}
                        </button>
                    </div>
                </section>
                )}

                {activeConfigTab === 'preview_strategy' && (
                <section style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginTop: '24px' }}>
                    <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <PageHeader
                            title="Preview Strategy"
                            purpose="Select how preview artifacts are served."
                            affects="Affects how template previews are generated and served."
                            variant="section"
                        />
                        {renderDirtyDot('preview_strategy')}
                        {renderStatusChip('preview_strategy')}
                    </div>
                    <p style={{ marginTop: 0, marginBottom: '16px', color: '#475569', fontSize: '13px', maxWidth: '560px' }}>
                        <strong>Static Preview</strong> pre-builds HTML and serves it from cache for fast loading; best for quick checks. <strong>Live Preview</strong> builds the template in a production-like environment so the preview matches the final site more closely, at the cost of slower load times.
                    </p>
                    {!canEditPreviewStrategy && (
                        <p style={{ marginTop: 0, marginBottom: '12px', color: '#64748b', fontSize: '12px' }}>
                            Only Admin can change this setting.
                        </p>
                    )}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
                        {[
                            {
                                value: 'serve_static_preview',
                                label: 'Static Preview (fast, cached)',
                                helper: 'Generates a static HTML preview and serves it quickly.',
                            },
                            {
                                value: 'zip_only',
                                label: 'Live Preview (accurate, dynamic)',
                                helper: 'Shows a dynamic preview closer to production, but slower.',
                            },
                        ].map((option) => (
                            <label
                                key={option.value}
                                style={{
                                    border: '1px solid #e2e8f0',
                                    borderRadius: '10px',
                                    padding: '12px',
                                    display: 'flex',
                                    gap: '10px',
                                    alignItems: 'flex-start',
                                    background: previewStrategy === option.value ? '#eff6ff' : 'white',
                                    opacity: canEditPreviewStrategy ? 1 : 0.6,
                                    cursor: canEditPreviewStrategy ? 'pointer' : 'not-allowed',
                                }}
                            >
                                <input
                                    type="radio"
                                    name="preview-strategy"
                                    value={option.value}
                                    checked={previewStrategy === option.value}
                                    onChange={(e) => setPreviewStrategy(e.target.value)}
                                    disabled={!canEditPreviewStrategy}
                                    style={{ marginTop: '4px' }}
                                />
                                <div>
                                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#0f172a' }}>{option.label}</div>
                                    <div style={{ fontSize: '12px', color: '#64748b' }}>{option.helper}</div>
                                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                                        Value: <span style={{ fontFamily: 'monospace' }}>{option.value}</span>
                                    </div>
                                </div>
                            </label>
                        ))}
                    </div>
                    <div style={{ marginTop: '12px' }}>
                        <button
                            onClick={handleSavePreviewStrategy}
                            disabled={savingPreview || !canEditPreviewStrategy}
                            style={{ padding: '8px 16px', background: '#2563eb', color: 'white', borderRadius: '6px', border: 'none', cursor: canEditPreviewStrategy ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: '13px', opacity: savingPreview || !canEditPreviewStrategy ? 0.7 : 1 }}
                        >
                            {savingPreview ? 'Saving...' : 'Save Strategy'}
                        </button>
                    </div>
                </section>
                )}

                {activeConfigTab === 'hitl_gates' && (
                <section style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginTop: '24px' }}>
                    <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <PageHeader
                            title="Global HITL Gates"
                            purpose="Choose how much human approval is required before stages can proceed. Default for all projects is No HITL."
                            affects="When a gate is on: JobRun ends as NEEDS_HUMAN, StageOutput gets gate_decision=PAUSED_HITL, and the project does not auto-advance until approved."
                            variant="section"
                        />
                        {renderDirtyDot('hitl_gates')}
                        {renderStatusChip('hitl_gates')}
                    </div>
                    {!canEditGates && (
                        <p style={{ marginTop: 0, marginBottom: '12px', color: '#64748b', fontSize: '12px' }}>
                            Only Admin can change this setting.
                        </p>
                    )}
                    {(() => {
                        const gateKeys = ['onboarding', 'assignment', 'build', 'test', 'defect_validation', 'complete'] as const;
                        const gates = globalStageGates as Record<string, boolean>;
                        const countOn = gateKeys.filter(k => gates[k]).length;
                        const preset = countOn === 0 ? 'none' : countOn === gateKeys.length ? 'full' : 'partial';
                        const setPreset = (p: 'none' | 'partial' | 'full') => {
                            if (p === 'none') setGlobalStageGates(prev => ({ ...prev, ...Object.fromEntries(gateKeys.map(k => [k, false])) }));
                            if (p === 'full') setGlobalStageGates(prev => ({ ...prev, ...Object.fromEntries(gateKeys.map(k => [k, true])) }));
                        };
                        return (
                            <>
                                <div style={{ marginBottom: '16px' }}>
                                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>HITL mode</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                        <button type="button" onClick={() => setPreset('none')} disabled={!canEditGates} title="No human approval required at any stage (default for new projects)" style={{ padding: '8px 14px', borderRadius: '8px', border: '2px solid', fontSize: '13px', fontWeight: 600, cursor: canEditGates ? 'pointer' : 'not-allowed', background: preset === 'none' ? '#eff6ff' : 'white', borderColor: preset === 'none' ? '#2563eb' : '#e2e8f0', color: preset === 'none' ? '#1d4ed8' : '#475569' }}>No HITL</button>
                                        <button type="button" onClick={() => setPreset('full')} disabled={!canEditGates} title="Require approval at every stage" style={{ padding: '8px 14px', borderRadius: '8px', border: '2px solid', fontSize: '13px', fontWeight: 600, cursor: canEditGates ? 'pointer' : 'not-allowed', background: preset === 'full' ? '#fef3c7' : 'white', borderColor: preset === 'full' ? '#f59e0b' : '#e2e8f0', color: preset === 'full' ? '#92400e' : '#475569' }}>Full HITL</button>
                                        <span style={{ alignSelf: 'center', fontSize: '12px', color: '#94a3b8' }}>Partial = choose stages below</span>
                                    </div>
                                </div>
                                <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>Stages requiring approval (partial mode)</div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px' }}>
                                    {[
                                        { key: 'onboarding', label: 'Onboarding' },
                                        { key: 'assignment', label: 'Assignment' },
                                        { key: 'build', label: 'Build' },
                                        { key: 'test', label: 'Test' },
                                        { key: 'defect_validation', label: 'Defect Validation' },
                                        { key: 'complete', label: 'Complete' },
                                    ].map(({ key, label }) => (
                                        <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '10px 12px' }}>
                                            <input
                                                type="checkbox"
                                                checked={(globalStageGates as any)[key]}
                                                onChange={(e) => setGlobalStageGates(prev => ({ ...prev, [key]: e.target.checked }))}
                                                disabled={!canEditGates}
                                            />
                                            <span style={{ fontSize: '14px', fontWeight: 600 }}>{label}</span>
                                        </label>
                                    ))}
                                </div>
                                <div style={{ marginTop: '16px' }}>
                                    <button
                                        onClick={handleSaveGlobalGates}
                                        disabled={savingGates || !canEditGates}
                                        style={{ padding: '8px 24px', background: '#2563eb', color: 'white', borderRadius: '6px', border: 'none', cursor: canEditGates ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: '13px', opacity: savingGates || !canEditGates ? 0.7 : 1 }}
                                    >
                                        {savingGates ? 'Saving...' : 'Save Global Gates'}
                                    </button>
                                </div>
                            </>
                        );
                    })()}
                </section>
                )}

                {activeConfigTab === 'learning' && (
                <section style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginTop: '24px' }}>
                    <PageHeader title="Learning Proposals" purpose="Policy suggestions from delivery outcomes and sentiment (shadow mode). Review and apply manually." variant="section" />
                    <LearningProposalsPanel />
                </section>
                )}

                {getDirtySections().length > 0 && (
                    <div
                        style={{
                            position: 'sticky',
                            bottom: 0,
                            marginTop: '24px',
                            background: '#0f172a',
                            color: 'white',
                            padding: '12px 16px',
                            borderRadius: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '12px',
                            boxShadow: '0 -4px 12px rgba(15, 23, 42, 0.2)',
                            zIndex: 5,
                        }}
                    >
                        <div style={{ fontSize: '13px' }}>
                            Unsaved changes in:{' '}
                            <strong>
                                {getDirtySections()
                                    .map((key) => sectionLabels[key])
                                    .join(', ')}
                            </strong>
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                                onClick={handleSaveAll}
                                style={{
                                    padding: '8px 14px',
                                    borderRadius: '8px',
                                    border: 'none',
                                    background: '#2563eb',
                                    color: 'white',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    fontSize: '13px',
                                }}
                            >
                                Save all
                            </button>
                            <button
                                onClick={handleDiscardAll}
                                style={{
                                    padding: '8px 14px',
                                    borderRadius: '8px',
                                    border: '1px solid #94a3b8',
                                    background: 'transparent',
                                    color: '#e2e8f0',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    fontSize: '13px',
                                }}
                            >
                                Discard changes
                            </button>
                        </div>
                    </div>
                )}
            </main>
        </div>
        </RequireCapability>
    );
}
