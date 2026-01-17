'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { usersAPI } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import Navigation from '@/components/Navigation';

interface User {
    id: string;
    name: string;
    email: string;
    role: string;
    region?: string;
    date_of_joining?: string;
    is_active: boolean;
    is_archived?: boolean;
    archived_at?: string;
    created_at: string;
}

const REGIONS = [
    { value: 'INDIA', label: 'India', code: 'IN', flagUrl: 'https://flagcdn.com/w40/in.png' },
    { value: 'US', label: 'US', code: 'US', flagUrl: 'https://flagcdn.com/w40/us.png' },
    { value: 'PH', label: 'Philippines', code: 'PH', flagUrl: 'https://flagcdn.com/w40/ph.png' },
];

const FlagIcon = ({ region, size = 20 }: { region: string; size?: number }) => {
    const regionData = REGIONS.find(r => r.value === region);
    if (!regionData) return <span>{region}</span>;
    return (
        <img
            src={regionData.flagUrl}
            alt={`${regionData.label} flag`}
            width={size}
            height={Math.round(size * 0.75)}
            style={{ borderRadius: 2, objectFit: 'cover' }}
        />
    );
};

type ModalType = 'create' | 'edit' | 'delete' | 'deactivate' | null;

export default function UsersPage() {
    const router = useRouter();
    const [users, setUsers] = useState<User[]>([]);
    const [archivedUsers, setArchivedUsers] = useState<User[]>([]);
    const [showArchived, setShowArchived] = useState(false);
    const [loading, setLoading] = useState(true);
    const [currentUser, setCurrentUser] = useState<User | null>(null);
    const [modalType, setModalType] = useState<ModalType>(null);
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        role: 'CONSULTANT',
        region: 'INDIA',
        date_of_joining: '',
    });
    const [error, setError] = useState('');
    const [processing, setProcessing] = useState(false);

    const isAdmin = currentUser?.role === 'ADMIN';
    const isManager = currentUser?.role === 'MANAGER';

    useEffect(() => {
        const user = getCurrentUser();
        if (!user) {
            router.push('/login');
            return;
        }
        if (user.role !== 'ADMIN' && user.role !== 'MANAGER') {
            router.push('/dashboard');
            return;
        }
        setCurrentUser(user);
        loadUsers();
    }, [router]);

    const loadUsers = async () => {
        try {
            console.log('Loading users...');
            const [activeResponse, archivedResponse] = await Promise.all([
                usersAPI.list(),
                usersAPI.listArchived()
            ]);
            console.log('Active users:', activeResponse.data);
            console.log('Archived users:', archivedResponse.data);
            setUsers(activeResponse.data);
            setArchivedUsers(archivedResponse.data);
        } catch (error) {
            console.error('Failed to load users:', error);
        } finally {
            setLoading(false);
        }
    };

    const openCreateModal = () => {
        setFormData({ name: '', email: '', password: '', role: 'CONSULTANT', region: 'INDIA', date_of_joining: '' });
        setError('');
        setModalType('create');
    };

    const openEditModal = (user: User) => {
        setSelectedUser(user);
        setFormData({
            name: user.name,
            email: user.email,
            password: '',
            role: user.role,
            region: user.region || 'INDIA',
            date_of_joining: user.date_of_joining || ''
        });
        setError('');
        setModalType('edit');
    };

    const openDeactivateModal = (user: User) => {
        setSelectedUser(user);
        setError('');
        setModalType('deactivate');
    };

    const openDeleteModal = (user: User) => {
        setSelectedUser(user);
        setError('');
        setModalType('delete');
    };

    const closeModal = () => {
        setModalType(null);
        setSelectedUser(null);
        setError('');
    };

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setProcessing(true);

        try {
            const payload = {
                ...formData,
                date_of_joining: formData.date_of_joining || null
            };
            await usersAPI.create(payload);
            closeModal();
            loadUsers();
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            setError(typeof detail === 'object' ? JSON.stringify(detail) : detail || 'Failed to create user');
        } finally {
            setProcessing(false);
        }
    };

    const handleEdit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedUser) return;
        setError('');
        setProcessing(true);

        try {
            await usersAPI.update(selectedUser.id, {
                name: formData.name,
                email: formData.email,
                role: formData.role,
                region: formData.region,
                date_of_joining: formData.date_of_joining || null,
            });
            closeModal();
            loadUsers();
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            setError(typeof detail === 'object' ? JSON.stringify(detail) : detail || 'Failed to update user');
        } finally {
            setProcessing(false);
        }
    };

    const handleDeactivate = async () => {
        if (!selectedUser) return;
        setError('');
        setProcessing(true);

        try {
            await usersAPI.update(selectedUser.id, { is_active: !selectedUser.is_active });
            closeModal();
            loadUsers();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update user status');
        } finally {
            setProcessing(false);
        }
    };

    const handleDelete = async () => {
        if (!selectedUser) return;
        setError('');
        setProcessing(true);

        try {
            await usersAPI.archive(selectedUser.id);
            closeModal();
            loadUsers();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to archive user');
        } finally {
            setProcessing(false);
        }
    };

    const handleReactivate = async (user: User) => {
        setProcessing(true);
        try {
            await usersAPI.reactivate(user.id);
            loadUsers();
        } catch (err: any) {
            console.error('Failed to reactivate user:', err);
        } finally {
            setProcessing(false);
        }
    };

    const getRoleColor = (role: string) => {
        const colors: Record<string, string> = {
            ADMIN: 'var(--role-admin)',
            MANAGER: 'var(--role-manager)',
            CONSULTANT: 'var(--role-consultant)',
            PC: 'var(--role-pc)',
            BUILDER: 'var(--role-builder)',
            TESTER: 'var(--role-tester)',
        };
        return colors[role] || 'var(--text-muted)';
    };

    const canEditUser = (targetUser: User) => targetUser.id !== currentUser?.id && (isAdmin || isManager);
    const canDeactivateUser = (targetUser: User) => targetUser.id !== currentUser?.id && (isAdmin || isManager);
    const canDeleteUser = (targetUser: User) => targetUser.id !== currentUser?.id && isAdmin;

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner" />
                <p>Loading users...</p>
                <style jsx>{`
                    .loading-screen {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        gap: var(--space-md);
                    }
                    .loading-screen p {
                        color: var(--text-muted);
                    }
                `}</style>
            </div>
        );
    }

    if (!currentUser) return null;

    return (
        <div className="page-wrapper">
            <Navigation />
            <main className="users-page">
                <header className="page-header">
                    <div className="header-text">
                        <h1>User Management</h1>
                        <p>Create and manage users and their roles</p>
                    </div>
                    <button onClick={openCreateModal} className="btn-create">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="12" y1="5" x2="12" y2="19" />
                            <line x1="5" y1="12" x2="19" y2="12" />
                        </svg>
                        Create User
                    </button>
                </header>

                <div className="users-table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>User</th>
                                <th>Email</th>
                                <th>Role</th>
                                <th>Region</th>
                                <th>Joined</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((user, index) => (
                                <tr
                                    key={user.id}
                                    className={user.id === currentUser.id ? 'current-user' : ''}
                                    style={{ animationDelay: `${index * 30}ms` }}
                                >
                                    <td className="cell-user">
                                        <div className="user-avatar" style={{ background: getRoleColor(user.role) }}>
                                            {user.name.charAt(0).toUpperCase()}
                                        </div>
                                        <span className="user-name">
                                            {user.name}
                                            {user.id === currentUser.id && <span className="you-badge">You</span>}
                                        </span>
                                    </td>
                                    <td className="cell-email">{user.email}</td>
                                    <td>
                                        <span className="role-badge" style={{ color: getRoleColor(user.role) }}>
                                            {user.role}
                                        </span>
                                    </td>
                                    <td>
                                        <span className="region-badge">
                                            <FlagIcon region={user.region || ''} size={16} />
                                            {REGIONS.find(r => r.value === user.region)?.code || user.region || 'N/A'}
                                        </span>
                                    </td>
                                    <td className="cell-date">
                                        {user.date_of_joining
                                            ? new Date(user.date_of_joining).toLocaleDateString()
                                            : <span className="not-set">Not set</span>
                                        }
                                    </td>
                                    <td>
                                        <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                                            {user.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="cell-actions">
                                        {canEditUser(user) && (
                                            <button
                                                onClick={() => openEditModal(user)}
                                                className="btn-icon btn-edit"
                                                title="Edit"
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                                                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                                                </svg>
                                            </button>
                                        )}
                                        {canDeactivateUser(user) && (
                                            <button
                                                onClick={() => openDeactivateModal(user)}
                                                className={`btn-icon ${user.is_active ? 'btn-deactivate' : 'btn-activate'}`}
                                                title={user.is_active ? 'Deactivate' : 'Activate'}
                                            >
                                                {user.is_active ? (
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                        <circle cx="12" cy="12" r="10" />
                                                        <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
                                                    </svg>
                                                ) : (
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                                                        <polyline points="22 4 12 14.01 9 11.01" />
                                                    </svg>
                                                )}
                                            </button>
                                        )}
                                        {canDeleteUser(user) && (
                                            <button
                                                onClick={() => openDeleteModal(user)}
                                                className="btn-icon btn-delete"
                                                title="Delete"
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                    <polyline points="3 6 5 6 21 6" />
                                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                                                    <line x1="10" y1="11" x2="10" y2="17" />
                                                    <line x1="14" y1="11" x2="14" y2="17" />
                                                </svg>
                                            </button>
                                        )}
                                        {user.id === currentUser.id && (
                                            <span className="no-actions">—</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Archived Users Section */}
                {isAdmin && archivedUsers.length > 0 && (
                    <section className="archived-section">
                        <button
                            className="archived-header"
                            onClick={() => setShowArchived(!showArchived)}
                            aria-expanded={showArchived}
                        >
                            <div className="archived-title">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="21 8 21 21 3 21 3 8" />
                                    <rect x="1" y="3" width="22" height="5" />
                                    <line x1="10" y1="12" x2="14" y2="12" />
                                </svg>
                                <span>Archived Users ({archivedUsers.length})</span>
                            </div>
                            <svg
                                className={`chevron ${showArchived ? 'open' : ''}`}
                                width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                            >
                                <polyline points="6 9 12 15 18 9" />
                            </svg>
                        </button>

                        {showArchived && (
                            <div className="archived-content">
                                <table className="archived-table">
                                    <thead>
                                        <tr>
                                            <th>User</th>
                                            <th>Email</th>
                                            <th>Role</th>
                                            <th>Archived On</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {archivedUsers.map((user) => (
                                            <tr key={user.id}>
                                                <td className="cell-user">
                                                    <div className="user-avatar archived" style={{ background: 'var(--text-hint)' }}>
                                                        {user.name.charAt(0).toUpperCase()}
                                                    </div>
                                                    <span className="user-name">{user.name}</span>
                                                </td>
                                                <td className="cell-email">{user.email}</td>
                                                <td>
                                                    <span className="role-badge" style={{ color: 'var(--text-muted)' }}>
                                                        {user.role}
                                                    </span>
                                                </td>
                                                <td className="cell-date">
                                                    {user.archived_at ? new Date(user.archived_at).toLocaleDateString() : 'N/A'}
                                                </td>
                                                <td>
                                                    <button
                                                        onClick={() => handleReactivate(user)}
                                                        className="btn-reactivate"
                                                        disabled={processing}
                                                        title="Reactivate user"
                                                    >
                                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                                                            <path d="M3 3v5h5" />
                                                            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
                                                            <path d="M16 21h5v-5" />
                                                        </svg>
                                                        Reactivate
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>
                )}

                <section className="permissions-info">
                    <h3>Role Permissions</h3>
                    <div className="permissions-grid">
                        {[
                            { role: 'ADMIN', desc: 'Full access - Create, edit, deactivate, and archive users' },
                            { role: 'MANAGER', desc: 'Create, edit, and deactivate users (no archive)' },
                            { role: 'CONSULTANT', desc: 'Create projects, update onboarding, view status' },
                            { role: 'PC', desc: 'Task assignment access, manage assignment stage' },
                            { role: 'BUILDER', desc: 'Build stage access only' },
                            { role: 'TESTER', desc: 'Test stage access only' },
                        ].map((item) => (
                            <div key={item.role} className="permission-item">
                                <span className="role-badge" style={{ color: getRoleColor(item.role) }}>{item.role}</span>
                                <span className="role-desc">{item.desc}</span>
                            </div>
                        ))}
                    </div>
                </section>
            </main>

            {/* Modals */}
            {(modalType === 'create' || modalType === 'edit') && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <h2>{modalType === 'create' ? 'Create New User' : 'Edit User'}</h2>
                        <form onSubmit={modalType === 'create' ? handleCreate : handleEdit}>
                            <div className="form-group">
                                <label>Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    required
                                    disabled={processing}
                                    placeholder="Full name"
                                />
                            </div>
                            <div className="form-group">
                                <label>Email</label>
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required
                                    disabled={processing}
                                    placeholder="user@example.com"
                                />
                            </div>
                            {modalType === 'create' && (
                                <div className="form-group">
                                    <label>Password</label>
                                    <input
                                        type="password"
                                        value={formData.password}
                                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                        required
                                        disabled={processing}
                                        placeholder="Minimum 6 characters"
                                        minLength={6}
                                    />
                                </div>
                            )}
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Role</label>
                                    <select
                                        value={formData.role}
                                        onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                                        disabled={processing}
                                    >
                                        <option value="ADMIN">Admin</option>
                                        <option value="MANAGER">Manager</option>
                                        <option value="CONSULTANT">Consultant</option>
                                        <option value="PC">PC</option>
                                        <option value="BUILDER">Builder</option>
                                        <option value="TESTER">Tester</option>
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Region</label>
                                    <select
                                        value={formData.region}
                                        onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                                        disabled={processing}
                                    >
                                        {REGIONS.map((region) => (
                                            <option key={region.value} value={region.value}>
                                                {region.code} - {region.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Date of Joining</label>
                                    <input
                                        type="date"
                                        value={formData.date_of_joining}
                                        onChange={(e) => setFormData({ ...formData, date_of_joining: e.target.value })}
                                        disabled={processing}
                                    />
                                    <span className="form-hint">Used for leave entitlement calculations</span>
                                </div>
                            </div>
                            {error && <div className="error-message">{error}</div>}
                            <div className="modal-actions">
                                <button type="button" onClick={closeModal} className="btn-cancel">Cancel</button>
                                <button type="submit" disabled={processing} className="btn-submit">
                                    {processing ? 'Saving...' : modalType === 'create' ? 'Create' : 'Save'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {modalType === 'deactivate' && selectedUser && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal modal-sm" onClick={(e) => e.stopPropagation()}>
                        <h2>{selectedUser.is_active ? 'Deactivate' : 'Activate'} User</h2>
                        <p className="modal-text">
                            Are you sure you want to {selectedUser.is_active ? 'deactivate' : 'activate'}{' '}
                            <strong>{selectedUser.name}</strong>?
                        </p>
                        {error && <div className="error-message">{error}</div>}
                        <div className="modal-actions">
                            <button onClick={closeModal} className="btn-cancel">Cancel</button>
                            <button
                                onClick={handleDeactivate}
                                disabled={processing}
                                className={selectedUser.is_active ? 'btn-warning' : 'btn-success'}
                            >
                                {processing ? 'Processing...' : selectedUser.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {modalType === 'delete' && selectedUser && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal modal-sm" onClick={(e) => e.stopPropagation()}>
                        <h2>Archive User</h2>
                        <p className="modal-text">
                            Are you sure you want to archive <strong>{selectedUser.name}</strong>?
                        </p>
                        <p className="modal-info">The user will be moved to the Archived Users section and can be reactivated later.</p>
                        {error && <div className="error-message">{error}</div>}
                        <div className="modal-actions">
                            <button onClick={closeModal} className="btn-cancel">Cancel</button>
                            <button onClick={handleDelete} disabled={processing} className="btn-danger">
                                {processing ? 'Archiving...' : 'Archive'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <style jsx>{`
                .users-page {
                    max-width: 1600px;
                    margin: 0 auto;
                    padding: var(--space-xl) var(--space-lg);
                }
                
                .page-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--space-xl);
                }
                
                .header-text h1 {
                    margin-bottom: var(--space-xs);
                }
                
                .header-text p {
                    color: var(--text-muted);
                }
                
                .btn-create {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    padding: 12px var(--space-lg);
                    background: linear-gradient(135deg, var(--color-success) 0%, #059669 100%);
                    color: white;
                    border-radius: var(--radius-md);
                    font-weight: 600;
                    font-size: 14px;
                }
                
                .btn-create:hover {
                    transform: translateY(-1px);
                }
                
                .users-table-container {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    overflow: hidden;
                    margin-bottom: var(--space-xl);
                }
                
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                
                th {
                    text-align: left;
                    padding: var(--space-md) var(--space-lg);
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    color: var(--text-muted);
                    background: var(--bg-tertiary);
                    border-bottom: 1px solid var(--border-light);
                    white-space: nowrap;
                }
                
                td {
                    padding: var(--space-md) var(--space-lg);
                    color: var(--text-secondary);
                    border-bottom: 1px solid var(--border-light);
                    vertical-align: middle;
                    white-space: nowrap;
                    height: 60px;
                }
                
                tbody tr {
                    animation: fadeIn 0.3s ease forwards;
                    opacity: 0;
                    height: 60px;
                }
                
                tbody tr:hover {
                    background: var(--bg-secondary);
                }
                
                tbody tr.current-user {
                    background: var(--color-warning-bg);
                }
                
                .cell-user {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                }
                
                .user-avatar {
                    width: 36px;
                    height: 36px;
                    border-radius: var(--radius-full);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: 600;
                    font-size: 14px;
                }
                
                .user-name {
                    font-weight: 600;
                    color: var(--text-primary);
                    display: inline-flex;
                    align-items: center;
                    gap: var(--space-sm);
                }
                
                .you-badge {
                    font-size: 10px;
                    padding: 2px 6px;
                    background: var(--color-warning);
                    color: white;
                    border-radius: var(--radius-full);
                    font-weight: 600;
                }
                
                .cell-email {
                    color: var(--text-muted);
                    max-width: 280px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                
                .cell-date {
                    font-size: 13px;
                    color: var(--text-muted);
                }
                
                .not-set {
                    color: var(--text-muted);
                    font-style: italic;
                    font-size: 12px;
                }
                
                .form-hint {
                    display: block;
                    font-size: 12px;
                    color: var(--text-muted);
                    margin-top: 4px;
                }
                
                .role-badge {
                    font-size: 12px;
                    font-weight: 600;
                }
                
                .region-badge {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    font-size: 13px;
                    color: var(--text-secondary);
                }
                
                .status-badge {
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: var(--radius-full);
                    font-size: 11px;
                    font-weight: 600;
                }
                
                .status-badge.active {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                }
                
                .status-badge.inactive {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                }
                
                .cell-actions {
                    display: flex;
                    gap: 8px;
                    align-items: center;
                    justify-content: flex-start;
                    height: 100%;
                }
                
                .btn-icon {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 32px;
                    height: 32px;
                    border-radius: 6px;
                    transition: all 0.2s ease;
                    cursor: pointer;
                    border: none;
                    outline: none;
                }
                
                .btn-icon svg {
                    flex-shrink: 0;
                    width: 16px;
                    height: 16px;
                }
                
                .btn-edit {
                    background: var(--color-info-bg);
                    color: var(--color-info);
                    border: 1px solid var(--color-info-border);
                }
                
                .btn-edit:hover {
                    background: var(--color-info);
                    color: white;
                    transform: scale(1.05);
                }
                
                .btn-edit:focus-visible {
                    outline: 2px solid var(--color-info);
                    outline-offset: 2px;
                }
                
                .btn-deactivate {
                    background: var(--color-warning-bg);
                    color: var(--color-warning);
                    border: 1px solid var(--color-warning-border);
                }
                
                .btn-deactivate:hover {
                    background: var(--color-warning);
                    color: white;
                    transform: scale(1.05);
                }
                
                .btn-deactivate:focus-visible {
                    outline: 2px solid var(--color-warning);
                    outline-offset: 2px;
                }
                
                .btn-activate {
                    background: var(--color-success-bg);
                    color: var(--color-success);
                    border: 1px solid var(--color-success-border);
                }
                
                .btn-activate:hover {
                    background: var(--color-success);
                    color: white;
                    transform: scale(1.05);
                }
                
                .btn-activate:focus-visible {
                    outline: 2px solid var(--color-success);
                    outline-offset: 2px;
                }
                
                .btn-delete {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                    border: 1px solid var(--color-error-border);
                }
                
                .btn-delete:hover {
                    background: var(--color-error);
                    color: white;
                    transform: scale(1.05);
                }
                
                .btn-delete:focus-visible {
                    outline: 2px solid var(--color-error);
                    outline-offset: 2px;
                }
                
                .no-actions {
                    color: var(--text-hint);
                }
                
                .permissions-info {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    padding: var(--space-lg);
                }
                
                .permissions-info h3 {
                    font-size: 14px;
                    color: var(--text-secondary);
                    margin-bottom: var(--space-md);
                }
                
                .permissions-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: var(--space-sm);
                }
                
                .permission-item {
                    display: flex;
                    align-items: center;
                    gap: var(--space-md);
                    padding: var(--space-sm) var(--space-md);
                    background: var(--bg-secondary);
                    border-radius: var(--radius-md);
                    border: 1px solid var(--border-light);
                }
                
                .role-desc {
                    font-size: 12px;
                    color: var(--text-muted);
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
                    animation: fadeIn 0.2s ease;
                }
                
                .modal {
                    background: var(--bg-primary);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-xl);
                    padding: var(--space-xl);
                    width: 100%;
                    max-width: 480px;
                    animation: slideIn 0.2s ease;
                    box-shadow: var(--shadow-lg);
                }
                
                .modal-sm {
                    max-width: 400px;
                }
                
                .modal h2 {
                    font-size: 18px;
                    margin-bottom: var(--space-lg);
                }
                
                .modal-text {
                    color: var(--text-secondary);
                    margin-bottom: var(--space-sm);
                }
                
                .modal-warning {
                    color: var(--color-error);
                    font-size: 13px;
                    margin-bottom: var(--space-md);
                }
                
                .modal-info {
                    color: var(--text-muted);
                    font-size: 13px;
                    margin-bottom: var(--space-md);
                    background: var(--bg-tertiary);
                    padding: var(--space-sm) var(--space-md);
                    border-radius: var(--radius-md);
                    border-left: 3px solid var(--color-info);
                }
                
                .form-group {
                    margin-bottom: var(--space-md);
                }
                
                .form-row {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: var(--space-md);
                }
                
                .form-row .form-group {
                    margin-bottom: 0;
                }
                
                .form-group label {
                    display: block;
                    font-size: 13px;
                    font-weight: 600;
                    color: var(--text-secondary);
                    margin-bottom: var(--space-sm);
                }
                
                .form-group input,
                .form-group select {
                    width: 100%;
                    padding: 12px var(--space-md);
                    background: var(--bg-input);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    color: var(--text-primary);
                    font-size: 14px;
                }
                
                .form-group input:focus,
                .form-group select:focus {
                    outline: none;
                    border-color: var(--accent-primary);
                }
                
                .form-group select option {
                    background: var(--bg-primary);
                    color: var(--text-primary);
                }
                
                .form-group input:focus,
                .form-group select:focus {
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
                }
                
                .error-message {
                    background: var(--color-error-bg);
                    color: var(--color-error);
                    padding: var(--space-md);
                    border-radius: var(--radius-md);
                    margin-bottom: var(--space-md);
                    font-size: 13px;
                    font-weight: 500;
                    border: 1px solid var(--color-error-border);
                }
                
                .modal-actions {
                    display: flex;
                    gap: var(--space-md);
                    justify-content: flex-end;
                    margin-top: var(--space-lg);
                }
                
                .btn-cancel {
                    padding: 10px var(--space-lg);
                    background: var(--bg-input);
                    color: var(--text-secondary);
                    border: 1px solid var(--border-medium);
                    border-radius: var(--radius-md);
                    font-size: 13px;
                }
                
                .btn-cancel:hover {
                    background: var(--bg-card-hover);
                }
                
                .btn-submit {
                    padding: 10px var(--space-lg);
                    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
                    color: white;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 600;
                }
                
                .btn-success {
                    padding: 10px var(--space-lg);
                    background: var(--color-success);
                    color: white;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 600;
                }
                
                .btn-warning {
                    padding: 10px var(--space-lg);
                    background: var(--color-warning);
                    color: white;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 600;
                }
                
                .btn-danger {
                    padding: 10px var(--space-lg);
                    background: var(--color-error);
                    color: white;
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 600;
                }
                
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                /* Archived Section Styles */
                .archived-section {
                    background: var(--bg-card);
                    border: 1px solid var(--border-light);
                    border-radius: var(--radius-lg);
                    margin-bottom: var(--space-xl);
                    overflow: hidden;
                }
                
                .archived-header {
                    width: 100%;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: var(--space-md) var(--space-lg);
                    background: var(--bg-tertiary);
                    border: none;
                    cursor: pointer;
                    transition: background 0.2s ease;
                }
                
                .archived-header:hover {
                    background: var(--bg-secondary);
                }
                
                .archived-title {
                    display: flex;
                    align-items: center;
                    gap: var(--space-sm);
                    font-weight: 600;
                    color: var(--text-secondary);
                }
                
                .archived-title svg {
                    color: var(--text-muted);
                }
                
                .chevron {
                    transition: transform 0.2s ease;
                    color: var(--text-muted);
                }
                
                .chevron.open {
                    transform: rotate(180deg);
                }
                
                .archived-content {
                    border-top: 1px solid var(--border-light);
                    animation: fadeIn 0.2s ease;
                }
                
                .archived-table {
                    width: 100%;
                    border-collapse: collapse;
                    opacity: 0.85;
                }
                
                .archived-table th {
                    text-align: left;
                    padding: var(--space-sm) var(--space-lg);
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    color: var(--text-hint);
                    background: var(--bg-secondary);
                    border-bottom: 1px solid var(--border-light);
                }
                
                .archived-table td {
                    padding: var(--space-sm) var(--space-lg);
                    color: var(--text-muted);
                    border-bottom: 1px solid var(--border-light);
                    vertical-align: middle;
                }
                
                .archived-table tbody tr:hover {
                    background: var(--bg-secondary);
                }
                
                .archived-table .user-avatar.archived {
                    opacity: 0.6;
                }
                
                .archived-table .user-name {
                    color: var(--text-muted);
                }
                
                .btn-reactivate {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 8px 14px;
                    background: var(--color-success-bg);
                    color: var(--color-success);
                    border: 1px solid var(--color-success-border);
                    border-radius: var(--radius-md);
                    font-size: 13px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .btn-reactivate:hover:not(:disabled) {
                    background: var(--color-success);
                    color: white;
                }
                
                .btn-reactivate:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
            `}</style>
        </div>
    );
}
