import React, { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";
import SaveButton from "../../components/profile/SaveButton.js";
import ProfileHeader from "../../components/profile/ProfileHeader";
import DetailCard from "../../components/profile/DetailCard";


export default function BankDetailsScreen() {
  const [bankDetails] = useState({
    accountHolder: "John Doe",
    bankName: "State Bank of India",
    accountNumber: "XXXX XXXX 4589",
    ifscCode: "SBIN0001234",
    branchName: "Madhapur Branch",
    accountType: "Savings",
    upiId: "john@sbi",
    salaryAccount: "Yes",
  });

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="Bank Details"
        showBack
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        {/* Summary Card */}

        <View style={styles.summaryCard}>
          <View style={styles.avatar}>
            <Ionicons
              name="card"
              size={32}
              color="#173B8C"
            />
          </View>

          <View style={styles.summaryContent}>
            <Text style={styles.employeeName}>
              Banking Information
            </Text>

            <Text style={styles.employeeId}>
              Salary Account Details
            </Text>

            <View style={styles.statusRow}>
              <View style={styles.statusDot} />

              <Text style={styles.statusText}>
                Verified
              </Text>
            </View>
          </View>

          <TouchableOpacity
            style={styles.editButton}
            activeOpacity={0.85}
          >
            <Ionicons
              name="create-outline"
              size={18}
              color="#173B8C"
            />
          </TouchableOpacity>
        </View>

        {/* Bank Information */}

        <Text style={styles.sectionTitle}>
          Account Information
        </Text>

        <DetailCard
          icon="person-outline"
          label="Account Holder Name"
          value={bankDetails.accountHolder}
        />

        <DetailCard
          icon="business-outline"
          label="Bank Name"
          value={bankDetails.bankName}
        />

        <DetailCard
          icon="card-outline"
          label="Account Number"
          value={bankDetails.accountNumber}
        />

        <DetailCard
          icon="code-slash-outline"
          label="IFSC Code"
          value={bankDetails.ifscCode}
        />

        <DetailCard
          icon="location-outline"
          label="Branch Name"
          value={bankDetails.branchName}
        />

        <DetailCard
          icon="wallet-outline"
          label="Account Type"
          value={bankDetails.accountType}
        />

        <DetailCard
          icon="phone-portrait-outline"
          label="UPI ID"
          value={bankDetails.upiId}
        />

        <DetailCard
          icon="cash-outline"
          label="Salary Account"
          value={bankDetails.salaryAccount}
        />

        <SaveButton
          title="Save Changes"
          onPress={() => {}}
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

  summaryCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 18,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#E8EDF3",
    marginBottom: 24,

    shadowColor: "#0F172A",
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },

  avatar: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: "#EEF4FF",
    justifyContent: "center",
    alignItems: "center",
  },

  summaryContent: {
    flex: 1,
    marginLeft: 16,
  },

  employeeName: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  employeeId: {
    marginTop: 4,
    fontSize: 13,
    color: "#64748B",
    fontWeight: "600",
  },

  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 10,
  },

  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#22C55E",
    marginRight: 8,
  },

  statusText: {
    fontSize: 13,
    fontWeight: "600",
    color: "#16A34A",
  },

  editButton: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: "#F8FAFC",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#E2E8F0",
  },

  sectionTitle: {
    marginBottom: 14,
    marginTop: 6,
    fontSize: 18,
    fontWeight: "800",
    color: "#0F172A",
    letterSpacing: -0.3,
  },
});