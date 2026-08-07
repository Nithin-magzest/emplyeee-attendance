import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  TouchableOpacity,
  FlatList,
  Alert,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../store/AuthContext";
import { fetchEmployees, fetchLeaveRequests, fetchOnboarding } from "../../api/client";

import AdminHeader from "../../components/admin/AdminHeader";

export default function HrDashboard({ navigation }) {
  const { user, signOut } = useAuth();
  const [stats, setStats] = useState({
    totalEmployees: 0,
    activeOnboarding: 0,
    pendingLeaves: 0,
    pendingResignations: 0,
    openTickets: 0,
  });

  const [onboardingList, setOnboardingList] = useState([]);
  const [pendingLeaveList, setPendingLeaveList] = useState([]);

  useEffect(() => {
    loadHrMetrics();
  }, []);

  const loadHrMetrics = async () => {
    try {
      const [empRes, leaveRes, obRes] = await Promise.all([
        fetchEmployees().catch(() => null),
        fetchLeaveRequests().catch(() => null),
        fetchOnboarding().catch(() => null),
      ]);
      if (empRes?.data?.employees && Array.isArray(empRes.data.employees)) {
        setStats((prev) => ({ ...prev, totalEmployees: empRes.data.employees.length }));
      } else if (Array.isArray(empRes?.data)) {
        setStats((prev) => ({ ...prev, totalEmployees: empRes.data.length }));
      }
      if (leaveRes?.data?.requests && Array.isArray(leaveRes.data.requests)) {
        const pending = leaveRes.data.requests.filter((l) => l.status === "Pending");
        setStats((prev) => ({ ...prev, pendingLeaves: pending.length }));
        setPendingLeaveList(
          pending.map((r) => ({
            id: r.id?.toString() || Math.random().toString(),
            name: r.employee_name || r.name || "Employee",
            days: r.leave_type || "Leave",
            reason: r.reason || "Personal",
            date: r.start_date || "Upcoming",
          }))
        );
      }
      if (obRes?.data && Array.isArray(obRes.data)) {
        setOnboardingList(obRes.data);
        setStats((prev) => ({ ...prev, activeOnboarding: obRes.data.length }));
      }
    } catch (_) {}
  };

  const handleApproveLeave = (id) => {
    setPendingLeaveList(pendingLeaveList.filter((item) => item.id !== id));
    setStats((prev) => ({ ...prev, pendingLeaves: Math.max(0, prev.pendingLeaves - 1) }));
    Alert.alert("Leave Approved", "The leave request has been approved successfully.");
  };

  return (
    <LinearGradient colors={["#F8FAFC", "#EEF2F6"]} style={styles.container}>
      <SafeAreaView style={styles.container}>
        <AdminHeader title="Human Resources" subtitle="HR PORTAL" navigation={navigation} />

        <ScrollView style={styles.scroll} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          {/* HR Welcome Card */}
          <LinearGradient colors={["#0369A1", "#0284C7"]} style={styles.heroCard}>
            <View style={styles.heroTop}>
              <View>
                <Text style={styles.heroSub}>PEOPLE & TALENT MANAGEMENT</Text>
                <Text style={styles.heroName}>{user?.name || "HR Manager"}</Text>
                <Text style={styles.heroCompany}>{user?.company || "Enterprise HRMS"}</Text>
              </View>
              <View style={styles.avatarBg}>
                <Ionicons name="person-circle" size={48} color="#E0F2FE" />
              </View>
            </View>

            <View style={styles.statsRow}>
              <View style={styles.statBox}>
                <Text style={styles.statVal}>{stats.totalEmployees}</Text>
                <Text style={styles.statLbl}>Workforce</Text>
              </View>
              <View style={styles.statLine} />
              <View style={styles.statBox}>
                <Text style={styles.statVal}>{stats.activeOnboarding}</Text>
                <Text style={styles.statLbl}>Onboarding</Text>
              </View>
              <View style={styles.statLine} />
              <View style={styles.statBox}>
                <Text style={styles.statVal}>{stats.pendingLeaves}</Text>
                <Text style={styles.statLbl}>Pending Leave</Text>
              </View>
            </View>
          </LinearGradient>

          {/* Quick Actions */}
          <Text style={styles.sectionTitle}>HR Operations Hub</Text>
          <View style={styles.actionGrid}>
            <TouchableOpacity style={styles.actionTile} onPress={() => navigation.navigate("Employees")}>
              <View style={[styles.tileIconBg, { backgroundColor: "#E0F2FE" }]}>
                <Ionicons name="person-add" size={22} color="#0284C7" />
              </View>
              <Text style={styles.tileTitle}>Employees</Text>
              <Text style={styles.tileDesc}>Directory & Onboard</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionTile} onPress={() => navigation.navigate("LeaveRequests")}>
              <View style={[styles.tileIconBg, { backgroundColor: "#FEF3C7" }]}>
                <Ionicons name="calendar" size={22} color="#D97706" />
              </View>
              <Text style={styles.tileTitle}>Leave & Offs</Text>
              <Text style={styles.tileDesc}>Approvals ({stats.pendingLeaves})</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionTile} onPress={() => navigation.navigate("Onboarding")}>
              <View style={[styles.tileIconBg, { backgroundColor: "#F3E8FF" }]}>
                <Ionicons name="clipboard" size={22} color="#9333EA" />
              </View>
              <Text style={styles.tileTitle}>Onboarding</Text>
              <Text style={styles.tileDesc}>{stats.activeOnboarding} Tasks Active</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionTile} onPress={() => navigation.navigate("Performance")}>
              <View style={[styles.tileIconBg, { backgroundColor: "#DCFCE7" }]}>
                <Ionicons name="trending-up" size={22} color="#16A34A" />
              </View>
              <Text style={styles.tileTitle}>Performance</Text>
              <Text style={styles.tileDesc}>Reviews & KPIs</Text>
            </TouchableOpacity>
          </View>

          {/* Onboarding Tracker */}
          <View style={styles.cardHeader}>
            <Text style={styles.sectionTitle}>Active Onboarding Pipeline</Text>
            <TouchableOpacity onPress={() => navigation.navigate("Onboarding")}>
              <Text style={styles.viewAllText}>View All</Text>
            </TouchableOpacity>
          </View>

          {onboardingList.map((ob) => (
            <View key={ob.id} style={styles.itemCard}>
              <View style={styles.itemLeft}>
                <View style={styles.iconCircle}>
                  <Ionicons name="body" size={20} color="#0284C7" />
                </View>
                <View>
                  <Text style={styles.itemTitle}>{ob.empName}</Text>
                  <Text style={styles.itemSub}>{ob.role} • {ob.dept}</Text>
                </View>
              </View>
              <View style={styles.itemRight}>
                <Text style={styles.progressText}>{ob.progress}</Text>
                <Text style={styles.statusBadge}>{ob.status}</Text>
              </View>
            </View>
          ))}

          {/* Pending Leaves */}
          <View style={[styles.cardHeader, { marginTop: 20 }]}>
            <Text style={styles.sectionTitle}>Pending Leave Approvals</Text>
            <TouchableOpacity onPress={() => navigation.navigate("LeaveRequests")}>
              <Text style={styles.viewAllText}>Manage</Text>
            </TouchableOpacity>
          </View>

          {pendingLeaveList.map((req) => (
            <View key={req.id} style={styles.leaveCard}>
              <View style={styles.leaveInfo}>
                <Text style={styles.leaveName}>{req.name}</Text>
                <Text style={styles.leaveDetail}>{req.days} — {req.reason}</Text>
              </View>
              <TouchableOpacity style={styles.approveBtn} onPress={() => handleApproveLeave(req.id)}>
                <Ionicons name="checkmark-circle" size={18} color="#FFFFFF" />
                <Text style={styles.approveBtnText}>Approve</Text>
              </TouchableOpacity>
            </View>
          ))}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 14,
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: "#E2E8F0",
  },
  menuBtn: { padding: 4 },
  headerTitleContainer: { alignItems: "center" },
  hrBadge: { flexDirection: "row", alignItems: "center", backgroundColor: "#E0F2FE", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 12, marginBottom: 2 },
  hrBadgeText: { fontSize: 10, color: "#0284C7", fontWeight: "700", marginLeft: 4, letterSpacing: 0.5 },
  headerTitle: { fontSize: 18, fontWeight: "700", color: "#0F172A" },
  logoutBtn: { padding: 4 },
  scroll: { flex: 1 },
  content: { padding: 20, paddingBottom: 40 },
  heroCard: { borderRadius: 20, padding: 20, marginBottom: 24, elevation: 4, shadowColor: "#0284C7", shadowOpacity: 0.25, shadowRadius: 10 },
  heroTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  heroSub: { fontSize: 11, color: "#BAE6FD", fontWeight: "700", letterSpacing: 1 },
  heroName: { fontSize: 22, fontWeight: "800", color: "#FFFFFF", marginTop: 2 },
  heroCompany: { fontSize: 13, color: "#E0F2FE", marginTop: 2 },
  avatarBg: { width: 52, height: 52, borderRadius: 26, justifyContent: "center", alignItems: "center" },
  statsRow: { flexDirection: "row", backgroundColor: "rgba(255,255,255,0.15)", padding: 14, borderRadius: 14, alignItems: "center" },
  statBox: { flex: 1, alignItems: "center" },
  statVal: { fontSize: 18, fontWeight: "800", color: "#FFFFFF" },
  statLbl: { fontSize: 11, color: "#E0F2FE", marginTop: 2 },
  statLine: { width: 1, height: 26, backgroundColor: "rgba(255,255,255,0.2)" },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#0F172A", marginBottom: 12 },
  actionGrid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", marginBottom: 20 },
  actionTile: { width: "48%", backgroundColor: "#FFFFFF", padding: 16, borderRadius: 16, marginBottom: 12, borderWidth: 1, borderColor: "#E2E8F0", elevation: 2 },
  tileIconBg: { width: 42, height: 42, borderRadius: 12, justifyContent: "center", alignItems: "center", marginBottom: 10 },
  tileTitle: { fontSize: 14, fontWeight: "700", color: "#0F172A" },
  tileDesc: { fontSize: 11, color: "#64748B", marginTop: 2 },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  viewAllText: { fontSize: 13, fontWeight: "700", color: "#0284C7" },
  itemCard: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFFFFF", padding: 14, borderRadius: 14, marginBottom: 10, borderWidth: 1, borderColor: "#E2E8F0" },
  itemLeft: { flexDirection: "row", alignItems: "center" },
  iconCircle: { width: 36, height: 36, borderRadius: 10, backgroundColor: "#E0F2FE", justifyContent: "center", alignItems: "center", marginRight: 12 },
  itemTitle: { fontSize: 14, fontWeight: "700", color: "#0F172A" },
  itemSub: { fontSize: 12, color: "#64748B", marginTop: 2 },
  itemRight: { alignItems: "flex-end" },
  progressText: { fontSize: 14, fontWeight: "800", color: "#0284C7" },
  statusBadge: { fontSize: 10, color: "#64748B", fontWeight: "600", marginTop: 2 },
  leaveCard: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", backgroundColor: "#FFFFFF", padding: 14, borderRadius: 14, marginBottom: 10, borderWidth: 1, borderColor: "#E2E8F0" },
  leaveInfo: { flex: 1 },
  leaveName: { fontSize: 14, fontWeight: "700", color: "#0F172A" },
  leaveDetail: { fontSize: 12, color: "#64748B", marginTop: 2 },
  approveBtn: { flexDirection: "row", alignItems: "center", backgroundColor: "#16A34A", paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10 },
  approveBtnText: { fontSize: 12, fontWeight: "700", color: "#FFFFFF", marginLeft: 4 },
});
