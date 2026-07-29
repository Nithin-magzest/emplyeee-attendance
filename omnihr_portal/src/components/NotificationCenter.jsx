import React from 'react';
import { X, Bell, Clock, ShieldAlert, CheckCircle2, AlertTriangle } from 'lucide-react';

export const NotificationCenter = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const notifications = [
    {
      id: 1,
      title: 'UK Entity Payroll Variance Flagged (+6.2%)',
      desc: 'Gross payroll exceeded typical threshold due to annual bonus payouts.',
      time: '12m ago',
      type: 'ALERT'
    },
    {
      id: 2,
      title: 'APAC Expansion Headcount Approval Pending',
      desc: 'VP of Platform Eng requested +250 headcount requisitions.',
      time: '1h ago',
      type: 'ACTION'
    },
    {
      id: 3,
      title: 'SOC 2 Type II Audit Log Synchronized',
      desc: 'All security telemetry events written to immutable audit database.',
      time: '3h ago',
      type: 'INFO'
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/80 backdrop-blur-sm font-sans">
      <div className="w-full max-w-sm bg-[#111827] border-l border-slate-800 p-6 shadow-2xl flex flex-col justify-between h-full space-y-6">
        <div>
          <div className="flex justify-between items-center pb-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white">System Notification Center</h3>
            </div>
            <button onClick={onClose} className="p-1 rounded-lg border border-slate-800 text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="my-4 space-y-3">
            {notifications.map((n) => (
              <div key={n.id} className="bg-[#0A0E1A] border border-slate-800 p-3.5 rounded-xl space-y-1 text-xs">
                <div className="flex justify-between items-start font-bold">
                  <span className="text-white font-sans">{n.title}</span>
                  <span className="text-[10px] font-mono text-slate-500 shrink-0">{n.time}</span>
                </div>
                <p className="text-[11px] text-slate-400">{n.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <button onClick={onClose} className="w-full bg-slate-900 border border-slate-800 text-slate-300 font-bold py-2 rounded-xl text-xs">
          Dismiss Notification Drawer
        </button>
      </div>
    </div>
  );
};
