import React, { useState } from 'react';
import { MOCK_ATTENDANCE } from '../data/mockHrmsData';
import { StatusBadge } from '../components/common/StatusBadge';
import { Clock, MapPin, Calendar, ShieldCheck, CheckCircle2, AlertOctagon, Camera, RefreshCw } from 'lucide-react';

export const AttendanceModule = () => {
  const [punchedIn, setPunchedIn] = useState(false);
  const [ptoRequested, setPtoRequested] = useState(false);

  return (
    <div className="space-y-6 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            Zoho People &amp; Keka Biometric Attendance
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">Geofenced Time Tracker &amp; Roster Management</h2>
        </div>

        <div className="flex items-center gap-2 bg-[#111827] border border-slate-800 px-3.5 py-2 rounded-xl text-xs font-mono">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-300 font-bold">GPS Geofence + Webcam Verification Active</span>
        </div>
      </div>

      {/* Interactive Geofenced Check-In / Punch Simulator */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="space-y-2 text-center sm:text-left">
          <span className="text-[10px] font-mono font-bold text-indigo-400 uppercase tracking-wider block">Live Punch Telemetry</span>
          <h3 className="text-xl font-bold text-white">New York HQ Office (US Hub)</h3>
          <p className="text-xs text-slate-400 font-mono">Lat: 40.7128, Lon: -74.0060 · IP: 198.51.100.42 (Verified)</p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            onClick={() => setPunchedIn(!punchedIn)}
            className={`px-6 py-3 rounded-xl font-bold text-xs transition-all shadow-xl flex items-center gap-2 ${
              punchedIn ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/20' : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20'
            }`}
          >
            <Camera className="w-4 h-4" />
            {punchedIn ? 'Punch Out (End Today\'s Shift)' : 'Biometric Punch In (Start Shift)'}
          </button>
        </div>
      </div>

      {/* Global Location Attendance Heatmap */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <MapPin className="w-4 h-4 text-emerald-400" /> Global Work Location Distribution (Today)
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {MOCK_ATTENDANCE.todayHeatmap.map((h, i) => (
            <div key={i} className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="font-bold text-slate-200">{h.location}</span>
                <span className="text-[10px] font-mono text-slate-500">{h.total.toLocaleString()} staff</span>
              </div>

              <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden flex">
                <div style={{ width: `${h.inOffice}%` }} className="bg-indigo-500 h-full" />
                <div style={{ width: `${h.remote}%` }} className="bg-cyan-500 h-full" />
                <div style={{ width: `${h.leave}%` }} className="bg-slate-700 h-full" />
              </div>

              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>In Office {h.inOffice}%</span>
                <span>Remote {h.remote}%</span>
                <span>On Leave {h.leave}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
