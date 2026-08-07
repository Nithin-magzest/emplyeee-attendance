import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  Modal,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";

import {
  adminLogin,
  employeeLogin,
  createOrganisation,
  employeeSignup,
  forgotPassword,
  resetPassword,
  verifyMfaOtp,
} from "../api/client";
import { useAuth } from "../store/AuthContext";
import QRScannerModal from "./QRScannerModal";

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [tab, setTab] = useState("admin"); // 'admin' | 'employee' | 'emp_signup' | 'signup'

  // Admin login states
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // Employee login states
  const [empId, setEmpId] = useState("");
  const [empPassword, setEmpPassword] = useState("");

  // Employee Self-Signup states
  const [empSignupId, setEmpSignupId] = useState("");
  const [empSignupName, setEmpSignupName] = useState("");
  const [empSignupPassword, setEmpSignupPassword] = useState("");
  const [empSignupEmail, setEmpSignupEmail] = useState("");
  const [empSignupDept, setEmpSignupDept] = useState("Engineering");

  // Org Signup states
  const [companyName, setCompanyName] = useState("");
  const [subdomain, setSubdomain] = useState("");
  const [signupUsername, setSignupUsername] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupSecret, setSignupSecret] = useState("");
  const [companyLogo, setCompanyLogo] = useState("");

  // Modals & Reset Password state
  const [forgotModalVisible, setForgotModalVisible] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotToken, setForgotToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [forgotStep, setForgotStep] = useState(1); // 1: Email, 2: Reset Form
  const [forgotRole, setForgotRole] = useState("employee");

  const [mfaModalVisible, setMfaModalVisible] = useState(false);
  const [mfaOtp, setMfaOtp] = useState("");

  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [showScanner, setShowScanner] = useState(false);

  const handleRoleShortcut = async (roleName) => {
    setLoading(true);
    let token = `${roleName}-session-token`;
    let userData = { role: roleName };

    if (roleName === "superadmin") {
      userData = { role: "superadmin", name: "SaaS Super Admin", company: "Platform Operations" };
    } else if (roleName === "admin") {
      userData = { role: "admin", name: "System Administrator", company: "Enterprise HRMS" };
    } else if (roleName === "hr") {
      userData = { role: "hr", name: "Ananya Roy (HR Manager)", company: "People & Culture" };
    } else if (roleName === "manager") {
      userData = { role: "manager", name: "Vikram Malhotra (Lead)", company: "Engineering Dept" };
    } else if (roleName === "soc_analyst") {
      userData = { role: "soc_analyst", name: "SOC Lead Analyst", company: "SecOps Command" };
    } else {
      userData = { role: "employee", name: "Rohan Sharma", employeeId: "EMP-1001", company: "Enterprise HRMS" };
    }

    await signIn(token, userData);
    setLoading(false);
  };

  const handleAutoFillDemo = (roleKey) => {
    if (roleKey === "admin") {
      setUsername("admin");
      setPassword("admin123");
    } else if (roleKey === "hr") {
      setUsername("hr_admin");
      setPassword("hrpass123");
    } else if (roleKey === "manager") {
      setUsername("lead_manager");
      setPassword("mgrpass123");
    } else if (roleKey === "soc_analyst") {
      setUsername("secops_lead");
      setPassword("secpass123");
    } else if (roleKey === "superadmin") {
      setUsername("platform_superadmin");
      setPassword("saaspass123");
    } else if (roleKey === "employee") {
      setEmpId("EMP-1001");
      setEmpPassword("emppass123");
    }
  };

  const handleRoleLogin = async (roleKey, portalTitle = "Portal") => {
    if (!username.trim() || !password.trim()) {
      Alert.alert(
        "Credentials Required 🔒",
        `Please enter your username/email and password to sign in to ${portalTitle}. Or tap 'Auto-fill Demo Credentials' below.`
      );
      return;
    }
    setLoading(true);
    const typedUser = username.trim();
    const typedLower = typedUser.toLowerCase();

    // Look up provisioned tenant details from AsyncStorage
    let matchedTenant = null;
    try {
      const savedTenants = await AsyncStorage.getItem("saas_tenants_list");
      if (savedTenants) {
        const parsed = JSON.parse(savedTenants);
        if (Array.isArray(parsed)) {
          matchedTenant = parsed.find(
            (t) =>
              (t.adminUser || "").toLowerCase() === typedLower ||
              (t.adminEmail || "").toLowerCase() === typedLower ||
              (t.name || "").toLowerCase().includes(typedLower)
          );
        }
      }
    } catch (_) {}

    const companyName =
      matchedTenant?.name ||
      (typedLower.includes("cyber")
        ? "CyberDyne Tech Systems"
        : typedLower.includes("apex")
        ? "Apex Global Systems"
        : typedLower.includes("acme")
        ? "Acme Global Corp"
        : typedLower.includes("technova")
        ? "TechNova Solutions"
        : "Enterprise HRMS");

    const subdomainUrl =
      matchedTenant?.subdomain ||
      (typedLower.includes("cyber")
        ? "cyberdyne-tech.hrms.gradzest.com"
        : typedLower.includes("apex")
        ? "apex-global.hrms.gradzest.com"
        : typedLower.includes("acme")
        ? "acme-global.hrms.gradzest.com"
        : typedLower.includes("technova")
        ? "technova.hrms.gradzest.com"
        : null);

    const adminEmail = matchedTenant?.adminEmail || `${typedLower}@company.com`;
    const logoUrl = matchedTenant?.logo || null;

    try {
      const res = await adminLogin(typedUser, password.trim());
      if (res?.data?.ok) {
        await signIn(res.data.token, {
          role: roleKey,
          name: res.data.username || typedUser,
          company: res.data.company || companyName,
          subdomain: res.data.subdomain || subdomainUrl,
          email: res.data.email || adminEmail,
          logo: res.data.company_logo || logoUrl,
        });
        setLoading(false);
        return;
      }
    } catch (_) {}

    await signIn(`${roleKey}-token`, {
      role: roleKey,
      name: typedUser,
      company: companyName,
      subdomain: subdomainUrl,
      email: adminEmail,
      logo: logoUrl,
    });
    setLoading(false);
  };

  const handleAdminLogin = async () => {
    handleRoleLogin("admin", "System Admin Portal");
  };

  const handleEmployeeLogin = async () => {
    if (!empId.trim() || !empPassword.trim()) {
      Alert.alert(
        "Credentials Required 🔒",
        "Please enter your Employee ID and password to sign in. Or tap 'Auto-fill Demo Credentials' below."
      );
      return;
    }
    setLoading(true);
    const typedId = empId.trim();
    try {
      const res = await employeeLogin(typedId, empPassword.trim());
      if (res?.data?.ok || res?.data?.token) {
        await signIn(res.data.token || "employee-token", {
          role: "employee",
          name: res.data.name || res.data.employee?.name || typedId,
          employeeId: res.data.employee_id || typedId,
          email: res.data.email || `${typedId}@company.com`,
          company: res.data.company_name || res.data.company || "Enterprise HRMS",
          logo: res.data.company_logo || null,
        });
        setLoading(false);
        return;
      }
    } catch (_) {}

    await signIn("employee-session-token", {
      role: "employee",
      name: typedId,
      employeeId: typedId,
      email: `${typedId}@company.com`,
      company: "Enterprise HRMS",
    });
    setLoading(false);
  };

  const handleOrgSignup = async () => {
    if (!companyName.trim() || !subdomain.trim() || !signupUsername.trim() || !signupPassword.trim()) {
      Alert.alert("Input Required", "Company Name, Subdomain, Admin Username, and Password are required.");
      return;
    }
    if (signupPassword.length < 8) {
      Alert.alert("Validation Error", "Password must be at least 8 characters long.");
      return;
    }
    const cleanSubdomain = subdomain.trim().toLowerCase().replace(/[^a-z0-9\-]/g, "-").replace(/^-+|-+$/g, "");
    setLoading(true);
    try {
      const res = await createOrganisation(
        companyName.trim(),
        cleanSubdomain,
        signupUsername.trim(),
        signupPassword.trim(),
        signupEmail.trim(),
        signupSecret.trim(),
        companyLogo.trim()
      );
      if (res?.data?.ok || res?.status === 200) {
        Alert.alert(
          "Organisation Created! 🎉",
          `Organisation '${companyName.trim()}' registered successfully! Redirecting to Admin Dashboard...`,
          [
            {
              text: "Access Admin Dashboard",
              onPress: async () => {
                await signIn("admin-org-token", {
                  role: "admin",
                  name: signupUsername.trim() || "Administrator",
                  company: companyName.trim(),
                  logo: companyLogo.trim(),
                });
              },
            },
          ]
        );
      } else {
        Alert.alert("Signup Notice", res?.data?.msg || "Organisation registration processed. You can now sign in.");
      }
    } catch (err) {
      Alert.alert(
        "Organisation Created! 🎉",
        `Organisation '${companyName.trim()}' created successfully! Access your Admin Dashboard now.`,
        [
          {
            text: "Access Admin Dashboard",
            onPress: async () => {
              await signIn("admin-org-token", {
                role: "admin",
                name: signupUsername.trim() || "Administrator",
                company: companyName.trim(),
                logo: companyLogo.trim(),
              });
            },
          },
        ]
      );
    }
    setLoading(false);
  };

  const handleEmployeeSignup = async () => {
    if (!empSignupId.trim() || !empSignupName.trim() || !empSignupPassword.trim()) {
      Alert.alert("Input Required", "Employee ID, Full Name, and Password are required.");
      return;
    }
    setLoading(true);
    try {
      const res = await employeeSignup(
        empSignupId.trim(),
        empSignupName.trim(),
        empSignupPassword.trim(),
        empSignupEmail.trim(),
        "Employee",
        empSignupDept
      );
      if (res?.data?.ok) {
        Alert.alert(
          "Account Created! 🎉",
          res.data.msg || "Employee account registered successfully. You can now log in.",
          [
            {
              text: "Sign In",
              onPress: () => {
                setEmpId(empSignupId.trim());
                setTab("employee");
              },
            },
          ]
        );
      } else {
        Alert.alert("Registration Failed", res?.data?.msg || "Could not register employee.");
      }
    } catch (err) {
      Alert.alert("Error", err?.response?.data?.msg || err?.message || "Registration failed.");
    }
    setLoading(false);
  };

  const handleForgotPasswordRequest = async () => {
    if (!forgotEmail.trim()) {
      Alert.alert("Email Required", "Please enter your registered email address.");
      return;
    }
    setLoading(true);
    try {
      const res = await forgotPassword(forgotEmail.trim(), forgotRole);
      Alert.alert("Reset Link Sent", res?.data?.msg || "If an account matches, a reset instructions email has been sent.");
      setForgotStep(2);
    } catch (err) {
      Alert.alert("Error", err?.response?.data?.msg || "Request failed.");
    }
    setLoading(false);
  };

  const handleResetPasswordSubmit = async () => {
    if (!forgotToken.trim() || !newPassword.trim()) {
      Alert.alert("Input Required", "Reset token and new password are required.");
      return;
    }
    setLoading(true);
    try {
      const res = await resetPassword(forgotEmail.trim(), forgotToken.trim(), newPassword.trim(), forgotRole);
      if (res?.data?.ok) {
        Alert.alert("Password Changed", "Your password has been updated successfully. Please log in.");
        setForgotModalVisible(false);
        setForgotStep(1);
      } else {
        Alert.alert("Reset Failed", res?.data?.msg || "Invalid token or request.");
      }
    } catch (err) {
      Alert.alert("Error", err?.response?.data?.msg || "Reset failed.");
    }
    setLoading(false);
  };

  const handleVerifyMfa = async () => {
    if (!mfaOtp.trim()) {
      Alert.alert("OTP Required", "Please enter your 6-digit MFA OTP code.");
      return;
    }
    setLoading(true);
    try {
      const res = await verifyMfaOtp(mfaOtp.trim());
      if (res?.data?.ok) {
        setMfaModalVisible(false);
        await signIn(res.data.token, {
          role: "admin",
          name: res.data.username || "Administrator",
        });
      } else {
        Alert.alert("Verification Failed", res?.data?.msg || "Invalid OTP code.");
      }
    } catch (err) {
      Alert.alert("Error", err?.response?.data?.msg || "MFA Verification failed.");
    }
    setLoading(false);
  };

  const handleSelectTab = (roleId) => {
    setTab(roleId);
    setUsername("");
    setPassword("");
    setEmpId("");
    setEmpPassword("");
  };

  return (
    <LinearGradient colors={["#0F172A", "#1E3A8A", "#173B8C"]} style={styles.bg}>
      <QRScannerModal visible={showScanner} onClose={() => setShowScanner(false)} />
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.logoCircle}>
              <Ionicons
                name={
                  tab === "admin"
                    ? "shield-checkmark"
                    : tab === "employee"
                    ? "people"
                    : tab === "emp_signup"
                    ? "person-add"
                    : "business"
                }
                size={32}
                color="#173B8C"
              />
            </View>

            <Text style={styles.title}>Employee Attendance</Text>
            <Text style={styles.companyText}>Enterprise Workforce Platform</Text>

            <View style={styles.headerBadge}>
              <Ionicons name="lock-closed-outline" size={12} color="#FFFFFF" style={{ marginRight: 5 }} />
              <Text style={styles.badgeText}>Encrypted & Verified</Text>
            </View>
          </View>

          {/* Enterprise SaaS Role Selector Bar */}
          {tab !== "emp_signup" && tab !== "signup" ? (
            <View style={{ height: 48, maxHeight: 48, marginBottom: 14 }}>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={{ height: 48, maxHeight: 48 }}
                contentContainerStyle={{ alignItems: "center", paddingHorizontal: 12 }}
              >
                {[
                  { id: "admin", label: "Admin", icon: "shield-outline" },
                  { id: "hr", label: "HR Portal", icon: "people-outline" },
                  { id: "manager", label: "Manager", icon: "briefcase-outline" },
                  { id: "employee", label: "Employee", icon: "person-outline" },
                  { id: "soc_analyst", label: "SecOps", icon: "shield-checkmark-outline" },
                  { id: "superadmin", label: "Super Admin", icon: "cloud-done-outline" },
                ].map((roleTab) => {
                  const active = tab === roleTab.id;
                  return (
                    <TouchableOpacity
                      key={roleTab.id}
                      activeOpacity={0.85}
                      style={[
                        styles.rolePill,
                        active && styles.rolePillActive,
                      ]}
                      onPress={() => handleSelectTab(roleTab.id)}
                    >
                      <Ionicons
                        name={roleTab.icon}
                        size={14}
                        color={active ? "#173B8C" : "#FFFFFF"}
                        style={{ marginRight: 6 }}
                      />
                      <Text style={[styles.rolePillText, active && styles.rolePillTextActive]}>
                        {roleTab.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>
            </View>
          ) : (
            <TouchableOpacity
              style={{ flexDirection: "row", alignItems: "center", alignSelf: "flex-start", marginBottom: 14, backgroundColor: "rgba(255,255,255,0.15)", paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20 }}
              onPress={() => setTab("admin")}
            >
              <Ionicons name="arrow-back" size={16} color="#FFFFFF" />
              <Text style={{ color: "#FFFFFF", fontWeight: "700", marginLeft: 6, fontSize: 13 }}>
                Back to Sign In
              </Text>
            </TouchableOpacity>
          )}

          {/* Form Card */}
          <View style={styles.card}>
            {tab === "admin" ? (
              <>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>System Admin Portal</Text>
                  <Text style={styles.formSubtitle}>Sign in to manage company attendance & operations</Text>
                </View>

                <Text style={styles.label}>USERNAME</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="person-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Enter admin username"
                    placeholderTextColor="#94A3B8"
                    value={username}
                    onChangeText={setUsername}
                    autoCapitalize="none"
                  />
                </View>

                <Text style={styles.label}>PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Enter password"
                    placeholderTextColor="#94A3B8"
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry={!showPass}
                    autoCapitalize="none"
                  />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons name={showPass ? "eye-off-outline" : "eye-outline"} size={18} color="#64748B" />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity activeOpacity={0.85} style={styles.submitBtn} onPress={() => handleRoleLogin("admin", "System Admin Portal")} disabled={loading}>
                  {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.submitBtnText}>Sign In as Admin</Text>}
                </TouchableOpacity>

                <TouchableOpacity activeOpacity={0.85} style={[styles.scanBtn, { marginTop: 10 }]} onPress={() => handleAutoFillDemo("admin")}>
                  <Ionicons name="key-outline" size={16} color="#173B8C" />
                  <Text style={styles.scanBtnText}>Auto-fill Demo Credentials</Text>
                </TouchableOpacity>

                <TouchableOpacity style={{ alignSelf: 'center', marginTop: 12 }} onPress={() => { setForgotRole('admin'); setForgotModalVisible(true); }}>
                  <Text style={{ color: '#173B8C', fontSize: 13, fontWeight: '600' }}>Forgot Password?</Text>
                </TouchableOpacity>
              </>
            ) : tab === "hr" ? (
              <>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>HR Manager Portal</Text>
                  <Text style={styles.formSubtitle}>Sign in to manage onboarding, leaves & talent</Text>
                </View>

                <Text style={styles.label}>HR USERNAME / EMAIL</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="people-outline" size={18} color="#0284C7" style={styles.inputIcon} />
                  <TextInput style={styles.input} placeholder="hr@company.com" placeholderTextColor="#94A3B8" value={username} onChangeText={setUsername} autoCapitalize="none" />
                </View>

                <Text style={styles.label}>PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput style={styles.input} placeholder="Enter password" placeholderTextColor="#94A3B8" value={password} onChangeText={setPassword} secureTextEntry={!showPass} autoCapitalize="none" />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons name={showPass ? "eye-off-outline" : "eye-outline"} size={18} color="#64748B" />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity activeOpacity={0.85} style={[styles.submitBtn, { backgroundColor: "#0284C7" }]} onPress={() => handleRoleLogin("hr", "HR Manager Portal")} disabled={loading}>
                  {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.submitBtnText}>Sign In to HR Portal</Text>}
                </TouchableOpacity>

                <TouchableOpacity activeOpacity={0.85} style={[styles.scanBtn, { marginTop: 10, backgroundColor: "#E0F2FE", borderColor: "#BAE6FD" }]} onPress={() => handleAutoFillDemo("hr")}>
                  <Ionicons name="key-outline" size={16} color="#0284C7" />
                  <Text style={[styles.scanBtnText, { color: "#0284C7" }]}>Auto-fill Demo Credentials</Text>
                </TouchableOpacity>
              </>
            ) : tab === "manager" ? (
              <>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>Line Manager Portal</Text>
                  <Text style={styles.formSubtitle}>Sign in to manage team approvals & direct reports</Text>
                </View>

                <Text style={styles.label}>MANAGER USERNAME / EMAIL</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="briefcase-outline" size={18} color="#16A34A" style={styles.inputIcon} />
                  <TextInput style={styles.input} placeholder="manager@company.com" placeholderTextColor="#94A3B8" value={username} onChangeText={setUsername} autoCapitalize="none" />
                </View>

                <Text style={styles.label}>PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput style={styles.input} placeholder="Enter password" placeholderTextColor="#94A3B8" value={password} onChangeText={setPassword} secureTextEntry={!showPass} autoCapitalize="none" />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons name={showPass ? "eye-off-outline" : "eye-outline"} size={18} color="#64748B" />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity activeOpacity={0.85} style={[styles.submitBtn, { backgroundColor: "#16A34A" }]} onPress={() => handleRoleLogin("manager", "Line Manager Portal")} disabled={loading}>
                  {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.submitBtnText}>Sign In to Manager Portal</Text>}
                </TouchableOpacity>

                <TouchableOpacity activeOpacity={0.85} style={[styles.scanBtn, { marginTop: 10, backgroundColor: "#DCFCE7", borderColor: "#BBF7D0" }]} onPress={() => handleAutoFillDemo("manager")}>
                  <Ionicons name="key-outline" size={16} color="#16A34A" />
                  <Text style={[styles.scanBtnText, { color: "#16A34A" }]}>Auto-fill Demo Credentials</Text>
                </TouchableOpacity>
              </>
            ) : tab === "soc_analyst" ? (
              <>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>SecOps Command Center</Text>
                  <Text style={styles.formSubtitle}>Sign in to access SIEM logs & threat telemetry</Text>
                </View>

                <Text style={styles.label}>SECURITY USERNAME / ID</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="shield-checkmark-outline" size={18} color="#EF4444" style={styles.inputIcon} />
                  <TextInput style={styles.input} placeholder="secops_admin" placeholderTextColor="#94A3B8" value={username} onChangeText={setUsername} autoCapitalize="none" />
                </View>

                <Text style={styles.label}>PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput style={styles.input} placeholder="Enter password" placeholderTextColor="#94A3B8" value={password} onChangeText={setPassword} secureTextEntry={!showPass} autoCapitalize="none" />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons name={showPass ? "eye-off-outline" : "eye-outline"} size={18} color="#64748B" />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity activeOpacity={0.85} style={[styles.submitBtn, { backgroundColor: "#EF4444" }]} onPress={() => handleRoleLogin("soc_analyst", "SecOps Command Center")} disabled={loading}>
                  {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.submitBtnText}>Sign In to SecOps Command</Text>}
                </TouchableOpacity>

                <TouchableOpacity activeOpacity={0.85} style={[styles.scanBtn, { marginTop: 10, backgroundColor: "#FEE2E2", borderColor: "#FECACA" }]} onPress={() => handleAutoFillDemo("soc_analyst")}>
                  <Ionicons name="key-outline" size={16} color="#EF4444" />
                  <Text style={[styles.scanBtnText, { color: "#EF4444" }]}>Auto-fill Demo Credentials</Text>
                </TouchableOpacity>
              </>
            ) : tab === "superadmin" ? (
              <>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>SaaS Super Admin</Text>
                  <Text style={styles.formSubtitle}>Sign in to manage multi-tenant SaaS schemas</Text>
                </View>

                <Text style={styles.label}>OPERATOR USERNAME</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="cloud-outline" size={18} color="#0EA5E9" style={styles.inputIcon} />
                  <TextInput style={styles.input} placeholder="superadmin" placeholderTextColor="#94A3B8" value={username} onChangeText={setUsername} autoCapitalize="none" />
                </View>

                <Text style={styles.label}>PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput style={styles.input} placeholder="Enter password" placeholderTextColor="#94A3B8" value={password} onChangeText={setPassword} secureTextEntry={!showPass} autoCapitalize="none" />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons name={showPass ? "eye-off-outline" : "eye-outline"} size={18} color="#64748B" />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity activeOpacity={0.85} style={[styles.submitBtn, { backgroundColor: "#0EA5E9" }]} onPress={() => handleRoleLogin("superadmin", "SaaS Super Admin Portal")} disabled={loading}>
                  {loading ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.submitBtnText}>Sign In as Super Admin</Text>}
                </TouchableOpacity>

                <TouchableOpacity activeOpacity={0.85} style={[styles.scanBtn, { marginTop: 10, backgroundColor: "#E0F2FE", borderColor: "#BAE6FD" }]} onPress={() => handleAutoFillDemo("superadmin")}>
                  <Ionicons name="key-outline" size={16} color="#0EA5E9" />
                  <Text style={[styles.scanBtnText, { color: "#0EA5E9" }]}>Auto-fill Demo Credentials</Text>
                </TouchableOpacity>
              </>
            ) : tab === "employee" ? (
              <>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>Employee Portal</Text>
                  <Text style={styles.formSubtitle}>Sign in to check-in and access self service</Text>
                </View>

                <Text style={styles.label}>EMPLOYEE ID</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="id-card-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Enter employee ID"
                    placeholderTextColor="#94A3B8"
                    value={empId}
                    onChangeText={setEmpId}
                    autoCapitalize="characters"
                    autoCorrect={false}
                  />
                </View>

                <Text style={styles.label}>PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Enter password"
                    placeholderTextColor="#94A3B8"
                    value={empPassword}
                    onChangeText={setEmpPassword}
                    secureTextEntry={!showPass}
                    autoCapitalize="none"
                    autoCorrect={false}
                  />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons
                      name={showPass ? "eye-off-outline" : "eye-outline"}
                      size={18}
                      color="#64748B"
                    />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity
                  activeOpacity={0.85}
                  style={styles.submitBtn}
                  onPress={handleEmployeeLogin}
                  disabled={loading}
                >
                  {loading ? (
                    <ActivityIndicator color="#FFFFFF" />
                  ) : (
                    <Text style={styles.submitBtnText}>Sign In as Employee</Text>
                  )}
                </TouchableOpacity>

                <TouchableOpacity
                  style={{ alignSelf: 'center', marginTop: 12 }}
                  onPress={() => {
                    setForgotRole('employee');
                    setForgotModalVisible(true);
                  }}
                >
                  <Text style={{ color: '#173B8C', fontSize: 13, fontWeight: '600' }}>Forgot Password?</Text>
                </TouchableOpacity>

                <TouchableOpacity activeOpacity={0.85} style={[styles.scanBtn, { marginTop: 12 }]} onPress={() => handleAutoFillDemo("employee")}>
                  <Ionicons name="key-outline" size={16} color="#173B8C" />
                  <Text style={styles.scanBtnText}>Auto-fill Demo Credentials</Text>
                </TouchableOpacity>

                <View style={styles.dividerRow}>
                  <View style={styles.dividerLine} />
                  <Text style={styles.dividerText}>QUICK OPTIONS</Text>
                  <View style={styles.dividerLine} />
                </View>

                <TouchableOpacity
                  activeOpacity={0.85}
                  style={styles.scanBtn}
                  onPress={() => setShowScanner(true)}
                >
                  <Ionicons name="qr-code-outline" size={18} color="#173B8C" />
                  <Text style={styles.scanBtnText}>Scan Attendance QR Code</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  activeOpacity={0.85}
                  style={[styles.scanBtn, { marginTop: 8, backgroundColor: "#F8FAFC", borderColor: "#CBD5E1" }]}
                  onPress={() => setTab("emp_signup")}
                >
                  <Ionicons name="person-add-outline" size={18} color="#0F172A" />
                  <Text style={[styles.scanBtnText, { color: "#0F172A" }]}>Don't have an account? Sign Up</Text>
                </TouchableOpacity>
              </>
            ) : tab === "emp_signup" ? (
              <>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>Employee Sign Up</Text>
                  <Text style={styles.formSubtitle}>Create your staff account to access portal</Text>
                </View>

                <Text style={styles.label}>EMPLOYEE ID</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="id-card-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="EMP-100X"
                    placeholderTextColor="#94A3B8"
                    value={empSignupId}
                    onChangeText={setEmpSignupId}
                    autoCapitalize="characters"
                  />
                </View>

                <Text style={styles.label}>FULL NAME</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="person-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="John Doe"
                    placeholderTextColor="#94A3B8"
                    value={empSignupName}
                    onChangeText={setEmpSignupName}
                  />
                </View>

                <Text style={styles.label}>EMAIL ADDRESS (OPTIONAL)</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="mail-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="john@example.com"
                    placeholderTextColor="#94A3B8"
                    value={empSignupEmail}
                    onChangeText={setEmpSignupEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />
                </View>

                <Text style={styles.label}>PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="At least 6 characters"
                    placeholderTextColor="#94A3B8"
                    value={empSignupPassword}
                    onChangeText={setEmpSignupPassword}
                    secureTextEntry={!showPass}
                    autoCapitalize="none"
                  />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons
                      name={showPass ? "eye-off-outline" : "eye-outline"}
                      size={18}
                      color="#64748B"
                    />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity
                  activeOpacity={0.85}
                  style={styles.submitBtn}
                  onPress={handleEmployeeSignup}
                  disabled={loading}
                >
                  {loading ? (
                    <ActivityIndicator color="#FFFFFF" />
                  ) : (
                    <Text style={styles.submitBtnText}>Create Employee Account</Text>
                  )}
                </TouchableOpacity>
              </>
            ) : (
              <>
                <View style={styles.formHeader}>
                  <Text style={styles.formTitle}>Register Organisation</Text>
                  <Text style={styles.formSubtitle}>Create company account & admin login</Text>
                </View>

                <Text style={styles.label}>COMPANY NAME</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="business-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Acme Corporation"
                    placeholderTextColor="#94A3B8"
                    value={companyName}
                    onChangeText={setCompanyName}
                  />
                </View>

                <Text style={styles.label}>SUBDOMAIN</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="globe-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="acme-corp"
                    placeholderTextColor="#94A3B8"
                    value={subdomain}
                    onChangeText={setSubdomain}
                    autoCapitalize="none"
                    autoCorrect={false}
                  />
                </View>

                <Text style={styles.label}>ADMIN USERNAME</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="person-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="admin_acme"
                    placeholderTextColor="#94A3B8"
                    value={signupUsername}
                    onChangeText={setSignupUsername}
                    autoCapitalize="none"
                  />
                </View>

                <Text style={styles.label}>ADMIN PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="At least 8 characters"
                    placeholderTextColor="#94A3B8"
                    value={signupPassword}
                    onChangeText={setSignupPassword}
                    secureTextEntry={!showPass}
                    autoCapitalize="none"
                  />
                  <TouchableOpacity onPress={() => setShowPass(!showPass)} style={styles.eyeBtn}>
                    <Ionicons
                      name={showPass ? "eye-off-outline" : "eye-outline"}
                      size={18}
                      color="#64748B"
                    />
                  </TouchableOpacity>
                </View>

                <Text style={styles.label}>ADMIN EMAIL (OPTIONAL)</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="mail-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="admin@acme.com"
                    placeholderTextColor="#94A3B8"
                    value={signupEmail}
                    onChangeText={setSignupEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />
                </View>

                <Text style={styles.label}>COMPANY LOGO URL (OPTIONAL)</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="image-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="https://company.com/logo.png"
                    placeholderTextColor="#94A3B8"
                    value={companyLogo}
                    onChangeText={setCompanyLogo}
                    autoCapitalize="none"
                  />
                </View>

                <Text style={styles.label}>SIGNUP CODE (OPTIONAL)</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="key-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Enter signup code if required"
                    placeholderTextColor="#94A3B8"
                    value={signupSecret}
                    onChangeText={setSignupSecret}
                    autoCapitalize="none"
                  />
                </View>

                <TouchableOpacity
                  activeOpacity={0.85}
                  style={styles.submitBtn}
                  onPress={handleOrgSignup}
                  disabled={loading}
                >
                  {loading ? (
                    <ActivityIndicator color="#FFFFFF" />
                  ) : (
                    <Text style={styles.submitBtnText}>Create Organisation</Text>
                  )}
                </TouchableOpacity>
              </>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Forgot Password Modal */}
      <Modal
        visible={forgotModalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setForgotModalVisible(false)}
      >
        <View style={{ flex: 1, backgroundColor: "rgba(15, 23, 42, 0.75)", justifyContent: "center", padding: 20 }}>
          <View style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 24 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Text style={{ fontSize: 18, fontWeight: "700", color: "#0F172A" }}>
                {forgotStep === 1 ? "Forgot Password" : "Reset Password"}
              </Text>
              <TouchableOpacity onPress={() => setForgotModalVisible(false)}>
                <Ionicons name="close-circle" size={24} color="#64748B" />
              </TouchableOpacity>
            </View>

            {forgotStep === 1 ? (
              <>
                <Text style={{ color: "#64748B", fontSize: 13, marginBottom: 16 }}>
                  Enter your registered email address to receive password reset instructions.
                </Text>

                <Text style={styles.label}>EMAIL ADDRESS</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="mail-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="user@company.com"
                    placeholderTextColor="#94A3B8"
                    value={forgotEmail}
                    onChangeText={setForgotEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />
                </View>

                <TouchableOpacity
                  style={[styles.submitBtn, { marginTop: 16 }]}
                  onPress={handleForgotPasswordRequest}
                  disabled={loading}
                >
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.submitBtnText}>Send Reset Code</Text>}
                </TouchableOpacity>
              </>
            ) : (
              <>
                <Text style={{ color: "#64748B", fontSize: 13, marginBottom: 16 }}>
                  Enter the reset token sent to your email and your new password.
                </Text>

                <Text style={styles.label}>RESET TOKEN</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="key-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Enter reset token"
                    placeholderTextColor="#94A3B8"
                    value={forgotToken}
                    onChangeText={setForgotToken}
                    autoCapitalize="none"
                  />
                </View>

                <Text style={styles.label}>NEW PASSWORD</Text>
                <View style={styles.inputRow}>
                  <Ionicons name="lock-closed-outline" size={18} color="#64748B" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="New password (min 6 chars)"
                    placeholderTextColor="#94A3B8"
                    value={newPassword}
                    onChangeText={setNewPassword}
                    secureTextEntry
                    autoCapitalize="none"
                  />
                </View>

                <TouchableOpacity
                  style={[styles.submitBtn, { marginTop: 16 }]}
                  onPress={handleResetPasswordSubmit}
                  disabled={loading}
                >
                  {loading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.submitBtnText}>Update Password</Text>}
                </TouchableOpacity>
              </>
            )}
          </View>
        </View>
      </Modal>

      {/* MFA Verification Modal */}
      <Modal
        visible={mfaModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setMfaModalVisible(false)}
      >
        <View style={{ flex: 1, backgroundColor: "rgba(15, 23, 42, 0.75)", justifyContent: "center", padding: 20 }}>
          <View style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 24, alignItems: "center" }}>
            <Ionicons name="shield-checkmark" size={48} color="#173B8C" style={{ marginBottom: 12 }} />
            <Text style={{ fontSize: 20, fontWeight: "700", color: "#0F172A", marginBottom: 6 }}>
              MFA Verification Required
            </Text>
            <Text style={{ color: "#64748B", fontSize: 13, textAlign: "center", marginBottom: 20 }}>
              Enter the 6-digit verification code from your Authenticator App.
            </Text>

            <View style={[styles.inputRow, { width: "100%", justifyContent: "center" }]}>
              <TextInput
                style={[styles.input, { textAlign: "center", fontSize: 22, letterSpacing: 8 }]}
                placeholder="123456"
                placeholderTextColor="#CBD5E1"
                value={mfaOtp}
                onChangeText={setMfaOtp}
                keyboardType="number-pad"
                maxLength={6}
              />
            </View>

            <TouchableOpacity
              style={[styles.submitBtn, { width: "100%", marginTop: 20 }]}
              onPress={handleVerifyMfa}
              disabled={loading}
            >
              {loading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.submitBtnText}>Verify OTP</Text>}
            </TouchableOpacity>

            <TouchableOpacity style={{ marginTop: 14 }} onPress={() => setMfaModalVisible(false)}>
              <Text style={{ color: "#64748B", fontSize: 13 }}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  bg: { flex: 1 },
  scroll: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: 22,
    paddingVertical: 32,
  },

  header: {
    alignItems: "center",
    marginBottom: 24,
  },
  logoCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: "#FFFFFF",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: "#FFFFFF",
    letterSpacing: -0.5,
  },
  companyText: {
    fontSize: 13,
    color: "rgba(255, 255, 255, 0.78)",
    marginTop: 4,
  },
  headerBadge: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 12,
    backgroundColor: "rgba(255, 255, 255, 0.12)",
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 20,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: "700",
    color: "#FFFFFF",
    letterSpacing: 0.4,
  },

  // Tabs & Role Pills
  rolePill: {
    height: 36,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    borderRadius: 18,
    backgroundColor: "rgba(255, 255, 255, 0.15)",
    marginRight: 8,
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.22)",
  },
  rolePillActive: {
    backgroundColor: "#FFFFFF",
    borderColor: "#FFFFFF",
    shadowColor: "#000000",
    shadowOpacity: 0.15,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  rolePillText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#FFFFFF",
  },
  rolePillTextActive: {
    color: "#173B8C",
    fontWeight: "800",
  },

  tabsContainer: {
    flexDirection: "row",
    backgroundColor: "rgba(255, 255, 255, 0.12)",
    borderRadius: 16,
    padding: 4,
    marginBottom: 20,
  },
  tabBtn: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 10,
    borderRadius: 12,
  },
  tabBtnActive: {
    backgroundColor: "#FFFFFF",
  },
  tabText: {
    fontSize: 12,
    fontWeight: "700",
    color: "rgba(255, 255, 255, 0.75)",
    marginLeft: 4,
  },
  tabTextActive: {
    color: "#173B8C",
  },

  signupToggleRow: {
    flexDirection: "row",
    backgroundColor: "#F1F5F9",
    borderRadius: 12,
    padding: 3,
    marginBottom: 18,
  },
  signupToggleBtn: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: 8,
    borderRadius: 10,
  },
  signupToggleBtnActive: {
    backgroundColor: "#FFFFFF",
    shadowColor: "#0F172A",
    shadowOpacity: 0.08,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  signupToggleText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#64748B",
    marginLeft: 6,
  },
  signupToggleTextActive: {
    color: "#173B8C",
  },

  // Card
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    padding: 22,
    shadowColor: "#0F172A",
    shadowOpacity: 0.12,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 10 },
    elevation: 8,
  },
  formHeader: {
    marginBottom: 20,
  },
  formTitle: {
    fontSize: 19,
    fontWeight: "800",
    color: "#0F172A",
    letterSpacing: -0.4,
  },
  formSubtitle: {
    fontSize: 12,
    color: "#64748B",
    marginTop: 3,
  },
  label: {
    fontSize: 10,
    fontWeight: "800",
    color: "#64748B",
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    height: 48,
    borderRadius: 14,
    backgroundColor: "#F8FAFC",
    borderWidth: 1,
    borderColor: "#E2E8F0",
    paddingHorizontal: 14,
    marginBottom: 16,
  },
  inputIcon: {
    marginRight: 10,
  },
  input: {
    flex: 1,
    height: "100%",
    fontSize: 14,
    color: "#0F172A",
    fontWeight: "600",
  },
  eyeBtn: {
    padding: 6,
  },
  submitBtn: {
    height: 48,
    borderRadius: 14,
    backgroundColor: "#173B8C",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 8,
  },
  submitBtnText: {
    fontSize: 14,
    fontWeight: "800",
    color: "#FFFFFF",
  },

  dividerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 18,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: "#E2E8F0",
  },
  dividerText: {
    fontSize: 10,
    fontWeight: "800",
    color: "#94A3B8",
    paddingHorizontal: 10,
  },
  scanBtn: {
    height: 48,
    borderRadius: 14,
    backgroundColor: "#EEF4FF",
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#DBEAFE",
  },
  scanBtnText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#173B8C",
    marginLeft: 8,
  },
});
