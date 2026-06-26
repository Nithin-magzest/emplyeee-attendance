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

import ProfileHeader from "../../components/profile/ProfileHeader";
import DetailCard from "../../components/profile/DetailCard";
import SaveButton from "../../components/profile/SaveButton";

export default function EmergencyContactScreen() {
  const [emergencyContact] = useState({
    primaryName: "David Doe",
    primaryRelation: "Father",
    primaryPhone: "+91 98765 43210",
    primaryEmail: "david@example.com",

    secondaryName: "Mary Doe",
    secondaryRelation: "Mother",
    secondaryPhone: "+91 91234 56789",
    secondaryEmail: "mary@example.com",

    address: "Flat No. 302, Green Residency, Hyderabad, Telangana",
  });

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="Emergency Contact"
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
              name="medical"
              size={32}
              color="#173B8C"
            />
          </View>

          <View style={styles.summaryContent}>
            <Text style={styles.employeeName}>
              Emergency Contacts
            </Text>

            <Text style={styles.employeeId}>
              Keep these details updated
            </Text>

            <View style={styles.statusRow}>
              <View style={styles.statusDot} />

              <Text style={styles.statusText}>
                Information Verified
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

        {/* Primary Contact */}

        <Text style={styles.sectionTitle}>
          Primary Emergency Contact
        </Text>

        <DetailCard
          icon="person-outline"
          label="Contact Name"
          value={emergencyContact.primaryName}
        />

        <DetailCard
          icon="people-outline"
          label="Relationship"
          value={emergencyContact.primaryRelation}
        />

        <DetailCard
          icon="call-outline"
          label="Phone Number"
          value={emergencyContact.primaryPhone}
        />

        <DetailCard
          icon="mail-outline"
          label="Email Address"
          value={emergencyContact.primaryEmail}
        />

        {/* Secondary Contact */}

        <Text style={styles.sectionTitle}>
          Secondary Emergency Contact
        </Text>

        <DetailCard
          icon="person-outline"
          label="Contact Name"
          value={emergencyContact.secondaryName}
        />

        <DetailCard
          icon="people-outline"
          label="Relationship"
          value={emergencyContact.secondaryRelation}
        />

        <DetailCard
          icon="call-outline"
          label="Phone Number"
          value={emergencyContact.secondaryPhone}
        />

        <DetailCard
          icon="mail-outline"
          label="Email Address"
          value={emergencyContact.secondaryEmail}
        />

        {/* Address */}

        <Text style={styles.sectionTitle}>
          Emergency Address
        </Text>

        <DetailCard
          icon="location-outline"
          label="Address"
          value={emergencyContact.address}
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