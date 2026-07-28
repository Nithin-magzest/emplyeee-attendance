import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTenant } from './TenantContext';
import {
  DollarSign,
  TrendingUp,
  Award,
  Send,
  Zap,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  Slack,
  Github,
  Mail,
  Video,
  UserX,
  RefreshCw,
  Sliders,
  Globe
} from 'lucide-react';

interface KudosFeedItem {
  id: string;
  sender: string;
  receiver: string;
  points: number;
  tag: string;
  message: string;
  time: string;
}

export const Dashboard: React.FC = () => {
  const { config, resetToSetup } = useTenant();

  // Kudos State
  const [recipient, setRecipient] = useState<string>('');
  const [points, setPoints] = useState<number>(25);
  const [tag, setTag] = useState<string>('Ownership');
  const [message, setMessage] = useState<string>('');
  const [kudosFeed, setKudosFeed] = useState<KudosFeedItem[]>([
    {
      id: '1',
      sender: 'Sarah Jenkins',
      receiver: 'Alex Rivera',
      points: 50,
      tag: 'Ownership',
      message: 'Alex resolved the auth pipeline bottleneck single-handedly. Inspiring work!',
      time: '12 mins ago'
    },
    {
      id: '2',
      sender: 'Michael Chen',
      receiver: 'Elena Rostova',
      points: 25,
      tag: 'Customer Obsession',
      message: 'Elena spent 2 hours walking our enterprise customer through their API setup.',
      time: '1 hour ago'
    }
  ]);

  // Offboarding Modal State
  const [offboardModalOpen, setOffboardModalOpen] = useState<boolean>(false);
  const [offboardStep, setOffboardStep] = useState<number>(0);
  const [isProcessingOffboard, setIsProcessingOffboard] = useState<boolean>(false);

  // Submit Kudos
  const handleSendKudos = (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipient || !message) return;
    setKudosFeed([
      {
        id: Date.now().toString(),
        sender: 'You (Admin)',
        receiver: recipient,
        points,
        tag,
        message,
        time: 'Just now'
      },
      ...kudosFeed
    ]);
    setRecipient('');
    setMessage('');
  };

  // Run Zero-Touch Offboarding Simulation
  const handleExecuteOffboarding = () => {
    setIsProcessingOffboard(true);
    setOffboardStep(1);

    const steps = [
      { s: 1, delay: 600 },
      { s: 2, delay: 1200 },
      { s: 3, delay: 1800 },
      { s: 4, delay: 2400 }
    ];

    steps.forEach(({ s, delay }) => {
      setTimeout(() => {
        setOffboardStep(s);
        if (s === 4) {
          setIsProcessingOffboard(false);
        }
      }, delay);
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 sm:p-10 relative overflow-hidden selection:bg-indigo-500 selection:text-white">
      <div 
        className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-[150px] pointer-events-none transition-colors duration-700 opacity-25"
        style={{ backgroundColor: config.primaryColor }}
      />
      <div 
        className="absolute top-1/2 -right-40 w-96 h-96 rounded-full blur-[150px] pointer-events-none transition-colors duration-700 opacity-20"
        style={{ backgroundColor: config.secondaryColor }}
      />

      <header className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 mb-8 pb-6 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div 
            className="w-11 h-11 rounded-2xl flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/10 transition-all"
            style={{ background: `linear-gradient(135deg, ${config.primaryColor}, ${config.secondaryColor})` }}
          >
            {config.companyName ? config.companyName.substring(0, 2).toUpperCase() : 'AG'}
          </div>
          <div>
            <h1 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
              {config.companyName}
              <span className="text-[10px] font-mono font-bold bg-slate-900 text-slate-300 border border-slate-800 px-2.5 py-0.5 rounded-full">
                {config.subdomain}
              </span>
            </h1>
            <p className="text-xs text-slate-400 font-medium">Autonomous HRMS &amp; Workforce Portal</p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <span className="bg-slate-900 border border-slate-800 text-slate-400 text-xs px-3 py-1.5 rounded-xl font-mono flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5 text-indigo-400" /> IdP: {config.ssoProvider}
          </span>

          <button
            onClick={resetToSetup}
            className="bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-all"
          >
            <Sliders className="w-3.5 h-3.5 text-indigo-400" /> Setup Wizard
          </button>

          <div className="flex items-center gap-3 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-xl">
            <div className="w-7 h-7 rounded-lg text-white font-bold text-xs flex items-center justify-center" style={{ backgroundColor: config.primaryColor }}>
              KV
            </div>
            <div className="text-left text-xs">
              <span className="block font-bold text-white">{config.adminName}</span>
              <span className="block text-[10px] text-slate-400">{config.adminEmail}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        <motion.div 
          className="md:col-span-2 bg-slate-900/60 border border-slate-800/80 rounded-3xl p-6 backdrop-blur-xl flex flex-col justify-between shadow-2xl relative overflow-hidden"
          whileHover={{ y: -3, borderColor: 'rgba(255,255,255,0.15)' }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        >
          <div className="flex justify-between items-start mb-6">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
                <DollarSign className="w-4 h-4 text-emerald-400" /> Total Compensation &amp; Equity Matrix
              </div>
              <h2 className="text-3xl font-black text-white tracking-tight">$240,000 <span className="text-xs font-normal text-slate-400">/ year</span></h2>
            </div>
            <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5" /> +12% Equity Vesting
            </span>
          </div>

          <div className="space-y-3 my-4">
            <div className="flex justify-between text-xs font-medium">
              <span className="text-slate-400">Vested Options (ISO Pool)</span>
              <span className="font-mono font-bold" style={{ color: config.primaryColor }}>12,500 / 20,000 Shares (62.5%)</span>
            </div>
            <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden border border-slate-800 p-0.5">
              <motion.div 
                className="h-full rounded-full"
                style={{ background: `linear-gradient(90deg, ${config.primaryColor}, ${config.secondaryColor})` }}
                initial={{ width: '0%' }}
                animate={{ width: '62.5%' }}
                transition={{ duration: 1.2, ease: 'easeOut' }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-slate-500 font-mono">
              <span>Cliff: Passed (1 Oct 2024)</span>
              <span>Next Vest: 15 Aug 2026 (+416 Shares)</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 pt-4 border-t border-slate-800/80 text-center text-xs">
            <div className="bg-slate-950/60 p-3 rounded-2xl border border-slate-800/50">
              <span className="block text-slate-400 mb-1">Base Salary</span>
              <span className="font-bold text-white font-mono">$180,000</span>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-2xl border border-slate-800/50">
              <span className="block text-slate-400 mb-1">Stock Value</span>
              <span className="font-bold font-mono" style={{ color: config.primaryColor }}>$60,000</span>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-2xl border border-slate-800/50">
              <span className="block text-slate-400 mb-1">Health Perks</span>
              <span className="font-bold text-emerald-400 font-mono">$4,800/yr</span>
            </div>
          </div>
        </motion.div>

        <motion.div 
          className="bg-slate-900/60 border border-slate-800/80 rounded-3xl p-6 backdrop-blur-xl flex flex-col justify-between shadow-2xl"
          whileHover={{ y: -3, borderColor: 'rgba(255,255,255,0.15)' }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <Zap className="w-4 h-4 text-cyan-400" /> Zero-Touch IT Hub
              </div>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>

            <h3 className="text-base font-bold text-white mb-1">Automated Licensing</h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Auto-grants Slack, GitHub &amp; Zoom upon hire. 1-click zero-touch offboarding data wipe.
            </p>

            <div className="grid grid-cols-2 gap-2 mb-4">
              {[
                { name: 'Slack', icon: Slack, ok: config.autoProvisionSlack },
                { name: 'GitHub', icon: Github, ok: config.autoProvisionGithub },
                { name: 'Google', icon: Mail, ok: true },
                { name: 'Zoom', icon: Video, ok: config.autoProvisionZoom }
              ].map((item, idx) => (
                <div key={idx} className="flex items-center justify-between bg-slate-950/80 border border-slate-800 px-3 py-2 rounded-xl text-xs">
                  <span className="flex items-center gap-2 text-slate-300 font-medium">
                    <item.icon className="w-3.5 h-3.5 text-slate-400" /> {item.name}
                  </span>
                  <CheckCircle2 className={`w-3.5 h-3.5 ${item.ok ? 'text-emerald-400' : 'text-slate-600'}`} />
                </div>
              ))}
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => { setOffboardModalOpen(true); setOffboardStep(0); }}
            className="w-full bg-slate-950 hover:bg-rose-950/30 border border-slate-800 hover:border-rose-500/40 text-slate-300 hover:text-rose-400 font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-2 transition-all group"
          >
            <UserX className="w-4 h-4 text-rose-400 group-hover:rotate-12 transition-transform" /> 
            Trigger Magic Offboarding
          </motion.button>
        </motion.div>

        {config.secopsEnabled ? (
          <motion.div 
            className="bg-indigo-950/20 border border-indigo-500/30 rounded-3xl p-6 backdrop-blur-xl flex flex-col justify-between shadow-2xl"
            whileHover={{ y: -3 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-300 uppercase tracking-wider">
                  <ShieldAlert className="w-4 h-4 text-indigo-400" /> SecOps Threat Center
                </div>
                <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full">
                  SIEM LIVE
                </span>
              </div>

              <h3 className="text-base font-bold text-white mb-2">Active Security Shield</h3>
              <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                SIEM event streams, active session maps, and SOAR playbooks provisioned for SecOps team.
              </p>

              <div className="space-y-2 text-xs font-mono">
                <div className="bg-slate-950/80 border border-slate-800 p-2.5 rounded-xl text-slate-300 flex justify-between">
                  <span>Blocked Malicious IPs</span>
                  <span className="text-emerald-400 font-bold">200 / day</span>
                </div>
                <div className="bg-slate-950/80 border border-slate-800 p-2.5 rounded-xl text-slate-300 flex justify-between">
                  <span>SecOps Officer</span>
                  <span className="text-indigo-400 font-bold">{config.secopsEmail || 'secops@acme.com'}</span>
                </div>
              </div>
            </div>

            <a href="/secops" className="w-full mt-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center gap-1.5 transition-all shadow-lg shadow-indigo-600/20">
              Launch SecOps Console →
            </a>
          </motion.div>
        ) : (
          <motion.div 
            className="bg-emerald-950/20 border border-emerald-500/30 rounded-3xl p-6 backdrop-blur-xl flex flex-col justify-between shadow-2xl"
            whileHover={{ y: -3 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-300 uppercase tracking-wider">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" /> Quiet Security
                </div>
                <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full">
                  AUTONOMOUS
                </span>
              </div>

              <h3 className="text-base font-bold text-white mb-2">Autonomous Security Shield</h3>
              <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                Background protection auto-blocks malicious IPs &amp; rate-limits endpoints without UI clutter.
              </p>

              <div className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-xl text-xs space-y-1">
                <span className="text-emerald-400 font-bold block flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 100% Protection Active
                </span>
                <span className="text-slate-400 block text-[11px]">Auto IP bans, rate limiting, and encrypted audit logging active.</span>
              </div>
            </div>

            <div className="text-[11px] text-slate-500 font-mono text-center">
              SecOps UI suppressed per tenant config
            </div>
          </motion.div>
        )}

        <motion.div 
          className="md:col-span-3 lg:col-span-4 bg-slate-900/60 border border-slate-800/80 rounded-3xl p-6 backdrop-blur-xl shadow-2xl"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
              <Award className="w-4 h-4 text-amber-400" /> Peer Recognition (Kudos Feed)
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Monthly Budget: <strong className="text-amber-400">{config.kudosMonthlyBudget} pts / emp</strong>
            </span>
          </div>

          <form onSubmit={handleSendKudos} className="bg-slate-950/80 border border-slate-800/80 p-4 rounded-2xl mb-6 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <input
                type="text"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="Recipient name (e.g. Alex Rivera)"
                className="bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
              />
              <select
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none"
              >
                {config.companyValues.map((v, i) => (
                  <option key={i} value={v}>{v}</option>
                ))}
              </select>
              <div className="flex gap-2">
                {[10, 25, 50].map((pts) => (
                  <button
                    key={pts}
                    type="button"
                    onClick={() => setPoints(pts)}
                    className={`flex-1 text-xs font-mono font-bold rounded-xl border transition-all ${
                      points === pts ? 'bg-amber-500/20 border-amber-500 text-amber-300' : 'bg-slate-900 border-slate-800 text-slate-400'
                    }`}
                  >
                    +{pts}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Write a message celebrating their contribution..."
                className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
              />
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="submit"
                className="text-white font-bold px-5 py-2 rounded-xl text-xs flex items-center gap-1.5 shadow-md transition-all shrink-0"
                style={{ backgroundColor: config.primaryColor }}
              >
                <Send className="w-3.5 h-3.5" /> Award Points
              </motion.button>
            </div>
          </form>

          <div className="space-y-3">
            <AnimatePresence>
              {kudosFeed.map((item) => (
                <motion.div 
                  key={item.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-slate-950/60 border border-slate-800/60 rounded-xl p-4 flex justify-between items-start gap-4"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1 text-xs">
                      <span className="font-bold text-white">{item.sender}</span>
                      <span className="text-slate-500">praised</span>
                      <span className="font-bold" style={{ color: config.primaryColor }}>{item.receiver}</span>
                      <span className="text-[10px] font-mono bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-slate-400">#{item.tag}</span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{item.message}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono text-xs font-bold px-2.5 py-1 rounded-full block mb-1">
                      +{item.points} pts
                    </span>
                    <span className="text-[10px] text-slate-500">{item.time}</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </motion.div>

      </main>

      <AnimatePresence>
        {offboardModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              className="fixed inset-0 bg-slate-950/80 backdrop-blur-md"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOffboardModalOpen(false)}
            />
            <motion.div
              className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl z-10 text-center"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
            >
              <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto mb-4 text-rose-400">
                <UserX className="w-6 h-6" />
              </div>

              <h3 className="text-lg font-bold text-white mb-1">Zero-Touch Magic Offboarding</h3>
              <p className="text-xs text-slate-400 mb-6">Instant 1-click access revocation &amp; asset wipe execution.</p>

              {!isProcessingOffboard && offboardStep === 0 ? (
                <div className="space-y-4">
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 text-left space-y-1">
                    <span className="font-bold block text-white">Target Employee: Sam Miller</span>
                    <span className="text-slate-400 block">Services: Slack, GitHub, Google Workspace, Figma</span>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => setOffboardModalOpen(false)}
                      className="flex-1 bg-slate-950 border border-slate-800 text-slate-400 font-bold py-2.5 rounded-xl text-xs"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleExecuteOffboarding}
                      className="flex-1 bg-rose-600 hover:bg-rose-500 text-white font-bold py-2.5 rounded-xl text-xs shadow-lg shadow-rose-600/20"
                    >
                      Revoke Access Now
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 text-left">
                  {[
                    { title: 'Revoking Slack & GitHub Tokens', done: offboardStep >= 1 },
                    { title: 'Wiping Google Workspace Sessions', done: offboardStep >= 2 },
                    { title: 'Sending Remote Device Lock Command', done: offboardStep >= 3 },
                    { title: 'Offboarding Audit Log Finalized', done: offboardStep >= 4 }
                  ].map((st, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-slate-950 border border-slate-800 p-3 rounded-xl text-xs">
                      <span className={st.done ? 'text-white font-medium' : 'text-slate-500'}>{st.title}</span>
                      {st.done ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : (
                        <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin shrink-0" />
                      )}
                    </div>
                  ))}

                  {offboardStep === 4 && (
                    <button
                      onClick={() => setOffboardModalOpen(false)}
                      className="w-full mt-4 bg-emerald-600 hover:bg-emerald-500 text-black font-bold py-2.5 rounded-xl text-xs shadow-md"
                    >
                      Close &amp; Return to Dashboard
                    </button>
                  )}
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
};
