import React from 'react';
import { MetricCard } from '../components/common/MetricCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { MOCK_COMPANY } from '../data/mockHrmsData';
import { Users, UserPlus, ShieldCheck, DollarSign, TrendingUp, Clock, Calendar, ArrowUpRight } from 'lucide-react';

export const DashboardModule = () => {
  return (
    <div className="space-y-6 font-sans">
      {/* Module Title */}
      <div className="flex justify-between items-center pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            MagHR Premier Global Control Tower
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">Executive Headcount &amp; Operations</h2>
        </div>

        <div className="flex items-center gap-2 bg-[#111827] border border-slate-800 px-3.5 py-2 rounded-xl text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono text-slate-300 font-bold">5 Entities Synchronized</span>
        </div>
      </div>

      {/* KPI Cards Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Global Headcount"
          value="60,847"
          subtitle="+4.2% YTD expansion"
          icon={Users}
          color="indigo"
          badgeText="60k+ Scale"
        />
        <MetricCard
          title="New Hires YTD"
          value="1,247"
          subtitle="98.4% accept rate"
          icon={UserPlus}
          color="emerald"
          badgeText="Onboarding"
        />
        <MetricCard
          title="Retention Rate"
          value="94.2%"
          subtitle="vs 91.8% industry median"
          icon={ShieldCheck}
          color="cyan"
          badgeText="Darwinbox ML"
        />
        <MetricCard
          title="Annual Payroll Spend"
          value="$4.2 Billion"
          subtitle="5 Legal Entities processed"
          icon={DollarSign}
          color="amber"
          badgeText="Deel / Gusto"
        />
      </div>

      {/* Main Grid: Attrition Forecast & Quick Action Items */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Attrition Risk Forecast Card */}
        <div className="lg:col-span-2 bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" /> Predictive Workforce Attrition Risk (Darwinbox AI)
              </h3>
              <p className="text-xs text-slate-400">ML risk scoring evaluating workload, overtime caps &amp; engagement signals</p>
            </div>
            <StatusBadge status="STABLE (-0.8% next qtr)" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-slate-400 text-xs block">Low Risk Personnel</span>
              <span className="text-xl font-bold font-mono text-emerald-400">57,280 (94.1%)</span>
            </div>
            <div className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-slate-400 text-xs block">Medium Risk Watchlist</span>
              <span className="text-xl font-bold font-mono text-amber-400">2,940 (4.8%)</span>
            </div>
            <div className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-slate-400 text-xs block">High Priority Retention</span>
              <span className="text-xl font-bold font-mono text-rose-400">627 (1.1%)</span>
            </div>
          </div>
        </div>

        {/* Executive Action SLAs */}
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-rose-400" /> Pending Approvals &amp; SLA Timers
          </h3>

          <div className="space-y-3 text-xs">
            {[
              { title: 'APAC Expansion Headcount (+250 Req)', sla: '4h 12m', unit: 'Core Platform Eng' },
              { title: 'UK Entity Payroll Variance (+6.2%)', sla: '1h 30m', unit: 'Finance Audit' },
              { title: 'VP AI Ethics Offer Approval ($450k)', sla: '8h 00m', unit: 'Executive Office' }
            ].map((item, idx) => (
              <div key={idx} className="bg-[#0A0E1A] border border-slate-800 p-3 rounded-xl space-y-1">
                <div className="flex justify-between items-center font-bold text-slate-200">
                  <span className="truncate max-w-[180px]">{item.title}</span>
                  <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                    {item.sla}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 block">Unit: {item.unit}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
