import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function AttendanceEmptyState() {
  return (
    <View style={styles.container}>
      <Ionicons
        name="calendar-outline"
        size={70}
        color="#CBD5E1"
      />

      <Text style={styles.title}>
        No Attendance Found
      </Text>

      <Text style={styles.subtitle}>
        Attendance records for this month are not available.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 40,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 30,
  },

  title: {
    marginTop: 16,
    fontSize: 18,
    fontWeight: "700",
    color: "#173B8C",
  },

  subtitle: {
    marginTop: 8,
    textAlign: "center",
    color: "#64748B",
    fontSize: 14,
    lineHeight: 22,
  },
});