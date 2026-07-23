import React, { useState } from "react";

import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  StyleSheet,
} from "react-native";

import AdminHeader from "../../components/admin/AdminHeader";
import AdminSearchBar from "../../components/admin/AdminSearchBar";

import THEME from "../../constants/theme";

export default function EmployeesScreen() {
  const [search, setSearch] = useState("");

  return (
    <SafeAreaView style={styles.container}>
      <AdminHeader title="Employees" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <AdminSearchBar
          value={search}
          onChangeText={setSearch}
          placeholder="Search employees..."
        />

        {/* Summary */}

        <View style={styles.summaryCard}>
          <Text style={styles.summaryNumber}>
            254
          </Text>

          <Text style={styles.summaryTitle}>
            Total Employees
          </Text>

          <Text style={styles.summarySubtitle}>
            228 Active • 18 On Leave • 8 Inactive
          </Text>
        </View>

        {/* Employee List */}
                <View style={styles.employeeCard}>
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

            <Text style={styles.employeeRole}>
              Software Engineer • Engineering
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
              <Text style={styles.statusText}>
                Active
              </Text>
            </View>

            <Text style={styles.chevron}>
              ›
            </Text>
          </View>
        </View>

        <View style={styles.employeeCard}>
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

            <Text style={styles.employeeRole}>
              UI/UX Designer • Design
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
                Leave
              </Text>
            </View>

            <Text style={styles.chevron}>
              ›
            </Text>
          </View>
        </View>

        <View style={styles.employeeCard}>
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

            <Text style={styles.employeeRole}>
              HR Manager • Human Resources
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
              <Text style={styles.statusText}>
                Active
              </Text>
            </View>

            <Text style={styles.chevron}>
              ›
            </Text>
          </View>
        </View>

        <View style={styles.employeeCard}>
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

            <Text style={styles.employeeRole}>
              QA Engineer • Testing
            </Text>
          </View>

          <View style={styles.rightSection}>
            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor:
                    THEME.colors.redBg,
                },
              ]}
            >
              <Text
                style={[
                  styles.statusText,
                  {
                    color:
                      THEME.colors.danger,
                  },
                ]}
              >
                Inactive
              </Text>
            </View>

            <Text style={styles.chevron}>
              ›
            </Text>
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

  summaryCard: {
    backgroundColor: THEME.colors.card,

    borderRadius: THEME.radius.card,

    padding: THEME.spacing.cardPadding,

    marginBottom: THEME.spacing.sectionGap,

    borderWidth: 1,
    borderColor: THEME.colors.border,

    alignItems: "center",

    ...THEME.shadows.md,
  },

  summaryNumber: {
    ...THEME.typography.statNumber,

    color: THEME.colors.primary,
  },

  summaryTitle: {
    marginTop: 6,

    ...THEME.typography.cardTitle,

    color: THEME.colors.text,
  },

  summarySubtitle: {
    marginTop: 6,

    ...THEME.typography.caption,

    color: THEME.colors.textSecondary,

    textAlign: "center",
  },

  employeeCard: {
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
    marginTop: 2,

    ...THEME.typography.caption,

    color: THEME.colors.textSecondary,
  },

  employeeRole: {
    marginTop: 6,

    ...THEME.typography.body,

    color: THEME.colors.textSecondary,
  },

  rightSection: {
    alignItems: "flex-end",

    justifyContent: "center",
  },

  statusBadge: {
    paddingHorizontal: 12,

    paddingVertical: 5,

    borderRadius: 20,
  },

  statusText: {
    fontSize: 12,

    fontWeight: "700",

    color: THEME.colors.success,
  },

  chevron: {
    marginTop: 10,

    fontSize: 24,

    color: THEME.colors.textLight,

    fontWeight: "600",
  },
});