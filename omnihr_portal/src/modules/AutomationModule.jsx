import React, { useState } from 'react';
import { MOCK_AUTOMATIONS } from '../data/mockHrmsData';
import { StatusBadge } from '../components/common/StatusBadge';
import { Zap, Sparkles, Plus, Play, CheckCircle2 } from 'lucide-react';

export const AutomationModule = () => {
  const [promptInput, setPromptInput] = useState('');
  const [automations, setAutomations] = useState(MOCK_AUTOMATIONS);

  const handleCreatePromptAutomation = (e) => {
    e.preventDefault();
    if (!promptInput.trim()) return;

    const newAuto = {
      id: `AUTO-${Date.now().toString().slice(-3)}`,
      trigger: `AI Prompt Trigger: "${promptInput}"`,
      action: "Execute prompt-based workflow action",
      status: "ACTIVE",
      executions: 1
    };

    setAutomations([newAuto, ...automations]);
    setPromptInput('');
  };

  return (
    <div className="space-y-6 font-sans">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            Rippling &amp; Personio Style Workflow Builder
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">Prompt-Driven AI Workflow Automation Engine</h2>
        </div>
      </header>

      {/* AI Prompt Automation Creator */}
      <form onSubmit={handleCreatePromptAutomation} className="bg-[#111827] border border-indigo-500/30 rounded-2xl p-6 shadow-xl space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-300 animate-pulse" /> Build New Workflow via Natural Language Prompt
        </h3>

        <div className="flex gap-2">
          <input
            type="text"
            value={promptInput}
            onChange={(e) => setPromptInput(e.target.value)}
            placeholder="e.g. When an employee in Sales submits a 5+ day leave, require VP approval and auto-assign backup AE..."
            className="flex-1 bg-[#0A0E1A] border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-5 py-2.5 rounded-xl text-xs flex items-center gap-1.5 shadow-lg shadow-indigo-600/20 shrink-0"
          >
            <Plus className="w-4 h-4" /> Synthesize Workflow
          </button>
        </div>
      </form>

      {/* Active Workflows Grid */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white mb-2">Active Enterprise Automations ({automations.length})</h3>

        <div className="space-y-3 font-mono text-xs">
          {automations.map((a) => (
            <div key={a.id} className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl flex justify-between items-center gap-4">
              <div className="space-y-1">
                <span className="font-bold text-white block">{a.trigger}</span>
                <span className="text-indigo-400 text-[11px] block font-semibold">Action: {a.action}</span>
                <span className="text-[10px] text-slate-500 block">ID: {a.id} · Executed {a.executions.toLocaleString()} times</span>
              </div>
              <StatusBadge status={a.status} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
