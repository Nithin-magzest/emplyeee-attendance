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
import { useNavigation } from "@react-navigation/native";

import ProfileHeader from "../../components/profile/ProfileHeader";
import DetailCard from "../../components/profile/DetailCard";
import SaveButton from "../../components/profile/SaveButton";

export default function WorkInfoScreen() {
  const navigation = useNavigation();

  const [workInfo, setWorkInfo] = useState({
    employeeId: "EMP001",
    employeeName: "John Doe",
    designation: "Software Engineer",
    department: "Engineering",
    employmentType: "Full Time",
    joiningDate: "15 Jan 2024",
    reportingManager: "Michael Johnson",
    employeeStatus: "Active",
    workLocation: "Hyderabad",
    workMode: "Hybrid",
    shift: "General Shift",
    officeEmail: "john.doe@company.com",
    officePhone: "+91 9876543210",
  });

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="Work Information"
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
              name="briefcase"
              size={32}
              color="#173B8C"
            />
          </View>

          <View style={styles.summaryContent}>
            <Text style={styles.employeeName}>
              {workInfo.employeeName}
            </Text>

            <Text style={styles.employeeId}>
              {workInfo.employeeId}
            </Text>

            <View style={styles.statusRow}>
              <View style={styles.statusDot} />

              <Text style={styles.statusText}>
                {workInfo.employeeStatus}
              </Text>
            </View>
          </View>

          <TouchableOpacity
            activeOpacity={0.85}
            style={styles.editButton}
          >
            <Ionicons
              name="create-outline"
              size={18}
              color="#173B8C"
            />
          </TouchableOpacity>
        </View>

        {/* Employment Information */}

        <Text style={styles.sectionTitle}>
          Employment Details
        </Text>

        <DetailCard
          icon="briefcase-outline"
          label="Designation"
          value={workInfo.designation}
        />

        <DetailCard
          icon="business-outline"
          label="Department"
          value={workInfo.department}
        />

        <DetailCard
          icon="people-outline"
          label="Employment Type"
          value={workInfo.employmentType}
        />

        <DetailCard
          icon="calendar-outline"
          label="Joining Date"
          value={workInfo.joiningDate}
        />

        <DetailCard
          icon="person-circle-outline"
          label="Reporting Manager"
          value={workInfo.reportingManager}
        />

        <DetailCard
          icon="checkmark-circle-outline"
          label="Employee Status"
          value={workInfo.employeeStatus}
        />

        <DetailCard
          icon="location-outline"
          label="Work Location"
          value={workInfo.workLocation}
        />

        <DetailCard
          icon="laptop-outline"
          label="Work Mode"
          value={workInfo.workMode}
        />

        <DetailCard
          icon="time-outline"
          label="Shift"
          value={workInfo.shift}
        />

        <DetailCard
          icon="mail-outline"
          label="Official Email"
          value={workInfo.officeEmail}
        />

        <DetailCard
          icon="call-outline"
          label="Office Phone"
          value={workInfo.officePhone}
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

    fontSize: 18,

    fontWeight: "800",

    color: "#0F172A",

    letterSpacing: -0.3,
  },
});