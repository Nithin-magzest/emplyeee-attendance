import React, { useState } from "react";

import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import AdminHeader from "../../components/admin/AdminHeader";
import THEME from "../../constants/theme";

export default function AnalyticsScreen() {
  const [selectedPeriod, setSelectedPeriod] =
    useState("Month");

  const overview = {
    attendance: 94.8,
    present: 241,
    absent: 13,
    employees: 254,
    late: 9,
    leave: 11,
  };

  const attendanceTrend = [
    { label: "Jan", value: 88 },
    { label: "Feb", value: 90 },
    { label: "Mar", value: 91 },
    { label: "Apr", value: 92 },
    { label: "May", value: 94 },
    { label: "Jun", value: 95 },
    { label: "Jul", value: 94 },
  ];

  const departments = [
    {
      name: "Engineering",
      attendance: 97,
      employees: 82,
      color: "#16A34A",
    },
    {
      name: "Sales",
      attendance: 91,
      employees: 61,
      color: "#2563EB",
    },
    {
      name: "Support",
      attendance: 89,
      employees: 48,
      color: "#F59E0B",
    },
    {
      name: "Finance",
      attendance: 93,
      employees: 25,
      color: "#7C3AED",
    },
    {
      name: "HR",
      attendance: 96,
      employees: 18,
      color: "#EC4899",
    },
  ];

  const performers = [
    {
      name: "Emma Wilson",
      department: "Engineering",
      attendance: "100%",
    },
    {
      name: "John David",
      department: "Sales",
      attendance: "99%",
    },
    {
      name: "Sophia Lee",
      department: "Finance",
      attendance: "98%",
    },
  ];

  const alerts = [
    {
      title: "5 Leave Requests Pending",
      subtitle: "Requires HR approval",
      icon: "document-text-outline",
      color: "#2563EB",
    },
    {
      title: "2 Employees Absent 3 Days",
      subtitle: "Immediate attention required",
      icon: "warning-outline",
      color: "#DC2626",
    },
    {
      title: "Attendance Improved",
      subtitle: "6% better than last month",
      icon: "trending-up-outline",
      color: "#16A34A",
    },
  ];

  const KPI = ({
    icon,
    title,
    value,
    color,
    subtitle,
  }) => (
    <View style={styles.kpiCard}>

      <View
        style={[
          styles.kpiIcon,
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

      <Text style={styles.kpiValue}>
        {value}
      </Text>

      <Text style={styles.kpiTitle}>
        {title}
      </Text>

      <Text style={styles.kpiSubtitle}>
        {subtitle}
      </Text>

    </View>
  );

  const AlertItem = ({ item }) => (
    <View style={styles.alertItem}>

      <View
        style={[
          styles.alertIcon,
          {
            backgroundColor: item.color + "15",
          },
        ]}
      >
        <Ionicons
          name={item.icon}
          size={20}
          color={item.color}
        />
      </View>

      <View style={{ flex: 1 }}>

        <Text style={styles.alertTitle}>
          {item.title}
        </Text>

        <Text style={styles.alertSubtitle}>
          {item.subtitle}
        </Text>

      </View>

    </View>
  );

  return (
    <SafeAreaView style={styles.container}>

      <AdminHeader title="Analytics" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >

        <View style={styles.header}>

          <View>

            <Text style={styles.heading}>
              Workforce Overview
            </Text>

            <Text style={styles.subHeading}>
              Attendance insights and workforce performance
            </Text>

          </View>

          <TouchableOpacity
            style={styles.reportButton}
          >

            <Ionicons
              name="download-outline"
              size={18}
              color="#FFFFFF"
            />

            <Text style={styles.reportText}>
              Report
            </Text>

          </TouchableOpacity>

        </View>

        <View style={styles.summaryCard}>

          <View style={styles.summaryTop}>

            <Text style={styles.summaryTitle}>
              Overall Attendance
            </Text>

            <View style={styles.summaryBadge}>

              <Ionicons
                name="trending-up"
                size={14}
                color="#16A34A"
              />

              <Text style={styles.summaryBadgeText}>
                +6%
              </Text>

            </View>

          </View>

          <Text style={styles.summaryValue}>
            {overview.attendance}%
          </Text>

          <Text style={styles.summarySubtitle}>
            Excellent workforce engagement this month
          </Text>

        </View>

        <View style={styles.kpiGrid}>

          <KPI
            icon="people-outline"
            title="Employees"
            value={overview.employees}
            subtitle="Total workforce"
            color="#2563EB"
          />

          <KPI
            icon="checkmark-circle-outline"
            title="Present"
            value={overview.present}
            subtitle="Today"
            color="#16A34A"
          />

          <KPI
            icon="close-circle-outline"
            title="Absent"
            value={overview.absent}
            subtitle="Today"
            color="#DC2626"
          />

          <KPI
            icon="time-outline"
            title="Late"
            value={overview.late}
            subtitle="Checked in late"
            color="#F59E0B"
          />

        </View>

        <View style={styles.section}>

          <Text style={styles.sectionTitle}>
            Time Period
          </Text>

          <View style={styles.filterRow}>

            {["Week", "Month", "Year"].map(
              (item) => (
                <TouchableOpacity
                  key={item}
                  onPress={() =>
                    setSelectedPeriod(item)
                  }
                  style={[
                    styles.filterButton,
                    selectedPeriod === item &&
                      styles.filterButtonActive,
                  ]}
                >

                  <Text
                    style={[
                      styles.filterText,
                      selectedPeriod === item &&
                        styles.filterTextActive,
                    ]}
                  >
                    {item}
                  </Text>

                </TouchableOpacity>
              )
            )}

          </View>

        </View>

        <View style={styles.section}>

          <View style={styles.sectionHeader}>

            <Text style={styles.sectionTitle}>
              Attendance Trend
            </Text>

            <Text style={styles.sectionSmall}>
              Last 7 Months
            </Text>

          </View>

          <View style={styles.chartContainer}>

            {attendanceTrend.map(
              (item, index) => (
                <View
                  key={index}
                  style={styles.chartColumn}
                >

                  <View
                    style={styles.chartBackground}
                  >

                    <View
                      style={[
                        styles.chartBar,
                        {
                          height:
                            item.value * 1.2,
                        },
                      ]}
                    />

                  </View>

                  <Text style={styles.chartLabel}>
                    {item.label}
                  </Text>

                </View>
              )
            )}

          </View>

        </View>

        {/* Continue from here in Part 2 */}
                {/* Department Performance */}

        <View style={styles.section}>

          <View style={styles.sectionHeader}>

            <Text style={styles.sectionTitle}>
              Department Performance
            </Text>

            <Text style={styles.sectionSmall}>
              Attendance %
            </Text>

          </View>

          {departments.map((item, index) => (

            <View
              key={index}
              style={styles.departmentCard}
            >

              <View style={styles.departmentHeader}>

                <View>

                  <Text style={styles.departmentName}>
                    {item.name}
                  </Text>

                  <Text style={styles.departmentEmployees}>
                    {item.employees} Employees
                  </Text>

                </View>

                <Text
                  style={[
                    styles.departmentPercent,
                    {
                      color: item.color,
                    },
                  ]}
                >
                  {item.attendance}%
                </Text>

              </View>

              <View style={styles.progressTrack}>

                <View
                  style={[
                    styles.progressFill,
                    {
                      width: `${item.attendance}%`,
                      backgroundColor: item.color,
                    },
                  ]}
                />

              </View>

            </View>

          ))}

        </View>

        {/* Attendance Distribution */}

        <View style={styles.section}>

          <Text style={styles.sectionTitle}>
            Attendance Distribution
          </Text>

          <View style={styles.distributionRow}>

            <View style={styles.distributionCard}>

              <View
                style={[
                  styles.distributionIcon,
                  {
                    backgroundColor: "#DCFCE7",
                  },
                ]}
              >

                <Ionicons
                  name="checkmark-circle"
                  size={22}
                  color="#16A34A"
                />

              </View>

              <Text style={styles.distributionValue}>
                {overview.present}
              </Text>

              <Text style={styles.distributionLabel}>
                Present
              </Text>

            </View>

            <View style={styles.distributionCard}>

              <View
                style={[
                  styles.distributionIcon,
                  {
                    backgroundColor: "#FEE2E2",
                  },
                ]}
              >

                <Ionicons
                  name="close-circle"
                  size={22}
                  color="#DC2626"
                />

              </View>

              <Text style={styles.distributionValue}>
                {overview.absent}
              </Text>

              <Text style={styles.distributionLabel}>
                Absent
              </Text>

            </View>

            <View style={styles.distributionCard}>

              <View
                style={[
                  styles.distributionIcon,
                  {
                    backgroundColor: "#FEF3C7",
                  },
                ]}
              >

                <Ionicons
                  name="calendar-outline"
                  size={22}
                  color="#F59E0B"
                />

              </View>

              <Text style={styles.distributionValue}>
                {overview.leave}
              </Text>

              <Text style={styles.distributionLabel}>
                Leave
              </Text>

            </View>

          </View>

        </View>

        {/* Top Performers */}

        <View style={styles.section}>

          <View style={styles.sectionHeader}>

            <Text style={styles.sectionTitle}>
              Top Performers
            </Text>

            <TouchableOpacity>

              <Text style={styles.viewAll}>
                View All
              </Text>

            </TouchableOpacity>

          </View>

          {performers.map((item, index) => (

            <View
              key={index}
              style={styles.employeeCard}
            >

              <View style={styles.avatar}>

                <Text style={styles.avatarText}>
                  {item.name.charAt(0)}
                </Text>

              </View>

              <View style={{ flex: 1 }}>

                <Text style={styles.employeeName}>
                  {item.name}
                </Text>

                <Text style={styles.employeeDepartment}>
                  {item.department}
                </Text>

              </View>

              <View
                style={styles.employeeScore}
              >

                <Ionicons
                  name="trophy"
                  size={18}
                  color="#F59E0B"
                />

                <Text style={styles.scoreText}>
                  {item.attendance}
                </Text>

              </View>

            </View>

          ))}

        </View>

        {/* Smart Alerts */}

        <View style={styles.section}>

          <View style={styles.sectionHeader}>

            <Text style={styles.sectionTitle}>
              Smart Alerts
            </Text>

            <View style={styles.alertBadge}>

              <Text style={styles.alertBadgeText}>
                {alerts.length}
              </Text>

            </View>

          </View>

          {alerts.map((item, index) => (

            <AlertItem
              key={index}
              item={item}
            />

          ))}

        </View>

        {/* Attendance Insights */}

        <View style={styles.section}>

          <Text style={styles.sectionTitle}>
            Attendance Insights
          </Text>

          <View style={styles.insightCard}>

            <Ionicons
              name="trending-up-outline"
              size={26}
              color="#16A34A"
            />

            <View
              style={{
                flex: 1,
                marginLeft: 14,
              }}
            >

              <Text style={styles.insightTitle}>
                Attendance Increased
              </Text>

              <Text style={styles.insightDescription}>
                Overall attendance has
                improved by 6% compared
                to the previous month,
                with Engineering and HR
                showing the highest
                consistency.
              </Text>

            </View>

          </View>

          <View style={styles.insightCard}>

            <Ionicons
              name="time-outline"
              size={26}
              color="#2563EB"
            />

            <View
              style={{
                flex: 1,
                marginLeft: 14,
              }}
            >

              <Text style={styles.insightTitle}>
                Average Working Hours
              </Text>

              <Text style={styles.insightDescription}>
                Employees worked an
                average of 8.4 hours
                daily during the selected
                reporting period.
              </Text>

            </View>

          </View>

        </View>

        <View style={{ height: 40 }} />

      </ScrollView>

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
      container: {
    flex: 1,
    backgroundColor: "#F8FAFC",
  },

  content: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },

  header: {
    marginTop: 12,
    marginBottom: 24,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  heading: {
    fontSize: 28,
    fontWeight: "800",
    color: "#0F172A",
  },

  subHeading: {
    marginTop: 6,
    fontSize: 14,
    color: "#64748B",
    lineHeight: 22,
  },

  reportButton: {
    height: 44,
    paddingHorizontal: 18,
    borderRadius: 14,
    backgroundColor: "#2563EB",

    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",

    elevation: 2,
  },

  reportText: {
    marginLeft: 8,
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 14,
  },

  summaryCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 18,
    padding: 22,
    marginBottom: 22,
    borderWidth: 1,
    borderColor: "#E2E8F0",

    elevation: 2,
  },

  summaryTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  summaryTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#64748B",
  },

  summaryBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#DCFCE7",
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
  },

  summaryBadgeText: {
    marginLeft: 4,
    color: "#16A34A",
    fontWeight: "700",
    fontSize: 13,
  },

  summaryValue: {
    marginTop: 18,
    fontSize: 42,
    fontWeight: "800",
    color: "#111827",
  },

  summarySubtitle: {
    marginTop: 8,
    fontSize: 14,
    color: "#64748B",
    lineHeight: 22,
  },

  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginBottom: 22,
  },

  kpiCard: {
    width: "48%",
    backgroundColor: "#FFFFFF",
    borderRadius: 18,
    padding: 18,
    marginBottom: 16,

    borderWidth: 1,
    borderColor: "#E5E7EB",

    elevation: 1,
  },

  kpiIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    justifyContent: "center",
    alignItems: "center",
  },

  kpiValue: {
    marginTop: 16,
    fontSize: 28,
    fontWeight: "800",
    color: "#111827",
  },

  kpiTitle: {
    marginTop: 6,
    fontSize: 14,
    fontWeight: "700",
    color: "#1E293B",
  },

  kpiSubtitle: {
    marginTop: 4,
    fontSize: 12,
    color: "#94A3B8",
  },

  section: {
    backgroundColor: "#FFFFFF",
    borderRadius: 18,
    padding: 20,
    marginBottom: 22,

    borderWidth: 1,
    borderColor: "#E5E7EB",

    elevation: 1,
  },

  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 18,
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#0F172A",
  },

  sectionSmall: {
    fontSize: 13,
    color: "#64748B",
    fontWeight: "600",
  },

  filterRow: {
    flexDirection: "row",
    marginTop: 16,
  },

  filterButton: {
    flex: 1,
    height: 42,
    borderRadius: 12,
    backgroundColor: "#F1F5F9",
    justifyContent: "center",
    alignItems: "center",
    marginHorizontal: 4,
  },

  filterButtonActive: {
    backgroundColor: "#2563EB",
  },

  filterText: {
    fontSize: 14,
    fontWeight: "700",
    color: "#2563EB",
  },

  filterTextActive: {
    color: "#FFFFFF",
  },

  chartContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    marginTop: 20,
    height: 180,
  },

  chartColumn: {
    flex: 1,
    alignItems: "center",
  },

  chartBackground: {
    height: 145,
    justifyContent: "flex-end",
  },

  chartBar: {
    width: 20,
    backgroundColor: "#2563EB",
    borderRadius: 12,
  },

  chartLabel: {
    marginTop: 10,
    fontSize: 12,
    fontWeight: "600",
    color: "#64748B",
  },

  departmentCard: {
    marginBottom: 18,
  },

  departmentHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },

  departmentName: {
    fontSize: 15,
    fontWeight: "700",
    color: "#111827",
  },

  departmentEmployees: {
    marginTop: 3,
    fontSize: 12,
    color: "#94A3B8",
  },

  departmentPercent: {
    fontSize: 17,
    fontWeight: "800",
  },

  progressTrack: {
    height: 8,
    width: "100%",
    backgroundColor: "#E5E7EB",
    borderRadius: 8,
    overflow: "hidden",
  },

  progressFill: {
    height: "100%",
    borderRadius: 8,
  },
    distributionRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 18,
  },

  distributionCard: {
    width: "31%",
    backgroundColor: "#F8FAFC",
    borderRadius: 16,
    paddingVertical: 18,
    paddingHorizontal: 10,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },

  distributionIcon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
  },

  distributionValue: {
    fontSize: 24,
    fontWeight: "800",
    color: "#111827",
  },

  distributionLabel: {
    marginTop: 6,
    fontSize: 13,
    fontWeight: "600",
    color: "#64748B",
  },

  employeeCard: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#EEF2F7",
  },

  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: "#DBEAFE",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
  },

  avatarText: {
    fontSize: 18,
    fontWeight: "800",
    color: "#2563EB",
  },

  employeeName: {
    fontSize: 15,
    fontWeight: "700",
    color: "#111827",
  },

  employeeDepartment: {
    marginTop: 4,
    fontSize: 13,
    color: "#64748B",
  },

  employeeScore: {
    flexDirection: "row",
    alignItems: "center",
  },

  scoreText: {
    marginLeft: 6,
    fontSize: 16,
    fontWeight: "800",
    color: "#16A34A",
  },

  alertBadge: {
    minWidth: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: "#2563EB",
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 8,
  },

  alertBadgeText: {
    color: "#FFFFFF",
    fontSize: 12,
    fontWeight: "700",
  },

  alertItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#EEF2F7",
  },

  alertIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
  },

  alertTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#111827",
  },

  alertSubtitle: {
    marginTop: 4,
    fontSize: 13,
    color: "#64748B",
  },

  insightCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    backgroundColor: "#F8FAFC",
    borderRadius: 16,
    padding: 16,
    marginTop: 14,
    borderWidth: 1,
    borderColor: "#EEF2F7",
  },

  insightTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 6,
  },

  insightDescription: {
    fontSize: 13,
    lineHeight: 20,
    color: "#64748B",
  },

  viewAll: {
    fontSize: 14,
    fontWeight: "700",
    color: "#2563EB",
  },

  shadow: {
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: {
      width: 0,
      height: 2,
    },
    elevation: 2,
  },
});