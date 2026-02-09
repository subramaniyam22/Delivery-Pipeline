'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';

interface PendingRequirement {
  requirement_type: string;
  description: string;
  status: string;
}

interface ProjectClientInfo {
  project_id: string;
  project_title: string;
  client_name: string;
  client_company: string | null;
  client_primary_contact: string | null;
  client_emails: string[];
  pending_requirements: PendingRequirement[];
  last_reminder_sent: string | null;
}

interface ReminderLog {
  id: string;
  reminder_type: string;
  sent_to: string[];
  subject: string;
  message: string | null;
  sent_at: string;
  status: string;
}

export default function ClientManagementPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<ProjectClientInfo[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectClientInfo | null>(null);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [showReminderModal, setShowReminderModal] = useState(false);
  const [reminderHistory, setReminderHistory] = useState<ReminderLog[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const [emailForm, setEmailForm] = useState({
    client_emails: [''],
    client_primary_contact: '',
    client_company: ''
  });

  const [reminderForm, setReminderForm] = useState({
    reminder_type: 'requirements_pending',
    subject: '',
    message: ''
  });

  useEffect(() => {
    const userData = localStorage.getItem('user');
    const token = localStorage.getItem('access_token');
    
    if (!userData || !token) {
      router.push('/login');
      return;
    }
    
    const parsed = JSON.parse(userData);
    const allowedRoles = ['ADMIN', 'MANAGER', 'CONSULTANT', 'PC'];
    if (!allowedRoles.includes(parsed.role)) {
      router.push('/dashboard');
      return;
    }
    
    setUser(parsed);
    loadProjects();
  }, [router]);

  const getApiUrl = () => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8000';
      }
      return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    }
    return 'http://localhost:8000';
  };

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const loadProjects = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${getApiUrl()}/client-management/projects`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        setProjects(await response.json());
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadReminderHistory = async (projectId: string) => {
    try {
      const response = await fetch(`${getApiUrl()}/client-management/reminders/${projectId}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        setReminderHistory(await response.json());
      }
    } catch (error) {
      console.error('Failed to load reminders:', error);
    }
  };

  const openEmailModal = (project: ProjectClientInfo) => {
    setSelectedProject(project);
    setEmailForm({
      client_emails: project.client_emails.length > 0 ? project.client_emails : [''],
      client_primary_contact: project.client_primary_contact || '',
      client_company: project.client_company || ''
    });
    setShowEmailModal(true);
  };

  const openReminderModal = (project: ProjectClientInfo) => {
    setSelectedProject(project);
    loadReminderHistory(project.project_id);
    
    // Auto-generate subject based on pending requirements
    const pendingTypes = project.pending_requirements.map(r => r.requirement_type).join(', ');
    setReminderForm({
      reminder_type: 'requirements_pending',
      subject: `Action Required: ${pendingTypes || 'Project Update'} - ${project.project_title}`,
      message: `Dear ${project.client_primary_contact || 'Client'},\n\nWe wanted to follow up on the pending items for your project "${project.project_title}".\n\nPending Items:\n${project.pending_requirements.map(r => `- ${r.requirement_type}: ${r.description}`).join('\n')}\n\nPlease provide the above at your earliest convenience to keep the project on track.\n\nThank you for your cooperation.`
    });
    setShowReminderModal(true);
  };

  const handleEmailUpdate = async () => {
    if (!selectedProject) return;
    setSubmitting(true);
    
    try {
      const response = await fetch(
        `${getApiUrl()}/client-management/projects/${selectedProject.project_id}/client-emails`,
        {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            client_emails: emailForm.client_emails.filter(e => e.trim()),
            client_primary_contact: emailForm.client_primary_contact || null,
            client_company: emailForm.client_company || null
          })
        }
      );
      
      if (response.ok) {
        setShowEmailModal(false);
        loadProjects();
        alert('Client information updated successfully!');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to update client information');
      }
    } catch (error) {
      console.error('Error updating emails:', error);
      alert('Failed to update client information');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSendReminder = async () => {
    if (!selectedProject) return;
    if (!selectedProject.client_emails.length) {
      alert('Please add client email addresses first');
      return;
    }
    
    setSubmitting(true);
    
    try {
      const response = await fetch(`${getApiUrl()}/client-management/send-reminder`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          project_id: selectedProject.project_id,
          reminder_type: reminderForm.reminder_type,
          subject: reminderForm.subject,
          message: reminderForm.message
        })
      });
      
      if (response.ok) {
        loadReminderHistory(selectedProject.project_id);
        alert('Reminder sent successfully!');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to send reminder');
      }
    } catch (error) {
      console.error('Error sending reminder:', error);
      alert('Failed to send reminder');
    } finally {
      setSubmitting(false);
    }
  };

  const addEmailField = () => {
    setEmailForm({ ...emailForm, client_emails: [...emailForm.client_emails, ''] });
  };

  const removeEmailField = (index: number) => {
    const newEmails = emailForm.client_emails.filter((_, i) => i !== index);
    setEmailForm({ ...emailForm, client_emails: newEmails.length ? newEmails : [''] });
  };

  const updateEmailField = (index: number, value: string) => {
    const newEmails = [...emailForm.client_emails];
    newEmails[index] = value;
    setEmailForm({ ...emailForm, client_emails: newEmails });
  };

  const buildClientSummary = (project: ProjectClientInfo) => {
    const pendingCount = project.pending_requirements.length;
    if (pendingCount > 0) {
      return `Waiting on ${pendingCount} requirement${pendingCount === 1 ? '' : 's'} from client.`;
    }
    if (project.last_reminder_sent) {
      return `Last reminder sent on ${new Date(project.last_reminder_sent).toLocaleDateString()}.`;
    }
    return 'Client details are up to date. No pending items.';
  };

  if (loading || !user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div className="spinner" />
      </div>
    );
  }

  return (
    <RequireCapability cap="view_clients">
    <div className="page-container">
      <Navigation />
      
      <main className="main-content">
        <div className="page-header">
          <PageHeader
            title="Client Management"
            purpose="Track client contacts, project context, and communication status."
            variant="page"
          />
        </div>

        <div className="table-wrapper">
          <table className="client-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Client</th>
                <th>Summary</th>
                <th>Contacts</th>
                <th>Emails</th>
                <th>Pending</th>
                <th>Last Reminder</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr key={project.project_id}>
                  <td>
                    <div className="cell-title">{project.project_title}</div>
                    <div className="mono">{project.project_id}</div>
                  </td>
                  <td>
                    <div className="cell-title">{project.client_name}</div>
                    <div className="subtle">{project.client_company || '—'}</div>
                  </td>
                  <td className="summary-cell">{buildClientSummary(project)}</td>
                  <td>
                    <div className="subtle">{project.client_primary_contact || '—'}</div>
                  </td>
                  <td>
                    <div className="subtle">
                      {project.client_emails.length > 0 ? project.client_emails.join(', ') : 'Not configured'}
                    </div>
                  </td>
                  <td>
                    {project.pending_requirements.length > 0 ? (
                      <span className="pending-pill">
                        {project.pending_requirements.length} pending
                      </span>
                    ) : (
                      <span className="status-pill">Clear</span>
                    )}
                  </td>
                  <td>
                    <span className="subtle">
                      {project.last_reminder_sent
                        ? new Date(project.last_reminder_sent).toLocaleDateString()
                        : '—'}
                    </span>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button className="btn-secondary" onClick={() => openEmailModal(project)}>
                        Edit Contacts
                      </button>
                      <button 
                        className="btn-primary" 
                        onClick={() => openReminderModal(project)}
                        disabled={project.client_emails.length === 0}
                      >
                        Send Reminder
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {projects.length === 0 && (
                <tr>
                  <td colSpan={8} className="empty-row">
                    No projects assigned to manage client communications.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </main>

      {/* Email Modal */}
      {showEmailModal && selectedProject && (
        <div className="modal-overlay" onClick={() => setShowEmailModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📧 Edit Client Contacts</h2>
              <button className="close-btn" onClick={() => setShowEmailModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <p className="project-name">{selectedProject.project_title}</p>
              
              <div className="form-group">
                <label>Company Name</label>
                <input 
                  type="text" 
                  value={emailForm.client_company}
                  onChange={(e) => setEmailForm({...emailForm, client_company: e.target.value})}
                  placeholder="Enter company name"
                />
              </div>
              
              <div className="form-group">
                <label>Primary Contact Name</label>
                <input 
                  type="text" 
                  value={emailForm.client_primary_contact}
                  onChange={(e) => setEmailForm({...emailForm, client_primary_contact: e.target.value})}
                  placeholder="Enter contact name"
                />
              </div>
              
              <div className="form-group">
                <label>Email Addresses</label>
                {emailForm.client_emails.map((email, idx) => (
                  <div key={idx} className="email-row">
                    <input 
                      type="email" 
                      value={email}
                      onChange={(e) => updateEmailField(idx, e.target.value)}
                      placeholder="client@example.com"
                    />
                    {emailForm.client_emails.length > 1 && (
                      <button className="btn-remove" onClick={() => removeEmailField(idx)}>×</button>
                    )}
                  </div>
                ))}
                <button className="btn-add" onClick={addEmailField}>+ Add Another Email</button>
              </div>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowEmailModal(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleEmailUpdate} disabled={submitting}>
                {submitting ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reminder Modal */}
      {showReminderModal && selectedProject && (
        <div className="modal-overlay" onClick={() => setShowReminderModal(false)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📤 Send Client Reminder</h2>
              <button className="close-btn" onClick={() => setShowReminderModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <p className="project-name">{selectedProject.project_title}</p>
              <p className="recipients">To: {selectedProject.client_emails.join(', ')}</p>
              
              <div className="form-group">
                <label>Reminder Type</label>
                <select 
                  value={reminderForm.reminder_type}
                  onChange={(e) => setReminderForm({...reminderForm, reminder_type: e.target.value})}
                >
                  <option value="requirements_pending">Requirements Pending</option>
                  <option value="document_needed">Document Needed</option>
                  <option value="approval_required">Approval Required</option>
                  <option value="general">General Follow-up</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>Subject</label>
                <input 
                  type="text" 
                  value={reminderForm.subject}
                  onChange={(e) => setReminderForm({...reminderForm, subject: e.target.value})}
                />
              </div>
              
              <div className="form-group">
                <label>Message</label>
                <textarea 
                  value={reminderForm.message}
                  onChange={(e) => setReminderForm({...reminderForm, message: e.target.value})}
                  rows={8}
                />
              </div>

              {reminderHistory.length > 0 && (
                <div className="reminder-history">
                  <h4>📜 Previous Reminders</h4>
                  <ul>
                    {reminderHistory.slice(0, 3).map((r) => (
                      <li key={r.id}>
                        <span className="date">{new Date(r.sent_at).toLocaleDateString()}</span>
                        <span className="subject">{r.subject}</span>
                        <span className={`status ${r.status.toLowerCase()}`}>{r.status}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setShowReminderModal(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleSendReminder} disabled={submitting}>
                {submitting ? 'Sending...' : '📤 Send Reminder'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .page-container { min-height: 100vh; background: #f8fafc; }
        .main-content { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        
        .page-header { margin-bottom: 2rem; }
        .page-header h1 { font-size: 1.75rem; color: #1e293b; margin-bottom: 0.25rem; }
        .page-header p { color: #64748b; }
        
        .table-wrapper { background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }
        .client-table { width: 100%; border-collapse: collapse; }
        .client-table th { text-align: left; font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase; color: #64748b; background: #f8fafc; padding: 0.75rem 1rem; border-bottom: 1px solid #e2e8f0; }
        .client-table td { padding: 0.85rem 1rem; border-bottom: 1px solid #e2e8f0; font-size: 0.9rem; color: #1e293b; vertical-align: top; }
        .client-table tr:last-child td { border-bottom: none; }
        .cell-title { font-weight: 600; }
        .summary-cell { max-width: 260px; color: #475569; }
        .subtle { color: #64748b; font-size: 0.85rem; }
        .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 0.8rem; color: #94a3b8; }
        .pending-pill { background: #fef3c7; color: #92400e; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
        .status-pill { background: #dcfce7; color: #166534; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
        .row-actions { display: flex; gap: 0.5rem; }
        .empty-row { text-align: center; color: #94a3b8; font-size: 0.9rem; padding: 2rem; }
        .btn-primary { flex: 1; padding: 0.75rem; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; }
        .btn-primary:hover { background: #1d4ed8; }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-secondary { flex: 1; padding: 0.75rem; background: #f1f5f9; color: #1e293b; border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer; font-weight: 500; }
        .btn-secondary:hover { background: #e2e8f0; }
        
        .empty-state { text-align: center; padding: 4rem; background: white; border-radius: 12px; }
        .empty-icon { font-size: 3rem; }
        .empty-state h3 { margin: 1rem 0 0.5rem; color: #1e293b; }
        .empty-state p { color: #64748b; }
        
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .modal { background: white; border-radius: 16px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; }
        .modal-lg { max-width: 650px; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1.25rem 1.5rem; border-bottom: 1px solid #e2e8f0; }
        .modal-header h2 { font-size: 1.25rem; color: #1e293b; margin: 0; }
        .close-btn { background: none; border: none; font-size: 1.5rem; color: #64748b; cursor: pointer; }
        .modal-body { padding: 1.5rem; }
        .project-name { font-weight: 600; color: #1e293b; margin-bottom: 0.5rem; }
        .recipients { font-size: 0.85rem; color: #64748b; margin-bottom: 1rem; }
        
        .form-group { margin-bottom: 1.25rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; color: #1e293b; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 1rem; box-sizing: border-box; }
        .form-group textarea { resize: vertical; font-family: inherit; }
        
        .email-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
        .email-row input { flex: 1; }
        .btn-remove { width: 36px; background: #fee2e2; color: #991b1b; border: none; border-radius: 8px; cursor: pointer; }
        .btn-add { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 0.9rem; padding: 0.5rem 0; }
        
        .reminder-history { background: #f8fafc; border-radius: 8px; padding: 1rem; margin-top: 1rem; }
        .reminder-history h4 { font-size: 0.9rem; color: #1e293b; margin: 0 0 0.75rem; }
        .reminder-history ul { list-style: none; padding: 0; margin: 0; }
        .reminder-history li { display: flex; align-items: center; gap: 1rem; padding: 0.5rem 0; border-bottom: 1px solid #e2e8f0; font-size: 0.85rem; }
        .reminder-history li:last-child { border-bottom: none; }
        .reminder-history .date { color: #64748b; min-width: 80px; }
        .reminder-history .subject { flex: 1; color: #1e293b; }
        .reminder-history .status { padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }
        .reminder-history .status.sent { background: #dcfce7; color: #166534; }
        .reminder-history .status.failed { background: #fee2e2; color: #991b1b; }
        
        .modal-actions { display: flex; gap: 1rem; padding: 1rem 1.5rem; border-top: 1px solid #e2e8f0; }
        .modal-actions .btn-primary, .modal-actions .btn-secondary { flex: 1; }
        
        @media (max-width: 768px) {
          .projects-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
    </RequireCapability>
  );
}
