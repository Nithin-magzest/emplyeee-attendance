import React from "react";
import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

function StatBox({
  icon,
  title,
  value,
  color,
  bg,
}) {
  return (
    <View style={styles.statBox}>
      <View
        style={[
          styles.iconContainer,
          { backgroundColor: bg },
        ]}
      >
        <Ionicons
          name={icon}
          size={18}
          color={color}
        />
      </View>

      <Text style={styles.statValue}>
        {value}
      </Text>

      <Text style={styles.statTitle}>
        {title}
      </Text>
    </View>
  );
}

export default function ProgressCard({
  completed = 5,
  pending = 2,
  remaining = 1,
  total = 8,
}) {
  const percentage = Math.round(
    (completed / total) * 100
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Ionicons
          name="analytics"
          size={22}
          color="#173B8C"
        />

        <Text style={styles.title}>
          Onboarding Progress
        </Text>
      </View>

      {/* Progress */}

      <View style={styles.progressSection}>
        <View style={styles.progressCircle}>
          <Text style={styles.percent}>
            {percentage}%
          </Text>

          <Text style={styles.complete}>
            Complete
          </Text>
        </View>

        <View style={styles.progressInfo}>
          <Text style={styles.heading}>
            Great Progress 🎉
          </Text>

          <Text style={styles.subtitle}>
            You have completed{" "}
            <Text style={styles.bold}>
              {completed}
            </Text>{" "}
            of{" "}
            <Text style={styles.bold}>
              {total}
            </Text>{" "}
            onboarding tasks.
          </Text>

          <View style={styles.progressBar}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${percentage}%`,
                },
              ]}
            />
          </View>

          <Text style={styles.progressText}>
            {percentage}% Completed
          </Text>
        </View>
      </View>

      {/* Statistics */}

      <View style={styles.statsRow}>
        <StatBox
          icon="checkmark-circle"
          title="Completed"
          value={completed}
          color="#22C55E"
          bg="#ECFDF5"
        />

        <StatBox
          icon="time"
          title="Pending"
          value={pending}
          color="#F59E0B"
          bg="#FFF7ED"
        />

        <StatBox
          icon="hourglass"
          title="Remaining"
          value={remaining}
          color="#2563EB"
          bg="#EEF4FF"
        />

        <StatBox
          icon="clipboard"
          title="Total"
          value={total}
          color="#7C3AED"
          bg="#F5F3FF"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",

    borderRadius: 26,

    padding: 22,

    marginBottom: 22,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 14,
    shadowOffset: {
      width: 0,
      height: 6,
    },

    elevation: 3,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 22,
  },

  title: {
    marginLeft: 10,
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  progressSection: {
    flexDirection: "row",
    marginBottom: 24,
  },

  progressCircle: {
    width: 100,
    height: 100,

    borderRadius: 50,

    backgroundColor: "#EEF4FF",

    borderWidth: 6,
    borderColor: "#173B8C",

    justifyContent: "center",
    alignItems: "center",
  },

  percent: {
    fontSize: 24,
    fontWeight: "800",
    color: "#173B8C",
  },

  complete: {
    fontSize: 12,
    color: "#64748B",
    marginTop: 2,
  },

  progressInfo: {
    flex: 1,
    marginLeft: 18,
    justifyContent: "center",
  },

  heading: {
    fontSize: 18,
    fontWeight: "800",
    color: "#0F172A",
  },

  subtitle: {
    marginTop: 8,
    fontSize: 14,
    lineHeight: 22,
    color: "#64748B",
  },

  bold: {
    fontWeight: "800",
    color: "#173B8C",
  },

  progressBar: {
    height: 10,
    borderRadius: 10,
    backgroundColor: "#E2E8F0",
    marginTop: 18,
    overflow: "hidden",
  },

  progressFill: {
    height: "100%",
    borderRadius: 10,
    backgroundColor: "#22C55E",
  },

  progressText: {
    marginTop: 8,
    color: "#22C55E",
    fontWeight: "700",
    fontSize: 13,
  },

  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  statBox: {
    width: "23%",

    alignItems: "center",

    backgroundColor: "#F8FAFC",

    borderRadius: 16,

    paddingVertical: 16,
  },

  iconContainer: {
    width: 42,
    height: 42,

    borderRadius: 21,

    justifyContent: "center",
    alignItems: "center",

    marginBottom: 10,
  },

  statValue: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  statTitle: {
    marginTop: 5,
    fontSize: 11,
    fontWeight: "700",
    color: "#64748B",
    textAlign: "center",
  },
});