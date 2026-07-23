import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function AttendanceEmptyState() {
  return (
    <View style={styles.card}>
      <View style={styles.iconContainer}>
        <View style={styles.iconCircle}>
          <Ionicons
            name="calendar-clear-outline"
            size={54}
            color="#173B8C"
          />
        </View>
      </View>

      <Text style={styles.title}>
        No Attendance Records
      </Text>

      <Text style={styles.subtitle}>
        We couldn't find any attendance entries for
        the selected month. Once attendance is marked,
        your records will automatically appear here.
      </Text>

      <View style={styles.tipCard}>
        <Ionicons
          name="information-circle-outline"
          size={18}
          color="#173B8C"
        />

        <Text style={styles.tipText}>
          Try selecting another month or refresh the
          page to check for newly synced attendance.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",

    marginTop: 28,
    marginBottom: 30,

    borderRadius: 24,

    paddingVertical: 40,
    paddingHorizontal: 28,

    alignItems: "center",

    borderWidth: 1,
    borderColor: "#E8EDF5",

    shadowColor: "#0F172A",
    shadowOpacity: 0.06,
    shadowRadius: 18,
    shadowOffset: {
      width: 0,
      height: 8,
    },

    elevation: 5,
  },

  iconContainer: {
    marginBottom: 22,
  },

  iconCircle: {
    width: 110,
    height: 110,

    borderRadius: 55,

    backgroundColor: "#EEF4FF",

    justifyContent: "center",
    alignItems: "center",

    borderWidth: 8,
    borderColor: "#F8FAFC",
  },

  title: {
    fontSize: 22,

    fontWeight: "800",

    color: "#0F172A",

    textAlign: "center",
  },

  subtitle: {
    marginTop: 12,

    fontSize: 15,

    color: "#64748B",

    lineHeight: 24,

    textAlign: "center",
  },

  tipCard: {
    marginTop: 26,

    flexDirection: "row",

    alignItems: "flex-start",

    backgroundColor: "#EEF4FF",

    borderRadius: 16,

    paddingHorizontal: 16,
    paddingVertical: 14,
  },

  tipText: {
    flex: 1,

    marginLeft: 10,

    color: "#173B8C",

    fontSize: 13,

    fontWeight: "600",

    lineHeight: 20,
  },
});