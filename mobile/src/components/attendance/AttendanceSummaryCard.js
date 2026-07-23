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

export default function AttendanceSummaryCard({
  month,
  year,
  percentage = 96,
  present = 22,
  late = 1,
  absent = 0,
  onPrevious,
  onNext,
}) {
  return (
    <View style={styles.card}>
      {/* Header */}

      <View style={styles.header}>
        <View>
          <Text style={styles.month}>
            {MONTHS[month - 1]} {year}
          </Text>

          <Text style={styles.caption}>
            Attendance Dashboard
          </Text>
        </View>

        <View style={styles.actions}>
          <TouchableOpacity
            activeOpacity={0.85}
            style={styles.iconButton}
            onPress={onPrevious}
          >
            <Ionicons
              name="chevron-back"
              size={18}
              color="#173B8C"
            />
          </TouchableOpacity>

          <TouchableOpacity
            activeOpacity={0.85}
            style={styles.iconButton}
            onPress={onNext}
          >
            <Ionicons
              name="chevron-forward"
              size={18}
              color="#173B8C"
            />
          </TouchableOpacity>
        </View>
      </View>

      {/* Attendance Score */}

      <View style={styles.scoreSection}>
        <View style={styles.scoreHeader}>
          <Text style={styles.scoreTitle}>
            Attendance Score
          </Text>

          <View style={styles.liveBadge}>
            <View style={styles.liveDot} />

            <Text style={styles.liveText}>
              LIVE
            </Text>
          </View>
        </View>

        <Text style={styles.score}>
          {percentage}%
        </Text>

        <Text style={styles.scoreDescription}>
          Based on this month's attendance
        </Text>

        <View style={styles.progressTrack}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${Math.max(
                  0,
                  Math.min(percentage, 100)
                )}%`,
              },
            ]}
          />
        </View>
      </View>

      {/* Divider */}

      <View style={styles.divider} />

      {/* Analytics */}

      <View style={styles.analyticsRow}>
        <View style={styles.metric}>
          <View
            style={[
              styles.metricIcon,
              {
                backgroundColor: "#ECFDF5",
              },
            ]}
          >
            <Ionicons
              name="checkmark-circle"
              size={18}
              color="#16A34A"
            />
          </View>

          <Text style={styles.metricValue}>
            {present}
          </Text>

          <Text style={styles.metricLabel}>
            Present
          </Text>
        </View>

        <View style={styles.verticalDivider} />

        <View style={styles.metric}>
          <View
            style={[
              styles.metricIcon,
              {
                backgroundColor: "#FFF7ED",
              },
            ]}
          >
            <Ionicons
              name="time-outline"
              size={18}
              color="#EA580C"
            />
          </View>

          <Text style={styles.metricValue}>
            {late}
          </Text>

          <Text style={styles.metricLabel}>
            Late
          </Text>
        </View>

        <View style={styles.verticalDivider} />

        <View style={styles.metric}>
          <View
            style={[
              styles.metricIcon,
              {
                backgroundColor: "#FEF2F2",
              },
            ]}
          >
            <Ionicons
              name="close-circle"
              size={18}
              color="#DC2626"
            />
          </View>

          <Text style={styles.metricValue}>
            {absent}
          </Text>

          <Text style={styles.metricLabel}>
            Absent
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",

    marginBottom: 22,

    borderRadius: 20,

    padding: 22,

    borderWidth: 1,

    borderColor: "#EDF2F7",

    shadowColor: "#0F172A",

    shadowOpacity: 0.05,

    shadowRadius: 18,

    shadowOffset: {
      width: 0,
      height: 10,
    },

    elevation: 5,
  },

  header: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  month: {
    fontSize: 26,

    fontWeight: "800",

    color: "#0F172A",

    letterSpacing: -0.6,
  },

  caption: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",

    fontWeight: "600",
  },

  actions: {
    flexDirection: "row",
  },

  iconButton: {
    width: 42,

    height: 42,

    borderRadius: 12,

    backgroundColor: "#F8FAFC",

    borderWidth: 1,

    borderColor: "#E2E8F0",

    justifyContent: "center",

    alignItems: "center",

    marginLeft: 10,
  },

  scoreSection: {
    marginTop: 26,
  },

  scoreHeader: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  scoreTitle: {
    fontSize: 15,

    fontWeight: "700",

    color: "#475569",
  },

  liveBadge: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#ECFDF5",

    paddingHorizontal: 10,

    paddingVertical: 5,

    borderRadius: 30,
  },

  liveDot: {
    width: 7,

    height: 7,

    borderRadius: 4,

    backgroundColor: "#22C55E",

    marginRight: 6,
  },

  liveText: {
    color: "#15803D",

    fontWeight: "700",

    fontSize: 11,
  },

  score: {
    marginTop: 12,

    fontSize: 52,

    fontWeight: "900",

    color: "#173B8C",

    letterSpacing: -2,
  },

  scoreDescription: {
    marginTop: 4,

    fontSize: 13,

    color: "#64748B",
  },

  progressTrack: {
    marginTop: 20,

    height: 6,

    backgroundColor: "#E2E8F0",

    borderRadius: 20,

    overflow: "hidden",
  },

  progressFill: {
    height: "100%",

    backgroundColor: "#173B8C",

    borderRadius: 20,
  },

  divider: {
    marginVertical: 24,

    height: 1,

    backgroundColor: "#EEF2F7",
  },

  analyticsRow: {
    flexDirection: "row",

    alignItems: "center",

    justifyContent: "space-between",
  },

  metric: {
    flex: 1,

    alignItems: "center",
  },
    metricIcon: {
    width: 44,

    height: 44,

    borderRadius: 14,

    justifyContent: "center",

    alignItems: "center",

    marginBottom: 12,
  },

  metricValue: {
    fontSize: 28,

    fontWeight: "800",

    color: "#0F172A",

    letterSpacing: -0.5,
  },

  metricLabel: {
    marginTop: 4,

    fontSize: 13,

    fontWeight: "600",

    color: "#64748B",
  },

  verticalDivider: {
    width: 1,

    alignSelf: "stretch",

    backgroundColor: "#EEF2F7",

    marginHorizontal: 8,
  },
});