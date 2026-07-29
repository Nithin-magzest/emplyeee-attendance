import React from 'react';
import {
  LayoutDashboard,
  Users,
  DollarSign,
  Clock,
  Briefcase,
  Award,
  Zap,
  BarChart2,
  Smartphone,
  ShieldAlert,
  Sparkles
} from 'lucide-react';

export const Sidebar = ({ activeModule, setActiveModule, onOpenMobileSim, onOpenAiBot }) => {
  const modules = [
    { id: 'dashboard', label: 'Executive Tower', icon: LayoutDashboard, badge: 'Live' },
    { id: 'corehr', label: 'Core HR & Org Tree', icon: Users, badge: 'Rippling' },
    { id: 'payroll', label: 'Global Payroll & EWA', icon: DollarSign, badge: 'Gusto/Deel' },
    { id: 'attendance', label: 'Time & Attendance', icon: Clock, badge: 'Biometric' },
    { id: 'ats', label: 'ATS Recruiting', icon: Briefcase, badge: 'Kanban' },
    { id: 'performance', label: 'Performance 9-Box', icon: Award, badge: 'Workday' },
    { id: 'automations', label: 'AI Workflow Engine', icon: Zap, badge: 'Prompt' },
    { id: 'analytics', label: 'Workforce Analytics', icon: BarChart2, badge: 'SVG' }
  ];

  return (
    <aside className="w-64 bg-[#0F172A] border-r border-slate-800 flex flex-col justify-between shrink-0 font-sans hidden md:flex">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-400 text-white font-bold flex items-center justify-center font-mono text-lg shadow-lg shadow-indigo-500/20">
              OH
            </div>
            <div>
              <h1 className="text-base font-black text-white tracking-tight flex items-center gap-1.5">
                OmniHR <span className="text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.2 rounded uppercase">Premier</span>
              </h1>
              <p className="text-[11px] text-slate-400 font-mono">60,000+ Scale HRMS</p>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {modules.map((m) => {
            const Icon = m.icon;
            const isActive = activeModule === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setActiveModule(m.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{m.label}</span>
                </div>
                {m.badge && (
                  <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase ${
                    isActive ? 'bg-indigo-700 text-indigo-100 border-indigo-500' : 'bg-slate-900 text-slate-500 border-slate-800'
                  }`}>
                    {m.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Action Footer */}
      <div className="p-4 border-t border-slate-800 space-y-2 bg-[#0A0E1A]/50">
        <button
          onClick={onOpenAiBot}
          className="w-full bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white text-xs font-bold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-all"
        >
          <Sparkles className="w-4 h-4 text-amber-300 animate-pulse" /> OmniAI HR Bot
        </button>

        <button
          onClick={onOpenMobileSim}
          className="w-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-bold py-2 px-3 rounded-xl flex items-center justify-center gap-2 transition-all"
        >
          <Smartphone className="w-3.5 h-3.5 text-cyan-400" /> Mobile ESS Preview
        </button>
      </div>
    </aside>
  );
};
