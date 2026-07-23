import React from "react";
import {
  View,
  Text,
  SafeAreaView,
  ScrollView,
} from "react-native";

import ProfileHeader from "../../components/profile/ProfileHeader";

import HeaderCard from "../../components/earnings/HeaderCard";
import SummaryCard from "../../components/earnings/SummaryCard";
import BreakdownRow from "../../components/earnings/BreakdownRow";
import PayslipCard from "../../components/earnings/PayslipCard";
import StatChip from "../../components/earnings/StatChip";

import { StyleSheet } from "react-native";

export default function EarningsScreen() {
  const earnings = {
    month: "June",
    year: "2026",

    grossPay: 45000,

    incentives: 2500,

    overtime: 1000,

    total: 48500,

    fullDays: 22,

    halfDays: 1,

    lateDays: 2,

    absent: 0,

    dailyRate: 2000,
  };

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="Earnings"
        showBack={false}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        {/* Earnings Header */}

        <HeaderCard
          month={earnings.month}
          year={earnings.year}
          total={earnings.total}
          grossPay={earnings.grossPay}
          incentives={earnings.incentives}
          overtime={earnings.overtime}
        />

        {/* Status Chips */}

        <View style={styles.chipContainer}>
          <StatChip
            label="Salary Credited"
            color="#22C55E"
            background="#ECFDF5"
          />

          <StatChip
            label="Payslip Available"
            color="#2563EB"
            background="#EEF4FF"
          />

          <StatChip
            label="Estimated"
            color="#F59E0B"
            background="#FFF7ED"
          />
        </View>

        {/* Summary */}

        <Text style={styles.sectionTitle}>
          Salary Summary
        </Text>

        <SummaryCard
          icon="wallet-outline"
          title="Gross Pay"
          value={earnings.grossPay}
          color="#2563EB"
          background="#EEF4FF"
        />

        <SummaryCard
          icon="trophy-outline"
          title="Incentives"
          value={earnings.incentives}
          color="#F59E0B"
          background="#FFF7ED"
        />

        <SummaryCard
          icon="time-outline"
          title="Overtime"
          value={earnings.overtime}
          color="#22C55E"
          background="#ECFDF5"
        />

        {/* Attendance Breakdown */}

        <Text style={styles.sectionTitle}>
          Monthly Breakdown
        </Text>

        <View style={styles.breakdownCard}>
          <BreakdownRow
            icon="checkmark-circle-outline"
            label="Full Days"
            value={`${earnings.fullDays} Days`}
            color="#22C55E"
            background="#ECFDF5"
            valueColor="#16A34A"
          />

          <BreakdownRow
            icon="remove-circle-outline"
            label="Half Days"
            value={`${earnings.halfDays} Day`}
            color="#F59E0B"
            background="#FFF7ED"
            valueColor="#D97706"
          />

          <BreakdownRow
            icon="alarm-outline"
            label="Late Days"
            value={`${earnings.lateDays} Days`}
            color="#EA580C"
            background="#FFF7ED"
            valueColor="#EA580C"
          />

          <BreakdownRow
            icon="close-circle-outline"
            label="Absent"
            value={`${earnings.absent} Days`}
            color="#EF4444"
            background="#FEF2F2"
            valueColor="#DC2626"
          />

          <BreakdownRow
            icon="cash-outline"
            label="Daily Rate"
            value={`₹${earnings.dailyRate.toLocaleString()}`}
            color="#173B8C"
            background="#EEF4FF"
            valueColor="#173B8C"
          />
        </View>

        {/* Payslip */}

        <PayslipCard
          onViewPayslip={(month, year) => {
            console.log(
              "View Payslip:",
              month,
              year
            );
          }}
        />

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
    paddingHorizontal: 18,
    paddingBottom: 120,
  },

  chipContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginBottom: 22,
  },

  sectionTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
    marginBottom: 14,
    marginTop: 4,
    letterSpacing: -0.4,
  },

  breakdownCard: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    paddingHorizontal: 18,
    paddingVertical: 8,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,

    marginBottom: 22,
  },

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    padding: 18,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    marginBottom: 18,

    shadowColor: "#0F172A",
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },

  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
  },

  cardTitle: {
    marginLeft: 10,
    fontSize: 18,
    fontWeight: "800",
    color: "#0F172A",
  },

  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",

    paddingVertical: 10,

    borderBottomWidth: 1,
    borderBottomColor: "#EEF2F7",
  },

  rowLabel: {
    fontSize: 15,
    fontWeight: "600",
    color: "#475569",
  },

  rowValue: {
    fontSize: 16,
    fontWeight: "800",
    color: "#173B8C",
  },

  infoCard: {
    backgroundColor: "#EEF4FF",

    borderRadius: 18,

    padding: 16,

    marginTop: 20,
    marginBottom: 18,

    borderLeftWidth: 4,
    borderLeftColor: "#173B8C",
  },

  infoTitle: {
    fontSize: 16,
    fontWeight: "800",
    color: "#173B8C",
    marginBottom: 8,
  },

  infoText: {
    fontSize: 14,
    lineHeight: 22,
    color: "#475569",
    fontWeight: "500",
  },

  divider: {
    height: 1,
    backgroundColor: "#EEF2F7",
    marginVertical: 18,
  },

  footerCard: {
    backgroundColor: "#FFFFFF",

    borderRadius: 20,

    padding: 18,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    marginTop: 20,

    shadowColor: "#0F172A",
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },

  footerTitle: {
    fontSize: 17,
    fontWeight: "800",
    color: "#0F172A",
    marginBottom: 10,
  },

  footerText: {
    fontSize: 14,
    lineHeight: 22,
    color: "#64748B",
  },
});