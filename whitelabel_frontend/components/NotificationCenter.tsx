import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock, CheckCircle2, AlertCircle, ShieldAlert, FileText } from 'lucide-react';

interface NotificationItem {
  id: string;
  title: string;
  category: 'APPROVAL' | 'SECURITY' | 'PAYROLL' | 'COMPLIANCE';
  message: string;
  slaTimer?: string;
  time: string;
  read?: boolean;
}

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({ isOpen, onClose }) => {
  const notifications: NotificationItem[] = [
    {
      id: 'n1',
      title: 'Executive Headcount Requisition',
      category: 'APPROVAL',
      message: 'Finance & HRBP sign-off required for Sr. Director of AI Engineering (Req #842).',
      slaTimer: '2h 15m remaining',
      time: '10 mins ago'
    },
    {
      id: 'n2',
      title: 'Payroll Variance Alert Flagged',
      category: 'PAYROLL',
      message: 'UK Entity July run deviates +6.2% from June cycle ($420k bonus payout).',
      time: '45 mins ago'
    },
    {
      id: 'n3',
      title: 'SOC 2 Type II Evidence Renewal',
      category: 'COMPLIANCE',
      message: 'AWS IAM Role audit log evidence upload due in 4 days.',
      time: '2 hours ago'
    },
    {
      id: 'n4',
      title: 'Suspicious IP Anomaly Blocked',
      category: 'SECURITY',
      message: '185.220.101.5 auto-banned by Quiet Security Shield (Tor exit node).',
      time: '4 hours ago'
    }
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden font-sans">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm"
          />

          <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="w-screen max-w-md bg-[#111827] border-l border-slate-800 shadow-2xl flex flex-col justify-between"
            >
              {/* Header */}
              <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-[#0F172A]">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center font-bold text-xs">
                    4
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">Notification Centre</h3>
                    <p className="text-[11px] text-slate-400">Action items, approvals &amp; compliance SLAs</p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {notifications.map((item) => (
                  <div
                    key={item.id}
                    className="p-3.5 bg-[#0A0E1A] border border-slate-800/80 rounded-2xl space-y-2 hover:border-slate-700 transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase border bg-slate-900 text-indigo-300 border-indigo-500/30">
                        {item.category}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">{item.time}</span>
                    </div>

                    <h4 className="text-xs font-bold text-slate-100">{item.title}</h4>
                    <p className="text-xs text-slate-400 leading-relaxed">{item.message}</p>

                    {item.slaTimer && (
                      <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-1 rounded-lg">
                        <Clock className="w-3 h-3" /> SLA Timer: {item.slaTimer}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-slate-800 bg-[#0F172A] text-center">
                <button
                  onClick={onClose}
                  className="w-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-bold py-2 rounded-xl text-xs transition-all"
                >
                  Mark All as Read &amp; Close
                </button>
              </div>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  );
};
