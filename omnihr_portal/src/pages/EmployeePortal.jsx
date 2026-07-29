import React, { useState, useEffect } from "react";
import {
  User, DollarSign, Clock, Calendar, Bell, LogOut, Download,
  CheckCircle, AlertCircle, Building2, Award, ChevronRight,
  Smartphone, MapPin, CreditCard, TrendingUp, FileText, Zap
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function EmployeePortal() {
  const { user, logout, apiCall } = useAuth();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [payItems, setPayItems] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [ptoRequests, setPtoRequests] = useState([]);
  const [leaveBalance, setLeaveBalance] = useState(null);
  const [clockedIn, setClockedIn] = useState(false);
  const [currentLog, setCurrentLog] = useState(null);
  const [leaveFm, setLeaveFm] = useState({ leaveType: "Annual PTO", startDate: "", endDate: "", reason: "" });
  const [toasts, setToasts] = useState([]);

  const showToast = (msg, type = "success") => {
    const id = Date.now();
    setToasts(t => [...t, { id, msg, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
  };

  useEffect(() => {
    apiCall("/payroll/items").then(setPayItems).catch(() => {});
    apiCall("/attendance").then(setAttendance).catch(() => {});
    apiCall("/attendance/pto-requests").then(setPtoRequests).catch(() => {});
    apiCall("/attendance/leave-balances").then(d => setLeaveBalance(d[0] || null)).catch(() => {});
  }, []);

  const handleClockIn = async () => {
    try {
      const log = await apiCall("/attendance/checkin", {
        method: "POST",
        body: JSON.stringify({ verificationMode: "WebCam Face ID", locationName: "Office / Remote" }),
      });
      setClockedIn(true);
      setCurrentLog(log);
      showToast("✅ Clocked In successfully!");
    } catch (e) { showToast(e.message, "error"); }
  };

  const handleClockOut = async () => {
    if (!currentLog) return;
    try {
      await apiCall(`/attendance/${currentLog.id}/checkout`, { method: "PUT", body: "{}" });
      setClockedIn(false);
      setCurrentLog(null);
      showToast("👋 Clocked Out successfully!");
    } catch (e) { showToast(e.message, "error"); }
  };

  const submitLeave = async (e) => {
    e.preventDefault();
    try {
      const res = await apiCall("/attendance/pto-requests", {
        method: "POST",
        body: JSON.stringify(leaveFm),
      });
      setPtoRequests(p => [res, ...p]);
      showToast("📋 Leave request submitted!");
      setLeaveFm({ leaveType: "Annual PTO", startDate: "", endDate: "", reason: "" });
    } catch (e) { showToast(e.message, "error"); }
  };

  const downloadPayslip = (item) => {
    const blob = new Blob([
      `OmniHR Premier — Payslip\n\nPay Period: ${item.pay_period}\nEmployee: ${user.name}\nBase Pay: ${item.currency} ${Number(item.base_pay).toLocaleString()}\nBonus/Allowances: ${Number(item.bonus_allowances || 0).toLocaleString()}\nTax Deductions: -${Number(item.tax_deductions).toLocaleString()}\n----------------------------------\nNet Pay: ${item.currency} ${Number(item.net_pay).toLocaleString()}\nPayout Date: ${item.payout_date}\nStatus: ${item.status}`
    ], { type: 'text/plain' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = `Payslip_${item.pay_period?.replace(' ', '_')}.txt`; a.click();
  };

  const emp = user?.employeeProfile;
  const navTabs = [
    { id: "dashboard", icon: Building2, label: "My Dashboard" },
    { id: "payslips", icon: DollarSign, label: "Payslips" },
    { id: "attendance", icon: Clock, label: "Attendance" },
    { id: "leaves", icon: Calendar, label: "Leave" },
    { id: "profile", icon: User, label: "My Profile" },
  ];

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#0B0F19", fontFamily: "Inter, sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        @keyframes slideIn { from{opacity:0;transform:translateY(-10px)} to{opacity:1;transform:translateY(0)} }
        .ess-card { background: rgba(21,28,44,0.95); border: 1px solid rgba(255,255,255,0.07); border-radius: 16px; padding: 20px; transition: all 0.2s; }
        .ess-card:hover { border-color: rgba(99,102,241,0.3); }
        .nav-tab { transition: all 0.2s; cursor: pointer; padding: 10px 18px; border-radius: 10px; display:flex; align-items:center; gap:8px; border: 1px solid transparent; background: transparent; color: #64748B; font-size: 14px; font-weight: 500; font-family: Inter, sans-serif; }
        .nav-tab.active { background: rgba(99,102,241,0.15); color: #A5B4FC; border-color: rgba(99,102,241,0.3); }
        .nav-tab:hover:not(.active) { background: rgba(255,255,255,0.04); color: #94A3B8; }
        .toast { animation: slideIn 0.3s ease; position: fixed; bottom: 24px; right: 24px; z-index: 9999; padding: 12px 20px; border-radius: 12px; font-size: 14px; font-weight: 600; display:flex; align-items:center; gap:8px; backdrop-filter:blur(12px); }
      `}</style>

      {/* Toasts */}
      {toasts.map(t => (
        <div key={t.id} className="toast" style={{
          background: t.type === "error" ? "rgba(244,63,94,0.9)" : "rgba(16,185,129,0.9)",
          color: "white", border: `1px solid ${t.type === "error" ? "#F43F5E" : "#10B981"}`,
        }}>{t.msg}</div>
      ))}

      {/* Header */}
      <div style={{ background: "rgba(21,28,44,0.98)", borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "14px 28px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: "36px", height: "36px", background: "linear-gradient(135deg,#6366F1,#06B6D4)", borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Building2 size={18} color="white" />
          </div>
          <div>
            <p style={{ color: "#F1F5F9", fontWeight: 700, fontSize: "16px", margin: 0 }}>OmniHR Premier</p>
            <p style={{ color: "#475569", fontSize: "11px", margin: 0 }}>Employee Self-Service Portal</p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {emp?.avatar_url && <img src={emp.avatar_url} alt="" style={{ width: "36px", height: "36px", borderRadius: "50%", border: "2px solid rgba(99,102,241,0.5)" }} />}
          <div>
            <p style={{ color: "#F1F5F9", fontWeight: 600, fontSize: "14px", margin: 0 }}>{user?.name}</p>
            <p style={{ color: "#475569", fontSize: "11px", margin: 0 }}>{emp?.role_title || "Employee"}</p>
          </div>
          <button onClick={logout} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 14px", background: "rgba(244,63,94,0.12)", border: "1px solid rgba(244,63,94,0.3)", borderRadius: "8px", color: "#F43F5E", cursor: "pointer", fontSize: "13px", fontFamily: "Inter, sans-serif" }}>
            <LogOut size={14} /> Logout
          </button>
        </div>
      </div>

      {/* Nav */}
      <div style={{ background: "rgba(15,20,32,0.8)", borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "0 28px", display: "flex", gap: "4px" }}>
        {navTabs.map(({ id, icon: Icon, label }) => (
          <button key={id} onClick={() => setActiveTab(id)} className={`nav-tab ${activeTab === id ? "active" : ""}`}>
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "28px" }}>
        {/* DASHBOARD */}
        {activeTab === "dashboard" && (
          <div>
            <h2 style={{ color: "#F1F5F9", fontSize: "22px", fontWeight: 700, marginBottom: "24px" }}>
              Welcome back, {user?.name?.split(" ")[0]} 👋
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: "16px", marginBottom: "28px" }}>
              {[
                { label: "PTO Available", value: `${leaveBalance?.pto_available || 0} Days`, icon: Calendar, color: "#6366F1" },
                { label: "Sick Days Left", value: `${leaveBalance?.sick_available || 0} Days`, icon: AlertCircle, color: "#F59E0B" },
                { label: "Payslips", value: `${payItems.length} Records`, icon: DollarSign, color: "#10B981" },
                { label: "Attendance", value: `${attendance.length} Logs`, icon: Clock, color: "#06B6D4" },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="ess-card">
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{ width: "40px", height: "40px", background: `${color}20`, borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon size={20} color={color} />
                    </div>
                    <div>
                      <p style={{ color: "#64748B", fontSize: "12px", margin: 0 }}>{label}</p>
                      <p style={{ color: "#F1F5F9", fontSize: "20px", fontWeight: 700, margin: 0 }}>{value}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Clock In/Out */}
            <div className="ess-card" style={{ marginBottom: "20px", background: "rgba(99,102,241,0.08)", borderColor: "rgba(99,102,241,0.3)" }}>
              <p style={{ color: "#A5B4FC", fontWeight: 700, fontSize: "16px", marginBottom: "16px" }}>⏱️ Time & Attendance</p>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <button onClick={clockedIn ? handleClockOut : handleClockIn} style={{
                  padding: "12px 28px", borderRadius: "10px", border: "none", cursor: "pointer",
                  background: clockedIn ? "rgba(244,63,94,0.85)" : "linear-gradient(135deg,#10B981,#059669)",
                  color: "white", fontWeight: 700, fontSize: "15px", fontFamily: "Inter, sans-serif",
                }}>
                  {clockedIn ? "🔴 Clock Out" : "🟢 Clock In"}
                </button>
                <span style={{ color: "#475569", fontSize: "13px" }}>
                  {clockedIn ? `Clocked in at ${new Date(currentLog?.check_in_time).toLocaleTimeString()}` : "Not clocked in yet today"}
                </span>
              </div>
            </div>

            {/* Recent pay items */}
            {payItems.length > 0 && (
              <div className="ess-card">
                <p style={{ color: "#94A3B8", fontWeight: 700, fontSize: "15px", marginBottom: "14px" }}>💰 Latest Payslip</p>
                {payItems.slice(0, 1).map(pi => (
                  <div key={pi.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div>
                      <p style={{ color: "#F1F5F9", fontWeight: 700, fontSize: "22px", margin: 0 }}>{pi.currency} {Number(pi.net_pay).toLocaleString()}</p>
                      <p style={{ color: "#475569", fontSize: "13px", margin: "4px 0 0" }}>Net pay for {pi.pay_period} · {pi.status}</p>
                    </div>
                    <button onClick={() => downloadPayslip(pi)} style={{ padding: "8px 16px", borderRadius: "8px", background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#A5B4FC", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", fontFamily: "Inter, sans-serif" }}>
                      <Download size={14} /> Download
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* PAYSLIPS */}
        {activeTab === "payslips" && (
          <div>
            <h2 style={{ color: "#F1F5F9", fontSize: "20px", fontWeight: 700, marginBottom: "20px" }}>My Payslips</h2>
            {payItems.length === 0 ? (
              <div className="ess-card" style={{ textAlign: "center", padding: "48px", color: "#475569" }}>No payslips found.</div>
            ) : payItems.map(pi => (
              <div key={pi.id} className="ess-card" style={{ marginBottom: "12px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <p style={{ color: "#F1F5F9", fontWeight: 700, fontSize: "16px", margin: 0 }}>{pi.pay_period}</p>
                  <p style={{ color: "#475569", fontSize: "13px", margin: "4px 0 0" }}>Base: {pi.currency} {Number(pi.base_pay).toLocaleString()} · Tax: -{Number(pi.tax_deductions).toLocaleString()}</p>
                  <p style={{ color: "#10B981", fontWeight: 700, fontSize: "15px", margin: "6px 0 0" }}>Net: {pi.currency} {Number(pi.net_pay).toLocaleString()}</p>
                </div>
                <div style={{ textAlign: "right", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "8px" }}>
                  <span style={{ padding: "4px 10px", borderRadius: "20px", background: pi.status === "Approved" ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)", color: pi.status === "Approved" ? "#10B981" : "#F59E0B", fontSize: "12px", fontWeight: 600 }}>
                    {pi.status}
                  </span>
                  <button onClick={() => downloadPayslip(pi)} style={{ padding: "6px 14px", borderRadius: "8px", background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#A5B4FC", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontFamily: "Inter, sans-serif" }}>
                    <Download size={13} /> Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ATTENDANCE */}
        {activeTab === "attendance" && (
          <div>
            <h2 style={{ color: "#F1F5F9", fontSize: "20px", fontWeight: 700, marginBottom: "20px" }}>My Attendance</h2>
            <div className="ess-card" style={{ marginBottom: "20px" }}>
              <div style={{ display: "flex", gap: "12px" }}>
                <button onClick={clockedIn ? handleClockOut : handleClockIn} style={{
                  padding: "12px 24px", borderRadius: "10px", border: "none", cursor: "pointer",
                  background: clockedIn ? "rgba(244,63,94,0.85)" : "linear-gradient(135deg,#10B981,#059669)",
                  color: "white", fontWeight: 700, fontSize: "14px", fontFamily: "Inter, sans-serif",
                }}>
                  {clockedIn ? "🔴 Clock Out" : "🟢 Clock In"}
                </button>
                <div style={{ color: "#64748B", fontSize: "13px", alignSelf: "center" }}>
                  {clockedIn ? `Clocked in: ${new Date(currentLog?.check_in_time).toLocaleTimeString()}` : "Not clocked in today"}
                </div>
              </div>
            </div>
            {attendance.map(a => (
              <div key={a.id} className="ess-card" style={{ marginBottom: "8px", display: "flex", justifyContent: "space-between" }}>
                <div>
                  <p style={{ color: "#F1F5F9", fontSize: "14px", fontWeight: 600, margin: 0 }}>{new Date(a.check_in_time).toLocaleDateString()}</p>
                  <p style={{ color: "#475569", fontSize: "12px", margin: "4px 0 0" }}>In: {new Date(a.check_in_time).toLocaleTimeString()} · {a.verification_mode}</p>
                  <p style={{ color: "#475569", fontSize: "12px" }}>{a.location_name}</p>
                </div>
                <span style={{ padding: "4px 10px", borderRadius: "20px", height: "fit-content", background: a.status === "On Time" ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)", color: a.status === "On Time" ? "#10B981" : "#F59E0B", fontSize: "12px", fontWeight: 600 }}>
                  {a.status}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* LEAVES */}
        {activeTab === "leaves" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
            <div>
              <h2 style={{ color: "#F1F5F9", fontSize: "20px", fontWeight: 700, marginBottom: "16px" }}>Leave Balances</h2>
              {leaveBalance && (
                <div className="ess-card" style={{ marginBottom: "20px" }}>
                  {[["Annual PTO", leaveBalance.pto_available, "#6366F1"], ["Sick Leave", leaveBalance.sick_available, "#F43F5E"], ["Casual Leave", leaveBalance.casual_available, "#F59E0B"]].map(([t, v, c]) => (
                    <div key={t} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                      <span style={{ color: "#94A3B8", fontSize: "14px" }}>{t}</span>
                      <span style={{ color: c, fontWeight: 700, fontSize: "16px" }}>{v} days</span>
                    </div>
                  ))}
                </div>
              )}

              <h3 style={{ color: "#94A3B8", fontSize: "15px", fontWeight: 700, marginBottom: "12px" }}>My Leave History</h3>
              {ptoRequests.map(r => (
                <div key={r.id} className="ess-card" style={{ marginBottom: "8px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div>
                      <p style={{ color: "#F1F5F9", fontWeight: 600, fontSize: "14px", margin: 0 }}>{r.leave_type}</p>
                      <p style={{ color: "#475569", fontSize: "12px", margin: "4px 0 0" }}>{r.start_date} → {r.end_date} ({r.total_days} days)</p>
                    </div>
                    <span style={{ padding: "4px 10px", borderRadius: "20px", height: "fit-content", background: r.status === "Approved" ? "rgba(16,185,129,0.15)" : "rgba(245,158,11,0.15)", color: r.status === "Approved" ? "#10B981" : "#F59E0B", fontSize: "11px", fontWeight: 600 }}>
                      {r.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div>
              <h2 style={{ color: "#F1F5F9", fontSize: "20px", fontWeight: 700, marginBottom: "16px" }}>Request Leave</h2>
              <form onSubmit={submitLeave} className="ess-card">
                {[
                  { label: "Leave Type", name: "leaveType", type: "select", options: ["Annual PTO", "Sick Leave", "Casual Leave", "Maternity/Paternity", "Unpaid Leave"] },
                  { label: "Start Date", name: "startDate", type: "date" },
                  { label: "End Date", name: "endDate", type: "date" },
                  { label: "Reason", name: "reason", type: "textarea" },
                ].map(f => (
                  <div key={f.name} style={{ marginBottom: "14px" }}>
                    <label style={{ color: "#94A3B8", fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "6px" }}>{f.label}</label>
                    {f.type === "select" ? (
                      <select value={leaveFm[f.name]} onChange={e => setLeaveFm(p => ({ ...p, [f.name]: e.target.value }))}
                        style={{ width: "100%", padding: "10px", background: "rgba(15,20,36,0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#F1F5F9", fontFamily: "Inter, sans-serif", fontSize: "14px" }}>
                        {f.options.map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : f.type === "textarea" ? (
                      <textarea value={leaveFm[f.name]} onChange={e => setLeaveFm(p => ({ ...p, [f.name]: e.target.value }))} rows={3}
                        style={{ width: "100%", padding: "10px", background: "rgba(15,20,36,0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#F1F5F9", fontFamily: "Inter, sans-serif", fontSize: "14px", resize: "vertical", boxSizing: "border-box" }} />
                    ) : (
                      <input type={f.type} value={leaveFm[f.name]} onChange={e => setLeaveFm(p => ({ ...p, [f.name]: e.target.value }))}
                        style={{ width: "100%", padding: "10px", background: "rgba(15,20,36,0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#F1F5F9", fontFamily: "Inter, sans-serif", fontSize: "14px", boxSizing: "border-box" }} />
                    )}
                  </div>
                ))}
                <button type="submit" style={{ width: "100%", padding: "12px", background: "linear-gradient(135deg,#6366F1,#4F46E5)", border: "none", borderRadius: "10px", color: "white", fontWeight: 700, cursor: "pointer", fontFamily: "Inter, sans-serif" }}>
                  Submit Leave Request
                </button>
              </form>
            </div>
          </div>
        )}

        {/* PROFILE */}
        {activeTab === "profile" && emp && (
          <div style={{ maxWidth: "640px" }}>
            <h2 style={{ color: "#F1F5F9", fontSize: "20px", fontWeight: 700, marginBottom: "20px" }}>My Profile</h2>
            <div className="ess-card">
              <div style={{ display: "flex", gap: "20px", alignItems: "center", marginBottom: "24px" }}>
                <img src={emp.avatar_url} alt="" style={{ width: "80px", height: "80px", borderRadius: "50%", border: "3px solid rgba(99,102,241,0.5)" }} />
                <div>
                  <p style={{ color: "#F1F5F9", fontWeight: 800, fontSize: "22px", margin: 0 }}>{emp.first_name} {emp.last_name}</p>
                  <p style={{ color: "#6366F1", fontSize: "14px", margin: "4px 0 0" }}>{emp.role_title}</p>
                  <p style={{ color: "#475569", fontSize: "13px", margin: "2px 0 0" }}>{emp.emp_code}</p>
                </div>
              </div>
              {[
                { label: "Email", value: emp.email },
                { label: "Department", value: emp.department_name },
                { label: "Location", value: emp.location },
                { label: "Employment Type", value: emp.employment_type },
                { label: "Join Date", value: emp.joined_date },
                { label: "Status", value: emp.status },
                { label: "Performance Rating", value: `⭐ ${emp.performance_rating}/5.0` },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  <span style={{ color: "#64748B", fontSize: "13px" }}>{label}</span>
                  <span style={{ color: "#E2E8F0", fontSize: "13px", fontWeight: 600 }}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
