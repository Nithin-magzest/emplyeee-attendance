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

export default function LeaveRequestsScreen() {
  const [search, setSearch] = useState("");

  return (
    <SafeAreaView style={styles.container}>
      <AdminHeader title="Leave Requests" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <AdminSearchBar
          value={search}
          onChangeText={setSearch}
          placeholder="Search leave requests..."
        />

        {/* Summary */}

        <View style={styles.grid}>
          <DashboardStatCard
            title="Pending"
            value="12"
            subtitle="Awaiting Approval"
            icon="time-outline"
            iconColor={THEME.colors.warning}
            iconBackground={THEME.colors.yellowBg}
          />

          <DashboardStatCard
            title="Approved"
            value="38"
            subtitle="This Month"
            icon="checkmark-circle-outline"
            iconColor={THEME.colors.success}
            iconBackground={THEME.colors.greenBg}
          />

          <DashboardStatCard
            title="Rejected"
            value="5"
            subtitle="This Month"
            icon="close-circle-outline"
            iconColor={THEME.colors.danger}
            iconBackground={THEME.colors.redBg}
          />

          <DashboardStatCard
            title="Total"
            value="55"
            subtitle="Leave Requests"
            icon="document-text-outline"
            iconColor={THEME.colors.primary}
            iconBackground={THEME.colors.blueBg}
          />
        </View>

        {/* Leave Requests */}
                <View style={styles.leaveCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>RK</Text>
          </View>

          <View style={styles.employeeInfo}>
            <Text style={styles.employeeName}>
              Rahul Kumar
            </Text>

            <Text style={styles.leaveType}>
              Casual Leave
            </Text>

            <Text style={styles.leaveDates}>
              10 Jul 2026 • 12 Jul 2026
            </Text>

            <Text style={styles.leaveReason}>
              Family Function
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

        <View style={styles.leaveCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>PS</Text>
          </View>

          <View style={styles.employeeInfo}>
            <Text style={styles.employeeName}>
              Priya Sharma
            </Text>

            <Text style={styles.leaveType}>
              Sick Leave
            </Text>

            <Text style={styles.leaveDates}>
              08 Jul 2026 • 09 Jul 2026
            </Text>

            <Text style={styles.leaveReason}>
              Viral Fever
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
                Approved
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.leaveCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>AJ</Text>
          </View>

          <View style={styles.employeeInfo}>
            <Text style={styles.employeeName}>
              Arjun Joshi
            </Text>

            <Text style={styles.leaveType}>
              Earned Leave
            </Text>

            <Text style={styles.leaveDates}>
              15 Jul 2026 • 18 Jul 2026
            </Text>

            <Text style={styles.leaveReason}>
              Personal Work
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
                Rejected
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.leaveCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>VN</Text>
          </View>

          <View style={styles.employeeInfo}>
            <Text style={styles.employeeName}>
              Vikram Nair
            </Text>

            <Text style={styles.leaveType}>
              Maternity Leave
            </Text>

            <Text style={styles.leaveDates}>
              20 Jul 2026 • 20 Aug 2026
            </Text>

            <Text style={styles.leaveReason}>
              Maternity Benefits
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
                Approved
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

  leaveCard: {
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

  leaveType: {
    marginTop: 4,
    ...THEME.typography.bodyMedium,
    color: THEME.colors.primary,
  },

  leaveDates: {
    marginTop: 4,
    ...THEME.typography.caption,
    color: THEME.colors.textSecondary,
  },

  leaveReason: {
    marginTop: 6,
    ...THEME.typography.body,
    color: THEME.colors.textSecondary,
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