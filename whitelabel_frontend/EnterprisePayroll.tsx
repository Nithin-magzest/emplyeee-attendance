import React, { useState } from 'react';
import {
  DollarSign,
  Calendar,
  AlertTriangle,
  FileText,
  Printer,
  CheckCircle2,
  TrendingUp,
  CreditCard,
  Building
} from 'lucide-react';

interface PayrollRun {
  entity: string;
  country: string;
  payPeriod: string;
  totalGross: number;
  taxHoldback: number;
  netPayout: number;
  variancePct: number;
  status: 'AUDITED' | 'VARIANCE_FLAGGED' | 'CALCULATING';
}

export const EnterprisePayroll: React.FC = () => {
  const [selectedPayslip, setSelectedPayslip] = useState<boolean>(false);

  const payrollRuns: PayrollRun[] = [
    { entity: 'US Inc. (Delaware)', country: 'United States', payPeriod: 'Jul 15 - Jul 31, 2026', totalGross: 14200000, taxHoldback: 3550000, netPayout: 10650000, variancePct: +1.2, status: 'AUDITED' },
    { entity: 'UK Ltd. (London)', country: 'United Kingdom', payPeriod: 'Jul 01 - Jul 31, 2026', totalGross: 8400000, taxHoldback: 2100000, netPayout: 6300000, variancePct: +6.2, status: 'VARIANCE_FLAGGED' },
    { entity: 'SG Pte. (Singapore)', country: 'Singapore', payPeriod: 'Jul 01 - Jul 31, 2026', totalGross: 5100000, taxHoldback: 765000, netPayout: 4335000, variancePct: +0.4, status: 'AUDITED' },
    { entity: 'DE GmbH (Munich)', country: 'Germany', payPeriod: 'Jul 01 - Jul 31, 2026', totalGross: 6800000, taxHoldback: 2720000, netPayout: 4080000, variancePct: -0.8, status: 'AUDITED' },
    { entity: 'IN Pvt Ltd (Bengaluru)', country: 'India', payPeriod: 'Jul 01 - Jul 31, 2026', totalGross: 3200000, taxHoldback: 640000, netPayout: 2560000, variancePct: +2.1, status: 'CALCULATING' }
  ];

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-slate-100 font-sans p-6 sm:p-8 space-y-6">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <DollarSign className="w-6 h-6 text-emerald-400" /> Enterprise Payroll Hub
          </h1>
          <p className="text-xs text-slate-400">Multi-entity payroll execution &amp; variance audit engine ($4.2B Annual Scale)</p>
        </div>

        <button
          onClick={() => setSelectedPayslip(true)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20"
        >
          <FileText className="w-4 h-4" /> Sample Executive Payslip (PDF Print)
        </button>
      </header>

      {/* Variance Alert Banner */}
      <div className="bg-amber-500/10 border border-amber-500/30 p-4 rounded-2xl flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400 flex items-center justify-center font-bold">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-amber-300">Payroll Variance Alert: UK Entity (+6.2% Deviation)</h4>
            <p className="text-xs text-slate-400">July payroll gross exceeds June threshold due to £420k quarterly executive bonus payouts.</p>
          </div>
        </div>
        <button className="bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30 px-3 py-1.5 rounded-xl text-xs font-bold font-mono">
          Review Audit Trail →
        </button>
      </div>

      {/* Multi-Entity Payroll Run Table */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Building className="w-4 h-4 text-indigo-400" /> Global Subsidiary Payroll Runs (July 2026 Cycle)
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-[#0A0E1A] text-slate-400 uppercase font-bold text-[10px] border-b border-slate-800">
              <tr>
                <th className="p-3">Legal Entity</th>
                <th className="p-3">Pay Period</th>
                <th className="p-3">Gross Payroll</th>
                <th className="p-3">Tax &amp; Statutory Holdback</th>
                <th className="p-3">Net Disbursement</th>
                <th className="p-3">Cycle Variance</th>
                <th className="p-3">Audit Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {payrollRuns.map((r, i) => (
                <tr key={i} className="hover:bg-slate-800/40">
                  <td className="p-3 font-bold text-white">{r.entity} <span className="text-[10px] text-slate-500 font-mono block">{r.country}</span></td>
                  <td className="p-3 text-slate-400 font-mono">{r.payPeriod}</td>
                  <td className="p-3 font-mono font-bold text-slate-200">${r.totalGross.toLocaleString()}</td>
                  <td className="p-3 font-mono text-rose-400">${r.taxHoldback.toLocaleString()}</td>
                  <td className="p-3 font-mono font-bold text-emerald-400">${r.netPayout.toLocaleString()}</td>
                  <td className="p-3 font-mono">
                    <span className={r.variancePct > 5 ? 'text-amber-400 font-bold' : 'text-slate-400'}>
                      {r.variancePct > 0 ? `+${r.variancePct}%` : `${r.variancePct}%`}
                    </span>
                  </td>
                  <td className="p-3">
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      r.status === 'AUDITED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      r.status === 'VARIANCE_FLAGGED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-slate-800 text-slate-400'
                    }`}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* PDF Payslip Modal */}
      {selectedPayslip && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="w-full max-w-2xl bg-[#111827] border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-6 font-sans">
            <div className="flex justify-between items-center pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white font-bold flex items-center justify-center font-mono">
                  OH
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">OmniHR Premier — Executive Payslip</h3>
                  <p className="text-xs text-slate-400">Pay Period: July 01 – July 31, 2026</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button onClick={() => window.print()} className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5">
                  <Printer className="w-3.5 h-3.5" /> Print / Save PDF
                </button>
                <button onClick={() => setSelectedPayslip(false)} className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white px-3 py-1.5 rounded-xl text-xs font-bold">
                  Close
                </button>
              </div>
            </div>

            <div className="space-y-4 text-xs font-mono bg-[#0A0E1A] p-5 rounded-2xl border border-slate-800">
              <div className="grid grid-cols-2 gap-4 pb-4 border-b border-slate-800">
                <div>
                  <span className="text-slate-500 block text-[10px]">EMPLOYEE NAME</span>
                  <span className="text-white font-bold">Dr. Evelyn Vance</span>
                  <span className="text-slate-400 block text-[11px]">VP of Distributed Infrastructure</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-500 block text-[10px]">EMPLOYEE ID</span>
                  <span className="text-indigo-400 font-bold">EMP-1001</span>
                  <span className="text-slate-400 block text-[11px]">US Inc. (Delaware)</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-slate-300">
                  <span>Base Salary Earnings</span>
                  <span className="font-bold text-white">$31,666.67</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Executive Bonus Allowance</span>
                  <span className="font-bold text-white">$5,000.00</span>
                </div>
                <div className="flex justify-between text-rose-400">
                  <span>Federal Tax &amp; FICA Deductions</span>
                  <span className="font-bold">-$8,420.00</span>
                </div>
                <div className="flex justify-between text-rose-400">
                  <span>Health &amp; 401(k) Pre-Tax Contribution</span>
                  <span className="font-bold">-$2,100.00</span>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-between items-center text-sm">
                <span className="font-bold text-white">NET TAKE-HOME PAYOUT</span>
                <span className="font-black text-emerald-400 text-lg">$26,146.67</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
