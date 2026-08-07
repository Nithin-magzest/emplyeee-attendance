import React from "react";
import { View, Text, StyleSheet, TouchableOpacity, Image } from "react-native";
import { DrawerContentScrollView } from "@react-navigation/drawer";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "../../store/AuthContext";

export default function SuperAdminDrawerContent(props) {
  const { navigation, state } = props;
  const { user, signOut } = useAuth();
  const insets = useSafeAreaInsets();
  const activeRoute = state?.routes[state?.index]?.name || "SuperAdminDashboard";

  const menuItems = [
    { title: "SaaS Operator Hub", icon: "cloud-done-outline", iconFocused: "cloud-done", route: "SuperAdminDashboard", badge: "HOSTED" },
    { title: "Global Analytics", icon: "bar-chart-outline", iconFocused: "bar-chart", route: "Analytics", badge: "METRICS" },
    { title: "Tenant Hierarchies", icon: "git-network-outline", iconFocused: "git-network", route: "OrgChart" },
    { title: "System Configuration", icon: "settings-outline", iconFocused: "settings", route: "Settings" },
  ];

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* SaaS Unified Navy Header */}
      <LinearGradient
        colors={["#0B2253", "#173B8C"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.header}
      >
        <View style={styles.headerRow}>
          <View style={styles.avatarBorder}>
            <View style={styles.avatar}>
              <Ionicons name="cloud" size={24} color="#0B2253" />
            </View>
            <View style={styles.onlineDot} />
          </View>

          <View style={styles.userInfo}>
            <Text style={styles.name} numberOfLines={1}>
              {user?.company || user?.name || "Magzest SaaS Platform"}
            </Text>
            <Text style={styles.empId} numberOfLines={1}>
              {user?.name || "Platform Operator"}
            </Text>
            <View style={styles.roleBadgeRow}>
              <View style={styles.roleBadge}>
                <Ionicons name="sparkles" size={12} color="#F59E0B" style={{ marginRight: 4 }} />
                <Text style={styles.roleText}>Multi-Tenant Super Admin</Text>
              </View>
            </View>
          </View>
        </View>
      </LinearGradient>

      <DrawerContentScrollView {...props} showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>SAAS PLATFORM MANAGEMENT</Text>
          {menuItems.map((item) => {
            const active = activeRoute === item.route;
            return (
              <TouchableOpacity
                key={item.title}
                activeOpacity={0.88}
                style={[styles.menuItem, active && styles.activeMenuItem]}
                onPress={() => {
                  navigation.navigate(item.route);
                  navigation.closeDrawer();
                }}
              >
                <View style={[styles.iconBg, active && styles.activeIconBg]}>
                  <Ionicons name={active ? item.iconFocused : item.icon} size={18} color={active ? "#FFFFFF" : "#0B2253"} />
                </View>

                <Text style={[styles.menuText, active && styles.activeMenuText]} numberOfLines={1}>
                  {item.title}
                </Text>

                {item.badge && !active && (
                  <View style={styles.pillBadge}>
                    <Text style={styles.pillBadgeText}>{item.badge}</Text>
                  </View>
                )}

                <View style={[styles.chevronContainer, active && styles.activeChevronContainer]}>
                  <Ionicons name={active ? "checkmark-circle" : "chevron-forward"} size={16} color={active ? "#22C55E" : "#94A3B8"} />
                </View>
              </TouchableOpacity>
            );
          })}
        </View>
      </DrawerContentScrollView>

      {/* Bottom Logout Button */}
      <View style={[styles.bottomContainer, { paddingBottom: Math.max(insets.bottom, 16) }]}>
        <TouchableOpacity activeOpacity={0.88} style={styles.logoutButton} onPress={signOut}>
          <Ionicons name="log-out-outline" size={20} color="#EF4444" />
          <Text style={styles.logoutText}>Sign Out Super Admin</Text>
        </TouchableOpacity>

        <Text style={styles.version}>Magzest HRMS SaaS • Platform v1.0.0</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#FFFFFF" },
  header: { paddingHorizontal: 20, paddingTop: 20, paddingBottom: 22 },
  headerRow: { flexDirection: "row", alignItems: "center" },
  avatarBorder: { width: 54, height: 54, borderRadius: 27, borderWidth: 2, borderColor: "rgba(255, 255, 255, 0.4)", justifyContent: "center", alignItems: "center", position: "relative" },
  avatar: { width: 46, height: 46, borderRadius: 23, backgroundColor: "#FFFFFF", justifyContent: "center", alignItems: "center" },
  onlineDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: "#22C55E", borderWidth: 2, borderColor: "#0B2253", position: "absolute", bottom: 0, right: 0 },
  userInfo: { marginLeft: 14, flex: 1 },
  name: { fontSize: 16, fontWeight: "800", color: "#FFFFFF", letterSpacing: -0.3 },
  empId: { fontSize: 13, color: "rgba(255, 255, 255, 0.8)", marginTop: 2, fontWeight: "500" },
  roleBadgeRow: { marginTop: 6 },
  roleBadge: { flexDirection: "row", alignItems: "center", backgroundColor: "rgba(255, 255, 255, 0.15)", paddingHorizontal: 8, paddingVertical: 3, borderRadius: 12, alignSelf: "flex-start" },
  roleText: { fontSize: 10, fontWeight: "700", color: "#FFFFFF" },
  scroll: { paddingHorizontal: 12, paddingTop: 16 },
  section: { marginBottom: 20 },
  sectionTitle: { fontSize: 11, fontWeight: "800", color: "#64748B", letterSpacing: 0.8, marginBottom: 12, paddingHorizontal: 8 },
  menuItem: { flexDirection: "row", alignItems: "center", paddingVertical: 12, paddingHorizontal: 12, borderRadius: 14, marginBottom: 6, backgroundColor: "transparent" },
  activeMenuItem: { backgroundColor: "#173B8C" },
  iconBg: { width: 34, height: 34, borderRadius: 10, backgroundColor: "#F1F5F9", justifyContent: "center", alignItems: "center", marginRight: 12 },
  activeIconBg: { backgroundColor: "rgba(255, 255, 255, 0.2)" },
  menuText: { flex: 1, fontSize: 14, fontWeight: "600", color: "#1E293B" },
  activeMenuText: { color: "#FFFFFF", fontWeight: "800" },
  pillBadge: { backgroundColor: "#E0F2FE", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10, marginRight: 8 },
  pillBadgeText: { fontSize: 10, fontWeight: "800", color: "#0369A1" },
  chevronContainer: { marginLeft: 4 },
  activeChevronContainer: { backgroundColor: "rgba(255,255,255,0.15)", padding: 4, borderRadius: 12 },
  bottomContainer: { paddingHorizontal: 16, paddingTop: 12, borderTopWidth: 1, borderTopColor: "#F1F5F9" },
  logoutButton: { flexDirection: "row", alignItems: "center", justifyContent: "center", backgroundColor: "#FEF2F2", paddingVertical: 14, borderRadius: 14 },
  logoutText: { fontSize: 14, fontWeight: "700", color: "#EF4444", marginLeft: 8 },
  version: { textAlign: "center", fontSize: 11, color: "#94A3B8", marginTop: 12, fontWeight: "600" },
});
