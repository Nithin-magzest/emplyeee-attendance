import React, { useState } from 'react';
import { useTenant } from './TenantContext';
import {
  ShieldAlert,
  Terminal,
  CheckCircle2,
  EyeOff,
  Radio
} from 'lucide-react';

interface AuditLog {
  id: string;
  timestamp: string;
  eventType: string;
  actor: string;
  ipAddress: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  actionTaken: string;
}

export const SecOpsThreatCenter: React.FC = () => {
  const { config } = useTenant();
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');

  const [logs] = useState<AuditLog[]>([
    {
      id: 'log-101',
      timestamp: '11:42:05 AM',
      eventType: 'auth.brute_force_attempt',
      actor: '185.220.101.5',
      ipAddress: '185.220.101.5 (Tor Exit)',
      severity: 'HIGH',
      actionTaken: 'IP Auto-Blocked (24h Ban)'
    },
    {
      id: 'log-102',
      timestamp: '11:38:12 AM',
      eventType: 'rbac.privilege_escalation_blocked',
      actor: 'dev_contractor@partner.com',
      ipAddress: '198.51.100.42',
      severity: 'HIGH',
      actionTaken: 'Session Revoked'
    },
    {
      id: 'log-103',
      timestamp: '11:20:44 AM',
      eventType: 'session.geo_impossible_travel',
      actor: 'marcus.vance@company.com',
      ipAddress: '103.21.244.0 (Singapore -> NYC)',
      severity: 'MEDIUM',
      actionTaken: 'MFA Step-Up Triggered'
    },
    {
      id: 'log-104',
      timestamp: '10:55:01 AM',
      eventType: 'api.rate_limit_exceeded',
      actor: 'api_key_sandbox_94',
      ipAddress: '192.0.2.1',
      severity: 'LOW',
      actionTaken: 'Throttled (429 Too Many Requests)'
    }
  ]);

  const filteredLogs = filterSeverity === 'ALL' 
    ? logs 
    : logs.filter((l) => l.severity === filterSeverity);

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl shadow-2xl space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              SecOps Threat &amp; SIEM Audit Center
              <span className="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-mono px-2 py-0.5 rounded-full uppercase">
                Live Monitoring
              </span>
            </h3>
            <p className="text-xs text-slate-400">Real-time threat intelligence &amp; autonomous SOAR playbook execution</p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-xl text-slate-300">
            Pipeline: <strong className="text-emerald-400">10,420 events/s</strong>
          </div>
          <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-xl text-slate-300">
            CIS Security Score: <strong className="text-indigo-400">96.4%</strong>
          </div>
        </div>
      </div>

      <div className="bg-slate-950 border border-slate-800/80 p-3.5 rounded-2xl flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-slate-300 font-medium">
          <EyeOff className="w-4 h-4 text-amber-400" />
          <span><strong>RBAC Privacy Boundary Active:</strong> SecOps officers cannot access employee salary or payroll data.</span>
        </div>
        <span className="text-[10px] font-mono text-slate-500">Tenant: {config.companyName}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { name: 'Brute Force Auto-Mitigation', status: 'ACTIVE', count: '200 Blocked / 24h', color: 'text-emerald-400' },
          { name: 'Impossible Travel Step-Up MFA', status: 'ACTIVE', count: '3 MFA Challenges', color: 'text-emerald-400' },
          { name: 'Malware ClamAV Stream Scanner', status: 'ACTIVE', count: '0 Threat Vectors', color: 'text-emerald-400' }
        ].map((pb, idx) => (
          <div key={idx} className="bg-slate-950/70 border border-slate-800/70 p-3 rounded-2xl flex justify-between items-center text-xs">
            <div>
              <span className="font-bold text-slate-200 block">{pb.name}</span>
              <span className="text-[11px] text-slate-500 font-mono">{pb.count}</span>
            </div>
            <span className={`text-[10px] font-mono font-bold ${pb.color} flex items-center gap-1`}>
              <CheckCircle2 className="w-3 h-3" /> {pb.status}
            </span>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Terminal className="w-4 h-4 text-indigo-400" /> Real-Time SIEM Audit Event Logs
          </h4>

          <div className="flex gap-1.5 text-[10px] font-mono font-bold">
            {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
              <button
                key={sev}
                onClick={() => setFilterSeverity(sev)}
                className={`px-2.5 py-1 rounded-lg border transition-all ${
                  filterSeverity === sev 
                    ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' 
                    : 'bg-slate-950 border-slate-800 text-slate-500'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {filteredLogs.map((log) => (
            <div key={log.id} className="bg-slate-950 border border-slate-800/80 p-3 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-white">{log.eventType}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    log.severity === 'HIGH' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30' :
                    log.severity === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                    'bg-slate-800 text-slate-400'
                  }`}>
                    {log.severity}
                  </span>
                </div>
                <span className="text-[11px] text-slate-400 block font-mono">Actor: {log.actor} ({log.ipAddress})</span>
              </div>

              <div className="text-right shrink-0">
                <span className="text-emerald-400 font-mono text-[11px] font-bold block">{log.actionTaken}</span>
                <span className="text-slate-500 text-[10px]">{log.timestamp}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
};
