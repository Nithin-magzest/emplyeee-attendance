import React, { useState } from "react";

import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import AdminHeader from "../../components/admin/AdminHeader";
import AdminSearchBar from "../../components/admin/AdminSearchBar";
import DashboardStatCard from "../../components/admin/DashboardStatCard";

import THEME from "../../constants/theme";

export default function PayrollScreen() {
  const [search, setSearch] = useState("");

  return (
    <SafeAreaView style={styles.container}>
      <AdminHeader title="Payroll" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <AdminSearchBar
          value={search}
          onChangeText={setSearch}
          placeholder="Search employee..."
        />

        {/* Payroll Summary */}

        <View style={styles.grid}>
          <DashboardStatCard
            title="Processed"
            value="248"
            subtitle="Employees Paid"
            icon="wallet-outline"
            iconColor={THEME.colors.success}
            iconBackground={THEME.colors.greenBg}
            trend="+12"
          />

          <DashboardStatCard
            title="Pending"
            value="12"
            subtitle="Awaiting Payroll"
            icon="time-outline"
            iconColor={THEME.colors.warning}
            iconBackground={THEME.colors.yellowBg}
          />

          <DashboardStatCard
            title="Total Payroll"
            value="₹24.8L"
            subtitle="Current Month"
            icon="cash-outline"
            iconColor={THEME.colors.primary}
            iconBackground={THEME.colors.blueBg}
          />

          <DashboardStatCard
            title="Bonuses"
            value="₹2.1L"
            subtitle="Distributed"
            icon="gift-outline"
            iconColor={THEME.colors.payroll}
            iconBackground={THEME.colors.purpleBg}
          />
        </View>

        {/* Employee Payroll */}
                <View style={styles.payrollCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>RK</Text>
          </View>

          <View style={styles.employeeInfo}>
            <Text style={styles.employeeName}>
              Rahul Kumar
            </Text>

            <Text style={styles.employeeId}>
              EMP-1001
            </Text>

            <Text style={styles.salaryText}>
              Gross: ₹58,000
            </Text>

            <Text style={styles.netSalary}>
              Net Pay: ₹54,850
            </Text>
          </View>

          <View style={styles.rightSection}>
            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor:
                    THEME.colors.greenBg,
                },
              ]}
            >
              <Text
                style={[
                  styles.statusText,
                  {
                    color:
                      THEME.colors.success,
                  },
                ]}
              >
                Paid
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.payrollCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>PS</Text>
          </View>

          <View style={styles.employeeInfo}>
            <Text style={styles.employeeName}>
              Priya Sharma
            </Text>

            <Text style={styles.employeeId}>
              EMP-1002
            </Text>

            <Text style={styles.salaryText}>
              Gross: ₹62,500
            </Text>

            <Text style={styles.netSalary}>
              Net Pay: ₹58,940
            </Text>
          </View>

          <View style={styles.rightSection}>
            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor:
                    THEME.colors.greenBg,
                },
              ]}
            >
              <Text
                style={[
                  styles.statusText,
                  {
                    color:
                      THEME.colors.success,
                  },
                ]}
              >
                Paid
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.payrollCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>AJ</Text>
          </View>

          <View style={styles.employeeInfo}>
            <Text style={styles.employeeName}>
              Arjun Joshi
            </Text>

            <Text style={styles.employeeId}>
              EMP-1003
            </Text>

            <Text style={styles.salaryText}>
              Gross: ₹48,000
            </Text>

            <Text style={styles.netSalary}>
              Net Pay: ₹45,320
            </Text>
          </View>

          <View style={styles.rightSection}>
            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor:
                    THEME.colors.yellowBg,
                },
              ]}
            >
              <Text
                style={[
                  styles.statusText,
                  {
                    color:
                      THEME.colors.warning,
                  },
                ]}
              >
                Pending
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.payrollCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>VN</Text>
          </View>

          <View style={styles.employeeInfo}>
            <Text style={styles.employeeName}>
              Vikram Nair
            </Text>

            <Text style={styles.employeeId}>
              EMP-1004
            </Text>

            <Text style={styles.salaryText}>
              Gross: ₹71,000
            </Text>

            <Text style={styles.netSalary}>
              Net Pay: ₹66,540
            </Text>
          </View>

          <View style={styles.rightSection}>
            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor:
                    THEME.colors.greenBg,
                },
              ]}
            >
              <Text
                style={[
                  styles.statusText,
                  {
                    color:
                      THEME.colors.success,
                  },
                ]}
              >
                Paid
              </Text>
            </View>
          </View>
        </View>
                <View style={{ height: 110 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },

  content: {
    paddingHorizontal: THEME.spacing.screenHorizontal,
    paddingTop: THEME.spacing.screenVertical,
    paddingBottom: 30,
  },

  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginBottom: THEME.spacing.sectionGap,
  },

  payrollCard: {
    flexDirection: "row",
    alignItems: "center",

    backgroundColor: THEME.colors.card,

    borderRadius: THEME.radius.card,

    padding: THEME.spacing.cardPadding,

    marginBottom: THEME.spacing.cardGap,

    borderWidth: 1,
    borderColor: THEME.colors.border,

    ...THEME.shadows.sm,
  },

  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,

    backgroundColor: THEME.colors.blueBg,

    justifyContent: "center",
    alignItems: "center",
  },

  avatarText: {
    fontSize: 18,
    fontWeight: "700",
    color: THEME.colors.primary,
  },

  employeeInfo: {
    flex: 1,
    marginLeft: 16,
  },

  employeeName: {
    ...THEME.typography.cardTitle,
    color: THEME.colors.text,
  },

  employeeId: {
    marginTop: 4,
    ...THEME.typography.caption,
    color: THEME.colors.textSecondary,
  },

  salaryText: {
    marginTop: 6,
    ...THEME.typography.body,
    color: THEME.colors.textSecondary,
  },

  netSalary: {
    marginTop: 4,
    ...THEME.typography.bodyMedium,
    color: THEME.colors.success,
    fontWeight: "700",
  },

  rightSection: {
    alignItems: "flex-end",
    justifyContent: "center",
  },

  statusBadge: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
  },

  statusText: {
    fontSize: 12,
    fontWeight: "700",
  },
});