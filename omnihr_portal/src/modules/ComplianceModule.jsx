import React, { useState } from 'react';
import { Shield, ShieldCheck, ShieldAlert, Lock, Globe, FileText, AlertTriangle, CheckCircle, Clock, Users, Download, Eye, ChevronRight, Search, Filter, Calendar, Award, Database, Server, Key, Activity, ChevronLeft } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function ComplianceModule() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');

  const [auditSearch, setAuditSearch] = useState('');
  const [auditAction, setAuditAction] = useState('');

  const mockAuditLogs = [
    { id: 1, timestamp: '2026-07-29 01:25:10', user: 'admin@omnihr.com', action: 'LOGIN', resource: 'System', ip: '192.168.1.45', status: 'Success' },
    { id: 2, timestamp: '2026-07-29 01:15:05', user: 'hr@omnihr.com', action: 'CREATE_EMPLOYEE', resource: 'Employee: EMP004', ip: '10.0.0.12', status: 'Success' },
    { id: 3, timestamp: '2026-07-29 01:10:00', user: 'finance@omnihr.com', action: 'PAYROLL_RUN', resource: 'Payroll: Jul2026', ip: '10.0.0.55', status: 'Success' },
    { id: 4, timestamp: '2026-07-28 23:45:12', user: 'unknown', action: 'LOGIN_FAILED', resource: 'System', ip: '45.22.11.9', status: 'Failed' },
    { id: 5, timestamp: '2026-07-28 22:30:00', user: 'manager@omnihr.com', action: 'VIEW_SALARY', resource: 'Employee: EMP002', ip: '192.168.1.100', status: 'Success' },
    { id: 6, timestamp: '2026-07-28 20:15:22', user: 'admin@omnihr.com', action: 'EXPORT_DATA', resource: 'Report: Q2_Attrition', ip: '192.168.1.45', status: 'Warning' },
    { id: 7, timestamp: '2026-07-28 18:00:00', user: 'hr@omnihr.com', action: 'UPDATE_POLICY', resource: 'Doc: WFH_Policy', ip: '10.0.0.12', status: 'Success' },
    { id: 8, timestamp: '2026-07-28 15:45:10', user: 'user@omnihr.com', action: 'LOGIN', resource: 'System', ip: '192.168.1.50', status: 'Success' },
    { id: 9, timestamp: '2026-07-28 14:20:05', user: 'finance@omnihr.com', action: 'EXPORT_DATA', resource: 'Report: Payroll_Jul', ip: '10.0.0.55', status: 'Success' },
    { id: 10, timestamp: '2026-07-28 12:10:00', user: 'admin@omnihr.com', action: 'CHANGE_PERMISSION', resource: 'Role: Manager', ip: '192.168.1.45', status: 'Warning' },
    { id: 11, timestamp: '2026-07-28 10:05:12', user: 'unknown', action: 'LOGIN_FAILED', resource: 'System', ip: '203.0.113.45', status: 'Failed' },
    { id: 12, timestamp: '2026-07-28 09:30:00', user: 'manager@omnihr.com', action: 'APPROVE_LEAVE', resource: 'Request: L-849', ip: '192.168.1.100', status: 'Success' },
    { id: 13, timestamp: '2026-07-28 08:15:22', user: 'hr@omnihr.com', action: 'LOGIN', resource: 'System', ip: '10.0.0.12', status: 'Success' },
    { id: 14, timestamp: '2026-07-27 22:00:00', user: 'system', action: 'DATA_BACKUP', resource: 'Database: Main', ip: 'localhost', status: 'Success' },
    { id: 15, timestamp: '2026-07-27 18:45:10', user: 'admin@omnihr.com', action: 'CREATE_USER', resource: 'User: dev@omnihr.com', ip: '192.168.1.45', status: 'Success' },
  ];

  const filteredLogs = mockAuditLogs.filter(log => {
    const matchSearch = log.user.toLowerCase().includes(auditSearch.toLowerCase()) || log.action.toLowerCase().includes(auditSearch.toLowerCase());
    const matchAction = auditAction ? log.action === auditAction : true;
    return matchSearch && matchAction;
  });

  const getLogStatusBadge = (status) => {
    switch (status) {
      case 'Success': return <span className="badge badge-success">{status}</span>;
      case 'Warning': return <span className="badge badge-warning">{status}</span>;
      case 'Failed': return <span className="badge badge-danger">{status}</span>;
      default: return <span className="badge badge-muted">{status}</span>;
    }
  };

  const handleDownloadCsv = () => {
    const csvContent = "data:text/csv;charset=utf-8,Timestamp,User,Action,Resource,IP Address,Status\n" 
      + filteredLogs.map(e => `${e.timestamp},${e.user},${e.action},${e.resource},${e.ip},${e.status}`).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "audit_logs.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="page-body">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="page-title">Compliance & Security Center</h1>
          <p className="page-subtitle">Monitor security events, compliance frameworks, and access controls.</p>
        </div>
      </div>

      <div className="tab-bar">
        <button className={`tab-item ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={`tab-item ${activeTab === 'auditlog' ? 'active' : ''}`} onClick={() => setActiveTab('auditlog')}>Audit Log</button>
        <button className={`tab-item ${activeTab === 'dataprivacy' ? 'active' : ''}`} onClick={() => setActiveTab('dataprivacy')}>Data Privacy</button>
        <button className={`tab-item ${activeTab === 'accesscontrol' ? 'active' : ''}`} onClick={() => setActiveTab('accesscontrol')}>Access Control</button>
      </div>

      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Framework Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '24px' }}>
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <ShieldCheck size={32} color="#10b981" />
                <span className="badge badge-success">Active</span>
              </div>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 4px 0' }}>SOC 2 Type II</h3>
                <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#1e293b' }}>98.4%</div>
              </div>
              <div>
                <div style={{ width: '100%', height: '8px', backgroundColor: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: '98.4%', height: '100%', backgroundColor: '#10b981' }}></div>
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>Last audited: March 2026</div>
              </div>
              <button className="btn btn-ghost btn-sm" style={{ width: '100%' }}>View Report</button>
            </div>

            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Lock size={32} color="#3b82f6" />
                <span className="badge badge-success">Certified</span>
              </div>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 4px 0' }}>ISO 27001</h3>
                <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#1e293b' }}>96.1%</div>
              </div>
              <div>
                <div style={{ width: '100%', height: '8px', backgroundColor: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: '96.1%', height: '100%', backgroundColor: '#3b82f6' }}></div>
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>Certified until Dec 2026</div>
              </div>
              <button className="btn btn-ghost btn-sm" style={{ width: '100%' }}>View Report</button>
            </div>

            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Globe size={32} color="#8b5cf6" />
                <span className="badge badge-success">Compliant</span>
              </div>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 4px 0' }}>GDPR</h3>
                <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#1e293b' }}>99.2%</div>
              </div>
              <div>
                <div style={{ width: '100%', height: '8px', backgroundColor: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: '99.2%', height: '100%', backgroundColor: '#8b5cf6' }}></div>
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>All 27 EU countries covered</div>
              </div>
              <button className="btn btn-ghost btn-sm" style={{ width: '100%' }}>View Report</button>
            </div>

            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Award size={32} color="#f59e0b" />
                <span className="badge badge-success">Certified</span>
              </div>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 4px 0' }}>ISO 9001</h3>
                <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#1e293b' }}>97.8%</div>
              </div>
              <div>
                <div style={{ width: '100%', height: '8px', backgroundColor: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: '97.8%', height: '100%', backgroundColor: '#f59e0b' }}></div>
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>Quality management certified</div>
              </div>
              <button className="btn btn-ghost btn-sm" style={{ width: '100%' }}>View Report</button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
            <div className="card">
              <h3 className="section-label">Security KPIs</h3>
              <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                <div className="kpi-card danger">
                  <div className="kpi-label">Failed Login Attempts (24h)</div>
                  <div className="kpi-value">12</div>
                </div>
                <div className="kpi-card success">
                  <div className="kpi-label">Active Sessions</div>
                  <div className="kpi-value">2,847</div>
                </div>
                <div className="kpi-card info">
                  <div className="kpi-label">MFA Adoption</div>
                  <div className="kpi-value">94.2%</div>
                </div>
                <div className="kpi-card success">
                  <div className="kpi-label">Data Encrypted</div>
                  <div className="kpi-value">100%</div>
                </div>
              </div>
            </div>

            <div className="card">
              <h3 className="section-label">Compliance Calendar</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ backgroundColor: '#fef2f2', padding: '8px', borderRadius: '8px' }}><Calendar size={20} color="#ef4444" /></div>
                  <div>
                    <div style={{ fontWeight: 500 }}>UK PAYE Filing</div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>Due: July 31, 2026</div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ backgroundColor: '#fffbeb', padding: '8px', borderRadius: '8px' }}><Calendar size={20} color="#f59e0b" /></div>
                  <div>
                    <div style={{ fontWeight: 500 }}>France DSN</div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>Due: August 5, 2026</div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ backgroundColor: '#f8fafc', padding: '8px', borderRadius: '8px' }}><Calendar size={20} color="#64748b" /></div>
                  <div>
                    <div style={{ fontWeight: 500 }}>US 941 Q3</div>
                    <div style={{ fontSize: '12px', color: '#64748b' }}>Due: August 15, 2026</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="section-label">Recent Security Events</h3>
            <table className="dt-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event</th>
                  <th>User</th>
                  <th>IP Address</th>
                  <th>Severity</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>2026-07-29 01:25:10</td>
                  <td>Multiple Failed Logins</td>
                  <td>unknown</td>
                  <td>45.22.11.9</td>
                  <td><span className="badge badge-danger">High</span></td>
                </tr>
                <tr>
                  <td>2026-07-28 20:15:22</td>
                  <td>Mass Data Export</td>
                  <td>admin@omnihr.com</td>
                  <td>192.168.1.45</td>
                  <td><span className="badge badge-warning">Medium</span></td>
                </tr>
                <tr>
                  <td>2026-07-28 12:10:00</td>
                  <td>Role Permission Change</td>
                  <td>admin@omnihr.com</td>
                  <td>192.168.1.45</td>
                  <td><span className="badge badge-warning">Medium</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'auditlog' && (
        <div className="card">
          <div className="dt-wrapper">
            <div className="dt-toolbar">
              <div className="dt-search">
                <Search size={16} />
                <input 
                  type="text" 
                  placeholder="Search user or action..." 
                  className="form-input" 
                  value={auditSearch}
                  onChange={(e) => setAuditSearch(e.target.value)}
                />
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <select className="form-select" value={auditAction} onChange={(e) => setAuditAction(e.target.value)}>
                  <option value="">All Actions</option>
                  <option value="LOGIN">LOGIN</option>
                  <option value="LOGIN_FAILED">LOGIN_FAILED</option>
                  <option value="CREATE_EMPLOYEE">CREATE_EMPLOYEE</option>
                  <option value="PAYROLL_RUN">PAYROLL_RUN</option>
                  <option value="EXPORT_DATA">EXPORT_DATA</option>
                </select>
                <input type="date" className="form-input" />
                <input type="date" className="form-input" />
                <button className="btn btn-secondary" onClick={handleDownloadCsv}>
                  <Download size={16} style={{ marginRight: '8px' }} /> Export CSV
                </button>
              </div>
            </div>

            <table className="dt-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>IP Address</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map(log => (
                  <tr key={log.id}>
                    <td>{log.timestamp}</td>
                    <td>{log.user}</td>
                    <td style={{ fontWeight: 500 }}>{log.action}</td>
                    <td>{log.resource}</td>
                    <td>{log.ip}</td>
                    <td>{getLogStatusBadge(log.status)}</td>
                  </tr>
                ))}
                {filteredLogs.length === 0 && (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '32px', color: '#64748b' }}>No audit logs found.</td>
                  </tr>
                )}
              </tbody>
            </table>
            
            {/* Simple pagination footer for visual consistency */}
            <div className="dt-footer">
              <div style={{ fontSize: '14px', color: '#64748b' }}>
                Showing 1 to {filteredLogs.length} of {filteredLogs.length} entries
              </div>
              <div className="pagination">
                <button className="page-btn" disabled><ChevronLeft size={16} /></button>
                <button className="page-btn active">1</button>
                <button className="page-btn" disabled><ChevronRight size={16} /></button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'dataprivacy' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="card">
            <h3 className="section-label">Data Residency</h3>
            <table className="dt-table">
              <thead>
                <tr>
                  <th>Country</th>
                  <th>Entity</th>
                  <th>Data Categories</th>
                  <th>Legal Basis</th>
                  <th>Retention Period</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Germany (EU)</td>
                  <td>OmniHR GmbH</td>
                  <td>PII, Financial, Health</td>
                  <td>Legitimate Interest, Consent</td>
                  <td>7 Years</td>
                </tr>
                <tr>
                  <td>United States</td>
                  <td>OmniHR Inc.</td>
                  <td>PII, Financial</td>
                  <td>Contract Performance</td>
                  <td>7 Years</td>
                </tr>
                <tr>
                  <td>Singapore</td>
                  <td>OmniHR APAC Pte Ltd</td>
                  <td>PII</td>
                  <td>Legitimate Interest</td>
                  <td>5 Years</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div className="card">
              <h3 className="section-label">GDPR Subject Rights Requests</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {[
                  { id: 'REQ-101', type: 'Right to Access', subject: 'John Doe', status: 'Pending', daysLeft: 12 },
                  { id: 'REQ-102', type: 'Right to Erasure', subject: 'Jane Smith', status: 'In Progress', daysLeft: 4 },
                  { id: 'REQ-103', type: 'Right to Portability', subject: 'Alice Johnson', status: 'Completed', daysLeft: 0 },
                  { id: 'REQ-104', type: 'Right to Access', subject: 'Bob Williams', status: 'Pending', daysLeft: 20 },
                  { id: 'REQ-105', type: 'Right to Rectification', subject: 'Eve Brown', status: 'Completed', daysLeft: 0 }
                ].map(req => (
                  <div key={req.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                    <div>
                      <div style={{ fontWeight: 500 }}>{req.type}</div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>{req.subject} • {req.id}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span className={`badge ${req.status === 'Completed' ? 'badge-success' : req.status === 'In Progress' ? 'badge-warning' : 'badge-info'}`}>
                        {req.status}
                      </span>
                      {req.daysLeft > 0 && <div style={{ fontSize: '12px', color: '#ef4444', marginTop: '4px' }}>{req.daysLeft} days left</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <h3 className="section-label">Data Processing Activities</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[
                  { activity: 'Payroll Processing', basis: 'Contract' },
                  { activity: 'Performance Management', basis: 'Legitimate Interest' },
                  { activity: 'Employee Onboarding', basis: 'Contract' },
                  { activity: 'Benefits Administration', basis: 'Contract' },
                  { activity: 'Employee Survey Analytics', basis: 'Consent' }
                ].map((item, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', backgroundColor: '#f8fafc', borderRadius: '8px' }}>
                    <span style={{ fontWeight: 500, color: '#334155' }}>{item.activity}</span>
                    <span style={{ color: '#64748b', fontSize: '14px' }}>{item.basis}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'accesscontrol' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="card">
            <h3 className="section-label">Role Permission Matrix</h3>
            <div style={{ overflowX: 'auto' }}>
              <table className="dt-table" style={{ minWidth: '800px' }}>
                <thead>
                  <tr>
                    <th>Role</th>
                    <th>Dashboard</th>
                    <th>Core HR</th>
                    <th>Payroll</th>
                    <th>Attendance</th>
                    <th>ATS</th>
                    <th>Performance</th>
                    <th>Compliance</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { role: 'Super Admin', perms: ['full', 'full', 'full', 'full', 'full', 'full', 'full'] },
                    { role: 'HR Manager', perms: ['full', 'full', 'full', 'full', 'full', 'full', 'read'] },
                    { role: 'Payroll Admin', perms: ['full', 'read', 'full', 'read', 'none', 'none', 'none'] },
                    { role: 'Recruiter', perms: ['read', 'read', 'none', 'none', 'full', 'none', 'none'] },
                    { role: 'Employee', perms: ['read', 'read', 'read', 'read', 'none', 'read', 'none'] }
                  ].map((row, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 500 }}>{row.role}</td>
                      {row.perms.map((p, j) => (
                        <td key={j} style={{ textAlign: 'center' }}>
                          {p === 'full' ? <span style={{ color: '#10b981', fontWeight: 'bold' }}>✓ Full</span> :
                           p === 'read' ? <span style={{ color: '#3b82f6' }}>⊘ Read</span> :
                           <span style={{ color: '#94a3b8' }}>—</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div className="card">
              <h3 className="section-label">Active Users by Role</h3>
              <table className="dt-table">
                <thead>
                  <tr>
                    <th>Role</th>
                    <th>User Count</th>
                    <th>Last Active</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Super Admin</td>
                    <td>3</td>
                    <td>Just now</td>
                  </tr>
                  <tr>
                    <td>HR Manager</td>
                    <td>12</td>
                    <td>5 mins ago</td>
                  </tr>
                  <tr>
                    <td>Payroll Admin</td>
                    <td>5</td>
                    <td>1 hour ago</td>
                  </tr>
                  <tr>
                    <td>Recruiter</td>
                    <td>8</td>
                    <td>12 mins ago</td>
                  </tr>
                  <tr>
                    <td>Employee</td>
                    <td>60,819</td>
                    <td>Just now</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="card">
              <h3 className="section-label">Suspicious Access Attempts</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div className="alert alert-danger" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <AlertTriangle size={20} />
                  <div>
                    <div style={{ fontWeight: 500 }}>Multiple failed logins from unknown IP</div>
                    <div style={{ fontSize: '12px', marginTop: '4px' }}>45.22.11.9 (Russia) • 25 attempts in 5 mins</div>
                  </div>
                </div>
                <div className="alert alert-warning" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <ShieldAlert size={20} />
                  <div>
                    <div style={{ fontWeight: 500 }}>Unusual data export volume</div>
                    <div style={{ fontSize: '12px', marginTop: '4px' }}>admin@omnihr.com • 500,000 rows exported</div>
                  </div>
                </div>
                <div className="alert alert-info" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <Clock size={20} />
                  <div>
                    <div style={{ fontWeight: 500 }}>Login outside business hours</div>
                    <div style={{ fontSize: '12px', marginTop: '4px' }}>finance@omnihr.com • 03:15 AM local time</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
