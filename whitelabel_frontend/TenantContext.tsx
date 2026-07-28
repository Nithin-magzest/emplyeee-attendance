import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface TenantConfig {
  companyName: string;
  subdomain: string;
  companySize: '1-50' | '50-500' | '500+';
  logoUrl: string;
  primaryColor: string;
  secondaryColor: string;
  isDarkMode: boolean;
  companyValues: string[];
  kudosMonthlyBudget: number;

  ssoProvider: 'GOOGLE_WORKSPACE' | 'AZURE_AD' | 'OKTA' | 'EMAIL_PASS';
  autoProvisionSlack: boolean;
  autoProvisionGithub: boolean;
  autoProvisionZoom: boolean;
  autoProvisionFigma: boolean;
  defaultMdmPolicy: 'MACOS_ENFORCED' | 'WINDOWS_ENFORCED' | 'DUAL';

  secopsEnabled: boolean;
  mfaEnforced: boolean;
  gdprRetentionYears: number;
  ipWhitelistingEnabled: boolean;
  ipWhitelistRange: string;

  adminName: string;
  adminEmail: string;
  secopsEmail: string;

  setupCompleted: boolean;
}

const defaultTenantConfig: TenantConfig = {
  companyName: 'Acme Enterprise Corp',
  subdomain: 'acme.nexus-hrms.com',
  companySize: '50-500',
  logoUrl: '',
  primaryColor: '#6366f1',   // Indigo
  secondaryColor: '#ec4899', // Pink / Violet
  isDarkMode: true,
  companyValues: ['Customer Obsession', 'Ownership', 'Zero-to-One', 'Radical Transparency'],
  kudosMonthlyBudget: 100,

  ssoProvider: 'GOOGLE_WORKSPACE',
  autoProvisionSlack: true,
  autoProvisionGithub: true,
  autoProvisionZoom: true,
  autoProvisionFigma: false,
  defaultMdmPolicy: 'MACOS_ENFORCED',

  secopsEnabled: true,
  mfaEnforced: true,
  gdprRetentionYears: 7,
  ipWhitelistingEnabled: false,
  ipWhitelistRange: '192.168.1.0/24',

  adminName: 'Kaelen Vance',
  adminEmail: 'admin@acme.com',
  secopsEmail: 'secops@acme.com',

  setupCompleted: false
};

interface TenantContextType {
  config: TenantConfig;
  updateConfig: (partial: Partial<TenantConfig>) => void;
  completeSetup: (finalConfig: Partial<TenantConfig>) => void;
  resetToSetup: () => void;
}

const TenantContext = createContext<TenantContextType>({
  config: defaultTenantConfig,
  updateConfig: () => {},
  completeSetup: () => {},
  resetToSetup: () => {}
});

export const TenantProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<TenantConfig>(defaultTenantConfig);

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--primary-accent', config.primaryColor);
    root.style.setProperty('--secondary-accent', config.secondaryColor);

    const hex = config.primaryColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16) || 99;
    const g = parseInt(hex.substring(2, 4), 16) || 102;
    const b = parseInt(hex.substring(4, 6), 16) || 241;
    root.style.setProperty('--brand-glow', `rgba(${r}, ${g}, ${b}, 0.25)`);
  }, [config.primaryColor, config.secondaryColor]);

  const updateConfig = (partial: Partial<TenantConfig>) => {
    setConfig((prev) => ({ ...prev, ...partial }));
  };

  const completeSetup = (finalConfig: Partial<TenantConfig>) => {
    setConfig((prev) => ({
      ...prev,
      ...finalConfig,
      setupCompleted: true
    }));
  };

  const resetToSetup = () => {
    setConfig((prev) => ({ ...prev, setupCompleted: false }));
  };

  return (
    <TenantContext.Provider value={{ config, updateConfig, completeSetup, resetToSetup }}>
      {children}
    </TenantContext.Provider>
  );
};

export const useTenant = () => useContext(TenantContext);
