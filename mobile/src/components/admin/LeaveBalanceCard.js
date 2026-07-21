import React from "react";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";

export default function LeaveBalanceCard({
  total,
  remaining,
  used,
}) {
  const percentage =
    total > 0 ? (remaining / total) * 100 : 0;

  return (
    <View style={styles.card}>

      {/* Header */}

      <View style={styles.header}>

        <View>

          <Text style={styles.title}>
            Annual Leave Balance
          </Text>

          <Text style={styles.subtitle}>
            Current Leave Summary
          </Text>

        </View>

        <View style={styles.iconBox}>

          <Ionicons
            name="briefcase-outline"
            size={24}
            color={LEAVE_THEME.colors.primary}
          />

        </View>

      </View>

      {/* Remaining */}

      <View style={styles.balanceSection}>

        <Text style={styles.remainingValue}>
          {remaining}
        </Text>

        <Text style={styles.remainingLabel}>
          Days Remaining
        </Text>

      </View>

      {/* Progress */}

      <View style={styles.progressContainer}>

        <View style={styles.progressBackground}>

          <View
            style={[
              styles.progressFill,
              {
                width: `${percentage}%`,
              },
            ]}
          />

        </View>

      </View>

      {/* Bottom Stats */}

      <View style={styles.statsRow}>

        <View style={styles.statItem}>

          <Text style={styles.statValue}>
            {total}
          </Text>

          <Text style={styles.statLabel}>
            Total
          </Text>

        </View>

        <View style={styles.divider} />

        <View style={styles.statItem}>

          <Text
            style={[
              styles.statValue,
              {
                color:
                  LEAVE_THEME.colors.warning,
              },
            ]}
          >
            {used}
          </Text>

          <Text style={styles.statLabel}>
            Used
          </Text>

        </View>

        <View style={styles.divider} />

        <View style={styles.statItem}>

          <Text
            style={[
              styles.statValue,
              {
                color:
                  LEAVE_THEME.colors.success,
              },
            ]}
          >
            {remaining}
          </Text>

          <Text style={styles.statLabel}>
            Remaining
          </Text>

        </View>

      </View>

    </View>
  );
}

const styles = StyleSheet.create({

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 18,

    borderWidth: 1,

    borderColor:
      LEAVE_THEME.colors.border,

    ...LEAVE_THEME.shadow,
  },

  header: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",
  },

  title: {
    fontSize: 18,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  subtitle: {
    marginTop: 4,

    fontSize: 13,

    color:
      LEAVE_THEME.colors.textMuted,
  },

  iconBox: {
    width: 54,

    height: 54,

    borderRadius: 16,

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",
  },

  balanceSection: {
    marginTop: 28,

    alignItems: "center",
  },

  remainingValue: {
    fontSize: 44,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  remainingLabel: {
    marginTop: 6,

    fontSize: 15,

    color:
      LEAVE_THEME.colors.textMuted,
  },

  progressContainer: {
    marginTop: 24,
  },

  progressBackground: {
    height: 10,

    borderRadius: 10,

    backgroundColor:
      LEAVE_THEME.colors.divider,

    overflow: "hidden",
  },

  progressFill: {
    height: "100%",

    borderRadius: 10,

    backgroundColor:
      LEAVE_THEME.colors.primary,
  },

  statsRow: {
    flexDirection: "row",

    justifyContent: "space-between",

    alignItems: "center",

    marginTop: 24,
  },

  statItem: {
    flex: 1,

    alignItems: "center",
  },

  divider: {
    width: 1,

    height: 42,

    backgroundColor:
      LEAVE_THEME.colors.divider,
  },

  statValue: {
    fontSize: 22,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  statLabel: {
    marginTop: 4,

    fontSize: 12,

    fontWeight: "600",

    color:
      LEAVE_THEME.colors.textMuted,
  },

});