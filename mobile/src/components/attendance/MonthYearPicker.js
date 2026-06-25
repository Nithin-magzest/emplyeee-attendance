import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export default function MonthYearPicker({
  month,
  year,
  onPrevious,
  onNext,
}) {
  return (
    <View style={styles.card}>
      {/* Top Row */}

      <View style={styles.topRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.smallTitle}>
            Attendance Overview
          </Text>

          <Text style={styles.title}>
            {MONTHS[month - 1]} {year}
          </Text>
        </View>

        <View style={styles.navigation}>
          <TouchableOpacity
            activeOpacity={0.85}
            style={styles.arrowButton}
            onPress={onPrevious}
          >
            <Ionicons
              name="chevron-back"
              size={22}
              color="#173B8C"
            />
          </TouchableOpacity>

          <TouchableOpacity
            activeOpacity={0.85}
            style={styles.arrowButton}
            onPress={onNext}
          >
            <Ionicons
              name="chevron-forward"
              size={22}
              color="#173B8C"
            />
          </TouchableOpacity>
        </View>
      </View>

      {/* Bottom Badge */}

      <View style={styles.badgeRow}>
        <View style={styles.badge}>
          <Ionicons
            name="calendar-outline"
            size={18}
            color="#173B8C"
          />

          <Text style={styles.badgeText}>
            {MONTHS[month - 1]} {year}
          </Text>
        </View>

        <View style={styles.liveBadge}>
          <View style={styles.liveDot} />

          <Text style={styles.liveText}>
            Monthly View
          </Text>
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

  topRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  smallTitle: {
    fontSize: 13,
    fontWeight: "600",
    color: "#64748B",
  },

  title: {
    marginTop: 5,
    fontSize: 26,
    fontWeight: "800",
    color: "#0F172A",
    letterSpacing: -0.4,
  },

  navigation: {
    flexDirection: "row",
  },

  arrowButton: {
    width: 46,
    height: 46,

    borderRadius: 14,

    backgroundColor: "#F8FAFC",

    justifyContent: "center",
    alignItems: "center",

    marginLeft: 10,

    borderWidth: 1,
    borderColor: "#E5E7EB",
  },

  badgeRow: {
    marginTop: 22,

    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  badge: {
    flexDirection: "row",
    alignItems: "center",

    backgroundColor: "#EEF4FF",

    paddingHorizontal: 14,
    paddingVertical: 9,

    borderRadius: 30,
  },

  badgeText: {
    marginLeft: 8,

    color: "#173B8C",

    fontWeight: "700",

    fontSize: 14,
  },

  liveBadge: {
    flexDirection: "row",
    alignItems: "center",

    backgroundColor: "#ECFDF5",

    paddingHorizontal: 12,
    paddingVertical: 8,

    borderRadius: 30,
  },

  liveDot: {
    width: 8,
    height: 8,

    borderRadius: 4,

    backgroundColor: "#22C55E",

    marginRight: 7,
  },

  liveText: {
    color: "#15803D",

    fontSize: 12,

    fontWeight: "700",
  },
});