'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { configurationAPI, configAPI } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import { Dialog } from '@/components/ui/dialog';
import PageHeader from '@/components/PageHeader';

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
    const [newTemplate, setNewTemplate] = useState({
        name: '',
        repo_url: '',
        default_branch: 'main',
        description: '',
        intent: '',
        features_input: '',
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
            if (templatesRes) setTemplates(templatesData);
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
        try {
            await configurationAPI.generateTemplatePreview(template.id);
            updateTemplateInState({ ...template, preview_status: 'generating', preview_error: null });
            setSuccess('Preview generation started');
            pollTemplatePreview(template.id);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start preview generation');
        }
    };

    const handleOpenPreview = (template: TemplateRegistry) => {
        setPreviewTemplate(template);
        setPreviewModalOpen(true);
        if (template.preview_status === 'generating') {
            pollTemplatePreview(template.id);
        }
    };

    const handleSetDefaultTemplate = async (id: string) => {
        try {
            if (!canEditTemplates) {
                setError('Only Admin can change this setting.');
                return;
            }
            setDefaultTemplateId(id);
            await saveDefaultTemplate(id);
            setSuccess('Default template updated');
            setValidationErrors('templates_default', []);
        } catch (err: any) {
            const message = isConflictError(err)
                ? conflictMessage
                : (err.response?.data?.detail || 'Failed to update default template');
            setError(message);
            setValidationErrors('templates_default', [message]);
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
            setError(err.response?.data?.detail || 'Failed to delete template');
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
                <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1d4ed8', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px', fontSize: '13px' }}>
                    Client feedback in Sentiments can be used to refine templates, SLAs, and quality thresholds.
                </div>

                {error && <div className="alert alert-error">{error}</div>}
                {success && <div className="alert alert-success">{success}</div>}

                <section style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
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
                        <button
                            className="btn-primary"
                            onClick={() => {
                                if (!canEditTemplates) return;
                                if (showAddForm) {
                                    setShowAddForm(false);
                                    setNewTemplate({ name: '', repo_url: '', default_branch: 'main', description: '', intent: '', features_input: '' });
                                    setTemplateSource('ai');
                                    setShowAdvanced(false);
                                } else {
                                    setShowAddForm(true);
                                }
                            }}
                            disabled={!canEditTemplates}
                            style={{
                                padding: '8px 16px',
                                background: '#2563eb',
                                color: 'white',
                                borderRadius: '6px',
                                border: 'none',
                                cursor: canEditTemplates ? 'pointer' : 'not-allowed',
                                fontSize: '13px',
                                opacity: canEditTemplates ? 1 : 0.6,
                            }}
                        >
                            {showAddForm ? 'Cancel' : '+ Add Template'}
                        </button>
                    </div>
                    {!canEditTemplates && (
                        <p style={{ marginTop: 0, marginBottom: '16px', color: '#64748b', fontSize: '12px' }}>
                            Only Admin can change this setting.
                        </p>
                    )}
                    <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <label style={{ fontSize: '13px', color: '#64748b' }}>Default Template</label>
                        <select
                            value={defaultTemplateId}
                            onChange={(e) => handleSetDefaultTemplate(e.target.value)}
                            disabled={!canEditTemplates}
                            style={{
                                padding: '6px 10px',
                                borderRadius: '6px',
                                border: '1px solid #cbd5e1',
                                fontSize: '13px',
                                opacity: canEditTemplates ? 1 : 0.6,
                                cursor: canEditTemplates ? 'pointer' : 'not-allowed',
                            }}
                        >
                            <option value="">Select default</option>
                            {templates.filter(t => t.is_published).map((t) => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                        </select>
                    </div>

                    {showAddForm && canEditTemplates && (
                        <form onSubmit={handleAddTemplate} style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e2e8f0' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                                <label style={{ fontSize: '13px', fontWeight: 600 }}>Template Source</label>
                                <div style={{ display: 'inline-flex', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
                                    <button
                                        type="button"
                                        onClick={() => setTemplateSource('ai')}
                                        style={{
                                            padding: '6px 12px',
                                            border: 'none',
                                            background: templateSource === 'ai' ? '#2563eb' : 'transparent',
                                            color: templateSource === 'ai' ? 'white' : '#475569',
                                            cursor: 'pointer',
                                            fontSize: '12px',
                                        }}
                                    >
                                        AI Generated
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setTemplateSource('git')}
                                        style={{
                                            padding: '6px 12px',
                                            border: 'none',
                                            background: templateSource === 'git' ? '#2563eb' : 'transparent',
                                            color: templateSource === 'git' ? 'white' : '#475569',
                                            cursor: 'pointer',
                                            fontSize: '12px',
                                        }}
                                    >
                                        Git Repository
                                    </button>
                                </div>
                                {templateSource === 'ai' && (
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>Preview generated by AI. Repo/Branch optional.</span>
                                )}
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                                <div>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Name</label>
                                    <input
                                        required
                                        type="text"
                                        value={newTemplate.name}
                                        onChange={e => setNewTemplate({ ...newTemplate, name: e.target.value })}
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                    />
                                </div>
                                <div style={{ gridColumn: 'span 2' }}>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                                        Template Intent {templateSource === 'ai' && <span style={{ color: '#2563eb' }}>(recommended)</span>}
                                    </label>
                                    <textarea
                                        rows={3}
                                        value={newTemplate.intent}
                                        onChange={e => setNewTemplate({ ...newTemplate, intent: e.target.value })}
                                        placeholder="Modern property listing site for rentals with gallery, enquiry form, map."
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                    />
                                </div>
                                <div style={{ gridColumn: 'span 2' }}>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Description</label>
                                    <input
                                        type="text"
                                        value={newTemplate.description}
                                        onChange={e => setNewTemplate({ ...newTemplate, description: e.target.value })}
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                    />
                                </div>
                                <div style={{ gridColumn: 'span 2' }}>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Features</label>
                                    <input
                                        type="text"
                                        value={newTemplate.features_input}
                                        onChange={e => setNewTemplate({ ...newTemplate, features_input: e.target.value })}
                                        placeholder="Gallery grid, map section, contact form, pricing table"
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                    />
                                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>Comma-separated list.</span>
                                </div>
                            </div>

                            <div style={{ marginBottom: '16px' }}>
                                <button
                                    type="button"
                                    onClick={() => setShowAdvanced(!showAdvanced)}
                                    style={{ padding: '6px 12px', border: '1px solid #e2e8f0', background: 'white', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}
                                >
                                    {showAdvanced || templateSource === 'git' ? 'Hide Advanced' : 'Show Advanced'}
                                </button>
                            </div>

                            {(templateSource === 'git' || showAdvanced) && (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                                    <div style={{ gridColumn: 'span 2' }}>
                                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                                            Repo URL {templateSource === 'git' && <span style={{ color: '#ef4444' }}>*</span>}
                                        </label>
                                        <input
                                            required={templateSource === 'git'}
                                            type="text"
                                            value={newTemplate.repo_url}
                                            onChange={e => setNewTemplate({ ...newTemplate, repo_url: e.target.value })}
                                            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Default Branch</label>
                                        <input
                                            type="text"
                                            value={newTemplate.default_branch}
                                            onChange={e => setNewTemplate({ ...newTemplate, default_branch: e.target.value })}
                                            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                        />
                                    </div>
                                </div>
                            )}

                            <div style={{ padding: '12px', borderRadius: '8px', border: '1px dashed #cbd5e1', background: '#f8fafc', marginBottom: '16px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                                    <strong style={{ fontSize: '13px' }}>Preview</strong>
                                    <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '12px', background: '#f1f5f9', color: '#475569' }}>
                                        Not generated
                                    </span>
                                </div>
                                <p style={{ fontSize: '12px', color: '#64748b', margin: 0 }}>
                                    Save the template to enable AI preview generation.
                                </p>
                            </div>
                            <button type="submit" style={{ padding: '8px 24px', background: '#10b981', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
                                Save Template
                            </button>
                        </form>
                    )}

                    <div style={{ overflowX: 'auto' }}>
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
                                {previewTemplate.preview_status === 'generating' ? (
                                    <button disabled style={{ padding: '8px 16px', background: '#e2e8f0', color: '#475569', border: 'none', borderRadius: '6px' }}>
                                        Generating...
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => handleGeneratePreview(previewTemplate)}
                                        disabled={isGitTemplate || !canEditTemplates}
                                        style={{
                                            padding: '8px 16px',
                                            background: '#2563eb',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '6px',
                                            cursor: isGitTemplate || !canEditTemplates ? 'not-allowed' : 'pointer',
                                            opacity: isGitTemplate || !canEditTemplates ? 0.6 : 1,
                                        }}
                                    >
                                        {previewTemplate.preview_status === 'ready' ? 'Regenerate Preview' : 'Generate Preview'}
                                    </button>
                                )}
                                {getTemplatePreviewUrl(previewTemplate) && (
                                    <a
                                        href={getTemplatePreviewUrl(previewTemplate)}
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

                            {previewTemplate.preview_status === 'ready' && previewTemplate.preview_url && (
                                <iframe
                                    title="Template Preview"
                                    src={previewTemplate.preview_url}
                                    style={{ width: '100%', height: '420px', border: '1px solid #e2e8f0', borderRadius: '8px' }}
                                />
                            )}
                        </div>
                    )}
                </Dialog>

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

                <section style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginTop: '24px' }}>
                    <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <PageHeader
                            title="Global HITL Gates"
                            purpose="Toggle stage gates to require human approval globally."
                            affects="Affects approval requirements before a stage can proceed."
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
                </section>
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
