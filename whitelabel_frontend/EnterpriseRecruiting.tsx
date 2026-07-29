import React, { useState } from 'react';
import {
  Briefcase,
  UserPlus,
  CheckCircle2,
  Calendar,
  FileSignature,
  Layers
} from 'lucide-react';

interface Candidate {
  id: string;
  name: string;
  targetRole: string;
  stage: 'APPLIED' | 'SCREENED' | 'INTERVIEW' | 'OFFER' | 'HIRED';
  matchScore: number;
}

export const EnterpriseRecruiting: React.FC = () => {
  const [candidates] = useState<Candidate[]>([
    { id: 'C-901', name: 'Alexander Wright', targetRole: 'Sr. Staff Distributed Engineer', stage: 'INTERVIEW', matchScore: 96 },
    { id: 'C-902', name: 'Sophia Chen', targetRole: 'Director of AI Ethics & Policy', stage: 'OFFER', matchScore: 98 },
    { id: 'C-903', name: 'Dimitri Rostov', targetRole: 'Lead Security Automation Engineer', stage: 'SCREENED', matchScore: 92 },
    { id: 'C-904', name: 'Hannah Abbott', targetRole: 'VP of Global Enterprise Sales', stage: 'HIRED', matchScore: 95 }
  ]);

  const stages: Candidate['stage'][] = ['APPLIED', 'SCREENED', 'INTERVIEW', 'OFFER', 'HIRED'];

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 font-sans p-6 sm:p-8 space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-indigo-400" /> Enterprise ATS &amp; Recruiting Pipeline
          </h1>
          <p className="text-xs text-slate-400">Headcount requisition workflows, AI candidate matching &amp; e-signature offer letters</p>
        </div>

        <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20">
          <UserPlus className="w-4 h-4" /> Create Headcount Requisition
        </button>
      </header>

      {/* Headcount Requisition Approval Workflow */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" /> Active Headcount Requisition Chain
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs font-mono">
          {[
            { step: '1. HC Plan Audit', status: 'APPROVED', date: 'Jul 10' },
            { step: '2. Finance Sign-off', status: 'APPROVED', date: 'Jul 12' },
            { step: '3. HRBP Approval', status: 'APPROVED', date: 'Jul 14' },
            { step: '4. Hiring Mgr Launch', status: 'ACTIVE IN MARKET', date: 'Jul 15' }
          ].map((s, i) => (
            <div key={i} className="bg-[#0A0E1A] border border-slate-800 p-3 rounded-xl space-y-1">
              <span className="text-slate-400 block">{s.step}</span>
              <span className="text-emerald-400 font-bold block">{s.status}</span>
              <span className="text-[10px] text-slate-500">{s.date}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Candidate Pipeline Kanban Board */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white mb-2">Active Recruiting Pipeline Kanban</h3>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {stages.map((stg) => {
            const list = candidates.filter((c) => c.stage === stg);
            return (
              <div key={stg} className="bg-[#0A0E1A] border border-slate-800/80 rounded-xl p-3 space-y-3">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800 text-xs">
                  <span className="font-bold text-slate-300 font-mono text-[11px]">{stg}</span>
                  <span className="text-[10px] font-mono text-indigo-400 font-bold bg-indigo-500/10 px-2 py-0.5 rounded">
                    {list.length}
                  </span>
                </div>

                <div className="space-y-2">
                  {list.map((cand) => (
                    <div key={cand.id} className="bg-[#111827] border border-slate-800 p-3 rounded-xl text-xs space-y-1 hover:border-indigo-500/50 transition-all">
                      <span className="font-bold text-white block">{cand.name}</span>
                      <span className="text-[11px] text-slate-400 block">{cand.targetRole}</span>
                      <div className="flex justify-between items-center pt-1 text-[10px] font-mono">
                        <span className="text-slate-500">{cand.id}</span>
                        <span className="text-emerald-400 font-bold">{cand.matchScore}% Match</span>
                      </div>
                    </div>
                  ))}
                  {list.length === 0 && (
                    <div className="text-center p-4 text-[11px] text-slate-600 font-mono">No candidates</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
