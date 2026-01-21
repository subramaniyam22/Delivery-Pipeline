'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { configurationAPI } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import Navigation from '@/components/Navigation';

interface ThemeTemplate {
    id: string;
    name: string;
    description: string;
    preview_url: string;
    actual_web_url: string;
    colors_json: any;
    features_json: string[];
    is_active: boolean;
    is_published: boolean;
}

export default function ConfigurationPage() {
    const router = useRouter();
    const [user, setUser] = useState<any>(null);
    const [templates, setTemplates] = useState<ThemeTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Form State
    const [showAddForm, setShowAddForm] = useState(false);
    const [showBulkUpload, setShowBulkUpload] = useState(false);
    const [newTemplate, setNewTemplate] = useState({
        id: '',
        name: '',
        description: '',
        preview_url: '',
        actual_web_url: '',
        colors_json: { primary: '#000000', secondary: '#333333', accent: '#666666' },
        features_input: '' // Comma separated
    });

    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = async () => {
        try {
            const currentUser = getCurrentUser();
            if (!currentUser || !['ADMIN', 'MANAGER'].includes(currentUser.role)) {
                router.push('/projects');
                return;
            }
            setUser(currentUser);
            loadTemplates();
        } catch (err) {
            router.push('/login');
        }
    };

    const loadTemplates = async () => {
        try {
            setLoading(true);
            const res = await configurationAPI.getTemplates();
            setTemplates(res.data);
        } catch (err) {
            setError('Failed to load templates');
        } finally {
            setLoading(false);
        }
    };

    const handleAddTemplate = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        try {
            // Process features
            const features = newTemplate.features_input.split(',').map(f => f.trim()).filter(f => f);

            await configurationAPI.createTemplate({
                ...newTemplate,
                features_json: features,
                // colors_json is already an object
            });

            setSuccess('Template added successfully');
            setShowAddForm(false);
            setNewTemplate({
                id: '',
                name: '',
                description: '',
                preview_url: '',
                actual_web_url: '',
                colors_json: { primary: '#000000', secondary: '#333333', accent: '#666666' },
                features_input: ''
            });
            loadTemplates();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create template');
        }
    };

    const handleDeleteTemplate = async (id: string) => {
        if (!confirm('Are you sure you want to delete this template?')) return;

        try {
            await configurationAPI.deleteTemplate(id);
            setSuccess('Template deleted');
            loadTemplates();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete template');
        }
    };

    const handleTogglePublish = async (id: string, currentStatus: boolean) => {
        try {
            await configurationAPI.togglePublish(id, !currentStatus);
            setSuccess(`Template ${!currentStatus ? 'published' : 'unpublished'}`);
            loadTemplates();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update status');
        }
    };

    if (!user) return <div className="loading-screen">Loading...</div>;

    return (
        <div className="page-wrapper">
            <Navigation />
            <main className="container" style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
                <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1e293b' }}>System Configuration</h1>
                        <p style={{ color: '#64748b' }}>Manage global settings and templates</p>
                    </div>
                </header>

                {error && <div className="alert alert-error">{error}</div>}
                {success && <div className="alert alert-success">{success}</div>}

                {/* Templates Section */}
                <section className="config-section" style={{ background: 'white', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Theme Templates</h2>
                        <button
                            className="btn-primary"
                            onClick={() => setShowAddForm(!showAddForm)}
                            style={{ padding: '8px 16px', background: '#2563eb', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
                        >
                            {showAddForm ? 'Cancel' : '+ Add New Template'}
                        </button>
                        <button
                            className="btn-secondary"
                            onClick={() => setShowBulkUpload(!showBulkUpload)}
                            style={{ marginLeft: '10px', padding: '8px 16px', background: '#ffffff', color: '#64748b', borderRadius: '6px', border: '1px solid #cbd5e1', cursor: 'pointer' }}
                        >
                            {showBulkUpload ? 'Cancel Upload' : 'Bulk Upload'}
                        </button>
                    </div>

                    {showBulkUpload && (
                        <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '8px', marginBottom: '24px', border: '1px solid #e2e8f0' }}>
                            <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px', color: '#334155' }}>Bulk Upload Templates</h3>
                            <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '16px' }}>
                                Upload a file (.xlsx, .docx, .pdf, .csv) with the following columns: <br />
                                <strong>Template ID, Template Name, Description, Preview Image URL, Actual Template Web URL, Features (comma separated)</strong>
                            </p>
                            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                <input
                                    type="file"
                                    id="bulk-upload-input"
                                    accept=".xlsx,.xls,.doc,.docx,.pdf,.csv"
                                    style={{ fontSize: '14px' }}
                                />
                                <button
                                    onClick={async () => {
                                        const fileInput = document.getElementById('bulk-upload-input') as HTMLInputElement;
                                        if (!fileInput || !fileInput.files || !fileInput.files[0]) {
                                            setError('Please select a file to upload.');
                                            return;
                                        }

                                        const file = fileInput.files[0];
                                        setLoading(true);
                                        setError('');

                                        try {
                                            const res = await configurationAPI.uploadBulkTemplates(file);
                                            setSuccess(res.data.message);
                                            if (res.data.errors && res.data.errors.length > 0) {
                                                setError(`Some rows failed: ${res.data.errors.join(', ')}`);
                                            }
                                            setShowBulkUpload(false);
                                            loadTemplates();
                                        } catch (err: any) {
                                            setError(err.response?.data?.detail || 'Failed to upload templates');
                                        } finally {
                                            setLoading(false);
                                        }
                                    }}
                                    style={{ padding: '8px 16px', background: '#3b82f6', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
                                >
                                    Upload File
                                </button>
                            </div>
                        </div>
                    )}

                    {showAddForm && (
                        <form onSubmit={handleAddTemplate} style={{ background: '#f8fafc', padding: '20px', borderRadius: '8px', marginBottom: '24px', border: '1px solid #e2e8f0' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                                <div>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Template ID (unique-slug)</label>
                                    <input
                                        required
                                        type="text"
                                        placeholder="e.g. modern-corporate"
                                        value={newTemplate.id}
                                        onChange={e => setNewTemplate({ ...newTemplate, id: e.target.value })}
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Name</label>
                                    <input
                                        required
                                        type="text"
                                        placeholder="Display Name"
                                        value={newTemplate.name}
                                        onChange={e => setNewTemplate({ ...newTemplate, name: e.target.value })}
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
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Preview Image URL</label>
                                    <input
                                        type="text"
                                        placeholder="https://..."
                                        value={newTemplate.preview_url}
                                        onChange={e => setNewTemplate({ ...newTemplate, preview_url: e.target.value })}
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                    />
                                </div>
                                <div style={{ gridColumn: 'span 2' }}>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Actual Template Web URL</label>
                                    <input
                                        type="text"
                                        placeholder="https://example.com/template-demo"
                                        value={newTemplate.actual_web_url}
                                        onChange={e => setNewTemplate({ ...newTemplate, actual_web_url: e.target.value })}
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                    />
                                </div>
                                <div style={{ gridColumn: 'span 2' }}>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>Features (comma separated)</label>
                                    <input
                                        type="text"
                                        placeholder="Hero, Blog, Contact Form"
                                        value={newTemplate.features_input}
                                        onChange={e => setNewTemplate({ ...newTemplate, features_input: e.target.value })}
                                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                    />
                                </div>
                            </div>
                            <button type="submit" style={{ padding: '8px 24px', background: '#10b981', color: 'white', borderRadius: '6px', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
                                Save Template
                            </button>
                        </form>
                    )}

                    {/* Table View */}
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                            <thead>
                                <tr style={{ background: '#f8fafc', color: '#64748b', textAlign: 'left' }}>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0', width: '80px' }}>Preview</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>Template Info</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>Features</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>URLs</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0' }}>Status</th>
                                    <th style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0', textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr><td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>Loading templates...</td></tr>
                                ) : templates.length === 0 ? (
                                    <tr><td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>No templates found. Add one manually or bulk upload.</td></tr>
                                ) : (
                                    templates.map(t => (
                                        <tr key={t.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                            <td style={{ padding: '12px 16px' }}>
                                                <div style={{ width: '60px', height: '40px', background: '#f1f5f9', borderRadius: '4px', overflow: 'hidden' }}>
                                                    {t.preview_url ? (
                                                        <img
                                                            src={t.preview_url}
                                                            alt={t.name}
                                                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                                            onError={(e) => {
                                                                e.currentTarget.style.display = 'none';
                                                                const parent = e.currentTarget.parentElement;
                                                                if (parent) {
                                                                    const div = document.createElement('div');
                                                                    div.style.width = '100%';
                                                                    div.style.height = '100%';
                                                                    div.style.display = 'flex';
                                                                    div.style.alignItems = 'center';
                                                                    div.style.justifyContent = 'center';
                                                                    div.style.background = '#f1f5f9';
                                                                    div.style.color = '#94a3b8';
                                                                    div.style.fontSize = '10px';
                                                                    div.style.textAlign = 'center';
                                                                    div.textContent = 'Preview';
                                                                    parent.appendChild(div);
                                                                }
                                                            }}
                                                        />
                                                    ) : (
                                                        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px' }}>No Img</div>
                                                    )}
                                                </div>
                                            </td>
                                            <td style={{ padding: '12px 16px' }}>
                                                <div style={{ fontWeight: 600, color: '#1e293b' }}>{t.name}</div>
                                                <div style={{ fontSize: '12px', color: '#64748b' }}>ID: {t.id}</div>
                                                <div style={{ fontSize: '12px', color: '#64748b', maxWidth: '250px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.description}</div>
                                            </td>
                                            <td style={{ padding: '12px 16px' }}>
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxWidth: '200px' }}>
                                                    {t.features_json && t.features_json.slice(0, 3).map((f, i) => (
                                                        <span key={i} style={{ fontSize: '10px', background: '#e0f2fe', color: '#0369a1', padding: '2px 6px', borderRadius: '4px' }}>{f}</span>
                                                    ))}
                                                    {t.features_json && t.features_json.length > 3 && <span style={{ fontSize: '10px', color: '#64748b' }}>+{t.features_json.length - 3} more</span>}
                                                </div>
                                            </td>
                                            <td style={{ padding: '12px 16px' }}>
                                                {t.actual_web_url ? (
                                                    <a href={t.actual_web_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '13px', color: '#2563eb', textDecoration: 'none' }}>
                                                        View Demo ↗
                                                    </a>
                                                ) : <span style={{ color: '#94a3b8', fontSize: '13px' }}>-</span>}
                                            </td>
                                            <td style={{ padding: '12px 16px' }}>
                                                {t.is_published ? (
                                                    <span style={{ fontSize: '12px', background: '#dcfce7', color: '#166534', padding: '4px 8px', borderRadius: '12px', fontWeight: 600 }}>Published</span>
                                                ) : (
                                                    <span style={{ fontSize: '12px', background: '#f1f5f9', color: '#475569', padding: '4px 8px', borderRadius: '12px', fontWeight: 600 }}>Draft</span>
                                                )}
                                            </td>
                                            <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                                                <button
                                                    onClick={() => handleTogglePublish(t.id, t.is_published)}
                                                    style={{ padding: '6px 12px', background: 'transparent', border: t.is_published ? '1px solid #f97316' : '1px solid #10b981', color: t.is_published ? '#f97316' : '#10b981', borderRadius: '4px', cursor: 'pointer', marginRight: '8px', fontSize: '12px' }}
                                                >
                                                    {t.is_published ? 'Unpublish' : 'Publish'}
                                                </button>
                                                <button
                                                    onClick={() => handleDeleteTemplate(t.id)}
                                                    style={{ padding: '6px 12px', background: 'transparent', border: '1px solid #ef4444', color: '#ef4444', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                                                >
                                                    Delete
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>
            </main>
        </div>
    );
}
