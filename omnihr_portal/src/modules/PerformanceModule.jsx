import React, { useState } from 'react';
import { MOCK_PERFORMANCE } from '../data/mockHrmsData';
import { StatusBadge } from '../components/common/StatusBadge';
import { Award, Grid, Target, CheckCircle2 } from 'lucide-react';

export const PerformanceModule = () => {
  const [selectedQuad, setSelectedQuad] = useState<string | null>(null);

  const gridMatrix = [
    [
      { label: 'High Potential / Low Perf', key: '2x1' },
      { label: 'High Potential / Med Perf', key: '2x2' },
      { label: '★ STAR (High Pot / High Perf)', key: 'STAR' }
    ],
    [
      { label: 'Med Potential / Low Perf', key: '1x1' },
      { label: 'Core Performer (Med/Med)', key: 'CORE_PERFORMER' },
      { label: 'High Performer (Med Pot / High Perf)', key: 'HIGH_PERFORMER' }
    ],
    [
      { label: 'Low Potential / Low Perf', key: 'RISK' },
      { label: 'Solid Professional', key: 'SOLID' },
      { label: 'High Contributor', key: 'CONTRIBUTOR' }
    ]
  ];

  return (
    <div className="space-y-6 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            Workday Style 360 Feedback &amp; 9-Box Matrix
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">9-Box Talent Calibration &amp; OKRs</h2>
        </div>
      </div>

      {/* 9-Box Grid */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Grid className="w-4 h-4 text-indigo-400" /> Workday 9-Box Talent Calibration Matrix
          </h3>
          {selectedQuad && (
            <button onClick={() => setSelectedQuad(null)} className="text-xs font-mono text-indigo-400 hover:underline">
              Reset Filter
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-3">
          {gridMatrix.flat().map((q) => {
            const isSelected = selectedQuad === q.key;
            return (
              <div
                key={q.key}
                onClick={() => setSelectedQuad(q.key)}
                className={`p-4 rounded-xl border text-xs cursor-pointer transition-all min-h-[90px] flex flex-col justify-between ${
                  q.key === 'STAR' ? 'bg-indigo-950/40 border-indigo-500/50 hover:bg-indigo-900/50' :
                  isSelected ? 'bg-slate-800 border-indigo-400' : 'bg-[#0A0E1A] border-slate-800 hover:border-slate-700'
                }`}
              >
                <span className={`font-bold block ${q.key === 'STAR' ? 'text-indigo-300' : 'text-slate-200'}`}>
                  {q.label}
                </span>
                <span className="text-[10px] font-mono text-slate-500">Key: {q.key}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* OKR Hierarchy */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Target className="w-4 h-4 text-emerald-400" /> Enterprise OKR Alignment Tree
        </h3>

        <div className="space-y-3 font-mono text-xs">
          {MOCK_PERFORMANCE.okrs.map((okr, idx) => (
            <div key={idx} className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-bold text-white">{okr.title}</span>
                <span className="text-emerald-400 font-bold">{okr.progress}% Completed</span>
              </div>
              <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                <div style={{ width: `${okr.progress}%` }} className="bg-emerald-500 h-full" />
              </div>
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>Owner: {okr.owner}</span>
                <span>Unit: {okr.category}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
