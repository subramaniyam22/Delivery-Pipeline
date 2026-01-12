'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navigation from '@/components/Navigation';

interface Leave {
  id: string;
  user_id: string;
  user_name: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  status: string;
  reason: string | null;
  partial_day: boolean;
  hours_off: number | null;
  approved_by_name: string | null;
  created_at: string;
}

interface Holiday {
  id: string;
  name: string;
  date: string;
  year: number;
  region?: string;
  is_optional?: boolean;
  is_mandatory?: boolean;
  description?: string;
}

interface LeaveBalance {
  id: string;
  leave_type: string;
  year: number;
  entitled_days: number;
  used_days: number;
  pending_days: number;
  carried_forward: number;
  adjusted_days: number;
  available_days: number;
}

interface LeavePolicy {
  id: string;
  leave_type: string;
  role: string | null;
  region: string | null;
  annual_days: number;
  can_carry_forward: boolean;
  max_carry_forward_days: number;
  requires_approval: boolean;
  min_notice_days: number;
}

interface Meeting {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  is_all_day: boolean;
  is_busy: boolean;
  category: string | null;
  duration_hours: number;
}

const LEAVE_TYPES = [
  { value: 'CASUAL', label: '🏖️ Casual Leave', color: '#4CAF50' },
  { value: 'SICK', label: '🤒 Sick Leave', color: '#f44336' },
  { value: 'EARNED', label: '💰 Earned Leave', color: '#2196F3' },
  { value: 'MATERNITY', label: '👶 Maternity Leave', color: '#E91E63' },
  { value: 'PATERNITY', label: '👨‍👧 Paternity Leave', color: '#9C27B0' },
  { value: 'BEREAVEMENT', label: '🕯️ Bereavement Leave', color: '#607D8B' },
  { value: 'COMPENSATORY', label: '⚡ Compensatory Off', color: '#FF9800' },
  { value: 'WORK_FROM_HOME', label: '🏠 Work From Home', color: '#00BCD4' },
];

const STATUS_COLORS: Record<string, string> = {
  PENDING: '#FF9800',
  APPROVED: '#4CAF50',
  REJECTED: '#f44336',
  CANCELLED: '#9E9E9E',
};

export default function LeaveManagementPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'balances' | 'requests' | 'pending' | 'holidays' | 'policies' | 'meetings' | 'capacity'>('balances');
  
  // Data states
  const [myBalances, setMyBalances] = useState<LeaveBalance[]>([]);
  const [myLeaves, setMyLeaves] = useState<Leave[]>([]);
  const [pendingLeaves, setPendingLeaves] = useState<Leave[]>([]);
  const [companyHolidays, setCompanyHolidays] = useState<Holiday[]>([]);
  const [regionHolidays, setRegionHolidays] = useState<Holiday[]>([]);
  const [policies, setPolicies] = useState<LeavePolicy[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [meetingStats, setMeetingStats] = useState({ total_meeting_hours: 0, meeting_count: 0 });
  const [capacityData, setCapacityData] = useState<any>(null);
  
  const [loading, setLoading] = useState(true);
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [showHolidayModal, setShowHolidayModal] = useState(false);
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  
  const [formData, setFormData] = useState({
    leave_type: 'CASUAL',
    start_date: '',
    end_date: '',
    reason: '',
    partial_day: false,
    hours_off: 0,
  });
  
  const [holidayFormData, setHolidayFormData] = useState({
    name: '',
    date: '',
    year: new Date().getFullYear(),
    region: '',
    is_optional: false,
    is_mandatory: true,
    description: '',
  });
  
  const [meetingFormData, setMeetingFormData] = useState({
    title: '',
    start_time: '',
    end_time: '',
    is_all_day: false,
    is_busy: true,
    category: 'internal',
  });
  
  const [policyFormData, setPolicyFormData] = useState({
    leave_type: 'CASUAL',
    role: '',
    region: '',
    annual_days: 12,
    can_carry_forward: false,
    max_carry_forward_days: 0,
    requires_approval: true,
    min_notice_days: 1,
  });
  
  const [policyInputMode, setPolicyInputMode] = useState<'manual' | 'bulk'>('manual');
  const [bulkPolicyText, setBulkPolicyText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState<string>('');

  useEffect(() => {
    const userData = localStorage.getItem('user');
    const token = localStorage.getItem('access_token');
    
    // Redirect to login if user data or token is missing
    if (!userData || !token) {
      router.push('/login');
      return;
    }
    const parsedUser = JSON.parse(userData);
    setUser(parsedUser);
    setSelectedRegion(parsedUser.region || 'US');
    loadAllData(parsedUser);
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

  const loadAllData = async (currentUser: any) => {
    setLoading(true);
    try {
      await Promise.all([
        loadMyBalances(),
        loadMyLeaves(),
        loadPolicies(),
        loadCompanyHolidays(),
        loadRegionHolidays(currentUser.region || 'US'),
        loadMeetings(),
        loadCapacity(currentUser),
        currentUser.role === 'ADMIN' || currentUser.role === 'MANAGER' ? loadPendingLeaves() : Promise.resolve(),
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMyBalances = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/balances/my?year=${new Date().getFullYear()}`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setMyBalances(data);
      }
    } catch (error) {
      console.error('Error loading balances:', error);
    }
  };

  const loadMyLeaves = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/leaves/my`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setMyLeaves(data);
      }
    } catch (error) {
      console.error('Error loading leaves:', error);
    }
  };

  const loadPendingLeaves = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/leaves/pending`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setPendingLeaves(data);
      }
    } catch (error) {
      console.error('Error loading pending leaves:', error);
    }
  };

  const loadPolicies = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/entitlement-policies`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setPolicies(data);
      }
    } catch (error) {
      console.error('Error loading policies:', error);
    }
  };

  const loadCompanyHolidays = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/holidays/company?year=${new Date().getFullYear()}`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setCompanyHolidays(data);
      }
    } catch (error) {
      console.error('Error loading company holidays:', error);
    }
  };

  const loadRegionHolidays = async (region: string) => {
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/holidays/region/${region}?year=${new Date().getFullYear()}`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setRegionHolidays(data);
      }
    } catch (error) {
      console.error('Error loading region holidays:', error);
    }
  };

  const loadMeetings = async () => {
    try {
      const today = new Date();
      const endDate = new Date(today);
      endDate.setDate(endDate.getDate() + 14);
      
      const response = await fetch(
        `${getApiUrl()}/leave-holiday/meetings/my?start_date=${today.toISOString().split('T')[0]}&end_date=${endDate.toISOString().split('T')[0]}`,
        { headers: getAuthHeaders() }
      );
      if (response.ok) {
        const data = await response.json();
        setMeetings(data.meetings || []);
        setMeetingStats({
          total_meeting_hours: data.total_meeting_hours || 0,
          meeting_count: data.meeting_count || 0
        });
      }
    } catch (error) {
      console.error('Error loading meetings:', error);
    }
  };

  const loadCapacity = async (currentUser: any) => {
    try {
      const today = new Date();
      const endDate = new Date(today);
      endDate.setDate(endDate.getDate() + 14);
      
      const response = await fetch(
        `${getApiUrl()}/leave-holiday/capacity/detailed/${currentUser.id}?start_date=${today.toISOString().split('T')[0]}&end_date=${endDate.toISOString().split('T')[0]}`,
        { headers: getAuthHeaders() }
      );
      if (response.ok) {
        const data = await response.json();
        setCapacityData(data);
      }
    } catch (error) {
      console.error('Error loading capacity:', error);
    }
  };

  const handleRequestLeave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/leaves`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(formData),
      });
      
      if (response.ok) {
        setShowRequestModal(false);
        setFormData({
          leave_type: 'CASUAL',
          start_date: '',
          end_date: '',
          reason: '',
          partial_day: false,
          hours_off: 0,
        });
        await Promise.all([loadMyLeaves(), loadMyBalances()]);
        alert('Leave request submitted successfully!');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to submit leave request');
      }
    } catch (error) {
      console.error('Error submitting leave:', error);
      alert('Failed to submit leave request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveLeave = async (leaveId: string) => {
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/leaves/${leaveId}/approve`, {
        method: 'PUT',
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        await loadPendingLeaves();
        alert('Leave approved!');
      }
    } catch (error) {
      console.error('Error approving leave:', error);
    }
  };

  const handleRejectLeave = async (leaveId: string) => {
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/leaves/${leaveId}/reject`, {
        method: 'PUT',
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        await loadPendingLeaves();
        alert('Leave rejected!');
      }
    } catch (error) {
      console.error('Error rejecting leave:', error);
    }
  };

  const handleAddHoliday = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const endpoint = holidayFormData.region 
        ? `${getApiUrl()}/leave-holiday/holidays/region`
        : `${getApiUrl()}/leave-holiday/holidays/company`;
      
      const body = holidayFormData.region
        ? holidayFormData
        : { name: holidayFormData.name, date: holidayFormData.date, year: holidayFormData.year, description: holidayFormData.description };
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
      });
      
      if (response.ok) {
        setShowHolidayModal(false);
        setHolidayFormData({
          name: '',
          date: '',
          year: new Date().getFullYear(),
          region: '',
          is_optional: false,
          is_mandatory: true,
          description: '',
        });
        await Promise.all([loadCompanyHolidays(), loadRegionHolidays(selectedRegion)]);
        alert('Holiday added successfully!');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to add holiday');
      }
    } catch (error) {
      console.error('Error adding holiday:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/meetings`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(meetingFormData),
      });
      
      if (response.ok) {
        setShowMeetingModal(false);
        setMeetingFormData({
          title: '',
          start_time: '',
          end_time: '',
          is_all_day: false,
          is_busy: true,
          category: 'internal',
        });
        await loadMeetings();
        alert('Meeting block added!');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to add meeting');
      }
    } catch (error) {
      console.error('Error adding meeting:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddPolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const response = await fetch(`${getApiUrl()}/leave-holiday/entitlement-policies`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          ...policyFormData,
          role: policyFormData.role || null,
          region: policyFormData.region || null,
        }),
      });
      
      if (response.ok) {
        setShowPolicyModal(false);
        setPolicyFormData({
          leave_type: 'CASUAL',
          role: '',
          region: '',
          annual_days: 12,
          can_carry_forward: false,
          max_carry_forward_days: 0,
          requires_approval: true,
          min_notice_days: 1,
        });
        await loadPolicies();
        alert('Policy added successfully!');
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to add policy');
      }
    } catch (error) {
      console.error('Error adding policy:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const parseBulkPolicies = (text: string) => {
    // Parse CSV or JSON format
    const lines = text.trim().split('\n');
    const policies: any[] = [];
    
    // Try JSON first
    try {
      const jsonData = JSON.parse(text);
      if (Array.isArray(jsonData)) {
        return jsonData;
      }
    } catch {}
    
    // Parse as CSV (header + rows)
    if (lines.length > 1) {
      const headers = lines[0].toLowerCase().split(',').map(h => h.trim());
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim());
        if (values.length >= 2) {
          const policy: any = {};
          headers.forEach((header, idx) => {
            const value = values[idx];
            if (header.includes('type')) policy.leave_type = value?.toUpperCase();
            else if (header.includes('days') && header.includes('annual')) policy.annual_days = parseInt(value) || 0;
            else if (header.includes('role')) policy.role = value || null;
            else if (header.includes('region')) policy.region = value || null;
            else if (header.includes('carry')) policy.can_carry_forward = value?.toLowerCase() === 'yes' || value?.toLowerCase() === 'true';
            else if (header.includes('max') && header.includes('carry')) policy.max_carry_forward_days = parseInt(value) || 0;
            else if (header.includes('approval')) policy.requires_approval = value?.toLowerCase() !== 'no' && value?.toLowerCase() !== 'auto';
            else if (header.includes('notice')) policy.min_notice_days = parseInt(value) || 0;
          });
          if (policy.leave_type) policies.push(policy);
        }
      }
    }
    return policies;
  };

  const handleBulkImport = async () => {
    if (!bulkPolicyText.trim()) {
      alert('Please paste or enter policy data');
      return;
    }
    
    setSubmitting(true);
    const policies = parseBulkPolicies(bulkPolicyText);
    
    if (policies.length === 0) {
      alert('Could not parse any policies. Please check the format.\n\nSupported formats:\n- CSV with headers: leave_type, annual_days, role, region, carry_forward, approval, notice_days\n- JSON array of policy objects');
      setSubmitting(false);
      return;
    }
    
    let successCount = 0;
    let errorCount = 0;
    
    for (const policy of policies) {
      try {
        const response = await fetch(`${getApiUrl()}/leave-holiday/entitlement-policies`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            leave_type: policy.leave_type || 'CASUAL',
            role: policy.role || null,
            region: policy.region || null,
            annual_days: policy.annual_days || 12,
            can_carry_forward: policy.can_carry_forward || false,
            max_carry_forward_days: policy.max_carry_forward_days || 0,
            requires_approval: policy.requires_approval !== false,
            min_notice_days: policy.min_notice_days || 0,
          }),
        });
        if (response.ok) successCount++;
        else errorCount++;
      } catch {
        errorCount++;
      }
    }
    
    setSubmitting(false);
    setBulkPolicyText('');
    setPolicyInputMode('manual');
    setShowPolicyModal(false);
    await loadPolicies();
    alert(`Imported ${successCount} policies successfully${errorCount > 0 ? `, ${errorCount} failed` : ''}`);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setBulkPolicyText(text);
    };
    reader.readAsText(file);
  };

  const getLeaveTypeInfo = (type: string) => {
    return LEAVE_TYPES.find(t => t.value === type) || { label: type, color: '#9E9E9E' };
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!user) return null;

  const isManager = user.role === 'ADMIN' || user.role === 'MANAGER';

  return (
    <div className="page-container">
      <Navigation />
      
      <main className="main-content">
        <div className="page-header">
          <div className="header-left">
            <h1>📅 Leave & Capacity Management</h1>
            <p>Manage leaves, holidays, meetings, and track your capacity</p>
          </div>
          <button className="btn-primary" onClick={() => setShowRequestModal(true)}>
            ➕ Request Leave
          </button>
        </div>

        <div className="tabs">
          <button className={`tab ${activeTab === 'balances' ? 'active' : ''}`} onClick={() => setActiveTab('balances')}>
            💰 My Balances
          </button>
          <button className={`tab ${activeTab === 'requests' ? 'active' : ''}`} onClick={() => setActiveTab('requests')}>
            📋 My Requests
          </button>
          {isManager && (
            <button className={`tab ${activeTab === 'pending' ? 'active' : ''}`} onClick={() => setActiveTab('pending')}>
              ⏳ Approvals {pendingLeaves.length > 0 && <span className="badge">{pendingLeaves.length}</span>}
            </button>
          )}
          <button className={`tab ${activeTab === 'holidays' ? 'active' : ''}`} onClick={() => setActiveTab('holidays')}>
            🎉 Holidays
          </button>
          {isManager && (
            <button className={`tab ${activeTab === 'policies' ? 'active' : ''}`} onClick={() => setActiveTab('policies')}>
              📜 Policies
            </button>
          )}
          <button className={`tab ${activeTab === 'meetings' ? 'active' : ''}`} onClick={() => setActiveTab('meetings')}>
            📆 Meetings
          </button>
          <button className={`tab ${activeTab === 'capacity' ? 'active' : ''}`} onClick={() => setActiveTab('capacity')}>
            📊 My Capacity
          </button>
        </div>

        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Loading...</p>
          </div>
        ) : (
          <div className="tab-content">
            {/* Balances Tab */}
            {activeTab === 'balances' && (
              <div className="balances-section">
                <h3>Leave Balances for {new Date().getFullYear()}</h3>
                <div className="balance-grid">
                  {myBalances.map((balance) => {
                    const typeInfo = getLeaveTypeInfo(balance.leave_type);
                    const usedPct = (balance.used_days / balance.entitled_days) * 100;
                    return (
                      <div key={balance.id} className="balance-card">
                        <div className="balance-header" style={{ borderColor: typeInfo.color }}>
                          <span className="balance-type">{typeInfo.label}</span>
                        </div>
                        <div className="balance-stats">
                          <div className="stat-row">
                            <span>Entitled</span>
                            <strong>{balance.entitled_days} days</strong>
                          </div>
                          {balance.carried_forward > 0 && (
                            <div className="stat-row">
                              <span>Carried Forward</span>
                              <strong>+{balance.carried_forward} days</strong>
                            </div>
                          )}
                          <div className="stat-row">
                            <span>Used</span>
                            <strong className="used">{balance.used_days} days</strong>
                          </div>
                          {balance.pending_days > 0 && (
                            <div className="stat-row">
                              <span>Pending</span>
                              <strong className="pending">{balance.pending_days} days</strong>
                            </div>
                          )}
                          <div className="stat-row available">
                            <span>Available</span>
                            <strong>{balance.available_days} days</strong>
                          </div>
                        </div>
                        <div className="balance-bar">
                          <div 
                            className="bar-fill" 
                            style={{ 
                              width: `${Math.min(usedPct, 100)}%`,
                              backgroundColor: usedPct > 80 ? '#f44336' : typeInfo.color
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Requests Tab */}
            {activeTab === 'requests' && (
              <div className="leaves-list">
                {myLeaves.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-icon">📭</span>
                    <h3>No Leave Requests</h3>
                    <p>You haven't requested any leaves yet.</p>
                    <button className="btn-primary" onClick={() => setShowRequestModal(true)}>Request Leave</button>
                  </div>
                ) : (
                  myLeaves.map((leave) => {
                    const typeInfo = getLeaveTypeInfo(leave.leave_type);
                    return (
                      <div key={leave.id} className="leave-card">
                        <div className="leave-header">
                          <span className="leave-type" style={{ backgroundColor: typeInfo.color }}>{typeInfo.label}</span>
                          <span className="leave-status" style={{ backgroundColor: STATUS_COLORS[leave.status] }}>{leave.status}</span>
                        </div>
                        <div className="leave-dates">
                          <span>{formatDate(leave.start_date)} - {formatDate(leave.end_date)}</span>
                        </div>
                        {leave.reason && <p className="leave-reason">{leave.reason}</p>}
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Pending Approvals Tab */}
            {activeTab === 'pending' && isManager && (
              <div className="leaves-list">
                {pendingLeaves.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-icon">✅</span>
                    <h3>All Caught Up!</h3>
                    <p>No pending leave requests.</p>
                  </div>
                ) : (
                  pendingLeaves.map((leave) => {
                    const typeInfo = getLeaveTypeInfo(leave.leave_type);
                    return (
                      <div key={leave.id} className="leave-card pending">
                        <div className="leave-header">
                          <div className="user-info">
                            <span className="user-avatar">{leave.user_name.charAt(0)}</span>
                            <span>{leave.user_name}</span>
                          </div>
                          <span className="leave-type" style={{ backgroundColor: typeInfo.color }}>{typeInfo.label}</span>
                        </div>
                        <div className="leave-dates">
                          <span>{formatDate(leave.start_date)} - {formatDate(leave.end_date)}</span>
                        </div>
                        {leave.reason && <p className="leave-reason">{leave.reason}</p>}
                        <div className="approval-actions">
                          <button className="btn-approve" onClick={() => handleApproveLeave(leave.id)}>✅ Approve</button>
                          <button className="btn-reject" onClick={() => handleRejectLeave(leave.id)}>❌ Reject</button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Holidays Tab */}
            {activeTab === 'holidays' && (
              <div className="holidays-section">
                <div className="holidays-header">
                  <h3>Public Holidays {new Date().getFullYear()}</h3>
                  {isManager && (
                    <button className="btn-secondary" onClick={() => setShowHolidayModal(true)}>➕ Add Holiday</button>
                  )}
                </div>
                
                <div className="holidays-grid">
                  <div className="holidays-column">
                    <h4>🏢 Company Holidays (Source of Truth)</h4>
                    <p className="info-text">These holidays apply to all employees.</p>
                    {companyHolidays.length === 0 ? (
                      <p className="no-data">No company holidays configured</p>
                    ) : (
                      <ul className="holiday-list">
                        {companyHolidays.map((h) => (
                          <li key={h.id} className="holiday-item company">
                            <span className="holiday-date">{formatDate(h.date)}</span>
                            <span className="holiday-name">{h.name}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  
                  <div className="holidays-column">
                    <div className="region-header">
                      <h4>🌍 Regional Holidays</h4>
                      <select value={selectedRegion} onChange={(e) => { setSelectedRegion(e.target.value); loadRegionHolidays(e.target.value); }}>
                        <option value="US">🇺🇸 US</option>
                        <option value="INDIA">🇮🇳 India</option>
                        <option value="PH">🇵🇭 Philippines</option>
                      </select>
                    </div>
                    {regionHolidays.length === 0 ? (
                      <p className="no-data">No regional holidays configured</p>
                    ) : (
                      <ul className="holiday-list">
                        {regionHolidays.map((h) => (
                          <li key={h.id} className={`holiday-item region ${h.is_optional ? 'optional' : ''}`}>
                            <span className="holiday-date">{formatDate(h.date)}</span>
                            <span className="holiday-name">
                              {h.name}
                              {h.is_optional && <span className="optional-badge">Optional</span>}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Policies Tab */}
            {activeTab === 'policies' && isManager && (
              <div className="policies-section">
                <div className="section-header">
                  <h3>Leave Entitlement Policies</h3>
                  <button className="btn-secondary" onClick={() => setShowPolicyModal(true)}>➕ Add Policy</button>
                </div>
                <div className="policies-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Leave Type</th>
                        <th>Role</th>
                        <th>Region</th>
                        <th>Annual Days</th>
                        <th>Carry Forward</th>
                        <th>Approval</th>
                        <th>Notice</th>
                      </tr>
                    </thead>
                    <tbody>
                      {policies.map((policy) => (
                        <tr key={policy.id}>
                          <td>{getLeaveTypeInfo(policy.leave_type).label}</td>
                          <td>{policy.role || 'All'}</td>
                          <td>{policy.region || 'All'}</td>
                          <td>{policy.annual_days}</td>
                          <td>{policy.can_carry_forward ? `Yes (max ${policy.max_carry_forward_days})` : 'No'}</td>
                          <td>{policy.requires_approval ? 'Required' : 'Auto'}</td>
                          <td>{policy.min_notice_days} days</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Meetings Tab */}
            {activeTab === 'meetings' && (
              <div className="meetings-section">
                <div className="section-header">
                  <h3>📆 Meeting Blocks (Next 2 Weeks)</h3>
                  <button className="btn-secondary" onClick={() => setShowMeetingModal(true)}>➕ Add Meeting</button>
                </div>
                
                <div className="meeting-stats">
                  <div className="stat-card">
                    <span className="stat-value">{meetingStats.meeting_count}</span>
                    <span className="stat-label">Meetings</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-value">{meetingStats.total_meeting_hours.toFixed(1)}h</span>
                    <span className="stat-label">Total Time</span>
                  </div>
                </div>
                
                <p className="info-text">
                  💡 Add your recurring meetings to get accurate capacity calculations. 
                  Soon: Sync with Google Calendar or Outlook!
                </p>
                
                {meetings.length === 0 ? (
                  <div className="empty-state">
                    <span className="empty-icon">📅</span>
                    <h3>No Meetings Tracked</h3>
                    <p>Add your meetings to improve capacity accuracy.</p>
                  </div>
                ) : (
                  <div className="meeting-list">
                    {meetings.map((meeting) => (
                      <div key={meeting.id} className="meeting-card">
                        <div className="meeting-info">
                          <span className="meeting-title">{meeting.title}</span>
                          <span className="meeting-time">
                            {formatDateTime(meeting.start_time)} - {formatDateTime(meeting.end_time)}
                          </span>
                        </div>
                        <div className="meeting-meta">
                          <span className="meeting-duration">{meeting.duration_hours.toFixed(1)}h</span>
                          {meeting.is_busy && <span className="busy-badge">Blocks Capacity</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Capacity Tab */}
            {activeTab === 'capacity' && capacityData && (
              <div className="capacity-section">
                <h3>📊 My Capacity Overview (Next 2 Weeks)</h3>
                
                <div className="capacity-summary">
                  <div className="capacity-card main">
                    <span className="capacity-label">Net Available</span>
                    <span className="capacity-value">{capacityData.capacity_breakdown?.net_available_hours || 0}h</span>
                    <div className="capacity-bar">
                      <div 
                        className="bar-fill"
                        style={{ 
                          width: `${capacityData.utilization?.percentage || 0}%`,
                          backgroundColor: capacityData.utilization?.status === 'CRITICAL' ? '#f44336' : 
                                          capacityData.utilization?.status === 'HIGH' ? '#FF9800' : '#4CAF50'
                        }}
                      />
                    </div>
                    <span className="utilization-label">
                      {capacityData.utilization?.percentage || 0}% Utilized ({capacityData.utilization?.status})
                    </span>
                  </div>
                </div>
                
                <div className="capacity-breakdown">
                  <h4>Capacity Breakdown</h4>
                  <div className="breakdown-grid">
                    <div className="breakdown-item">
                      <span className="item-label">Base Capacity</span>
                      <span className="item-value positive">+{capacityData.capacity_breakdown?.base_capacity_hours || 0}h</span>
                      <span className="item-detail">({capacityData.capacity_breakdown?.daily_hours}h × {capacityData.period?.working_days} days)</span>
                    </div>
                    <div className="breakdown-item">
                      <span className="item-label">Leave/Holidays</span>
                      <span className="item-value negative">-{capacityData.capacity_breakdown?.deductions?.leave_hours || 0}h</span>
                      <span className="item-detail">({capacityData.capacity_breakdown?.deductions?.leave_days || 0} days off)</span>
                    </div>
                    <div className="breakdown-item">
                      <span className="item-label">Meetings</span>
                      <span className="item-value negative">-{capacityData.capacity_breakdown?.deductions?.meeting_hours || 0}h</span>
                    </div>
                    <div className="breakdown-item">
                      <span className="item-label">Buffer ({capacityData.capacity_breakdown?.deductions?.buffer_percentage}%)</span>
                      <span className="item-value negative">-{capacityData.capacity_breakdown?.deductions?.buffer_hours || 0}h</span>
                    </div>
                    <div className="breakdown-item total">
                      <span className="item-label">Remaining</span>
                      <span className="item-value">{capacityData.capacity_breakdown?.remaining_hours || 0}h</span>
                    </div>
                  </div>
                </div>
                
                {(capacityData.upcoming_blockers?.leaves?.length > 0 || capacityData.upcoming_blockers?.holidays?.length > 0) && (
                  <div className="blockers-section">
                    <h4>⚠️ Upcoming Blockers</h4>
                    <div className="blockers-list">
                      {capacityData.upcoming_blockers?.leaves?.map((leave: any, idx: number) => (
                        <span key={`leave-${idx}`} className="blocker-tag leave">
                          {leave.type}: {leave.start_date} to {leave.end_date}
                        </span>
                      ))}
                      {capacityData.upcoming_blockers?.holidays?.map((holiday: any, idx: number) => (
                        <span key={`holiday-${idx}`} className="blocker-tag holiday">
                          🎉 {holiday.name} ({holiday.date})
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Request Leave Modal */}
      {showRequestModal && (
        <div className="modal-overlay" onClick={() => setShowRequestModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📅 Request Leave</h2>
              <button className="close-btn" onClick={() => setShowRequestModal(false)}>×</button>
            </div>
            <form onSubmit={handleRequestLeave}>
              <div className="form-group">
                <label>Leave Type</label>
                <select value={formData.leave_type} onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })} required>
                  {LEAVE_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
                {myBalances.find(b => b.leave_type === formData.leave_type) && (
                  <p className="balance-hint">
                    Available: {myBalances.find(b => b.leave_type === formData.leave_type)?.available_days} days
                  </p>
                )}
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Start Date</label>
                  <input type="date" value={formData.start_date} onChange={(e) => setFormData({ ...formData, start_date: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>End Date</label>
                  <input type="date" value={formData.end_date} onChange={(e) => setFormData({ ...formData, end_date: e.target.value })} min={formData.start_date} required />
                </div>
              </div>
              <div className="form-group">
                <label>Reason</label>
                <textarea value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })} placeholder="Optional reason..." rows={2} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowRequestModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit Request'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Holiday Modal */}
      {showHolidayModal && (
        <div className="modal-overlay" onClick={() => setShowHolidayModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🎉 Add Holiday</h2>
              <button className="close-btn" onClick={() => setShowHolidayModal(false)}>×</button>
            </div>
            <form onSubmit={handleAddHoliday}>
              <div className="form-group">
                <label>Holiday Name</label>
                <input type="text" value={holidayFormData.name} onChange={(e) => setHolidayFormData({ ...holidayFormData, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Date</label>
                <input type="date" value={holidayFormData.date} onChange={(e) => setHolidayFormData({ ...holidayFormData, date: e.target.value, year: new Date(e.target.value).getFullYear() })} required />
              </div>
              <div className="form-group">
                <label>Scope</label>
                <select value={holidayFormData.region} onChange={(e) => setHolidayFormData({ ...holidayFormData, region: e.target.value })}>
                  <option value="">🏢 Company-wide (all employees)</option>
                  <option value="US">🇺🇸 US Only</option>
                  <option value="INDIA">🇮🇳 India Only</option>
                  <option value="PH">🇵🇭 Philippines Only</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowHolidayModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Adding...' : 'Add Holiday'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Meeting Modal */}
      {showMeetingModal && (
        <div className="modal-overlay" onClick={() => setShowMeetingModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📆 Add Meeting Block</h2>
              <button className="close-btn" onClick={() => setShowMeetingModal(false)}>×</button>
            </div>
            <form onSubmit={handleAddMeeting}>
              <div className="form-group">
                <label>Meeting Title</label>
                <input type="text" value={meetingFormData.title} onChange={(e) => setMeetingFormData({ ...meetingFormData, title: e.target.value })} placeholder="e.g., Daily Standup" required />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Start Time</label>
                  <input type="datetime-local" value={meetingFormData.start_time} onChange={(e) => setMeetingFormData({ ...meetingFormData, start_time: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>End Time</label>
                  <input type="datetime-local" value={meetingFormData.end_time} onChange={(e) => setMeetingFormData({ ...meetingFormData, end_time: e.target.value })} required />
                </div>
              </div>
              <div className="form-group">
                <label>Category</label>
                <select value={meetingFormData.category} onChange={(e) => setMeetingFormData({ ...meetingFormData, category: e.target.value })}>
                  <option value="internal">Internal Meeting</option>
                  <option value="client">Client Meeting</option>
                  <option value="standup">Standup</option>
                  <option value="training">Training</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" checked={meetingFormData.is_busy} onChange={(e) => setMeetingFormData({ ...meetingFormData, is_busy: e.target.checked })} />
                  Blocks capacity (count as unavailable time)
                </label>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowMeetingModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Adding...' : 'Add Meeting'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Policy Modal */}
      {showPolicyModal && (
        <div className="modal-overlay" onClick={() => setShowPolicyModal(false)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📜 Add Leave Policy</h2>
              <button className="close-btn" onClick={() => setShowPolicyModal(false)}>×</button>
            </div>
            
            {/* Mode Toggle */}
            <div className="mode-toggle">
              <button 
                type="button"
                className={`toggle-btn ${policyInputMode === 'manual' ? 'active' : ''}`}
                onClick={() => setPolicyInputMode('manual')}
              >
                ✏️ Manual Entry
              </button>
              <button 
                type="button"
                className={`toggle-btn ${policyInputMode === 'bulk' ? 'active' : ''}`}
                onClick={() => setPolicyInputMode('bulk')}
              >
                📋 Bulk Import
              </button>
            </div>

            {policyInputMode === 'manual' ? (
              <form onSubmit={handleAddPolicy}>
                <div className="form-group">
                  <label>Leave Type</label>
                  <select value={policyFormData.leave_type} onChange={(e) => setPolicyFormData({ ...policyFormData, leave_type: e.target.value })} required>
                    {LEAVE_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                    <option value="UNPAID">📝 Unpaid Leave</option>
                  </select>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Role (Optional)</label>
                    <select value={policyFormData.role} onChange={(e) => setPolicyFormData({ ...policyFormData, role: e.target.value })}>
                      <option value="">All Roles</option>
                      <option value="ADMIN">Admin</option>
                      <option value="MANAGER">Manager</option>
                      <option value="PC">PC</option>
                      <option value="CONSULTANT">Consultant</option>
                      <option value="BUILDER">Builder</option>
                      <option value="TESTER">Tester</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Region (Optional)</label>
                    <select value={policyFormData.region} onChange={(e) => setPolicyFormData({ ...policyFormData, region: e.target.value })}>
                      <option value="">All Regions</option>
                      <option value="US">🇺🇸 US</option>
                      <option value="INDIA">🇮🇳 India</option>
                      <option value="PH">🇵🇭 Philippines</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Annual Days</label>
                    <input type="number" min="0" max="365" value={policyFormData.annual_days} onChange={(e) => setPolicyFormData({ ...policyFormData, annual_days: parseInt(e.target.value) || 0 })} required />
                  </div>
                  <div className="form-group">
                    <label>Min Notice (Days)</label>
                    <input type="number" min="0" max="90" value={policyFormData.min_notice_days} onChange={(e) => setPolicyFormData({ ...policyFormData, min_notice_days: parseInt(e.target.value) || 0 })} required />
                  </div>
                </div>
                <div className="form-group checkbox-group">
                  <label>
                    <input type="checkbox" checked={policyFormData.requires_approval} onChange={(e) => setPolicyFormData({ ...policyFormData, requires_approval: e.target.checked })} />
                    Requires Manager Approval
                  </label>
                </div>
                <div className="form-group checkbox-group">
                  <label>
                    <input type="checkbox" checked={policyFormData.can_carry_forward} onChange={(e) => setPolicyFormData({ ...policyFormData, can_carry_forward: e.target.checked })} />
                    Can Carry Forward to Next Year
                  </label>
                </div>
                {policyFormData.can_carry_forward && (
                  <div className="form-group">
                    <label>Max Carry Forward Days</label>
                    <input type="number" min="0" max="30" value={policyFormData.max_carry_forward_days} onChange={(e) => setPolicyFormData({ ...policyFormData, max_carry_forward_days: parseInt(e.target.value) || 0 })} />
                  </div>
                )}
                <div className="modal-actions">
                  <button type="button" className="btn-secondary" onClick={() => setShowPolicyModal(false)}>Cancel</button>
                  <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Adding...' : 'Add Policy'}</button>
                </div>
              </form>
            ) : (
              <div className="bulk-import-section">
                <div className="form-group">
                  <label>Upload CSV/JSON File</label>
                  <input 
                    type="file" 
                    accept=".csv,.json,.txt" 
                    onChange={handleFileUpload}
                    className="file-input"
                  />
                </div>
                
                <div className="divider">
                  <span>OR</span>
                </div>
                
                <div className="form-group">
                  <label>Paste Policy Data (CSV or JSON)</label>
                  <textarea 
                    value={bulkPolicyText}
                    onChange={(e) => setBulkPolicyText(e.target.value)}
                    placeholder={`CSV Format:
leave_type,annual_days,role,region,carry_forward,approval,notice_days
CASUAL,12,,,no,required,1
SICK,12,,,no,auto,0
EARNED,15,,,yes,required,7

JSON Format:
[
  {"leave_type": "CASUAL", "annual_days": 12, "requires_approval": true},
  {"leave_type": "SICK", "annual_days": 12, "requires_approval": false}
]`}
                    rows={10}
                    className="bulk-textarea"
                  />
                </div>
                
                <div className="format-help">
                  <h4>📖 Supported Formats:</h4>
                  <ul>
                    <li><strong>CSV:</strong> Headers: leave_type, annual_days, role, region, carry_forward, max_carry_days, approval, notice_days</li>
                    <li><strong>JSON:</strong> Array of policy objects with leave_type, annual_days, etc.</li>
                    <li><strong>Leave Types:</strong> CASUAL, SICK, EARNED, MATERNITY, PATERNITY, BEREAVEMENT, COMPENSATORY, WORK_FROM_HOME, UNPAID</li>
                  </ul>
                </div>
                
                <div className="modal-actions">
                  <button type="button" className="btn-secondary" onClick={() => setShowPolicyModal(false)}>Cancel</button>
                  <button type="button" className="btn-primary" onClick={handleBulkImport} disabled={submitting || !bulkPolicyText.trim()}>
                    {submitting ? 'Importing...' : `Import Policies`}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        .page-container { min-height: 100vh; background: #f8fafc; }
        .main-content { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
        .header-left h1 { font-size: 1.75rem; color: #1e293b; margin-bottom: 0.25rem; }
        .header-left p { color: #64748b; }
        
        .tabs { display: flex; gap: 0.25rem; border-bottom: 2px solid #e2e8f0; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .tab { padding: 0.75rem 1rem; background: none; border: none; color: #64748b; font-weight: 500; cursor: pointer; position: relative; display: flex; align-items: center; gap: 0.5rem; }
        .tab.active { color: #2563eb; }
        .tab.active::after { content: ''; position: absolute; bottom: -2px; left: 0; right: 0; height: 2px; background: #2563eb; }
        .tab .badge { background: #2563eb; color: white; padding: 0.125rem 0.5rem; border-radius: 10px; font-size: 0.75rem; }
        
        .loading-container { display: flex; flex-direction: column; align-items: center; padding: 4rem; }
        .spinner { width: 40px; height: 40px; border: 3px solid #e2e8f0; border-top-color: #2563eb; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .empty-state { text-align: center; padding: 4rem 2rem; background: #ffffff; border-radius: 12px; }
        .empty-icon { font-size: 3rem; display: block; margin-bottom: 1rem; }
        .empty-state h3 { color: #1e293b; margin-bottom: 0.5rem; }
        .empty-state p { color: #64748b; margin-bottom: 1.5rem; }
        
        /* Balances */
        .balances-section h3 { margin-bottom: 1.5rem; color: #1e293b; }
        .balance-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
        .balance-card { background: #ffffff; border-radius: 12px; padding: 1.25rem; border: 1px solid #e2e8f0; }
        .balance-header { padding-bottom: 0.75rem; margin-bottom: 1rem; border-bottom: 3px solid; }
        .balance-type { font-weight: 600; color: #1e293b; }
        .balance-stats { display: flex; flex-direction: column; gap: 0.5rem; }
        .stat-row { display: flex; justify-content: space-between; font-size: 0.9rem; }
        .stat-row span { color: #64748b; }
        .stat-row strong { color: #1e293b; }
        .stat-row strong.used { color: #f44336; }
        .stat-row strong.pending { color: #FF9800; }
        .stat-row.available { padding-top: 0.5rem; border-top: 1px dashed #e2e8f0; font-size: 1rem; }
        .stat-row.available strong { color: #4CAF50; }
        .balance-bar { height: 6px; background: #f8fafc; border-radius: 3px; margin-top: 1rem; overflow: hidden; }
        .bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
        
        /* Leaves List */
        .leaves-list { display: grid; gap: 1rem; }
        .leave-card { background: #ffffff; border-radius: 12px; padding: 1.25rem; border: 1px solid #e2e8f0; }
        .leave-card.pending { border-left: 4px solid #FF9800; }
        .leave-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .user-info { display: flex; align-items: center; gap: 0.75rem; }
        .user-avatar { width: 36px; height: 36px; background: #2563eb; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; }
        .leave-type, .leave-status { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; color: white; font-weight: 500; }
        .leave-dates { color: #1e293b; font-weight: 500; margin-bottom: 0.5rem; }
        .leave-reason { color: #64748b; font-size: 0.9rem; padding: 0.75rem; background: #f8fafc; border-radius: 8px; }
        .approval-actions { display: flex; gap: 0.75rem; margin-top: 1rem; }
        .btn-approve { flex: 1; padding: 0.75rem; background: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; }
        .btn-reject { flex: 1; padding: 0.75rem; background: #f44336; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; }
        
        /* Holidays */
        .holidays-section { background: #ffffff; border-radius: 12px; padding: 1.5rem; }
        .holidays-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
        .holidays-header h3 { color: #1e293b; margin: 0; }
        .holidays-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
        @media (max-width: 768px) { .holidays-grid { grid-template-columns: 1fr; } }
        .holidays-column h4 { color: #1e293b; margin-bottom: 0.5rem; }
        .region-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
        .region-header select { padding: 0.25rem 0.5rem; border-radius: 4px; border: 1px solid #e2e8f0; }
        .info-text { color: #64748b; font-size: 0.85rem; margin-bottom: 1rem; }
        .no-data { color: #64748b; font-style: italic; }
        .holiday-list { list-style: none; padding: 0; margin: 0; }
        .holiday-item { display: flex; gap: 1rem; padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; }
        .holiday-item.company { background: #E3F2FD; }
        .holiday-item.region { background: #FFF3E0; }
        .holiday-item.optional { opacity: 0.7; }
        .holiday-date { color: #64748b; font-size: 0.85rem; min-width: 100px; }
        .holiday-name { color: #1e293b; font-weight: 500; display: flex; align-items: center; gap: 0.5rem; }
        .optional-badge { background: #9E9E9E; color: white; padding: 0.125rem 0.5rem; border-radius: 10px; font-size: 0.7rem; }
        
        /* Policies */
        .policies-section { background: #ffffff; border-radius: 12px; padding: 1.5rem; }
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
        .section-header h3 { color: #1e293b; margin: 0; }
        .policies-table { overflow-x: auto; }
        .policies-table table { width: 100%; border-collapse: collapse; }
        .policies-table th, .policies-table td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
        .policies-table th { color: #64748b; font-weight: 500; font-size: 0.85rem; }
        .policies-table td { color: #1e293b; }
        
        /* Meetings */
        .meetings-section { background: #ffffff; border-radius: 12px; padding: 1.5rem; }
        .meeting-stats { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
        .stat-card { background: #f8fafc; padding: 1rem 1.5rem; border-radius: 8px; text-align: center; }
        .stat-value { display: block; font-size: 1.5rem; font-weight: 700; color: #2563eb; }
        .stat-label { color: #64748b; font-size: 0.85rem; }
        .meeting-list { display: grid; gap: 0.75rem; }
        .meeting-card { display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: #f8fafc; border-radius: 8px; }
        .meeting-title { font-weight: 500; color: #1e293b; display: block; }
        .meeting-time { font-size: 0.85rem; color: #64748b; }
        .meeting-duration { font-weight: 600; color: #2563eb; margin-right: 0.5rem; }
        .busy-badge { background: #FFF3E0; color: #E65100; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }
        
        /* Capacity */
        .capacity-section { background: #ffffff; border-radius: 12px; padding: 1.5rem; }
        .capacity-section h3 { color: #1e293b; margin-bottom: 1.5rem; }
        .capacity-summary { margin-bottom: 2rem; }
        .capacity-card.main { background: #f8fafc; padding: 1.5rem; border-radius: 12px; text-align: center; }
        .capacity-label { display: block; color: #64748b; margin-bottom: 0.5rem; }
        .capacity-value { display: block; font-size: 2.5rem; font-weight: 700; color: #2563eb; }
        .capacity-bar { height: 8px; background: #E0E0E0; border-radius: 4px; margin: 1rem 0; overflow: hidden; }
        .utilization-label { color: #64748b; font-size: 0.9rem; }
        
        .capacity-breakdown h4 { color: #1e293b; margin-bottom: 1rem; }
        .breakdown-grid { display: grid; gap: 0.75rem; }
        .breakdown-item { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: #f8fafc; border-radius: 8px; }
        .item-label { color: #64748b; }
        .item-value { font-weight: 600; }
        .item-value.positive { color: #4CAF50; }
        .item-value.negative { color: #f44336; }
        .item-detail { color: #94a3b8; font-size: 0.8rem; }
        .breakdown-item.total { background: #2563eb; color: white; }
        .breakdown-item.total .item-label, .breakdown-item.total .item-value { color: white; }
        
        .blockers-section { margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0; }
        .blockers-section h4 { color: #1e293b; margin-bottom: 1rem; }
        .blockers-list { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .blocker-tag { padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.85rem; }
        .blocker-tag.leave { background: #FFEBEE; color: #C62828; }
        .blocker-tag.holiday { background: #FFF3E0; color: #E65100; }
        
        /* Modals */
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
        .modal { background: #ffffff; border-radius: 16px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); }
        .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1.25rem 1.5rem; border-bottom: 1px solid #e2e8f0; background: #f8fafc; border-radius: 16px 16px 0 0; }
        .modal-header h2 { font-size: 1.25rem; color: #1e293b; margin: 0; }
        .close-btn { background: none; border: none; font-size: 1.5rem; color: #64748b; cursor: pointer; line-height: 1; padding: 0.25rem; }
        .close-btn:hover { color: #1e293b; }
        .modal form { padding: 1.5rem; background: #ffffff; }
        .form-group { margin-bottom: 1.25rem; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; color: #1e293b; font-weight: 500; font-size: 0.9rem; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 8px; background: #ffffff; color: #1e293b; font-size: 1rem; box-sizing: border-box; }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
        .balance-hint { color: #64748b; font-size: 0.85rem; margin-top: 0.25rem; }
        .checkbox-group label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; color: #1e293b; }
        .checkbox-group input[type="checkbox"] { width: auto; }
        .modal-actions { display: flex; gap: 1rem; justify-content: flex-end; padding-top: 1rem; border-top: 1px solid #e2e8f0; background: #ffffff; }
        
        .btn-primary { padding: 0.75rem 1.5rem; background: #2563eb; color: #ffffff; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 0.95rem; }
        .btn-primary:hover { background: #1d4ed8; }
        .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-secondary { padding: 0.75rem 1.5rem; background: #f8fafc; color: #1e293b; border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 0.95rem; }
        .btn-secondary:hover { background: #f1f5f9; }
        
        /* Modal Large */
        .modal-lg { max-width: 600px; }
        
        /* Mode Toggle */
        .mode-toggle { display: flex; gap: 0; border-bottom: 1px solid #e2e8f0; margin: 0; padding: 0 1.5rem; }
        .toggle-btn { flex: 1; padding: 1rem; background: none; border: none; border-bottom: 3px solid transparent; color: #64748b; font-weight: 500; cursor: pointer; transition: all 0.2s; }
        .toggle-btn:hover { background: #f8fafc; }
        .toggle-btn.active { color: #2563eb; border-bottom-color: #2563eb; background: #f8fafc; }
        
        /* Bulk Import */
        .bulk-import-section { padding: 1.5rem; }
        .file-input { width: 100%; padding: 0.75rem; border: 2px dashed #e2e8f0; border-radius: 8px; background: #f8fafc; cursor: pointer; }
        .file-input:hover { border-color: #2563eb; }
        .divider { display: flex; align-items: center; gap: 1rem; margin: 1.5rem 0; color: #94a3b8; }
        .divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: #e2e8f0; }
        .bulk-textarea { width: 100%; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 8px; font-family: monospace; font-size: 0.85rem; resize: vertical; min-height: 200px; background: #ffffff; color: #1e293b; box-sizing: border-box; }
        .bulk-textarea::placeholder { color: #94a3b8; }
        .format-help { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 1rem; margin-top: 1rem; }
        .format-help h4 { margin: 0 0 0.5rem; color: #0369a1; font-size: 0.9rem; }
        .format-help ul { margin: 0; padding-left: 1.25rem; font-size: 0.8rem; color: #0c4a6e; }
        .format-help li { margin-bottom: 0.25rem; }
      `}</style>
    </div>
  );
}
