/**
 * Wi-Fi & Network Posture Risk Evaluation Engine
 */
class DevicePostureEngine {
  static evaluateRisk() {
    let riskScore = 0;
    const isUnencrypted = window.location.protocol !== 'https:';
    const isPublicWifi = navigator.connection && navigator.connection.type === 'cellular';

    if (isUnencrypted && window.location.hostname !== '127.0.0.1' && window.location.hostname !== 'localhost') {
      riskScore += 70;
    }
    if (isPublicWifi) {
      riskScore += 30;
    }

    if (riskScore > 65) {
      this.triggerLockout(riskScore);
    }
  }

  static async triggerLockout(score) {
    // 1. Lock UI View immediately
    document.body.innerHTML = `
      <div style="background:#0f172a; color:#fff; height:100vh; display:flex; align-items:center; justify-content:center; flex-direction:column; text-align:center; padding:24px;">
        <h1 style="color:#f87171; font-size:32px; margin-bottom:16px;">⚠️ Security Lockout Triggered</h1>
        <p style="max-width:500px; color:#9ca3af; font-size:16px;">High Network Risk Detected (${score}%). Active session terminated for data protection. Please connect to a secure corporate network.</p>
      </div>
    `;

    // 2. Report Fingerprint & Risk to SOC Alert Database
    try {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
      await fetch('/api/security/report_posture_lockout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
        body: JSON.stringify({
          risk_score: score,
          user_agent: navigator.userAgent,
          timestamp: new Date().toISOString()
        })
      });
    } catch (e) {}

    // 3. Clear session storage
    sessionStorage.clear();
    localStorage.clear();
  }
}

document.addEventListener('DOMContentLoaded', () => DevicePostureEngine.evaluateRisk());
