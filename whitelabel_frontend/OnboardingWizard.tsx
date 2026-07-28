import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTenant, TenantConfig } from './TenantContext';
import {
  Building2,
  Palette,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  Zap,
  Lock,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Slack,
  Github,
  Video,
  Figma,
  Check
} from 'lucide-react';

interface PaletteOption {
  name: string;
  primary: string;
  secondary: string;
}

const PRESET_PALETTES: PaletteOption[] = [
  { name: 'Linear Indigo / Violet', primary: '#6366f1', secondary: '#8b5cf6' },
  { name: 'Stripe Cyan / Slate', primary: '#0ea5e9', secondary: '#6366f1' },
  { name: 'Vercel Emerald / Mint', primary: '#10b981', secondary: '#059669' },
  { name: 'HiBob Amber / Coral', primary: '#f59e0b', secondary: '#f43f5e' },
  { name: 'Workday Ruby / Rose', primary: '#e11d48', secondary: '#9333ea' }
];

export const OnboardingWizard: React.FC = () => {
  const { config, updateConfig, completeSetup } = useTenant();

  const [step, setStep] = useState<number>(1);
  const [deployStep, setDeployStep] = useState<number>(0);

  // Step 1 State: Identity & Culture (HiBob Model)
  const [companyName, setCompanyName] = useState<string>(config.companyName);
  const [subdomain, setSubdomain] = useState<string>(config.subdomain);
  const [companySize, setCompanySize] = useState<'1-50' | '50-500' | '500+'>(config.companySize);
  const [primaryColor, setPrimaryColor] = useState<string>(config.primaryColor);
  const [secondaryColor, setSecondaryColor] = useState<string>(config.secondaryColor);
  const [kudosBudget, setKudosBudget] = useState<number>(config.kudosMonthlyBudget);

  // Step 2 State: IT Provisioning & SSO (Rippling Model)
  const [ssoProvider, setSsoProvider] = useState<'GOOGLE_WORKSPACE' | 'AZURE_AD' | 'OKTA' | 'EMAIL_PASS'>(config.ssoProvider);
  const [autoSlack, setAutoSlack] = useState<boolean>(config.autoProvisionSlack);
  const [autoGithub, setAutoGithub] = useState<boolean>(config.autoProvisionGithub);
  const [autoZoom, setAutoZoom] = useState<boolean>(config.autoProvisionZoom);
  const [autoFigma, setAutoFigma] = useState<boolean>(config.autoProvisionFigma);

  // Step 3 State: Security & SecOps (Workday Model)
  const [secopsEnabled, setSecopsEnabled] = useState<boolean>(config.secopsEnabled);

  // Step 4 State: Master Credentials
  const [adminName, setAdminName] = useState<string>(config.adminName);
  const [adminEmail, setAdminEmail] = useState<string>(config.adminEmail);
  const [adminPass, setAdminPass] = useState<string>('');
  const [secopsEmail, setSecopsEmail] = useState<string>(config.secopsEmail);
  const [secopsPass, setSecopsPass] = useState<string>('');

  // Live Palette Switcher with Immediate Background Re-theming
  const applyPalette = (p: string, s: string) => {
    setPrimaryColor(p);
    setSecondaryColor(s);
    updateConfig({ primaryColor: p, secondaryColor: s });
  };

  // Step 5 Deployment Animation
  const startDeployment = () => {
    setStep(5);
    const steps = [
      { s: 1, delay: 600 },
      { s: 2, delay: 1200 },
      { s: 3, delay: 1800 },
      { s: 4, delay: 2400 }
    ];

    steps.forEach(({ s, delay }) => {
      setTimeout(() => {
        setDeployStep(s);
        if (s === 4) {
          setTimeout(() => {
            completeSetup({
              companyName,
              subdomain,
              companySize,
              primaryColor,
              secondaryColor,
              kudosMonthlyBudget: kudosBudget,
              ssoProvider,
              autoProvisionSlack: autoSlack,
              autoProvisionGithub: autoGithub,
              autoProvisionZoom: autoZoom,
              autoProvisionFigma: autoFigma,
              secopsEnabled,
              adminName,
              adminEmail,
              secopsEmail
            });
          }, 800);
        }
      }, delay);
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-hidden">
      <div className="absolute inset-0 bg-slate-950/85 backdrop-blur-2xl transition-colors duration-500" />

      <div 
        className="absolute w-[650px] h-[650px] rounded-full blur-[150px] pointer-events-none transition-colors duration-700 opacity-30"
        style={{ backgroundColor: primaryColor }}
      />

      <motion.div
        className="relative w-full max-w-2xl bg-slate-900/90 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden backdrop-blur-2xl z-10 flex flex-col max-h-[90vh]"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
      >
        <div className="p-6 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div 
              className="w-10 h-10 rounded-2xl flex items-center justify-center text-white font-bold shadow-lg"
              style={{ background: `linear-gradient(135deg, ${primaryColor}, ${secondaryColor})` }}
            >
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-black text-white tracking-tight">Enterprise Setup Wizard</h2>
              <p className="text-xs text-slate-400">Configure tenant branding, IdP, and SecOps boundaries</p>
            </div>
          </div>

          <div className="flex items-center gap-1 font-mono text-xs">
            {[1, 2, 3, 4, 5].map((s) => (
              <div
                key={s}
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  step === s 
                    ? 'text-white shadow-md' 
                    : step > s 
                    ? 'bg-slate-800 text-emerald-400' 
                    : 'bg-slate-950 text-slate-600'
                }`}
                style={step === s ? { backgroundColor: primaryColor } : {}}
              >
                {step > s ? <Check className="w-3.5 h-3.5" /> : s}
              </div>
            ))}
          </div>
        </div>

        <div className="p-6 sm:p-8 overflow-y-auto flex-1 space-y-6">
          <AnimatePresence mode="wait">
            
            {step === 1 && (
              <motion.div key="st1" initial={{ opacity: 0, x: 15 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -15 }} className="space-y-6">
                <div>
                  <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-indigo-400" /> Step 1: Branding &amp; Culture Identity (HiBob Model)
                  </h3>
                  <p className="text-xs text-slate-400">Enter company name and select real-time brand accent colors.</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Company Name *</label>
                    <input
                      type="text"
                      value={companyName}
                      onChange={(e) => { setCompanyName(e.target.value); updateConfig({ companyName: e.target.value }); }}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Subdomain</label>
                    <input
                      type="text"
                      value={subdomain}
                      onChange={(e) => setSubdomain(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-2">
                    <Palette className="w-4 h-4 text-purple-400" /> Select Brand Accent (Live Preview)
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {PRESET_PALETTES.map((pal, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => applyPalette(pal.primary, pal.secondary)}
                        className={`flex items-center justify-between p-3 rounded-xl border text-xs text-left transition-all ${
                          primaryColor === pal.primary ? 'bg-slate-950 border-indigo-500' : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <span className="font-semibold text-slate-200">{pal.name}</span>
                        <div className="flex items-center gap-1.5">
                          <span className="w-4 h-4 rounded-full border border-slate-700" style={{ backgroundColor: pal.primary }} />
                          <span className="w-4 h-4 rounded-full border border-slate-700" style={{ backgroundColor: pal.secondary }} />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div key="st2" initial={{ opacity: 0, x: 15 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -15 }} className="space-y-6">
                <div>
                  <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-cyan-400" /> Step 2: IT Provisioning &amp; Identity Setup (Rippling Model)
                  </h3>
                  <p className="text-xs text-slate-400">Configure single sign-on providers and zero-touch day-1 app licensing.</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Default SSO Provider</label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {[
                      { id: 'GOOGLE_WORKSPACE', label: 'Google' },
                      { id: 'AZURE_AD', label: 'Azure AD' },
                      { id: 'OKTA', label: 'Okta SSO' },
                      { id: 'EMAIL_PASS', label: 'Email / Pass' }
                    ].map((idp) => (
                      <button
                        key={idp.id}
                        type="button"
                        onClick={() => setSsoProvider(idp.id as any)}
                        className={`p-3 rounded-xl border text-xs font-bold transition-all ${
                          ssoProvider === idp.id ? 'bg-indigo-950/40 border-indigo-500 text-indigo-300' : 'bg-slate-950 border-slate-800 text-slate-400'
                        }`}
                      >
                        {idp.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Automated App Provisioning Rules</label>
                  <div className="grid grid-cols-2 gap-2.5">
                    {[
                      { name: 'Slack Workspace', state: autoSlack, set: setAutoSlack, icon: Slack },
                      { name: 'GitHub Enterprise', state: autoGithub, set: setAutoGithub, icon: Github },
                      { name: 'Zoom Business', state: autoZoom, set: setAutoZoom, icon: Video },
                      { name: 'Figma Enterprise', state: autoFigma, set: setAutoFigma, icon: Figma }
                    ].map((app, idx) => (
                      <div
                        key={idx}
                        onClick={() => app.set(!app.state)}
                        className={`p-3 rounded-xl border cursor-pointer flex items-center justify-between text-xs transition-all ${
                          app.state ? 'bg-slate-950 border-emerald-500/50 text-white' : 'bg-slate-950/60 border-slate-800 text-slate-500'
                        }`}
                      >
                        <span className="flex items-center gap-2 font-semibold">
                          <app.icon className="w-4 h-4 text-slate-400" /> {app.name}
                        </span>
                        <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${app.state ? 'bg-emerald-500 border-emerald-500 text-black' : 'border-slate-700'}`}>
                          {app.state && <Check className="w-3 h-3 stroke-[3]" />}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div key="st3" initial={{ opacity: 0, x: 15 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -15 }} className="space-y-6">
                <div>
                  <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-amber-400" /> Step 3: Security &amp; SecOps Architecture (Workday Model)
                  </h3>
                  <p className="text-xs text-slate-400">Select whether to expose a dedicated SecOps Threat Center or activate Quiet Security.</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div
                    onClick={() => setSecopsEnabled(true)}
                    className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                      secopsEnabled ? 'bg-indigo-950/30 border-indigo-500' : 'bg-slate-950/60 border-slate-800'
                    }`}
                  >
                    <div className="flex justify-between mb-2">
                      <ShieldAlert className="w-5 h-5 text-indigo-400" />
                      <span className="text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full">VISUAL SECOPS</span>
                    </div>
                    <h4 className="text-sm font-bold text-white mb-1">Visual SecOps Threat Center</h4>
                    <p className="text-xs text-slate-400">SIEM live logs, active session maps, anomaly alerts &amp; SOAR playbooks.</p>
                  </div>

                  <div
                    onClick={() => setSecopsEnabled(false)}
                    className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                      !secopsEnabled ? 'bg-emerald-950/30 border-emerald-500' : 'bg-slate-950/60 border-slate-800'
                    }`}
                  >
                    <div className="flex justify-between mb-2">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <span className="text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full">QUIET SECURITY</span>
                    </div>
                    <h4 className="text-sm font-bold text-white mb-1">Autonomous Quiet Shield</h4>
                    <p className="text-xs text-slate-400">Hides SecOps UI. Auto-blocks bad IPs, rate-limits &amp; logs audit trails silently.</p>
                  </div>
                </div>
              </motion.div>
            )}

            {step === 4 && (
              <motion.div key="st4" initial={{ opacity: 0, x: 15 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -15 }} className="space-y-6">
                <div>
                  <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
                    <Lock className="w-4 h-4 text-emerald-400" /> Step 4: Admin Accounts &amp; RBAC Boundaries
                  </h3>
                  <p className="text-xs text-slate-400">Configure master accounts for HR Administration and SecOps Security.</p>
                </div>

                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl space-y-3">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">Master HR Admin</span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input
                      type="email"
                      value={adminEmail}
                      onChange={(e) => setAdminEmail(e.target.value)}
                      placeholder="admin@company.com"
                      className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
                    />
                    <input
                      type="password"
                      value={adminPass}
                      onChange={(e) => setAdminPass(e.target.value)}
                      placeholder="Master Admin Password"
                      className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
                    />
                  </div>
                </div>

                {secopsEnabled && (
                  <div className="p-4 bg-indigo-950/20 border border-indigo-500/30 rounded-2xl space-y-3">
                    <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider block">SecOps Security Lead (RBAC Isolated)</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <input
                        type="email"
                        value={secopsEmail}
                        onChange={(e) => setSecopsEmail(e.target.value)}
                        placeholder="secops@company.com"
                        className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
                      />
                      <input
                        type="password"
                        value={secopsPass}
                        onChange={(e) => setSecopsPass(e.target.value)}
                        placeholder="SecOps Password"
                        className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
                      />
                    </div>
                  </div>
                )}
              </motion.div>
            )}

            {step === 5 && (
              <motion.div key="st5" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-6 text-center py-4">
                <div className="w-12 h-12 rounded-2xl mx-auto flex items-center justify-center text-white font-bold animate-bounce" style={{ backgroundColor: primaryColor }}>
                  <Zap className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-black text-white">Deploying Tenant Workspace...</h3>

                <div className="space-y-2.5 max-w-sm mx-auto text-left">
                  {[
                    { label: `Provisioning Schema (${companyName})`, done: deployStep >= 1 },
                    { label: `Injecting CSS Custom Properties (${primaryColor})`, done: deployStep >= 2 },
                    { label: secopsEnabled ? 'Enabling SecOps Threat Center' : 'Activating Quiet Shield', done: deployStep >= 3 },
                    { label: 'Unlocking Next-Gen Bento Dashboard', done: deployStep >= 4 }
                  ].map((st, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-950 border border-slate-800 p-3 rounded-xl text-xs">
                      <span className={st.done ? 'text-white font-semibold' : 'text-slate-500'}>{st.label}</span>
                      {st.done ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <span className="w-3 h-3 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>

        {step < 5 && (
          <div className="p-6 border-t border-slate-800/80 bg-slate-950/60 flex justify-between items-center">
            {step > 1 ? (
              <button onClick={() => setStep(step - 1)} className="bg-slate-950 border border-slate-800 text-slate-300 font-bold px-4 py-2.5 rounded-xl text-xs flex items-center gap-1.5">
                <ArrowLeft className="w-4 h-4" /> Back
              </button>
            ) : <div />}

            {step < 4 ? (
              <button onClick={() => setStep(step + 1)} className="text-white font-bold px-6 py-2.5 rounded-xl text-xs flex items-center gap-1.5 shadow-lg" style={{ backgroundColor: primaryColor }}>
                Continue <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button onClick={startDeployment} className="text-white font-extrabold px-6 py-2.5 rounded-xl text-xs flex items-center gap-1.5 shadow-lg" style={{ backgroundColor: primaryColor }}>
                🚀 Launch White-Label Portal
              </button>
            )}
          </div>
        )}
      </motion.div>

    </div>
  );
};
