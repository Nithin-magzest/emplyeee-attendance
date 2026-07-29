import React, { useState } from 'react';
import { Search, Bell, Globe, Sliders, ShieldCheck, User } from 'lucide-react';
import { MOCK_COMPANY } from '../data/mockHrmsData';

export const Header = ({ onOpenNotif, selectedEntity, setSelectedEntity }) => {
  const [searchTerm, setSearchTerm] = useState('');

  return (
    <header className="h-16 bg-[#0F172A] border-b border-slate-800 px-6 flex items-center justify-between shrink-0 font-sans">
      {/* Global Search Bar */}
      <div className="relative w-full max-w-md">
        <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Global Search (Employees, Payroll, ATS, SecOps, OKRs...)"
          className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl pl-10 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-all"
        />
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Multi-Entity Currency Selector */}
        <div className="flex items-center gap-1.5 bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-1 text-xs">
          <Globe className="w-3.5 h-3.5 text-indigo-400" />
          <select
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
            className="bg-transparent text-slate-200 text-xs font-mono font-bold focus:outline-none cursor-pointer"
          >
            {MOCK_COMPANY.entities.map((ent) => (
              <option key={ent.code} value={ent.code} className="bg-[#111827] text-slate-200">
                {ent.name} ({ent.symbol})
              </option>
            ))}
          </select>
        </div>

        {/* Notifications */}
        <button
          onClick={onOpenNotif}
          className="relative bg-[#0A0E1A] hover:bg-slate-800 border border-slate-800 p-2 rounded-xl text-slate-300 transition-all"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-indigo-500 border-2 border-[#0F172A]" />
        </button>

        {/* User Profile Avatar */}
        <div className="flex items-center gap-3 border-l border-slate-800 pl-4">
          <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white font-mono font-bold text-xs flex items-center justify-center">
            EV
          </div>
          <div className="text-left text-xs hidden sm:block">
            <span className="block font-bold text-white">Dr. Evelyn Vance</span>
            <span className="block text-[10px] text-slate-400 font-mono">VP Infra &amp; Core HR Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
};
