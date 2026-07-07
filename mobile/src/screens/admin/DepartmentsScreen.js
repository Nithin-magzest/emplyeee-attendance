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

export default function DepartmentsScreen() {
  const [search, setSearch] = useState("");

  return (
    <SafeAreaView style={styles.container}>
      <AdminHeader title="Departments" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <AdminSearchBar
          value={search}
          onChangeText={setSearch}
          placeholder="Search departments..."
        />

        {/* Department Summary */}

        <View style={styles.grid}>
          <DashboardStatCard
            title="Departments"
            value="8"
            subtitle="Total Departments"
            icon="business-outline"
            iconColor={THEME.colors.primary}
            iconBackground={THEME.colors.blueBg}
          />

          <DashboardStatCard
            title="Employees"
            value="248"
            subtitle="Across Departments"
            icon="people-outline"
            iconColor={THEME.colors.success}
            iconBackground={THEME.colors.greenBg}
          />

          <DashboardStatCard
            title="Managers"
            value="14"
            subtitle="Department Heads"
            icon="person-outline"
            iconColor={THEME.colors.payroll}
            iconBackground={THEME.colors.purpleBg}
          />

          <DashboardStatCard
            title="Budget"
            value="₹18.6L"
            subtitle="Monthly Budget"
            icon="cash-outline"
            iconColor={THEME.colors.warning}
            iconBackground={THEME.colors.yellowBg}
          />
        </View>

        {/* Department Cards */}
                <View style={styles.departmentCard}>
          <View style={styles.departmentInfo}>
            <Text style={styles.departmentName}>
              Engineering
            </Text>

            <Text style={styles.departmentHead}>
              Head: Rahul Verma
            </Text>

            <Text style={styles.departmentDetails}>
              Employees: 82
            </Text>

            <Text style={styles.departmentBudget}>
              Monthly Budget: ₹8.4L
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
                Active
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.departmentCard}>
          <View style={styles.departmentInfo}>
            <Text style={styles.departmentName}>
              Human Resources
            </Text>

            <Text style={styles.departmentHead}>
              Head: Priya Sharma
            </Text>

            <Text style={styles.departmentDetails}>
              Employees: 18
            </Text>

            <Text style={styles.departmentBudget}>
              Monthly Budget: ₹1.8L
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
                Active
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.departmentCard}>
          <View style={styles.departmentInfo}>
            <Text style={styles.departmentName}>
              Finance
            </Text>

            <Text style={styles.departmentHead}>
              Head: Arjun Mehta
            </Text>

            <Text style={styles.departmentDetails}>
              Employees: 26
            </Text>

            <Text style={styles.departmentBudget}>
              Monthly Budget: ₹2.6L
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
                Active
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.departmentCard}>
          <View style={styles.departmentInfo}>
            <Text style={styles.departmentName}>
              Marketing
            </Text>

            <Text style={styles.departmentHead}>
              Head: Neha Kapoor
            </Text>

            <Text style={styles.departmentDetails}>
              Employees: 15
            </Text>

            <Text style={styles.departmentBudget}>
              Monthly Budget: ₹1.5L
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
                Inactive
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

  departmentCard: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",

    backgroundColor: THEME.colors.card,

    borderRadius: THEME.radius.card,

    padding: THEME.spacing.cardPadding,

    marginBottom: THEME.spacing.cardGap,

    borderWidth: 1,
    borderColor: THEME.colors.border,

    ...THEME.shadows.sm,
  },

  departmentInfo: {
    flex: 1,
  },

  departmentName: {
    ...THEME.typography.cardTitle,
    color: THEME.colors.text,
  },

  departmentHead: {
    marginTop: 6,
    ...THEME.typography.body,
    color: THEME.colors.textSecondary,
  },

  departmentDetails: {
    marginTop: 4,
    ...THEME.typography.caption,
    color: THEME.colors.textSecondary,
  },

  departmentBudget: {
    marginTop: 8,
    ...THEME.typography.bodyMedium,
    color: THEME.colors.primary,
    fontWeight: "700",
  },

  rightSection: {
    alignItems: "flex-end",
    justifyContent: "center",
    marginLeft: 16,
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