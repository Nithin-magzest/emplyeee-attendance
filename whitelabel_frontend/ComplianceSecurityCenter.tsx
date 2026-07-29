import React, { useState } from 'react';
import {
  ShieldCheck,
  Lock,
  Globe,
  FileText,
  Search,
  CheckCircle2,
  AlertTriangle,
  Server,
  Database,
  Calendar
} from 'lucide-react';

interface AuditLog {
  id: string;
  timestamp: string;
  eventType: string;
  user: string;
  ip: string;
  status: 'SUCCESS' | 'FLAGGED' | 'BLOCKED';
}

export const ComplianceSecurityCenter: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');

  const auditLogs: AuditLog[] = [
    { id: 'LOG-8801', timestamp: '2026-07-29 01:42:05', eventType: 'auth.mfa_step_up', user: 'evelyn.vance@company.com', ip: '198.51.100.42', status: 'SUCCESS' },
    { id: 'LOG-8802', timestamp: '2026-07-29 01:38:12', eventType: 'payroll.bulk_export', user: 'sarah.jenkins@company.com', ip: '198.51.100.10', status: 'SUCCESS' },
    { id: 'LOG-8803', timestamp: '2026-07-29 01:20:44', eventType: 'secops.ip_auto_ban', user: 'SYSTEM_AUTONOMOUS', ip: '185.220.101.5', status: 'BLOCKED' },
    { id: 'LOG-8804', timestamp: '2026-07-29 00:55:01', eventType: 'idor.unauthorized_access', user: 'contractor_99@external.com', ip: '203.0.113.14', status: 'FLAGGED' }
  ];

  const filteredLogs = auditLogs.filter(
    (l) =>
      l.eventType.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.ip.includes(searchTerm)
  );

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 font-sans p-6 sm:p-8 space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-400" /> Compliance &amp; Security Governance Center
          </h1>
          <p className="text-xs text-slate-400">GDPR, SOC 2 Type II, ISO 27001 posture, Data Residency &amp; DB Audit Explorer</p>
        </div>

        <div className="flex items-center gap-2 bg-[#111827] border border-slate-800 px-3.5 py-2 rounded-xl text-xs font-mono">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-300 font-bold">100% Compliance Certification Score</span>
        </div>
      </header>

      {/* Compliance Certification Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { cert: 'GDPR (EU Data Privacy)', status: 'COMPLIANT', audit: 'Audited Jun 2026', region: 'Frankfurt (eu-central-1)' },
          { cert: 'SOC 2 Type II', status: 'COMPLIANT', audit: 'Audited May 2026', region: 'US East (us-east-1)' },
          { cert: 'ISO 27001 Security', status: 'CERTIFIED', audit: 'Audited Apr 2026', region: 'London (eu-west-2)' },
          { cert: 'ISO 9001 Quality Management', status: 'CERTIFIED', audit: 'Audited Jan 2026', region: 'Singapore (ap-southeast-1)' }
        ].map((c, i) => (
          <div key={i} className="bg-[#111827] border border-slate-800 p-5 rounded-2xl space-y-2 shadow-xl">
            <div className="flex justify-between items-start">
              <span className="font-bold text-white text-xs">{c.cert}</span>
              <span className="text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded">
                {c.status}
              </span>
            </div>
            <span className="text-[11px] text-slate-400 block">{c.audit}</span>
            <span className="text-[10px] font-mono text-slate-500 block">Host: {c.region}</span>
          </div>
        ))}
      </div>

      {/* Data Residency Mapping Grid */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Globe className="w-4 h-4 text-indigo-400" /> Enterprise Data Residency &amp; Encryption Map
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          {[
            { entity: 'US Inc. (Delaware)', host: 'AWS US-East (N. Virginia)', db: 'PostgreSQL Multi-AZ (AES-256)' },
            { entity: 'UK Ltd. & DE GmbH', host: 'AWS EU-Central (Frankfurt)', db: 'PostgreSQL GDPR Isolated (AES-256)' },
            { entity: 'SG Pte. & IN Pvt', host: 'AWS AP-Southeast (Singapore)', db: 'PostgreSQL Regional Node (AES-256)' }
          ].map((m, i) => (
            <div key={i} className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-2">
              <span className="font-bold text-white block">{m.entity}</span>
              <span className="text-indigo-400 text-[11px] block">{m.host}</span>
              <span className="text-slate-400 text-[10px] block">{m.db}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Audit Log Explorer */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" /> Database Audit Log Explorer (Real-Time SIEM-Lite Query)
          </h3>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search event, user, IP..."
              className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto text-xs font-mono">
          <table className="w-full text-left">
            <thead className="bg-[#0A0E1A] text-slate-400 uppercase text-[10px] border-b border-slate-800">
              <tr>
                <th className="p-3">Log ID</th>
                <th className="p-3">Timestamp (UTC)</th>
                <th className="p-3">Event Type</th>
                <th className="p-3">Actor Email</th>
                <th className="p-3">Source IP</th>
                <th className="p-3">Verdict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40">
                  <td className="p-3 font-bold text-indigo-400">{log.id}</td>
                  <td className="p-3 text-slate-400">{log.timestamp}</td>
                  <td className="p-3 font-bold text-white">{log.eventType}</td>
                  <td className="p-3 text-slate-300">{log.user}</td>
                  <td className="p-3 text-slate-400">{log.ip}</td>
                  <td className="p-3">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      log.status === 'SUCCESS' ? 'bg-emerald-500/10 text-emerald-400' :
                      log.status === 'BLOCKED' ? 'bg-rose-500/10 text-rose-400' :
                      'bg-amber-500/10 text-amber-400'
                    }`}>
                      {log.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
