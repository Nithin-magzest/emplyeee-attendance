import React from 'react';
import { LineChart, DonutChart, BarChart } from './components/Charts';
import {
  TrendingUp,
  BarChart2,
  PieChart,
  Users,
  DollarSign,
  Download
} from 'lucide-react';

export const WorkforceAnalytics: React.FC = () => {
  const attritionTrendData = [
    { label: 'Q1 25', value: 5.8 },
    { label: 'Q2 25', value: 5.4 },
    { label: 'Q3 25', value: 5.1 },
    { label: 'Q4 25', value: 4.8 },
    { label: 'Q1 26', value: 4.5 },
    { label: 'Q2 26', value: 4.2 }
  ];

  const diversityDonut = [
    { label: 'Female Leaders', value: 44, color: '#ec4899' },
    { label: 'Male Leaders', value: 51, color: '#4F46E5' },
    { label: 'Non-Binary/Other', value: 5, color: '#10b981' }
  ];

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 font-sans p-6 sm:p-8 space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <BarChart2 className="w-6 h-6 text-indigo-400" /> Workforce Intelligence &amp; Analytics
          </h1>
          <p className="text-xs text-slate-400">Pure SVG analytics, linear regression forecasts &amp; D&amp;I metrics</p>
        </div>

        <button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20">
          <Download className="w-4 h-4" /> Export Scheduled Report (CSV)
        </button>
      </header>

      {/* Analytics KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[#111827] border border-slate-800 p-5 rounded-2xl space-y-2 shadow-xl">
          <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Hiring Velocity</span>
          <span className="text-2xl font-black font-mono text-white block">24.2 Days</span>
          <span className="text-[11px] text-emerald-400 font-medium">8.5 days faster than market median</span>
        </div>

        <div className="bg-[#111827] border border-slate-800 p-5 rounded-2xl space-y-2 shadow-xl">
          <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Cost Per Hire</span>
          <span className="text-2xl font-black font-mono text-emerald-400 block">$4,250</span>
          <span className="text-[11px] text-slate-400 font-medium">Includes AI resume screening savings</span>
        </div>

        <div className="bg-[#111827] border border-slate-800 p-5 rounded-2xl space-y-2 shadow-xl">
          <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Linear Forecast (2027 Headcount)</span>
          <span className="text-2xl font-black font-mono text-indigo-400 block">68,400 FTEs</span>
          <span className="text-[11px] text-slate-400 font-medium">+7,553 projected growth</span>
        </div>
      </div>

      {/* Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" /> Annualized Attrition Reduction Rate (%)
          </h3>
          <LineChart data={attritionTrendData} height={200} color="#10b981" />
        </div>

        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
              <PieChart className="w-4 h-4 text-pink-400" /> Leadership Diversity &amp; Inclusion Breakdown
            </h3>
            <p className="text-xs text-slate-400 mb-4">Executive leadership gender &amp; demographic ratio</p>
          </div>

          <DonutChart data={diversityDonut} size={180} centerText="44%" centerSubtext="FEMALE LEADERS" />
        </div>
      </div>
    </div>
  );
};
