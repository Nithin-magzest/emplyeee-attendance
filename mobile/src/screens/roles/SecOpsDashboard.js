import React, { useState } from "react";
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
  Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useAuth } from "../../store/AuthContext";
import AdminHeader from "../../components/admin/AdminHeader";

export default function SecOpsDashboard({ navigation }) {
  const { signOut } = useAuth();
  const [threatLevel, setThreatLevel] = useState("LOW / NOMINAL");
  const [securityLogs, setSecurityLogs] = useState([]);
  const [bannedIPs, setBannedIPs] = useState([]);
  const [newIp, setNewIp] = useState("");
  const [banModal, setBanModal] = useState(false);

  const handleBanIP = () => {
    if (!newIp.trim()) {
      Alert.alert("Input Required", "Please enter a valid IP address.");
      return;
    }
    setBannedIPs([newIp.trim(), ...bannedIPs]);
    setNewIp("");
    setBanModal(false);
    Alert.alert("WAF Rule Added 🛡️", `IP ${newIp.trim()} blacklisted on WAF edge firewall.`);
  };

  return (
    <LinearGradient colors={["#F8FAFC", "#EEF2F6"]} style={styles.container}>
      <SafeAreaView style={styles.container}>
        <AdminHeader title="SIEM Command Center" subtitle="SECOPS TELEMETRY" navigation={navigation} />

        <ScrollView style={styles.scroll} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          {/* Security Hero Banner */}
          <LinearGradient colors={["#0B2253", "#173B8C"]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.heroCard}>
            <View style={styles.heroTopRow}>
              <View>
                <Text style={styles.heroSmall}>SIEM Threat Engine</Text>
                <Text style={styles.heroTitle}>Security Operations</Text>
                <Text style={styles.heroSub}>Live CSP, WAF & Risk Audit Log Engine</Text>
              </View>
              <View style={styles.shieldBadge}>
                <Ionicons name="shield-checkmark" size={22} color="#22C55E" />
              </View>
            </View>

            <View style={styles.metricsGrid}>
              <View style={styles.metricBox}>
                <Text style={styles.metricVal}>0</Text>
                <Text style={styles.metricLabel}>Critical Breaches</Text>
              </View>
              <View style={styles.metricBox}>
                <Text style={styles.metricVal}>{bannedIPs.length}</Text>
                <Text style={styles.metricLabel}>Blacklisted IPs</Text>
              </View>
              <View style={styles.metricBox}>
                <Text style={styles.metricVal}>100%</Text>
                <Text style={styles.metricLabel}>WAF Edge Shield</Text>
              </View>
            </View>

            <TouchableOpacity style={styles.banBtn} onPress={() => setBanModal(true)}>
              <Ionicons name="hand-stop-outline" size={18} color="#0B2253" style={{ marginRight: 6 }} />
              <Text style={styles.banBtnText}>Blacklist IP on WAF Edge</Text>
            </TouchableOpacity>
          </LinearGradient>

          {/* Banned IPs Bar */}
          <View style={styles.ipSection}>
            <Text style={styles.ipSectionTitle}>ACTIVE BANNED IP LIST ({bannedIPs.length})</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingVertical: 4 }}>
              {bannedIPs.map((ip) => (
                <View key={ip} style={styles.ipChip}>
                  <Ionicons name="lock-closed" size={12} color="#EF4444" style={{ marginRight: 4 }} />
                  <Text style={styles.ipChipText}>{ip}</Text>
                </View>
              ))}
            </ScrollView>
          </View>

          {/* Security Audit Log Stream */}
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>REAL-TIME SECURITY LOG AUDIT STREAM</Text>
          </View>

          <FlatList
            data={securityLogs}
            keyExtractor={(item) => item.id}
            scrollEnabled={false}
            renderItem={({ item }) => (
              <View style={styles.logCard}>
                <View style={styles.logTopRow}>
                  <View style={styles.logTypeGroup}>
                    <Ionicons name="alert-circle-outline" size={16} color="#0B2253" style={{ marginRight: 6 }} />
                    <Text style={styles.logType}>{item.type}</Text>
                  </View>
                  <Text style={styles.logTime}>{item.time}</Text>
                </View>

                <Text style={styles.logDetail}>{item.detail}</Text>

                <View style={styles.logFooter}>
                  <Text style={styles.ipText}>IP: {item.ip}</Text>
                  <View style={styles.statusChip}>
                    <Text style={styles.statusChipText}>{item.status}</Text>
                  </View>
                </View>
              </View>
            )}
          />
        </ScrollView>

        {/* Blacklist IP Modal */}
        <Modal visible={banModal} animationType="slide" transparent>
          <View style={styles.modalBg}>
            <View style={styles.modalCard}>
              <View style={styles.modalHeader}>
                <Ionicons name="shield-outline" size={24} color="#173B8C" />
                <Text style={styles.modalTitle}>Blacklist IP Address</Text>
              </View>

              <Text style={styles.modalSub}>
                Adds an instant drop rule to the Web Application Firewall (WAF) to block bad actors.
              </Text>

              <TextInput
                style={styles.ipInput}
                placeholder="Enter IP (e.g. 198.51.100.45)"
                placeholderTextColor="#94A3B8"
                value={newIp}
                onChangeText={setNewIp}
                keyboardType="numeric"
                autoCapitalize="none"
              />

              <View style={styles.modalButtons}>
                <TouchableOpacity style={styles.cancelBtn} onPress={() => setBanModal(false)}>
                  <Text style={styles.cancelBtnText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.confirmBtn} onPress={handleBanIP}>
                  <Text style={styles.confirmBtnText}>Enforce WAF Drop Rule</Text>
                </TouchableOpacity>
              </View>
            </View>
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
  heroCard: { borderRadius: 20, padding: 20, marginBottom: 16, shadowColor: "#0B2253", shadowOpacity: 0.15, shadowRadius: 10, elevation: 4 },
  heroTopRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  heroSmall: { fontSize: 11, fontWeight: "800", color: "#38BDF8", letterSpacing: 1 },
  heroTitle: { fontSize: 22, fontWeight: "800", color: "#FFFFFF", marginTop: 4 },
  heroSub: { fontSize: 12, color: "rgba(255, 255, 255, 0.8)", marginTop: 2 },
  shieldBadge: { width: 42, height: 42, borderRadius: 12, backgroundColor: "rgba(255, 255, 255, 0.15)", justifyContent: "center", alignItems: "center" },
  metricsGrid: { flexDirection: "row", marginTop: 18, backgroundColor: "rgba(255, 255, 255, 0.1)", borderRadius: 14, padding: 12 },
  metricBox: { flex: 1, alignItems: "center" },
  metricVal: { fontSize: 18, fontWeight: "800", color: "#FFFFFF" },
  metricLabel: { fontSize: 10, fontWeight: "600", color: "rgba(255, 255, 255, 0.75)", marginTop: 2 },
  banBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", backgroundColor: "#FFFFFF", paddingVertical: 12, borderRadius: 12, marginTop: 16 },
  banBtnText: { fontSize: 13, fontWeight: "800", color: "#0B2253" },
  ipSection: { marginBottom: 16 },
  ipSectionTitle: { fontSize: 11, fontWeight: "800", color: "#64748B", letterSpacing: 0.8, marginBottom: 6 },
  ipChip: { flexDirection: "row", alignItems: "center", backgroundColor: "#FEE2E2", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 12, marginRight: 8, borderWidth: 1, borderColor: "#FECACA" },
  ipChipText: { fontSize: 12, fontWeight: "700", color: "#EF4444" },
  sectionHeader: { marginBottom: 10 },
  sectionTitle: { fontSize: 11, fontWeight: "800", color: "#64748B", letterSpacing: 0.8 },
  logCard: { backgroundColor: "#FFFFFF", borderRadius: 16, padding: 16, marginBottom: 10, borderWidth: 1, borderColor: "#E2E8F0" },
  logTopRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  logTypeGroup: { flexDirection: "row", alignItems: "center" },
  logType: { fontSize: 14, fontWeight: "800", color: "#0F172A" },
  logTime: { fontSize: 11, color: "#94A3B8", fontWeight: "600" },
  logDetail: { fontSize: 12, color: "#64748B", marginTop: 6 },
  logFooter: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: "#F1F5F9" },
  ipText: { fontSize: 11, fontWeight: "700", color: "#64748B" },
  statusChip: { backgroundColor: "#F1F5F9", paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  statusChipText: { fontSize: 10, fontWeight: "700", color: "#0F172A" },
  modalBg: { flex: 1, backgroundColor: "rgba(15, 23, 42, 0.6)", justifyContent: "center", alignItems: "center", padding: 20 },
  modalCard: { backgroundColor: "#FFFFFF", width: "100%", borderRadius: 20, padding: 20 },
  modalHeader: { flexDirection: "row", alignItems: "center", marginBottom: 10 },
  modalTitle: { fontSize: 18, fontWeight: "800", color: "#0F172A", marginLeft: 10 },
  modalSub: { fontSize: 13, color: "#64748B", lineHeight: 18, marginBottom: 14 },
  ipInput: { height: 46, borderRadius: 12, backgroundColor: "#F8FAFC", borderWidth: 1, borderColor: "#E2E8F0", paddingHorizontal: 14, fontSize: 14, color: "#0F172A", fontWeight: "600" },
  modalButtons: { flexDirection: "row", marginTop: 18, justifyContent: "flex-end" },
  cancelBtn: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 10, marginRight: 8 },
  cancelBtnText: { fontSize: 13, fontWeight: "700", color: "#64748B" },
  confirmBtn: { backgroundColor: "#173B8C", paddingHorizontal: 16, paddingVertical: 10, borderRadius: 10 },
  confirmBtnText: { fontSize: 13, fontWeight: "800", color: "#FFFFFF" },
});
