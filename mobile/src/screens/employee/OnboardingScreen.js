import React from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";

import ProfileHeader from "../../components/profile/ProfileHeader";

import OnboardingStatusCard from "../../components/onboarding/OnboardingStatusCard";
import ProgressCard from "../../components/onboarding/ProgressCard";
import CompanyInfoCard from "../../components/onboarding/CompanyInfoCard";
import HRContactCard from "../../components/onboarding/HRContactCard";
import TimelineCard from "../../components/onboarding/TimelineCard";
import ChecklistCard from "../../components/onboarding/ChecklistCard";
import NextActionCard from "../../components/onboarding/NextActionCard";

export default function OnboardingScreen() {
  const onboarding = {
    employeeName: "John Doe",
    employeeId: "EMP001",

    status: "In Progress",
    progress: 72,

    department: "Engineering",
    designation: "Software Engineer",

    manager: "Rakesh Sharma",

    officeLocation: "Hyderabad",

    joiningDate: "15 June 2026",

    workMode: "Hybrid",

    employmentType: "Full Time",

    shift: "General Shift",

    hr: {
      name: "Priya Sharma",

      designation: "HR Executive",

      email: "hr@company.com",

      phone: "+91 9876543210",
    },
  };

  const timeline = [
    {
      title: "Offer Accepted",
      date: "10 Jun 2026",
      status: "Completed",
    },

    {
      title: "Documents Submitted",
      date: "12 Jun 2026",
      status: "Completed",
    },

    {
      title: "HR Verification",
      date: "13 Jun 2026",
      status: "Completed",
    },

    {
      title: "Laptop Allocation",
      date: "15 Jun 2026",
      status: "Completed",
    },

    {
      title: "Team Introduction",
      date: "20 Jun 2026",
      status: "Pending",
    },

    {
      title: "Technical Training",
      date: "24 Jun 2026",
      status: "Pending",
    },

    {
      title: "Project Allocation",
      date: "30 Jun 2026",
      status: "Pending",
    },
  ];

  const checklist = [
    {
      title: "Accept Offer Letter",
      subtitle: "Employment contract signed",
      completed: true,
    },

    {
      title: "Submit Aadhaar Card",
      subtitle: "Identity verification",
      completed: true,
    },

    {
      title: "Submit PAN Card",
      subtitle: "Tax verification",
      completed: true,
    },

    {
      title: "Upload Degree Certificate",
      subtitle: "Educational verification",
      completed: true,
    },

    {
      title: "Complete HR Orientation",
      subtitle: "Mandatory HR induction",
      completed: false,
    },

    {
      title: "Meet Reporting Manager",
      subtitle: "Manager introduction",
      completed: false,
    },

    {
      title: "Complete Technical Training",
      subtitle: "Training module",
      completed: false,
    },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="My Onboarding"
        showBack={false}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <OnboardingStatusCard
          employeeName={onboarding.employeeName}
          employeeId={onboarding.employeeId}
          status={onboarding.status}
        />

        <ProgressCard
          progress={onboarding.progress}
        />

        <CompanyInfoCard
          designation={onboarding.designation}
          department={onboarding.department}
          manager={onboarding.manager}
          officeLocation={onboarding.officeLocation}
          joiningDate={onboarding.joiningDate}
          workMode={onboarding.workMode}
          employmentType={onboarding.employmentType}
          shift={onboarding.shift}
        />

        <HRContactCard
          name={onboarding.hr.name}
          designation={onboarding.hr.designation}
          email={onboarding.hr.email}
          phone={onboarding.hr.phone}
          onCall={() => {
            console.log("Call HR");
          }}
          onEmail={() => {
            console.log("Email HR");
          }}
        />

        <TimelineCard
          timeline={timeline}
        />

        <ChecklistCard
          items={checklist}
        />

        <NextActionCard
          title="Complete HR Orientation"
          description="Attend the mandatory HR onboarding session to learn about company policies, benefits, and workplace guidelines."
          dueDate="24 June 2026"
          priority="High"
          onPress={() => {
            console.log("Continue Onboarding");
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
});