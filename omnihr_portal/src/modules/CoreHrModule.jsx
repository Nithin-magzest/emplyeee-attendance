import React, { useState } from 'react';
import { MOCK_EMPLOYEES } from '../data/mockHrmsData';
import { StatusBadge } from '../components/common/StatusBadge';
import { Users, Laptop, GitFork, Search, Filter, ShieldCheck, Mail, MapPin, Building, ChevronDown, ChevronRight, X } from 'lucide-react';

export const CoreHrModule = () => {
  const [activeTab, setActiveTab] = useState<'DIRECTORY' | 'ORG_CHART' | 'DEVICES'>('DIRECTORY');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEmp, setSelectedEmp] = useState<typeof MOCK_EMPLOYEES[0] | null>(null);

  const filteredEmployees = MOCK_EMPLOYEES.filter(
    (e) =>
      e.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.department.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            BambooHR &amp; Rippling Consolidated Core HR
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">Directory, Smart Org Tree &amp; IT Device Hub</h2>
        </div>

        <div className="flex gap-1.5 bg-[#111827] border border-slate-800 p-1 rounded-xl text-xs font-semibold">
          <button
            onClick={() => setActiveTab('DIRECTORY')}
            className={`px-3.5 py-1.5 rounded-lg transition-all ${activeTab === 'DIRECTORY' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
          >
            Employee Directory
          </button>
          <button
            onClick={() => setActiveTab('ORG_CHART')}
            className={`px-3.5 py-1.5 rounded-lg transition-all ${activeTab === 'ORG_CHART' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
          >
            Smart Org Hierarchy
          </button>
          <button
            onClick={() => setActiveTab('DEVICES')}
            className={`px-3.5 py-1.5 rounded-lg transition-all ${activeTab === 'DEVICES' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
          >
            IT Hardware (Rippling)
          </button>
        </div>
      </div>

      {/* Directory Tab */}
      {activeTab === 'DIRECTORY' && (
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex justify-between items-center gap-4">
            <div className="relative w-full max-w-sm">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter 60,847 employees by name, title, department..."
                className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
              />
            </div>
            <span className="text-xs font-mono text-slate-400">Showing {filteredEmployees.length} records</span>
          </div>

          <div className="overflow-x-auto text-xs">
            <table className="w-full text-left">
              <thead className="bg-[#0A0E1A] text-slate-400 font-bold uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="p-3">Employee Name</th>
                  <th className="p-3">Role &amp; Business Unit</th>
                  <th className="p-3">Location &amp; Entity</th>
                  <th className="p-3">Base Compensation</th>
                  <th className="p-3">Risk Index</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {filteredEmployees.map((emp) => (
                  <tr key={emp.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-3">
                      <button onClick={() => setSelectedEmp(emp)} className="flex items-center gap-3 text-left group">
                        <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white font-mono font-bold text-xs flex items-center justify-center">
                          {emp.avatar}
                        </div>
                        <div>
                          <span className="font-bold text-white block group-hover:text-indigo-400 transition-colors">{emp.name}</span>
                          <span className="text-[10px] text-slate-500 font-mono">{emp.email}</span>
                        </div>
                      </button>
                    </td>
                    <td className="p-3">
                      <span className="font-medium text-slate-200 block">{emp.role}</span>
                      <span className="text-[10px] text-slate-500">{emp.department}</span>
                    </td>
                    <td className="p-3 font-mono">
                      <span className="text-slate-300 block">{emp.location}</span>
                      <span className="text-[10px] text-slate-500">{emp.entity}</span>
                    </td>
                    <td className="p-3 font-mono font-bold text-emerald-400">
                      ${emp.salary.toLocaleString()} /yr
                    </td>
                    <td className="p-3 font-mono">
                      <StatusBadge status={emp.attritionRisk} text={`${emp.attritionRisk} RISK`} />
                    </td>
                    <td className="p-3">
                      <StatusBadge status={emp.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Org Chart Tab */}
      {activeTab === 'ORG_CHART' && (
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-base font-bold text-white mb-2">Smart Org Hierarchy Tree</h3>

          <div className="space-y-4 font-mono text-xs">
            <div className="bg-[#0A0E1A] border border-indigo-500/40 p-4 rounded-xl space-y-1">
              <span className="text-indigo-400 font-bold block">Chief Executive Officer (CEO Office)</span>
              <span className="text-slate-400 text-[11px] block">Executive Board · Global Scale</span>
            </div>

            <div className="pl-6 border-l-2 border-slate-800 space-y-3">
              {MOCK_EMPLOYEES.map((emp) => (
                <div key={emp.id} className="bg-[#0A0E1A] border border-slate-800 p-3 rounded-xl flex justify-between items-center">
                  <div>
                    <span className="font-bold text-white block">{emp.name} ({emp.role})</span>
                    <span className="text-[10px] text-slate-500 font-mono">Reports To: {emp.manager} · Directs: {emp.directReports}</span>
                  </div>
                  <span className="text-[10px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                    {emp.department}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* IT Hardware Tab (Rippling Style) */}
      {activeTab === 'DEVICES' && (
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
            <Laptop className="w-5 h-5 text-cyan-400" /> Rippling IT Hardware &amp; MDM Device Hub
          </h3>

          <div className="overflow-x-auto text-xs">
            <table className="w-full text-left">
              <thead className="bg-[#0A0E1A] text-slate-400 font-bold uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="p-3">Assigned User</th>
                  <th className="p-3">Device Model</th>
                  <th className="p-3">Serial Number</th>
                  <th className="p-3">MDM Enrollment</th>
                  <th className="p-3">Assigned Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {MOCK_EMPLOYEES.map((emp) => (
                  <tr key={emp.id} className="hover:bg-slate-800/40">
                    <td className="p-3 font-bold text-white">{emp.name}</td>
                    <td className="p-3 text-slate-300">{emp.device.model}</td>
                    <td className="p-3 text-slate-400">{emp.device.serial}</td>
                    <td className="p-3">
                      <StatusBadge status="ACTIVE" text={emp.device.status} />
                    </td>
                    <td className="p-3 text-slate-500">{emp.device.assignedDate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Profile Drawer */}
      {selectedEmp && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#111827] border-l border-slate-800 p-6 shadow-2xl space-y-6 overflow-y-auto font-sans">
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-indigo-600 text-white font-mono font-bold text-lg flex items-center justify-center">
                  {selectedEmp.avatar}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">{selectedEmp.name}</h3>
                  <p className="text-xs text-slate-400">{selectedEmp.role}</p>
                </div>
              </div>
              <button onClick={() => setSelectedEmp(null)} className="p-1 rounded-lg border border-slate-800 text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 bg-[#0A0E1A] p-4 rounded-xl border border-slate-800 text-xs font-mono">
              <div className="flex justify-between"><span className="text-slate-400">ID</span><span className="text-white font-bold">{selectedEmp.id}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Entity</span><span className="text-white font-bold">{selectedEmp.entity}</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Salary</span><span className="text-emerald-400 font-bold">${selectedEmp.salary.toLocaleString()}/yr</span></div>
              <div className="flex justify-between"><span className="text-slate-400">Device</span><span className="text-slate-200">{selectedEmp.device.model}</span></div>
            </div>

            <button onClick={() => setSelectedEmp(null)} className="w-full bg-slate-900 border border-slate-800 text-slate-300 font-bold py-2 rounded-xl text-xs">
              Close Drawer
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
