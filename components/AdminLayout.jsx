import React from 'react';
import Sidebar from './Sidebar';

export default function AdminLayout({ children, sessionExpired }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-100">
      {/* Fixed Sidebar - Prevents navigation column jumping */}
      <aside className="w-64 min-w-[16rem] h-full bg-slate-900 text-white flex-shrink-0 flex flex-col">
        <Sidebar />
      </aside>

      {/* Main Viewport Container */}
      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0">
        
        {/* Session Alert Banner - Fixed height container prevents layout pop-in */}
        {sessionExpired && (
          <div className="bg-red-100 border-b border-red-300 text-red-700 px-6 py-3 text-sm font-medium flex-shrink-0">
            ⚠️ Your session expired. Please log in again.
          </div>
        )}

        {/* Scrollable Content Area */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
