import React, { useState } from 'react';
import {
  Clock,
  MapPin,
  Calendar,
  AlertOctagon,
  CheckCircle2,
  Users,
  ChevronRight,
  ShieldCheck,
  Building
} from 'lucide-react';

interface AttendanceLocationHeatmap {
  hub: string;
  totalEmployees: number;
  inOfficePct: number;
  remotePct: number;
  onLeavePct: number;
}

export const WorkforceAttendance: React.FC = () => {
  const [heatmaps] = useState<AttendanceLocationHeatmap[]>([
    { hub: 'New York HQ (US)', totalEmployees: 18400, inOfficePct: 62, remotePct: 32, onLeavePct: 6 },
    { hub: 'London Hub (UK)', totalEmployees: 12100, inOfficePct: 58, remotePct: 36, onLeavePct: 6 },
    { hub: 'Singapore Tech Hub (SG)', totalEmployees: 9400, inOfficePct: 74, remotePct: 22, onLeavePct: 4 },
    { hub: 'Munich R&D (DE)', totalEmployees: 6800, inOfficePct: 52, remotePct: 42, onLeavePct: 6 },
    { hub: 'Bengaluru Development (IN)', totalEmployees: 14147, inOfficePct: 81, remotePct: 15, onLeavePct: 4 }
  ]);

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 font-sans p-6 sm:p-8 space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <Clock className="w-6 h-6 text-indigo-400" /> Workforce Management &amp; Attendance
          </h1>
          <p className="text-xs text-slate-400">Live global location heatmap, roster schedules &amp; multi-level leave approvals</p>
        </div>

        <div className="flex items-center gap-2 bg-[#111827] border border-slate-800 px-3.5 py-2 rounded-xl text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono text-slate-300 font-bold">60,847 Real-Time Telemetry Active</span>
        </div>
      </header>

      {/* Live Location Heatmap */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <MapPin className="w-4 h-4 text-emerald-400" /> Global Work Location Distribution (Today)
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {heatmaps.map((h, i) => (
            <div key={i} className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="font-bold text-slate-200">{h.hub}</span>
                <span className="text-[10px] font-mono text-slate-500">{h.totalEmployees.toLocaleString()} staff</span>
              </div>

              <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden flex">
                <div style={{ width: `${h.inOfficePct}%` }} className="bg-indigo-500 h-full" title={`In Office ${h.inOfficePct}%`} />
                <div style={{ width: `${h.remotePct}%` }} className="bg-cyan-500 h-full" title={`Remote ${h.remotePct}%`} />
                <div style={{ width: `${h.onLeavePct}%` }} className="bg-slate-700 h-full" title={`On Leave ${h.onLeavePct}%`} />
              </div>

              <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-indigo-500" /> Office {h.inOfficePct}%</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500" /> Remote {h.remotePct}%</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-700" /> Leave {h.onLeavePct}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Multi-Level Leave Approval Queue + Overtime Auto-Flag */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Multi-Level Leave Approvals */}
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-indigo-400" /> Multi-Level Leave Approval Escalation Queue
          </h3>

          <div className="space-y-3 text-xs">
            {[
              { emp: 'Marcus Sterling', type: 'Annual Sabbatical (14 days)', level: 'Level 3: Finance Sign-off', status: 'PENDING_FINANCE' },
              { emp: 'Priya Sharma', type: 'Parental Leave (30 days)', level: 'Level 2: HRBP Review', status: 'PENDING_HRBP' }
            ].map((l, idx) => (
              <div key={idx} className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl flex justify-between items-center">
                <div>
                  <span className="font-bold text-white block">{l.emp}</span>
                  <span className="text-slate-400 text-[11px] block">{l.type}</span>
                  <span className="text-[10px] font-mono text-indigo-400 font-bold">{l.level}</span>
                </div>
                <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-3 py-1.5 rounded-lg text-xs">
                  Review Request
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Overtime Auto-Flag Tracker (>48hrs/week) */}
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 text-rose-400" /> Overtime Cap Compliance Tracker (&gt;48 hrs/week)
          </h3>

          <div className="space-y-3 text-xs">
            {[
              { emp: 'Dr. Evelyn Vance', hrs: 52.4, dept: 'Core Platform Engineering', alert: 'EXCEEDS 48H CAP' },
              { emp: 'Kaelen Rivera', hrs: 49.8, dept: 'Global Sales', alert: 'EXCEEDS 48H CAP' }
            ].map((o, idx) => (
              <div key={idx} className="bg-[#0A0E1A] border border-rose-500/30 p-4 rounded-xl flex justify-between items-center">
                <div>
                  <span className="font-bold text-white block">{o.emp}</span>
                  <span className="text-slate-400 text-[11px] block">{o.dept}</span>
                </div>
                <div className="text-right font-mono">
                  <span className="font-bold text-rose-400 block">{o.hrs} hrs/wk</span>
                  <span className="text-[10px] bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded font-bold">{o.alert}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
