import React, { useState } from 'react';
import { X, Sparkles, Send, Bot, User, CornerDownLeft } from 'lucide-react';

export const AiAssistantModal = ({ isOpen, onClose }) => {
  const [inputMsg, setInputMsg] = useState('');
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: 'Hello Dr. Evelyn Vance! I am MagAI, your 24/7 HR & SecOps assistant. How can I help you with workforce queries, PTO balances, or IT device provisioning today?',
      time: 'Just now'
    }
  ]);

  if (!isOpen) return null;

  const handleSend = (e) => {
    e.preventDefault();
    if (!inputMsg.trim()) return;

    const userText = inputMsg;
    setMessages((prev) => [
      ...prev,
      { sender: 'user', text: userText, time: 'Just now' }
    ]);
    setInputMsg('');

    setTimeout(() => {
      let reply = "I've checked our global HR database. ";
      const lower = userText.toLowerCase();

      if (lower.includes('pto') || lower.includes('leave') || lower.includes('balance')) {
        reply += "Your current paid time off balance is 24 days (Executive Tier). Team capacity is at 94.2%, so any leave request will be auto-approved instantly.";
      } else if (lower.includes('payroll') || lower.includes('salary') || lower.includes('payslip')) {
        reply += "Your July 2026 Net Take-Home Salary of $26,146.67 (US Inc. Delaware) is scheduled for disbursement on July 31st.";
      } else if (lower.includes('device') || lower.includes('macbook') || lower.includes('it')) {
        reply += "Your assigned MacBook Pro 16\" M3 Max (Serial C02G188XMD6M) is active and verified compliant under Rippling MDM policies.";
      } else {
        reply += `I have initiated an automated query for "${userText}". All policies are compliant with SOC 2 Type II and GDPR rules.`;
      }

      setMessages((prev) => [
        ...prev,
        { sender: 'ai', text: reply, time: 'Just now' }
      ]);
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md font-sans">
      <div className="w-full max-w-lg bg-[#111827] border border-slate-800 rounded-3xl p-6 shadow-2xl flex flex-col justify-between h-[540px]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-400 text-white flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                MagAI HR &amp; Workforce Assistant
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              </h3>
              <p className="text-[11px] text-slate-400">Continuous NLP Telemetry &amp; Policy Automation Engine</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl border border-slate-800 text-slate-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto my-4 space-y-3 pr-1 text-xs">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex gap-2.5 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.sender === 'ai' && (
                <div className="w-7 h-7 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
              )}
              <div
                className={`p-3.5 rounded-2xl max-w-[80%] leading-relaxed ${
                  m.sender === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-none font-medium'
                    : 'bg-[#0A0E1A] border border-slate-800 text-slate-200 rounded-bl-none'
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="pt-3 border-t border-slate-800 flex gap-2">
          <input
            type="text"
            value={inputMsg}
            onChange={(e) => setInputMsg(e.target.value)}
            placeholder="Ask OmniAI about PTO balance, payslips, or IT devices..."
            className="flex-1 bg-[#0A0E1A] border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md shadow-indigo-600/20 shrink-0"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
