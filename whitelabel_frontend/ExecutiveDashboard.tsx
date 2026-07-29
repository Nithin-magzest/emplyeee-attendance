import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LineChart, DonutChart, BarChart } from './components/Charts';
import { NotificationCenter } from './components/NotificationCenter';
import {
  Users,
  UserPlus,
  ShieldCheck,
  DollarSign,
  TrendingUp,
  Clock,
  Calendar,
  Bell,
  ArrowUpRight,
  Building2,
  Globe2,
  Briefcase
} from 'lucide-react';

export const ExecutiveDashboard: React.FC = () => {
  const [notifOpen, setNotifOpen] = useState(false);

  const headcountLineData = [
    { label: 'Aug 25', value: 54200 },
    { label: 'Sep 25', value: 55100 },
    { label: 'Oct 25', value: 56400 },
    { label: 'Nov 25', value: 57200 },
    { label: 'Dec 25', value: 58000 },
    { label: 'Jan 26', value: 58900 },
    { label: 'Feb 26', value: 59300 },
    { label: 'Mar 26', value: 59800 },
    { label: 'Apr 26', value: 60100 },
    { label: 'May 26', value: 60400 },
    { label: 'Jun 26', value: 60650 },
    { label: 'Jul 26', value: 60847 }
  ];

  const regionalDonutData = [
    { label: 'Americas (US/CA/BR)', value: 28400, color: '#4F46E5' },
    { label: 'EMEA (UK/DE/FR)', value: 18200, color: '#0ea5e9' },
    { label: 'APAC (SG/IN/JP)', value: 14247, color: '#10b981' }
  ];

  const attritionBarData = [
    { label: 'Engineering', value: 4.1 },
    { label: 'Sales', value: 8.4, color: '#f59e0b' },
    { label: 'Marketing', value: 5.2 },
    { label: 'Customer Success', value: 6.8 },
    { label: 'Operations', value: 3.2 }
  ];

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 font-sans p-6 sm:p-8 space-y-6">
      {/* Top Header */}
      <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full uppercase">
              OmniHR Premier Edition
            </span>
            <span className="text-slate-500 text-xs font-mono">• 60,000+ Employee Scale</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">Executive Control Tower</h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setNotifOpen(true)}
            className="relative bg-[#111827] hover:bg-slate-800 border border-slate-800 p-2.5 rounded-xl text-slate-300 transition-all"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-indigo-500 border-2 border-[#0A0E1A]" />
          </button>
          <div className="bg-[#111827] border border-slate-800 px-3.5 py-2 rounded-xl text-xs flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono text-slate-300">5 Entities Online</span>
          </div>
        </div>
      </header>

      {/* KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Global Headcount', val: '60,847', sub: '+4.2% YTD growth', icon: Users, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
          { label: 'New Hires YTD', val: '1,247', sub: '98.4% offer acceptance', icon: UserPlus, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
          { label: 'Annual Retention Rate', val: '94.2%', sub: 'vs 91.8% industry median', icon: ShieldCheck, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
          { label: 'Global Annual Payroll', val: '$4.2 Billion', sub: '5 legal entities processed', icon: DollarSign, color: 'text-amber-400', bg: 'bg-amber-500/10' }
        ].map((kpi, i) => (
          <div key={i} className="bg-[#111827] border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between">
            <div className="flex justify-between items-start mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{kpi.label}</span>
              <div className={`p-2.5 rounded-xl border border-slate-800 ${kpi.bg} ${kpi.color}`}>
                <kpi.icon className="w-4 h-4" />
              </div>
            </div>
            <div>
              <span className="text-2xl font-black text-white font-mono tracking-tight block mb-1">{kpi.val}</span>
              <span className="text-[11px] text-slate-400 font-medium">{kpi.sub}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Visualizations Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Line Chart: Headcount Trend */}
        <div className="lg:col-span-2 bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-indigo-400" /> 12-Month Headcount Trajectory
              </h3>
              <p className="text-xs text-slate-400">Net active headcount progression across all global subsidiaries</p>
            </div>
            <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg">
              +12.2% 12-mo Δ
            </span>
          </div>

          <LineChart data={headcountLineData} height={210} color="#4F46E5" fillGradient={true} />
        </div>

        {/* Donut Chart: Regional Distribution */}
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
              <Globe2 className="w-4 h-4 text-emerald-400" /> Workforce by Geographic Region
            </h3>
            <p className="text-xs text-slate-400 mb-4">Distribution across Americas, EMEA, and APAC</p>
          </div>

          <DonutChart data={regionalDonutData} size={180} centerText="60,847" centerSubtext="GLOBAL FTEs" />
        </div>
      </div>

      {/* Second Row: Bar Chart + Action Items + Payroll Calendar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Department Attrition Bar Chart */}
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-amber-400" /> Department Attrition Rate (%)
              </h3>
              <p className="text-xs text-slate-400">Annualized turnover by business unit</p>
            </div>
          </div>

          <BarChart data={attritionBarData} height={160} defaultColor="#4F46E5" />
        </div>

        {/* Action Items Feed with SLA Timers */}
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-rose-400" /> Executive Approvals &amp; SLA Queue
          </h3>

          <div className="space-y-3">
            {[
              { title: 'APAC Expansion Headcount (+250 Req)', sla: '4h 12m remaining', dept: 'Engineering' },
              { title: 'UK Entity Payroll Variance Audit (+6.2%)', sla: '1h 30m remaining', dept: 'Finance' },
              { title: 'VP of AI Research Offer Approval ($450k)', sla: '8h 00m remaining', dept: 'Executive' }
            ].map((item, idx) => (
              <div key={idx} className="bg-[#0A0E1A] border border-slate-800 p-3 rounded-xl space-y-1 text-xs">
                <div className="flex justify-between items-center font-bold text-slate-200">
                  <span className="truncate max-w-[200px]">{item.title}</span>
                  <span className="text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                    {item.sla}
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 block">Unit: {item.dept}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Global Payroll Calendar */}
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
              <Calendar className="w-4 h-4 text-indigo-400" /> Global Payroll Calendar
            </h3>
            <p className="text-xs text-slate-400 mb-3">Upcoming disbursement dates across legal entities</p>

            <div className="space-y-2 text-xs">
              {[
                { entity: 'US Inc. (Delaware)', date: '31 Jul 2026', status: 'LOCKED & AUDITED', color: 'text-emerald-400' },
                { entity: 'UK Ltd. (London)', date: '31 Jul 2026', status: 'VARIANCE REVIEW', color: 'text-amber-400' },
                { entity: 'SG Pte. (Singapore)', date: '05 Aug 2026', status: 'PRE-CALCULATING', color: 'text-slate-400' }
              ].map((p, i) => (
                <div key={i} className="bg-[#0A0E1A] border border-slate-800 p-3 rounded-xl flex justify-between items-center">
                  <div>
                    <span className="font-bold text-slate-200 block">{p.entity}</span>
                    <span className="text-[10px] font-mono text-slate-500">Target: {p.date}</span>
                  </div>
                  <span className={`text-[10px] font-mono font-bold ${p.color}`}>{p.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <NotificationCenter isOpen={notifOpen} onClose={() => setNotifOpen(false)} />
    </div>
  );
};
