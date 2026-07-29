import React, { useState } from 'react';
import {
  Award,
  Grid,
  Users,
  TrendingUp,
  Target,
  ChevronRight,
  UserCheck
} from 'lucide-react';

interface NineBoxEmployee {
  id: string;
  name: string;
  title: string;
  quadrant: string; // e.g. "STAR", "HIGH_PERFORMER"
  perfRating: number; // 1-3
  potRating: number;  // 1-3
}

export const TalentPerformance: React.FC = () => {
  const [selectedQuadrant, setSelectedQuadrant] = useState<string | null>(null);

  const employees: NineBoxEmployee[] = [
    { id: 'E1', name: 'Dr. Evelyn Vance', title: 'VP of Distributed Infra', quadrant: 'STAR (3x3)', perfRating: 3, potRating: 3 },
    { id: 'E2', name: 'Marcus Sterling', title: 'Principal SecOps Architect', quadrant: 'HIGH PERFORMER (3x2)', perfRating: 3, potRating: 2 },
    { id: 'E3', name: 'Priya Sharma', title: 'Staff ML Engineer', quadrant: 'HIGH POTENTIAL (2x3)', perfRating: 2, potRating: 3 },
    { id: 'E4', name: 'Kaelen Rivera', title: 'Enterprise AE', quadrant: 'CORE PERFORMER (2x2)', perfRating: 2, potRating: 2 }
  ];

  const gridMatrix = [
    [
      { label: 'High Potential / Low Perf', pot: 3, perf: 1, key: '2x1' },
      { label: 'High Potential / Med Perf', pot: 3, perf: 2, key: '2x2' },
      { label: '★ STAR (High Pot / High Perf)', pot: 3, perf: 3, key: 'STAR' }
    ],
    [
      { label: 'Med Potential / Low Perf', pot: 2, perf: 1, key: '1x1' },
      { label: 'Core Performer (Med/Med)', pot: 2, perf: 2, key: 'CORE' },
      { label: 'High Performer (Med Pot / High Perf)', pot: 2, perf: 3, key: 'HIGH_PERF' }
    ],
    [
      { label: 'Low Potential / Low Perf', pot: 1, perf: 1, key: 'RISK' },
      { label: 'Solid Professional (Low Pot / Med Perf)', pot: 1, perf: 2, key: 'SOLID' },
      { label: 'High Contributor (Low Pot / High Perf)', pot: 1, perf: 3, key: 'CONTRIBUTOR' }
    ]
  ];

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 font-sans p-6 sm:p-8 space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <Award className="w-6 h-6 text-amber-400" /> Talent Management &amp; Performance
          </h1>
          <p className="text-xs text-slate-400">9-Box Calibration Matrix, Succession Planning &amp; OKR Alignment</p>
        </div>

        <div className="flex gap-2">
          <button className="bg-slate-900 border border-slate-800 text-slate-300 font-bold px-4 py-2 rounded-xl text-xs">
            Export Calibration Stack
          </button>
        </div>
      </header>

      {/* Interactive 9-Box Grid */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Grid className="w-4 h-4 text-indigo-400" /> Executive 9-Box Talent Matrix
            </h3>
            <p className="text-xs text-slate-400">Click any quadrant to view filtered executive talent roster</p>
          </div>
          {selectedQuadrant && (
            <button
              onClick={() => setSelectedQuadrant(null)}
              className="text-xs font-mono text-indigo-400 hover:underline"
            >
              Reset Quadrant Filter
            </button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-3 pt-2">
          {gridMatrix.flat().map((q) => {
            const isSelected = selectedQuadrant === q.key;
            return (
              <div
                key={q.key}
                onClick={() => setSelectedQuadrant(q.key)}
                className={`p-4 rounded-xl border text-xs cursor-pointer transition-all min-h-[100px] flex flex-col justify-between ${
                  q.key === 'STAR' ? 'bg-indigo-950/40 border-indigo-500/50 hover:bg-indigo-900/50' :
                  isSelected ? 'bg-slate-800 border-indigo-400' : 'bg-[#0A0E1A] border-slate-800 hover:border-slate-700'
                }`}
              >
                <span className={`font-bold block ${q.key === 'STAR' ? 'text-indigo-300' : 'text-slate-200'}`}>
                  {q.label}
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  Potential: {q.pot}/3 · Performance: {q.perf}/3
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Succession Planning Table */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <UserCheck className="w-4 h-4 text-emerald-400" /> Critical Role Succession Pipeline
        </h3>

        <div className="overflow-x-auto text-xs">
          <table className="w-full text-left">
            <thead className="bg-[#0A0E1A] text-slate-400 font-bold uppercase text-[10px] border-b border-slate-800">
              <tr>
                <th className="p-3">Critical Executive Role</th>
                <th className="p-3">Incumbent</th>
                <th className="p-3">Ready-Now Successors</th>
                <th className="p-3">Emergency Backfill</th>
                <th className="p-3">Risk Exposure</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {[
                { role: 'VP of Distributed Infrastructure', incumbent: 'Dr. Evelyn Vance', ready: 'Marcus Sterling (100% Ready)', backup: 'Priya Sharma (Ready 1-2 yrs)', risk: 'LOW' },
                { role: 'VP of Global Enterprise Sales', incumbent: 'Hannah Abbott', ready: 'Kaelen Rivera (90% Ready)', backup: 'Alex Rivera (Ready 1 yr)', risk: 'MEDIUM' }
              ].map((s, i) => (
                <tr key={i} className="hover:bg-slate-800/40">
                  <td className="p-3 font-bold text-white">{s.role}</td>
                  <td className="p-3 text-slate-300">{s.incumbent}</td>
                  <td className="p-3 font-mono text-emerald-400">{s.ready}</td>
                  <td className="p-3 font-mono text-slate-400">{s.backup}</td>
                  <td className="p-3 font-mono text-xs font-bold text-emerald-400">{s.risk}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
