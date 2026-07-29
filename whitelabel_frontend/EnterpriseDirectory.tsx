import React, { useState } from 'react';
import { DataTable, Column } from './components/DataTable';
import {
  Users,
  Filter,
  Download,
  Building2,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  X,
  ChevronRight,
  ChevronDown,
  UserCheck,
  FileText
} from 'lucide-react';

interface EmployeeRecord {
  id: string;
  fullName: string;
  email: string;
  department: string;
  role: string;
  location: string;
  legalEntity: string;
  salary: number;
  joinDate: string;
  attritionRisk: 'LOW' | 'MEDIUM' | 'HIGH';
  status: 'ACTIVE' | 'ON_LEAVE' | 'OFFBOARDING';
}

export const EnterpriseDirectory: React.FC = () => {
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeRecord | null>(null);
  const [viewTab, setViewTab] = useState<'DIRECTORY' | 'ORG_CHART'>('DIRECTORY');

  // Sample Enterprise Directory Dataset (60k Scale Mock)
  const [employees] = useState<EmployeeRecord[]>([
    {
      id: 'EMP-1001',
      fullName: 'Dr. Evelyn Vance',
      email: 'evelyn.vance@company.com',
      department: 'Core Platform Engineering',
      role: 'VP of Distributed Infrastructure',
      location: 'New York, US',
      legalEntity: 'US Inc. (Delaware)',
      salary: 380000,
      joinDate: '2020-03-15',
      attritionRisk: 'LOW',
      status: 'ACTIVE'
    },
    {
      id: 'EMP-1002',
      fullName: 'Marcus Sterling',
      email: 'marcus.sterling@company.com',
      department: 'Security Operations',
      role: 'Principal SecOps Architect',
      location: 'London, UK',
      legalEntity: 'UK Ltd. (London)',
      salary: 290000,
      joinDate: '2021-06-01',
      attritionRisk: 'LOW',
      status: 'ACTIVE'
    },
    {
      id: 'EMP-1003',
      fullName: 'Priya Sharma',
      email: 'priya.sharma@company.com',
      department: 'AI & Data Science',
      role: 'Staff ML Research Engineer',
      location: 'Singapore, SG',
      legalEntity: 'SG Pte. (Singapore)',
      salary: 240000,
      joinDate: '2022-01-10',
      attritionRisk: 'MEDIUM',
      status: 'ACTIVE'
    },
    {
      id: 'EMP-1004',
      fullName: 'Kaelen Rivera',
      email: 'kaelen.rivera@company.com',
      department: 'Global Sales',
      role: 'Enterprise AE — EMEA',
      location: 'Frankfurt, DE',
      legalEntity: 'DE GmbH (Munich)',
      salary: 210000,
      joinDate: '2019-11-20',
      attritionRisk: 'HIGH',
      status: 'ON_LEAVE'
    },
    {
      id: 'EMP-1005',
      fullName: 'Sarah Jenkins',
      email: 'sarah.jenkins@company.com',
      department: 'Human Resources',
      role: 'Senior Director of People Operations',
      location: 'New York, US',
      legalEntity: 'US Inc. (Delaware)',
      salary: 265000,
      joinDate: '2018-08-04',
      attritionRisk: 'LOW',
      status: 'ACTIVE'
    }
  ]);

  const columns: Column<EmployeeRecord>[] = [
    {
      key: 'fullName',
      label: 'Employee Name & Email',
      render: (emp) => (
        <button
          onClick={() => setSelectedEmployee(emp)}
          className="text-left hover:text-indigo-400 transition-colors group"
        >
          <span className="font-bold text-white block group-hover:underline">{emp.fullName}</span>
          <span className="text-[11px] text-slate-500 font-mono">{emp.email}</span>
        </button>
      )
    },
    { key: 'department', label: 'Department & Role', render: (e) => (
      <div>
        <span className="font-medium text-slate-200 block">{e.role}</span>
        <span className="text-[10px] text-slate-500">{e.department}</span>
      </div>
    )},
    { key: 'location', label: 'Location & Entity', render: (e) => (
      <div>
        <span className="font-mono text-slate-300 block">{e.location}</span>
        <span className="text-[10px] text-slate-500">{e.legalEntity}</span>
      </div>
    )},
    { key: 'salary', label: 'Annual Compensation', render: (e) => (
      <span className="font-mono font-bold text-emerald-400">${e.salary.toLocaleString()}</span>
    )},
    { key: 'joinDate', label: 'Join Date', render: (e) => (
      <span className="font-mono text-slate-400">{e.joinDate}</span>
    )},
    { key: 'attritionRisk', label: 'Risk Score', render: (e) => (
      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
        e.attritionRisk === 'HIGH' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30' :
        e.attritionRisk === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
        'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
      }`}>
        {e.attritionRisk} RISK
      </span>
    )},
    { key: 'status', label: 'Status', render: (e) => (
      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
        e.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-400'
      }`}>
        {e.status}
      </span>
    )}
  ];

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 font-sans p-6 sm:p-8 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <Users className="w-6 h-6 text-indigo-400" /> Core HR Directory
          </h1>
          <p className="text-xs text-slate-400">Paginated enterprise global employee registry (60,847 records)</p>
        </div>

        <div className="flex gap-2 bg-[#111827] border border-slate-800 p-1 rounded-xl">
          <button
            onClick={() => setViewTab('DIRECTORY')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
              viewTab === 'DIRECTORY' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Data Directory
          </button>
          <button
            onClick={() => setViewTab('ORG_CHART')}
            className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
              viewTab === 'ORG_CHART' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Org Hierarchy Tree
          </button>
        </div>
      </div>

      {viewTab === 'DIRECTORY' ? (
        <DataTable
          data={employees}
          columns={columns}
          pageSize={20}
          searchPlaceholder="Search 60,847 employees by name, role, department, location..."
          onBulkAction={(selected, act) => {
            alert(`Executed ${act} on ${selected.length} employee records.`);
          }}
        />
      ) : (
        /* Org Chart Hierarchy Tree View */
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <h3 className="text-base font-bold text-white mb-4">Enterprise Executive Reporting Chain</h3>
          <div className="space-y-4 font-mono text-xs">
            <div className="bg-[#0A0E1A] border border-indigo-500/30 p-4 rounded-xl space-y-1">
              <span className="text-indigo-400 font-bold block">Chief Executive Officer (CEO) — Sarah Jenkins</span>
              <span className="text-slate-400 text-[11px] block">Direct Reports: 8 Executive VPs · Global Scale</span>
            </div>

            <div className="pl-6 border-l-2 border-slate-800 space-y-3">
              <div className="bg-[#0A0E1A] border border-slate-800 p-3 rounded-xl">
                <span className="text-emerald-400 font-bold block">VP of Distributed Infrastructure — Dr. Evelyn Vance</span>
                <span className="text-slate-500 text-[11px] block">Core Platform Engineering · 1,420 Engineers</span>
              </div>
              <div className="bg-[#0A0E1A] border border-slate-800 p-3 rounded-xl">
                <span className="text-cyan-400 font-bold block">Principal SecOps Architect — Marcus Sterling</span>
                <span className="text-slate-500 text-[11px] block">Cyber SecOps &amp; Compliance · 42 Analysts</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Employee Detail Drawer */}
      {selectedEmployee && (
        <div className="fixed inset-0 z-50 overflow-hidden font-sans">
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={() => setSelectedEmployee(null)} />
          <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-lg bg-[#111827] border-l border-slate-800 p-6 shadow-2xl space-y-6 overflow-y-auto">
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-600 text-white font-bold text-lg flex items-center justify-center font-mono">
                    {selectedEmployee.fullName.substring(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white">{selectedEmployee.fullName}</h3>
                    <p className="text-xs text-slate-400">{selectedEmployee.role}</p>
                  </div>
                </div>
                <button onClick={() => setSelectedEmployee(null)} className="p-1 rounded-lg border border-slate-800 text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-3 bg-[#0A0E1A] p-4 rounded-xl border border-slate-800 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-400">Employee ID</span>
                  <span className="text-slate-100 font-bold">{selectedEmployee.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Legal Entity</span>
                  <span className="text-slate-100 font-bold">{selectedEmployee.legalEntity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Base Salary</span>
                  <span className="text-emerald-400 font-bold">${selectedEmployee.salary.toLocaleString()}/yr</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Join Date</span>
                  <span className="text-slate-100 font-bold">{selectedEmployee.joinDate}</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedEmployee(null)}
                className="w-full bg-slate-900 border border-slate-800 text-slate-300 font-bold py-2.5 rounded-xl text-xs"
              >
                Close Profile Drawer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
