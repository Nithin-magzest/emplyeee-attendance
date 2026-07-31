/**
 * Dynamic Runtime Theme Injector
 * Fetches active company configuration and updates CSS Custom Properties live without reloading.
 */
class ThemeEngine {
  static async applyTheme() {
    try {
      const response = await fetch('/api/company/settings');
      const result = await response.json();
      
      if (result.success && result.data) {
        const config = result.data;
        const root = document.documentElement;

        if (config.primary_color) {
          root.style.setProperty('--primary-color', config.primary_color);
        }
        if (config.secondary_color) {
          root.style.setProperty('--secondary-color', config.secondary_color);
        }
        if (config.logo_url) {
          root.style.setProperty('--logo-url', `url('${config.logo_url}')`);
          document.querySelectorAll('.company-logo-img').forEach(img => {
            img.src = config.logo_url;
          });
        }
        if (config.company_name) {
          document.title = `${config.company_name} — HRMS & Attendance Platform`;
          document.querySelectorAll('.company-name-text').forEach(el => {
            el.textContent = config.company_name;
          });
        }
      }
    } catch (err) {
      console.warn('[ThemeEngine] Failed to apply runtime theme:', err);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => ThemeEngine.applyTheme());
