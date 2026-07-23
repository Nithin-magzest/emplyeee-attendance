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

export default function PersonalInfoScreen() {
  const navigation = useNavigation();

  const [profile, setProfile] = useState({
    employeeId: "EMP001",
    firstName: "John",
    lastName: "Doe",
    gender: "Male",
    dob: "15 Mar 2001",
    bloodGroup: "O+",
    maritalStatus: "Single",
    nationality: "Indian",
    religion: "Hindu",
    fatherName: "David Doe",
    motherName: "Mary Doe",
  });

  return (
    <SafeAreaView style={styles.container}>

      <ProfileHeader
  title="Personal Information"
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
              name="person"
              size={34}
              color="#173B8C"
            />

          </View>

          <View style={styles.summaryContent}>

            <Text style={styles.employeeName}>
              {profile.firstName} {profile.lastName}
            </Text>

            <Text style={styles.employeeId}>
              {profile.employeeId}
            </Text>

            <View style={styles.statusRow}>

              <View style={styles.statusDot} />

              <Text style={styles.statusText}>
                Active Employee
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

        {/* Section */}

        <Text style={styles.sectionTitle}>
          Personal Details
        </Text>

        <DetailCard
          icon="person-outline"
          label="First Name"
          value={profile.firstName}
        />

        <DetailCard
          icon="person-outline"
          label="Last Name"
          value={profile.lastName}
        />

        <DetailCard
          icon="male-female-outline"
          label="Gender"
          value={profile.gender}
        />

        <DetailCard
          icon="calendar-outline"
          label="Date of Birth"
          value={profile.dob}
        />

        <DetailCard
          icon="water-outline"
          label="Blood Group"
          value={profile.bloodGroup}
        />

        <DetailCard
          icon="heart-outline"
          label="Marital Status"
          value={profile.maritalStatus}
        />

        <DetailCard
          icon="flag-outline"
          label="Nationality"
          value={profile.nationality}
        />

        <DetailCard
          icon="people-outline"
          label="Father Name"
          value={profile.fatherName}
        />

        <DetailCard
          icon="people-outline"
          label="Mother Name"
          value={profile.motherName}
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