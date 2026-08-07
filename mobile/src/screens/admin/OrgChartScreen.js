import React, { useState, useEffect } from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from "react-native";
import { DrawerActions } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import THEME from "../../constants/theme";
import AdminHeader from "../../components/admin/AdminHeader";
import { fetchDepartments } from "../../api/client";

export default function OrgChartScreen({ navigation }) {
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [departments, setDepartments] = useState([]);

  const loadData = async () => {
    try {
      const res = await fetchDepartments();
      if (res?.data?.departments && Array.isArray(res.data.departments)) {
        setDepartments(
          res.data.departments.map((d) => ({
            name: d.name || d.department || "Department",
            head: d.head || d.manager || "Department Head",
            members: d.employees_count || d.count || 0,
            teams: d.teams || ["Core Team"],
          }))
        );
      } else {
        setDepartments([]);
      }
    } catch {
      setDepartments([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  return (
    <LinearGradient colors={["#F8FAFC", "#EEF2F6"]} style={styles.container}>
      <SafeAreaView style={styles.container}>
        <AdminHeader title="Organisation Tree" subtitle="HIERARCHY" navigation={navigation} />

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#173B8C" />}
        >
          <View style={styles.heroCard}>
            <Ionicons name="git-network-outline" size={28} color="#173B8C" />
            <Text style={styles.heroTitle}>Corporate Structure</Text>
            <Text style={styles.heroSub}>Visual Departmental & Team Reporting Matrix</Text>
          </View>

          {loading ? (
            <ActivityIndicator size="large" color="#173B8C" style={{ marginTop: 24 }} />
          ) : departments.length === 0 ? (
            <View style={styles.emptyCard}>
              <Ionicons name="people-outline" size={32} color="#64748B" />
              <Text style={styles.emptyTitle}>No Departments Found</Text>
              <Text style={styles.emptyText}>Add departments and staff members to populate the corporate hierarchy tree.</Text>
            </View>
          ) : (
            departments.map((dept, index) => (
              <View key={index} style={styles.deptCard}>
                <View style={styles.deptHeader}>
                  <View style={styles.deptIconBg}>
                    <Ionicons name="business" size={18} color="#173B8C" />
                  </View>
                  <View style={{ flex: 1, marginLeft: 10 }}>
                    <Text style={styles.deptName}>{dept.name}</Text>
                    <Text style={styles.deptHead}>Head: {dept.head}</Text>
                  </View>
                  <View style={styles.memberBadge}>
                    <Text style={styles.memberText}>{dept.members} Staff</Text>
                  </View>
                </View>

                <View style={styles.teamsRow}>
                  {dept.teams.map((t, idx) => (
                    <View key={idx} style={styles.teamChip}>
                      <Text style={styles.teamChipText}>{t}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ))
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { flex: 1 },
  content: { padding: 16, paddingBottom: 40 },
  heroCard: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 18, alignItems: "center", marginBottom: 16, borderWidth: 1, borderColor: "#E2E8F0" },
  heroTitle: { fontSize: 16, fontWeight: "800", color: "#0F172A", marginTop: 6 },
  heroSub: { fontSize: 12, color: "#64748B", marginTop: 2 },
  emptyCard: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 24, alignItems: "center", borderWidth: 1, borderColor: "#E2E8F0" },
  emptyTitle: { fontSize: 15, fontWeight: "800", color: "#0F172A", marginTop: 8 },
  emptyText: { fontSize: 12, color: "#64748B", textAlign: "center", marginTop: 4 },
  deptCard: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: "#E2E8F0" },
  deptHeader: { flexDirection: "row", alignItems: "center" },
  deptIconBg: { width: 36, height: 36, borderRadius: 10, backgroundColor: "#F1F5F9", justifyContent: "center", alignItems: "center" },
  deptName: { fontSize: 15, fontWeight: "800", color: "#0F172A" },
  deptHead: { fontSize: 12, color: "#64748B", marginTop: 1 },
  memberBadge: { backgroundColor: "#E0F2FE", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  memberText: { fontSize: 11, fontWeight: "700", color: "#0369A1" },
  teamsRow: { flexDirection: "row", flexWrap: "wrap", marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: "#F1F5F9" },
  teamChip: { backgroundColor: "#F8FAFC", paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, marginRight: 6, marginBottom: 4, borderWidth: 1, borderColor: "#E2E8F0" },
  teamChipText: { fontSize: 11, fontWeight: "600", color: "#475569" },
});
