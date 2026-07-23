import React from "react";
import {
  View,
  Text,
  StyleSheet,
  Image,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import THEME from "../../constants/theme";

export default function EmployeeProfileCard({
  employee = {},
  onEdit = () => {},
  onCall = () => {},
}) {
  const initials = employee.name
    ? employee.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .substring(0, 2)
        .toUpperCase()
    : "NA";

  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.profileSection}>
          {employee.photo ? (
            <Image
              source={{ uri: employee.photo }}
              style={styles.avatar}
            />
          ) : (
            <View style={styles.placeholder}>
              <Text style={styles.initials}>
                {initials}
              </Text>
            </View>
          )}

          <View style={styles.info}>
            <Text
              numberOfLines={1}
              style={styles.name}
            >
              {employee.name || "Employee Name"}
            </Text>

            <Text style={styles.designation}>
              {employee.designation || "Designation"}
            </Text>

            <View style={styles.badge}>
              <Text style={styles.badgeText}>
                {employee.employeeId || "EMP001"}
              </Text>
            </View>
          </View>
        </View>

        <TouchableOpacity
          style={styles.editButton}
          activeOpacity={0.8}
          onPress={onEdit}
        >
          <Ionicons
            name="create-outline"
            size={20}
            color={THEME.colors.primary}
          />
        </TouchableOpacity>
      </View>

      <View style={styles.divider} />

      <View style={styles.statsRow}>
        <View style={styles.statItem}>
          <Ionicons
            name="business-outline"
            size={18}
            color={THEME.colors.primary}
          />
          <Text style={styles.statLabel}>
            Department
          </Text>
          <Text style={styles.statValue}>
            {employee.department || "-"}
          </Text>
        </View>

        <View style={styles.statItem}>
          <Ionicons
            name="location-outline"
            size={18}
            color={THEME.colors.primary}
          />
          <Text style={styles.statLabel}>
            Branch
          </Text>
          <Text style={styles.statValue}>
            {employee.branch || "-"}
          </Text>
        </View>

        <View style={styles.statItem}>
          <Ionicons
            name="call-outline"
            size={18}
            color={THEME.colors.primary}
          />
          <TouchableOpacity onPress={onCall}>
            <Text
              numberOfLines={1}
              style={styles.phone}
            >
              {employee.phone || "-"}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    padding: 20,
    marginBottom: 22,

    borderWidth: 1,
    borderColor: "#E9EEF7",

    shadowColor: "#000",
    shadowOpacity: 0.05,
    shadowRadius: 12,
    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 5,
  },

  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  profileSection: {
    flexDirection: "row",
    flex: 1,
    alignItems: "center",
  },

  avatar: {
    width: 78,
    height: 78,
    borderRadius: 39,
  },

  placeholder: {
    width: 78,
    height: 78,
    borderRadius: 39,
    backgroundColor: "#EEF4FF",
    justifyContent: "center",
    alignItems: "center",
  },

  initials: {
    fontSize: 28,
    fontWeight: "700",
    color: THEME.colors.primary,
  },

  info: {
    marginLeft: 16,
    flex: 1,
  },

  name: {
    fontSize: 22,
    fontWeight: "800",
    color: "#0F172A",
  },

  designation: {
    marginTop: 5,
    fontSize: 14,
    color: "#64748B",
  },

  badge: {
    alignSelf: "flex-start",
    marginTop: 12,
    backgroundColor: "#EEF4FF",
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },

  badgeText: {
    color: THEME.colors.primary,
    fontWeight: "700",
    fontSize: 12,
  },

  editButton: {
    width: 48,
    height: 48,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#F8FAFC",
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },

  divider: {
    marginVertical: 20,
    height: 1,
    backgroundColor: "#EEF2F7",
  },

  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  statItem: {
    flex: 1,
    alignItems: "center",
  },

  statLabel: {
    marginTop: 8,
    color: "#64748B",
    fontSize: 12,
  },

  statValue: {
    marginTop: 4,
    color: "#0F172A",
    fontSize: 14,
    fontWeight: "700",
    textAlign: "center",
  },

  phone: {
    marginTop: 4,
    color: THEME.colors.primary,
    fontWeight: "700",
    fontSize: 14,
  },
});