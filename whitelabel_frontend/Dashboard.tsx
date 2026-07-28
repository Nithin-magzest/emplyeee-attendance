import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useTenant } from './TenantContext';
import { SecOpsThreatCenter } from './SecOpsThreatCenter';
import {
  DollarSign,
  TrendingUp,
  Award,
  Send,
  Zap,
  ShieldCheck,
  Globe,
  Sliders,
  Slack,
  Github,
  Video,
  Figma,
  CheckCircle2
} from 'lucide-react';

interface KudosItem {
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

  const [recipient, setRecipient] = useState<string>('');
  const [points, setPoints] = useState<number>(25);
  const [tag, setTag] = useState<string>('Customer Obsession');
  const [message, setMessage] = useState<string>('');
  const [feed, setFeed] = useState<KudosItem[]>([
    {
      id: '1',
      sender: 'Sarah Jenkins',
      receiver: 'Alex Rivera',
      points: 50,
      tag: 'Ownership',
      message: 'Alex resolved the auth pipeline bottleneck single-handedly. Fantastic work!',
      time: '12 mins ago'
    },
    {
      id: '2',
      sender: 'Michael Chen',
      receiver: 'Elena Rostova',
      points: 25,
      tag: 'Customer Obsession',
      message: 'Elena spent 2 hours onboarding our enterprise client smoothly.',
      time: '1 hour ago'
    }
  ]);

  const handleSendKudos = (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipient || !message) return;
    setFeed([{
      id: Date.now().toString(),
      sender: 'You',
      receiver: recipient,
      points,
      tag,
      message,
      time: 'Just now'
    }, ...feed]);
    setRecipient('');
    setMessage('');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 sm:p-10 relative overflow-hidden">
      <div 
        className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-[140px] pointer-events-none transition-colors duration-700 opacity-25"
        style={{ backgroundColor: config.primaryColor }}
      />
      <div 
        className="absolute top-1/2 -right-40 w-96 h-96 rounded-full blur-[140px] pointer-events-none transition-colors duration-700 opacity-20"
        style={{ backgroundColor: config.secondaryColor }}
      />

      <header className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 mb-8 pb-6 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div 
            className="w-11 h-11 rounded-2xl flex items-center justify-center text-white font-bold shadow-lg transition-all"
            style={{ background: `linear-gradient(135deg, ${config.primaryColor}, ${config.secondaryColor})` }}
          >
            {config.companyName ? config.companyName.substring(0, 2).toUpperCase() : 'AG'}
          </div>
          <div>
            <h1 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
              {config.companyName}
              <span className="text-[10px] font-mono font-bold bg-slate-900 text-slate-300 border border-slate-800 px-2 py-0.5 rounded-full">
                {config.subdomain}
              </span>
            </h1>
            <p className="text-xs text-slate-400 font-medium">Enterprise HRMS &amp; Workforce Portal</p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <span className="bg-slate-900 border border-slate-800 text-slate-400 text-xs px-3 py-1.5 rounded-xl font-mono flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5 text-indigo-400" /> IdP: {config.ssoProvider}
          </span>

          <button
            onClick={resetToSetup}
            className="bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-all"
          >
            <Sliders className="w-3.5 h-3.5 text-indigo-400" /> Re-Configure White-Label
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

      <main className="max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          
          <motion.div 
            className="md:col-span-2 bg-slate-900/60 border border-slate-800/80 rounded-3xl p-6 backdrop-blur-xl flex flex-col justify-between shadow-xl"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
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
                <div 
                  className="h-full rounded-full transition-all duration-1000"
                  style={{ width: '62.5%', background: `linear-gradient(90deg, ${config.primaryColor}, ${config.secondaryColor})` }}
                />
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
            className="bg-slate-900/60 border border-slate-800/80 rounded-3xl p-6 backdrop-blur-xl flex flex-col justify-between shadow-xl"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <Zap className="w-4 h-4 text-cyan-400" /> IT Provisioning Rules
                </div>
              </div>

              <div className="space-y-2">
                {[
                  { name: 'Slack Workspace', active: config.autoProvisionSlack, icon: Slack },
                  { name: 'GitHub Enterprise', active: config.autoProvisionGithub, icon: Github },
                  { name: 'Zoom Business', active: config.autoProvisionZoom, icon: Video },
                  { name: 'Figma Enterprise', active: config.autoProvisionFigma, icon: Figma }
                ].map((app, idx) => (
                  <div key={idx} className="flex items-center justify-between bg-slate-950/80 border border-slate-800 p-2.5 rounded-xl text-xs">
                    <span className="flex items-center gap-2 text-slate-300 font-medium">
                      <app.icon className="w-3.5 h-3.5 text-slate-400" /> {app.name}
                    </span>
                    <span className={`text-[10px] font-mono font-bold ${app.active ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {app.active ? 'AUTO-GRANTED' : 'OFF'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 text-center text-[11px] text-slate-500 font-mono">
              Identities Synced via {config.ssoProvider}
            </div>
          </motion.div>

          {!config.secopsEnabled && (
            <motion.div 
              className="bg-emerald-950/20 border border-emerald-500/30 rounded-3xl p-6 backdrop-blur-xl flex flex-col justify-between shadow-xl"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
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
                  Background protection is auto-blocking malicious IPs and rate-limiting endpoints without UI clutter.
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

        </div>

        {config.secopsEnabled && <SecOpsThreatCenter />}

      </main>
    </div>
  );
};
