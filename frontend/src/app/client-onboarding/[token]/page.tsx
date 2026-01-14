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

interface OnboardingFormData {
    project_title: string;
    project_id: string;
    completion_percentage: number;
    missing_fields: string[];
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

    const logoInputRef = useRef<HTMLInputElement>(null);
    const imageInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        loadFormData();
    }, [token]);

    const loadFormData = async () => {
        try {
            const res = await clientAPI.getOnboardingForm(token);
            setFormData(res.data);
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

    const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setSaving(true);
        try {
            await clientAPI.uploadImage(token, file);
            setSuccess('Image uploaded successfully!');
            await loadFormData();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to upload image');
        } finally {
            setSaving(false);
        }
    };

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
                    <span className="completion-label">Complete</span>
                </div>
            </header>

            {/* Alerts */}
            {error && <div className="alert alert-error">{error}</div>}
            {success && <div className="alert alert-success">{success}</div>}

            {/* Missing Fields Alert */}
            {formData.missing_fields.length > 0 && (
                <div className="missing-alert">
                    <h3>⚠️ Information Needed</h3>
                    <p>Please provide the following to complete your onboarding:</p>
                    <ul>
                        {formData.missing_fields.map((field, i) => (
                            <li key={i}>{field}</li>
                        ))}
                    </ul>
                </div>
            )}

            <main className="form-container">
                {/* Logo Upload Section */}
                <section className="form-section">
                    <h2>🖼️ Company Logo</h2>
                    <p className="section-desc">Upload your company logo (PNG, SVG, or JPEG)</p>
                    
                    <div className="upload-area">
                        {formData.data.logo_file_path || formData.data.logo_url ? (
                            <div className="uploaded-preview">
                                <div className="preview-badge">✓ Logo Uploaded</div>
                                <p>{formData.data.logo_file_path || formData.data.logo_url}</p>
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
                        <button className="btn-upload" onClick={() => logoInputRef.current?.click()}>
                            {formData.data.logo_file_path ? 'Replace Logo' : 'Upload Logo'}
                        </button>
                    </div>

                    <div className="or-divider"><span>or</span></div>
                    
                    <div className="url-input">
                        <label>Logo URL</label>
                        <input
                            type="url"
                            value={formData.data.logo_url || ''}
                            onChange={(e) => saveFormData({ logo_url: e.target.value })}
                            placeholder="https://example.com/logo.png"
                        />
                    </div>
                </section>

                {/* Images Upload Section */}
                <section className="form-section">
                    <h2>📸 Website Images</h2>
                    <p className="section-desc">Upload images for your website (hero images, product photos, etc.)</p>
                    
                    <div className="images-grid">
                        {formData.data.images?.map((img, i) => (
                            <div key={i} className="image-item">
                                <span className="image-badge">✓</span>
                                <span className="image-name">{img.filename || img}</span>
                            </div>
                        ))}
                        <div className="upload-placeholder small" onClick={() => imageInputRef.current?.click()}>
                            <span className="upload-icon">+</span>
                            <span>Add Image</span>
                        </div>
                    </div>
                    <input
                        ref={imageInputRef}
                        type="file"
                        accept="image/*"
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
                                onChange={(e) => saveFormData({ copy_text: e.target.value })}
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
                            onChange={(e) => saveFormData({ privacy_policy_url: e.target.value })}
                            placeholder="https://example.com/privacy"
                        />
                    </div>
                    <div className="or-divider"><span>or</span></div>
                    <div className="copy-input">
                        <label>Privacy Policy Text</label>
                        <textarea
                            value={formData.data.privacy_policy_text || ''}
                            onChange={(e) => saveFormData({ privacy_policy_text: e.target.value })}
                            placeholder="Paste your privacy policy here..."
                            rows={4}
                        />
                    </div>
                </section>
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
            `}</style>
        </div>
    );
}

