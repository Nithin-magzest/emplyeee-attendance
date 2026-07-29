import React, { useState } from 'react';
import { Building2, Lock, Mail, Eye, EyeOff, ShieldCheck, ArrowRight, User, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const DEMO_ACCOUNTS = [
  { role: 'Super Admin', email: 'admin@omnihr.io', password: 'Admin@123', color: '#4F46E5', desc: 'Full system access' },
  { role: 'HR Manager', email: 'hr@omnihr.io', password: 'HRManager@2026', color: '#0284C7', desc: 'All HR modules' },
  { role: 'Employee ESS', email: 's.martinez@omnihr.io', password: 'Employee@123', color: '#059669', desc: 'Self-service only' },
];

export default function LoginPage({ onLoginSuccess }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) { setError('Email and password are required.'); return; }
    setError(''); setLoading(true);
    const result = await login(email.trim(), password);
    setLoading(false);
    if (result.success) onLoginSuccess(result.role);
    else setError(result.error || 'Authentication failed. Please verify your credentials.');
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', fontFamily: 'Inter, sans-serif',
      background: '#070B14',
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        @keyframes fadeIn { from{opacity:0} to{opacity:1} }
        @keyframes slideUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        .login-panel { animation: fadeIn 0.4s ease; }
        .login-form { animation: slideUp 0.45s ease; }
        .demo-pill { transition: all 0.15s; cursor:pointer; }
        .demo-pill:hover { filter:brightness(1.15); transform:translateY(-1px); }
        .submit-btn { transition: all 0.15s; }
        .submit-btn:hover:not(:disabled) { filter:brightness(1.1); transform:translateY(-1px); box-shadow: 0 8px 24px rgba(79,70,229,0.45) !important; }
        .inp { transition: border-color 0.2s, box-shadow 0.2s; }
        .inp:focus { outline:none; border-color: rgba(79,70,229,0.7) !important; box-shadow: 0 0 0 3px rgba(79,70,229,0.12); }
      `}</style>

      {/* Left: Branding Panel */}
      <div className="login-panel" style={{
        width: '45%', background: 'linear-gradient(160deg, #0D1321 0%, #111827 60%, #0A0E1A 100%)',
        borderRight: '1px solid #1F2937', padding: '60px 56px',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '44px', height: '44px', borderRadius: '12px',
            background: 'linear-gradient(135deg, #4F46E5, #0284C7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(79,70,229,0.4)',
          }}>
            <Building2 size={22} color="white" />
          </div>
          <div>
            <p style={{ color: '#F9FAFB', fontWeight: 800, fontSize: '18px', margin: 0, letterSpacing: '-0.02em' }}>OmniHR Premier</p>
            <p style={{ color: '#4B5563', fontSize: '11px', margin: 0, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Enterprise Edition</p>
          </div>
        </div>

        {/* Center content */}
        <div>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            padding: '5px 12px', borderRadius: '99px',
            background: 'rgba(79,70,229,0.12)', border: '1px solid rgba(79,70,229,0.25)',
            color: '#818CF8', fontSize: '11px', fontWeight: 600,
            textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '24px',
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#4F46E5', display: 'inline-block' }} />
            Trusted by 2,400+ enterprises
          </div>
          <h1 style={{
            color: '#F9FAFB', fontSize: '40px', fontWeight: 800, lineHeight: 1.15,
            letterSpacing: '-0.03em', marginBottom: '20px',
          }}>
            One platform for your<br />
            <span style={{ background: 'linear-gradient(135deg, #6366F1, #0284C7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              entire workforce
            </span>
          </h1>
          <p style={{ color: '#6B7280', fontSize: '15px', lineHeight: 1.7, maxWidth: '380px' }}>
            Manage 60,000+ employees across 150+ countries with AI-powered HR, global payroll, compliance, and workforce analytics — in one unified platform.
          </p>

          {/* Feature bullets */}
          <div style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {[
              'Global payroll in 150+ countries with auto-compliance',
              'AI-powered talent management and 9-box succession',
              'SOC 2 Type II · ISO 27001 · GDPR certified',
              'Real-time workforce analytics and predictive insights',
            ].map(f => (
              <div key={f} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <CheckCircle size={16} color="#059669" style={{ flexShrink: 0, marginTop: '2px' }} />
                <span style={{ color: '#9CA3AF', fontSize: '13px' }}>{f}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: '32px' }}>
          {[
            { value: '60K+', label: 'Employees Managed' },
            { value: '150+', label: 'Countries' },
            { value: '99.99%', label: 'Uptime SLA' },
          ].map(({ value, label }) => (
            <div key={label}>
              <p style={{ color: '#F9FAFB', fontWeight: 800, fontSize: '22px', margin: 0 }}>{value}</p>
              <p style={{ color: '#4B5563', fontSize: '11px', margin: '2px 0 0' }}>{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right: Login Form */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '40px 60px',
      }}>
        <div className="login-form" style={{ width: '100%', maxWidth: '420px' }}>
          {/* Header */}
          <div style={{ marginBottom: '32px' }}>
            <h2 style={{ color: '#F9FAFB', fontSize: '24px', fontWeight: 800, margin: '0 0 6px', letterSpacing: '-0.02em' }}>
              Sign in to your account
            </h2>
            <p style={{ color: '#6B7280', fontSize: '13px', margin: 0 }}>
              Enter your credentials to access your workspace
            </p>
          </div>

          {/* Error */}
          {error && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '12px 14px', borderRadius: '10px', marginBottom: '20px',
              background: 'rgba(220,38,38,0.1)', border: '1px solid rgba(220,38,38,0.3)',
            }}>
              <AlertCircle size={15} color="#F87171" style={{ flexShrink: 0 }} />
              <span style={{ color: '#F87171', fontSize: '13px' }}>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', color: '#9CA3AF', fontSize: '12px', fontWeight: 600, marginBottom: '7px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Work Email
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={15} color="#4B5563" style={{ position: 'absolute', left: '13px', top: '50%', transform: 'translateY(-50%)' }} />
                <input className="inp" type="email" value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com" autoComplete="email"
                  style={{
                    width: '100%', padding: '11px 12px 11px 38px', boxSizing: 'border-box',
                    background: '#0D1321', border: '1px solid #1F2937',
                    borderRadius: '10px', color: '#F9FAFB', fontSize: '13px',
                    fontFamily: 'Inter, sans-serif',
                  }} />
              </div>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '7px' }}>
                <label style={{ color: '#9CA3AF', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Password</label>
                <span style={{ color: '#4F46E5', fontSize: '12px', cursor: 'pointer', fontWeight: 500 }}>Forgot password?</span>
              </div>
              <div style={{ position: 'relative' }}>
                <Lock size={15} color="#4B5563" style={{ position: 'absolute', left: '13px', top: '50%', transform: 'translateY(-50%)' }} />
                <input className="inp" type={showPass ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••••••" autoComplete="current-password"
                  style={{
                    width: '100%', padding: '11px 38px 11px 38px', boxSizing: 'border-box',
                    background: '#0D1321', border: '1px solid #1F2937',
                    borderRadius: '10px', color: '#F9FAFB', fontSize: '13px',
                    fontFamily: 'Inter, sans-serif',
                  }} />
                <button type="button" onClick={() => setShowPass(v => !v)} style={{
                  position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer', color: '#4B5563', display: 'flex',
                }}>
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="submit-btn"
              style={{
                width: '100%', padding: '13px', border: 'none', borderRadius: '10px',
                background: loading ? '#2D2D5E' : 'linear-gradient(135deg, #4F46E5, #4338CA)',
                color: 'white', fontWeight: 700, fontSize: '14px', cursor: loading ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                fontFamily: 'Inter, sans-serif', boxShadow: '0 4px 16px rgba(79,70,229,0.35)',
              }}>
              {loading ? (
                <>
                  <div style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', borderRadius: '50%', animation: 'spin 0.75s linear infinite' }} />
                  Authenticating...
                </>
              ) : (
                <> <ShieldCheck size={16} /> Sign In to OmniHR <ArrowRight size={16} /> </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '28px 0 20px' }}>
            <div style={{ flex: 1, height: '1px', background: '#1F2937' }} />
            <span style={{ color: '#374151', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Demo Accounts</span>
            <div style={{ flex: 1, height: '1px', background: '#1F2937' }} />
          </div>

          {/* Demo Pills */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {DEMO_ACCOUNTS.map(acc => (
              <button key={acc.email} onClick={() => { setEmail(acc.email); setPassword(acc.password); setError(''); }}
                className="demo-pill"
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px', borderRadius: '10px', border: `1px solid ${acc.color}30`,
                  background: `${acc.color}0D`, cursor: 'pointer', fontFamily: 'Inter, sans-serif', width: '100%',
                }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: `${acc.color}20`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {acc.role === 'Employee ESS' ? <User size={13} color={acc.color} /> : <ShieldCheck size={13} color={acc.color} />}
                  </div>
                  <div style={{ textAlign: 'left' }}>
                    <p style={{ color: '#E5E7EB', fontSize: '13px', fontWeight: 600, margin: 0 }}>{acc.role}</p>
                    <p style={{ color: '#6B7280', fontSize: '11px', margin: '1px 0 0' }}>{acc.desc}</p>
                  </div>
                </div>
                <span style={{ color: acc.color, fontSize: '11px', fontWeight: 600, fontFamily: 'monospace' }}>
                  Click to fill →
                </span>
              </button>
            ))}
          </div>

          {/* Security footer */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px', marginTop: '32px' }}>
            {['SOC 2 Type II', 'ISO 27001', 'GDPR'].map(cert => (
              <div key={cert} style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#374151', fontSize: '10px', fontWeight: 600 }}>
                <ShieldCheck size={11} color="#374151" />
                {cert}
              </div>
            ))}
          </div>
          <p style={{ textAlign: 'center', color: '#1F2937', fontSize: '11px', marginTop: '10px' }}>
            256-bit AES · TLS 1.3 · Zero-trust architecture
          </p>
        </div>
      </div>
    </div>
  );
}
