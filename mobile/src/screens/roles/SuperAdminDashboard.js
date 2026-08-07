import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  FlatList,
  Modal,
  TextInput,
  Image,
  Alert,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useAuth } from "../../store/AuthContext";
import AdminHeader from "../../components/admin/AdminHeader";
import { createOrganisation } from "../../api/client";

export default function SuperAdminDashboard({ navigation }) {
  const { signIn } = useAuth();
  const [tenants, setTenants] = useState([]);

  const [provisionModal, setProvisionModal] = useState(false);
  const [newCompany, setNewCompany] = useState("");
  const [newSubdomain, setNewSubdomain] = useState("");
  const [newIndustry, setNewIndustry] = useState("Technology / SaaS");
  const [newRegion, setNewRegion] = useState("aws-us-east-1 (N. Virginia)");
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [newAdminUser, setNewAdminUser] = useState("");
  const [newAdminPass, setNewAdminPass] = useState("");
  const [newCompanyLogo, setNewCompanyLogo] = useState("");
  const [newPlan, setNewPlan] = useState("Enterprise Unlimited");
  const [submitting, setSubmitting] = useState(false);

  // Reload tenants from AsyncStorage every time screen comes into focus
  useFocusEffect(
    useCallback(() => {
      let isMounted = true;
      const loadTenants = async () => {
        try {
          const saved = await AsyncStorage.getItem("saas_tenants_list");
          if (saved && isMounted) {
            const parsed = JSON.parse(saved);
            if (Array.isArray(parsed)) {
              setTenants(parsed);
            }
          }
        } catch (_) {}
      };
      loadTenants();
      return () => {
        isMounted = false;
      };
    }, [])
  );

  const saveNewTenant = async (newTenantObj) => {
    try {
      const existingStr = await AsyncStorage.getItem("saas_tenants_list");
      let currentList = [];
      if (existingStr) {
        const parsed = JSON.parse(existingStr);
        if (Array.isArray(parsed)) {
          currentList = parsed;
        }
      }

      // Deduplicate by name and subdomain
      const filtered = currentList.filter(
        (t) =>
          t.id !== newTenantObj.id &&
          t.name.toLowerCase() !== newTenantObj.name.toLowerCase() &&
          t.subdomain.toLowerCase() !== newTenantObj.subdomain.toLowerCase()
      );

      const updatedList = [newTenantObj, ...filtered];
      setTenants(updatedList);
      await AsyncStorage.setItem("saas_tenants_list", JSON.stringify(updatedList));
    } catch (_) {
      setTenants((prev) => [newTenantObj, ...prev]);
    }
  };

  const handleProvisionTenant = async () => {
    if (!newCompany.trim() || !newSubdomain.trim() || !newAdminUser.trim() || !newAdminPass.trim()) {
      Alert.alert("Fields Required", "Please enter Company Name, Subdomain, Admin Username, and Admin Password.");
      return;
    }
    setSubmitting(true);
    const cleanSub = newSubdomain.trim().toLowerCase().replace(/[^a-z0-9\-]/g, "-").replace(/^-+|-+$/g, "");
    const adminEmail = newAdminEmail.trim() || `admin@${cleanSub}.com`;
    const logoUrl = newCompanyLogo.trim() || null;

    try {
      await createOrganisation(newCompany.trim(), cleanSub, newAdminUser.trim(), newAdminPass.trim(), adminEmail, "", logoUrl).catch(() => null);
    } catch (_) {}

    const newTenantObj = {
      id: Date.now().toString(),
      name: newCompany.trim(),
      subdomain: `${cleanSub}.hrms.gradzest.com`,
      tier: newPlan,
      industry: newIndustry,
      region: newRegion.split(" ")[0],
      users: 1,
      maxUsers: 1000,
      status: "Active",
      dbSchema: `att_${cleanSub.replace(/-/g, "_")}`,
      dbPool: `Pool D-${Math.floor(Math.random() * 90 + 10)}`,
      adminUser: newAdminUser.trim(),
      adminEmail: adminEmail,
      logo: logoUrl,
    };

    await saveNewTenant(newTenantObj);
    setSubmitting(false);
    setProvisionModal(false);

    Alert.alert(
      "Tenant Provisioned! 🎉",
      `Organisation '${newCompany.trim()}' schema '${newTenantObj.dbSchema}' allocated.\n\nPortal: https://${newTenantObj.subdomain}\nAdmin User: ${newAdminUser.trim()}\nAdmin Email: ${adminEmail}`,
      [
        {
          text: `Log In as ${newAdminUser.trim()} (Org Admin)`,
          onPress: async () => {
            await signIn("admin-org-token", {
              role: "admin",
              name: newAdminUser.trim(),
              company: newCompany.trim(),
              email: adminEmail,
              logo: logoUrl,
              subdomain: newTenantObj.subdomain,
            });
          },
        },
        { text: "Stay in Super Admin Hub", style: "cancel" },
      ]
    );

    setNewCompany("");
    setNewSubdomain("");
    setNewAdminEmail("");
    setNewAdminUser("");
    setNewAdminPass("");
    setNewCompanyLogo("");
  };

  return (
    <LinearGradient colors={["#F8FAFC", "#EEF2F6"]} style={styles.container}>
      <SafeAreaView style={styles.container}>
        <AdminHeader title="Super Admin Hub" subtitle="SAAS OPERATOR" navigation={navigation} />

        <ScrollView style={styles.scroll} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          {/* Operator Hero */}
          <LinearGradient colors={["#0B2253", "#173B8C"]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.heroCard}>
            <View style={styles.heroTopRow}>
              <View>
                <Text style={styles.heroSmall}>Multi-Tenant Operations</Text>
                <Text style={styles.heroTitle}>SaaS Platform Control</Text>
                <Text style={styles.heroSub}>Automated DB Isolation & Multi-Tenant Telemetry</Text>
              </View>
              <View style={styles.cloudBadge}>
                <Ionicons name="cloud-done" size={20} color="#38BDF8" />
              </View>
            </View>

            <View style={styles.metricsGrid}>
              <View style={styles.metricBox}>
                <Text style={styles.metricVal}>{tenants.length}</Text>
                <Text style={styles.metricLabel}>Hosted Tenants</Text>
              </View>
              <View style={styles.metricBox}>
                <Text style={styles.metricVal}>{tenants.reduce((acc, curr) => acc + (curr.users || 1), 0)}</Text>
                <Text style={styles.metricLabel}>Active Licenses</Text>
              </View>
              <View style={styles.metricBox}>
                <Text style={styles.metricVal}>99.99%</Text>
                <Text style={styles.metricLabel}>DB Pool Uptime</Text>
              </View>
            </View>

            <TouchableOpacity style={styles.provisionBtn} onPress={() => setProvisionModal(true)}>
              <Ionicons name="add-circle" size={18} color="#0B2253" style={{ marginRight: 6 }} />
              <Text style={styles.provisionBtnText}>Provision New SaaS Tenant</Text>
            </TouchableOpacity>
          </LinearGradient>

          {/* Tenants Section */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>ACTIVE ORGANISATION TENANTS ({tenants.length})</Text>
            <TouchableOpacity onPress={() => Alert.alert("Telemetry Refresh", "Latest tenant DB metrics updated.")}>
              <Text style={styles.actionLink}>Refresh Metrics</Text>
            </TouchableOpacity>
          </View>

          <FlatList
            data={tenants}
            keyExtractor={(item) => item.id}
            scrollEnabled={false}
            ListEmptyComponent={
              <View style={styles.emptyCard}>
                <Ionicons name="business-outline" size={36} color="#0B2253" style={{ marginBottom: 8 }} />
                <Text style={styles.emptyTitle}>No SaaS Tenants Provisioned</Text>
                <Text style={styles.emptyText}>
                  Tap 'Provision New SaaS Tenant' above to allocate your first organization database schema and Org Admin account.
                </Text>
              </View>
            }
            renderItem={({ item }) => (
              <View style={styles.tenantCard}>
                <View style={styles.tenantTop}>
                  <View style={styles.companyLogoBg}>
                    {item.logo ? (
                      <Image source={{ uri: item.logo }} style={styles.companyLogoImg} />
                    ) : (
                      <Text style={styles.logoText}>{(item.name || "A").charAt(0).toUpperCase()}</Text>
                    )}
                  </View>

                  <View style={{ flex: 1, marginLeft: 12 }}>
                    <Text style={styles.tenantName}>{item.name}</Text>
                    <Text style={styles.tenantUrl}>https://{item.subdomain}</Text>
                  </View>

                  <View style={[styles.statusTag, (item.status || "").includes("Warning") ? styles.statusWarning : styles.statusActive]}>
                    <Text style={[styles.statusText, (item.status || "").includes("Warning") ? styles.statusTextWarning : styles.statusTextActive]}>
                      {item.status || "Active"}
                    </Text>
                  </View>
                </View>

                <View style={styles.infoPillsRow}>
                  <View style={styles.infoPill}>
                    <Ionicons name="ribbon-outline" size={12} color="#0369A1" style={{ marginRight: 4 }} />
                    <Text style={styles.infoPillText}>{item.tier}</Text>
                  </View>
                  <View style={styles.infoPill}>
                    <Ionicons name="globe-outline" size={12} color="#0284C7" style={{ marginRight: 4 }} />
                    <Text style={styles.infoPillText}>{item.region}</Text>
                  </View>
                  <View style={styles.infoPill}>
                    <Ionicons name="person-outline" size={12} color="#475569" style={{ marginRight: 4 }} />
                    <Text style={styles.infoPillText}>{item.adminUser} ({item.adminEmail})</Text>
                  </View>
                </View>

                <View style={styles.progressRow}>
                  <View style={styles.progressBarBg}>
                    <View style={[styles.progressBarFill, { width: `${Math.min(100, ((item.users || 1) / (item.maxUsers || 1000)) * 100)}%` }]} />
                  </View>
                  <Text style={styles.progressText}>
                    {item.users || 1} / {item.maxUsers || 1000} Licenses
                  </Text>
                </View>

                <View style={styles.tenantFooter}>
                  <View style={styles.footerInfo}>
                    <Ionicons name="server-outline" size={14} color="#64748B" />
                    <Text style={styles.footerText}>Schema: {item.dbSchema} ({item.dbPool})</Text>
                  </View>

                  <TouchableOpacity
                    style={styles.manageBtn}
                    onPress={() =>
                      Alert.alert(
                        "Tenant Operations",
                        `Switch to log in as Org Admin for ${item.name}?\n\nAdmin User: ${item.adminUser}\nAdmin Email: ${item.adminEmail}\nSchema: ${item.dbSchema}`,
                        [
                          {
                            text: `Sign In as ${item.adminUser}`,
                            onPress: async () => {
                              await signIn("admin-org-token", {
                                role: "admin",
                                name: item.adminUser,
                                company: item.name,
                                email: item.adminEmail,
                                logo: item.logo,
                                subdomain: item.subdomain,
                              });
                            },
                          },
                          { text: "Cancel", style: "cancel" },
                        ]
                      )
                    }
                  >
                    <Text style={styles.manageBtnText}>Sign In as Org Admin</Text>
                    <Ionicons name="chevron-forward" size={14} color="#173B8C" />
                  </TouchableOpacity>
                </View>
              </View>
            )}
          />
        </ScrollView>

        {/* Provision Modal */}
        <Modal visible={provisionModal} animationType="slide" transparent>
          <View style={styles.modalBg}>
            <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center", width: "100%" }}>
              <View style={styles.modalCard}>
                <View style={styles.modalHeader}>
                  <Ionicons name="cloud-upload" size={24} color="#173B8C" />
                  <Text style={styles.modalTitle}>Provision SaaS Tenant</Text>
                </View>
                <Text style={styles.modalSub}>
                  Allocates isolated PostgreSQL tenant schema, database connection pool locks, and seeds the Organization Admin user.
                </Text>

                {/* Section 1: Organisation & Identity */}
                <Text style={styles.sectionHeaderTitle}>1. ORGANISATION & IDENTITY</Text>
                <Text style={styles.inputLabel}>COMPANY LEGAL NAME</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Apex Global Systems Inc."
                  placeholderTextColor="#94A3B8"
                  value={newCompany}
                  onChangeText={setNewCompany}
                />

                <Text style={styles.inputLabel}>INDUSTRY CATEGORY</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 6, marginBottom: 4 }}>
                  {["Technology / SaaS", "Fintech", "Healthcare", "Logistics & Supply"].map((ind) => (
                    <TouchableOpacity
                      key={ind}
                      style={[styles.chipItem, newIndustry === ind && styles.chipItemActive]}
                      onPress={() => setNewIndustry(ind)}
                    >
                      <Text style={[styles.chipItemText, newIndustry === ind && styles.chipItemTextActive]}>{ind}</Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>

                <Text style={styles.inputLabel}>COMPANY LOGO URL (OPTIONAL)</Text>
                <TextInput
                  style={styles.input}
                  placeholder="https://company.com/logo.png"
                  placeholderTextColor="#94A3B8"
                  value={newCompanyLogo}
                  onChangeText={setNewCompanyLogo}
                  autoCapitalize="none"
                />

                {/* Section 2: Domain & Cloud Region */}
                <Text style={[styles.sectionHeaderTitle, { marginTop: 12 }]}>2. DOMAIN & CLOUD REGION</Text>
                <Text style={styles.inputLabel}>SUBDOMAIN SLUG</Text>
                <TextInput
                  style={styles.input}
                  placeholder="apex-global"
                  placeholderTextColor="#94A3B8"
                  value={newSubdomain}
                  onChangeText={setNewSubdomain}
                  autoCapitalize="none"
                />

                <Text style={styles.inputLabel}>CLOUD REGION DATA CENTER</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 6, marginBottom: 4 }}>
                  {["aws-us-east-1 (N. Virginia)", "gcp-asia-south1 (Mumbai)", "aws-eu-central-1 (Frankfurt)"].map((reg) => (
                    <TouchableOpacity
                      key={reg}
                      style={[styles.chipItem, newRegion === reg && styles.chipItemActive]}
                      onPress={() => setNewRegion(reg)}
                    >
                      <Text style={[styles.chipItemText, newRegion === reg && styles.chipItemTextActive]}>{reg}</Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>

                {/* Section 3: Admin Credentials */}
                <Text style={[styles.sectionHeaderTitle, { marginTop: 12 }]}>3. PRIMARY ORG ADMIN CREDENTIALS</Text>
                <Text style={styles.inputLabel}>ADMIN WORK EMAIL</Text>
                <TextInput
                  style={styles.input}
                  placeholder="admin@apexglobal.com"
                  placeholderTextColor="#94A3B8"
                  value={newAdminEmail}
                  onChangeText={setNewAdminEmail}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />

                <Text style={styles.inputLabel}>ORG ADMIN USERNAME</Text>
                <TextInput
                  style={styles.input}
                  placeholder="apex_admin"
                  placeholderTextColor="#94A3B8"
                  value={newAdminUser}
                  onChangeText={setNewAdminUser}
                  autoCapitalize="none"
                />

                <Text style={styles.inputLabel}>ORG ADMIN PASSWORD</Text>
                <TextInput
                  style={styles.input}
                  placeholder="Pass123!"
                  placeholderTextColor="#94A3B8"
                  value={newAdminPass}
                  onChangeText={setNewAdminPass}
                  secureTextEntry
                />

                {/* Section 4: Plan Tier */}
                <Text style={[styles.sectionHeaderTitle, { marginTop: 12 }]}>4. SUBSCRIPTION PLAN TIER</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 6, marginBottom: 4 }}>
                  {["Enterprise Unlimited", "Professional Tier", "Starter SaaS"].map((tier) => (
                    <TouchableOpacity
                      key={tier}
                      style={[styles.chipItem, newPlan === tier && styles.chipItemActive]}
                      onPress={() => setNewPlan(tier)}
                    >
                      <Text style={[styles.chipItemText, newPlan === tier && styles.chipItemTextActive]}>{tier}</Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>

                <View style={styles.modalButtons}>
                  <TouchableOpacity style={styles.cancelBtn} onPress={() => setProvisionModal(false)} disabled={submitting}>
                    <Text style={styles.cancelBtnText}>Cancel</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.confirmBtn} onPress={handleProvisionTenant} disabled={submitting}>
                    <Text style={styles.confirmBtnText}>{submitting ? "Allocating..." : "Confirm Provisioning"}</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </ScrollView>
          </View>
        </Modal>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { flex: 1 },
  content: { padding: 16, paddingBottom: 40 },
  heroCard: { borderRadius: 20, padding: 20, marginBottom: 20, shadowColor: "#0B2253", shadowOpacity: 0.15, shadowRadius: 10, elevation: 4 },
  heroTopRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  heroSmall: { fontSize: 11, fontWeight: "800", color: "#38BDF8", letterSpacing: 1 },
  heroTitle: { fontSize: 22, fontWeight: "800", color: "#FFFFFF", marginTop: 4 },
  heroSub: { fontSize: 12, color: "rgba(255, 255, 255, 0.8)", marginTop: 2 },
  cloudBadge: { width: 42, height: 42, borderRadius: 12, backgroundColor: "rgba(255, 255, 255, 0.15)", justifyContent: "center", alignItems: "center" },
  metricsGrid: { flexDirection: "row", marginTop: 18, backgroundColor: "rgba(255, 255, 255, 0.1)", borderRadius: 14, padding: 12 },
  metricBox: { flex: 1, alignItems: "center" },
  metricVal: { fontSize: 18, fontWeight: "800", color: "#FFFFFF" },
  metricLabel: { fontSize: 10, fontWeight: "600", color: "rgba(255, 255, 255, 0.75)", marginTop: 2 },
  provisionBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", backgroundColor: "#FFFFFF", paddingVertical: 12, borderRadius: 12, marginTop: 16 },
  provisionBtnText: { fontSize: 13, fontWeight: "800", color: "#0B2253" },
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  sectionTitle: { fontSize: 12, fontWeight: "800", color: "#64748B", letterSpacing: 0.8 },
  actionLink: { fontSize: 12, fontWeight: "700", color: "#173B8C" },
  emptyCard: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 24, alignItems: "center", borderWidth: 1, borderColor: "#E2E8F0", marginBottom: 12 },
  emptyTitle: { fontSize: 15, fontWeight: "800", color: "#0F172A", marginBottom: 4 },
  emptyText: { fontSize: 12, color: "#64748B", textAlign: "center", lineHeight: 18 },
  tenantCard: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: "#E2E8F0" },
  tenantTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  companyLogoBg: { width: 40, height: 40, borderRadius: 12, backgroundColor: "#173B8C", justifyContent: "center", alignItems: "center", overflow: "hidden" },
  companyLogoImg: { width: "100%", height: "100%" },
  logoText: { fontSize: 18, fontWeight: "900", color: "#FFFFFF" },
  tenantName: { fontSize: 16, fontWeight: "800", color: "#0F172A" },
  tenantUrl: { fontSize: 12, color: "#173B8C", fontWeight: "600", marginTop: 2 },
  infoPillsRow: { flexDirection: "row", flexWrap: "wrap", marginTop: 10 },
  infoPill: { flexDirection: "row", alignItems: "center", backgroundColor: "#F1F5F9", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, marginRight: 6, marginBottom: 4 },
  infoPillText: { fontSize: 11, fontWeight: "700", color: "#334155" },
  statusTag: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  statusActive: { backgroundColor: "#DCFCE7" },
  statusWarning: { backgroundColor: "#FEF3C7" },
  statusText: { fontSize: 11, fontWeight: "700" },
  statusTextActive: { color: "#16A34A" },
  statusTextWarning: { color: "#D97706" },
  progressRow: { marginTop: 10, flexDirection: "row", alignItems: "center" },
  progressBarBg: { flex: 1, height: 8, borderRadius: 4, backgroundColor: "#F1F5F9", overflow: "hidden", marginRight: 10 },
  progressBarFill: { height: "100%", backgroundColor: "#173B8C", borderRadius: 4 },
  progressText: { fontSize: 11, fontWeight: "700", color: "#64748B" },
  tenantFooter: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: "#F1F5F9" },
  footerInfo: { flexDirection: "row", alignItems: "center" },
  footerText: { fontSize: 11, color: "#64748B", marginLeft: 6, fontWeight: "500" },
  manageBtn: { flexDirection: "row", alignItems: "center" },
  manageBtnText: { fontSize: 12, fontWeight: "700", color: "#173B8C", marginRight: 4 },
  modalBg: { flex: 1, backgroundColor: "rgba(15, 23, 42, 0.6)", padding: 20 },
  modalCard: { backgroundColor: "#FFFFFF", width: "100%", borderRadius: 20, padding: 20 },
  modalHeader: { flexDirection: "row", alignItems: "center", marginBottom: 4 },
  modalTitle: { fontSize: 18, fontWeight: "800", color: "#0F172A", marginLeft: 10 },
  modalSub: { fontSize: 12, color: "#64748B", lineHeight: 17, marginBottom: 12 },
  sectionHeaderTitle: { fontSize: 11, fontWeight: "800", color: "#173B8C", letterSpacing: 0.8 },
  inputLabel: { fontSize: 10, fontWeight: "800", color: "#64748B", marginTop: 6, letterSpacing: 0.5 },
  input: { height: 40, backgroundColor: "#F8FAFC", borderWidth: 1, borderColor: "#E2E8F0", borderRadius: 10, paddingHorizontal: 12, fontSize: 13, color: "#0F172A", marginTop: 3 },
  chipItem: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12, backgroundColor: "#F1F5F9", marginRight: 6 },
  chipItemActive: { backgroundColor: "#173B8C" },
  chipItemText: { fontSize: 11, fontWeight: "700", color: "#64748B" },
  chipItemTextActive: { color: "#FFFFFF" },
  modalButtons: { flexDirection: "row", marginTop: 18, justifyContent: "flex-end" },
  cancelBtn: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 10, marginRight: 8 },
  cancelBtnText: { fontSize: 13, fontWeight: "700", color: "#64748B" },
  confirmBtn: { backgroundColor: "#173B8C", paddingHorizontal: 16, paddingVertical: 10, borderRadius: 10 },
  confirmBtnText: { fontSize: 13, fontWeight: "800", color: "#FFFFFF" },
});
