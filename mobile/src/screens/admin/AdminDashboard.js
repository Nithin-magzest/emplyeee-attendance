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
import QuickActionCard from "../../components/admin/QuickActionCard";
import ActivityCard from "../../components/admin/ActivityCard";

import THEME from "../../constants/theme";

export default function AdminDashboard() {
  const [search, setSearch] = useState("");

  return (
    <SafeAreaView style={styles.container}>
      <AdminHeader title="Dashboard" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        {/* Search */}

        <AdminSearchBar
          value={search}
          onChangeText={setSearch}
          placeholder="Search employees..."
        />

        {/* Statistics */}

        <View style={styles.grid}>
          <DashboardStatCard
            title="Employees"
            value="254"
            subtitle="Total Employees"
            icon="people-outline"
            iconColor={THEME.colors.employee}
            iconBackground={THEME.colors.blueBg}
            trend="+12%"
          />

          <DashboardStatCard
            title="Present"
            value="228"
            subtitle="Today's Attendance"
            icon="checkmark-circle-outline"
            iconColor={THEME.colors.success}
            iconBackground={THEME.colors.greenBg}
            trend="+3%"
          />

          <DashboardStatCard
            title="Absent"
            value="18"
            subtitle="Not Checked In"
            icon="close-circle-outline"
            iconColor={THEME.colors.danger}
            iconBackground={THEME.colors.redBg}
          />

          <DashboardStatCard
            title="Payroll"
            value="₹8.2L"
            subtitle="This Month"
            icon="wallet-outline"
            iconColor={THEME.colors.payroll}
            iconBackground={THEME.colors.purpleBg}
          />
        </View>

        {/* Quick Actions */}

                <QuickActionCard
          title="Add Employee"
          subtitle="Register a new employee"
          icon="person-add-outline"
          iconColor={THEME.colors.primary}
          iconBackground={THEME.colors.blueBg}
          onPress={() => {}}
        />

        <QuickActionCard
          title="Attendance"
          subtitle="Manage today's attendance"
          icon="calendar-outline"
          iconColor={THEME.colors.success}
          iconBackground={THEME.colors.greenBg}
          onPress={() => {}}
        />

        <QuickActionCard
          title="Payroll"
          subtitle="Generate employee salaries"
          icon="wallet-outline"
          iconColor={THEME.colors.payroll}
          iconBackground={THEME.colors.purpleBg}
          onPress={() => {}}
        />

        <QuickActionCard
          title="Leave Requests"
          subtitle="Review pending leave requests"
          icon="document-text-outline"
          iconColor={THEME.colors.warning}
          iconBackground={THEME.colors.yellowBg}
          onPress={() => {}}
        />

        {/* Recent Activities */}

        <ActivityCard
          icon="person-add-outline"
          iconColor={THEME.colors.primary}
          iconBackground={THEME.colors.blueBg}
          title="New Employee Registered"
          description="Rahul Sharma joined the Engineering department."
          time="5 minutes ago"
        />

        <ActivityCard
          icon="checkmark-circle-outline"
          iconColor={THEME.colors.success}
          iconBackground={THEME.colors.greenBg}
          title="Attendance Updated"
          description="Today's attendance has been synchronized successfully."
          time="18 minutes ago"
        />

        <ActivityCard
          icon="document-text-outline"
          iconColor={THEME.colors.warning}
          iconBackground={THEME.colors.yellowBg}
          title="Leave Request Submitted"
          description="Priya submitted a Casual Leave request."
          time="34 minutes ago"
        />

        <ActivityCard
          icon="wallet-outline"
          iconColor={THEME.colors.payroll}
          iconBackground={THEME.colors.purpleBg}
          title="Payroll Generated"
          description="June payroll generated successfully."
          time="1 hour ago"
        />

        <View
          style={{
            height: 120,
          }}
        />
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
    paddingHorizontal:
      THEME.spacing.screenHorizontal,

    paddingTop:
      THEME.spacing.screenVertical,

    paddingBottom: 30,
  },

  grid: {
    flexDirection: "row",

    flexWrap: "wrap",

    justifyContent: "space-between",

    marginBottom:
      THEME.spacing.sectionGap,
  },
});