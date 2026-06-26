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

export default function ContactScreen() {
  const [contactInfo] = useState({
    phone: "+91 98765 43210",
    alternatePhone: "+91 91234 56789",
    workEmail: "john.doe@company.com",
    personalEmail: "john.doe@gmail.com",
    address: "Flat No. 302, Green Residency",
    city: "Hyderabad",
    state: "Telangana",
    country: "India",
    pincode: "500081",
    emergencyContact: "David Doe",
    emergencyRelation: "Father",
    emergencyPhone: "+91 99887 76655",
  });

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="Contact Information"
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
              name="call"
              size={32}
              color="#173B8C"
            />
          </View>

          <View style={styles.summaryContent}>
            <Text style={styles.summaryTitle}>
              Contact Details
            </Text>

            <Text style={styles.summarySubtitle}>
              Keep your information up to date
            </Text>

            <View style={styles.statusRow}>
              <View style={styles.statusDot} />

              <Text style={styles.statusText}>
                Verified
              </Text>
            </View>
          </View>

          <TouchableOpacity style={styles.editButton}>
            <Ionicons
              name="create-outline"
              size={18}
              color="#173B8C"
            />
          </TouchableOpacity>
        </View>

        {/* Contact Details */}

        <Text style={styles.sectionTitle}>
          Contact Details
        </Text>

        <DetailCard
          icon="call-outline"
          label="Mobile Number"
          value={contactInfo.phone}
        />

        <DetailCard
          icon="call-outline"
          label="Alternate Number"
          value={contactInfo.alternatePhone}
        />

        <DetailCard
          icon="mail-outline"
          label="Official Email"
          value={contactInfo.workEmail}
        />

        <DetailCard
          icon="mail-open-outline"
          label="Personal Email"
          value={contactInfo.personalEmail}
        />

        {/* Address */}

        <Text style={styles.sectionTitle}>
          Address
        </Text>

        <DetailCard
          icon="home-outline"
          label="Address"
          value={contactInfo.address}
        />

        <DetailCard
          icon="business-outline"
          label="City"
          value={contactInfo.city}
        />

        <DetailCard
          icon="map-outline"
          label="State"
          value={contactInfo.state}
        />

        <DetailCard
          icon="flag-outline"
          label="Country"
          value={contactInfo.country}
        />

        <DetailCard
          icon="location-outline"
          label="PIN Code"
          value={contactInfo.pincode}
        />

        {/* Emergency Contact */}

        <Text style={styles.sectionTitle}>
          Emergency Contact
        </Text>

        <DetailCard
          icon="person-outline"
          label="Contact Person"
          value={contactInfo.emergencyContact}
        />

        <DetailCard
          icon="people-outline"
          label="Relationship"
          value={contactInfo.emergencyRelation}
        />

        <DetailCard
          icon="call-outline"
          label="Emergency Number"
          value={contactInfo.emergencyPhone}
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

  summaryTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  summarySubtitle: {
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