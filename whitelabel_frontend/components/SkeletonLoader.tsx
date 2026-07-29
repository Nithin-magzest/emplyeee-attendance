import React from 'react';

export const SkeletonLoader: React.FC<{ type?: 'card' | 'table' | 'profile' }> = ({ type = 'card' }) => {
  if (type === 'table') {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-10 bg-[#111827] border border-slate-800 rounded-xl" />
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-12 bg-[#111827]/60 border border-slate-800/60 rounded-xl" />
        ))}
      </div>
    );
  }

  if (type === 'profile') {
    return (
      <div className="p-6 bg-[#111827] border border-slate-800 rounded-2xl animate-pulse space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-slate-800 rounded-2xl" />
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-slate-800 rounded w-1/3" />
            <div className="h-3 bg-slate-800/60 rounded w-1/4" />
          </div>
        </div>
        <div className="h-20 bg-slate-800/40 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="p-6 bg-[#111827] border border-slate-800 rounded-2xl animate-pulse space-y-4">
      <div className="h-4 bg-slate-800 rounded w-1/4" />
      <div className="h-8 bg-slate-800/60 rounded w-1/2" />
      <div className="h-16 bg-slate-800/30 rounded-xl" />
    </div>
  );
};
