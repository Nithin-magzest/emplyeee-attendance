import React, { useState } from 'react';

export default function SecOpsDashboard() {
  const [code, setCode] = useState('');
  const [isUnlocked, setIsUnlocked] = useState(false);

  const handleVerify = (e) => {
    e.preventDefault();
    // Verification logic...
    if (code === '123456') setIsUnlocked(true);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">SecOps & Security Management</h1>
      
      {/* Moved SMTP Configuration Card */}
      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">📡 SMTP Configuration</h2>
        
        {!isUnlocked ? (
          <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
            <p className="text-sm text-red-800 font-medium mb-3">
              🛡️ Identity Verification Required. Stored SMTP credentials require authentication.
            </p>
            <form onSubmit={handleVerify} className="flex gap-3">
              <input 
                type="text" 
                maxLength="6"
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-center tracking-widest font-mono w-36"
              />
              <button 
                type="submit" 
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium transition"
              >
                Verify & Unlock
              </button>
            </form>
          </div>
        ) : (
          <div className="space-y-4">
            {/* SMTP Settings Form goes here once unlocked */}
            <p className="text-sm text-green-600 font-medium">✓ Identity verified. You can update SMTP settings below.</p>
          </div>
        )}
      </div>
    </div>
  );
}
