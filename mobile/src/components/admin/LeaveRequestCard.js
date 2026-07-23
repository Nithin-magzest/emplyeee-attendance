import React from "react";

import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import LEAVE_THEME from "../../constants/leaveTheme";
import LeaveStatusChip from "./LeaveStatusChip";

export default function LeaveRequestCard({
  leave,
  onApprove,
  onReject,
  onView,
}) {
  return (
    <View style={styles.card}>

      {/* Header */}

      <View style={styles.header}>

        <View style={styles.avatar}>

          <Ionicons
            name="person"
            size={26}
            color={LEAVE_THEME.colors.primary}
          />

        </View>

        <View style={styles.employeeInfo}>

          <Text style={styles.name}>
            {leave.employeeName}
          </Text>

          <Text style={styles.employeeId}>
            {leave.employeeId}
          </Text>

          <Text style={styles.department}>
            {leave.department}
          </Text>

        </View>

        <LeaveStatusChip
          status={leave.status}
        />

      </View>

      {/* Leave Type */}

      <View style={styles.typeContainer}>

        <Ionicons
          name="briefcase-outline"
          size={18}
          color={LEAVE_THEME.colors.primary}
        />

        <Text style={styles.leaveType}>
          {leave.leaveType}
        </Text>

      </View>

      {/* Dates */}

      <View style={styles.infoRow}>

        <View style={styles.infoBox}>

          <Text style={styles.infoLabel}>
            From
          </Text>

          <Text style={styles.infoValue}>
            {leave.startDate}
          </Text>

        </View>

        <View style={styles.infoBox}>

          <Text style={styles.infoLabel}>
            To
          </Text>

          <Text style={styles.infoValue}>
            {leave.endDate}
          </Text>

        </View>

        <View style={styles.infoBox}>

          <Text style={styles.infoLabel}>
            Duration
          </Text>

          <Text style={styles.infoValue}>
            {leave.days} Days
          </Text>

        </View>

      </View>

      {/* Reason */}

      <View style={styles.reasonContainer}>

        <Text style={styles.reasonTitle}>
          Reason
        </Text>

        <Text style={styles.reason}>
          {leave.reason}
        </Text>

      </View>

      {/* Actions */}

      <View style={styles.actions}>

        <TouchableOpacity
          style={styles.rejectButton}
          activeOpacity={0.85}
          onPress={() => onReject(leave)}
        >

          <Ionicons
            name="close"
            size={18}
            color="#DC2626"
          />

          <Text style={styles.rejectText}>
            Reject
          </Text>

        </TouchableOpacity>

        <TouchableOpacity
          style={styles.viewButton}
          activeOpacity={0.85}
          onPress={() => onView(leave)}
        >

          <Ionicons
            name="eye-outline"
            size={18}
            color="#2563EB"
          />

          <Text style={styles.viewText}>
            View
          </Text>

        </TouchableOpacity>

        <TouchableOpacity
          style={styles.approveButton}
          activeOpacity={0.85}
          onPress={() => onApprove(leave)}
        >

          <Ionicons
            name="checkmark"
            size={18}
            color="#FFFFFF"
          />

          <Text style={styles.approveText}>
            Approve
          </Text>

        </TouchableOpacity>

      </View>

    </View>
  );
}

const styles = StyleSheet.create({

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 18,

    marginBottom: 18,

    borderWidth: 1,

    borderColor:
      LEAVE_THEME.colors.border,

    ...LEAVE_THEME.shadow,
  },

  header: {
    flexDirection: "row",

    alignItems: "center",

    marginBottom: 18,
  },

  avatar: {
    width: 58,

    height: 58,

    borderRadius: 18,

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",
  },

  employeeInfo: {
    flex: 1,

    marginLeft: 14,
  },

  name: {
    fontSize: 17,

    fontWeight: "800",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  employeeId: {
    marginTop: 3,

    fontSize: 13,

    color:
      LEAVE_THEME.colors.textMuted,
  },

  department: {
    marginTop: 3,

    fontSize: 13,

    color:
      LEAVE_THEME.colors.textSecondary,
  },

  typeContainer: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    alignSelf: "flex-start",

    paddingHorizontal: 12,

    paddingVertical: 7,

    borderRadius: 20,

    marginBottom: 18,
  },

  leaveType: {
    marginLeft: 8,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.primary,
  },

  infoRow: {
    flexDirection: "row",

    justifyContent: "space-between",

    marginBottom: 18,
  },

  infoBox: {
    flex: 1,
  },

  infoLabel: {
    fontSize: 12,

    color:
      LEAVE_THEME.colors.textMuted,
  },

  infoValue: {
    marginTop: 5,

    fontSize: 14,

    fontWeight: "700",

    color:
      LEAVE_THEME.colors.textPrimary,
  },

  reasonContainer: {
    backgroundColor: "#F8FAFC",

    borderRadius: 16,

    padding: 14,

    marginBottom: 18,
  },

  reasonTitle: {
    fontWeight: "700",

    color:
      LEAVE_THEME.colors.textPrimary,

    marginBottom: 6,
  },

  reason: {
    color:
      LEAVE_THEME.colors.textSecondary,

    lineHeight: 20,

    fontSize: 14,
  },

  actions: {
    flexDirection: "row",

    justifyContent: "space-between",
  },

  rejectButton: {
    flex: 1,

    marginRight: 8,

    height: 46,

    borderRadius: 14,

    backgroundColor:
      LEAVE_THEME.colors.dangerLight,

    justifyContent: "center",

    alignItems: "center",

    flexDirection: "row",
  },

  rejectText: {
    marginLeft: 6,

    color:
      LEAVE_THEME.colors.danger,

    fontWeight: "700",
  },

  viewButton: {
    flex: 1,

    marginHorizontal: 4,

    height: 46,

    borderRadius: 14,

    backgroundColor:
      LEAVE_THEME.colors.primaryLight,

    justifyContent: "center",

    alignItems: "center",

    flexDirection: "row",
  },

  viewText: {
    marginLeft: 6,

    color:
      LEAVE_THEME.colors.primary,

    fontWeight: "700",
  },

  approveButton: {
    flex: 1,

    marginLeft: 8,

    height: 46,

    borderRadius: 14,

    backgroundColor:
      LEAVE_THEME.colors.success,

    justifyContent: "center",

    alignItems: "center",

    flexDirection: "row",
  },

  approveText: {
    marginLeft: 6,

    color: "#FFFFFF",

    fontWeight: "700",
  },

});