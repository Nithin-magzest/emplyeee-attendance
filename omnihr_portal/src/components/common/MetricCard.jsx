import React from 'react';

export const MetricCard = ({ title, value, subtitle, icon: Icon, color = "indigo", badgeText }) => {
  const colorStyles = {
    indigo: "bg-indigo-500/10 border-indigo-500/30 text-indigo-400",
    emerald: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    amber: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    cyan: "bg-cyan-500/10 border-cyan-500/30 text-cyan-400",
    rose: "bg-rose-500/10 border-rose-500/30 text-rose-400"
  };

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between hover:border-slate-700 transition-all">
      <div className="flex justify-between items-start mb-3">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{title}</span>
        {Icon && (
          <div className={`p-2.5 rounded-xl border ${colorStyles[color] || colorStyles.indigo}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div>
        <div className="flex items-baseline justify-between gap-2 mb-1">
          <span className="text-2xl font-black text-white font-mono tracking-tight">{value}</span>
          {badgeText && (
            <span className="text-[10px] font-mono font-bold bg-slate-900 border border-slate-800 text-slate-300 px-2 py-0.5 rounded-full">
              {badgeText}
            </span>
          )}
        </div>
        {subtitle && <span className="text-[11px] text-slate-400 font-medium">{subtitle}</span>}
      </div>
    </div>
  );
};
