import React, { useState } from "react";
import {
  View,
 Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
} from "react-native";

import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";

import ProfileHeader from "../../components/profile/ProfileHeader";
import ProfileImageCard from "../../components/profile/ProfileImageCard";
import ProfileCompletionCard from "../../components/profile/ProfileCompletionCard";
import ProfileMenuCard from "../../components/profile/ProfileMenuCard";

export default function ProfileScreen() {
  const navigation = useNavigation();

  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = () => {
    setRefreshing(true);

    setTimeout(() => {
      setRefreshing(false);
    }, 800);
  };

  const profile = {
    name: "John Doe",
    employeeId: "EMP001",
    designation: "Software Engineer",
    department: "Engineering",
    email: "john.doe@company.com",
    phone: "+91 9876543210",
    completion: 88,
  };

  const menuItems = [
    {
      title: "Personal Information",
      subtitle: "Name, DOB, Gender & Identity",
      icon: "person-outline",
      color: "#2563EB",
      background: "#EEF4FF",
      screen: "PersonalInfo",
    },

    {
      title: "Work Information",
      subtitle: "Designation & Department",
      icon: "briefcase-outline",
      color: "#7C3AED",
      background: "#F5F3FF",
      screen: "WorkInfo",
    },

    {
      title: "Contact Details",
      subtitle: "Email, Phone & Address",
      icon: "call-outline",
      color: "#059669",
      background: "#ECFDF5",
      screen: "Contact",
    },

    {
      title: "Emergency Contact",
      subtitle: "Family Contact Details",
      icon: "people-outline",
      color: "#EA580C",
      background: "#FFF7ED",
      screen: "EmergencyContact",
    },

    {
      title: "Education",
      subtitle: "Academic Qualifications",
      icon: "school-outline",
      color: "#DC2626",
      background: "#FEF2F2",
      screen: "Education",
    },

    {
      title: "Experience",
      subtitle: "Previous Employment",
      icon: "layers-outline",
      color: "#0891B2",
      background: "#ECFEFF",
      screen: "Experience",
    },

    {
      title: "Documents",
      subtitle: "Certificates & Proofs",
      icon: "document-text-outline",
      color: "#4F46E5",
      background: "#EEF2FF",
      screen: "Documents",
    },

    {
      title: "Bank Details",
      subtitle: "Salary Account Information",
      icon: "card-outline",
      color: "#16A34A",
      background: "#F0FDF4",
      screen: "BankDetails",
    },

    {
      title: "Security",
      subtitle: "Password & Login",
      icon: "shield-checkmark-outline",
      color: "#E11D48",
      background: "#FFF1F2",
      screen: "Security",
    },

    {
      title: "Settings",
      subtitle: "Preferences & Notifications",
      icon: "settings-outline",
      color: "#64748B",
      background: "#F8FAFC",
      screen: "Settings",
    },
  ];

  return (
    <LinearGradient
      colors={[
        "#F8FAFC",
        "#F6F9FE",
        "#EEF4FF",
      ]}
      style={styles.container}
    >
      <ProfileHeader
  title="My Profile"
  showBack={false}
/>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={["#173B8C"]}
          />
        }
      >
        <ProfileImageCard
          employeeName={profile.name}
          employeeId={profile.employeeId}
          designation={profile.designation}
          department={profile.department}
        />

        <ProfileCompletionCard
          percentage={profile.completion}
        />

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            Employee Details
          </Text>

          <View style={styles.quickCard}>
            <View style={styles.quickRow}>
              <Ionicons
                name="mail-outline"
                size={18}
                color="#173B8C"
              />

              <Text style={styles.quickText}>
                {profile.email}
              </Text>
            </View>

            <View style={styles.divider} />

            <View style={styles.quickRow}>
              <Ionicons
                name="call-outline"
                size={18}
                color="#173B8C"
              />

              <Text style={styles.quickText}>
                {profile.phone}
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            Profile Sections
          </Text>

          {menuItems.map((item) => (
            <ProfileMenuCard
              key={item.title}
              title={item.title}
              subtitle={item.subtitle}
              icon={item.icon}
              color={item.color}
              background={item.background}
              onPress={() => {
  navigation.push(item.screen);
}}
            />
          ))}
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },

  content: {
    paddingHorizontal: 18,
    paddingTop: 6,
    paddingBottom: 120,
  },

  section: {
    marginTop: 18,
  },

  sectionTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#0F172A",
    marginBottom: 14,
    letterSpacing: -0.3,
  },

  quickCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 20,
    padding: 18,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },
    quickRow: {
    flexDirection: "row",
    alignItems: "center",
  },

  quickText: {
    marginLeft: 12,

    flex: 1,

    fontSize: 15,

    fontWeight: "600",

    color: "#334155",
  },

  divider: {
    height: 1,

    backgroundColor: "#EEF2F7",

    marginVertical: 16,
  },
});
