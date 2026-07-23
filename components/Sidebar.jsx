import React from 'react';

export default function Sidebar() {
  return (
    <div className="p-4 flex flex-col h-full">
      <div className="text-xl font-bold mb-6 text-white flex items-center gap-2">
        <span>⚙️</span> Admin Panel
      </div>
      <nav className="flex flex-col gap-2">
        <a href="/admin" className="px-3 py-2 rounded bg-slate-800 text-white font-medium hover:bg-slate-700">Dashboard</a>
        <a href="/employees" className="px-3 py-2 rounded text-slate-300 hover:bg-slate-800 hover:text-white">Employees</a>
        <a href="/monthly_report" className="px-3 py-2 rounded text-slate-300 hover:bg-slate-800 hover:text-white">Attendance</a>
        <a href="/salary_report" className="px-3 py-2 rounded text-slate-300 hover:bg-slate-800 hover:text-white">Salary & Payslips</a>
        <a href="/leave_holidays" className="px-3 py-2 rounded text-slate-300 hover:bg-slate-800 hover:text-white">Leaves & Holidays</a>
        <a href="/analytics" className="px-3 py-2 rounded text-slate-300 hover:bg-slate-800 hover:text-white">Analytics</a>
        <a href="/settings" className="px-3 py-2 rounded text-slate-300 hover:bg-slate-800 hover:text-white">Settings</a>
      </nav>
      <div className="mt-auto pt-4 border-t border-slate-800 text-xs text-slate-400">
        Attendance System v2.0
      </div>
    </div>
  );
}
