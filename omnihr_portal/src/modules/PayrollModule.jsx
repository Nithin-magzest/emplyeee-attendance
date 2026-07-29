import React, { useState } from 'react';
import { MOCK_PAYROLL } from '../data/mockHrmsData';
import { StatusBadge } from '../components/common/StatusBadge';
import { DollarSign, FileText, Printer, Zap, AlertTriangle, Building, CreditCard } from 'lucide-react';

export const PayrollModule = () => {
  const [ewaAmount, setEwaAmount] = useState(1500);
  const [ewaRequested, setEwaRequested] = useState(false);
  const [showPaystub, setShowPaystub] = useState(false);

  return (
    <div className="space-y-6 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            Gusto &amp; Deel Multi-Currency Global Payroll
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">Payroll Execution &amp; Earned Wage Access (EWA)</h2>
        </div>

        <button
          onClick={() => setShowPaystub(true)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20"
        >
          <FileText className="w-4 h-4" /> View Sample Executive Paystub
        </button>
      </div>

      {/* Earned Wage Access (EWA) On-Demand Wage Withdrawal Widget (Gusto Style) */}
      <div className="bg-gradient-to-r from-indigo-950/60 to-slate-900 border border-indigo-500/30 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-bold shadow-lg shadow-indigo-500/20">
              <Zap className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Earned Wage Access (EWA On-Demand Pay)</h3>
              <p className="text-xs text-slate-400">Withdraw up to 50% of earned accrued wages before payday with $0 interest</p>
            </div>
          </div>

          <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/30">
            Accrued: $6,400.00
          </span>
        </div>

        {!ewaRequested ? (
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">Select Withdrawal Amount:</span>
                <span className="text-indigo-400 font-bold text-sm">${ewaAmount}</span>
              </div>
              <input
                type="range"
                min="100"
                max="3200"
                step="100"
                value={ewaAmount}
                onChange={(e) => setEwaAmount(Number(e.target.value))}
                className="w-full h-2 bg-slate-900 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <div className="flex justify-between text-[10px] font-mono text-slate-500">
                <span>$100 (Min)</span>
                <span>$3,200 (50% Max Cap)</span>
              </div>
            </div>

            <div className="flex items-center justify-between bg-[#0A0E1A] p-3 rounded-xl border border-slate-800 text-xs">
              <span className="text-slate-400 font-mono">Instant Bank Transfer Fee: <strong className="text-white">$2.99</strong></span>
              <button
                onClick={() => setEwaRequested(true)}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-4 py-2 rounded-xl text-xs shadow-md shadow-emerald-600/20"
              >
                Transfer ${ewaAmount} Instantly
              </button>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs space-y-1 text-emerald-300 font-mono">
            <span className="font-bold block">✓ Instant Withdrawal Dispatched!</span>
            <span>${ewaAmount} has been transferred to your primary account (Fee $2.99). Remaining payroll will auto-adjust on July 31st.</span>
          </div>
        )}
      </div>

      {/* Multi-Entity Payroll Runs Table */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Building className="w-4 h-4 text-indigo-400" /> Global Subsidiary Runs ({MOCK_PAYROLL.cycle})
        </h3>

        <div className="overflow-x-auto text-xs font-mono">
          <table className="w-full text-left">
            <thead className="bg-[#0A0E1A] text-slate-400 font-bold uppercase text-[10px] border-b border-slate-800">
              <tr>
                <th className="p-3">Legal Entity</th>
                <th className="p-3">Gross Payroll</th>
                <th className="p-3">Tax &amp; Statutory</th>
                <th className="p-3">Net Disbursement</th>
                <th className="p-3">Variance Δ</th>
                <th className="p-3">Audit Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {MOCK_PAYROLL.runs.map((r, i) => (
                <tr key={i} className="hover:bg-slate-800/40">
                  <td className="p-3 font-bold text-white">{r.entity}</td>
                  <td className="p-3 text-slate-300">${r.gross.toLocaleString()}</td>
                  <td className="p-3 text-rose-400">${r.tax.toLocaleString()}</td>
                  <td className="p-3 text-emerald-400 font-bold">${r.net.toLocaleString()}</td>
                  <td className="p-3">
                    <span className={r.variance > 5 ? 'text-amber-400 font-bold' : 'text-slate-400'}>
                      {r.variance > 0 ? `+${r.variance}%` : `${r.variance}%`}
                    </span>
                  </td>
                  <td className="p-3">
                    <StatusBadge status={r.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Paystub Modal */}
      {showPaystub && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="w-full max-w-2xl bg-[#111827] border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-6 font-sans">
            <div className="flex justify-between items-center pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white font-bold flex items-center justify-center font-mono">
                  MH
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">MagHR Premier — Executive Paystub</h3>
                  <p className="text-xs text-slate-400">July 01 – July 31, 2026</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button onClick={() => window.print()} className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5">
                  <Printer className="w-3.5 h-3.5" /> Print / Save PDF
                </button>
                <button onClick={() => setShowPaystub(false)} className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white px-3 py-1.5 rounded-xl text-xs font-bold">
                  Close
                </button>
              </div>
            </div>

            <div className="space-y-4 text-xs font-mono bg-[#0A0E1A] p-5 rounded-2xl border border-slate-800">
              <div className="grid grid-cols-2 gap-4 pb-4 border-b border-slate-800">
                <div>
                  <span className="text-slate-500 block text-[10px]">EMPLOYEE NAME</span>
                  <span className="text-white font-bold">Dr. Evelyn Vance</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-500 block text-[10px]">EMPLOYEE ID</span>
                  <span className="text-indigo-400 font-bold">EMP-1001</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-slate-300"><span>Base Earnings</span><span className="font-bold text-white">$31,666.67</span></div>
                <div className="flex justify-between text-slate-300"><span>Bonus Allowance</span><span className="font-bold text-white">$5,000.00</span></div>
                <div className="flex justify-between text-rose-400"><span>Taxes &amp; FICA</span><span className="font-bold">-$8,420.00</span></div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-between items-center text-sm">
                <span className="font-bold text-white">NET DISBURSEMENT</span>
                <span className="font-black text-emerald-400 text-lg">$26,146.67</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
