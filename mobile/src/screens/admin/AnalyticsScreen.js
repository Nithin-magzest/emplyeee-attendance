import React, { useState } from "react";

import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
  Text,
} from "react-native";

import AdminHeader from "../../components/admin/AdminHeader";
import AdminSearchBar from "../../components/admin/AdminSearchBar";
import DashboardStatCard from "../../components/admin/DashboardStatCard";

import THEME from "../../constants/theme";

export default function AnalyticsScreen() {
  const [search, setSearch] = useState("");

  return (
    <SafeAreaView style={styles.container}>
      <AdminHeader title="Analytics" />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <AdminSearchBar
          value={search}
          onChangeText={setSearch}
          placeholder="Search analytics..."
        />

        {/* KPI Cards */}

        <View style={styles.grid}>
          <DashboardStatCard
            title="Attendance"
            value="92%"
            subtitle="Overall Attendance"
            icon="bar-chart-outline"
            iconColor={THEME.colors.success}
            iconBackground={THEME.colors.greenBg}
            trend="+4%"
          />

          <DashboardStatCard
            title="Productivity"
            value="88%"
            subtitle="Monthly Average"
            icon="trending-up-outline"
            iconColor={THEME.colors.primary}
            iconBackground={THEME.colors.blueBg}
            trend="+6%"
          />

          <DashboardStatCard
            title="Retention"
            value="96%"
            subtitle="Employee Retention"
            icon="people-outline"
            iconColor={THEME.colors.payroll}
            iconBackground={THEME.colors.purpleBg}
          />

          <DashboardStatCard
            title="Leaves"
            value="34"
            subtitle="Approved This Month"
            icon="document-text-outline"
            iconColor={THEME.colors.warning}
            iconBackground={THEME.colors.yellowBg}
          />
        </View>

        {/* Department Performance */}
                <View style={styles.analyticsCard}>
          <Text style={styles.cardTitle}>
            Department Performance
          </Text>

          <View style={styles.metricRow}>
            <Text style={styles.metricLabel}>
              Engineering
            </Text>

            <Text style={styles.metricValue}>
              95%
            </Text>
          </View>

          <View style={styles.progressBackground}>
            <View
              style={[
                styles.progressFill,
                {
                  width: "95%",
                  backgroundColor:
                    THEME.colors.success,
                },
              ]}
            />
          </View>

          <View style={styles.metricRow}>
            <Text style={styles.metricLabel}>
              HR
            </Text>

            <Text style={styles.metricValue}>
              88%
            </Text>
          </View>

          <View style={styles.progressBackground}>
            <View
              style={[
                styles.progressFill,
                {
                  width: "88%",
                  backgroundColor:
                    THEME.colors.primary,
                },
              ]}
            />
          </View>

          <View style={styles.metricRow}>
            <Text style={styles.metricLabel}>
              Finance
            </Text>

            <Text style={styles.metricValue}>
              91%
            </Text>
          </View>

          <View style={styles.progressBackground}>
            <View
              style={[
                styles.progressFill,
                {
                  width: "91%",
                  backgroundColor:
                    THEME.colors.payroll,
                },
              ]}
            />
          </View>

          <View style={styles.metricRow}>
            <Text style={styles.metricLabel}>
              Sales
            </Text>

            <Text style={styles.metricValue}>
              82%
            </Text>
          </View>

          <View style={styles.progressBackground}>
            <View
              style={[
                styles.progressFill,
                {
                  width: "82%",
                  backgroundColor:
                    THEME.colors.warning,
                },
              ]}
            />
          </View>
        </View>

        <View style={styles.analyticsCard}>
          <Text style={styles.cardTitle}>
            Monthly Summary
          </Text>

          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>
              New Employees
            </Text>

            <Text style={styles.summaryValue}>
              14
            </Text>
          </View>

          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>
              Resignations
            </Text>

            <Text style={styles.summaryValue}>
              2
            </Text>
          </View>

          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>
              Leave Requests
            </Text>

            <Text style={styles.summaryValue}>
              34
            </Text>
          </View>

          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>
              Payroll Processed
            </Text>

            <Text style={styles.summaryValue}>
              ₹8.2L
            </Text>
          </View>
        </View>
        