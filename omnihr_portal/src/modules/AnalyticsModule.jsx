import React from 'react';
import { StatusBadge } from '../components/common/StatusBadge';
import { BarChart2, ShieldCheck, Download, Globe, FileText, CheckCircle2 } from 'lucide-react';

export const AnalyticsModule = () => {
  return (
    <div className="space-y-6 font-sans">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            Workforce Intelligence &amp; Governance
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">Analytics &amp; Compliance Governance Center</h2>
        </div>

        <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20">
          <Download className="w-4 h-4" /> Export Audit Report (CSV)
        </button>
      </header>

      {/* Compliance Posture Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { cert: 'GDPR (EU Privacy)', status: 'COMPLIANT', host: 'AWS EU-Central (Frankfurt)' },
          { cert: 'SOC 2 Type II', status: 'COMPLIANT', host: 'AWS US-East (Virginia)' },
          { cert: 'ISO 27001 Security', status: 'CERTIFIED', host: 'AWS EU-West (London)' },
          { cert: 'ISO 9001 Quality', status: 'CERTIFIED', host: 'AWS AP-Southeast (Singapore)' }
        ].map((c, i) => (
          <div key={i} className="bg-[#111827] border border-slate-800 p-5 rounded-2xl space-y-2 shadow-xl">
            <div className="flex justify-between items-start">
              <span className="font-bold text-white text-xs">{c.cert}</span>
              <StatusBadge status={c.status} />
            </div>
            <span className="text-[10px] font-mono text-slate-500 block">{c.host}</span>
          </div>
        ))}
      </div>

      {/* Analytics Summary */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-emerald-400" /> Linear Regression Headcount &amp; Diversity Projections
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-1">
            <span className="text-slate-400 block">Hiring Velocity</span>
            <span className="text-xl font-bold text-white">24.2 Days</span>
            <span className="text-[10px] text-emerald-400 block">8.5 days faster than market median</span>
          </div>

          <div className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-1">
            <span className="text-slate-400 block">Cost Per Hire</span>
            <span className="text-xl font-bold text-emerald-400">$4,250</span>
            <span className="text-[10px] text-slate-500 block">AI Screening Automation active</span>
          </div>

          <div className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-1">
            <span className="text-slate-400 block">2027 Projected Scale</span>
            <span className="text-xl font-bold text-indigo-400">68,400 FTEs</span>
            <span className="text-[10px] text-slate-500 block">+7,553 projected growth</span>
          </div>
        </div>
      </div>
    </div>
  );
};
