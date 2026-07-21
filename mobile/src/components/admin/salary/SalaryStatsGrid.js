import React from "react";

import {
  View,
  Text,
  StyleSheet,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import SALARY_THEME from "../../../constants/salaryTheme";

function StatCard({
  title,
  value,
  icon,
  color,
  backgroundColor,
}) {
  return (
    <View style={styles.card}>

      <View
        style={[
          styles.iconContainer,
          {
            backgroundColor,
          },
        ]}
      >

        <Ionicons
          name={icon}
          size={22}
          color={color}
        />

      </View>

      <Text
        numberOfLines={1}
        style={styles.value}
      >
        {value}
      </Text>

      <Text style={styles.title}>
        {title}
      </Text>

    </View>
  );
}

export default function SalaryStatsGrid({
  totalEmployees,
  grossSalary,
  deductions,
  netSalary,
}) {
  return (
    <View style={styles.container}>

      <StatCard
        title="Employees"
        value={totalEmployees}
        icon="people-outline"
        color={SALARY_THEME.colors.primary}
        backgroundColor={
          SALARY_THEME.colors.primaryLight
        }
      />

      <StatCard
        title="Gross Salary"
        value={`₹ ${grossSalary.toLocaleString()}`}
        icon="wallet-outline"
        color={SALARY_THEME.colors.success}
        backgroundColor={
          SALARY_THEME.colors.successLight
        }
      />

      <StatCard
        title="Deductions"
        value={`₹ ${deductions.toLocaleString()}`}
        icon="remove-circle-outline"
        color={SALARY_THEME.colors.danger}
        backgroundColor={
          SALARY_THEME.colors.dangerLight
        }
      />

      <StatCard
        title="Net Salary"
        value={`₹ ${netSalary.toLocaleString()}`}
        icon="cash-outline"
        color={SALARY_THEME.colors.warning}
        backgroundColor={
          SALARY_THEME.colors.warningLight
        }
      />

    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginBottom: 20,
  },

  card: {
    width: "48%",

    backgroundColor:
      SALARY_THEME.colors.surface,

    borderRadius:
      SALARY_THEME.radius.lg,

    padding: 18,

    marginBottom: 16,

    borderWidth: 1,

    borderColor:
      SALARY_THEME.colors.border,

    ...SALARY_THEME.shadow,
  },

  iconContainer: {
    width: 48,

    height: 48,

    borderRadius: 14,

    justifyContent: "center",

    alignItems: "center",
  },

  value: {
    marginTop: 16,

    fontSize: 22,

    fontWeight: "800",

    color:
      SALARY_THEME.colors.textPrimary,
  },

  title: {
    marginTop: 6,

    fontSize: 13,

    fontWeight: "600",

    color:
      SALARY_THEME.colors.textMuted,
  },
});