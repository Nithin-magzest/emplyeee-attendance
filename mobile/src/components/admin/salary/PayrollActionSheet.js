import React from "react";

import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Pressable,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import SALARY_THEME from "../../../constants/salaryTheme";

function ActionItem({
  icon,
  color,
  title,
  subtitle,
  onPress,
}) {
  return (
    <TouchableOpacity
      activeOpacity={0.85}
      style={styles.actionItem}
      onPress={onPress}
    >
      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor: color + "15",
          },
        ]}
      >
        <Ionicons
          name={icon}
          size={22}
          color={color}
        />
      </View>

      <View style={styles.textContainer}>
        <Text style={styles.actionTitle}>
          {title}
        </Text>

        <Text style={styles.actionSubtitle}>
          {subtitle}
        </Text>
      </View>

      <Ionicons
        name="chevron-forward"
        size={20}
        color={SALARY_THEME.colors.textLight}
      />
    </TouchableOpacity>
  );
}

export default function PayrollActionSheet({
  visible,
  onClose,
  onGenerate,
  onExport,
  onPrint,
  onEmail,
  onLock,
}) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <Pressable
        style={styles.overlay}
        onPress={onClose}
      />

      <View style={styles.sheet}>

        <View style={styles.handle} />

        <Text style={styles.title}>
          Payroll Actions
        </Text>

        <Text style={styles.subtitle}>
          Select an action for this month's payroll
        </Text>

        <ActionItem
          icon="flash-outline"
          color={SALARY_THEME.colors.primary}
          title="Generate Payroll"
          subtitle="Calculate employee salaries"
          onPress={onGenerate}
        />

        <ActionItem
          icon="download-outline"
          color={SALARY_THEME.colors.success}
          title="Export Excel"
          subtitle="Download payroll report"
          onPress={onExport}
        />

        <ActionItem
          icon="print-outline"
          color={SALARY_THEME.colors.warning}
          title="Print Payroll"
          subtitle="Print salary register"
          onPress={onPrint}
        />

        <ActionItem
          icon="mail-outline"
          color={SALARY_THEME.colors.purple}
          title="Email Payslips"
          subtitle="Send payslips to employees"
          onPress={onEmail}
        />

        <ActionItem
          icon="lock-closed-outline"
          color={SALARY_THEME.colors.danger}
          title="Lock Payroll"
          subtitle="Finalize this payroll"
          onPress={onLock}
        />

        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.cancelButton}
          onPress={onClose}
        >
          <Text style={styles.cancelText}>
            Cancel
          </Text>
        </TouchableOpacity>

      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(15,23,42,0.35)",
  },

  sheet: {
    backgroundColor:
      SALARY_THEME.colors.surface,

    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,

    paddingHorizontal: 22,
    paddingTop: 14,
    paddingBottom: 30,
  },

  handle: {
    width: 52,
    height: 5,
    borderRadius: 3,
    backgroundColor:
      SALARY_THEME.colors.border,

    alignSelf: "center",
    marginBottom: 18,
  },

  title: {
    fontSize: 22,
    fontWeight: "800",
    color:
      SALARY_THEME.colors.textPrimary,
  },

  subtitle: {
    marginTop: 6,
    marginBottom: 22,
    fontSize: 14,
    color:
      SALARY_THEME.colors.textMuted,
  },

  actionItem: {
    flexDirection: "row",
    alignItems: "center",

    paddingVertical: 14,

    borderBottomWidth: 1,
    borderBottomColor:
      SALARY_THEME.colors.divider,
  },

  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 14,

    justifyContent: "center",
    alignItems: "center",
  },

  textContainer: {
    flex: 1,
    marginLeft: 14,
  },

  actionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color:
      SALARY_THEME.colors.textPrimary,
  },

  actionSubtitle: {
    marginTop: 4,
    fontSize: 13,
    color:
      SALARY_THEME.colors.textMuted,
  },

  cancelButton: {
    marginTop: 22,

    height: 52,

    borderRadius:
      SALARY_THEME.radius.md,

    backgroundColor:
      SALARY_THEME.colors.background,

    justifyContent: "center",
    alignItems: "center",

    borderWidth: 1,
    borderColor:
      SALARY_THEME.colors.border,
  },

  cancelText: {
    fontSize: 15,
    fontWeight: "700",
    color:
      SALARY_THEME.colors.textPrimary,
  },
});