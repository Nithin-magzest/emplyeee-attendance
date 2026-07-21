import React from "react";

import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import SALARY_THEME from "../../../constants/salaryTheme";

export default function SalaryEmployeeCard({
  employee,
  onView,
  onDownload,
  onEmail,
}) {
  const getStatusStyle = () => {
    switch (employee.payrollStatus) {
      case "Completed":
        return {
          background:
            SALARY_THEME.colors.successLight,
          text:
            SALARY_THEME.colors.success,
        };

      case "Pending":
        return {
          background:
            SALARY_THEME.colors.warningLight,
          text:
            SALARY_THEME.colors.warning,
        };

      default:
        return {
          background:
            SALARY_THEME.colors.primaryLight,
          text:
            SALARY_THEME.colors.primary,
        };
    }
  };

  const status = getStatusStyle();

  return (
    <View style={styles.card}>

      {/* Header */}

      <View style={styles.header}>

        <View style={styles.profileRow}>

          <View style={styles.avatar}>

            <Text style={styles.avatarText}>
              {employee.name.charAt(0)}
            </Text>

          </View>

          <View style={styles.profileInfo}>

            <Text style={styles.name}>
              {employee.name}
            </Text>

            <Text style={styles.employeeId}>
              {employee.employeeId}
            </Text>

            <Text style={styles.department}>
              {employee.department}
            </Text>

          </View>

        </View>

        <View
          style={[
            styles.statusChip,
            {
              backgroundColor:
                status.background,
            },
          ]}
        >

          <Text
            style={[
              styles.statusText,
              {
                color: status.text,
              },
            ]}
          >
            {employee.payrollStatus}
          </Text>

        </View>

      </View>

      {/* Attendance */}

      <View style={styles.section}>

        <Text style={styles.sectionTitle}>
          Attendance
        </Text>

        <View style={styles.attendanceRow}>

          <View style={styles.attendanceItem}>
            <Text style={styles.attendanceValue}>
              {employee.workDays}
            </Text>
            <Text style={styles.attendanceLabel}>
              Days
            </Text>
          </View>

          <View style={styles.attendanceItem}>
            <Text style={styles.attendanceValue}>
              {employee.attendance.full}
            </Text>
            <Text style={styles.attendanceLabel}>
              Full
            </Text>
          </View>

          <View style={styles.attendanceItem}>
            <Text style={styles.attendanceValue}>
              {employee.attendance.late}
            </Text>
            <Text style={styles.attendanceLabel}>
              Late
            </Text>
          </View>

          <View style={styles.attendanceItem}>
            <Text style={styles.attendanceValue}>
              {employee.attendance.absent}
            </Text>
            <Text style={styles.attendanceLabel}>
              Absent
            </Text>
          </View>

        </View>

      </View>

      {/* Salary */}

      <View style={styles.salaryCard}>

        <View style={styles.salaryRow}>

          <Text style={styles.salaryLabel}>
            Gross Salary
          </Text>

          <Text style={styles.salaryValue}>
            ₹ {employee.grossSalary.toLocaleString()}
          </Text>

        </View>

        <View style={styles.salaryRow}>

          <Text style={styles.salaryLabel}>
            Deductions
          </Text>

          <Text
            style={[
              styles.salaryValue,
              {
                color:
                  SALARY_THEME.colors.danger,
              },
            ]}
          >
            ₹
            {employee.deductions.absent.toLocaleString()}
          </Text>

        </View>

        <View style={styles.divider} />

        <View style={styles.salaryRow}>

          <Text style={styles.netLabel}>
            Net Salary
          </Text>

          <Text style={styles.netValue}>
            ₹ {employee.netSalary.toLocaleString()}
          </Text>

        </View>

      </View>

      {/* Actions */}

      <View style={styles.actionRow}>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onView(employee)}
        >

          <Ionicons
            name="eye-outline"
            size={18}
            color={SALARY_THEME.colors.primary}
          />

          <Text style={styles.actionText}>
            View
          </Text>

        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() =>
            onDownload(employee)
          }
        >

          <Ionicons
            name="download-outline"
            size={18}
            color={SALARY_THEME.colors.success}
          />

          <Text style={styles.actionText}>
            Download
          </Text>

        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onEmail(employee)}
        >

          <Ionicons
            name="mail-outline"
            size={18}
            color={SALARY_THEME.colors.warning}
          />

          <Text style={styles.actionText}>
            Email
          </Text>

        </TouchableOpacity>

      </View>

    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor:
      SALARY_THEME.colors.surface,

    borderRadius:
      SALARY_THEME.radius.lg,

    padding: 18,

    marginBottom: 18,

    borderWidth: 1,

    borderColor:
      SALARY_THEME.colors.border,

    ...SALARY_THEME.shadow,
  },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },

  profileRow: {
    flexDirection: "row",
    flex: 1,
  },

  avatar: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor:
      SALARY_THEME.colors.primaryLight,
    justifyContent: "center",
    alignItems: "center",
  },

  avatarText: {
    fontSize: 22,
    fontWeight: "800",
    color: SALARY_THEME.colors.primary,
  },

  profileInfo: {
    marginLeft: 14,
    flex: 1,
  },

  name: {
    fontSize: 17,
    fontWeight: "700",
    color:
      SALARY_THEME.colors.textPrimary,
  },

  employeeId: {
    marginTop: 3,
    fontSize: 13,
    color:
      SALARY_THEME.colors.textLight,
  },

  department: {
    marginTop: 4,
    fontSize: 14,
    color:
      SALARY_THEME.colors.textMuted,
  },

  statusChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },

  statusText: {
    fontSize: 12,
    fontWeight: "700",
  },

  section: {
    marginTop: 20,
  },

  sectionTitle: {
    fontSize: 15,
    fontWeight: "700",
    color:
      SALARY_THEME.colors.textPrimary,
    marginBottom: 12,
  },

  attendanceRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  attendanceItem: {
    alignItems: "center",
    flex: 1,
  },

  attendanceValue: {
    fontSize: 18,
    fontWeight: "800",
    color:
      SALARY_THEME.colors.primary,
  },

  attendanceLabel: {
    marginTop: 4,
    fontSize: 12,
    color:
      SALARY_THEME.colors.textMuted,
  },

  salaryCard: {
    marginTop: 22,
    backgroundColor:
      SALARY_THEME.colors.background,
    borderRadius: 14,
    padding: 16,
  },

  salaryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginVertical: 6,
  },

  salaryLabel: {
    fontSize: 14,
    color:
      SALARY_THEME.colors.textMuted,
  },

  salaryValue: {
    fontSize: 15,
    fontWeight: "700",
    color:
      SALARY_THEME.colors.textPrimary,
  },

  divider: {
    height: 1,
    backgroundColor:
      SALARY_THEME.colors.divider,
    marginVertical: 12,
  },

  netLabel: {
    fontSize: 15,
    fontWeight: "700",
    color:
      SALARY_THEME.colors.textPrimary,
  },

  netValue: {
    fontSize: 22,
    fontWeight: "800",
    color:
      SALARY_THEME.colors.success,
  },

  actionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 22,
  },

  actionButton: {
    flex: 1,
    marginHorizontal: 4,
    height: 44,
    borderRadius: 12,
    borderWidth: 1,
    borderColor:
      SALARY_THEME.colors.border,
    backgroundColor:
      SALARY_THEME.colors.surface,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
  },

  actionText: {
    marginLeft: 6,
    fontSize: 13,
    fontWeight: "700",
    color:
      SALARY_THEME.colors.textPrimary,
  },
});