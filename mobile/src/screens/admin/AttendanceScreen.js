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
import DashboardStatCard from "../../components/admin/DashboardStatCard";

import THEME from "../../constants/theme";

export default function AttendanceScreen() {
  const [search, setSearch] = useState("");

  return (
    <SafeAreaView style={styles.container}>
      <AdminHeader title="Attendance" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <AdminSearchBar
          value={search}
          onChangeText={setSearch}
          placeholder="Search employee..."
        />

        {/* Attendance Summary */}

        <View style={styles.grid}>
          <DashboardStatCard
            title="Present"
            value="228"
            subtitle="Today's Present"
            icon="checkmark-circle-outline"
            iconColor={THEME.colors.success}
            iconBackground={THEME.colors.greenBg}
            trend="+3%"
          />

          <DashboardStatCard
            title="Absent"
            value="18"
            subtitle="Today's Absent"
            icon="close-circle-outline"
            iconColor={THEME.colors.danger}
            iconBackground={THEME.colors.redBg}
          />

          <DashboardStatCard
            title="Late"
            value="8"
            subtitle="Late Arrivals"
            icon="time-outline"
            iconColor={THEME.colors.warning}
            iconBackground={THEME.colors.yellowBg}
          />

          <DashboardStatCard
            title="On Leave"
            value="12"
            subtitle="Approved Leave"
            icon="airplane-outline"
            iconColor={THEME.colors.primary}
            iconBackground={THEME.colors.blueBg}
          />
        </View>

        {/* Employee Attendance */}
                <View style={styles.attendanceCard}>
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

            <Text style={styles.timeText}>
              In: 09:02 AM • Out: 06:08 PM
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
              <Text style={styles.presentText}>
                Present
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.attendanceCard}>
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

            <Text style={styles.timeText}>
              In: 09:38 AM • Out: --
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
                  styles.presentText,
                  {
                    color:
                      THEME.colors.warning,
                  },
                ]}
              >
                Late
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.attendanceCard}>
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

            <Text style={styles.timeText}>
              No Attendance Recorded
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
                  styles.presentText,
                  {
                    color:
                      THEME.colors.danger,
                  },
                ]}
              >
                Absent
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.attendanceCard}>
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

            <Text style={styles.timeText}>
              Approved Leave
            </Text>
          </View>

          <View style={styles.rightSection}>
            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor:
                    THEME.colors.blueBg,
                },
              ]}
            >
              <Text
                style={[
                  styles.presentText,
                  {
                    color:
                      THEME.colors.primary,
                  },
                ]}
              >
                Leave
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

  attendanceCard: {
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

  timeText: {
    marginTop: 6,
    ...THEME.typography.body,
    color: THEME.colors.textSecondary,
  },

  rightSection: {
    justifyContent: "center",
    alignItems: "flex-end",
  },

  statusBadge: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
  },

  presentText: {
    fontSize: 12,
    fontWeight: "700",
    color: THEME.colors.success,
  },
});