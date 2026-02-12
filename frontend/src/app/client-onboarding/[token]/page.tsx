'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { clientAPI } from '@/lib/api';

interface Template {
    id: string;
    name: string;
    description: string;
    preview_url: string;
    preview_thumbnail_url?: string;
    colors: { primary: string; secondary: string; accent: string };
    features: string[];
    actual_web_url?: string;
    category?: string;
    style?: string;
    pages_json?: Array<{ slug?: string; title?: string; sections?: unknown[] }>;
    required_inputs_json?: string[];
    optional_inputs_json?: string[];
}

interface PricingTier {
    words: number;
    price: number;
    description: string;
}

interface RequirementsData {
    project_summary?: string;
    project_notes?: string;
    phase_number?: string;
    template_mode?: 'NEW' | 'CLONE';
    template_references?: string;
    brand_guidelines_available?: boolean;
    brand_guidelines_details?: string;
    color_selection?: string;
    color_notes?: string;
    font_selection?: string;
    font_notes?: string;
    custom_graphic_notes_enabled?: boolean;
    custom_graphic_notes?: string;
    navigation_notes_option?: string;
    navigation_notes?: string;
    stock_images_reference?: string;
    floor_plan_images?: string;
    sitemap?: string;
    virtual_tours?: string;
    poi_categories?: string;
    specials_enabled?: boolean;
    specials_details?: string;
    copy_scope_notes?: string;
    pages?: string;
    domain_type?: string;
    vanity_domains?: string;
    call_tracking_plan?: string;
}

interface OnboardingFormData {
    project_title: string;
    project_id: string;
    completion_percentage: number;
    missing_fields: string[];
    submitted_at?: string | null;
    missing_fields_eta_json?: Record<string, string>;
    client_preview?: { preview_url?: string; status?: string } | null;
    data: {
        logo_url: string | null;
        logo_file_path: string | null;
        images: any[];
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
        selected_template_id: string | null;
        theme_colors: Record<string, string>;
        contacts: Array<{ name: string; email: string; role: string; is_primary: boolean }>;
        requirements?: RequirementsData;
        submitted_at?: string | null;
        missing_fields_eta_json?: Record<string, string>;
    };
    templates: Template[];
    copy_pricing: PricingTier[];
}

const ReviewModal = ({ onClose, onConfirm, phases, requirements }: any) => {
    return (
        <div className="modal-overlay" onClick={onClose} style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', zIndex: 2000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            backdropFilter: 'blur(4px)'
        }}>
            <div className="modal-content review-modal" onClick={e => e.stopPropagation()} style={{
                background: 'white',
                borderRadius: '16px',
                width: '90%',
                maxWidth: '600px',
                maxHeight: '90vh',
                overflowY: 'auto',
                boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)',
                display: 'flex',
                flexDirection: 'column'
            }}>
                <div className="review-header" style={{ padding: '24px', borderBottom: '1px solid #e2e8f0' }}>
                    <h2 style={{ margin: 0, fontSize: '20px', color: '#1e293b' }}>Review & Submit</h2>
                    <p style={{ margin: '4px 0 0', color: '#64748b' }}>Please check your progress before final submission.</p>
                </div>
                <div className="review-body" style={{ padding: '24px' }}>
                    <div style={{ marginBottom: '24px' }}>
                        <h4 style={{ margin: '0 0 12px', fontSize: '14px', textTransform: 'uppercase', color: '#94a3b8' }}>Completion Summary</h4>
                        <div className="phase-summary-list">
                            {phases.map((phase: any) => {
                                const phaseFields = requirements.filter((r: any) => phase.fields.includes(r.id));
                                const completed = phaseFields.filter((r: any) => r.provided).length;
                                const total = phaseFields.length;
                                const isComplete = completed === total && total > 0;

                                return (
                                    <div key={phase.id} className={`review-phase-item ${isComplete ? 'complete' : 'incomplete'}`} style={{
                                        display: 'flex', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid #f1f5f9'
                                    }}>
                                        <span style={{ fontWeight: 500, color: '#334155' }}>{phase.title}</span>
                                        <span className="status" style={{ color: isComplete ? '#10b981' : '#f59e0b', fontWeight: 500 }}>
                                            {isComplete ? '✓ Complete' : `${completed}/${total} steps`}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    <div className="timeline-info" style={{ background: '#f0f9ff', padding: '16px', borderRadius: '8px', border: '1px solid #bae6fd' }}>
                        <h4 style={{ margin: '0 0 8px', color: '#0369a1' }}>What happens next?</h4>
                        <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '14px', color: '#0c4a6e' }}>
                            <li>Our team will review your submission within 24 hours.</li>
                            <li>We'll schedule a kickoff call if we have any questions.</li>
                            <li>Development begins immediately after approval.</li>
                        </ul>
                    </div>
                </div>
                <div className="review-footer" style={{
                    padding: '20px 24px', background: '#f8fafc', borderTop: '1px solid #e2e8f0',
                    display: 'flex', justifyContent: 'flex-end', gap: '12px'
                }}>
                    <button className="btn-secondary" onClick={onClose} style={{
                        padding: '10px 20px', borderRadius: '8px', border: '1px solid #e2e8f0', background: 'white', color: '#64748b', cursor: 'pointer'
                    }}>Keep Editing</button>
                    <button className="btn-primary" onClick={onConfirm} style={{
                        padding: '10px 20px', borderRadius: '8px', border: 'none', background: '#2563eb', color: 'white', cursor: 'pointer'
                    }}>Confirm & Submit Project</button>
                </div>
            </div>
        </div>
    );
};

const PHASE_DEFINITIONS = [
    { id: 'phase-1', title: 'Project Basics', fields: ['project_summary', 'project_notes', 'phase_number', 'contacts'] },
    { id: 'phase-2', title: 'Brand & Visual Assets', fields: ['logo', 'images', 'copy', 'copy_scope', 'theme', 'template_mode', 'template_references'] },
    { id: 'phase-3', title: 'Design Preferences', fields: ['brand_guidelines', 'color_selection', 'font_selection', 'custom_graphics', 'navigation'] },
    { id: 'phase-4', title: 'Property Content', fields: ['floor_plans', 'virtual_tours', 'poi', 'stock_images', 'sitemap', 'specials'] },
    { id: 'phase-5', title: 'Compliance & Legal', fields: ['wcag', 'privacy'] },
    { id: 'phase-6', title: 'Website Fundamentals', fields: ['pages', 'domain', 'vanity', 'call_tracking'] }
];

const PhaseSection = ({
    id,
    title,
    isExpanded,
    onToggle,
    completion,
    children
}: {
    id: string;
    title: string;
    isExpanded: boolean;
    onToggle: () => void;
    completion: number;
    children: React.ReactNode;
}) => {
    return (
        <div
            id={id}
            className={`phase-section ${isExpanded ? 'active' : ''}`}
            style={{
                background: 'white',
                border: isExpanded ? '1px solid #bfdbfe' : '1px solid #cbd5e1',
                borderLeft: isExpanded ? '4px solid #2563eb' : '1px solid #cbd5e1',
                borderRadius: '12px',
                marginBottom: '16px',
                overflow: 'hidden',
                boxShadow: isExpanded ? '0 10px 15px -3px rgba(0, 0, 0, 0.1)' : '0 2px 4px rgba(0,0,0,0.05)',
                transition: 'all 0.2s'
            }}
        >
            <div
                className="phase-header"
                onClick={onToggle}
                style={{
                    padding: '16px 24px',
                    cursor: 'pointer',
                    background: isExpanded ? '#eff6ff' : '#f8fafc',
                    borderBottom: '1px solid transparent'
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                    <div className="phase-title">
                        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#1e293b' }}>{title}</h3>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div className="phase-progress" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div className="progress-bar-small" style={{ width: '100px', height: '6px', background: '#e2e8f0', borderRadius: '3px' }}>
                                <div className="fill" style={{ width: `${completion}%`, height: '100%', background: '#10b981', transition: 'width 0.3s' }} />
                            </div>
                            <span className="percentage" style={{ fontSize: '13px', color: '#64748b' }}>{Math.round(completion)}%</span>
                        </div>
                        <div className={`toggle-icon ${isExpanded ? 'expanded' : ''}`} style={{ fontSize: '18px', color: '#64748b' }}>
                            {isExpanded ? '−' : '+'}
                        </div>
                    </div>
                </div>
            </div>
            {isExpanded && (
                <div className="phase-content" style={{ padding: '24px' }}>
                    {children}
                </div>
            )}
        </div>
    );
};

const ChecklistPanel = ({
    requirements,
    onScrollTo
}: {
    requirements: any[];
    onScrollTo: (phaseId: string) => void;
}) => {
    const getPhaseStatus = (phaseId: string) => {
        const phaseDef = PHASE_DEFINITIONS.find(p => p.id === phaseId);
        if (!phaseDef) return { completed: 0, total: 0 };

        const phaseFields = requirements.filter(r => phaseDef.fields.includes(r.id));
        const completed = phaseFields.filter(r => r.provided).length;
        return { completed, total: phaseFields.length, isComplete: completed === phaseFields.length && phaseFields.length > 0 };
    };

    const overallCompleted = requirements.filter(r => r.provided).length;
    const overallTotal = requirements.length;

    return (
        <div className="checklist-panel">
            <div className="checklist-header">
                <h3>What's left to complete</h3>
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#64748b' }}>
                    {overallCompleted}/{overallTotal} items completed
                </div>
                <div style={{ height: '4px', background: '#e2e8f0', borderRadius: '2px', marginTop: '4px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', background: '#2563eb', width: `${(overallCompleted / overallTotal) * 100}%`, transition: 'width 0.3s' }} />
                </div>
            </div>
            <div className="checklist-content">
                {PHASE_DEFINITIONS.map(phase => {
                    const status = getPhaseStatus(phase.id);
                    if (status.total === 0) return null; // Skip if no fields in this phase (shouldn't happen with correct mapping)

                    return (
                        <div
                            key={phase.id}
                            className={`checklist-item ${status.isComplete ? 'completed' : ''}`}
                            onClick={() => onScrollTo(phase.id)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: '12px',
                                padding: '12px 16px',
                                borderBottom: '1px solid #f1f5f9',
                                cursor: 'pointer',
                                background: status.isComplete ? '#effdf5' : 'transparent',
                                color: status.isComplete ? '#10b981' : '#475569'
                            }}
                        >
                            <div style={{
                                width: '16px',
                                height: '16px',
                                border: `1.5px solid ${status.isComplete ? '#10b981' : '#cbd5e1'}`,
                                borderRadius: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                                background: status.isComplete ? '#10b981' : 'transparent',
                                color: 'white',
                                fontSize: '10px'
                            }}>
                                {status.isComplete && '✓'}
                            </div>
                            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <span style={{ fontWeight: 600, fontSize: '14px', color: '#1e293b' }}>{phase.title.split(':')[0]}</span>
                                <span style={{ fontSize: '12px', fontWeight: 500, color: status.isComplete ? '#10b981' : '#64748b' }}>
                                    {status.completed}/{status.total}
                                </span>
                            </div>
                            <div style={{ fontSize: '18px', color: '#cbd5e1', marginLeft: '8px' }}>›</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default function ClientOnboardingPage() {
    const params = useParams();
    const token = params.token as string;

    const [formData, setFormData] = useState<OnboardingFormData | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);


    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [missingFieldsEta, setMissingFieldsEta] = useState<Record<string, string>>({});
    const [previewImage, setPreviewImage] = useState<string | null>(null);
    const [showChatbot, setShowChatbot] = useState(true);
    const [chatMessages, setChatMessages] = useState<any[]>([
        { text: "👋 Hi there! I'm here to help you complete your onboarding. Do you have any questions about the form or requirements?", isBot: true, sender: 'bot' }
    ]);

    const setupWebSocket = () => {
        if (!formData?.project_id) return null;

        // Construct WS URL
        // In local dev: ws://localhost:8000/api/ai/ws/chat/{id}
        // In prod: wss://delivery-backend-vvbf.onrender.com/api/ai/ws/chat/{id}

        let baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        if (baseUrl.startsWith('http')) {
            baseUrl = baseUrl.replace(/^http/, 'ws');
        }

        const wsUrl = `${baseUrl}/api/ai/ws/chat/${formData.project_id}`;
        console.log('Connecting to WS (Client):', wsUrl);

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WS Connected (Client)');
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                setChatMessages(prev => {
                    // Avoid duplicates by ID
                    if (prev.find(l => l.id === message.id)) return prev;

                    // Deduplicate optimistic user messages (match by text and sender)
                    if (message.sender === 'user') {
                        const optimisticIndex = prev.findIndex(l =>
                            l.sender === 'user' &&
                            l.text === message.message &&
                            !l.id
                        );

                        if (optimisticIndex !== -1) {
                            // Replace optimistic message with real one
                            const newArr = [...prev];
                            newArr[optimisticIndex] = {
                                ...newArr[optimisticIndex],
                                id: message.id,
                                created_at: message.created_at
                            };
                            return newArr;
                        }
                    }

                    return [...prev, {
                        text: message.message,
                        isBot: message.sender !== 'user',
                        sender: message.sender,
                        id: message.id,
                        created_at: message.created_at
                    }];
                });
            } catch (e) {
                console.error('WS Message Parse Error', e);
            }
        };

        ws.onclose = () => {
            console.log('WS Disconnected (Client)');
        };

        return ws;
    };

    useEffect(() => {
        if (!formData?.project_id) return;

        // Initial Fetch
        const fetchChat = async () => {
            try {
                const res = await clientAPI.getChatLogs(formData.project_id);
                if (res.data && res.data.length > 0) {
                    const mapped = res.data.map((log: any) => ({
                        text: log.message,
                        isBot: log.sender !== 'user',
                        sender: log.sender,
                        id: log.id,
                        created_at: log.created_at
                    }));
                    setChatMessages(mapped);
                }
            } catch (e) {
                // Silent fail
            }
        };
        fetchChat();

        // Setup WebSocket
        const ws = setupWebSocket();

        return () => {
            if (ws) ws.close();
        };
    }, [formData?.project_id]);


    const [chatInput, setChatInput] = useState('');

    // Phase 2 & 3 Enhancements State
    const [showBrandGuidelines, setShowBrandGuidelines] = useState(false);
    const [showReviewModal, setShowReviewModal] = useState(false);
    const [browseTemplatesOpen, setBrowseTemplatesOpen] = useState(false);
    const [templateDetailDrawer, setTemplateDetailDrawer] = useState<Template | null>(null);
    const [templateGalleryFilters, setTemplateGalleryFilters] = useState<{ category?: string; style?: string; tag?: string }>({});
    const [submissionStatus, setSubmissionStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');

    // Effect to initialize toggles based on data
    useEffect(() => {
        if (formData?.data) {
            if (formData.data.requirements?.brand_guidelines_available) setShowBrandGuidelines(true);
        }
    }, [formData]);

    const handleSitemapPreset = (preset: string) => {
        if (!formData) return;
        const current = formData.data.requirements?.navigation_notes || '';
        const newLine = current ? '\n' : '';
        updateRequirements({ navigation_notes: current + newLine + '- ' + preset });
    };

    const handleInitialSubmit = () => {
        setShowReviewModal(true);
    };

    const confirmSubmit = async () => {
        setSubmissionStatus('submitting');
        await submitClientForm();
        setSubmissionStatus('success'); // OR error, handled in submitClientForm via alert currently
        setShowReviewModal(false);
    };

    const chatContainerRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [chatMessages, showChatbot]);

    const handleSendMessage = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!chatInput.trim()) return;

        const userMsgText = chatInput;
        const newUserMsg = { text: userMsgText, isBot: false, sender: 'user' };
        setChatMessages(prev => [...prev, newUserMsg]);
        setChatInput('');

        try {
            // Prepare context from form data
            const context = { ...(formData?.data || {}), project_id: formData?.project_id };

            // Show typing indicator or just wait (optimistic UI could handle 'typing...')
            // For now, we just await.

            const response = await clientAPI.consultAI(userMsgText, context);

            if (response.data.response) {
                // Do not add manually - wait for WebSocket
                // setChatMessages...
            }
        } catch (error) {
            console.error("AI Consult Error:", error);
            setChatMessages(prev => [...prev, {
                text: "I'm having trouble connecting to the consultant right now. Please try again later.",
                isBot: true
            }]);
        }
    };

    const logoInputRef = useRef<HTMLInputElement>(null);
    const variantInputRef = useRef<HTMLInputElement>(null);
    const imageInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        loadFormData();
    }, [token]);

    const loadFormData = async () => {
        try {
            const res = await clientAPI.getOnboardingForm(token);
            setFormData(res.data);
            setMissingFieldsEta(res.data.missing_fields_eta_json || res.data.data?.missing_fields_eta_json || {});
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load form. The link may be invalid or expired.');
        } finally {
            setLoading(false);
        }
    };

    const saveFormData = async (updates: Partial<OnboardingFormData['data']>) => {
        if (!formData) return;
        setSaving(true);
        setError('');

        try {
            const res = await clientAPI.updateOnboardingForm(token, updates);
            setSuccess('Changes saved successfully!');
            setTimeout(() => setSuccess(''), 3000);

            // Update local state
            setFormData(prev => prev ? {
                ...prev,
                completion_percentage: res.data.completion_percentage,
                missing_fields: res.data.missing_fields || prev.missing_fields,
                data: { ...prev.data, ...updates }
            } : null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save changes');
        } finally {
            setSaving(false);
        }
    };


    const [activePhase, setActivePhase] = useState<string | null>('phase-1');

    // Dynamic AI Hints
    const hintedPhasesRef = useRef<Set<string>>(new Set());
    const hintedFieldsRef = useRef<Set<string>>(new Set());
    const fieldHintTimerRef = useRef<number | null>(null);

    // Section-level hints
    useEffect(() => {
        const fetchHint = async () => {
            if (!activePhase) return;
            if (hintedPhasesRef.current.has(activePhase)) return;

            const phaseDef = PHASE_DEFINITIONS.find(p => p.id === activePhase);
            if (!phaseDef) return;

            hintedPhasesRef.current.add(activePhase);

            try {
                const response = await clientAPI.consultAI(
                    `I am starting the "${phaseDef.title}" section. Give me a brief overview of what's important here.`,
                    formData?.data
                );

                setChatMessages(prev => [...prev, {
                    text: `💡 **${phaseDef.title}**: ${response.data.response}`,
                    isBot: true
                }]);
            } catch (err) {
                console.error('Failed to fetch AI hint:', err);
            }
        };
        fetchHint();
    }, [activePhase]);

    // Field-level hints (debounced 800ms so quick tab-through doesn't trigger a request per field)
    const handleFieldFocus = (fieldId: string, label: string) => {
        if (hintedFieldsRef.current.has(fieldId)) return;
        if (fieldHintTimerRef.current) clearTimeout(fieldHintTimerRef.current);
        fieldHintTimerRef.current = window.setTimeout(async () => {
            fieldHintTimerRef.current = null;
            if (hintedFieldsRef.current.has(fieldId)) return;
            hintedFieldsRef.current.add(fieldId);
            try {
                const response = await clientAPI.consultAI(
                    `I am filling out the "${label}" field. What specific details should I include? Keep it short and helpful.`,
                    formData?.data
                );
                setChatMessages(prev => [...prev, {
                    text: `✍️ **Tip for ${label}**:\n${response.data.response}`,
                    isBot: true
                }]);
            } catch (err) {
                console.error('Failed to fetch field hint:', err);
            }
        }, 800);
    };

    const togglePhase = (phaseId: string) => {
        setActivePhase(prev => prev === phaseId ? null : phaseId);
    };

    const scrollToPhase = (phaseId: string) => {
        setActivePhase(phaseId);
        setTimeout(() => {
            const element = document.getElementById(phaseId);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }, 100);
    };

    // Helper to update local state without triggering API save (for controlled inputs)
    const updateLocalData = (updates: Partial<OnboardingFormData['data']>) => {
        setFormData(prev => prev ? {
            ...prev,
            data: { ...prev.data, ...updates }
        } : null);
    };

    const updateRequirements = (updates: Partial<RequirementsData>) => {
        if (!formData) return;
        const current = formData.data.requirements || {};
        const next = { ...current, ...updates };
        saveFormData({ requirements: next });
    };

    // Update requirements locally (for onChange)
    const updateRequirementsLocal = (updates: Partial<RequirementsData>) => {
        if (!formData) return;
        const current = formData.data.requirements || {};
        const next = { ...current, ...updates };
        updateLocalData({ requirements: next });
    };

    const updateContacts = (contacts: Array<{ name: string; email: string; role: string; is_primary: boolean }>) => {
        updateLocalData({ contacts });
        saveFormData({ contacts });
    };

    const addContactRow = () => {
        if (!formData) return;
        const contacts = [...(formData.data.contacts || [])];
        contacts.push({ name: '', email: '', role: '', is_primary: contacts.length === 0 });
        updateContacts(contacts);
    };

    const updateContactField = (index: number, updates: Partial<{ name: string; email: string; role: string; is_primary: boolean }>) => {
        if (!formData) return;
        const contacts = [...(formData.data.contacts || [])];
        contacts[index] = { ...contacts[index], ...updates };
        updateContacts(contacts);
    };

    const setPrimaryContact = (index: number) => {
        if (!formData) return;
        const contacts = (formData.data.contacts || []).map((c, i) => ({
            ...c,
            is_primary: i === index
        }));
        updateContacts(contacts);
    };

    const hasValue = (val: any) => {
        if (val === null || val === undefined) return false;
        if (typeof val === 'string') return val.trim().length > 0;
        if (Array.isArray(val)) return val.length > 0;
        if (typeof val === 'boolean') return true; // Boolean true/false counts as answered if not null
        return true;
    };

    const getAllRequirements = () => {
        if (!formData) return [];
        const req = formData.data.requirements || {};
        const data = formData.data;

        const navigationProvided = req.navigation_notes_option
            ? (req.navigation_notes_option === 'Custom' ? hasValue(req.navigation_notes) : true)
            : false;
        const templateModeProvided = hasValue(req.template_mode) || !!data.selected_template_id;
        const templateReferencesProvided = req.template_mode === 'NEW'
            ? hasValue(req.template_references)
            : templateModeProvided;

        const brandGuidelinesAvailable = data.requirements?.brand_guidelines_available;
        const brandGuidelinesProvided =
            brandGuidelinesAvailable === true
                ? hasValue(req.brand_guidelines_details)
                : brandGuidelinesAvailable === false;

        const items = [
            // Assets
            { id: 'logo', label: 'Company Logo', provided: !!(data.logo_url || data.logo_file_path), eta: missingFieldsEta['Company Logo'] },
            { id: 'images', label: 'Website Images', provided: (data.images?.length || 0) > 0, eta: missingFieldsEta['Website Images'] },
            { id: 'copy', label: 'Copy Text', provided: !!(data.copy_text || data.use_custom_copy), eta: missingFieldsEta['Copy Text'] },
            { id: 'wcag', label: 'Accessibility Choice', provided: data.wcag_confirmed === true, eta: missingFieldsEta['WCAG Compliance'] },
            { id: 'privacy', label: 'Privacy Policy', provided: !!(data.privacy_policy_url || data.privacy_policy_text), eta: missingFieldsEta['Privacy Policy'] },
            { id: 'theme', label: 'Theme Selection', provided: !!(data.selected_template_id), eta: missingFieldsEta['Theme Preference'] },
            { id: 'contacts', label: 'Contacts', provided: (data.contacts || []).some(c => c.is_primary), eta: missingFieldsEta['Contacts'] },

            // Project Requirements
            { id: 'project_summary', label: 'Project Summary', provided: hasValue(req.project_summary), eta: missingFieldsEta['Project Summary'] },
            { id: 'project_notes', label: 'Project Notes', provided: hasValue(req.project_notes), eta: missingFieldsEta['Project Notes'] },
            { id: 'phase_number', label: 'Phase', provided: hasValue(req.phase_number), eta: missingFieldsEta['Phase'] },
            { id: 'template_mode', label: 'Template Mode', provided: templateModeProvided, eta: missingFieldsEta['Template Mode'] },
            { id: 'template_references', label: 'Template References', provided: templateReferencesProvided, eta: missingFieldsEta['Template References'] },
            { id: 'brand_guidelines', label: 'Brand Guidelines', provided: brandGuidelinesProvided, eta: missingFieldsEta['Brand Guidelines'] },
            { id: 'color_selection', label: 'Color Selection', provided: hasValue(req.color_selection), eta: missingFieldsEta['Color Selection'] },
            { id: 'font_selection', label: 'Font Selection', provided: hasValue(req.font_selection), eta: missingFieldsEta['Font Selection'] },
            { id: 'custom_graphics', label: 'Custom Graphics', provided: data.requirements?.custom_graphic_notes_enabled === true ? hasValue(req.custom_graphic_notes) : data.requirements?.custom_graphic_notes_enabled === false, eta: missingFieldsEta['Custom Graphics'] },
            { id: 'navigation', label: 'Navigation', provided: navigationProvided, eta: missingFieldsEta['Navigation'] },
            { id: 'stock_images', label: 'Stock Images', provided: hasValue(req.stock_images_reference) && req.stock_images_reference?.trim() !== 'No', eta: missingFieldsEta['Stock Images'] },
            { id: 'floor_plans', label: 'Floor Plans', provided: hasValue(req.floor_plan_images), eta: missingFieldsEta['Floor Plans'] },
            { id: 'sitemap', label: 'Sitemap', provided: hasValue(req.sitemap), eta: missingFieldsEta['Sitemap'] },
            { id: 'virtual_tours', label: 'Virtual Tours', provided: hasValue(req.virtual_tours), eta: missingFieldsEta['Virtual Tours'] },
            { id: 'poi', label: 'POI Categories', provided: hasValue(req.poi_categories), eta: missingFieldsEta['POI Categories'] },
            { id: 'specials', label: 'Specials', provided: data.requirements?.specials_enabled === true ? hasValue(req.specials_details) : data.requirements?.specials_enabled === false, eta: missingFieldsEta['Specials'] },
            { id: 'copy_scope', label: 'Copy Scope', provided: (data.use_custom_copy === false) || hasValue(req.copy_scope_notes), eta: missingFieldsEta['Copy Scope'] },
            { id: 'pages', label: 'Pages', provided: hasValue(req.pages), eta: missingFieldsEta['Pages'] },
            { id: 'domain', label: 'Domain Type', provided: hasValue(req.domain_type), eta: missingFieldsEta['Domain Type'] },
            { id: 'vanity', label: 'Vanity Domains', provided: hasValue(req.vanity_domains), eta: missingFieldsEta['Vanity Domains'] },
            { id: 'call_tracking', label: 'Call Tracking', provided: hasValue(req.call_tracking_plan), eta: missingFieldsEta['Call Tracking'] },
        ];
        return items;
    };

    const getBackendBaseUrl = () => {
        if (process.env.NEXT_PUBLIC_API_URL) {
            return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '');
        }
        if (typeof window !== 'undefined') {
            const hostname = window.location.hostname;
            if (hostname.includes('onrender.com')) {
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
        let cleanPath = path.replace(/^\.?\//, '');

        // If the path already has 'uploads/' at the start, don't duplicate it
        if (cleanPath.startsWith('uploads/')) {
            return `${baseUrl}/${cleanPath}`;
        }
        return `${baseUrl}/uploads/${cleanPath}`;
    };

    const handleDeleteImage = async (index: number) => {
        if (!window.confirm('Are you sure you want to delete this image?')) return;

        setSaving(true);
        try {
            const res = await clientAPI.deleteImage(token, index);
            setSuccess('Image deleted successfully');
            setFormData(prev => prev ? {
                ...prev,
                data: { ...prev.data, images: res.data.images }
            } : null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete image');
        } finally {
            setSaving(false);
        }
    };

    const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setSaving(true);
        try {
            await clientAPI.uploadLogo(token, file);
            setSuccess('Logo uploaded successfully!');
            await loadFormData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to upload logo');
        } finally {
            setSaving(false);
        }
    };

    const handleVariantUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        if (!files.length) return;

        setSaving(true);
        try {
            for (const file of files) {
                // Resize or rename to distinguish as variant
                const newName = `brand_variant_${file.name}`;
                const renamedFile = new File([file], newName, { type: file.type });
                await clientAPI.uploadImage(token, renamedFile);
            }
            setSuccess('Logo variant(s) added successfully!');
            await loadFormData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to upload variant(s)');
        } finally {
            setSaving(false);
            e.target.value = '';
        }
    };

    const handleDeleteLogo = async () => {
        if (!window.confirm('Are you sure you want to delete the logo?')) return;

        setSaving(true);
        try {
            await clientAPI.deleteLogo(token);
            setSuccess('Logo deleted successfully');
            setFormData(prev => prev ? {
                ...prev,
                data: { ...prev.data, logo_url: null, logo_file_path: null }
            } : null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete logo');
        } finally {
            setSaving(false);
        }
    };

    const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        if (!files.length) return;

        setSaving(true);
        try {
            for (const file of files) {
                await clientAPI.uploadImage(token, file);
            }
            setSuccess(`${files.length} image(s) uploaded successfully!`);
            await loadFormData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to upload image(s)');
        } finally {
            setSaving(false);
            e.target.value = '';
        }
    };

    const submitClientForm = async () => {
        if (!formData) return;
        setSaving(true);
        setError('');
        try {
            await clientAPI.submitOnboardingForm(token, { missing_fields_eta: missingFieldsEta });
            setSuccess('Form submitted successfully! Our Consultant team has been notified and will reach out to you.');
            await loadFormData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit form');
        } finally {
            setSaving(false);
        }
    };

    const setEtaInDays = (field: string, days: number) => {
        const targetDate = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
        const isoDate = targetDate.toISOString().slice(0, 10);
        setMissingFieldsEta(prev => ({ ...prev, [field]: isoDate }));
    };

    const phaseOptions = Array.from({ length: 9 }, (_, i) => `Phase ${i + 1}`);
    const colorOptions = [
        'Keep from Clone',
        'Match to live website',
        'Color codes',
        'Match to logo',
        'Brand guidelines',
        'Other'
    ];
    const fontOptions = ['Template default', 'Keep from clone', 'Other'];
    const navigationOptions = ['Match to clone', 'Match to template', 'Custom'];
    const domainTypeOptions = ['Single', 'Multi', 'Mix'];
    const callTrackingOptions = [
        'Unlimited 2500 (Advanced Call Tracking/call pooling) is auto-generated service',
        'Default 0 (no call tracking or 1 client provided CTN)',
        'Other'
    ];

    const selectTemplate = (templateId: string) => {
        const template = formData?.templates.find(t => t.id === templateId);
        if (template) {
            saveFormData({
                selected_template_id: templateId,
                theme_colors: template.colors
            });
        }
    };

    const selectCopyPricing = (tier: PricingTier) => {
        saveFormData({
            use_custom_copy: true,
            custom_copy_word_count: tier.words,
            custom_copy_final_price: tier.price
        });
    };

    if (loading) {
        return (
            <div className="loading-page">
                <div className="spinner" />
                <p>Loading your onboarding form...</p>
                <style jsx>{`
                    .loading-page {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    }
                    .spinner {
                        width: 48px;
                        height: 48px;
                        border: 4px solid #e2e8f0;
                        border-top-color: #2563eb;
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                    }
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                    p { margin-top: 16px; color: #64748b; }
                `}</style>
            </div>
        );
    }

    if (error && !formData) {
        return (
            <div className="error-page">
                <div className="error-card">
                    <div className="error-icon">⚠️</div>
                    <h1>Unable to Load Form</h1>
                    <p>{error}</p>
                    <p className="contact-info">Please contact your project manager for assistance.</p>
                </div>
                <style jsx>{`
                    .error-page {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                        padding: 20px;
                    }
                    .error-card {
                        background: white;
                        padding: 48px;
                        border-radius: 16px;
                        text-align: center;
                        max-width: 480px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                    }
                    .error-icon { font-size: 64px; margin-bottom: 16px; }
                    h1 { color: #dc2626; margin-bottom: 16px; }
                    p { color: #64748b; margin-bottom: 8px; }
                    .contact-info { font-size: 14px; }
                `}</style>
            </div>
        );
    }

    if (!formData) return null;

    return (
        <div className="client-page">
            <header className="page-header">
                <div className="header-content">
                    <h1>📋 Project Onboarding</h1>
                    <p className="project-name">{formData.project_title}</p>
                </div>
                <div className="completion-badge">
                    <div className="completion-ring">
                        <svg viewBox="0 0 36 36">
                            <path className="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                            <path
                                className="ring-fill"
                                strokeDasharray={`${Math.round((getAllRequirements().filter(i => i.provided).length / getAllRequirements().length) * 100) || 0}, 100`}
                                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            />
                        </svg>
                        <span className="ring-value">{Math.round((getAllRequirements().filter(i => i.provided).length / getAllRequirements().length) * 100) || 0}%</span>
                    </div>
                    <div className="completion-text">
                        <span className="completion-label">Complete</span>
                        <span className="items-count">
                            {getAllRequirements().filter(i => i.provided).length}/{getAllRequirements().length} items
                        </span>
                    </div>
                </div>
            </header>

            {/* Alerts */}
            {error && (
                <div className="alert alert-error" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>{error}</span>
                    <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', lineHeight: 1, padding: '0 4px' }}>×</button>
                </div>
            )}
            {success && (
                <div className="alert alert-success" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>{success}</span>
                    <button onClick={() => setSuccess('')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px', lineHeight: 1, padding: '0 4px' }}>×</button>
                </div>
            )}

            {(formData.submitted_at || success) && formData.client_preview && (
                <div className="alert alert-info" style={{ marginTop: 8 }}>
                    {formData.client_preview.status === 'ready' && formData.client_preview.preview_url ? (
                        <a href={formData.client_preview.preview_url} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600 }}>
                            View your draft site
                        </a>
                    ) : (
                        <span>Your draft site is being prepared. We will notify you when it is ready.</span>
                    )}
                </div>
            )}

            <div className="layout-container">
                <main className="main-content">
                    {/* Phase 1: Project Basics */}
                    <PhaseSection
                        id="phase-1"
                        title="Project Basics"
                        isExpanded={activePhase === 'phase-1'}
                        onToggle={() => togglePhase('phase-1')}
                        completion={(getAllRequirements().filter(r => PHASE_DEFINITIONS[0].fields.includes(r.id) && r.provided).length / PHASE_DEFINITIONS[0].fields.length) * 100}
                    >
                        <div className="form-group">
                            <label>Project Summary</label>
                            <textarea
                                value={formData.data.requirements?.project_summary || ''}
                                onChange={(e) => updateRequirementsLocal({ project_summary: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                onFocus={() => handleFieldFocus('project_summary', 'Project Summary')}
                                rows={3}
                                placeholder="Brief summary of the project requirements..."
                            />
                        </div>

                        <div className="form-group">
                            <label>Project Notes (applies to all locations)</label>
                            <textarea
                                value={formData.data.requirements?.project_notes || ''}
                                onChange={(e) => updateRequirementsLocal({ project_notes: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                onFocus={() => handleFieldFocus('project_notes', 'Project Notes')}
                                rows={3}
                                placeholder="Notes that apply to all locations..."
                            />
                        </div>

                        <div className="form-group">
                            <label>Phase #</label>
                            <select
                                value={formData.data.requirements?.phase_number || ''}
                                onChange={(e) => updateRequirements({ phase_number: e.target.value })}
                            >
                                <option value="">Select phase</option>
                                {phaseOptions.map(option => (
                                    <option key={option} value={option}>{option}</option>
                                ))}
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Primary Contact Information <span className="required">*</span></label>
                            <div className="contact-list">
                                {(formData.data.contacts || []).map((contact, idx) => (
                                    <div key={idx} className="contact-row">
                                        <input
                                            type="text"
                                            placeholder="Name"
                                            value={contact.name || ''}
                                            onChange={(e) => updateContactField(idx, { name: e.target.value })}
                                        />
                                        <input
                                            type="email"
                                            placeholder="Email"
                                            value={contact.email || ''}
                                            onChange={(e) => updateContactField(idx, { email: e.target.value })}
                                        />
                                        <input
                                            type="text"
                                            placeholder="Role"
                                            value={contact.role || ''}
                                            onChange={(e) => updateContactField(idx, { role: e.target.value })}
                                        />
                                        <label className="contact-primary">
                                            <input
                                                type="radio"
                                                name="primary_contact"
                                                checked={!!contact.is_primary}
                                                onChange={() => setPrimaryContact(idx)}
                                            />
                                            Primary
                                        </label>
                                    </div>
                                ))}
                                <button className="btn-add-contact" type="button" onClick={addContactRow}>
                                    + Add Contact
                                </button>
                            </div>
                        </div>
                    </PhaseSection>

                    {/* Phase 2: Brand & Visual Assets */}
                    <PhaseSection
                        id="phase-2"
                        title="Brand & Visual Assets"
                        isExpanded={activePhase === 'phase-2'}
                        onToggle={() => togglePhase('phase-2')}
                        completion={(getAllRequirements().filter(r => PHASE_DEFINITIONS[1].fields.includes(r.id) && r.provided).length / PHASE_DEFINITIONS[1].fields.length) * 100}
                    >
                        {/* Logo Section */}
                        <div className="form-section-inner" style={{ marginBottom: '32px' }}>
                            <h4 style={{ margin: '0 0 16px', fontSize: '15px' }}>Company Logo</h4>
                            <div className="upload-area">
                                {formData.data.logo_url || formData.data.logo_file_path ? (
                                    <div className="logo-preview-container">
                                        <div className="logo-preview-card" style={{
                                            border: '1px solid #e2e8f0',
                                            borderRadius: '8px',
                                            padding: '16px',
                                            boxShadow: '0 2px 4px -1px rgba(0,0,0,0.05)',
                                            background: 'white',
                                            display: 'flex',
                                            flexDirection: 'column',
                                            alignItems: 'center',
                                            position: 'relative'
                                        }}>
                                            <button
                                                className="btn-remove-logo-x"
                                                onClick={handleDeleteLogo}
                                                title="Remove logo"
                                                style={{
                                                    position: 'absolute', top: '8px', right: '8px',
                                                    background: '#fee2e2', color: '#ef4444',
                                                    border: 'none', borderRadius: '50%',
                                                    width: '24px', height: '24px', cursor: 'pointer',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                                                }}
                                            >
                                                ×
                                            </button>
                                            <img
                                                src={getAssetUrl(formData.data.logo_url || formData.data.logo_file_path)}
                                                alt="Company Logo"
                                                className="logo-thumbnail"
                                                onClick={() => setPreviewImage(getAssetUrl(formData.data.logo_url || formData.data.logo_file_path))}
                                                title="Click to preview"
                                                style={{ maxWidth: '100%', maxHeight: '120px', objectFit: 'contain', marginBottom: '12px' }}
                                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                            />
                                            <div className="logo-actions" style={{ width: '100%', textAlign: 'center' }}>
                                                <div className="preview-badge" style={{ fontSize: '12px', color: '#10b981', fontWeight: 600, marginBottom: '8px' }}>✓ Logo Uploaded</div>
                                                <div className="logo-btn-group" style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                                                    <button className="btn-replace" onClick={() => logoInputRef.current?.click()} style={{
                                                        fontSize: '12px', color: '#2563eb', background: '#eff6ff', border: '1px solid #bfdbfe',
                                                        borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', fontWeight: 500
                                                    }}>
                                                        Replace Primary
                                                    </button>
                                                    <button className="btn-add-variant" onClick={() => variantInputRef.current?.click()} style={{
                                                        fontSize: '12px', color: '#475569', background: 'white', border: '1px solid #cbd5e1',
                                                        borderRadius: '6px', padding: '6px 12px', cursor: 'pointer', fontWeight: 500
                                                    }}>
                                                        Add Variant
                                                    </button>
                                                </div>
                                            </div>

                                            {/* Render Variants inside the card */}
                                            {formData.data.images?.filter(img => (img.filename || '').startsWith('brand_variant_')).length > 0 && (
                                                <div className="logo-variants" style={{ marginTop: '16px', borderTop: '1px solid #f1f5f9', paddingTop: '12px', width: '100%' }}>
                                                    <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px', textAlign: 'left', fontWeight: 600 }}>VARIANTS</div>
                                                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                                        {formData.data.images?.filter(img => (img.filename || '').startsWith('brand_variant_')).map((img, i) => {
                                                            const url = getAssetUrl(img.url || img.file_path || (typeof img === 'string' ? img : ''));
                                                            // Find actua index in main array for deletion
                                                            const realIndex = formData.data.images.findIndex(x => x === img);
                                                            return (
                                                                <div key={i} style={{ position: 'relative', width: '60px', height: '60px', border: '1px solid #e2e8f0', borderRadius: '4px', padding: '4px' }}>
                                                                    <img
                                                                        src={url}
                                                                        alt="Variant"
                                                                        onClick={() => setPreviewImage(url)}
                                                                        style={{ width: '100%', height: '100%', objectFit: 'contain', cursor: 'pointer' }}
                                                                        onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                                                    />
                                                                    <button onClick={() => handleDeleteImage(realIndex)} style={{
                                                                        position: 'absolute', top: '-6px', right: '-6px', width: '16px', height: '16px', background: '#ef4444', color: 'white',
                                                                        borderRadius: '50%', border: 'none', fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer'
                                                                    }}>×</button>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="upload-placeholder" onClick={() => logoInputRef.current?.click()}>
                                        <span className="upload-icon">📤</span>
                                        <span>Click to upload logo</span>
                                    </div>
                                )}
                                <input
                                    ref={logoInputRef}
                                    type="file"
                                    accept="image/png,image/jpeg,image/svg+xml,image/webp"
                                    onChange={handleLogoUpload}
                                    hidden
                                />
                                <input
                                    ref={variantInputRef}
                                    type="file"
                                    accept="image/png,image/jpeg,image/svg+xml,image/webp"
                                    multiple
                                    onChange={handleVariantUpload}
                                    hidden
                                />
                            </div>
                        </div>

                        {/* Images Section */}
                        <div className="form-section-inner" style={{ marginBottom: '32px' }}>
                            <div className="section-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <h4 style={{ margin: 0, fontSize: '15px' }}>Website Images</h4>
                                <button className="btn-add-header" onClick={() => imageInputRef.current?.click()}>
                                    + Add Image
                                </button>
                            </div>
                            <div className="images-grid">
                                <div className="info-box-blue" style={{ gridColumn: '1/-1', marginBottom: '16px', background: '#eff6ff', padding: '16px', borderRadius: '8px', border: '1px solid #dbeafe' }}>
                                    <h5 style={{ margin: '0 0 8px 0', color: '#1e40af', fontSize: '14px' }}>Recommended Approach</h5>
                                    <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', color: '#1e3a8a' }}>
                                        <li><strong>Hero Image:</strong> High impact, wide aspect ratio (min 1920px wide).</li>
                                        <li><strong>Amenities:</strong> Pool, Gym, Lounge, Office spaces.</li>
                                        <li><strong>Interiors:</strong> Living room, Kitchen, Bedroom.</li>
                                    </ul>
                                </div>

                                {formData.data.images?.length === 0 && (
                                    <div className="upload-placeholder" onClick={() => imageInputRef.current?.click()}>
                                        <span className="upload-icon">📷</span>
                                        <span>No images uploaded yet. Click to add.</span>
                                        <span style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>JPG, PNG (Max 5MB)</span>
                                    </div>
                                )}
                                {formData.data.images?.filter(img => !(img.filename || '').startsWith('brand_variant_')).map((img, i) => {
                                    // Use original index logic is tricky with filter. Better to rely on object identity or just pass ID if available. 
                                    // But handleDeleteImage takes INDEX.
                                    // We must find the index in original array.
                                    const realIndex = formData.data.images.findIndex(x => x === img);
                                    const url = getAssetUrl(img.url || img.file_path || (typeof img === 'string' ? img : ''));
                                    return (
                                        <div key={i} className="image-card">
                                            <div className="image-preview">
                                                <img
                                                    src={url}
                                                    alt={img.filename || 'Uploaded image'}
                                                    onClick={() => setPreviewImage(url)}
                                                    style={{ cursor: 'pointer' }}
                                                    title="Click to preview"
                                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                                />
                                                <button
                                                    className="btn-delete"
                                                    onClick={() => handleDeleteImage(realIndex)}
                                                    title="Delete image"
                                                >
                                                    ×
                                                </button>
                                            </div>
                                            <div className="image-info">
                                                <span className="image-name">{img.filename || 'Website Image'}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                            <input
                                ref={imageInputRef}
                                type="file"
                                accept="image/*"
                                multiple
                                onChange={handleImageUpload}
                                hidden
                            />
                        </div>

                        {/* Copy Section */}
                        <div className="form-section-inner" style={{ marginBottom: '32px' }}>
                            <h4 style={{ margin: '0 0 16px', fontSize: '15px' }}>Website Copy</h4>
                            <div className="copy-options">
                                <label className="option-card">
                                    <input
                                        type="radio"
                                        name="copy_option"
                                        checked={!formData.data.use_custom_copy}
                                        onChange={() => saveFormData({ use_custom_copy: false })}
                                    />
                                    <div className="option-content">
                                        <h4>I'll Provide My Own Copy</h4>
                                        <p>Enter your website text below</p>
                                    </div>
                                </label>
                                <label className="option-card">
                                    <input
                                        type="radio"
                                        name="copy_option"
                                        checked={formData.data.use_custom_copy}
                                        onChange={() => saveFormData({ use_custom_copy: true })}
                                    />
                                    <div className="option-content">
                                        <h4>Request Custom Copywriting</h4>
                                        <p>Professional writers will create your content</p>
                                    </div>
                                </label>
                            </div>

                            {!formData.data.use_custom_copy ? (
                                <div className="copy-input">
                                    <label>Your Website Copy</label>
                                    <textarea
                                        value={formData.data.copy_text || ''}
                                        onChange={(e) => updateLocalData({ copy_text: e.target.value })}
                                        onBlur={() => saveFormData({ copy_text: formData.data.copy_text })}
                                        onFocus={() => handleFieldFocus('copy_text', 'Website Copy')}
                                        placeholder="Enter all your website text content here..."
                                        rows={6}
                                    />
                                </div>
                            ) : (
                                <div className="pricing-section">
                                    <div className="pricing-grid">
                                        {formData.copy_pricing.map((tier) => (
                                            <div
                                                key={tier.words}
                                                className={`pricing-card ${formData.data.custom_copy_word_count === tier.words ? 'selected' : ''}`}
                                                onClick={() => selectCopyPricing(tier)}
                                            >
                                                <div className="price">${tier.price}</div>
                                                <div className="tier-name">{tier.description}</div>
                                                {formData.data.custom_copy_word_count === tier.words && (
                                                    <div className="selected-badge">✓ Selected</div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="form-group" style={{ marginTop: '16px' }}>
                                <label>Copy Text Scope – Additional Notes</label>
                                <textarea
                                    value={formData.data.requirements?.copy_scope_notes || ''}
                                    onChange={(e) => updateRequirementsLocal({ copy_scope_notes: e.target.value })}
                                    onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                    onFocus={() => handleFieldFocus('copy_scope_notes', 'Copy Scope Notes')}
                                    rows={3}
                                    placeholder="Additional notes about copy scope..."
                                />
                            </div>
                        </div>

                        {/* Template Section */}
                        <div className="form-section-inner">
                            <h4 style={{ margin: '0 0 16px', fontSize: '15px' }}>Website Template</h4>
                            <div className="form-group">
                                <label>Template Direction</label>
                                <div className="template-btn-group" style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
                                    <button
                                        className={`btn-toggle ${formData.data.requirements?.template_mode !== 'NEW' ? 'active' : ''}`}
                                        onClick={() => updateRequirements({ template_mode: 'CLONE' })}
                                        style={{
                                            flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid',
                                            borderColor: formData.data.requirements?.template_mode !== 'NEW' ? '#2563eb' : '#cbd5e1',
                                            background: formData.data.requirements?.template_mode !== 'NEW' ? '#eff6ff' : 'white',
                                            color: formData.data.requirements?.template_mode !== 'NEW' ? '#1e40af' : '#64748b',
                                            fontWeight: 600, cursor: 'pointer'
                                        }}
                                    >
                                        Clone from Validated Template
                                    </button>
                                    <button
                                        className={`btn-toggle ${formData.data.requirements?.template_mode === 'NEW' ? 'active' : ''}`}
                                        onClick={() => updateRequirements({ template_mode: 'NEW' })}
                                        style={{
                                            flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid',
                                            borderColor: formData.data.requirements?.template_mode === 'NEW' ? '#2563eb' : '#cbd5e1',
                                            background: formData.data.requirements?.template_mode === 'NEW' ? '#eff6ff' : 'white',
                                            color: formData.data.requirements?.template_mode === 'NEW' ? '#1e40af' : '#64748b',
                                            fontWeight: 600, cursor: 'pointer'
                                        }}
                                    >
                                        New Custom Design
                                    </button>
                                </div>
                            </div>

                            {formData.data.requirements?.template_mode !== 'NEW' ? (
                                <>
                                <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                                    <button
                                        type="button"
                                        onClick={() => setBrowseTemplatesOpen(true)}
                                        style={{ padding: '10px 20px', borderRadius: '8px', border: '1px solid #2563eb', background: '#eff6ff', color: '#2563eb', fontWeight: 600, cursor: 'pointer' }}
                                    >
                                        Browse Templates
                                    </button>
                                    {formData.data.selected_template_id && (() => {
                                        const t = formData.templates?.find(x => x.id === formData.data.selected_template_id);
                                        return t ? (
                                            <span style={{ fontSize: '14px', color: '#64748b' }}>Selected: <strong>{t.name}</strong></span>
                                        ) : null;
                                    })()}
                                </div>
                                {(formData.templates?.length ?? 0) === 0 ? (
                                    <div className="form-group" style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', color: '#64748b' }}>
                                        No validated templates are configured yet. Add and publish templates in the app Config &gt; Templates section to see them here.
                                    </div>
                                ) : (
                                <div className="templates-grid">
                                    {formData.templates!.map((template) => (
                                        <div
                                            key={template.id}
                                            className={`template-card ${formData.data.selected_template_id === template.id ? 'selected' : ''}`}
                                            onClick={() => selectTemplate(template.id)}
                                        >
                                            <div className="template-preview">
                                                {template.preview_url ? (
                                                    <img
                                                        src={template.preview_url}
                                                        alt={template.name}
                                                        className="template-thumb"
                                                        onError={(e) => {
                                                            e.currentTarget.style.display = 'none';
                                                            const parent = e.currentTarget.parentElement;
                                                            if (parent) {
                                                                const div = document.createElement('div');
                                                                div.className = 'template-thumb-placeholder';
                                                                div.style.background = `linear-gradient(135deg, ${template.colors.primary} 0%, ${template.colors.secondary} 100%)`;
                                                                div.style.width = '100%';
                                                                div.style.height = '100%';
                                                                div.style.borderRadius = '0'; // Inherit from parent
                                                                div.style.display = 'flex';
                                                                div.style.alignItems = 'center';
                                                                div.style.justifyContent = 'center';
                                                                div.style.color = 'white';
                                                                div.style.fontWeight = 'bold';
                                                                div.textContent = template.name.substring(0, 2).toUpperCase();
                                                                parent.appendChild(div);
                                                            }
                                                        }}
                                                    />
                                                ) : (
                                                    <div className="template-thumb-placeholder" style={{
                                                        background: `linear-gradient(135deg, ${template.colors.primary} 0%, ${template.colors.secondary} 100%)`,
                                                        display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold', fontSize: '24px'
                                                    }}>
                                                        {template.name.substring(0, 2).toUpperCase()}
                                                    </div>
                                                )}
                                                {formData.data.selected_template_id === template.id && (
                                                    <div className="selected-overlay">✓</div>
                                                )}
                                            </div>
                                            <div className="template-info">
                                                <h4>{template.name}</h4>
                                                <p>{template.description}</p>
                                                {template.actual_web_url && (
                                                    <div style={{ marginTop: '12px' }}>
                                                        <a
                                                            href={template.actual_web_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            onClick={(e) => e.stopPropagation()}
                                                            style={{
                                                                display: 'inline-block',
                                                                fontSize: '12px',
                                                                color: '#2563eb',
                                                                fontWeight: 600,
                                                                textDecoration: 'none',
                                                                borderBottom: '1px solid transparent'
                                                            }}
                                                            onMouseEnter={(e) => e.currentTarget.style.borderBottom = '1px solid #2563eb'}
                                                            onMouseLeave={(e) => e.currentTarget.style.borderBottom = '1px solid transparent'}
                                                        >
                                                            View Demo ↗
                                                        </a>
                                                        <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                            {template.actual_web_url}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                )
                                }
                                </>
                            ) : (
                                <div className="custom-design-section">
                                    <label>Select Design Package</label>
                                    <div className="pricing-grid" style={{ marginTop: '8px' }}>
                                        {[
                                            { name: 'Essential', price: 500, features: 'Custom Homepage + 5 Inner Pages' },
                                            { name: 'Professional', price: 1000, features: 'Custom Homepage + 10 Inner Pages' },
                                            { name: 'Enterprise', price: 2000, features: 'Fully Custom UI/UX + Branding' }
                                        ].map((tier) => (
                                            <div
                                                key={tier.name}
                                                className={`pricing-card`}
                                                style={{
                                                    border: (formData.data.requirements?.template_references || '').includes(tier.name) ? '2px solid #3b82f6' : '1px solid #cbd5e1',
                                                    padding: '16px',
                                                    borderRadius: '8px',
                                                    cursor: 'pointer',
                                                    background: (formData.data.requirements?.template_references || '').includes(tier.name) ? '#eff6ff' : 'white',
                                                    transition: 'all 0.2s',
                                                    transform: (formData.data.requirements?.template_references || '').includes(tier.name) ? 'scale(1.02)' : 'none',
                                                    boxShadow: (formData.data.requirements?.template_references || '').includes(tier.name) ? '0 4px 6px -1px rgba(59, 130, 246, 0.1)' : 'none'
                                                }}
                                                onClick={() => updateRequirements({ template_references: `Selected Package: ${tier.name} ($${tier.price})\nIncludes: ${tier.features}` })}
                                            >
                                                <div style={{ fontSize: '18px', fontWeight: 700, color: '#1e293b' }}>${tier.price}</div>
                                                <div style={{ fontWeight: 600, color: '#334155', marginBottom: '4px' }}>{tier.name}</div>
                                                <div style={{ fontSize: '12px', color: '#64748b' }}>{tier.features}</div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="form-group" style={{ marginTop: '16px' }}>
                                        <label>Design Parameters & Details</label>
                                        <textarea
                                            value={formData.data.requirements?.template_references || ''}
                                            onChange={(e) => updateRequirementsLocal({ template_references: e.target.value })}
                                            onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                            onFocus={() => handleFieldFocus('template_references', 'Design Parameters & Details')}
                                            rows={4}
                                            placeholder="Describe your vision, target audience, and key design elements..."
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="form-group" style={{ marginTop: '20px' }}>
                                <label>Reference links (optional)</label>
                                <textarea
                                    value={formData.data.requirements?.stock_images_reference || ''}
                                    onChange={(e) => updateRequirementsLocal({ stock_images_reference: e.target.value })}
                                    onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                    onFocus={() => handleFieldFocus('stock_images_reference', 'Reference links')}
                                    rows={3}
                                    placeholder="Add links to websites you like..."
                                />
                            </div>
                        </div>
                    </PhaseSection>

                    {/* Phase 3: Design Preferences */}
                    <PhaseSection
                        id="phase-3"
                        title="Design Preferences"
                        isExpanded={activePhase === 'phase-3'}
                        onToggle={() => togglePhase('phase-3')}
                        completion={(getAllRequirements().filter(r => PHASE_DEFINITIONS[2].fields.includes(r.id) && r.provided).length / PHASE_DEFINITIONS[2].fields.length) * 100}
                    >
                        <div className="form-group">
                            <div className="toggle-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <label style={{ margin: 0 }}>Do you have existing Brand Guidelines?</label>
                                <div className="toggle-switch-wrapper">
                                    <label className="switch">
                                        <input
                                            type="checkbox"
                                            checked={showBrandGuidelines}
                                            onChange={(e) => {
                                                setShowBrandGuidelines(e.target.checked);
                                                updateRequirements({ brand_guidelines_available: e.target.checked });
                                            }}
                                        />
                                        <span className="slider round"></span>
                                    </label>
                                </div>
                            </div>

                            {showBrandGuidelines && (
                                <textarea
                                    className="animate-fadeIn"
                                    value={formData.data.requirements?.brand_guidelines_details || ''}
                                    onChange={(e) => updateRequirementsLocal({ brand_guidelines_details: e.target.value })}
                                    onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                    onFocus={() => handleFieldFocus('brand_guidelines', 'Brand Guidelines')}
                                    rows={3}
                                    placeholder="Paste a link to your brand book or describe your guidelines..."
                                    style={{ marginTop: '8px' }}
                                />
                            )}
                        </div>

                        <div className="select-group">
                            <label>Color Selection</label>
                            <select
                                value={formData.data.requirements?.color_selection || ''}
                                onChange={(e) => updateRequirements({ color_selection: e.target.value })}
                            >
                                <option value="">Select color preference</option>
                                {colorOptions.map(option => (
                                    <option key={option} value={option}>{option}</option>
                                ))}
                            </select>
                        </div>
                        {['Color codes', 'Other'].includes(formData.data.requirements?.color_selection || '') && (
                            <div className="form-group">
                                <label>Color Notes / Codes</label>
                                <input
                                    type="text"
                                    value={formData.data.requirements?.color_notes || ''}
                                    onChange={(e) => updateRequirementsLocal({ color_notes: e.target.value })}
                                    onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                    onFocus={() => handleFieldFocus('color_notes', 'Color Notes')}
                                    placeholder="Hex codes or color notes"
                                />
                            </div>
                        )}

                        <div className="select-group">
                            <label>Font Selection</label>
                            <select
                                value={formData.data.requirements?.font_selection || ''}
                                onChange={(e) => updateRequirements({ font_selection: e.target.value })}
                            >
                                <option value="">Select font preference</option>
                                {fontOptions.map(option => (
                                    <option key={option} value={option}>{option}</option>
                                ))}
                            </select>
                        </div>
                        {formData.data.requirements?.font_selection === 'Other' && (
                            <div className="form-group">
                                <label>Font Notes</label>
                                <input
                                    type="text"
                                    value={formData.data.requirements?.font_notes || ''}
                                    onChange={(e) => updateRequirementsLocal({ font_notes: e.target.value })}
                                    onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                    onFocus={() => handleFieldFocus('font_notes', 'Font Notes')}
                                    placeholder="Font details or links"
                                />
                            </div>
                        )}

                        <div className="form-group">
                            <label>Custom Graphic Notes</label>
                            <div className="radio-group">
                                <label>
                                    <input
                                        type="radio"
                                        name="custom_graphics"
                                        checked={formData.data.requirements?.custom_graphic_notes_enabled === true}
                                        onChange={() => updateRequirements({ custom_graphic_notes_enabled: true })}
                                    />
                                    Yes
                                </label>
                                <label>
                                    <input
                                        type="radio"
                                        name="custom_graphics"
                                        checked={formData.data.requirements?.custom_graphic_notes_enabled === false}
                                        onChange={() => updateRequirements({ custom_graphic_notes_enabled: false })}
                                    />
                                    No
                                </label>
                            </div>
                            {formData.data.requirements?.custom_graphic_notes_enabled && (
                                <textarea
                                    value={formData.data.requirements?.custom_graphic_notes || ''}
                                    onChange={(e) => updateRequirementsLocal({ custom_graphic_notes: e.target.value })}
                                    onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                    onFocus={() => handleFieldFocus('custom_graphic_notes', 'Custom Graphic Notes')}
                                    rows={3}
                                    placeholder="Describe custom graphic needs..."
                                />
                            )}
                        </div>

                        <div className="select-group">
                            <label>Navigation</label>
                            <select
                                value={formData.data.requirements?.navigation_notes_option || ''}
                                onChange={(e) => updateRequirements({ navigation_notes_option: e.target.value })}
                            >
                                <option value="">Select navigation preference</option>
                                {navigationOptions.map(option => (
                                    <option key={option} value={option}>{option}</option>
                                ))}
                            </select>
                        </div>
                        {formData.data.requirements?.navigation_notes_option === 'Custom' && (
                            <div className="form-group">
                                <label>Navigation names</label>
                                <div className="mb-2" style={{ marginBottom: '8px' }}>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>Quick Presets:</span>
                                    <div className="chip-group" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '4px' }}>
                                        {['Home', 'Apartments', 'Amenities', 'Neighborhood', 'Gallery', 'Contact Us', 'Apply Now', 'Residents'].map(preset => (
                                            <button
                                                key={preset}
                                                className="chip-btn"
                                                onClick={() => handleSitemapPreset(preset)}
                                                style={{
                                                    padding: '4px 12px',
                                                    borderRadius: '16px',
                                                    border: '1px solid #cbd5e1',
                                                    background: 'white',
                                                    fontSize: '12px',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                + {preset}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <textarea
                                    value={formData.data.requirements?.navigation_notes || ''}
                                    onChange={(e) => updateRequirementsLocal({ navigation_notes: e.target.value })}
                                    onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                    rows={4}
                                    placeholder="List the pages you want on your menu..."
                                />
                            </div>
                        )}

                    </PhaseSection>

                    {/* Phase 4: Property Content */}
                    <PhaseSection
                        id="phase-4"
                        title="Property Content"
                        isExpanded={activePhase === 'phase-4'}
                        onToggle={() => togglePhase('phase-4')}
                        completion={(getAllRequirements().filter(r => PHASE_DEFINITIONS[3].fields.includes(r.id) && r.provided).length / PHASE_DEFINITIONS[3].fields.length) * 100}
                    >
                        <div className="form-group">
                            <label>Stock Images Reference</label>
                            <textarea
                                value={formData.data.requirements?.stock_images_reference || ''}
                                onChange={(e) => updateRequirementsLocal({ stock_images_reference: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                rows={2}
                                placeholder="Links or notes for stock images..."
                            />
                        </div>
                        <div className="form-group">
                            <label>Floor Plan Images</label>
                            <textarea
                                value={formData.data.requirements?.floor_plan_images || ''}
                                onChange={(e) => updateRequirementsLocal({ floor_plan_images: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                onFocus={() => handleFieldFocus('floor_plan_images', 'Floor Plan Images')}
                                rows={2}
                                placeholder="Links or notes for floor plan images..."
                            />
                        </div>
                        <div className="form-group">
                            <label>Sitemap</label>
                            <textarea
                                value={formData.data.requirements?.sitemap || ''}
                                onChange={(e) => updateRequirementsLocal({ sitemap: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                onFocus={() => handleFieldFocus('sitemap', 'Sitemap')}
                                rows={2}
                                placeholder="Sitemap links or details..."
                            />
                        </div>
                        <div className="form-group">
                            <label>Virtual Tours</label>
                            <textarea
                                value={formData.data.requirements?.virtual_tours || ''}
                                onChange={(e) => updateRequirementsLocal({ virtual_tours: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                onFocus={() => handleFieldFocus('virtual_tours', 'Virtual Tours')}
                                rows={2}
                                placeholder="Virtual tour links..."
                            />
                        </div>
                        <div className="form-group">
                            <label>Point of Interest Categories & Details</label>
                            <textarea
                                value={formData.data.requirements?.poi_categories || ''}
                                onChange={(e) => updateRequirementsLocal({ poi_categories: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                onFocus={() => handleFieldFocus('poi_categories', 'POI Categories')}
                                rows={3}
                                placeholder="POI categories and details..."
                            />
                        </div>

                        <div className="form-group">
                            <label>Specials</label>
                            <div className="radio-group">
                                <label>
                                    <input
                                        type="radio"
                                        name="specials"
                                        checked={formData.data.requirements?.specials_enabled === true}
                                        onChange={() => updateRequirements({ specials_enabled: true })}
                                    />
                                    Yes
                                </label>
                                <label>
                                    <input
                                        type="radio"
                                        name="specials"
                                        checked={formData.data.requirements?.specials_enabled === false}
                                        onChange={() => updateRequirements({ specials_enabled: false })}
                                    />
                                    No
                                </label>
                            </div>
                            {formData.data.requirements?.specials_enabled && (
                                <textarea
                                    value={formData.data.requirements?.specials_details || ''}
                                    onChange={(e) => updateRequirementsLocal({ specials_details: e.target.value })}
                                    onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                    onFocus={() => handleFieldFocus('specials_details', 'Specials Details')}
                                    rows={2}
                                    placeholder="Describe specials to add..."
                                />
                            )}
                        </div>
                    </PhaseSection>

                    {/* Phase 5: Compliance & Legal */}
                    <PhaseSection
                        id="phase-5"
                        title="Compliance & Legal"
                        isExpanded={activePhase === 'phase-5'}
                        onToggle={() => togglePhase('phase-5')}
                        completion={(getAllRequirements().filter(r => PHASE_DEFINITIONS[4].fields.includes(r.id) && r.provided).length / PHASE_DEFINITIONS[4].fields.length) * 100}
                    >
                        <div className="form-group">
                            <label>WCAG Compliance <span className="required">*</span></label>
                            <div className="radio-group">
                                <label>
                                    <input
                                        type="radio"
                                        name="wcag_compliance_required"
                                        checked={formData.data.wcag_compliance_required === true}
                                        onChange={() => saveFormData({
                                            wcag_compliance_required: true,
                                            wcag_confirmed: true
                                        })}
                                    />
                                    Yes
                                </label>
                                <label>
                                    <input
                                        type="radio"
                                        name="wcag_compliance_required"
                                        checked={formData.data.wcag_compliance_required === false}
                                        onChange={() => saveFormData({
                                            wcag_compliance_required: false,
                                            wcag_confirmed: true
                                        })}
                                    />
                                    No
                                </label>
                            </div>
                        </div>
                        {formData.data.wcag_compliance_required && (
                            <div className="select-group">
                                <label>Compliance Level</label>
                                <select
                                    value={formData.data.wcag_level}
                                    onChange={(e) => saveFormData({
                                        wcag_level: e.target.value,
                                        wcag_confirmed: true
                                    })}
                                >
                                    <option value="A">Level A (Minimum)</option>
                                    <option value="AA">Level AA (Standard)</option>
                                    <option value="AAA">Level AAA (Enhanced)</option>
                                </select>
                            </div>
                        )}

                        <div style={{ marginTop: '24px' }}>
                            <label style={{ display: 'block', fontWeight: 500, marginBottom: '8px', color: '#475569' }}>Privacy Policy</label>
                            <div className="url-input">
                                <input
                                    type="url"
                                    value={formData.data.privacy_policy_url || ''}
                                    onChange={(e) => updateLocalData({ privacy_policy_url: e.target.value })}
                                    onBlur={() => saveFormData({ privacy_policy_url: formData.data.privacy_policy_url })}
                                    placeholder="Enter Privacy Policy URL..."
                                />
                            </div>
                            <div className="or-divider"><span>or</span></div>
                            <div className="copy-input">
                                <textarea
                                    value={formData.data.privacy_policy_text || ''}
                                    onChange={(e) => updateLocalData({ privacy_policy_text: e.target.value })}
                                    onBlur={() => saveFormData({ privacy_policy_text: formData.data.privacy_policy_text })}
                                    placeholder="Paste privacy policy text here..."
                                    rows={4}
                                />
                            </div>
                        </div>
                    </PhaseSection>

                    {/* Phase 6: Technical & Launch Setup */}
                    <PhaseSection
                        id="phase-6"
                        title="Website Fundamentals"
                        isExpanded={activePhase === 'phase-6'}
                        onToggle={() => togglePhase('phase-6')}
                        completion={(getAllRequirements().filter(r => PHASE_DEFINITIONS[5].fields.includes(r.id) && r.provided).length / PHASE_DEFINITIONS[5].fields.length) * 100}
                    >
                        <div className="form-group">
                            <label>Pages for the Website</label>
                            <textarea
                                value={formData.data.requirements?.pages || ''}
                                onChange={(e) => updateRequirementsLocal({ pages: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                onFocus={() => handleFieldFocus('pages', 'Pages')}
                                rows={2}
                                placeholder="List pages (comma-separated)..."
                            />
                        </div>

                        <div className="select-group">
                            <label>Domain Type</label>
                            <select
                                value={formData.data.requirements?.domain_type || ''}
                                onChange={(e) => updateRequirements({ domain_type: e.target.value })}
                            >
                                <option value="">Select domain type</option>
                                {domainTypeOptions.map(option => (
                                    <option key={option} value={option}>{option}</option>
                                ))}
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Vanity Domains / Redirects</label>
                            <textarea
                                value={formData.data.requirements?.vanity_domains || ''}
                                onChange={(e) => updateRequirements({ vanity_domains: e.target.value })}
                                rows={2}
                                placeholder="Add vanity domains or redirect details..."
                            />
                        </div>

                        <div className="select-group">
                            <label>Call Tracking Plan</label>
                            <select
                                value={formData.data.requirements?.call_tracking_plan || ''}
                                onChange={(e) => updateRequirements({ call_tracking_plan: e.target.value })}
                            >
                                <option value="">Select call tracking plan</option>
                                {callTrackingOptions.map(option => (
                                    <option key={option} value={option}>{option}</option>
                                ))}
                            </select>
                        </div>
                    </PhaseSection>

                    {/* Spacer for fixed bottom bar */}

                </main >

                <aside className="sidebar">
                    <ChecklistPanel
                        requirements={getAllRequirements()}
                        onScrollTo={scrollToPhase}
                    />
                </aside>
            </div >

            {/* Fixed Bottom Action Bar */}
            < div className="bottom-action-bar" >
                <div style={{ color: '#64748b', fontSize: '14px' }}>
                    {saving ? 'Saving changes...' : 'Changes saved automatically'}
                </div>
                <button className="btn-submit-form" onClick={handleInitialSubmit}>
                    Review & Submit
                </button>
            </div >

            {
                showReviewModal && (
                    <ReviewModal
                        onClose={() => setShowReviewModal(false)}
                        onConfirm={confirmSubmit}
                        phases={PHASE_DEFINITIONS}
                        requirements={getAllRequirements()}
                    />
                )
            }

            {browseTemplatesOpen && formData?.templates && (
                <div className="modal-overlay" onClick={() => { setBrowseTemplatesOpen(false); setTemplateDetailDrawer(null); }} style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
                    <div onClick={e => e.stopPropagation()} style={{ background: 'white', borderRadius: '16px', maxWidth: '900px', width: '100%', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
                        <div style={{ padding: '20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h2 style={{ margin: 0, fontSize: '20px' }}>Browse Templates</h2>
                            <button type="button" onClick={() => { setBrowseTemplatesOpen(false); setTemplateDetailDrawer(null); }} style={{ padding: '8px 16px', border: '1px solid #e2e8f0', borderRadius: '8px', background: 'white', cursor: 'pointer' }}>Close</button>
                        </div>
                        <div style={{ display: 'flex', gap: '12px', padding: '12px 20px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                            <input type="text" placeholder="Category" value={templateGalleryFilters.category || ''} onChange={e => setTemplateGalleryFilters(f => ({ ...f, category: e.target.value || undefined }))} style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '13px' }} />
                            <input type="text" placeholder="Style" value={templateGalleryFilters.style || ''} onChange={e => setTemplateGalleryFilters(f => ({ ...f, style: e.target.value || undefined }))} style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '13px' }} />
                            <input type="text" placeholder="Tag" value={templateGalleryFilters.tag || ''} onChange={e => setTemplateGalleryFilters(f => ({ ...f, tag: e.target.value || undefined }))} style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '13px' }} />
                        </div>
                        {(() => {
                            const templates = formData.templates;
                            const filtered = templates.filter(t => {
                                if (templateGalleryFilters.category && (t.category || '') !== templateGalleryFilters.category) return false;
                                if (templateGalleryFilters.style && (t.style || '') !== templateGalleryFilters.style) return false;
                                if (templateGalleryFilters.tag && !(t.features || []).some((f: string) => (f || '').toLowerCase().includes((templateGalleryFilters.tag || '').toLowerCase()))) return false;
                                return true;
                            });
                            const domainType = formData.data.requirements?.domain_type || '';
                            const wcag = formData.data.wcag_compliance_required;
                            const customCopy = formData.data.use_custom_copy;
                            const recommended = [...filtered].sort((a, b) => {
                                let scoreA = 0, scoreB = 0;
                                if (domainType === 'Multi' && (a.features || []).some((f: string) => /multi|location/i.test(f))) scoreA += 2;
                                if (domainType === 'Multi' && (b.features || []).some((f: string) => /multi|location/i.test(f))) scoreB += 2;
                                if (wcag && (a.features || []).some((f: string) => /accessibility/i.test(f))) scoreA += 2;
                                if (wcag && (b.features || []).some((f: string) => /accessibility/i.test(f))) scoreB += 2;
                                if (customCopy && (a.style || '').match(/corporate|editorial/i)) scoreA += 1;
                                if (customCopy && (b.style || '').match(/corporate|editorial/i)) scoreB += 1;
                                return scoreB - scoreA;
                            }).slice(0, 3);
                            return (
                                <div style={{ flex: 1, overflow: 'auto', display: 'flex' }}>
                                    <div style={{ flex: 1, padding: '20px' }}>
                                        {recommended.length > 0 && (
                                            <div style={{ marginBottom: '20px' }}>
                                                <h4 style={{ margin: '0 0 12px', fontSize: '14px', color: '#64748b' }}>Recommended for you</h4>
                                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                                                    {recommended.map(t => (
                                                        <div key={t.id} onClick={() => setTemplateDetailDrawer(t)} style={{ border: '2px solid #2563eb', borderRadius: '12px', overflow: 'hidden', cursor: 'pointer', background: '#eff6ff' }}>
                                                            {(t.preview_thumbnail_url || t.preview_url) ? <img src={t.preview_thumbnail_url || t.preview_url} alt="" style={{ width: '100%', height: '100px', objectFit: 'cover' }} /> : <div style={{ width: '100%', height: '100px', background: `linear-gradient(135deg, ${t.colors?.primary || '#2563eb'}, ${t.colors?.secondary || '#1e40af'})`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>{t.name?.slice(0, 2).toUpperCase()}</div>}
                                                            <div style={{ padding: '10px' }}><strong>{t.name}</strong></div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                        <h4 style={{ margin: '0 0 12px', fontSize: '14px', color: '#64748b' }}>All templates</h4>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '16px' }}>
                                            {filtered.map(t => (
                                                <div key={t.id} onClick={() => setTemplateDetailDrawer(t)} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', overflow: 'hidden', cursor: 'pointer' }}>
                                                    {(t.preview_thumbnail_url || t.preview_url) ? <img src={t.preview_thumbnail_url || t.preview_url} alt="" style={{ width: '100%', height: '100px', objectFit: 'cover' }} onError={e => { e.currentTarget.style.display = 'none'; }} /> : <div style={{ width: '100%', height: '100px', background: `linear-gradient(135deg, ${t.colors?.primary || '#2563eb'}, ${t.colors?.secondary || '#1e40af'})`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>{t.name?.slice(0, 2).toUpperCase()}</div>}
                                                    <div style={{ padding: '10px' }}><strong>{t.name}</strong><div style={{ fontSize: '12px', color: '#64748b' }}>{t.category || t.style || '—'}</div></div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    {templateDetailDrawer && (
                                        <div style={{ width: '320px', borderLeft: '1px solid #e2e8f0', padding: '20px', overflow: 'auto', background: '#f8fafc' }}>
                                            <h4 style={{ margin: '0 0 12px' }}>{templateDetailDrawer.name}</h4>
                                            <p style={{ margin: '0 0 12px', fontSize: '13px', color: '#64748b' }}>{templateDetailDrawer.description || '—'}</p>
                                            <div style={{ marginBottom: '12px' }}>
                                                <strong style={{ fontSize: '12px' }}>Pages included</strong>
                                                <ul style={{ margin: '4px 0 0', paddingLeft: '18px', fontSize: '13px' }}>{(templateDetailDrawer.pages_json || []).map((p: any, i: number) => <li key={i}>{p.title || p.slug || 'Page'}</li>)}</ul>
                                                {((templateDetailDrawer.pages_json || []).length === 0) && <span style={{ fontSize: '12px', color: '#94a3b8' }}>—</span>}
                                            </div>
                                            <div style={{ marginBottom: '12px' }}>
                                                <strong style={{ fontSize: '12px' }}>Required inputs</strong>
                                                <ul style={{ margin: '4px 0 0', paddingLeft: '18px', fontSize: '13px' }}>{(templateDetailDrawer.required_inputs_json || templateDetailDrawer.features || []).map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>
                                            </div>
                                            {templateDetailDrawer.preview_url && (
                                                <a href={templateDetailDrawer.preview_url} target="_blank" rel="noreferrer" style={{ display: 'inline-block', marginBottom: '12px', fontSize: '13px', color: '#2563eb' }}>Open preview ↗</a>
                                            )}
                                            <button type="button" onClick={() => { selectTemplate(templateDetailDrawer.id); setBrowseTemplatesOpen(false); setTemplateDetailDrawer(null); }} style={{ width: '100%', padding: '10px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}>Select Template</button>
                                        </div>
                                    )}
                                </div>
                            );
                        })()}
                    </div>
                </div>
            )}

            {/* Chatbot Container Removed - Moved to End */}

            <footer className="page-footer">
                <p>Questions? Contact your project manager for assistance.</p>
            </footer>

            <style jsx global>{`
                /* Global Fixed Elements */
                .modal-overlay {
                    position: fixed;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 2000;
                    backdrop-filter: blur(4px);
                }

                .chatbot-container {
                    position: fixed;
                    bottom: 24px;
                    right: 24px;
                    z-index: 1500;
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                }
                
                .chat-tooltip {
                    background: white;
                    padding: 8px 12px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    font-size: 13px;
                    font-weight: 600;
                    color: #1e293b;
                    margin-bottom: 8px;
                    position: relative;
                    animation: bounceSlow 2s infinite;
                }

                .chat-tooltip:after {
                    content: '';
                    position: absolute;
                    bottom: -6px;
                    right: 24px;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 6px solid white;
                }

                @keyframes bounceSlow {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                }
            `}</style>
            <style jsx>{`
                .client-page {
                    min-height: 100vh;
                    background: #e2e8f0;
                    padding-bottom: 60px; /* Reduced space */
                }

                .page-header {
                    background: white;
                    padding: 24px 32px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                }

                .header-content h1 {
                    font-size: 24px;
                    margin: 0;
                    color: #1e293b;
                }

                .project-name {
                    margin: 4px 0 0 0;
                    color: #64748b;
                }

                .completion-badge {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }

                .completion-ring {
                    position: relative;
                    width: 60px;
                    height: 60px;
                }

                .completion-ring svg {
                    transform: rotate(-90deg);
                }

                .ring-bg {
                    fill: none;
                    stroke: #e2e8f0;
                    stroke-width: 3;
                }

                .ring-fill {
                    fill: none;
                    stroke: #10b981;
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
                }

                .completion-label {
                    font-size: 12px;
                    color: #64748b;
                    margin-top: 4px;
                }

                .alert {
                    max-width: 800px;
                    margin: 16px auto;
                    padding: 12px 20px;
                    border-radius: 8px;
                }

                .alert-error {
                    background: #fef2f2;
                    color: #dc2626;
                    border: 1px solid #fecaca;
                }

                .alert-success {
                    background: #f0fdf4;
                    color: #16a34a;
                    border: 1px solid #bbf7d0;
                }

                .missing-alert {
                    max-width: 800px;
                    margin: 16px auto;
                    padding: 20px;
                    background: #fffbeb;
                    border: 1px solid #fde68a;
                    border-radius: 12px;
                }

                .missing-alert h3 {
                    margin: 0 0 8px 0;
                    color: #d97706;
                }

                .missing-alert p {
                    margin: 0 0 12px 0;
                    color: #92400e;
                }

                .missing-alert ul {
                    margin: 0;
                    padding-left: 20px;
                    color: #78350f;
                }
                .missing-fields-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 10px;
                    margin: 12px 0 16px;
                }
                .missing-field-row {
                    display: flex;
                    flex-wrap: wrap;
                    align-items: center;
                    justify-content: space-between;
                    gap: 8px;
                    padding: 8px 12px;
                    background: #fff7ed;
                    border: 1px solid #fed7aa;
                    border-radius: 8px;
                }
                .missing-field-name {
                    font-weight: 600;
                    color: #7c2d12;
                    font-size: 14px;
                }
                .missing-field-actions {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 6px;
                    align-items: center;
                }
                .eta-btn {
                    padding: 4px 8px;
                    font-size: 11px;
                    border-radius: 4px;
                    border: 1px solid #fdba74;
                    background: white;
                    color: #9a3412;
                    cursor: pointer;
                }
                .eta-btn:hover {
                    background: #ffedd5;
                }
                .eta-input {
                    padding: 4px 8px;
                    border: 1px solid #fdba74;
                    border-radius: 4px;
                    font-size: 11px;
                    color: #9a3412;
                    background: white;
                    width: auto;
                }
                .btn-remove-logo-x {
                    position: absolute;
                    top: -10px;
                    right: -10px;
                    width: 28px;
                    height: 28px;
                    background: rgba(220, 38, 38, 0.9);
                    color: white;
                    border: none;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    font-size: 16px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    transition: all 0.2s;
                    z-index: 10;
                }
                .btn-remove-logo-x:hover {
                    background: #ef4444;
                    transform: scale(1.1);
                }
                .btn-submit-form {
                    padding: 10px 16px;
                    border-radius: 8px;
                    border: none;
                    background: #2563eb;
                    color: white;
                    font-weight: 600;
                    cursor: pointer;
                }
                .btn-submit-form:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }
                .submit-section {
                    display: flex;
                    justify-content: flex-end;
                    padding: 0 0 20px;
                }

                .form-container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 24px;
                }

                .form-section {
                    background: white;
                    padding: 24px;
                    border-radius: 12px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                }

                .form-section h2 {
                    margin: 0 0 8px 0;
                    font-size: 18px;
                    color: #1e293b;
                }

                .section-desc {
                    margin: 0 0 20px 0;
                    color: #64748b;
                    font-size: 14px;
                }

                .upload-area {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                }

                .upload-placeholder {
                    width: 100%;
                    padding: 40px;
                    border: 2px dashed #cbd5e1;
                    border-radius: 12px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .upload-placeholder:hover {
                    border-color: #2563eb;
                    background: #f8fafc;
                }

                .upload-placeholder.small {
                    padding: 20px;
                    min-width: 120px;
                }

                .upload-icon {
                    font-size: 32px;
                }

                .uploaded-preview {
                    padding: 16px;
                    background: #f0fdf4;
                    border-radius: 8px;
                    text-align: center;
                    width: 100%;
                }

                .preview-badge {
                    color: #16a34a;
                    font-weight: 600;
                }

                .btn-upload {
                    padding: 10px 24px;
                    background: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 500;
                }

                .btn-upload:hover {
                    background: #1d4ed8;
                }

                .or-divider {
                    display: flex;
                    align-items: center;
                    margin: 20px 0;
                }

                .or-divider::before,
                .or-divider::after {
                    content: '';
                    flex: 1;
                    height: 1px;
                    background: #e2e8f0;
                }

                .or-divider span {
                    padding: 0 16px;
                    color: #94a3b8;
                    font-size: 14px;
                }

                .url-input, .copy-input, .select-group {
                    margin-bottom: 16px;
                }
                .form-group {
                    margin-bottom: 16px;
                }
                .form-group label {
                    display: block;
                    font-size: 14px;
                    font-weight: 500;
                    color: #475569;
                    margin-bottom: 6px;
                }
                .form-group input,
                .form-group textarea {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    font-size: 14px;
                }
                .form-group input:focus,
                .form-group textarea:focus {
                    outline: none;
                    border-color: #2563eb;
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
                }
                .radio-group {
                    display: flex;
                    gap: 16px;
                    flex-wrap: wrap;
                    margin-bottom: 8px;
                }
                .radio-group label {
                    display: flex;
                    gap: 8px;
                    align-items: center;
                    font-size: 14px;
                    color: #475569;
                }

                .url-input label, .copy-input label, .select-group label {
                    display: block;
                    font-size: 14px;
                    font-weight: 500;
                    color: #475569;
                    margin-bottom: 6px;
                }

                .url-input input, .copy-input textarea, .select-group select {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    font-size: 14px;
                }

                .url-input input:focus, .copy-input textarea:focus, .select-group select:focus {
                    outline: none;
                    border-color: #2563eb;
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
                }

                .images-grid {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                }

                .image-item {
                    padding: 12px 16px;
                    background: #f0fdf4;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .image-badge {
                    color: #16a34a;
                }

                .copy-options {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 16px;
                    margin-bottom: 20px;
                }

                .option-card {
                    padding: 16px;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .option-card:has(input:checked) {
                    border-color: #2563eb;
                    background: #f8fafc;
                }

                .option-card input {
                    margin-right: 12px;
                }

                .option-content h4 {
                    margin: 0 0 4px 0;
                    font-size: 14px;
                }

                .option-content p {
                    margin: 0;
                    font-size: 12px;
                    color: #64748b;
                }

                .pricing-section h4 {
                    margin: 0 0 16px 0;
                }

                .pricing-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 12px;
                }

                .pricing-card {
                    padding: 20px;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    cursor: pointer;
                    text-align: center;
                    transition: all 0.2s;
                }

                .pricing-card:hover {
                    border-color: #2563eb;
                }

                .pricing-card.selected {
                    border-color: #10b981;
                    background: #f0fdf4;
                }

                .pricing-card .price {
                    font-size: 28px;
                    font-weight: 700;
                    color: #1e293b;
                }

                .pricing-card .tier-name {
                    font-size: 13px;
                    color: #64748b;
                    margin-top: 4px;
                }

                .pricing-card .selected-badge {
                    margin-top: 8px;
                    color: #10b981;
                    font-weight: 600;
                }

                .final-price {
                    margin-top: 16px;
                    padding: 16px;
                    background: #f0fdf4;
                    border-radius: 8px;
                    text-align: center;
                }

                .final-price p {
                    margin: 4px 0 0 0;
                    color: #64748b;
                    font-size: 14px;
                }

                .templates-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 16px;
                }

                .template-card {
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    overflow: hidden;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .template-card:hover {
                    border-color: #2563eb;
                    transform: translateY(-2px);
                }

                .template-card.selected {
                    border-color: #10b981;
                }

                .template-preview {
                    height: 120px;
                    position: relative;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .selected-overlay {
                    position: absolute;
                    inset: 0;
                    background: rgba(16, 185, 129, 0.9);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 32px;
                    color: white;
                }

                .template-info {
                    padding: 16px;
                }

                .template-info h4 {
                    margin: 0 0 4px 0;
                    font-size: 14px;
                }

                .template-info p {
                    margin: 0 0 8px 0;
                    font-size: 12px;
                    color: #64748b;
                }

                .template-features {
                    display: flex;
                    gap: 6px;
                    flex-wrap: wrap;
                }

                .feature-tag {
                    padding: 2px 8px;
                    background: #f1f5f9;
                    border-radius: 4px;
                    font-size: 11px;
                    color: #64748b;
                }

                .checkbox-group {
                    margin-bottom: 16px;
                }

                .checkbox-group label {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    cursor: pointer;
                }

                .page-footer {
                    text-align: center;
                    padding: 24px;
                    color: #64748b;
                    font-size: 14px;
                }

                @media (max-width: 768px) {
                    .copy-options, .pricing-grid, .templates-grid {
                        grid-template-columns: 1fr;
                    }
                }

                .logo-preview-container {
                    width: 100%;
                    display: flex;
                    justify-content: center;
                    margin-bottom: 20px;
                }

                .logo-preview-card {
                    background: white;
                    padding: 24px;
                    border: 1px solid #e2e8f0;
                    border-radius: 16px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 20px;
                    max-width: 400px;
                    width: 100%;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.05);
                }

                .logo-thumbnail {
                    max-width: 200px;
                    max-height: 200px;
                    object-fit: contain;
                }

                .logo-actions {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                    width: 100%;
                }

                .btn-replace {
                    padding: 8px 16px;
                    background: white;
                    color: #2563eb;
                    border: 1px solid #2563eb;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 500;
                    font-size: 14px;
                    transition: all 0.2s;
                }

                .btn-replace:hover {
                    background: #eff6ff;
                }

                .image-card {
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                    transition: all 0.2s;
                    position: relative;
                }

                .image-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 8px 24px rgba(0,0,0,0.1);
                }

                .image-preview {
                    position: relative;
                    aspect-ratio: 1;
                    background: #f8fafc;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-bottom: 1px solid #f1f5f9;
                }

                .image-preview img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }

                .btn-delete {
                    position: absolute;
                    top: 8px;
                    right: 8px;
                    width: 24px;
                    height: 24px;
                    background: rgba(220, 38, 38, 0.9);
                    color: white;
                    border: none;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    font-size: 16px;
                    opacity: 0;
                    transition: opacity 0.2s;
                    z-index: 5;
                }

                .image-card:hover .btn-delete {
                    opacity: 1;
                }

                .image-info {
                    padding: 8px 12px;
                }

                .image-name {
                    font-size: 12px;
                    color: #475569;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    display: block;
                }

                .upload-placeholder-card {
                    aspect-ratio: 1;
                    border: 2px dashed #cbd5e1;
                    border-radius: 12px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                    background: #f8fafc;
                }

                .upload-placeholder-card:hover {
                    border-color: #2563eb;
                    background: #eff6ff;
                    color: #2563eb;
                }

                .logo-preview-card {
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    background: white;
                    padding: 24px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                    width: 100%;
                    max-width: 400px;
                }
                .logo-thumbnail {
                    height: 200px;
                    width: auto;
                    object-fit: contain;
                    margin-bottom: 16px;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                .logo-thumbnail:hover {
                    transform: scale(1.02);
                }
                .logo-actions {
                    width: 100%;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                }
                .logo-btn-group {
                    display: flex;
                    gap: 12px;
                }
                .btn-replace {
                    padding: 8px 16px;
                    background: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background 0.2s;
                }
                .btn-replace:hover {
                    background: #1d4ed8;
                }
                .btn-remove-logo {
                    padding: 8px 16px;
                    background: #fee2e2;
                    color: #dc2626;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background 0.2s;
                }
                .btn-remove-logo:hover {
                    background: #fecaca;
                }
                /* Images Grid */
                .images-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                    gap: 16px;
                }
                .image-card {
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                    transition: transform 0.2s;
                    border: 1px solid #e2e8f0;
                }
                .image-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
                }
                .image-preview {
                    position: relative;
                    aspect-ratio: 16 / 9;
                    background: #f1f5f9;
                    overflow: hidden;
                }
                .image-preview img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    transition: transform 0.3s;
                }
                .image-preview:hover img {
                    transform: scale(1.05);
                }
                .btn-delete {
                    position: absolute;
                    top: 8px;
                    right: 8px;
                    width: 28px;
                    height: 28px;
                    border-radius: 50%;
                    background: rgba(0, 0, 0, 0.6);
                    color: white;
                    border: none;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    opacity: 0;
                    transition: all 0.2s;
                    font-size: 18px;
                    line-height: 1;
                }
                .image-card:hover .btn-delete {
                    opacity: 1;
                }
                .btn-delete:hover {
                    background: #ef4444;
                    transform: scale(1.1);
                }
                
                /* Lightbox */
                .lightbox-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.9);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                    padding: 24px;
                    animation: fadeIn 0.2s ease-out;
                }
                .lightbox-content {
                    position: relative;
                    max-width: 90vw;
                    max-height: 90vh;
                }
                .lightbox-content img {
                    max-width: 100%;
                    max-height: 90vh;
                    object-fit: contain;
                    border-radius: 4px;
                    border: 10px solid white; /* Requested 10px white border */
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
                }
                .section-header-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                .section-header-row h2 {
                    margin: 0;
                }
                .btn-add-header {
                    padding: 8px 16px;
                    background: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    transition: background 0.2s;
                }
                .btn-add-header:hover {
                    background: #1d4ed8;
                }
                .lightbox-close {
                    position: absolute;
                    top: -40px;
                    right: -10px;
                    background: none;
                    border: none;
                    color: white;
                    font-size: 32px;
                    cursor: pointer;
                    padding: 8px;
                    line-height: 1;
                    opacity: 0.8;
                    transition: opacity 0.2s;
                }
                .lightbox-close:hover {
                    opacity: 1;
                }
                /* Template Section Updates */
                .box-radio-group {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 16px;
                }
                .radio-card {
                    display: flex;
                    align-items: flex-start;
                    padding: 16px;
                    border: 2px solid #e2e8f0;
                    border-radius: 10px;
                    cursor: pointer;
                    transition: all 0.2s;
                    background: white;
                }
                .radio-card:hover {
                    border-color: #94a3b8;
                    background: #f8fafc;
                }
                .radio-card.selected {
                    border-color: #2563eb;
                    background: #eff6ff;
                }
                .radio-card input {
                    margin-top: 4px;
                    margin-right: 12px;
                }
                .radio-content {
                    display: flex;
                    flex-direction: column;
                }
                .radio-title {
                    font-weight: 600;
                    color: #1e293b;
                    font-size: 14px;
                }
                .radio-desc {
                    font-size: 12px;
                    color: #64748b;
                }
                .template-thumb {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
                .template-thumb-placeholder {
                    width: 100%;
                    height: 100%;
                }
                .info-card {
                    display: flex;
                    gap: 16px;
                    padding: 20px;
                    border-radius: 12px;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                }
                .info-card.highlight {
                    background: #fdf2f8; /* Pinkish tint for premium feel */
                    border-color: #fbcfe8;
                }
                .info-icon {
                    font-size: 24px;
                }
                .benefits-list {
                    margin: 8px 0 0 0;
                    padding-left: 20px;
                    font-size: 13px;
                    color: #475569;
                }
                .price-tag {
                    margin-left: auto;
                    text-align: right;
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                }
                .price-tag .label {
                    font-size: 11px;
                    text-transform: uppercase;
                    color: #64748b;
                    font-weight: 600;
                }
                .price-tag .amount {
                    font-size: 20px;
                    font-weight: 700;
                    color: #be185d;
                }
                @media (max-width: 640px) {
                    .box-radio-group { grid-template-columns: 1fr; }
                    .info-card { flex-direction: column; }
                    .price-tag { margin-left: 0; align-items: flex-start; margin-top: 12px; }
                }

                /* Layout Overhaul */
                .layout-container {
                    display: grid;
                    grid-template-columns: 1fr 300px;
                    gap: 24px;
                    max-width: 1100px; /* Reduced from 1200px for tighter feel */
                    margin: 24px auto;
                    padding: 0 20px;
                    align-items: start;
                }
                
                .main-content {
                    min-width: 0; /* Prevent overflow */
                }

                .sidebar {
                    position: sticky;
                    top: 24px;
                    height: calc(100vh - 48px);
                    overflow-y: auto;
                    padding-right: 4px; /* Scrollbar space */
                }
                
                .contact-list {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                .contact-row {
                    display: grid;
                    grid-template-columns: 1.2fr 1.5fr 1fr auto;
                    gap: 8px;
                    align-items: center;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 10px;
                }
                
                .contact-row input[type="text"],
                .contact-row input[type="email"] {
                    background: white;
                }
                
                .contact-primary {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 12px;
                    color: #475569;
                }
                
                .btn-add-contact {
                    align-self: flex-start;
                    padding: 8px 12px;
                    border-radius: 8px;
                    border: 1px solid #cbd5e1;
                    background: #ffffff;
                    color: #334155;
                    font-size: 12px;
                    font-weight: 600;
                    cursor: pointer;
                }
                
                .btn-add-contact:hover {
                    background: #f1f5f9;
                }
                
                .missing-fields-card {
                    background: #fff7ed;
                    border: 1px solid #fed7aa;
                    border-radius: 10px;
                    padding: 12px 14px;
                    margin-bottom: 12px;
                    color: #7c2d12;
                    font-size: 12px;
                }
                
                .missing-fields-title {
                    font-weight: 600;
                    margin-bottom: 6px;
                }
                
                .missing-fields-card ul {
                    margin: 0 0 6px 16px;
                    padding: 0;
                }
                
                .missing-fields-card li {
                    margin-bottom: 2px;
                }
                
                .missing-fields-note {
                    color: #9a3412;
                }

                @media (max-width: 1024px) {
                    .layout-container {
                        grid-template-columns: 1fr;
                    }
                    .sidebar {
                        display: none; /* Hide on mobile/tablet for now or move to bottom */
                    }
                }

                /* Phase Sections */
                .phase-section {
                    background: white;
                    border: 1px solid #cbd5e1;
                    border-radius: 12px;
                    margin-bottom: 16px;
                    overflow: hidden;
                    transition: all 0.2s;
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
                }

                .phase-section.active {
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                    border-color: #bfdbfe;
                    border-left: 4px solid #2563eb;
                }

                .phase-header {
                    padding: 16px 24px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    cursor: pointer;
                    background: #f8fafc;
                    border-bottom: 1px solid transparent;
                    transition: background 0.2s;
                }

                .phase-section.active .phase-header {
                    background: #eff6ff; /* Lighter blue tint */
                    border-bottom-color: #e2e8f0;
                }

                .phase-title h3 {
                    margin: 0;
                    font-size: 16px;
                    font-weight: 600;
                    color: #1e293b;
                }
                
                .phase-progress {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-top: 4px;
                }

                .phase-content {
                    padding: 24px;
                    animation: slideDown 0.3s ease-out;
                }

                @keyframes slideDown {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .toggle-icon {
                    width: 28px;
                    height: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #f1f5f9;
                    border-radius: 50%;
                    color: #64748b;
                    font-weight: bold;
                    transition: all 0.2s;
                    font-size: 18px;
                }

                .phase-header:hover .toggle-icon {
                    background: #e2e8f0;
                    color: #334155;
                }
                
                /* Modal Styles */
                .modal-overlay {
                    position: fixed;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 2000;
                    backdrop-filter: blur(4px);
                }
                
                .review-modal {
                    background: white;
                    border-radius: 16px;
                    width: 90%;
                    max-width: 600px;
                    max-height: 90vh;
                    overflow-y: auto;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
                }
                
                .review-header {
                    padding: 24px;
                    border-bottom: 1px solid #e2e8f0;
                }
                
                .review-body {
                    padding: 24px;
                }
                
                .review-footer {
                    padding: 20px 24px;
                    background: #f8fafc;
                    display: flex;
                    justify-content: flex-end;
                    gap: 12px;
                    border-top: 1px solid #e2e8f0;
                }
                
                .review-phase-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 12px;
                    border-bottom: 1px solid #f1f5f9;
                }
                
                .review-phase-item.complete .status { color: #10b981; }
                .review-phase-item.incomplete .status { color: #f59e0b; }
                
                .btn-secondary {
                    padding: 10px 20px;
                    border-radius: 8px;
                    border: 1px solid #e2e8f0;
                    background: white;
                    color: #64748b;
                    font-weight: 500;
                    cursor: pointer;
                }
                
                .btn-primary {
                    padding: 10px 20px;
                    border-radius: 8px;
                    border: none;
                    background: #2563eb;
                    color: white;
                    font-weight: 500;
                    cursor: pointer;
                    box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
                }

                /* Chip hover */
                .chip-btn:hover {
                    background: #f1f5f9 !important;
                    border-color: #94a3b8 !important;
                }

                    font-size: 16px;
                    font-weight: 600;
                    color: #1e293b;
                }
                
                .phase-progress {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-top: 4px;
                }

                .phase-content {
                    padding: 24px;
                    animation: slideDown 0.3s ease-out;
                }

                @keyframes slideDown {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                .toggle-icon {
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #f1f5f9;
                    border-radius: 50%;
                    color: #64748b;
                    font-weight: bold;
                    transition: all 0.2s;
                }

                .phase-header:hover .toggle-icon {
                    background: #e2e8f0;
                    color: #334155;
                }

                /* Conditional Toggle Styles */
                .toggle-section {
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 16px;
                }
                
                .toggle-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .toggle-label {
                    font-weight: 500;
                    color: #334155;
                }

                .switch {
                    position: relative;
                    display: inline-block;
                    width: 44px;
                    height: 24px;
                }
                
                .switch input { opacity: 0; width: 0; height: 0; }
                
                .slider {
                    position: absolute;
                    cursor: pointer;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background-color: #cbd5e1;
                    transition: .4s;
                    border-radius: 34px;
                }
                
                .slider:before {
                    position: absolute;
                    content: "";
                    height: 18px;
                    width: 18px;
                    left: 3px;
                    bottom: 3px;
                    background-color: white;
                    transition: .4s;
                    border-radius: 50%;
                }
                
                input:checked + .slider { background-color: #2563eb; }
                input:checked + .slider:before { transform: translateX(20px); }

                /* Chips for Navigation */
                .chip-group {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    margin-top: 8px;
                }
                
                .chip-btn {
                    padding: 6px 12px;
                    border-radius: 16px;
                    border: 1px solid #cbd5e1;
                    background: white;
                    color: #64748b;
                    font-size: 13px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                
                .chip-btn:hover {
                    border-color: #94a3b8;
                    background: #f8fafc;
                }
                
                .chip-btn.active {
                    background: #eff6ff;
                    border-color: #3b82f6;
                    color: #2563eb;
                    font-weight: 500;
                }

                /* Enhanced Phase Header */
                .phase-header {
                   padding: 20px 24px;
                }
                .phase-title h3 {
                    margin: 0;
                    font-size: 16px;
                    font-weight: 600;
                    color: #1e293b;
                }
                .progress-bar-small {
                    width: 100px;
                    height: 6px;
                    background: #e2e8f0;
                    border-radius: 3px;
                    overflow: hidden;
                }
                .progress-bar-small .fill {
                    height: 100%;
                    background: #10b981;
                    transition: width 0.3s;
                }
                .percentage {
                    font-size: 13px;
                    font-weight: 500;
                    color: #64748b;
                }
                .toggle-icon {
                    width: 32px;
                    height: 32px;
                    font-size: 20px;
                    transition: transform 0.3s;
                }
                .toggle-icon.expanded {
                    transform: rotate(180deg);
                }

                /* Chatbot Tooltip */
                .chat-tooltip {
                    position: absolute;
                    bottom: 70px;
                    right: 0;
                    background: white;
                    padding: 8px 12px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    font-size: 13px;
                    font-weight: 600;
                    color: #1e293b;
                    white-space: nowrap;
                    pointer-events: none;
                }
                .chat-tooltip:after {
                    content: '';
                    position: absolute;
                    bottom: -6px;
                    right: 24px;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 6px solid white;
                }
                @keyframes bounceSlow {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                }
                .animate-bounce-slow {
                    animation: bounceSlow 2s infinite;
                }

                /* Fixed Bottom Bar */
                .bottom-action-bar {
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    background: white;
                    border-top: 1px solid #e2e8f0;
                    padding: 16px 32px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    z-index: 900;
                    box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.05);
                }
                .bottom-bar-spacer {
                    height: 80px;
                }

                /* Checklist Panel */
                .checklist-panel {
                    background: white;
                    border-radius: 12px;
                    border: 1px solid #e2e8f0;
                    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
                    overflow: hidden;
                }

                .checklist-header {
                    padding: 16px;
                    background: #f1f5f9;
                    border-bottom: 1px solid #e2e8f0;
                }

                .checklist-header h3 {
                    margin: 0;
                    font-size: 14px;
                    font-weight: 600;
                    color: #334155;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }

                .checklist-content {
                    padding: 0;
                }

                .checklist-item {
                    display: flex;
                    flex-direction: row;
                    flex-wrap: nowrap;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    padding: 12px 16px;
                    border-bottom: 1px solid #f1f5f9;
                    cursor: pointer;
                    transition: background 0.1s;
                    font-size: 13px;
                    color: #475569;
                }

                .checklist-item:hover {
                    background: #f8fafc;
                    color: #1e293b;
                }

                .checklist-item.completed {
                    color: #10b981;
                    background: #effdf5;
                }

                .checklist-status {
                    width: 16px;
                    height: 16px;
                    border: 1.5px solid #cbd5e1;
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-shrink: 0;
                }

                .checklist-item.completed .checklist-status {
                    background: #10b981;
                    border-color: #10b981;
                    color: white;
                    font-size: 10px;
                }


            `}</style>

            {/* Lightbox Modal */}
            {
                previewImage && (
                    <div className="lightbox-overlay" onClick={() => setPreviewImage(null)}>
                        <div className="lightbox-content" onClick={e => e.stopPropagation()}>
                            <button className="lightbox-close" onClick={() => setPreviewImage(null)}>×</button>
                            <img src={previewImage} alt="Full size preview" />
                        </div>
                    </div>
                )
            }

            {/* Consolidated Chatbot Widget */}
            <div className="chatbot-widget-container">
                {!showChatbot && (
                    <div className="chat-tooltip">
                        Need help? Chat with us!
                    </div>
                )}

                <button className={`chatbot-toggle ${showChatbot ? 'active' : ''}`} onClick={() => setShowChatbot(!showChatbot)}>
                    {showChatbot ? '×' : '💬'}
                </button>

                {showChatbot && (
                    <div className="chatbot-window">
                        <div className="chatbot-header">
                            <h4>Consultant AI</h4>
                            <button onClick={() => setShowChatbot(false)} style={{ background: 'none', border: 'none', color: 'white', fontSize: '20px', cursor: 'pointer' }}>×</button>
                        </div>
                        <div className="chatbot-body" ref={chatContainerRef}>
                            {chatMessages.map((msg, idx) => (
                                <div key={idx} className={`chat-message ${msg.isBot ? 'bot' : 'user'}`} style={!msg.isBot ? { marginLeft: 'auto', background: '#2563eb', color: 'white' } : {}}>
                                    {msg.sender === 'consultant' && <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#2563eb', marginBottom: '2px' }}>Consultant</div>}
                                    {msg.sender === 'bot' && <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#64748b', marginBottom: '2px' }}>AI Assistant</div>}
                                    <p style={{ margin: 0 }}>{msg.text}</p>
                                </div>
                            ))}
                        </div>
                        <form className="chatbot-input" onSubmit={handleSendMessage}>
                            <input
                                type="text"
                                placeholder="Type a message..."
                                value={chatInput}
                                onChange={(e) => setChatInput(e.target.value)}
                            />
                            <button type="submit">→</button>
                        </form>
                    </div>
                )}
            </div>

            <style jsx>{`
                .chatbot-widget-container {
                    position: fixed;
                    bottom: 100px;
                    right: 24px;
                    z-index: 2000;
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    gap: 12px;
                }

                .chatbot-toggle {
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    background: #2563eb;
                    color: white;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                    z-index: 2002;
                }

                .chatbot-toggle:hover {
                    transform: scale(1.05);
                    background: #1d4ed8;
                }

                .chatbot-toggle.active {
                    transform: rotate(90deg);
                    background: #64748b;
                }

                .chat-tooltip {
                    background: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    font-size: 14px;
                    font-weight: 500;
                    color: #1e293b;
                    white-space: nowrap;
                    margin-bottom: 8px;
                    position: absolute;
                    bottom: 100%;
                    right: 0;
                    margin-bottom: 12px;
                    animation: float 3s ease-in-out infinite;
                }

                .chat-tooltip:after {
                    content: '';
                    position: absolute;
                    bottom: -6px;
                    right: 24px;
                    border-left: 6px solid transparent;
                    border-right: 6px solid transparent;
                    border-top: 6px solid white;
                }

                .chatbot-window {
                    position: absolute;
                    bottom: 100%;
                    right: 0;
                    margin-bottom: 12px;
                    width: 360px;
                    height: 520px;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 10px 40px -5px rgba(0, 0, 0, 0.2);
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    border: 1px solid #e2e8f0;
                    z-index: 2001;
                    animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                    transform-origin: bottom right;
                }

                .chatbot-header {
                    padding: 16px 20px;
                    background: #2563eb;
                    color: white !important;
                    border-bottom: 1px solid #1d4ed8;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .chatbot-header h4 {
                    margin: 0;
                    font-size: 16px;
                    font-weight: 600;
                    color: white !important;
                }
                
                .chatbot-body {
                     padding: 16px;
                     overflow-y: auto;
                     flex: 1;
                     background: #f8fafc;
                }

                .chat-message {
                    padding: 12px;
                    border-radius: 8px;
                    font-size: 14px;
                    line-height: 1.5;
                    margin-bottom: 12px;
                    max-width: 85%;
                    word-break: break-word;
                    white-space: pre-wrap;
                }

                .chat-message.bot {
                    background: white;
                    border: 1px solid #e2e8f0;
                    color: #1e293b;
                    border-bottom-left-radius: 2px;
                }

                .chat-message.user {
                    background-color: #2563eb;
                    color: white !important;
                    margin-left: auto;
                    border-bottom-right-radius: 2px;
                }

                .chat-message p {
                    margin: 0;
                }
                
                .chat-message.user *, .chat-message.user p {
                    color: white !important;
                }

                .chatbot-input {
                    background: white;
                    border-top: 1px solid #e2e8f0;
                    padding: 12px;
                    display: flex;
                    gap: 8px;
                }

                .chatbot-input input {
                    flex: 1;
                    padding: 8px 12px;
                    border: 1px solid #e2e8f0;
                    border-radius: 20px;
                    font-size: 13px;
                    outline: none;
                }

                .chatbot-input button {
                     background: none;
                     border: none;
                     color: #2563eb;
                     font-weight: bold;
                     cursor: pointer;
                }

                @keyframes float {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-6px); }
                }

                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(20px) scale(0.95); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                /* Templates Grid */
                .templates-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 24px;
                    margin-top: 24px;
                }

                .template-card {
                    background: white;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    overflow: hidden;
                    cursor: pointer;
                    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                }

                .template-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.15);
                    border-color: #93c5fd;
                }

                .template-card.selected {
                    border-color: #2563eb;
                    box-shadow: 0 0 0 2px #2563eb, 0 12px 24px -8px rgba(37, 99, 235, 0.2);
                }

                .template-preview {
                    height: 180px;
                    background: #f1f5f9;
                    position: relative;
                    overflow: hidden;
                }

                .template-thumb {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    transition: transform 0.5s;
                }

                .template-card:hover .template-thumb {
                    transform: scale(1.05);
                }

                .template-thumb-placeholder {
                    width: 100%;
                    height: 100%;
                }

                .selected-overlay {
                    position: absolute;
                    inset: 0;
                    background: rgba(37, 99, 235, 0.1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 32px;
                    font-weight: bold;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    backdrop-filter: blur(1px);
                }
                
                .selected-overlay:after {
                    content: '✓';
                    background: #2563eb;
                    width: 48px;
                    height: 48px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }

                .template-info {
                    padding: 16px;
                }

                .template-info h4 {
                    margin: 0 0 8px 0;
                    color: #1e293b;
                    font-size: 16px;
                    font-weight: 600;
                }

                .template-info p {
                    margin: 0;
                    color: #64748b;
                    font-size: 13px;
                    line-height: 1.5;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                }

            `}</style>
        </div >
    );
}
