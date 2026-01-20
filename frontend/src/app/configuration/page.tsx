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
    colors: any;
    features: string[];
    is_active: boolean;
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
    const [newTemplate, setNewTemplate] = useState({
        id: '',
        name: '',
        description: '',
        preview_url: '',
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
                    </div>

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

                    <div className="templates-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                        {loading ? <p>Loading templates...</p> : templates.map(t => (
                            <div key={t.id} className="template-card" style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
                                <div className="preview" style={{ height: '160px', background: '#f1f5f9', position: 'relative' }}>
                                    {t.preview_url ? (
                                        <img src={t.preview_url} alt={t.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                    ) : (
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8' }}>No Preview</div>
                                    )}
                                </div>
                                <div className="p-4" style={{ padding: '16px' }}>
                                    <h3 style={{ margin: '0 0 4px', fontSize: '16px', fontWeight: 600 }}>{t.name}</h3>
                                    <p style={{ margin: '0 0 12px', fontSize: '13px', color: '#64748b' }}>{t.description}</p>
                                    <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                                        {Object.entries(t.colors || {}).map(([c, v]: any) => (
                                            <span key={c} style={{ width: '20px', height: '20px', borderRadius: '50%', background: v, border: '1px solid rgba(0,0,0,0.1)' }} title={c}></span>
                                        ))}
                                    </div>
                                    <button
                                        onClick={() => handleDeleteTemplate(t.id)}
                                        style={{ width: '100%', padding: '8px', border: '1px solid #fee2e2', background: '#fef2f2', color: '#dc2626', borderRadius: '6px', cursor: 'pointer' }}
                                    >
                                        Delete
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            </main>
        </div>
    );
}
