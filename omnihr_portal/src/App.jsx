import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { MobileAppSimulator } from './components/MobileAppSimulator';
import { AiAssistantModal } from './components/AiAssistantModal';
import { NotificationCenter } from './components/NotificationCenter';

import { DashboardModule } from './modules/DashboardModule';
import { OnboardingFormModule } from './modules/OnboardingFormModule';
import { CoreHrModule } from './modules/CoreHrModule';
import { PayrollModule } from './modules/PayrollModule';
import { AttendanceModule } from './modules/AttendanceModule';
import { AtsModule } from './modules/AtsModule';
import { PerformanceModule } from './modules/PerformanceModule';
import { AutomationModule } from './modules/AutomationModule';
import { AnalyticsModule } from './modules/AnalyticsModule';

export function App() {
  const [activeModule, setActiveModule] = useState('dashboard');
  const [selectedEntity, setSelectedEntity] = useState('US_INC');
  const [isMobileSimOpen, setIsMobileSimOpen] = useState(false);
  const [isAiBotOpen, setIsAiBotOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);

  const renderModule = () => {
    switch (activeModule) {
      case 'dashboard':
        return <DashboardModule />;
      case 'onboarding_form':
        return <OnboardingFormModule />;
      case 'corehr':
        return <CoreHrModule />;
      case 'payroll':
        return <PayrollModule />;
      case 'attendance':
        return <AttendanceModule />;
      case 'ats':
        return <AtsModule />;
      case 'performance':
        return <PerformanceModule />;
      case 'automations':
        return <AutomationModule />;
      case 'analytics':
        return <AnalyticsModule />;
      default:
        return <DashboardModule />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0A0E1A] text-slate-100 font-sans">
      {/* Global Sidebar Navigation */}
      <Sidebar
        activeModule={activeModule}
        setActiveModule={setActiveModule}
        onOpenMobileSim={() => setIsMobileSimOpen(true)}
        onOpenAiBot={() => setIsAiBotOpen(true)}
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          onOpenNotif={() => setIsNotifOpen(true)}
          selectedEntity={selectedEntity}
          setSelectedEntity={setSelectedEntity}
        />

        {/* Scrollable Module Workspace */}
        <main className="flex-1 overflow-y-auto p-6 sm:p-8">
          {renderModule()}
        </main>
      </div>

      {/* Modals & Overlays */}
      <MobileAppSimulator
        isOpen={isMobileSimOpen}
        onClose={() => setIsMobileSimOpen(false)}
      />

      <AiAssistantModal
        isOpen={isAiBotOpen}
        onClose={() => setIsAiBotOpen(false)}
      />

      <NotificationCenter
        isOpen={isNotifOpen}
        onClose={() => setIsNotifOpen(false)}
      />
    </div>
  );
}

export default App;
