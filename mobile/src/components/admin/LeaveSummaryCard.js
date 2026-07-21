import React from "react";

import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";

export default function LeaveSummaryCard({
  totalRequests,
  pending,
  approved,
  rejected,
  month,
  year,
  onViewAll,
}) {
  return (
    <View style={styles.card}>

      {/* Header */}

      <View style={styles.header}>

        <View>

          <Text style={styles.title}>
            Leave Overview
          </Text>

          <Text style={styles.subtitle}>
            {month} {year}
          </Text>

        </View>

        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.viewButton}
          onPress={onViewAll}
        >

          <Ionicons
            name="arrow-forward"
            size={18}
            color={LEAVE_THEME.colors.primary}
          />

        </TouchableOpacity>

      </View>

      {/* Total Requests */}

      <View style={styles.totalContainer}>

        <Text style={styles.totalLabel}>
          Total Leave Requests
        </Text>

        <Text style={styles.totalValue}>
          {totalRequests}
        </Text>

      </View>

      {/* Divider */}

      <View style={styles.divider} />

      {/* Stats */}

      <View style={styles.statsRow}>

        <View style={styles.statCard}>

          <View
            style={[
              styles.iconCircle,
              {
                backgroundColor:
                  LEAVE_THEME.colors.warningLight,
              },
            ]}
          >

            <Ionicons
              name="time-outline"
              size={20}
              color={
                LEAVE_THEME.colors.warning
              }
            />

          </View>

          <Text style={styles.statNumber}>
            {pending}
          </Text>

          <Text style={styles.statTitle}>
            Pending
          </Text>

        </View>

        <View style={styles.statCard}>

          <View
            style={[
              styles.iconCircle,
              {
                backgroundColor:
                  LEAVE_THEME.colors.successLight,
              },
            ]}
          >

            <Ionicons
              name="checkmark-circle-outline"
              size={20}
              color={
                LEAVE_THEME.colors.success
              }
            />

          </View>

          <Text style={styles.statNumber}>
            {approved}
          </Text>

          <Text style={styles.statTitle}>
            Approved
          </Text>

        </View>

        <View style={styles.statCard}>

          <View
            style={[
              styles.iconCircle,
              {
                backgroundColor:
                  LEAVE_THEME.colors.dangerLight,
              },
            ]}
          >

            <Ionicons
              name="close-circle-outline"
              size={20}
              color={
                LEAVE_THEME.colors.danger
              }
            />

          </View>

          <Text style={styles.statNumber}>
            {rejected}
          </Text>

          <Text style={styles.statTitle}>
            Rejected
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

  viewButton: {
    width: 42,

    height: 42,

    borderRadius: 14,

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",
  },

  totalContainer: {
    marginTop: 24,
    marginBottom: 18,
  },

  totalLabel: {
    fontSize: 14,

    color:
      LEAVE_THEME.colors.textMuted,
  },

  totalValue: {
    marginTop: 6,

    fontSize: 42,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  divider: {
    height: 1,

    backgroundColor:
      LEAVE_THEME.colors.divider,

    marginBottom: 20,
  },

  statsRow: {
    flexDirection: "row",

    justifyContent: "space-between",
  },

  statCard: {
    flex: 1,

    alignItems: "center",
  },

  iconCircle: {
    width: 48,

    height: 48,

    borderRadius: 14,

    justifyContent: "center",

    alignItems: "center",
  },

  statNumber: {
    marginTop: 12,

    fontSize: 22,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  statTitle: {
    marginTop: 4,

    fontSize: 12,

    color:
      LEAVE_THEME.colors.textMuted,

    fontWeight: "600",
  },

});