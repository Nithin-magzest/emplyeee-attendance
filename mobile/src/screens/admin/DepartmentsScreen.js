import React, { useState, useEffect } from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
  Text,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { DrawerActions } from "@react-navigation/native";
import { LinearGradient } from "expo-linear-gradient";

import AdminHeader from "../../components/admin/AdminHeader";
import AdminSearchBar from "../../components/admin/AdminSearchBar";
import DashboardStatCard from "../../components/admin/DashboardStatCard";
import THEME from "../../constants/theme";
import { fetchDepartments } from "../../api/client";

export default function DepartmentsScreen({ navigation }) {
  const [search, setSearch] = useState("");
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const res = await fetchDepartments();
      if (res?.data?.ok && Array.isArray(res.data.departments)) {
        setDepartments(res.data.departments);
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

  const filteredDepts = departments.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  const totalEmployees = departments.reduce((acc, d) => acc + (d.count || 0), 0);

  return (
    <LinearGradient colors={["#F8FAFC", "#EEF2F6"]} style={styles.container}>
      <SafeAreaView style={{ flex: 1 }}>
        <AdminHeader title="Departments" subtitle="ORGANISATION UNITS" navigation={navigation} />

        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={["#173B8C"]} />
          }
        >
          <DashboardStatCard
            label="TOTAL DEPARTMENTS"
            value={departments.length.toString()}
            sublabel={`Managing ${totalEmployees} total employee allocations across teams.`}
            iconName="business"
          />

          <AdminSearchBar
            value={search}
            onChangeText={setSearch}
            placeholder="Search departments..."
          />

          <Text style={styles.sectionTitle}>ALL DEPARTMENTS ({filteredDepts.length})</Text>

          {loading ? (
            <ActivityIndicator size="large" color="#173B8C" style={{ marginTop: 20 }} />
          ) : filteredDepts.length === 0 ? (
            <View style={styles.emptyCard}>
              <Text style={styles.emptyText}>No departments found matching your search.</Text>
            </View>
          ) : (
            filteredDepts.map((dept, idx) => (
              <View key={dept.id || idx} style={styles.deptCard}>
                <View style={styles.deptHeader}>
                  <Text style={styles.deptName}>{dept.name}</Text>
                  <View style={styles.countBadge}>
                    <Text style={styles.countText}>{dept.count || 0} Staff</Text>
                  </View>
                </View>
                {dept.head && <Text style={styles.deptHead}>Lead: {dept.head}</Text>}
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
  content: { paddingHorizontal: 20, paddingTop: 10, paddingBottom: 40 },
  sectionTitle: { fontSize: 14, fontWeight: "800", color: "#64748B", marginVertical: 12, letterSpacing: 0.8 },
  emptyCard: { backgroundColor: "#FFFFFF", padding: 20, borderRadius: 16, alignItems: "center", marginTop: 10, borderWidth: 1, borderColor: "#E2E8F0" },
  emptyText: { color: "#64748B", fontSize: 13, fontWeight: "600" },
  deptCard: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 16, marginBottom: 10, borderWidth: 1, borderColor: "#E2E8F0" },
  deptHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  deptName: { fontSize: 16, fontWeight: "800", color: "#0F172A" },
  countBadge: { backgroundColor: "#E0F2FE", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10 },
  countText: { fontSize: 11, fontWeight: "800", color: "#0369A1" },
  deptHead: { fontSize: 12, color: "#64748B", marginTop: 6, fontWeight: "500" },
});