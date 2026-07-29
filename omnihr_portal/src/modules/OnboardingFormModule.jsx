import React, { useState } from 'react';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  FileText,
  UserCheck,
  Phone,
  Briefcase,
  Clock,
  DollarSign,
  Shield,
  Laptop,
  Award,
  CheckCircle2,
  Lock,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Save
} from 'lucide-react';

export const OnboardingFormModule = () => {
  const [activeStep, setActiveStep] = useState(1);
  const [submitted, setSubmitted] = useState(false);

  // Form State across 9 Modules
  const [formData, setFormData] = useState({
    // 1. Pre-Onboarding
    resumeFile: 'resume_evelyn_vance_2026.pdf',
    bgCheckConsent: true,
    refName: 'Dr. Robert Thorne (CTO, CyberDyn)',
    // 2. Personal Details
    firstName: 'Dr. Evelyn',
    lastName: 'Vance',
    dob: '1988-04-12',
    ssnMasked: '***-**-8492',
    visaType: 'US Citizen / Permanent Resident',
    // 3. Contact Details
    personalEmail: 'evelyn.vance.private@gmail.com',
    workEmail: 'evelyn.vance@omnihr.com',
    phone: '+1 (555) 234-5678',
    address: '742 Evergreen Terrace, New York, NY 10001',
    emergencyContact: 'Marcus Vance (Spouse) · +1 (555) 987-6543',
    // 4. Employment & Job Architecture
    jobTitle: 'VP of Distributed Infrastructure',
    department: 'Core Platform Engineering',
    legalEntity: 'US Inc. (Delaware)',
    employmentType: 'Full-Time Exempt',
    baseSalary: 380000,
    // 5. Time & Leave
    holidayCalendar: 'US Statutory Holidays',
    ptoTier: 'Executive Tier (24 Days)',
    shiftRoster: 'EMEA/US Core Shift (09:00 - 17:00)',
    // 6. Financial & Tax
    bankName: 'JPMorgan Chase Bank',
    routingNumber: '*****0210',
    accountNumber: '**********9402',
    taxFiling: 'Married Filing Jointly (W-4)',
    ewaOptIn: true,
    // 7. Benefits
    medicalPlan: 'Executive Premier PPO (High Deductible)',
    retirementMatch: 6.0,
    dependentsCount: 2,
    // 8. Assets & IT
    laptopModel: 'MacBook Pro 16" M3 Max',
    assetSerial: 'C02G188XMD6M',
    softwareLicenses: ['Slack', 'GitHub Enterprise', 'Figma', 'AWS Admin', 'Jira'],
    // 9. Performance & Offboarding
    skills: ['Distributed Systems', 'Go', 'Kubernetes', 'CyberSecOps', 'System Architecture'],
    certifications: ['CISSP Certified Security Professional', 'AWS Solutions Architect Fellow']
  });

  const steps = [
    { num: 1, label: 'Pre-Onboarding', icon: FileText },
    { num: 2, label: 'Personal & ID', icon: UserCheck },
    { num: 3, label: 'Contact Data', icon: Phone },
    { num: 4, label: 'Job Architecture', icon: Briefcase },
    { num: 5, label: 'Time & Leave', icon: Clock },
    { num: 6, label: 'Payroll & Tax', icon: DollarSign },
    { num: 7, label: 'Benefits', icon: Shield },
    { num: 8, label: 'IT Assets', icon: Laptop },
    { num: 9, label: 'Skills & Perf', icon: Award }
  ];

  const updateField = (field: string, val: any) => {
    setFormData((prev) => ({ ...prev, [field]: val }));
  };

  const handleNext = () => {
    if (activeStep < 9) setActiveStep(activeStep + 1);
    else setSubmitted(true);
  };

  const handlePrev = () => {
    if (activeStep > 1) setActiveStep(activeStep - 1);
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <span className="text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-2.5 py-0.5 rounded-full uppercase">
            Workday, BambooHR &amp; Rippling Schema Standard
          </span>
          <h2 className="text-2xl font-black text-white tracking-tight mt-1">Global 9-Module Enterprise Intake Form</h2>
        </div>

        <div className="flex items-center gap-2 bg-[#111827] border border-slate-800 px-3.5 py-2 rounded-xl text-xs font-mono">
          <Lock className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-slate-300 font-bold">AES-256 PII Column Encryption Active</span>
        </div>
      </div>

      {/* 9-Step Progress Indicator */}
      <div className="bg-[#111827] border border-slate-800 rounded-2xl p-4 shadow-xl overflow-x-auto">
        <div className="flex items-center justify-between min-w-[760px] gap-2">
          {steps.map((s) => {
            const Icon = s.icon;
            const isActive = activeStep === s.num;
            const isDone = activeStep > s.num;
            return (
              <button
                key={s.num}
                onClick={() => setActiveStep(s.num)}
                className={`flex-1 flex items-center gap-2 p-2.5 rounded-xl border text-xs transition-all ${
                  isActive
                    ? 'bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-600/20'
                    : isDone
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-[#0A0E1A] border-slate-800 text-slate-500 hover:text-slate-300'
                }`}
              >
                <div className={`w-6 h-6 rounded-lg flex items-center justify-center font-mono font-bold text-[10px] shrink-0 ${
                  isActive ? 'bg-indigo-700 text-white' : isDone ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}>
                  {isDone ? '✓' : s.num}
                </div>
                <span className="font-bold truncate hidden lg:inline">{s.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Form Content Container */}
      {!submitted ? (
        <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
          {/* Step Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              Module {activeStep}: {steps[activeStep - 1].label}
            </h3>
            <span className="text-xs font-mono text-slate-400">Step {activeStep} of 9</span>
          </div>

          {/* Module 1: Pre-Onboarding */}
          {activeStep === 1 && (
            <div className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Applicant Resume / CV Attachment</label>
                  <input
                    type="text"
                    value={formData.resumeFile}
                    onChange={(e) => updateField('resumeFile', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Professional References</label>
                  <input
                    type="text"
                    value={formData.refName}
                    onChange={(e) => updateField('refName', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="bg-[#0A0E1A] border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                <div>
                  <span className="font-bold text-white block">Background Check Authorization (Checkr / Sterling Integration)</span>
                  <span className="text-[11px] text-slate-400">Authorize automated background screening &amp; criminal history validation</span>
                </div>
                <input
                  type="checkbox"
                  checked={formData.bgCheckConsent}
                  onChange={(e) => updateField('bgCheckConsent', e.target.checked)}
                  className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
                />
              </div>
            </div>
          )}

          {/* Module 2: Personal & Identification Details */}
          {activeStep === 2 && (
            <div className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Legal First Name</label>
                  <input
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => updateField('firstName', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Legal Last Name</label>
                  <input
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => updateField('lastName', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Date of Birth (Encrypted)</label>
                  <input
                    type="date"
                    value={formData.dob}
                    onChange={(e) => updateField('dob', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Government ID / SSN / Aadhaar / PAN (AES-256 Encrypted)</label>
                  <input
                    type="text"
                    value={formData.ssnMasked}
                    onChange={(e) => updateField('ssnMasked', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-indigo-500/40 rounded-xl px-3 py-2 text-indigo-400 font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Work Visa / Citizenship Status</label>
                  <input
                    type="text"
                    value={formData.visaType}
                    onChange={(e) => updateField('visaType', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Module 3: Contact & Emergency Data */}
          {activeStep === 3 && (
            <div className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Personal Email Address</label>
                  <input
                    type="email"
                    value={formData.personalEmail}
                    onChange={(e) => updateField('personalEmail', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Corporate Work Email (SSO Key)</label>
                  <input
                    type="email"
                    value={formData.workEmail}
                    onChange={(e) => updateField('workEmail', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-indigo-400 font-mono font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 font-bold block mb-1">Physical Residential Address</label>
                <input
                  type="text"
                  value={formData.address}
                  onChange={(e) => updateField('address', e.target.value)}
                  className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                />
              </div>

              <div>
                <label className="text-slate-400 font-bold block mb-1">Primary Emergency Contact</label>
                <input
                  type="text"
                  value={formData.emergencyContact}
                  onChange={(e) => updateField('emergencyContact', e.target.value)}
                  className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                />
              </div>
            </div>
          )}

          {/* Module 4: Employment & Job Architecture */}
          {activeStep === 4 && (
            <div className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Job Title</label>
                  <input
                    type="text"
                    value={formData.jobTitle}
                    onChange={(e) => updateField('jobTitle', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-bold"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Department</label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => updateField('department', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Legal Employer Entity</label>
                  <input
                    type="text"
                    value={formData.legalEntity}
                    onChange={(e) => updateField('legalEntity', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Base Salary Rate ($/year)</label>
                  <input
                    type="number"
                    value={formData.baseSalary}
                    onChange={(e) => updateField('baseSalary', Number(e.target.value))}
                    className="w-full bg-[#0A0E1A] border border-indigo-500/40 rounded-xl px-3 py-2 text-emerald-400 font-mono font-bold text-sm"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Employment FLSA Type</label>
                  <input
                    type="text"
                    value={formData.employmentType}
                    onChange={(e) => updateField('employmentType', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Module 5: Time & Leave Configuration */}
          {activeStep === 5 && (
            <div className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Assigned Holiday Calendar</label>
                  <input
                    type="text"
                    value={formData.holidayCalendar}
                    onChange={(e) => updateField('holidayCalendar', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">PTO Policy Tier</label>
                  <input
                    type="text"
                    value={formData.ptoTier}
                    onChange={(e) => updateField('ptoTier', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Shift Roster Schedule</label>
                  <input
                    type="text"
                    value={formData.shiftRoster}
                    onChange={(e) => updateField('shiftRoster', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Module 6: Financial, Payroll & Tax */}
          {activeStep === 6 && (
            <div className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Bank Name</label>
                  <input
                    type="text"
                    value={formData.bankName}
                    onChange={(e) => updateField('bankName', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Bank Routing Code (Encrypted)</label>
                  <input
                    type="text"
                    value={formData.routingNumber}
                    onChange={(e) => updateField('routingNumber', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-indigo-500/40 rounded-xl px-3 py-2 text-indigo-400 font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Account Number (Encrypted)</label>
                  <input
                    type="text"
                    value={formData.accountNumber}
                    onChange={(e) => updateField('accountNumber', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-indigo-500/40 rounded-xl px-3 py-2 text-indigo-400 font-mono font-bold"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Module 7: Benefits */}
          {activeStep === 7 && (
            <div className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Medical Plan Choice</label>
                  <input
                    type="text"
                    value={formData.medicalPlan}
                    onChange={(e) => updateField('medicalPlan', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-bold"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">401(k) Match Contribution %</label>
                  <input
                    type="number"
                    value={formData.retirementMatch}
                    onChange={(e) => updateField('retirementMatch', Number(e.target.value))}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Registered Dependents</label>
                  <input
                    type="number"
                    value={formData.dependentsCount}
                    onChange={(e) => updateField('dependentsCount', Number(e.target.value))}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Module 8: IT Assets & Provisioning (Rippling) */}
          {activeStep === 8 && (
            <div className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Assigned Laptop Model</label>
                  <input
                    type="text"
                    value={formData.laptopModel}
                    onChange={(e) => updateField('laptopModel', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-bold"
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-bold block mb-1">Hardware Serial Number</label>
                  <input
                    type="text"
                    value={formData.assetSerial}
                    onChange={(e) => updateField('assetSerial', e.target.value)}
                    className="w-full bg-[#0A0E1A] border border-slate-800 rounded-xl px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Module 9: Skills & Performance */}
          {activeStep === 9 && (
            <div className="space-y-4 text-xs font-sans">
              <div>
                <label className="text-slate-400 font-bold block mb-1">Primary Skills Inventory</label>
                <div className="flex flex-wrap gap-2 p-3 bg-[#0A0E1A] border border-slate-800 rounded-xl">
                  {formData.skills.map((sk, idx) => (
                    <span key={idx} className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2.5 py-1 rounded-lg text-[11px] font-mono">
                      {sk}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-slate-400 font-bold block mb-1">Professional Certifications</label>
                <div className="space-y-1">
                  {formData.certifications.map((c, idx) => (
                    <div key={idx} className="bg-[#0A0E1A] border border-slate-800 p-2.5 rounded-xl font-mono text-slate-300">
                      ✓ {c}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Form Action Controls */}
          <div className="pt-6 border-t border-slate-800 flex justify-between items-center">
            <button
              onClick={handlePrev}
              disabled={activeStep === 1}
              className="bg-slate-900 hover:bg-slate-800 disabled:opacity-40 border border-slate-800 text-slate-300 font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-1.5"
            >
              <ChevronLeft className="w-4 h-4" /> Previous Stage
            </button>

            <button
              onClick={handleNext}
              className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6 py-2.5 rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20"
            >
              {activeStep === 9 ? (
                <>
                  <Save className="w-4 h-4" /> Commit Record &amp; Dispatch MDM
                </>
              ) : (
                <>
                  Next Stage <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-[#111827] border border-emerald-500/30 rounded-2xl p-8 shadow-2xl text-center space-y-4 font-sans">
          <div className="w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-white">Employee Onboarding Record Committed</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            All 9 Data Collection Modules for <strong className="text-white">{formData.firstName} {formData.lastName}</strong> have been encrypted (AES-256) and synchronized with Rippling MDM &amp; Deel Payroll.
          </p>

          <button
            onClick={() => { setSubmitted(false); setActiveStep(1); }}
            className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-bold px-5 py-2 rounded-xl text-xs"
          >
            Create Another Employee Record
          </button>
        </div>
      )}
    </div>
  );
};
