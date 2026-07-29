import React, { useState } from 'react';
import { MOCK_ATS_CANDIDATES } from '../data/mockHrmsData';
import { StatusBadge } from '../components/common/StatusBadge';
import { Briefcase, UserPlus, CheckCircle2, FileSignature, Sparkles } from 'lucide-react';

export const AtsModule = () => {
  const [candidates, setCandidates] = useState(MOCK_ATS_CANDIDATES);

  const stages = ['APPLIED', 'SCREENED', 'INTERVIEW', 'OFFER', 'HIRED'];

  const moveStage = (candId, nextStage) => {
    setCandidates((prev) =>
      prev.map((c) => (c.id === candId ? { ...c, stage: nextStage } : c))
    );
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            BambooHR Enterprise ATS Pipeline
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">Recruitment Kanban &amp; AI Candidate Scoring</h2>
        </div>

        <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20">
          <UserPlus className="w-4 h-4" /> Create Requisition
        </button>
      </div>

      {/* Kanban Board */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-300" /> Interactive Candidate Kanban Pipeline
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {stages.map((stg) => {
            const list = candidates.filter((c) => c.stage === stg);
            return (
              <div key={stg} className="bg-[#0A0E1A] border border-slate-800 rounded-xl p-3 space-y-3">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800 text-xs">
                  <span className="font-bold text-slate-300 font-mono text-[11px]">{stg}</span>
                  <span className="text-[10px] font-mono text-indigo-400 font-bold bg-indigo-500/10 px-2 py-0.5 rounded">
                    {list.length}
                  </span>
                </div>

                <div className="space-y-2">
                  {list.map((cand) => (
                    <div key={cand.id} className="bg-[#111827] border border-slate-800 p-3 rounded-xl text-xs space-y-2 hover:border-indigo-500/50 transition-all">
                      <div>
                        <span className="font-bold text-white block">{cand.name}</span>
                        <span className="text-[10px] text-slate-400 block">{cand.targetRole}</span>
                      </div>

                      <div className="flex justify-between items-center text-[10px] font-mono">
                        <span className="text-slate-500">{cand.expYears} yrs exp</span>
                        <span className="text-emerald-400 font-bold">{cand.matchScore}% AI Match</span>
                      </div>

                      {/* Advance Stage Control */}
                      <div className="pt-2 border-t border-slate-800/60 flex justify-between gap-1">
                        {stages.indexOf(stg) < stages.length - 1 && (
                          <button
                            onClick={() => moveStage(cand.id, stages[stages.indexOf(stg) + 1])}
                            className="w-full bg-slate-900 hover:bg-indigo-600 hover:text-white text-slate-400 py-1 rounded text-[10px] font-mono transition-all"
                          >
                            Advance →
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                  {list.length === 0 && (
                    <div className="text-center p-4 text-[10px] text-slate-600 font-mono">No candidates</div>
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
