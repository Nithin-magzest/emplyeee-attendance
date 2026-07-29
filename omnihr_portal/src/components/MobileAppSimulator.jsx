import React, { useState } from 'react';
import { X, Smartphone, Clock, DollarSign, Calendar, ShieldCheck, CheckCircle2, User, ChevronRight } from 'lucide-react';

export const MobileAppSimulator = ({ isOpen, onClose }) => {
  const [punchedIn, setPunchedIn] = useState(false);
  const [deviceFrame, setDeviceFrame] = useState<'ios' | 'android'>('ios');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md font-sans">
      <div className="relative bg-[#111827] border border-slate-800 rounded-3xl p-6 shadow-2xl flex flex-col items-center gap-4">
        {/* Frame Toggle Header */}
        <div className="w-full flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Smartphone className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-bold text-white">Mobile ESS Experience Simulator</span>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex bg-[#0A0E1A] border border-slate-800 p-0.5 rounded-lg text-[10px] font-mono">
              <button
                onClick={() => setDeviceFrame('ios')}
                className={`px-2.5 py-1 rounded ${deviceFrame === 'ios' ? 'bg-indigo-600 text-white' : 'text-slate-400'}`}
              >
                iOS Frame
              </button>
              <button
                onClick={() => setDeviceFrame('android')}
                className={`px-2.5 py-1 rounded ${deviceFrame === 'android' ? 'bg-indigo-600 text-white' : 'text-slate-400'}`}
              >
                Android Frame
              </button>
            </div>
            <button onClick={onClose} className="p-1 rounded-lg border border-slate-800 text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Mobile Phone Mockup Frame */}
        <div className={`w-80 h-[560px] bg-[#0A0E1A] border-4 ${deviceFrame === 'ios' ? 'border-slate-700 rounded-[48px]' : 'border-slate-800 rounded-[28px]'} overflow-hidden relative shadow-2xl flex flex-col justify-between`}>
          {/* iOS Dynamic Island / Notch */}
          {deviceFrame === 'ios' && (
            <div className="w-28 h-4 bg-slate-900 rounded-full mx-auto mt-2 shrink-0 z-10" />
          )}

          {/* Phone Screen Body */}
          <div className="p-4 flex-1 overflow-y-auto space-y-4 font-sans text-xs">
            {/* Header Greeting */}
            <div className="flex justify-between items-center bg-[#111827] p-3 rounded-2xl border border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white font-bold font-mono flex items-center justify-center">
                  EV
                </div>
                <div>
                  <span className="font-bold text-white block">Dr. Evelyn Vance</span>
                  <span className="text-[10px] text-slate-400 font-mono">VP Infra · US Inc.</span>
                </div>
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>

            {/* Attendance Punch Card */}
            <div className="bg-[#111827] border border-slate-800 p-4 rounded-2xl space-y-3 text-center">
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">Geofenced GPS Punch</span>
              <button
                onClick={() => setPunchedIn(!punchedIn)}
                className={`w-full py-3 rounded-xl font-bold text-xs transition-all flex items-center justify-center gap-2 ${
                  punchedIn ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/20' : 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/20'
                }`}
              >
                <Clock className="w-4 h-4" />
                {punchedIn ? 'Punch Out (End Shift)' : 'Punch In (New York HQ)'}
              </button>
              <span className="text-[10px] text-slate-500 font-mono block">GPS Verified: Lat 40.7128, Lon -74.0060</span>
            </div>

            {/* Quick Actions Grid */}
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="bg-[#111827] border border-slate-800 p-3 rounded-xl space-y-1">
                <DollarSign className="w-4 h-4 text-emerald-400 mx-auto" />
                <span className="font-bold text-white block text-[11px]">EWA Wage Pay</span>
                <span className="text-[9px] text-slate-500 font-mono">$1,500 Available</span>
              </div>
              <div className="bg-[#111827] border border-slate-800 p-3 rounded-xl space-y-1">
                <Calendar className="w-4 h-4 text-indigo-400 mx-auto" />
                <span className="font-bold text-white block text-[11px]">Apply PTO</span>
                <span className="text-[9px] text-slate-500 font-mono">24 Days Balance</span>
              </div>
            </div>

            {/* Recent Notifications Feed */}
            <div className="bg-[#111827] border border-slate-800 p-3 rounded-2xl space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Recent Alerts</span>
              <div className="bg-[#0A0E1A] p-2 rounded-xl text-[11px] space-y-0.5">
                <span className="font-bold text-emerald-400 block">July Payslip Ready</span>
                <span className="text-slate-400 block text-[10px]">Net Take-Home: $26,146.67</span>
              </div>
            </div>
          </div>

          {/* Bottom Bar Indicator */}
          <div className="w-32 h-1 bg-slate-700 rounded-full mx-auto mb-2 shrink-0" />
        </div>
      </div>
    </div>
  );
};
