import React from 'react';

export const StatusBadge = ({ status, text }) => {
  const normalized = (status || text || '').toUpperCase();

  let style = "bg-slate-800 text-slate-300 border-slate-700";

  if (["ACTIVE", "AUDITED", "APPROVED", "COMPLIANT", "CERTIFIED", "PUNCHED_IN", "HIRED"].includes(normalized)) {
    style = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  } else if (["PENDING", "ON_LEAVE", "MEDIUM", "VARIANCE_FLAGGED", "INTERVIEW", "CALCULATING"].includes(normalized)) {
    style = "bg-amber-500/10 text-amber-400 border-amber-500/30";
  } else if (["HIGH", "CRITICAL", "BLOCKED", "OFFBOARDING", "FLAGGED", "EXCEEDED"].includes(normalized)) {
    style = "bg-rose-500/10 text-rose-400 border-rose-500/30";
  }

  return (
    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase border inline-block ${style}`}>
      {text || status}
    </span>
  );
};
