'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { clientAPI } from '@/lib/api';

interface Template {
    id: string;
    name: string;
    description: string;
    preview_url: string;
    colors: { primary: string; secondary: string; accent: string };
    features: string[];
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

    const logoInputRef = useRef<HTMLInputElement>(null);
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
                data: { ...prev.data, ...updates }
            } : null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save changes');
        } finally {
            setSaving(false);
        }
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

        const items = [
            // Assets
            { id: 'logo', label: 'Company Logo', provided: !!(data.logo_url || data.logo_file_path), eta: missingFieldsEta['Company Logo'] },
            { id: 'images', label: 'Website Images', provided: (data.images?.length || 0) > 0, eta: missingFieldsEta['Website Images'] },
            { id: 'copy', label: 'Copy Text', provided: !!(data.copy_text || data.use_custom_copy), eta: missingFieldsEta['Copy Text'] },
            { id: 'wcag', label: 'Accessibility Choice', provided: data.wcag_confirmed !== undefined, eta: missingFieldsEta['WCAG Compliance'] },
            { id: 'privacy', label: 'Privacy Policy', provided: !!(data.privacy_policy_url || data.privacy_policy_text), eta: missingFieldsEta['Privacy Policy'] },
            { id: 'theme', label: 'Theme Selection', provided: !!(data.selected_template_id), eta: missingFieldsEta['Theme Preference'] },
            { id: 'contacts', label: 'Contacts', provided: (data.contacts?.length || 0) > 0, eta: missingFieldsEta['Contacts'] },

            // Project Requirements
            { id: 'project_summary', label: 'Project Summary', provided: hasValue(req.project_summary), eta: missingFieldsEta['Project Summary'] },
            { id: 'project_notes', label: 'Project Notes', provided: hasValue(req.project_notes), eta: missingFieldsEta['Project Notes'] },
            { id: 'phase_number', label: 'Phase', provided: hasValue(req.phase_number), eta: missingFieldsEta['Phase'] },
            { id: 'template_mode', label: 'Template Mode', provided: hasValue(req.template_mode), eta: missingFieldsEta['Template Mode'] },
            { id: 'template_references', label: 'Template References', provided: hasValue(req.template_references), eta: missingFieldsEta['Template References'] },
            { id: 'brand_guidelines', label: 'Brand Guidelines', provided: data.requirements?.brand_guidelines_available === true ? hasValue(req.brand_guidelines_details) : data.requirements?.brand_guidelines_available === false, eta: missingFieldsEta['Brand Guidelines'] },
            { id: 'color_selection', label: 'Color Selection', provided: hasValue(req.color_selection), eta: missingFieldsEta['Color Selection'] },
            { id: 'font_selection', label: 'Font Selection', provided: hasValue(req.font_selection), eta: missingFieldsEta['Font Selection'] },
            { id: 'custom_graphics', label: 'Custom Graphics', provided: data.requirements?.custom_graphic_notes_enabled === true ? hasValue(req.custom_graphic_notes) : data.requirements?.custom_graphic_notes_enabled === false, eta: missingFieldsEta['Custom Graphics'] },
            { id: 'navigation', label: 'Navigation', provided: hasValue(req.navigation_notes), eta: missingFieldsEta['Navigation'] },
            { id: 'stock_images', label: 'Stock Images', provided: hasValue(req.stock_images_reference), eta: missingFieldsEta['Stock Images'] },
            { id: 'floor_plans', label: 'Floor Plans', provided: hasValue(req.floor_plan_images), eta: missingFieldsEta['Floor Plans'] },
            { id: 'sitemap', label: 'Sitemap', provided: hasValue(req.sitemap), eta: missingFieldsEta['Sitemap'] },
            { id: 'virtual_tours', label: 'Virtual Tours', provided: hasValue(req.virtual_tours), eta: missingFieldsEta['Virtual Tours'] },
            { id: 'poi', label: 'POI Categories', provided: hasValue(req.poi_categories), eta: missingFieldsEta['POI Categories'] },
            { id: 'specials', label: 'Specials', provided: data.requirements?.specials_enabled === true ? hasValue(req.specials_details) : data.requirements?.specials_enabled === false, eta: missingFieldsEta['Specials'] },
            { id: 'copy_scope', label: 'Copy Scope', provided: hasValue(req.copy_scope_notes), eta: missingFieldsEta['Copy Scope'] },
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
            setSuccess('Form submitted successfully! Your consultant has been notified.');
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
                                strokeDasharray={`${formData.completion_percentage}, 100`}
                                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            />
                        </svg>
                        <span className="ring-value">{formData.completion_percentage}%</span>
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
            {error && <div className="alert alert-error">{error}</div>}
            {success && <div className="alert alert-success">{success}</div>}

            {/* Missing Fields Alert */}
            {/* Requirements Checklist Unified */}
            {getAllRequirements().filter(i => !i.provided).length > 0 ? (
                <div className="missing-alert">
                    <h3>⚠️ Action Required</h3>
                    <p>Please complete the following items ({getAllRequirements().filter(i => !i.provided).length} remaining):</p>
                    <div className="missing-fields-grid">
                        {getAllRequirements().filter(i => !i.provided).map((item, i) => (
                            <div key={item.id} className="missing-field-row">
                                <span className="checklist-icon">❌</span>
                                <div className="missing-field-name">{item.label}</div>
                                <div className="missing-field-actions">
                                    <button type="button" className="eta-btn" onClick={() => setEtaInDays(item.label, 1)}>1 day</button>
                                    <button type="button" className="eta-btn" onClick={() => setEtaInDays(item.label, 2)}>2 days</button>
                                    <input
                                        type="date"
                                        className="eta-input"
                                        value={missingFieldsEta[item.label] || ''}
                                        onChange={(e) =>
                                            setMissingFieldsEta(prev => ({ ...prev, [item.label]: e.target.value }))
                                        }
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                    <button className="btn-submit-form" disabled={saving} onClick={submitClientForm}>
                        {saving ? 'Submitting...' : 'Submit Form'}
                    </button>
                </div>
            ) : (
                <div className="missing-alert success-alert">
                    <h3>✅ All Set!</h3>
                    <p>You have provided all necessary information. Please review and submit.</p>
                    <button className="btn-submit-form" disabled={saving} onClick={submitClientForm}>
                        {saving ? 'Submitting...' : 'Submit Form'}
                    </button>
                </div>
            )}

            <main className="form-container">
                {/* Project Requirements */}
                <section className="form-section">
                    <h2>🧾 Project Requirements</h2>
                    <p className="section-desc">Share details to guide the project across all locations.</p>

                    <div className="form-group">
                        <label>Project Summary</label>
                        <textarea
                            value={formData.data.requirements?.project_summary || ''}
                            onChange={(e) => updateRequirementsLocal({ project_summary: e.target.value })}
                            onBlur={() => saveFormData({ requirements: formData.data.requirements })}
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
                </section>

                {/* Logo Upload Section */}
                <section className="form-section">
                    <h2>🖼️ Company Logo</h2>
                    <p className="section-desc">Upload your company logo (PNG, SVG, or JPEG)</p>

                    <div className="upload-area">
                        {formData.data.logo_url || formData.data.logo_file_path ? (
                            <div className="logo-preview-container">
                                <div className="logo-preview-card">
                                    <img
                                        src={getAssetUrl(formData.data.logo_url || formData.data.logo_file_path)}
                                        alt="Company Logo"
                                        className="logo-thumbnail"
                                        onClick={() => setPreviewImage(getAssetUrl(formData.data.logo_url || formData.data.logo_file_path))}
                                        title="Click to preview"
                                    />
                                    <div className="logo-actions">
                                        <div className="preview-badge">✓ Logo Uploaded</div>
                                        <div className="logo-btn-group">
                                            <button className="btn-replace" onClick={() => logoInputRef.current?.click()}>
                                                Replace
                                            </button>
                                            <button className="btn-remove-logo" onClick={handleDeleteLogo}>
                                                Remove
                                            </button>
                                        </div>
                                    </div>
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
                    </div>

                    <div className="or-divider"><span>or</span></div>

                    <div className="url-input">
                        <label>Logo URL</label>
                        <input
                            type="url"
                            value={formData.data.logo_url || ''}
                            onChange={(e) => updateLocalData({ logo_url: e.target.value })}
                            onBlur={() => saveFormData({ logo_url: formData.data.logo_url })}
                            placeholder="https://example.com/logo.png"
                        />
                    </div>
                </section>

                {/* Images Upload Section */}
                <section className="form-section">
                    <h2>📸 Website Images</h2>
                    <p className="section-desc">Upload images for your website (hero images, product photos, etc.)</p>

                    <div className="images-grid">
                        {formData.data.images?.map((img, i) => {
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
                                        />
                                        <button
                                            className="btn-delete"
                                            onClick={() => handleDeleteImage(i)}
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
                        <div className="upload-placeholder-card" onClick={() => imageInputRef.current?.click()}>
                            <span className="upload-icon">+</span>
                            <span>Add Image</span>
                        </div>
                    </div>
                    <input
                        ref={imageInputRef}
                        type="file"
                        accept="image/*"
                        multiple
                        onChange={handleImageUpload}
                        hidden
                    />
                </section>

                {/* Copy Text Section with Pricing */}
                <section className="form-section">
                    <h2>📝 Website Copy</h2>
                    <p className="section-desc">Provide your website text content or request custom copywriting</p>

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
                                placeholder="Enter all your website text content here..."
                                rows={6}
                            />
                        </div>
                    ) : (
                        <div className="pricing-section">
                            <h4>💰 Select a Copywriting Package</h4>
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
                            {formData.data.custom_copy_final_price && (
                                <div className="final-price">
                                    <strong>Your Selected Package:</strong> ${formData.data.custom_copy_final_price}
                                    <p>Up to {formData.data.custom_copy_word_count} words</p>
                                </div>
                            )}
                        </div>
                    )}
                </section>

                {/* Theme Templates Section */}
                <section className="form-section">
                    <h2>🎨 Website Template</h2>
                    <p className="section-desc">Choose a design template for your website</p>

                    <div className="templates-grid">
                        {formData.templates.map((template) => (
                            <div
                                key={template.id}
                                className={`template-card ${formData.data.selected_template_id === template.id ? 'selected' : ''}`}
                                onClick={() => selectTemplate(template.id)}
                            >
                                <div className="template-preview" style={{
                                    background: `linear-gradient(135deg, ${template.colors.primary} 0%, ${template.colors.secondary} 100%)`
                                }}>
                                    {formData.data.selected_template_id === template.id && (
                                        <div className="selected-overlay">✓</div>
                                    )}
                                </div>
                                <div className="template-info">
                                    <h4>{template.name}</h4>
                                    <p>{template.description}</p>
                                    <div className="template-features">
                                        {template.features.slice(0, 2).map((f, i) => (
                                            <span key={i} className="feature-tag">{f}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="form-group">
                        <label>Template Direction</label>
                        <div className="radio-group">
                            <label>
                                <input
                                    type="radio"
                                    name="template_mode"
                                    checked={formData.data.requirements?.template_mode === 'NEW'}
                                    onChange={() => updateRequirements({ template_mode: 'NEW' })}
                                />
                                New design
                            </label>
                            <label>
                                <input
                                    type="radio"
                                    name="template_mode"
                                    checked={formData.data.requirements?.template_mode === 'CLONE'}
                                    onChange={() => updateRequirements({ template_mode: 'CLONE' })}
                                />
                                Clone from existing template
                            </label>
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Reference links (optional)</label>
                        <textarea
                            value={formData.data.requirements?.template_references || ''}
                            onChange={(e) => updateRequirementsLocal({ template_references: e.target.value })}
                            onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                            rows={3}
                            placeholder="Add links or notes for reference..."
                        />
                    </div>
                </section>

                {/* WCAG Section */}
                <section className="form-section">
                    <h2>♿ Accessibility</h2>
                    <div className="checkbox-group">
                        <label>
                            <input
                                type="checkbox"
                                checked={formData.data.wcag_compliance_required}
                                onChange={(e) => saveFormData({
                                    wcag_compliance_required: e.target.checked,
                                    wcag_confirmed: true  // Mark as explicitly confirmed by client
                                })}
                            />
                            WCAG Compliance Required
                        </label>
                    </div>
                    {formData.data.wcag_compliance_required && (
                        <div className="select-group">
                            <label>Compliance Level</label>
                            <select
                                value={formData.data.wcag_level}
                                onChange={(e) => saveFormData({
                                    wcag_level: e.target.value,
                                    wcag_confirmed: true  // Mark as explicitly confirmed by client
                                })}
                            >
                                <option value="A">Level A (Minimum)</option>
                                <option value="AA">Level AA (Standard)</option>
                                <option value="AAA">Level AAA (Enhanced)</option>
                            </select>
                        </div>
                    )}
                </section>

                {/* Privacy Policy Section */}
                <section className="form-section">
                    <h2>🔒 Privacy Policy</h2>
                    <div className="url-input">
                        <label>Privacy Policy URL</label>
                        <input
                            type="url"
                            value={formData.data.privacy_policy_url || ''}
                            onChange={(e) => updateLocalData({ privacy_policy_url: e.target.value })}
                            onBlur={() => saveFormData({ privacy_policy_url: formData.data.privacy_policy_url })}
                            placeholder="https://example.com/privacy"
                        />
                    </div>
                    <div className="or-divider"><span>or</span></div>
                    <div className="copy-input">
                        <label>Privacy Policy Text</label>
                        <textarea
                            value={formData.data.privacy_policy_text || ''}
                            onChange={(e) => updateLocalData({ privacy_policy_text: e.target.value })}
                            onBlur={() => saveFormData({ privacy_policy_text: formData.data.privacy_policy_text })}
                            placeholder="Paste your privacy policy here..."
                            rows={4}
                        />
                    </div>
                </section>

                <section className="form-section">
                    <h2>🧩 Design & Content Details</h2>
                    <p className="section-desc">Add preferences to guide the build and testing teams.</p>

                    <div className="form-group">
                        <label>Brand Guidelines</label>
                        <div className="radio-group">
                            <label>
                                <input
                                    type="radio"
                                    name="brand_guidelines"
                                    checked={formData.data.requirements?.brand_guidelines_available === true}
                                    onChange={() => updateRequirements({ brand_guidelines_available: true })}
                                />
                                Yes
                            </label>
                            <label>
                                <input
                                    type="radio"
                                    name="brand_guidelines"
                                    checked={formData.data.requirements?.brand_guidelines_available === false}
                                    onChange={() => updateRequirements({ brand_guidelines_available: false })}
                                />
                                No
                            </label>
                        </div>
                        {formData.data.requirements?.brand_guidelines_available && (
                            <textarea
                                value={formData.data.requirements?.brand_guidelines_details || ''}
                                onChange={(e) => updateRequirementsLocal({ brand_guidelines_details: e.target.value })}
                                onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                                rows={3}
                                placeholder="Add brand guidelines link or details..."
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
                    <div className="form-group">
                        <label>Color Notes / Codes</label>
                        <input
                            type="text"
                            value={formData.data.requirements?.color_notes || ''}
                            onChange={(e) => updateRequirementsLocal({ color_notes: e.target.value })}
                            onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                            placeholder="Hex codes or color notes"
                        />
                    </div>

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
                    <div className="form-group">
                        <label>Font Notes</label>
                        <input
                            type="text"
                            value={formData.data.requirements?.font_notes || ''}
                            onChange={(e) => updateRequirementsLocal({ font_notes: e.target.value })}
                            onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                            placeholder="Font details or links"
                        />
                    </div>

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
                                rows={3}
                                placeholder="Describe custom graphic needs..."
                            />
                        )}
                    </div>

                    <div className="select-group">
                        <label>Navigation Notes</label>
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
                    <div className="form-group">
                        <label>Navigation Details</label>
                        <textarea
                            value={formData.data.requirements?.navigation_notes || ''}
                            onChange={(e) => updateRequirementsLocal({ navigation_notes: e.target.value })}
                            onBlur={() => saveFormData({ requirements: formData.data.requirements })}
                            rows={3}
                            placeholder="Add navigation notes..."
                        />
                    </div>

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
                            onChange={(e) => updateRequirements({ floor_plan_images: e.target.value })}
                            rows={2}
                            placeholder="Links or notes for floor plan images..."
                        />
                    </div>
                    <div className="form-group">
                        <label>Sitemap</label>
                        <textarea
                            value={formData.data.requirements?.sitemap || ''}
                            onChange={(e) => updateRequirements({ sitemap: e.target.value })}
                            rows={2}
                            placeholder="Sitemap links or details..."
                        />
                    </div>
                    <div className="form-group">
                        <label>Virtual Tours</label>
                        <textarea
                            value={formData.data.requirements?.virtual_tours || ''}
                            onChange={(e) => updateRequirements({ virtual_tours: e.target.value })}
                            rows={2}
                            placeholder="Virtual tour links..."
                        />
                    </div>
                    <div className="form-group">
                        <label>Point of Interest Categories & Details</label>
                        <textarea
                            value={formData.data.requirements?.poi_categories || ''}
                            onChange={(e) => updateRequirements({ poi_categories: e.target.value })}
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
                                onChange={(e) => updateRequirements({ specials_details: e.target.value })}
                                rows={2}
                                placeholder="Describe specials to add..."
                            />
                        )}
                    </div>

                    <div className="form-group">
                        <label>Copy Text Scope – Additional Notes</label>
                        <textarea
                            value={formData.data.requirements?.copy_scope_notes || ''}
                            onChange={(e) => updateRequirements({ copy_scope_notes: e.target.value })}
                            rows={3}
                            placeholder="Additional notes about copy scope..."
                        />
                    </div>

                    <div className="form-group">
                        <label>Pages for the Website</label>
                        <textarea
                            value={formData.data.requirements?.pages || ''}
                            onChange={(e) => updateRequirements({ pages: e.target.value })}
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
                </section>

                <div className="submit-section">
                    <button className="btn-submit-form" disabled={saving} onClick={submitClientForm}>
                        {saving ? 'Submitting...' : 'Submit Form'}
                    </button>
                </div>
            </main>

            <footer className="page-footer">
                <p>Questions? Contact your project manager for assistance.</p>
            </footer>

            <style jsx>{`
                .client-page {
                    min-height: 100vh;
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
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
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    margin: 12px 0 16px;
                }
                .missing-field-row {
                    display: flex;
                    flex-wrap: wrap;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    padding: 10px 12px;
                    background: #fff7ed;
                    border: 1px solid #fed7aa;
                    border-radius: 10px;
                }
                .missing-field-name {
                    font-weight: 600;
                    color: #7c2d12;
                }
                .missing-field-actions {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    align-items: center;
                }
                .eta-btn {
                    padding: 6px 10px;
                    font-size: 12px;
                    border-radius: 6px;
                    border: 1px solid #fdba74;
                    background: white;
                    color: #9a3412;
                    cursor: pointer;
                }
                .eta-btn:hover {
                    background: #ffedd5;
                }
                .eta-input {
                    padding: 6px 10px;
                    border: 1px solid #fdba74;
                    border-radius: 6px;
                    font-size: 12px;
                    color: #9a3412;
                    background: white;
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
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
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
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
            `}</style>

            {/* Lightbox Modal */}
            {previewImage && (
                <div className="lightbox-overlay" onClick={() => setPreviewImage(null)}>
                    <div className="lightbox-content" onClick={e => e.stopPropagation()}>
                        <button className="lightbox-close" onClick={() => setPreviewImage(null)}>×</button>
                        <img src={previewImage} alt="Full size preview" />
                    </div>
                </div>
            )}
        </div>
    );
}
