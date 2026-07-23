import React from "react";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";

const STAT_CONFIG = {
  pending: {
    title: "Pending",
    icon: "time-outline",
    color: LEAVE_THEME.colors.warning,
    background: LEAVE_THEME.colors.warningLight,
  },

  approved: {
    title: "Approved",
    icon: "checkmark-circle-outline",
    color: LEAVE_THEME.colors.success,
    background: LEAVE_THEME.colors.successLight,
  },

  rejected: {
    title: "Rejected",
    icon: "close-circle-outline",
    color: LEAVE_THEME.colors.danger,
    background: LEAVE_THEME.colors.dangerLight,
  },

  holidays: {
    title: "Holidays",
    icon: "calendar-outline",
    color: LEAVE_THEME.colors.primary,
    background: LEAVE_THEME.colors.primaryLight,
  },
};

function StatCard({
  title,
  value,
  icon,
  color,
  background,
}) {
  return (
    <View style={styles.card}>

      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor: background,
          },
        ]}
      >
        <Ionicons
          name={icon}
          size={22}
          color={color}
        />
      </View>

      <Text style={styles.value}>
        {value}
      </Text>

      <Text style={styles.title}>
        {title}
      </Text>

    </View>
  );
}

export default function LeaveStatsGrid({
  pending,
  approved,
  rejected,
  holidays,
}) {
  return (
    <View style={styles.container}>

      <View style={styles.row}>

        <StatCard
          title={STAT_CONFIG.pending.title}
          value={pending}
          icon={STAT_CONFIG.pending.icon}
          color={STAT_CONFIG.pending.color}
          background={STAT_CONFIG.pending.background}
        />

        <StatCard
          title={STAT_CONFIG.approved.title}
          value={approved}
          icon={STAT_CONFIG.approved.icon}
          color={STAT_CONFIG.approved.color}
          background={STAT_CONFIG.approved.background}
        />

      </View>

      <View style={styles.row}>

        <StatCard
          title={STAT_CONFIG.rejected.title}
          value={rejected}
          icon={STAT_CONFIG.rejected.icon}
          color={STAT_CONFIG.rejected.color}
          background={STAT_CONFIG.rejected.background}
        />

        <StatCard
          title={STAT_CONFIG.holidays.title}
          value={holidays}
          icon={STAT_CONFIG.holidays.icon}
          color={STAT_CONFIG.holidays.color}
          background={STAT_CONFIG.holidays.background}
        />

      </View>

    </View>
  );
}

const styles = StyleSheet.create({

  container: {
    marginBottom: 20,
  },

  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 14,
  },

  card: {
    width: "48%",

    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    paddingVertical: 20,

    paddingHorizontal: 16,

    borderWidth: 1,

    borderColor: LEAVE_THEME.colors.border,

    alignItems: "center",

    ...LEAVE_THEME.shadow,
  },

  iconContainer: {
    width: 52,

    height: 52,

    borderRadius: 16,

    justifyContent: "center",

    alignItems: "center",

    marginBottom: 14,
  },

  value: {
    fontSize: 28,

    fontWeight: "800",

    color: LEAVE_THEME.colors.textPrimary,
  },

  title: {
    marginTop: 6,

    fontSize: 13,

    fontWeight: "600",

    color: LEAVE_THEME.colors.textMuted,
  },

});